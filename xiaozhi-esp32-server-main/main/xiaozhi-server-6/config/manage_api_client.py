import os
import time
import base64
from typing import Optional, Dict

import httpx

TAG = __name__


class DeviceNotFoundException(Exception):
    pass


class DeviceBindException(Exception):
    def __init__(self, bind_code):
        self.bind_code = bind_code
        super().__init__(f"设备绑定异常，绑定码: {bind_code}")


class ManageApiClient:
    _instance = None
    _client = None
    _secret = None

    def __new__(cls, config):
        """单例模式确保全局唯一实例，并支持传入配置参数"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._init_client(config)
        return cls._instance

    @classmethod
    def _init_client(cls, config):
        """初始化持久化连接池"""
        cls.config = config.get("manager-api")

        if not cls.config:
            raise Exception("manager-api配置错误")

        if not cls.config.get("url") or not cls.config.get("secret"):
            raise Exception("manager-api的url或secret配置错误")

        if "你" in cls.config.get("secret"):
            raise Exception("请先配置manager-api的secret")

        cls._secret = cls.config.get("secret")
        cls.max_retries = cls.config.get("max_retries", 6)  # 最大重试次数
        cls.retry_delay = cls.config.get("retry_delay", 10)  # 初始重试延迟(秒)
        # NOTE(goody): 2025/4/16 http相关资源统一管理，后续可以增加线程池或者超时
        # 后续也可以统一配置apiToken之类的走通用的Auth
        cls._client = httpx.Client(
            base_url=cls.config.get("url"),
            headers={
                "User-Agent": f"PythonClient/2.0 (PID:{os.getpid()})",
                "Accept": "application/json",
                "Authorization": "Bearer " + cls._secret,
            },
            timeout=cls.config.get("timeout", 30),  # 默认超时时间30秒
        )

    @classmethod
    def _request(cls, method: str, endpoint: str, **kwargs) -> Dict:
        """发送单次HTTP请求并处理响应"""
        endpoint = endpoint.lstrip("/")
        print('endpoint', endpoint)
        print('wwwwwww', kwargs)
        # response = cls._client.request(method, endpoint, **kwargs)
        response = cls._client.request(method, endpoint, json=kwargs)
        response.raise_for_status()

        result = response.json()

        # 处理API返回的业务错误
        if result.get("code") == 10041:
            raise DeviceNotFoundException(result.get("msg"))
        elif result.get("code") == 10042:
            raise DeviceBindException(result.get("msg"))
        elif result.get("code") != 0:
            raise Exception(f"API返回错误: {result.get('msg', '未知错误')}")

        # 返回成功数据
        return result.get("data") if result.get("code") == 0 else None

    @classmethod
    def _should_retry(cls, exception: Exception) -> bool:
        """判断异常是否应该重试"""
        # 网络连接相关错误
        if isinstance(
            exception, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)
        ):
            return True

        # HTTP状态码错误
        if isinstance(exception, httpx.HTTPStatusError):
            status_code = exception.response.status_code
            return status_code in [408, 429, 500, 502, 503, 504]

        return False

    @classmethod
    def _execute_request(cls, method: str, endpoint: str, **kwargs) -> Dict:
        """带重试机制的请求执行器"""
        retry_count = 0

        while retry_count <= cls.max_retries:
            try:
                # 执行请求
                return cls._request(method, endpoint, **kwargs)
            except Exception as e:
                # 判断是否应该重试
                if retry_count < cls.max_retries and cls._should_retry(e):
                    retry_count += 1
                    print(
                        f"{method} {endpoint} 请求失败，将在 {cls.retry_delay:.1f} 秒后进行第 {retry_count} 次重试"
                    )
                    time.sleep(cls.retry_delay)
                    continue
                else:
                    # 不重试，直接抛出异常
                    raise

    @classmethod
    def safe_close(cls):
        """安全关闭连接池"""
        if cls._client:
            cls._client.close()
            cls._instance = None


def get_server_config() -> Optional[Dict]:
    """获取服务器基础配置"""
    from getmac import get_mac_address
    device_id = get_mac_address()
    return ManageApiClient._instance._execute_request("POST", "/config/server-base", deviceId=device_id)


def get_agent_models(
    mac_address: str, client_id: str, selected_module: Dict
) -> Optional[Dict]:
    """获取代理模型配置"""
    return ManageApiClient._instance._execute_request(
        "POST",
        "/config/agent-models",
        macAddress=mac_address,
        clientId=client_id,
        selectedModule=selected_module,
        # json={
        #     "macAddress": mac_address,
        #     "clientId": client_id,
        #     "selectedModule": selected_module,
        # },
    )


def save_mem_local_short(mac_address: str, short_momery: str) -> Optional[Dict]:
    try:
        return ManageApiClient._instance._execute_request(
            "PUT",
            f"/agent/saveMemory/" + mac_address,
            summaryMemory=short_momery,
            # json={
            #     "summaryMemory": short_momery,
            # },
        )
    except Exception as e:
        print(f"存储短期记忆到服务器失败: {e}")
        return None

def save_memobase(mac_address: str, short_momery: str) -> Optional[Dict]:
    try:
        from memobase import Memobase
        client = Memobase(project_url='http://47.98.51.180:8019', api_key='secret')
        print('client', client)
        users = client.get_all_users(search="", order_by='updated_at', order_desc=True)
        print('users', users)
        u_id = None
        for user in users:
            print(user.get('additional_fields'))
            if mac_address in user.get('additional_fields'):
                u_id = user.get('id')
                break
        if not u_id:
            u_id = client.add_user({mac_address: mac_address})
        u = client.get_user(u_id)
        events = u.event(topk=5)
        eid = events[0].id
        u.update_event(eid, {'event_tip': short_momery})
        print(u.event(topk=1))
    except Exception as e:
        print(f"存储memobase记忆到服务器失败: {e}")
        return None


def report(
    mac_address: str, session_id: str, chat_type: int, content: str, audio, report_time
) -> Optional[Dict]:
    """带熔断的业务方法示例"""
    if not content or not ManageApiClient._instance:
        return None
    try:
        return ManageApiClient._instance._execute_request(
            "POST",
            f"/agent/chat-history/report",
            macAddress=mac_address,
            sessionId=session_id,
            chatType=chat_type,
            content=content,
            reportTime=report_time,
            audioBase64=(
                base64.b64encode(audio).decode("utf-8") if audio else None
            ),
            # json={
            #     "macAddress": mac_address,
            #     "sessionId": session_id,
            #     "chatType": chat_type,
            #     "content": content,
            #     "reportTime": report_time,
            #     "audioBase64": (
            #         base64.b64encode(audio).decode("utf-8") if audio else None
            #     ),
            # },
        )
    except Exception as e:
        print(f"TTS上报失败: {e}")
        return None


def forward_log_to_java(config, log_data) -> Optional[Dict]:
    """转发主动问候日志到Java后端 - 增强认证错误处理"""
    if not log_data or not ManageApiClient._instance:
        return None
    
    # 检查是否禁用日志转发
    manager_api_config = config.get("manager-api", {})
    if not manager_api_config.get("enable_log_forward", True):
        return {"disabled": True, "reason": "log_forward_disabled"}
    
    # 获取认证错误处理配置
    auth_config = manager_api_config.get("auth_error_handling", {})
    ignore_auth_errors = auth_config.get("ignore_auth_errors", True)  # 默认忽略认证错误
    max_retries = auth_config.get("max_retry_attempts", 2)
    retry_interval = auth_config.get("retry_interval", 3)
    
    for attempt in range(max_retries + 1):
        try:
            result = ManageApiClient._instance._execute_request(
                "POST",
                f"/agent/proactive-greeting/log",
                **log_data
            )
            
            if result:
                if attempt > 0:
                    print(f"✅ 日志转发重试成功 (第{attempt+1}次尝试)")
                return result
            
        except Exception as e:
            error_msg = str(e)
            
            # 检查是否是Java认证问题
            is_auth_error = ("tokenEntity" in error_msg and "null" in error_msg)
            
            if is_auth_error:
                if ignore_auth_errors:
                    # 静默处理认证错误，不影响主要功能
                    print(f"⚠️ Java认证问题已忽略: tokenEntity为null (不影响设备正常工作)")
                    return {"ignored": True, "reason": "auth_error", "error": "tokenEntity_null"}
                
                if attempt < max_retries:
                    print(f"🔄 Java认证错误，{retry_interval}秒后重试... (第{attempt+1}/{max_retries+1}次)")
                    import time
                    time.sleep(retry_interval)
                    continue
                else:
                    print(f"❌ Java认证问题 (已重试{max_retries}次): Cannot invoke getUserId() - tokenEntity is null")
                    print("💡 解决建议:")
                    print("   1. 重启Java后端服务刷新认证token")
                    print("   2. 检查Java端SysUserTokenEntity配置") 
                    print("   3. 或在config.yaml中添加: manager-api.auth_error_handling.ignore_auth_errors: true")
                    return {"error": "auth_failed", "details": error_msg}
            else:
                # 其他类型错误
                if attempt < max_retries:
                    print(f"🔄 日志转发失败，{retry_interval}秒后重试: {e}")
                    import time
                    time.sleep(retry_interval)
                    continue
                else:
                    print(f"❌ 日志转发最终失败: {e}")
    
    return None


def init_service(config):
    ManageApiClient(config)


def manage_api_http_safe_close():
    ManageApiClient.safe_close()

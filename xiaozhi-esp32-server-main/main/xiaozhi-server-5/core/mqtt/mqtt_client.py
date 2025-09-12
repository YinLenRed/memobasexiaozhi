import json
import uuid
import time
import asyncio
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from paho.mqtt import client as mqtt_client
from config.logger import setup_logging

TAG = __name__


class MQTTClient:
    """MQTT客户端，用于与ESP32设备通信"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()
        
        # MQTT配置
        self.broker_host = config.get("mqtt", {}).get("host", "47.97.185.142")
        self.broker_port = config.get("mqtt", {}).get("port", 1883)
        self.username = config.get("mqtt", {}).get("username", "")
        self.password = config.get("mqtt", {}).get("password", "")
        # 获取客户端ID，如果为空则生成Python服务专用ID
        configured_client_id = config.get("mqtt", {}).get("client_id", "")
        if configured_client_id and configured_client_id.strip():
            self.client_id = configured_client_id
        else:
            self.client_id = f"xiaozhi-python-server-{uuid.uuid4().hex[:8]}"
        
        # MQTT客户端
        self.client = None
        self.connected = False
        self.running = False
        
        # 消息处理器
        self.message_handlers: Dict[str, Callable] = {}
        self.device_ack_handlers: Dict[str, Callable] = {}
        self.global_message_handler = None
        
        # 设备状态跟踪
        self.device_states: Dict[str, Dict] = {}
        
        # Java报告的设备在线状态
        self.java_device_online_status: Dict[str, bool] = {}
        
        # 线程安全锁
        self.lock = threading.Lock()
        
        # 保存主事件循环引用
        self._main_loop = None
        
    async def start(self):
        """启动MQTT客户端"""
        if self.running:
            return
            
        self.running = True
        # 保存当前事件循环
        self._main_loop = asyncio.get_running_loop()
        self.client = mqtt_client.Client(client_id=self.client_id)
        
        # 设置用户名密码
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        # 设置回调函数
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        try:
            # 连接到MQTT代理
            self.logger.bind(tag=TAG).info(f"连接MQTT代理: {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            
            # 启动网络循环线程
            self.client.loop_start()
            
            # 等待连接建立
            for _ in range(30):  # 最多等待30秒
                if self.connected:
                    break
                await asyncio.sleep(1)
            
            if not self.connected:
                raise Exception("MQTT连接超时")
                
            self.logger.bind(tag=TAG).info("MQTT客户端启动成功")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MQTT客户端启动失败: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """停止MQTT客户端"""
        if not self.running:
            return
            
        self.running = False
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            
        self.connected = False
        self.logger.bind(tag=TAG).info("MQTT客户端已停止")
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接成功回调"""
        if rc == 0:
            self.connected = True
            self.logger.bind(tag=TAG).info("MQTT连接成功")
            
            # 订阅设备回复和事件主题
            client.subscribe("device/+/ack")
            client.subscribe("device/+/event")
            
            # 订阅Java设备状态主题
            client.subscribe("xiaozhi/java-to-python/device-status/+")
            
            self.logger.bind(tag=TAG).info("已订阅设备主题: device/+/ack, device/+/event")
            self.logger.bind(tag=TAG).info("已订阅Java设备状态主题: xiaozhi/java-to-python/device-status/+")
        else:
            self.logger.bind(tag=TAG).error(f"MQTT连接失败，返回码: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self.connected = False
        if rc != 0:
            self.logger.bind(tag=TAG).warning(f"MQTT意外断开连接，返回码: {rc}")
        else:
            self.logger.bind(tag=TAG).info("MQTT正常断开连接")
    
    def _on_message(self, client, userdata, msg):
        """消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            self.logger.bind(tag=TAG).debug(f"收到MQTT消息: {topic} -> {payload}")
            
            # 特别关注统一事件主题的消息
            if topic == "server/dev/report/event":
                self.logger.bind(tag=TAG).info(f"📨 收到Java后端事件: {topic}")
                self.logger.bind(tag=TAG).info(f"📄 消息内容: {payload}")
            
            # 检查是否是Java设备状态消息
            if topic.startswith("xiaozhi/java-to-python/device-status/"):
                device_id = topic.split("/")[-1]
                try:
                    message_data = json.loads(payload)
                    self._handle_java_device_status(device_id, message_data)
                except json.JSONDecodeError:
                    self.logger.bind(tag=TAG).error(f"无法解析Java设备状态消息: {payload}")
                return
            
            # 解析设备ID
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3:
                device_id = topic_parts[1]
                message_type = topic_parts[2]
                
                # 解析消息内容
                try:
                    message_data = json.loads(payload)
                except json.JSONDecodeError:
                    self.logger.bind(tag=TAG).error(f"无法解析JSON消息: {payload}")
                    return
                
                # 处理不同类型的消息
                if message_type == "ack":
                    self._handle_device_ack(device_id, message_data)
                elif message_type == "event":
                    self._handle_device_event(device_id, message_data)
            
            # 调用全局消息处理器（用于统一事件服务等）
            if self.global_message_handler and self._main_loop:
                try:
                    # 使用主事件循环调度协程
                    def schedule_handler():
                        try:
                            task = self.global_message_handler(client, userdata, msg)
                            asyncio.create_task(task)
                        except Exception as e:
                            self.logger.bind(tag=TAG).error(f"调度消息处理器失败: {e}")
                    
                    self._main_loop.call_soon_threadsafe(schedule_handler)
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"全局消息处理器失败: {e}")
                    
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理MQTT消息失败: {e}")
    
    def _handle_device_ack(self, device_id: str, message_data: Dict):
        """处理设备ACK消息"""
        track_id = message_data.get("track_id")
        
        if track_id:
            # 更新设备状态
            with self.lock:
                if device_id not in self.device_states:
                    self.device_states[device_id] = {}
                self.device_states[device_id][track_id] = {
                    "status": "ack_received",
                    "timestamp": datetime.now().isoformat(),
                    "ack_data": message_data
                }
            
            # 调用注册的ACK处理器
            if track_id in self.device_ack_handlers:
                try:
                    self.device_ack_handlers[track_id](device_id, message_data)
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"处理设备ACK失败: {e}")
            
            # 触发默认的ACK后续处理（如果有注册的话）
            if hasattr(self, 'default_ack_handler') and self.default_ack_handler:
                try:
                    # 使用事件循环安全的方式调度协程
                    if self._main_loop and not self._main_loop.is_closed():
                        asyncio.run_coroutine_threadsafe(
                            self.default_ack_handler(device_id, track_id, message_data),
                            self._main_loop
                        )
                    else:
                        self.logger.bind(tag=TAG).warning("主事件循环不可用，跳过默认ACK处理器")
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"默认ACK处理器失败: {e}")
        
        self.logger.bind(tag=TAG).info(f"设备 {device_id} ACK: {message_data}")
    
    def set_default_ack_handler(self, handler):
        """设置默认的ACK处理器"""
        self.default_ack_handler = handler
    
    async def subscribe(self, topic: str, qos: int = 1):
        """订阅MQTT主题"""
        if not self.connected or not self.client:
            self.logger.bind(tag=TAG).warning(f"MQTT未连接，无法订阅主题: {topic}")
            return False
            
        try:
            result, _ = self.client.subscribe(topic, qos)
            if result == mqtt_client.MQTT_ERR_SUCCESS:
                self.logger.bind(tag=TAG).info(f"成功订阅MQTT主题: {topic}")
                return True
            else:
                self.logger.bind(tag=TAG).error(f"订阅MQTT主题失败: {topic}, 错误码: {result}")
                return False
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"订阅MQTT主题异常: {topic}, 错误: {e}")
            return False
    
    async def unsubscribe(self, topic: str):
        """取消订阅MQTT主题"""
        if not self.connected or not self.client:
            self.logger.bind(tag=TAG).warning(f"MQTT未连接，无法取消订阅: {topic}")
            return False
            
        try:
            result, _ = self.client.unsubscribe(topic)
            if result == mqtt_client.MQTT_ERR_SUCCESS:
                self.logger.bind(tag=TAG).info(f"成功取消订阅MQTT主题: {topic}")
                return True
            else:
                self.logger.bind(tag=TAG).error(f"取消订阅MQTT主题失败: {topic}, 错误码: {result}")
                return False
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"取消订阅MQTT主题异常: {topic}, 错误: {e}")
            return False
    
    def register_message_handler(self, topic_pattern: str, handler):
        """注册消息处理器"""
        self.message_handlers[topic_pattern] = handler
        self.logger.bind(tag=TAG).info(f"注册消息处理器: {topic_pattern}")
    
    def set_message_callback(self, handler):
        """设置通用消息回调（向后兼容）"""
        self.global_message_handler = handler
    
    def _handle_device_event(self, device_id: str, message_data: Dict):
        """处理设备事件消息"""
        event_type = message_data.get("evt")
        track_id = message_data.get("track_id")
        
        if event_type == "EVT_SPEAK_DONE" and track_id:
            # 更新设备状态
            with self.lock:
                if device_id in self.device_states and track_id in self.device_states[device_id]:
                    self.device_states[device_id][track_id]["status"] = "speak_done"
                    self.device_states[device_id][track_id]["completed_timestamp"] = datetime.now().isoformat()
        
        # 调用注册的消息处理器
        for handler in self.message_handlers.values():
            try:
                handler(device_id, event_type, message_data)
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"处理设备事件失败: {e}")
        
        self.logger.bind(tag=TAG).info(f"设备 {device_id} 事件: {message_data}")
    
    async def send_speak_command(self, device_id: str, text: str, track_id: str = None) -> str:
        """发送语音播放命令"""
        if not self.connected:
            raise Exception("MQTT未连接")
        
        if not track_id:
            track_id = f"WX{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"
        
        command = {
            "cmd": "SPEAK",
            "text": text,
            "track_id": track_id
        }
        
        # 使用配置中的主题模板，如果没有则使用默认值
        topic_template = self.config.get("mqtt", {}).get("topics", {}).get("command", "device/{device_id}/cmd")
        topic = topic_template.format(device_id=device_id)
        
        # 记录发送状态
        with self.lock:
            if device_id not in self.device_states:
                self.device_states[device_id] = {}
            self.device_states[device_id][track_id] = {
                "status": "command_sent",
                "timestamp": datetime.now().isoformat(),
                "text": text
            }
        
        # 发送MQTT消息
        result = self.client.publish(topic, json.dumps(command, ensure_ascii=False))
        
        if result.rc == 0:
            self.logger.bind(tag=TAG).info(f"发送语音命令成功: {device_id} -> {text[:50]}...")
            return track_id
        else:
            raise Exception(f"发送MQTT消息失败，返回码: {result.rc}")
    
    async def send_awaken_command(self, device_id: str, message: str, message_type: str = "weather") -> str:
        """发送设备唤醒命令"""
        if not self.connected:
            raise Exception("MQTT未连接")
        
        track_id = f"AW{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"
        
        command = {
            "type": message_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "track_id": track_id
        }
        
        # 使用唤醒设备专用主题
        topic = f"device/{device_id}/awaken"
        
        # 记录发送状态
        with self.lock:
            if device_id not in self.device_states:
                self.device_states[device_id] = {}
            self.device_states[device_id][track_id] = {
                "status": "awaken_command_sent",
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "message_type": message_type
            }
        
        # 发送MQTT消息
        result = self.client.publish(topic, json.dumps(command, ensure_ascii=False))
        
        if result.rc == 0:
            self.logger.bind(tag=TAG).info(f"发送唤醒命令成功: {device_id} -> {message_type}: {message[:50]}...")
            return track_id
        else:
            raise Exception(f"发送MQTT消息失败，返回码: {result.rc}")
    
    def send_message_to_topic(self, topic: str, message: dict) -> bool:
        """发送消息到指定主题（同步版本）"""
        if not self.connected:
            raise Exception("MQTT未连接")
        
        # 发送MQTT消息
        result = self.client.publish(topic, json.dumps(message, ensure_ascii=False))
        
        if result.rc == 0:
            self.logger.bind(tag=TAG).info(f"发送消息成功: {topic} -> {str(message)[:100]}...")
            return True
        else:
            self.logger.bind(tag=TAG).error(f"发送MQTT消息失败，返回码: {result.rc}")
            return False
    
    def register_ack_handler(self, track_id: str, handler: Callable):
        """注册ACK处理器"""
        self.device_ack_handlers[track_id] = handler
    
    def register_message_handler(self, name: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[name] = handler
    
    def get_device_state(self, device_id: str, track_id: str = None) -> Dict:
        """获取设备状态"""
        with self.lock:
            if device_id not in self.device_states:
                return {}
            
            if track_id:
                return self.device_states[device_id].get(track_id, {})
            
            return self.device_states[device_id]
    
    def _handle_java_device_status(self, device_id: str, message_data: Dict):
        """处理Java发送的设备状态更新"""
        try:
            status = message_data.get("status", "").lower()
            is_online = status == "online"
            
            with self.lock:
                self.java_device_online_status[device_id] = is_online
            
            self.logger.bind(tag=TAG).info(f"📥 Java设备状态更新: {device_id} -> {'在线' if is_online else '离线'}")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理Java设备状态失败: {e}")
    
    def is_device_online_from_java(self, device_id: str) -> bool:
        """获取Java报告的设备在线状态"""
        with self.lock:
            return self.java_device_online_status.get(device_id, False)
    
    def get_all_java_device_status(self) -> Dict[str, bool]:
        """获取所有Java报告的设备状态"""
        with self.lock:
            return self.java_device_online_status.copy()
    
    def cleanup_old_states(self, max_age_hours: int = 24):
        """清理旧状态记录"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        with self.lock:
            for device_id in list(self.device_states.keys()):
                device_tracks = self.device_states[device_id]
                for track_id in list(device_tracks.keys()):
                    track_info = device_tracks[track_id]
                    track_time = datetime.fromisoformat(track_info["timestamp"]).timestamp()
                    
                    if track_time < cutoff_time:
                        del device_tracks[track_id]
                
                # 如果设备没有任何跟踪记录，删除设备记录
                if not device_tracks:
                    del self.device_states[device_id]

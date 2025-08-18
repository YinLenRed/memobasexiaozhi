"""
Memobase客户端 - 集成记忆数据库服务
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List
from config.logger import setup_logging

TAG = __name__


class MemobaseClient:
    """Memobase记忆数据库客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()
        
        # Memobase配置
        memobase_config = config.get("proactive_greeting", {}).get("content_generation", {}).get("memobase", {})
        self.host = memobase_config.get("host", "47.98.51.180")
        self.port = memobase_config.get("port", 8019)
        self.api_endpoint = memobase_config.get("api_endpoint", f"http://{self.host}:{self.port}")
        self.timeout = memobase_config.get("timeout", 10)
        self.enabled = memobase_config.get("enabled", True)
        
        # 认证配置
        self.api_key = memobase_config.get("api_key", "")
        self.auth_token = memobase_config.get("auth_token", "")
        self.auth_header = memobase_config.get("auth_header", "Authorization")
        
        if not self.enabled:
            self.logger.bind(tag=TAG).warning("Memobase服务已禁用")
        else:
            self.logger.bind(tag=TAG).info(f"Memobase客户端初始化: {self.api_endpoint}")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """构建认证头部"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "xiaozhi-esp32-server/1.2.0"
        }
        
        if self.api_key:
            headers[self.auth_header] = f"Bearer {self.api_key}"
        elif self.auth_token:
            headers[self.auth_header] = self.auth_token
            
        return headers
    
    async def get_user_memory(self, user_id: str, device_id: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """获取用户记忆信息（使用用户上下文API）"""
        if not self.enabled:
            self.logger.bind(tag=TAG).debug("Memobase服务未启用，返回空记忆")
            return []
        
        try:
            # 调用Memobase用户上下文API
            url = f"{self.api_endpoint}/api/v1/users/context/{user_id}"
            headers = self._get_auth_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("errno") == 0:
                            context = data.get("data", {}).get("context", "")
                            self.logger.bind(tag=TAG).info(f"获取用户 {user_id} 上下文成功")
                            # 将上下文转换为记忆格式
                            return [{"context": context, "type": "user_context"}] if context else []
                        else:
                            self.logger.bind(tag=TAG).warning(f"Memobase API错误: {data.get('errmsg')}")
                            return []
                    else:
                        self.logger.bind(tag=TAG).warning(f"Memobase API返回错误: {response.status}")
                        return []
                        
        except asyncio.TimeoutError:
            self.logger.bind(tag=TAG).error(f"Memobase API调用超时: {self.timeout}秒")
            return []
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取用户记忆失败: {e}")
            return []
    
    async def get_user_context(self, user_id: str) -> str:
        """获取用户上下文记忆（直接返回文本）"""
        if not self.enabled:
            return ""
        
        try:
            url = f"{self.api_endpoint}/api/v1/users/context/{user_id}"
            headers = self._get_auth_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("errno") == 0:
                            context = data.get("data", {}).get("context", "")
                            self.logger.bind(tag=TAG).info(f"获取用户 {user_id} 上下文成功")
                            return context
                    return ""
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取用户上下文失败: {e}")
            return ""
    
    async def save_interaction_memory(
        self, 
        user_id: str, 
        device_id: str, 
        greeting_content: str, 
        user_response: str = None,
        interaction_type: str = "greeting"
    ) -> bool:
        """保存交互记忆（使用正确的blob插入API格式）"""
        if not self.enabled:
            return True
        
        try:
            # 构建OpenAI兼容的消息格式
            messages = [
                {
                    "role": "assistant", 
                    "content": f"主动问候: {greeting_content}",
                    "created_at": self._get_current_timestamp()
                }
            ]
            
            if user_response:
                messages.append({
                    "role": "user", 
                    "content": user_response,
                    "created_at": self._get_current_timestamp()
                })
            
            # 正确的blob格式：blob_data是字典，包含messages字段
            blob_data = {
                "blob_type": "chat",
                "blob_data": {
                    "messages": messages
                },
                "fields": {
                    "device_id": device_id,
                    "interaction_type": interaction_type,
                    "timestamp": self._get_current_timestamp(),
                    "success": user_response is not None,
                    "category": "proactive_greeting",
                    "greeting_category": "health_reminder"
                }
            }
            
            # 调用Memobase blob插入API
            url = f"{self.api_endpoint}/api/v1/blobs/insert/{user_id}"
            headers = self._get_auth_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=blob_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("errno") == 0:
                            blob_id = data.get("data", {}).get("id")
                            self.logger.bind(tag=TAG).info(f"保存用户 {user_id} 交互记忆成功, blob_id: {blob_id}")
                            return True
                        else:
                            self.logger.bind(tag=TAG).warning(f"保存记忆API错误: {data.get('errmsg')}")
                            return False
                    else:
                        response_text = await response.text()
                        self.logger.bind(tag=TAG).warning(f"保存记忆失败: {response.status}, 响应: {response_text[:200]}")
                        return False
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"保存交互记忆失败: {e}")
            return False
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳（ISO格式）"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户偏好信息"""
        if not self.enabled:
            return {}
        
        try:
            url = f"{self.api_endpoint}/api/memory/preferences/{user_id}"
            headers = self._get_auth_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        preferences = data.get("preferences", {})
                        self.logger.bind(tag=TAG).info(f"获取用户 {user_id} 偏好信息成功")
                        return preferences
                    else:
                        self.logger.bind(tag=TAG).warning(f"获取用户偏好失败: {response.status}")
                        return {}
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取用户偏好失败: {e}")
            return {}
    
    def format_memories_for_greeting(self, memories: List[Dict[str, Any]]) -> str:
        """将记忆数据格式化为适合问候的文本"""
        if not memories:
            return ""
        
        try:
            for memory in memories:
                if memory.get("type") == "user_context":
                    context = memory.get("context", "")
                    if context:
                        # 解析Markdown格式的上下文
                        return self._parse_context_for_greeting(context)
            
            return ""
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化记忆信息失败: {e}")
            return ""
    
    def _parse_context_for_greeting(self, context: str) -> str:
        """解析上下文内容，提取适合问候的信息"""
        try:
            # 简单解析Markdown格式的上下文
            lines = context.split('\n')
            current_state = []
            past_events = []
            
            in_current_state = False
            in_past_events = False
            
            for line in lines:
                line = line.strip()
                if "用户当前状态" in line:
                    in_current_state = True
                    in_past_events = False
                elif "过去事件" in line:
                    in_current_state = False
                    in_past_events = True
                elif line.startswith("- ") and line != "- ":
                    if in_current_state:
                        current_state.append(line[2:])
                    elif in_past_events:
                        past_events.append(line[2:])
                elif line.startswith("---"):
                    break
            
            # 构建问候用的记忆文本
            memory_parts = []
            if current_state:
                memory_parts.extend(current_state[:2])  # 最多2条当前状态
            if past_events:
                memory_parts.extend(past_events[:2])   # 最多2条过去事件
            
            if memory_parts:
                return "；".join(memory_parts)
            else:
                return ""
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"解析上下文失败: {e}")
            return ""
    
    async def health_check(self) -> bool:
        """检查Memobase服务健康状态"""
        if not self.enabled:
            return False
        
        try:
            url = f"{self.api_endpoint}/api/v1/healthcheck"
            headers = self._get_auth_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    is_healthy = response.status == 200
                    self.logger.bind(tag=TAG).info(f"Memobase健康检查: {'正常' if is_healthy else '异常'}")
                    return is_healthy
                    
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"Memobase健康检查失败: {e}")
            return False


# 便捷函数
async def get_user_memory_text(config: Dict[str, Any], user_id: str, device_id: str = None) -> str:
    """
    获取用户记忆信息的便捷函数
    
    Args:
        config: 应用配置
        user_id: 用户ID（需要是UUID格式）
        device_id: 设备ID
        
    Returns:
        str: 格式化的记忆文本
    """
    client = MemobaseClient(config)
    
    # 直接获取用户上下文
    context = await client.get_user_context(user_id)
    if context:
        return client._parse_context_for_greeting(context)
    else:
        return ""


# Function Calling支持
async def get_user_memory_for_greeting(user_id: str, device_id: str, config: Dict[str, Any]) -> str:
    """
    LLM Function Calling使用的记忆查询函数
    
    Args:
        user_id: 用户ID
        device_id: 设备ID
        config: 应用配置
        
    Returns:
        str: 格式化的记忆信息文本
    """
    return await get_user_memory_text(config, user_id, device_id)


# Function Calling的函数定义
MEMORY_FUNCTION_DEFINITION = {
    "name": "get_user_memory_for_greeting",
    "description": "获取用户的历史记忆信息，用于生成个性化的问候内容",
    "parameters": {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "用户ID，用于查询该用户的记忆信息"
            },
            "device_id": {
                "type": "string",
                "description": "设备ID，用于获取与该设备相关的记忆"
            }
        },
        "required": ["user_id", "device_id"]
    }
}

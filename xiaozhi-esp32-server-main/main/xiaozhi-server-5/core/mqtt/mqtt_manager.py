import asyncio
from typing import Dict, Any, Optional
from core.mqtt.mqtt_client import MQTTClient
from core.mqtt.proactive_greeting_service import ProactiveGreetingService
from core.mqtt.webhook_callback_handler import WebhookCallbackHandler
from core.services.unified_event_service import UnifiedEventService
from config.logger import setup_logging

TAG = __name__

# 🔧 全局MQTT管理器实例，用于跨模块访问
_global_mqtt_manager = None

def get_global_mqtt_manager() -> Optional['MQTTManager']:
    """获取全局MQTT管理器实例"""
    return _global_mqtt_manager

def set_global_mqtt_manager(manager):
    """设置全局MQTT管理器实例"""
    global _global_mqtt_manager
    _global_mqtt_manager = manager

def get_global_mqtt_client():
    """获取全局MQTT客户端实例"""
    global _global_mqtt_manager
    if _global_mqtt_manager and hasattr(_global_mqtt_manager, 'mqtt_client'):
        return _global_mqtt_manager.mqtt_client
    return None


class MQTTManager:
    """MQTT管理器，统一管理MQTT客户端和相关服务"""
    
    def __init__(self, config: Dict[str, Any], llm_instance=None, tts_instance=None, websocket_server=None):
        self.config = config
        self.logger = setup_logging()
        
        # 设置为全局实例
        set_global_mqtt_manager(self)
        
        # 初始化组件
        self.mqtt_client = MQTTClient(config)
        # 给MQTT客户端添加WebSocket服务器引用
        self.mqtt_client.websocket_server = websocket_server
        self.greeting_service = ProactiveGreetingService(config, self.mqtt_client, llm_instance, tts_instance)
        
        # 🔧 关键修复：初始化WebhookCallbackHandler（参考xiaozhi-server-2）
        self.webhook_handler = WebhookCallbackHandler(config, self.mqtt_client, tts_instance)
        self.logger.bind(tag=TAG).info("✅ WebhookCallbackHandler初始化成功")
        
        # 检查是否启用统一事件系统
        event_system_config = config.get("event_system", {})
        
        # 如果从API读取配置但缺少event_system，提供默认配置
        if config.get("read_config_from_api", False) and not event_system_config:
            self.logger.bind(tag=TAG).info("🔧 API配置缺少event_system，使用默认配置")
            # 提供默认的统一事件系统配置
            event_system_config = {
                "enabled": True,
                "topics": ["server/dev/report/event"],
                "device_location_mapping": {
                    "device_001": "西平县",
                    "device_002": "驻马店市",
                    "test_device": "西平县", 
                    "00:0c:29:fc:b7:b9": "西平县",
                    "device-6c": "北京市",
                    "device-3": "北京市"
                },
                "weather_alert": {
                    "max_content_length": 300,
                    "priority_levels": {
                        "Blue": "蓝色预警",
                        "Yellow": "黄色预警", 
                        "Orange": "橙色预警",
                        "Red": "红色预警"
                    },
                    "type_mapping": {
                        "1003": "暴雨预警",
                        "1250": "地质灾害预警"
                    }
                },
                "solar_terms": {
                    "enabled": True,
                    "advance_days": 1,
                    "reminder_time": "08:00"
                },
                "holidays": {
                    "enabled": True, 
                    "advance_days": 1,
                    "reminder_time": "09:00"
                }
            }
            # 将默认配置添加到config中
            config["event_system"] = event_system_config
            self.logger.bind(tag=TAG).info("✅ 已应用默认event_system配置")
        
        # 添加调试信息
        self.logger.bind(tag=TAG).info(f"🔍 配置诊断: event_system存在={bool('event_system' in config)}")
        self.logger.bind(tag=TAG).info(f"🔍 配置诊断: enabled值={event_system_config.get('enabled', 'NOT_FOUND')}")
        
        if event_system_config.get("enabled", False):
            self.unified_event_service = UnifiedEventService(self.mqtt_client)
            self.logger.bind(tag=TAG).info("统一事件服务已加载")
        else:
            self.unified_event_service = None
            self.logger.bind(tag=TAG).info("统一事件服务未启用 - enabled=False或event_system不存在")
        
        # 运行状态
        self.running = False
        
        # 记录传入的实例状态
        if llm_instance:
            self.logger.bind(tag=TAG).info("MQTT管理器使用外部LLM实例")
        if tts_instance:
            self.logger.bind(tag=TAG).info("MQTT管理器使用外部TTS实例")
    
    async def start(self):
        """启动MQTT管理器"""
        if self.running:
            return
        
        try:
            self.logger.bind(tag=TAG).info("启动MQTT管理器...")
            
            # 启动MQTT客户端
            await self.mqtt_client.start()
            
            # 启动主动问候服务
            await self.greeting_service.start()
            
            # 启动统一事件服务（如果启用）
            if self.unified_event_service:
                await self.unified_event_service.start()
                self.logger.bind(tag=TAG).info("统一事件服务启动成功")
            
            self.running = True
            self.logger.bind(tag=TAG).info("MQTT管理器启动成功")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MQTT管理器启动失败: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """停止MQTT管理器"""
        if not self.running:
            return
        
        self.logger.bind(tag=TAG).info("停止MQTT管理器...")
        
        # 停止服务
        if hasattr(self, 'unified_event_service') and self.unified_event_service:
            await self.unified_event_service.stop()
            self.logger.bind(tag=TAG).info("统一事件服务已停止")
        
        if hasattr(self, 'greeting_service'):
            await self.greeting_service.stop()
        
        if hasattr(self, 'mqtt_client'):
            await self.mqtt_client.stop()
        
        self.running = False
        self.logger.bind(tag=TAG).info("MQTT管理器已停止")
    
    async def send_proactive_greeting(
        self, 
        device_id: str, 
        initial_content: str, 
        category: str = "system_reminder",
        user_info: Dict[str, Any] = None,
        memory_info: str = None
    ) -> str:
        """发送主动问候（通过队列管理器发送API消息）"""
        if not self.running:
            raise Exception("MQTT管理器未启动")
        
        # 检查是否有统一事件服务和队列管理器
        if hasattr(self, 'unified_event_service') and self.unified_event_service:
            if hasattr(self.unified_event_service, 'message_queue'):
                try:
                    self.logger.bind(tag=TAG).info(f"🎵 API消息通过队列发送: {device_id} - {category}")
                    
                    # 生成消息内容（简化版本，直接使用initial_content）
                    content = initial_content
                    
                    # 设置优先级
                    priority = 1  # 默认优先级
                    if user_info and 'priority' in user_info:
                        try:
                            priority = int(user_info['priority'])
                        except (ValueError, TypeError):
                            priority = 1
                    
                    # 构建队列消息的用户信息
                    queue_user_info = {
                        "type": "api_greeting",
                        "category": category,
                        "original_user_info": user_info or {},
                        "memory_info": memory_info,
                        "timestamp": __import__('datetime').datetime.now().isoformat()
                    }
                    
                    # 添加消息到队列
                    message_id = self.unified_event_service.message_queue.add_message(
                        device_id=device_id,
                        content=content,
                        category=category,
                        priority=priority,
                        user_info=queue_user_info
                    )
                    
                    if message_id:
                        self.logger.bind(tag=TAG).info(f"✅ API消息已入队: {device_id}, 消息ID: {message_id}")
                        # 返回一个临时track_id，真实track_id由队列处理器生成
                        return f"API_{message_id[:12]}"
                    else:
                        self.logger.bind(tag=TAG).error("❌ API消息入队失败，回退到直接发送")
                        # 入队失败，回退到原来的方式
                        return await self.greeting_service.send_proactive_greeting(
                            device_id, initial_content, category, user_info, memory_info
                        )
                        
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"❌ 队列发送失败: {e}，回退到直接发送")
                    # 出错时回退到原来的方式
                    return await self.greeting_service.send_proactive_greeting(
                        device_id, initial_content, category, user_info, memory_info
                    )
            else:
                self.logger.bind(tag=TAG).warning("⚠️ 队列管理器未初始化，使用直接发送")
        else:
            self.logger.bind(tag=TAG).warning("⚠️ 统一事件服务未初始化，使用直接发送")
        
        # 回退到原来的发送方式
        return await self.greeting_service.send_proactive_greeting(
            device_id, initial_content, category, user_info, memory_info
        )
    
    def update_user_profile(self, device_id: str, user_info: Dict[str, Any]):
        """更新用户档案（对外接口）"""
        if self.running:
            self.greeting_service.update_user_profile(device_id, user_info)
    
    def get_device_state(self, device_id: str, track_id: str = None) -> Dict:
        """获取设备状态（对外接口）"""
        if not self.running:
            return {}
        
        return self.mqtt_client.get_device_state(device_id, track_id)
    
    def is_connected(self) -> bool:
        """检查MQTT连接状态"""
        return self.running and self.mqtt_client.connected
    
    def is_device_online(self, device_id: str) -> bool:
        """获取设备在线状态（优先使用Java报告的状态）"""
        if not self.running:
            return False
        return self.mqtt_client.is_device_online_from_java(device_id)
    
    def get_all_device_status(self) -> Dict[str, bool]:
        """获取所有设备状态"""
        if not self.running:
            return {}
        return self.mqtt_client.get_all_java_device_status()

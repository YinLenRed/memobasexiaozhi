import asyncio
from typing import Dict, Any, Optional
from core.mqtt.mqtt_client import MQTTClient
from core.mqtt.proactive_greeting_service import ProactiveGreetingService
from config.logger import setup_logging

TAG = __name__


class MQTTManager:
    """MQTT管理器，统一管理MQTT客户端和相关服务"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()
        
        # 初始化组件
        self.mqtt_client = MQTTClient(config)
        self.greeting_service = ProactiveGreetingService(config, self.mqtt_client)
        
        # 运行状态
        self.running = False
    
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
        """发送主动问候（对外接口）"""
        if not self.running:
            raise Exception("MQTT管理器未启动")
        
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主动天气问候服务
实现完整的流程：awaken -> MQTT -> ACK -> TTS -> WebSocket -> 硬件播放
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from config.logger import setup_logging
from core.tools.java_backend_weather import JavaBackendWeatherService, ProactiveWeatherGreetingService
from core.mqtt.webhook_callback_handler import AwakenWithCallbackService

TAG = __name__


class ProactiveWeatherService:
    """主动天气问候服务 - 集成天气查询和完整对话流程"""
    
    def __init__(self, config: Dict[str, Any], mqtt_client=None, tts_provider=None):
        self.config = config
        self.mqtt_client = mqtt_client
        self.tts_provider = tts_provider
        self.logger = setup_logging()
        
        # 初始化服务组件
        self.weather_service = JavaBackendWeatherService(config)
        self.greeting_service = ProactiveWeatherGreetingService(config, self.weather_service)
        self.awaken_service = AwakenWithCallbackService(config, mqtt_client, tts_provider)
        
        # 主动问候配置
        self.proactive_config = config.get("proactive_greeting", {})
        self.weather_config = self.proactive_config.get("weather", {})
        
        # 问候时间配置
        self.greeting_times = self.weather_config.get("greeting_times", {
            "morning": "08:00",
            "afternoon": "14:00", 
            "evening": "19:00"
        })
        
        # 设备列表
        self.target_devices = self.weather_config.get("devices", [])
        
        # 跟踪已发送的问候
        self.sent_greetings = {}
        
    async def start_proactive_weather_service(self):
        """启动主动天气问候服务"""
        self.logger.bind(tag=TAG).info("🌤️ 启动主动天气问候服务")
        
        # 启动定时任务
        asyncio.create_task(self._schedule_weather_greetings())
        
        self.logger.bind(tag=TAG).info("✅ 主动天气问候服务启动成功")
    
    async def _schedule_weather_greetings(self):
        """调度天气问候任务"""
        while True:
            try:
                current_time = datetime.now()
                
                # 检查每个时间点是否需要发送问候
                for greeting_type, time_str in self.greeting_times.items():
                    await self._check_and_send_greeting(current_time, greeting_type, time_str)
                
                # 每分钟检查一次
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"调度天气问候任务失败: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_send_greeting(self, current_time: datetime, greeting_type: str, time_str: str):
        """检查并发送问候"""
        try:
            # 解析目标时间
            target_hour, target_minute = map(int, time_str.split(":"))
            target_time = current_time.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            
            # 检查是否在时间窗口内（±5分钟）
            time_diff = abs((current_time - target_time).total_seconds())
            if time_diff > 300:  # 5分钟 = 300秒
                return
            
            # 生成今天的问候标识
            today_key = current_time.strftime("%Y-%m-%d")
            greeting_key = f"{today_key}_{greeting_type}"
            
            # 检查今天是否已经发送过这个时间段的问候
            if greeting_key in self.sent_greetings:
                return
            
            # 标记为已发送，避免重复
            self.sent_greetings[greeting_key] = current_time.isoformat()
            
            # 清理旧的记录
            self._cleanup_old_greetings()
            
            # 给所有目标设备发送问候
            for device_id in self.target_devices:
                try:
                    await self.send_weather_greeting_to_device(device_id, greeting_type)
                    await asyncio.sleep(2)  # 设备间隔2秒，避免并发过多
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"向设备 {device_id} 发送问候失败: {e}")
            
            self.logger.bind(tag=TAG).info(f"🌅 完成 {greeting_type} 时段天气问候，共 {len(self.target_devices)} 个设备")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"检查和发送问候失败: {e}")
    
    def _cleanup_old_greetings(self):
        """清理旧的问候记录"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            
            keys_to_remove = [
                key for key in self.sent_greetings.keys()
                if key.split("_")[0] < cutoff_date
            ]
            
            for key in keys_to_remove:
                del self.sent_greetings[key]
                
            if keys_to_remove:
                self.logger.bind(tag=TAG).debug(f"清理了 {len(keys_to_remove)} 条旧问候记录")
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"清理旧问候记录失败: {e}")
    
    async def send_weather_greeting_to_device(self, device_id: str, greeting_type: str = "general") -> str:
        """
        向指定设备发送天气问候
        
        完整流程：
        1. 生成天气问候内容
        2. 通过MQTT发送唤醒命令
        3. 等待设备ACK
        4. 自动生成TTS音频
        5. 通过WebSocket发送音频到设备
        6. 设备播放音频
        """
        try:
            self.logger.bind(tag=TAG).info(f"🌤️ 开始向设备 {device_id} 发送天气问候")
            
            # 1. 生成天气问候内容
            greeting_content = await self.greeting_service.generate_weather_greeting(device_id, greeting_type)
            
            self.logger.bind(tag=TAG).info(f"📝 生成问候内容: {greeting_content[:100]}...")
            
            # 2. 启动完整的回调流程（MQTT -> ACK -> TTS -> WebSocket -> 播放）
            track_id = await self.awaken_service.send_awaken_with_callback(
                device_id=device_id,
                message=greeting_content,
                message_type="weather_greeting"
            )
            
            self.logger.bind(tag=TAG).info(f"🚀 启动天气问候流程成功: {device_id}, track_id: {track_id}")
            
            return track_id
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"❌ 发送天气问候失败: {device_id}, {e}")
            raise
    
    async def send_immediate_weather_greeting(self, device_id: str, greeting_type: str = "general") -> Dict[str, Any]:
        """
        立即发送天气问候（用于手动触发或API调用）
        
        Args:
            device_id: 设备ID
            greeting_type: 问候类型
            
        Returns:
            Dict: 包含track_id和状态信息的字典
        """
        try:
            track_id = await self.send_weather_greeting_to_device(device_id, greeting_type)
            
            return {
                "success": True,
                "track_id": track_id,
                "device_id": device_id,
                "greeting_type": greeting_type,
                "timestamp": datetime.now().isoformat(),
                "message": "天气问候发送成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "device_id": device_id,
                "greeting_type": greeting_type,
                "timestamp": datetime.now().isoformat(),
                "message": "天气问候发送失败"
            }
    
    async def get_weather_info_only(self, device_id: str) -> Dict[str, Any]:
        """仅获取天气信息，不发送问候"""
        try:
            weather_summary = await self.weather_service.get_weather_summary(device_id)
            return {
                "success": True,
                "weather_data": weather_summary,
                "device_id": device_id,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "device_id": device_id,
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_weather_greeting_flow(self, device_id: str) -> Dict[str, Any]:
        """
        测试天气问候完整流程
        用于调试和验证功能
        """
        try:
            self.logger.bind(tag=TAG).info(f"🧪 开始测试天气问候流程: {device_id}")
            
            # 1. 测试天气数据获取
            weather_test = await self.get_weather_info_only(device_id)
            if not weather_test["success"]:
                return {
                    "success": False,
                    "step": "weather_data",
                    "error": weather_test["error"],
                    "message": "天气数据获取失败"
                }
            
            # 2. 测试问候内容生成
            try:
                greeting_content = await self.greeting_service.generate_weather_greeting(device_id, "general")
                self.logger.bind(tag=TAG).info(f"✅ 问候内容生成成功: {greeting_content[:50]}...")
            except Exception as e:
                return {
                    "success": False,
                    "step": "greeting_generation",
                    "error": str(e),
                    "message": "问候内容生成失败"
                }
            
            # 3. 测试MQTT连接
            if not self.mqtt_client or not hasattr(self.mqtt_client, 'connected') or not self.mqtt_client.connected:
                return {
                    "success": False,
                    "step": "mqtt_connection",
                    "error": "MQTT客户端未连接",
                    "message": "MQTT连接检查失败"
                }
            
            # 4. 执行完整流程
            track_id = await self.send_weather_greeting_to_device(device_id, "general")
            
            return {
                "success": True,
                "track_id": track_id,
                "device_id": device_id,
                "greeting_content": greeting_content,
                "weather_data": weather_test["weather_data"],
                "timestamp": datetime.now().isoformat(),
                "message": "天气问候流程测试成功"
            }
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"🚨 测试天气问候流程失败: {e}")
            return {
                "success": False,
                "step": "unknown",
                "error": str(e),
                "device_id": device_id,
                "timestamp": datetime.now().isoformat(),
                "message": "天气问候流程测试失败"
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "service_name": "ProactiveWeatherService",
            "weather_service_available": bool(self.weather_service),
            "mqtt_client_connected": bool(self.mqtt_client and hasattr(self.mqtt_client, 'connected') and self.mqtt_client.connected),
            "tts_provider_available": bool(self.tts_provider),
            "target_devices": self.target_devices,
            "greeting_times": self.greeting_times,
            "sent_greetings_today": len([k for k in self.sent_greetings.keys() if k.startswith(datetime.now().strftime("%Y-%m-%d"))]),
            "timestamp": datetime.now().isoformat()
        }
    
    def update_target_devices(self, devices: List[str]):
        """更新目标设备列表"""
        self.target_devices = devices
        self.logger.bind(tag=TAG).info(f"📱 更新目标设备列表: {devices}")
    
    def update_greeting_times(self, times: Dict[str, str]):
        """更新问候时间配置"""
        self.greeting_times.update(times)
        self.logger.bind(tag=TAG).info(f"⏰ 更新问候时间配置: {self.greeting_times}")


class WeatherGreetingScheduler:
    """天气问候调度器 - 单独的调度组件"""
    
    def __init__(self, weather_service: ProactiveWeatherService):
        self.weather_service = weather_service
        self.logger = setup_logging()
        self.running = False
        
    async def start(self):
        """启动调度器"""
        if self.running:
            return
            
        self.running = True
        self.logger.bind(tag=TAG).info("📅 启动天气问候调度器")
        
        # 启动主动问候服务
        await self.weather_service.start_proactive_weather_service()
    
    async def stop(self):
        """停止调度器"""
        self.running = False
        self.logger.bind(tag=TAG).info("⏹️ 停止天气问候调度器")
    
    async def trigger_immediate_greeting(self, device_id: str, greeting_type: str = "general") -> Dict[str, Any]:
        """立即触发问候"""
        return await self.weather_service.send_immediate_weather_greeting(device_id, greeting_type)


# 为外部API提供的便捷函数
async def create_weather_greeting_service(config: Dict[str, Any], mqtt_client=None, tts_provider=None) -> ProactiveWeatherService:
    """创建天气问候服务实例"""
    return ProactiveWeatherService(config, mqtt_client, tts_provider)


async def send_weather_greeting(device_id: str, greeting_type: str, config: Dict[str, Any], 
                               mqtt_client=None, tts_provider=None) -> Dict[str, Any]:
    """发送天气问候的便捷函数"""
    service = ProactiveWeatherService(config, mqtt_client, tts_provider)
    return await service.send_immediate_weather_greeting(device_id, greeting_type)

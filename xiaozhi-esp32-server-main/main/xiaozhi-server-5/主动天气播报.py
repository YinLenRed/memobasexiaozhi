#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主动天气播报功能
提供Python端主动调用天气播报的接口
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('主动天气播报')

class WeatherNotificationService:
    """天气通知服务"""
    
    def __init__(self):
        self.device_id = "f0:9e:9e:04:8a:44"  # 用户的硬件设备
        
    async def trigger_weather_alert(self, weather_info: str, custom_prompt: str = None):
        """触发天气播报"""
        try:
            logger.info("🌤️ 开始触发主动天气播报")
            
            # 构建Java后端兼容的数据结构
            weather_data = {
                "device_id": self.device_id,
                "topic": "天气预报",
                "data": [
                    {
                        "title": "实时天气播报",
                        "content": weather_info
                    }
                ],
                "prompt": custom_prompt or "请根据天气信息生成简洁明了的播报内容，语调自然友好"
            }
            
            logger.info("📋 构建的天气数据:")
            logger.info(json.dumps(weather_data, indent=2, ensure_ascii=False))
            
            # 直接调用统一事件服务
            from core.services.unified_event_service import get_unified_event_service
            
            event_service = get_unified_event_service()
            if not event_service:
                logger.error("❌ 统一事件服务未初始化")
                return False
            
            # 模拟MQTT消息处理
            await self._simulate_mqtt_event(event_service, weather_data)
            
            logger.info("✅ 天气播报触发完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 天气播报触发失败: {e}")
            return False
    
    async def _simulate_mqtt_event(self, event_service, weather_data):
        """模拟MQTT事件处理"""
        # 模拟MQTT消息对象
        class MockMessage:
            def __init__(self, topic, payload):
                self.topic = topic
                self.payload = payload.encode('utf-8')
        
        # 创建模拟消息
        topic = "xiaozhi/java-to-python/event/weather"
        payload = json.dumps(weather_data)
        mock_message = MockMessage(topic, payload)
        
        # 调用事件处理
        await event_service._handle_event_message(None, None, mock_message)
    
    async def trigger_weather_warning(self, warning_level: str, warning_content: str):
        """触发天气预警"""
        prompt = f"这是{warning_level}级天气预警，请用紧急且清晰的语调播报，提醒用户注意安全"
        weather_info = f"{warning_level}级预警：{warning_content}"
        
        return await self.trigger_weather_alert(weather_info, prompt)
    
    async def trigger_daily_weather(self, city: str, temperature: str, condition: str):
        """触发日常天气播报"""
        prompt = "请用轻松友好的语调播报今日天气，让用户了解出行注意事项"
        weather_info = f"{city}今日天气：{condition}，温度{temperature}，适合外出活动"
        
        return await self.trigger_weather_alert(weather_info, prompt)

# 快速调用函数
async def quick_weather_test():
    """快速天气测试"""
    logger.info("🧪 快速天气播报测试")
    logger.info("="*50)
    
    service = WeatherNotificationService()
    
    # 测试日常天气
    success = await service.trigger_daily_weather(
        city="北京",
        temperature="15-25℃", 
        condition="晴转多云"
    )
    
    if success:
        logger.info("✅ 天气播报测试成功")
        logger.info("💡 预期效果:")
        logger.info("   1. 硬件应该收到语音播报")
        logger.info("   2. 内容由LLM智能生成")
        logger.info("   3. 语调自然友好")
    else:
        logger.error("❌ 天气播报测试失败")
    
    return success

# HTTP API接口
def create_weather_api():
    """创建天气API接口"""
    api_code = '''
# 添加到主服务的API路由中

@app.post("/api/weather/trigger")
async def trigger_weather_notification(request: dict):
    """主动天气播报API"""
    try:
        weather_info = request.get("weather_info", "")
        custom_prompt = request.get("prompt", "")
        device_id = request.get("device_id", "f0:9e:9e:04:8a:44")
        
        if not weather_info:
            return {"error": "缺少天气信息", "code": "MISSING_WEATHER_INFO"}
        
        service = WeatherNotificationService()
        service.device_id = device_id
        
        success = await service.trigger_weather_alert(weather_info, custom_prompt)
        
        if success:
            return {"message": "天气播报触发成功", "code": "SUCCESS"}
        else:
            return {"error": "天气播报触发失败", "code": "TRIGGER_FAILED"}
            
    except Exception as e:
        return {"error": f"API调用失败: {e}", "code": "API_ERROR"}

# 使用示例：
# POST http://47.98.51.180:8003/api/weather/trigger
# {
#   "weather_info": "北京今日晴天，温度18-25度，微风，适合外出",
#   "prompt": "请用友好的语调播报天气",
#   "device_id": "f0:9e:9e:04:8a:44"
# }
'''
    
    logger.info("📝 HTTP API接口代码:")
    logger.info(api_code)
    return api_code

def main():
    """主函数"""
    logger.info("🌤️ 主动天气播报服务")
    logger.info("="*50)
    
    print("\n🎯 使用方法:")
    print("1. 快速测试: python 主动天气播报.py")
    print("2. 导入使用: from 主动天气播报 import WeatherNotificationService")
    print("3. HTTP API: 集成到主服务中")
    
    print("\n📋 调用示例:")
    print("service = WeatherNotificationService()")
    print("await service.trigger_daily_weather('北京', '15-25℃', '晴天')")
    
    print("\n🔧 Java后端集成:")
    print("1. Java定时任务调用Python HTTP API")
    print("2. 或Java直接发送MQTT事件给Python")
    
    # 创建API代码
    create_weather_api()
    
    # 运行快速测试
    try:
        success = asyncio.run(quick_weather_test())
        if success:
            print("\n🎉 测试完成！硬件应该有声音播放")
        else:
            print("\n❌ 测试失败，请检查服务状态")
    except Exception as e:
        logger.error(f"测试运行失败: {e}")

if __name__ == "__main__":
    main()

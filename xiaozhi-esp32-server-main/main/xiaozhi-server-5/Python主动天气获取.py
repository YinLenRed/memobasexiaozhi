#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python主动获取天气并播报
不依赖Java推送，Python自己获取天气数据并播报
"""

import asyncio
import logging
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('主动天气')

# 配置信息
DEVICE_ID = "f0:9e:9e:04:8a:44"
API_BASE = "http://47.98.51.180:8003"

class WeatherService:
    """天气服务类"""
    
    def __init__(self):
        self.api_keys = {
            # 免费天气API密钥（请替换为您的）
            "openweather": "your_openweather_api_key",
            "weatherapi": "your_weatherapi_key",
            "caiyunapp": "your_caiyun_token"
        }
    
    def get_weather_openweather(self, city: str = "Beijing") -> Optional[Dict]:
        """使用OpenWeatherMap获取天气"""
        try:
            # 免费API，无需密钥的简单版本
            url = f"http://wttr.in/{city}?format=j1"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                current = data["current_condition"][0]
                today = data["weather"][0]
                
                return {
                    "city": city,
                    "temperature": current["temp_C"],
                    "condition": current["weatherDesc"][0]["value"],
                    "humidity": current["humidity"],
                    "wind_speed": current["windspeedKmph"],
                    "max_temp": today["maxtempC"],
                    "min_temp": today["mintempC"],
                    "source": "wttr.in"
                }
        except Exception as e:
            logger.error(f"OpenWeather API失败: {e}")
            return None
    
    def get_weather_backup(self, city: str = "北京") -> Dict:
        """备用天气数据（模拟数据）"""
        from random import randint
        
        conditions = ["晴天", "多云", "阴天", "小雨", "晴转多云"]
        
        return {
            "city": city,
            "temperature": randint(15, 30),
            "condition": conditions[randint(0, len(conditions)-1)],
            "humidity": randint(40, 80),
            "wind_speed": randint(5, 15),
            "max_temp": randint(20, 35),
            "min_temp": randint(10, 20),
            "source": "模拟数据"
        }
    
    def format_weather_content(self, weather_data: Dict) -> str:
        """格式化天气播报内容"""
        city = weather_data.get("city", "当地")
        temp = weather_data.get("temperature", "未知")
        condition = weather_data.get("condition", "未知")
        max_temp = weather_data.get("max_temp", "")
        min_temp = weather_data.get("min_temp", "")
        wind = weather_data.get("wind_speed", "")
        humidity = weather_data.get("humidity", "")
        
        # 生成详细的天气播报内容
        content = f"{city}今天{condition}，当前温度{temp}度"
        
        if max_temp and min_temp:
            content += f"，最高{max_temp}度，最低{min_temp}度"
        
        if wind:
            if int(wind) < 10:
                content += "，微风"
            elif int(wind) < 20:
                content += f"，风速{wind}公里每小时"
            else:
                content += f"，大风{wind}公里每小时，注意防范"
        
        if humidity:
            if int(humidity) > 80:
                content += "，湿度较高"
            elif int(humidity) < 30:
                content += "，空气干燥"
        
        # 添加出行建议
        if condition in ["晴天", "多云"]:
            content += "，适合外出活动"
        elif "雨" in condition:
            content += "，出行请带雨具"
        elif condition == "阴天":
            content += "，可适当添加衣物"
        
        return content

class WeatherBroadcaster:
    """天气播报器"""
    
    def __init__(self):
        self.weather_service = WeatherService()
    
    async def broadcast_weather(self, city: str = "北京", voice_style: str = "友好"):
        """播报天气"""
        logger.info(f"🌤️ 开始获取{city}天气信息...")
        
        # 1. 获取天气数据
        weather_data = self.weather_service.get_weather_openweather(city)
        if not weather_data:
            logger.warning("🔄 主要天气API失败，使用备用数据")
            weather_data = self.weather_service.get_weather_backup(city)
        
        logger.info(f"✅ 天气数据获取成功: {weather_data['source']}")
        
        # 2. 格式化播报内容
        weather_content = self.weather_service.format_weather_content(weather_data)
        logger.info(f"📄 播报内容: {weather_content}")
        
        # 3. 生成播报提示
        prompts = {
            "友好": "请用友好温暖的语调播报天气，让听众感到温馨",
            "专业": "请用专业准确的语调播报天气信息",
            "轻松": "请用轻松愉快的语调播报天气，营造愉悦氛围",
            "简洁": "请用简洁明了的语调快速播报天气要点"
        }
        
        custom_prompt = prompts.get(voice_style, prompts["友好"])
        
        # 4. 发送播报请求
        success = await self.send_weather_broadcast(weather_content, custom_prompt)
        
        if success:
            logger.info("🎉 天气播报发送成功！")
            return weather_data
        else:
            logger.error("❌ 天气播报发送失败")
            return None
    
    async def send_weather_broadcast(self, content: str, prompt: str) -> bool:
        """发送天气播报"""
        try:
            payload = {
                "device_id": DEVICE_ID,
                "category": "weather",
                "initial_content": content,
                "user_info": {
                    "custom_prompt": prompt,
                    "source": "python_auto_weather"
                }
            }
            
            # 使用更长的超时时间
            response = requests.post(
                f"{API_BASE}/xiaozhi/greeting/send",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                track_id = result.get("track_id")
                logger.info(f"✅ 播报发送成功，跟踪ID: {track_id}")
                return True
            else:
                logger.error(f"❌ 播报发送失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 播报发送异常: {e}")
            return False
    
    async def scheduled_weather_broadcast(self, interval_minutes: int = 60):
        """定时天气播报"""
        logger.info(f"⏰ 启动定时天气播报，间隔{interval_minutes}分钟")
        
        while True:
            try:
                current_time = datetime.now()
                logger.info(f"🕐 {current_time.strftime('%H:%M')} - 执行定时天气播报")
                
                await self.broadcast_weather()
                
                # 等待指定间隔
                await asyncio.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("⏹️ 定时播报已停止")
                break
            except Exception as e:
                logger.error(f"❌ 定时播报异常: {e}")
                await asyncio.sleep(60)  # 出错时等待1分钟后重试

def create_weather_commands():
    """创建天气命令快捷方式"""
    commands = {
        "current": "获取当前天气",
        "beijing": "获取北京天气", 
        "shanghai": "获取上海天气",
        "guangzhou": "获取广州天气",
        "shenzhen": "获取深圳天气"
    }
    
    return commands

async def interactive_weather():
    """交互式天气播报"""
    broadcaster = WeatherBroadcaster()
    
    print("🌤️ Python主动天气播报工具")
    print("="*40)
    print("1. 立即播报天气")
    print("2. 指定城市播报")
    print("3. 定时天气播报")
    print("4. 退出")
    
    while True:
        try:
            choice = input("\n请选择功能 (1-4): ").strip()
            
            if choice == "1":
                print("\n🌞 播报当前天气...")
                await broadcaster.broadcast_weather()
                
            elif choice == "2":
                city = input("请输入城市名称: ").strip()
                if city:
                    style = input("语调选择 (友好/专业/轻松/简洁，默认:友好): ").strip() or "友好"
                    print(f"\n🌍 播报{city}天气...")
                    await broadcaster.broadcast_weather(city, style)
                else:
                    print("❌ 城市名称不能为空")
                    
            elif choice == "3":
                try:
                    interval = int(input("请输入播报间隔(分钟，默认60): ").strip() or "60")
                    print(f"\n⏰ 启动定时天气播报，每{interval}分钟播报一次...")
                    print("按 Ctrl+C 停止定时播报")
                    await broadcaster.scheduled_weather_broadcast(interval)
                except ValueError:
                    print("❌ 请输入有效的数字")
                    
            elif choice == "4":
                print("👋 退出天气播报工具")
                break
                
            else:
                print("❌ 无效选择，请输入 1-4")
                
        except KeyboardInterrupt:
            print("\n👋 退出天气播报工具")
            break
        except Exception as e:
            print(f"❌ 操作失败: {e}")

async def quick_weather_test():
    """快速天气测试"""
    logger.info("🧪 快速天气播报测试")
    
    broadcaster = WeatherBroadcaster()
    result = await broadcaster.broadcast_weather("北京", "友好")
    
    if result:
        logger.info("✅ 天气播报测试成功！")
        logger.info("💡 硬件应该播放了天气语音")
    else:
        logger.error("❌ 天气播报测试失败")

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "test":
            asyncio.run(quick_weather_test())
        elif arg == "beijing":
            asyncio.run(WeatherBroadcaster().broadcast_weather("北京"))
        elif arg == "auto":
            asyncio.run(WeatherBroadcaster().scheduled_weather_broadcast(30))  # 30分钟间隔
        else:
            print("用法: python Python主动天气获取.py [test|beijing|auto]")
            print("或者直接运行进入交互模式")
    else:
        asyncio.run(interactive_weather())

if __name__ == "__main__":
    main()


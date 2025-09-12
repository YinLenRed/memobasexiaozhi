#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立即获取天气并播报 - 简化版
"""

import requests
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('天气获取')

DEVICE_ID = "f0:9e:9e:04:8a:44"
API_BASE = "http://47.98.51.180:8003"

def get_weather_simple(city="北京"):
    """获取简单天气数据"""
    try:
        # 使用免费的天气API
        url = f"http://wttr.in/{city}?format=%l:+%c+%t+%h+%w"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            weather_text = response.text.strip()
            logger.info(f"✅ 获取到天气: {weather_text}")
            return weather_text
        else:
            logger.warning("天气API失败，使用模拟数据")
            return f"{city}: ☀️ 20°C 湿度60% 微风"
            
    except Exception as e:
        logger.error(f"天气获取失败: {e}")
        # 生成模拟天气数据
        temp = 20 + (datetime.now().hour % 10)
        return f"{city}今天晴天，温度{temp}度，微风，适合外出"

def format_weather_content(weather_raw, city="北京"):
    """格式化天气内容"""
    current_time = datetime.now().strftime("%H点%M分")
    
    # 简单处理天气数据
    if "°C" in weather_raw:
        # 从API返回的数据中提取信息
        content = f"{city}天气播报，现在{current_time}，{weather_raw}"
    else:
        # 使用模拟数据
        content = f"{city}天气播报，现在{current_time}，{weather_raw}"
    
    return content

def broadcast_weather_now(city="北京"):
    """立即播报天气"""
    logger.info(f"🌤️ 开始获取{city}天气...")
    
    # 1. 获取天气
    weather_raw = get_weather_simple(city)
    
    # 2. 格式化内容
    weather_content = format_weather_content(weather_raw, city)
    logger.info(f"📄 播报内容: {weather_content}")
    
    # 3. 发送播报
    try:
        payload = {
            "device_id": DEVICE_ID,
            "category": "weather",
            "initial_content": weather_content
        }
        
        logger.info("🚀 发送天气播报...")
        response = requests.post(
            f"{API_BASE}/xiaozhi/greeting/send",
            json=payload,
            timeout=25
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info("✅ 天气播报发送成功！")
            logger.info(f"📊 跟踪ID: {result['track_id']}")
            logger.info("💡 硬件应该马上播放天气语音")
            return True
        else:
            logger.error(f"❌ 播报失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 播报异常: {e}")
        return False

def main():
    """主函数"""
    import sys
    
    city = "北京"
    if len(sys.argv) > 1:
        city = sys.argv[1]
    
    logger.info("🌤️ Python主动天气播报")
    logger.info("="*30)
    
    success = broadcast_weather_now(city)
    
    if success:
        print(f"🎉 {city}天气播报成功！")
        print("💡 请检查硬件是否播放了语音")
    else:
        print(f"❌ {city}天气播报失败")
        print("💡 请检查网络和服务状态")

if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python主动触发天气播报
简单直接的天气播报触发脚本
"""

import requests
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('天气播报')

# 配置信息
PYTHON_API_BASE = "http://47.98.51.180:8003"
DEVICE_ID = "f0:9e:9e:04:8a:44"

def trigger_weather_alert(weather_info: str, prompt: str = None):
    """触发天气播报"""
    try:
        logger.info("🌤️ 开始触发天气播报")
        
        # 使用正确的主动问候API
        url = f"{PYTHON_API_BASE}/xiaozhi/greeting/send"
        
        payload = {
            "device_id": DEVICE_ID,
            "category": "weather",  # 使用weather类别
            "initial_content": weather_info,
            "user_info": {
                "custom_prompt": prompt or "请用友好自然的语调播报天气信息，提醒用户注意事项"
            }
        }
        
        logger.info(f"📋 发送请求到: {url}")
        logger.info(f"📄 请求数据: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        response = requests.post(url, json=payload, timeout=30)  # 增加超时时间
        
        if response.status_code == 200:
            result = response.json()
            logger.info("✅ 天气播报触发成功")
            logger.info(f"📊 响应: {result}")
            return True
        else:
            logger.error(f"❌ API调用失败: {response.status_code}")
            logger.error(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 天气播报触发失败: {e}")
        return False

def trigger_daily_weather():
    """触发日常天气播报"""
    weather_info = "北京今天晴天，温度18-25度，微风，空气质量良好，适合外出活动"
    prompt = "请用轻松友好的语调播报今日天气，让用户了解出行注意事项"
    
    return trigger_weather_alert(weather_info, prompt)

def trigger_weather_warning():
    """触发天气预警"""
    weather_info = "北京发布大风蓝色预警，阵风可达6-7级，请注意防范，避免户外活动"
    prompt = "这是天气预警信息，请用清晰严肃的语调播报，提醒用户注意安全"
    
    return trigger_weather_alert(weather_info, prompt)

def trigger_custom_weather(weather_content: str, voice_style: str = "友好"):
    """自定义天气播报"""
    prompts = {
        "友好": "请用友好温暖的语调播报天气",
        "严肃": "请用严肃认真的语调播报天气",  
        "轻松": "请用轻松愉快的语调播报天气",
        "紧急": "这是紧急天气信息，请用紧急清晰的语调播报"
    }
    
    prompt = prompts.get(voice_style, prompts["友好"])
    return trigger_weather_alert(weather_content, prompt)

def main():
    """主函数 - 提供交互式选择"""
    print("🌤️ Python主动天气播报工具")
    print("="*40)
    print("1. 日常天气播报")
    print("2. 天气预警播报") 
    print("3. 自定义天气播报")
    print("4. 退出")
    
    while True:
        try:
            choice = input("\n请选择功能 (1-4): ").strip()
            
            if choice == "1":
                print("\n🌞 触发日常天气播报...")
                success = trigger_daily_weather()
                if success:
                    print("✅ 日常天气播报已发送！硬件应该会播放语音")
                else:
                    print("❌ 播报失败，请检查服务状态")
                    
            elif choice == "2":
                print("\n⚠️ 触发天气预警播报...")
                success = trigger_weather_warning()
                if success:
                    print("✅ 天气预警播报已发送！硬件应该会播放语音")
                else:
                    print("❌ 播报失败，请检查服务状态")
                    
            elif choice == "3":
                weather_content = input("请输入天气内容: ").strip()
                if weather_content:
                    print("语调选择: 友好/严肃/轻松/紧急")
                    voice_style = input("请选择语调 (默认:友好): ").strip() or "友好"
                    
                    print(f"\n🎤 触发自定义天气播报 ({voice_style})...")
                    success = trigger_custom_weather(weather_content, voice_style)
                    if success:
                        print("✅ 自定义天气播报已发送！硬件应该会播放语音")
                    else:
                        print("❌ 播报失败，请检查服务状态")
                else:
                    print("❌ 天气内容不能为空")
                    
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

# 快速调用函数
def quick_test():
    """快速测试"""
    print("🧪 快速测试天气播报...")
    success = trigger_daily_weather()
    if success:
        print("✅ 测试成功！硬件应该有声音")
    else:
        print("❌ 测试失败！请检查服务")
    return success

if __name__ == "__main__":
    import sys
    
    # 支持命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            quick_test()
        elif sys.argv[1] == "daily":
            trigger_daily_weather()
        elif sys.argv[1] == "warning":
            trigger_weather_warning()
        else:
            print("用法: python 触发天气播报.py [test|daily|warning]")
    else:
        main()

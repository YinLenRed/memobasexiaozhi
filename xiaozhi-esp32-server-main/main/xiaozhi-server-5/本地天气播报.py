#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地天气播报
直接调用Python服务内部API，避免HTTP超时问题
"""

import asyncio
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('本地天气播报')

# 设备ID
DEVICE_ID = "f0:9e:9e:04:8a:44"

async def trigger_weather_local(weather_content: str, voice_style: str = "友好"):
    """本地触发天气播报"""
    try:
        logger.info("🌤️ 开始本地天气播报")
        logger.info(f"📋 天气内容: {weather_content}")
        logger.info(f"🎤 语调风格: {voice_style}")
        
        # 导入MQTT管理器
        from core.mqtt.mqtt_manager import MQTTManager
        from config.config_loader import load_config
        
        # 加载配置
        config = load_config()
        
        # 获取或创建MQTT管理器实例
        mqtt_manager = MQTTManager.get_instance()
        if not mqtt_manager:
            logger.error("❌ MQTT管理器未初始化")
            return False
        
        if not mqtt_manager.is_connected():
            logger.error("❌ MQTT未连接")
            return False
        
        # 准备prompt
        prompts = {
            "友好": "请用友好温暖的语调播报天气",
            "严肃": "请用严肃认真的语调播报天气",  
            "轻松": "请用轻松愉快的语调播报天气",
            "紧急": "这是紧急天气信息，请用紧急清晰的语调播报"
        }
        
        prompt = prompts.get(voice_style, prompts["友好"])
        
        # 构建用户信息
        user_info = {
            "custom_prompt": prompt,
            "trigger_source": "python_local",
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"🚀 发送天气播报到设备: {DEVICE_ID}")
        
        # 直接调用MQTT管理器的发送方法
        track_id = await mqtt_manager.send_proactive_greeting(
            device_id=DEVICE_ID,
            initial_content=weather_content,
            category="weather",
            user_info=user_info
        )
        
        logger.info(f"✅ 天气播报发送成功!")
        logger.info(f"📊 跟踪ID: {track_id}")
        logger.info(f"🎯 目标设备: {DEVICE_ID}")
        logger.info("💡 硬件应该马上播放天气语音!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 本地天气播报失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

async def daily_weather():
    """日常天气播报"""
    weather_content = "北京今天晴天，温度18-25度，微风，空气质量良好，适合外出活动"
    return await trigger_weather_local(weather_content, "友好")

async def weather_warning():
    """天气预警播报"""
    weather_content = "北京发布大风蓝色预警，阵风可达6-7级，请注意防范，避免户外活动"
    return await trigger_weather_local(weather_content, "紧急")

async def simple_weather():
    """简单天气测试"""
    weather_content = "测试天气播报：现在天气晴朗，温度20度，适合外出"
    return await trigger_weather_local(weather_content, "轻松")

async def interactive_weather():
    """交互式天气播报"""
    print("🌤️ Python本地天气播报工具")
    print("="*40)
    print("1. 日常天气播报")
    print("2. 天气预警播报") 
    print("3. 简单天气测试")
    print("4. 自定义天气播报")
    print("5. 退出")
    
    while True:
        try:
            choice = input("\n请选择功能 (1-5): ").strip()
            
            if choice == "1":
                print("\n🌞 触发日常天气播报...")
                success = await daily_weather()
                if success:
                    print("✅ 日常天气播报已发送！硬件应该会播放语音")
                else:
                    print("❌ 播报失败，请检查服务状态")
                    
            elif choice == "2":
                print("\n⚠️ 触发天气预警播报...")
                success = await weather_warning()
                if success:
                    print("✅ 天气预警播报已发送！硬件应该会播放语音")
                else:
                    print("❌ 播报失败，请检查服务状态")
                    
            elif choice == "3":
                print("\n🧪 触发简单天气测试...")
                success = await simple_weather()
                if success:
                    print("✅ 简单天气播报已发送！硬件应该会播放语音")
                else:
                    print("❌ 播报失败，请检查服务状态")
                    
            elif choice == "4":
                weather_content = input("请输入天气内容: ").strip()
                if weather_content:
                    print("语调选择: 友好/严肃/轻松/紧急")
                    voice_style = input("请选择语调 (默认:友好): ").strip() or "友好"
                    
                    print(f"\n🎤 触发自定义天气播报 ({voice_style})...")
                    success = await trigger_weather_local(weather_content, voice_style)
                    if success:
                        print("✅ 自定义天气播报已发送！硬件应该会播放语音")
                    else:
                        print("❌ 播报失败，请检查服务状态")
                else:
                    print("❌ 天气内容不能为空")
                    
            elif choice == "5":
                print("👋 退出天气播报工具")
                break
                
            else:
                print("❌ 无效选择，请输入 1-5")
                
        except KeyboardInterrupt:
            print("\n👋 退出天气播报工具")
            break
        except Exception as e:
            print(f"❌ 操作失败: {e}")

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "test":
            print("🧪 快速测试本地天气播报...")
            success = asyncio.run(simple_weather())
            if success:
                print("✅ 测试成功！硬件应该有声音")
            else:
                print("❌ 测试失败！请检查服务")
        elif arg == "daily":
            asyncio.run(daily_weather())
        elif arg == "warning":
            asyncio.run(weather_warning())
        else:
            print("用法: python 本地天气播报.py [test|daily|warning]")
            print("或者直接运行进入交互模式")
    else:
        asyncio.run(interactive_weather())

if __name__ == "__main__":
    main()

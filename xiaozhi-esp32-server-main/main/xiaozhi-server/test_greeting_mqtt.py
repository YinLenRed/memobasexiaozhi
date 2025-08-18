#!/usr/bin/env python3
"""
MQTT主动问候验证脚本
在CentOS服务器上验证主动问候功能
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime


class MQTTGreetingTester:
    """MQTT主动问候测试器"""
    
    def __init__(self, server_url="http://localhost:8003"):
        self.server_url = server_url
        
    async def check_server_status(self):
        """检查服务器状态"""
        print("🔍 检查服务器状态...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/xiaozhi/greeting/status", timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        print("✅ 服务器状态正常")
                        print(f"   响应: {result}")
                        return True
                    else:
                        print(f"⚠️ 服务器响应异常: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ 服务器连接失败: {e}")
            return False
    
    async def send_test_greeting(self, device_id, category="system_reminder", content=None):
        """发送测试问候"""
        if not content:
            content = f"这是一个测试问候消息，时间：{datetime.now().strftime('%H:%M:%S')}"
        
        print(f"\n📤 发送测试问候到设备: {device_id}")
        print(f"   内容: {content}")
        print(f"   类别: {category}")
        
        data = {
            "device_id": device_id,
            "initial_content": content,
            "category": category,
            "user_info": {
                "name": "测试用户",
                "age": 70,
                "location": "测试环境"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.server_url}/xiaozhi/greeting/send",
                    json=data,
                    timeout=30
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        print("✅ 问候发送成功")
                        print(f"   Track ID: {result.get('track_id')}")
                        print(f"   时间戳: {result.get('timestamp')}")
                        return result
                    else:
                        print(f"❌ 问候发送失败: {result}")
                        return None
                        
        except Exception as e:
            print(f"❌ 发送请求失败: {e}")
            return None
    
    async def test_different_categories(self, device_id):
        """测试不同类别的问候"""
        test_cases = [
            {
                "category": "system_reminder",
                "content": "测试系统提醒：该吃药了"
            },
            {
                "category": "weather", 
                "content": "测试天气问候：今天天气很好"
            },
            {
                "category": "news",
                "content": "测试新闻播报：为您播报今日要闻"
            },
            {
                "category": "music",
                "content": "测试音乐推荐：为您推荐轻松音乐"
            }
        ]
        
        print(f"\n🎯 开始测试不同类别问候，设备: {device_id}")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- 测试 {i}/{len(test_cases)} ---")
            result = await self.send_test_greeting(
                device_id=device_id,
                category=test_case["category"],
                content=test_case["content"]
            )
            
            if result:
                print(f"⏳ 等待5秒后继续下一个测试...")
                await asyncio.sleep(5)
            else:
                print("❌ 测试失败，跳过后续测试")
                break
    
    async def monitor_mqtt_flow(self, device_id):
        """模拟监控MQTT消息流"""
        print(f"\n📡 MQTT消息流监控指南")
        print("=" * 50)
        print("在另一个终端窗口运行以下命令来监控MQTT消息：")
        print()
        print("# 监控设备命令")
        print(f"mosquitto_sub -h 47.98.51.180 -t 'device/{device_id}/cmd'")
        print()
        print("# 监控设备应答") 
        print(f"mosquitto_sub -h 47.98.51.180 -t 'device/{device_id}/ack'")
        print()
        print("# 监控设备事件")
        print(f"mosquitto_sub -h 47.98.51.180 -t 'device/{device_id}/event'")
        print()
        print("# 监控所有设备（通配符）")
        print("mosquitto_sub -h 47.98.51.180 -t 'device/+/cmd'")
        print("mosquitto_sub -h 47.98.51.180 -t 'device/+/ack'") 
        print("mosquitto_sub -h 47.98.51.180 -t 'device/+/event'")
        print("=" * 50)
    
    def print_expected_mqtt_flow(self):
        """打印期望的MQTT消息流程"""
        print("\n🔄 预期的MQTT消息流程")
        print("=" * 50)
        print("1. 📤 Python发送命令:")
        print("   主题: device/{device_id}/cmd")
        print("   消息: {\"cmd\":\"SPEAK\",\"text\":\"...\",\"track_id\":\"...\"}")
        print()
        print("2. 📥 设备回复确认:")
        print("   主题: device/{device_id}/ack") 
        print("   消息: {\"ack\":\"received\",\"track_id\":\"...\"}")
        print()
        print("3. 🎵 Python发送音频（HTTP）")
        print()
        print("4. 📢 设备播放完成事件:")
        print("   主题: device/{device_id}/event")
        print("   消息: {\"evt\":\"EVT_SPEAK_DONE\",\"track_id\":\"...\",\"timestamp\":\"...\"}")
        print("=" * 50)


async def main():
    """主测试函数"""
    print("🎯 MQTT主动问候功能验证")
    print("=" * 60)
    
    # 可以根据实际情况修改服务器地址
    server_url = "http://localhost:8003"  # 本机测试
    # server_url = "http://your-server-ip:8003"  # 远程服务器
    
    tester = MQTTGreetingTester(server_url)
    
    # 1. 检查服务器状态
    if not await tester.check_server_status():
        print("❌ 服务器状态检查失败，请确认服务是否正常运行")
        return
    
    # 2. 打印MQTT监控指南
    device_id = "ESP32_TEST_001"  # 测试设备ID
    await tester.monitor_mqtt_flow(device_id)
    
    # 3. 打印预期流程
    tester.print_expected_mqtt_flow()
    
    # 4. 等待用户准备
    print(f"\n⏰ 准备发送测试消息到设备: {device_id}")
    print("请在另一个终端启动MQTT监控，然后按回车继续...")
    input()
    
    # 5. 发送单个测试
    print("\n🧪 发送单个测试问候...")
    result = await tester.send_test_greeting(device_id)
    
    if result:
        print("\n⏳ 请检查MQTT监控终端是否收到消息")
        print("如果看到消息，说明MQTT通信正常")
        
        # 询问是否继续更多测试
        print("\n是否要测试更多类别的问候？(y/n): ", end="")
        choice = input().strip().lower()
        
        if choice == 'y':
            await tester.test_different_categories(device_id)
    
    print("\n🎉 验证完成！")
    print("\n💡 验证总结：")
    print("1. ✅ HTTP API响应正常")
    print("2. 🔍 请检查MQTT监控是否收到消息") 
    print("3. 📱 如果有真实ESP32设备，检查是否收到语音")
    print("4. 📊 查看服务器日志确认详细流程")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")

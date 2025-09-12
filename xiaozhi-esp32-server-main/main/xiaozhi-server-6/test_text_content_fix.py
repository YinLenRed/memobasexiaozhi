#!/usr/bin/env python3
"""
测试主动问候文本内容修复
"""

import asyncio
import requests
import json
from datetime import datetime

def test_proactive_greeting_with_text():
    """测试主动问候显示正确的文本内容"""
    print("=== 测试主动问候文本内容修复 ===")
    
    # 测试设备列表
    test_devices = [
        "f0:9e:9e:04:8a:44",
        "7c:2c:67:8d:89:78"
    ]
    
    base_url = "http://localhost:5000"
    
    for device_id in test_devices:
        print(f"\n🔥 测试设备: {device_id}")
        
        # 构建测试消息
        test_message = f"文本内容修复测试：硬件应显示此消息而不是模板字符串！时间：{datetime.now().strftime('%H:%M:%S')}"
        
        payload = {
            "device_id": device_id,
            "category": "system_reminder", 
            "content": test_message
        }
        
        print(f"📤 发送内容: {test_message}")
        
        try:
            # 发送主动问候请求
            response = requests.post(
                f"{base_url}/api/greeting/proactive",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                track_id = result.get("track_id", "UNKNOWN")
                print(f"✅ 主动问候发送成功: {track_id}")
                print(f"🎯 期望硬件显示: {test_message}")
                print(f"❌ 不应显示: 主动问候播放 - {track_id}")
            else:
                print(f"❌ 发送失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ 发送异常: {e}")
        
        # 等待一下再测试下一个设备
        print("⏰ 等待8秒...")
        import time
        time.sleep(8)
    
    print("\n✨ 测试完成！请观察硬件屏幕显示：")
    print("✅ 正确：显示实际的问候内容")
    print("❌ 错误：显示'主动问候播放-WX.....'")

if __name__ == "__main__":
    test_proactive_greeting_with_text()

#!/usr/bin/env python3
"""
🌐 API远程调用测试工具
从任何地方测试API调用，验证硬件音频播放流程
"""

import requests
import json
import time
import sys

def test_api_call(device_id, content="现在该吃药了，记得按时服药哦！"):
    """测试API调用"""
    
    print("🌐 远程API调用测试")
    print("=" * 50)
    print(f"📱 设备ID: {device_id}")
    print(f"📝 测试内容: {content}")
    print()
    
    # API配置
    api_url = "http://172.20.12.204:8003/xiaozhi/greeting/send"
    
    # 请求数据
    payload = {
        "device_id": device_id,
        "initial_content": content,
        "category": "system_reminder"
    }
    
    try:
        print("🚀 发送API请求...")
        start_time = time.time()
        
        response = requests.post(
            api_url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10
        )
        
        end_time = time.time()
        duration = (end_time - start_time) * 1000
        
        print(f"⏱️  请求耗时: {duration:.1f}ms")
        print(f"📊 HTTP状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API调用成功!")
            print(f"📋 Track ID: {result.get('track_id', 'N/A')}")
            print(f"📱 设备ID: {result.get('device_id', 'N/A')}")
            
            if result.get('success'):
                print()
                print("🎯 硬件应该:")
                print("1. ✅ 收到MQTT SPEAK命令")
                print("2. ✅ 连接WebSocket音频服务")
                print("3. ✅ 播放健康提醒音频")
                print()
                print("💡 在Linux服务器上查看日志验证:")
                print(f"   grep -A10 -B5 '{result.get('track_id')}' ./logs/app_unified.log")
                
                return True, result.get('track_id')
            else:
                print("❌ API返回失败")
                print(f"📄 响应: {result}")
                return False, None
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"📄 响应: {response.text}")
            return False, None
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False, None
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败 - 请检查网络或API服务状态")
        return False, None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False, None

def main():
    if len(sys.argv) != 2:
        print("用法: python test_api_from_anywhere.py <device_id>")
        print("示例: python test_api_from_anywhere.py 7c:2c:67:8d:89:78")
        sys.exit(1)
    
    device_id = sys.argv[1]
    
    print(f"🎯 开始测试设备: {device_id}")
    print()
    
    # 测试1: 基础健康提醒
    success1, track_id1 = test_api_call(device_id, "现在该吃药了，记得按时服药哦！")
    
    time.sleep(2)
    
    # 测试2: 短提醒
    success2, track_id2 = test_api_call(device_id, "今天吃药了吗？")
    
    print()
    print("📊 测试总结")
    print("=" * 50)
    print(f"✅ 测试1 (长提醒): {'成功' if success1 else '失败'}")
    print(f"✅ 测试2 (短提醒): {'成功' if success2 else '失败'}")
    
    if success1 or success2:
        print()
        print("🎉 API调用成功！硬件应该收到音频播放命令")
        print("💡 如果硬件没有播放音频，请检查:")
        print("   1. 硬件MQTT连接状态")
        print("   2. 硬件WebSocket连接")
        print("   3. Linux服务器日志")
    else:
        print()
        print("❌ 所有测试失败，请检查网络连接和API服务状态")

if __name__ == "__main__":
    main()

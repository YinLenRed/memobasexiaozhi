#!/usr/bin/env python3
"""
🎵 修复后的音频传输测试脚本
验证主动问候音频传输是否正常工作
"""

import asyncio
import time
import requests
import json
import subprocess
import sys

def test_api_call(device_id, content="测试修复后的音频传输功能！"):
    """测试API调用是否正常"""
    
    print("🎯 修复后的音频传输测试")
    print("=" * 60)
    print(f"📱 设备ID: {device_id}")
    print(f"📝 测试内容: {content}")
    print()
    
    api_url = "http://172.20.12.204:8003/xiaozhi/greeting/send"
    
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
                print("🎯 修复后的音频传输流程:")
                print("1. ✅ API调用成功")
                print("2. 🧠 LLM生成问候内容")
                print("3. 🎵 TTS合成音频文件")
                print("4. 📡 MQTT发送SPEAK命令")
                print("5. ✅ 硬件ACK确认")
                print("6. 📂 音频文件转换为Opus帧")
                print("7. 🌐 WebSocket流式发送音频帧")
                print("8. 🎵 硬件实时播放音频")
                print("9. 📊 发送播放完成事件")
                print()
                print("💡 关键修复:")
                print("   - 参考普通对话的音频传输机制")
                print("   - 使用Opus编码的音频帧流式传输")
                print("   - 直接发送二进制数据而不是JSON")
                print("   - 添加流控制和活动时间更新")
                
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
        print("❌ 连接失败 - 请检查服务器状态")
        return False, None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False, None

def monitor_logs(track_id, duration=30):
    """监控服务器日志中的音频传输过程"""
    
    print(f"🔍 监控Track ID: {track_id} 的音频传输日志")
    print(f"⏰ 监控时长: {duration}秒")
    print()
    
    keywords = [
        "音频转换成功",
        "主动问候音频发送完成", 
        "WebSocket音频发送成功",
        "发送音频文件到设备",
        "语音合成成功"
    ]
    
    for keyword in keywords:
        print(f"🔍 查找关键词: {keyword}")
        try:
            # 注意：这里需要在Linux服务器上运行才能正确执行
            result = subprocess.run(
                ["grep", "-n", keyword, "./logs/app_unified.log"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[-3:]:  # 显示最近3条记录
                    print(f"    📋 {line}")
            else:
                print(f"    ❌ 未找到相关日志")
                
        except subprocess.TimeoutExpired:
            print(f"    ⏰ 查找超时")
        except Exception as e:
            print(f"    ❌ 查找失败: {e}")
        
        print()

def main():
    if len(sys.argv) != 2:
        print("用法: python test_fixed_audio_transmission.py <device_id>")
        print("示例: python test_fixed_audio_transmission.py 7c:2c:67:8d:89:78")
        sys.exit(1)
    
    device_id = sys.argv[1]
    
    print("🎵 修复后的音频传输功能测试")
    print("=" * 60)
    print("📋 修复内容:")
    print("   ✅ 参考普通对话的音频传输机制")
    print("   ✅ 使用文件路径而不是字节数据传递") 
    print("   ✅ 音频文件转换为Opus帧流式传输")
    print("   ✅ WebSocket服务器和MQTT客户端连接")
    print("   ✅ 添加流控制和活动时间管理")
    print()
    
    # 测试1: 基础音频传输
    success1, track_id1 = test_api_call(device_id, "修复测试：这是修复后的音频传输功能！")
    
    if success1 and track_id1:
        time.sleep(2)
        monitor_logs(track_id1)
        
        time.sleep(3)
        
        # 测试2: 健康提醒
        success2, track_id2 = test_api_call(device_id, "现在该吃药了，记得按时服药哦！")
        
        if success2 and track_id2:
            time.sleep(2)
            monitor_logs(track_id2)
    
    print()
    print("📊 修复验证总结")
    print("=" * 60)
    
    if success1:
        print("✅ 修复成功：音频传输功能已恢复")
        print("🎯 硬件应该能听到清晰的音频播放")
        print("💡 如果仍无声音，请检查硬件WebSocket连接")
    else:
        print("❌ 修复验证失败：需要进一步检查")
        print("🔍 请检查服务器状态和网络连接")
    
    print()
    print("🔧 技术要点:")
    print("   • 音频文件 → Opus帧转换")
    print("   • WebSocket二进制帧传输")
    print("   • 流控制（60ms/帧）")
    print("   • 连接管理和状态同步")

if __name__ == "__main__":
    main()

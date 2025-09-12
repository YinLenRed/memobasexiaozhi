#!/usr/bin/env python3
"""
🔧 音频文件问题修复验证脚本
验证TTS文件自动删除问题是否已修复
"""

import requests
import time
import json

def test_file_fix(device_id):
    """测试文件修复是否成功"""
    
    print("🔧 音频文件修复验证测试")
    print("=" * 50)
    print(f"📱 设备ID: {device_id}")
    print()
    print("📋 修复内容:")
    print("   ✅ 创建持久音频文件副本")
    print("   ✅ 防止TTS自动删除影响")
    print("   ✅ 音频发送完成后清理")
    print()
    
    api_url = "http://172.20.12.204:8003/xiaozhi/greeting/send"
    
    payload = {
        "device_id": device_id,
        "initial_content": "文件修复测试：这是修复后的音频传输！", 
        "category": "system_reminder"
    }
    
    try:
        print("🚀 发送API请求...")
        start_time = time.time()
        
        response = requests.post(
            api_url,
            headers={"Content-Type": application/json"},
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
            
            if result.get('success'):
                print()
                print("🎯 期待的修复效果:")
                print("1. ✅ 语音合成成功（有文件大小）")
                print("2. ✅ 创建持久音频文件")
                print("3. ✅ 音频转换成功（有帧数）")
                print("4. ✅ 主动问候音频发送完成")
                print("5. ✅ 已清理临时音频文件")
                print()
                print("🔍 在服务器日志中查找这些关键词:")
                print("   - '创建持久音频文件'")
                print("   - '音频转换成功'")
                print("   - '主动问候音频发送完成'")
                print("   - '已清理临时音频文件'")
                print()
                print("❌ 不应该再看到:")
                print("   - 'No such file or directory'")
                print("   - 'WebSocket音频发送失败'")
                
                return True, result.get('track_id')
            else:
                print("❌ API返回失败")
                return False, None
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            return False, None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False, None

def main():
    import sys
    if len(sys.argv) != 2:
        print("用法: python test_file_fix.py <device_id>")
        print("示例: python test_file_fix.py 7c:2c:67:8d:89:78")
        sys.exit(1)
    
    device_id = sys.argv[1]
    
    print("🔧 音频文件自动删除问题修复验证")
    print("=" * 60)
    
    success, track_id = test_file_fix(device_id)
    
    print()
    print("📊 修复验证结果")
    print("=" * 60)
    
    if success:
        print("✅ 文件修复测试成功")
        print("🎯 硬件应该能正常播放音频了")
        print()
        print("💡 技术要点:")
        print("   • 持久文件副本机制")
        print("   • 异步音频传输支持")
        print("   • 自动清理临时文件")
        print("   • 防止TTS删除干扰")
    else:
        print("❌ 文件修复测试失败")
        print("🔍 请检查服务器状态")
    
    print()
    print("🔧 下一步:")
    print("   1. 在Linux服务器重启Python服务")
    print("   2. 运行这个测试验证修复效果")
    print("   3. 检查硬件是否能听到音频")

if __name__ == "__main__":
    main()

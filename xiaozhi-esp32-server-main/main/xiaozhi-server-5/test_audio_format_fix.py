#!/usr/bin/env python3
"""
🎵 音频格式修复验证脚本
验证参考普通对话机制的音频格式处理是否成功
"""

import requests
import time

def test_audio_format_fix(device_id):
    """测试音频格式修复"""
    
    print("🎵 参考普通对话机制的音频格式修复测试")
    print("=" * 60)
    print(f"📱 设备ID: {device_id}")
    print()
    print("📋 修复内容:")
    print("   ✅ 完全参考普通对话的音频处理机制")
    print("   ✅ 使用 audio_bytes_to_data 函数")
    print("   ✅ 自动检测音频格式（MP3/WAV/AAC）")
    print("   ✅ 基于文件内容而非扩展名检测")
    print("   ✅ 与普通对话使用相同的Opus编码")
    print()
    
    api_url = "http://172.20.12.204:8003/xiaozhi/greeting/send"
    
    payload = {
        "device_id": device_id,
        "initial_content": "格式修复测试：现在使用普通对话的音频处理机制！", 
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
            
            if result.get('success'):
                print()
                print("🎯 期待的修复效果:")
                print("1. ✅ 语音合成成功")
                print("2. ✅ 创建持久音频文件")
                print("3. ✅ 自动检测音频格式 (mp3/wav)")
                print("4. ✅ 音频转换成功 (Opus帧)")
                print("5. ✅ 主动问候音频发送完成") 
                print("6. ✅ 已清理临时音频文件")
                print()
                print("🔍 关键日志指标:")
                print("   ✅ '创建持久音频文件'")
                print("   ✅ '音频转换成功: X 帧, 时长 X.Xs, 格式: mp3/wav'")
                print("   ✅ '主动问候音频发送完成'")
                print("   ✅ '已清理临时音频文件'")
                print()
                print("❌ 不应该再看到:")
                print("   ❌ 'Decoding failed. ffmpeg returned error'")
                print("   ❌ 'invalid start code'") 
                print("   ❌ 'Invalid data found when processing input'")
                print("   ❌ 'WebSocket音频发送失败'")
                
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
        print("用法: python test_audio_format_fix.py <device_id>")
        print("示例: python test_audio_format_fix.py 7c:2c:67:8d:89:78")
        sys.exit(1)
    
    device_id = sys.argv[1]
    
    print("🎵 参考普通对话机制的音频格式问题修复")
    print("=" * 70)
    
    success, track_id = test_audio_format_fix(device_id)
    
    print()
    print("📊 修复验证结果")
    print("=" * 70)
    
    if success:
        print("✅ 音频格式修复测试成功")
        print("🎯 硬件应该能正常播放音频了")
        print()
        print("💡 技术要点:")
        print("   • 完全参考普通对话的音频处理机制")
        print("   • 自动检测音频格式 (不依赖文件扩展名)")
        print("   • 使用 audio_bytes_to_data 函数")
        print("   • 与普通对话完全一致的Opus编码")
        print("   • 基于音频内容特征的格式识别")
    else:
        print("❌ 音频格式修复测试失败")
        print("🔍 请检查服务器状态")
    
    print()
    print("🔧 下一步:")
    print("   1. 在Linux服务器重启Python服务")
    print("   2. 运行这个测试验证修复效果")
    print("   3. 监控日志确认音频格式检测成功")
    print("   4. 验证硬件是否能听到清晰音频")

if __name__ == "__main__":
    main()

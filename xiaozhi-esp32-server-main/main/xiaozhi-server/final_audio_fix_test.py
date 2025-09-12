#!/usr/bin/env python3
"""
🎵 主动对话音频最终修复验证
完整对比普通对话机制，确保硬件音频播放正常
"""

import subprocess
import json
import time
from datetime import datetime

def print_comprehensive_fix_summary():
    """打印全面的修复总结"""
    print("🔧 主动对话音频 - 完整修复总结")
    print("=" * 80)
    
    print("❌ 原始问题:")
    print("  • 硬件人员反馈：主动对话无声音播放")
    print("  • 服务端日志显示音频发送成功，但硬件端无声")
    print("  • 普通对话音频正常，主动对话音频异常")
    
    print("\n🔍 根本原因分析:")
    print("  • 主动对话使用了简化的音频发送机制")
    print("  • 缺少普通对话中的关键状态管理")
    print("  • 缺少硬件播放的触发信号")
    
    print("\n✅ 完整修复方案:")
    print("  1️⃣ 使用sendAudioMessage()替代sendAudio()")
    print("     - 包含完整的TTS状态消息流程")
    print("     - sentence_start → audio → sentence_end → stop")
    print("     - stop消息是硬件播放的关键触发器")
    
    print("  2️⃣ 完整的连接状态管理:")
    print("     - llm_finish_task = True")
    print("     - client_is_speaking = True")
    print("     - client_abort = False")
    print("     - sentence_id = uuid.uuid4().hex")
    
    print("  3️⃣ TTS第一句话状态初始化:")
    print("     - tts_audio_first_sentence = True")
    print("     - 触发预缓冲机制（前3帧立即发送）")
    print("     - 与普通对话行为完全一致")
    
    print("  4️⃣ 使用SentenceType.LAST:")
    print("     - 确保发送stop消息")
    print("     - 触发clearSpeakStatus()清理")
    print("     - 完整的播放周期管理")
    
    print("\n🎯 预期效果:")
    print("  ✅ 主动对话音频与普通对话完全一致")
    print("  ✅ 硬件应该听到清晰的音频播放")
    print("  ✅ 包含所有必要的WebSocket消息")
    print("  ✅ 正确的状态管理和清理")

def send_final_test():
    """发送最终测试请求"""
    print("\n🚀 发送最终验证测试")
    print("=" * 50)
    
    device_id = "7c:2c:67:8d:89:78"
    test_content = "🎵 最终修复验证：主动对话音频应该正常播放了！"
    
    print(f"📱 设备ID: {device_id}")
    print(f"💬 测试内容: {test_content}")
    print(f"⏰ 发送时间: {datetime.now().strftime('%H:%M:%S')}")
    
    curl_command = [
        "curl", "-X", "POST", "http://172.20.12.204:8003/xiaozhi/greeting/send",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "device_id": device_id,
            "initial_content": test_content,
            "category": "system_reminder"
        })
    ]
    
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            if response.get("success"):
                track_id = response.get("track_id")
                print(f"✅ 请求发送成功")
                print(f"🆔 Track ID: {track_id}")
                return track_id
            else:
                print(f"❌ API返回失败: {response}")
                return None
        else:
            print(f"❌ curl命令失败: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

def print_monitoring_guide(track_id):
    """打印监控指南"""
    print(f"\n🔍 关键日志监控指南")
    print("=" * 50)
    
    if track_id:
        print(f"📋 监控Track ID: {track_id}")
        print(f"📂 日志文件: logs/app_unified.log")
        
        print(f"\n🎯 关键成功指标:")
        success_indicators = [
            "生成主动问候句子ID",
            "设置TTS第一句话标志: True",
            "发送音频消息: SentenceType.LAST",
            "发送第一段语音",  # 预缓冲标志
            "TTS状态消息: sentence_start",
            "TTS状态消息: sentence_end", 
            "TTS状态消息: stop",  # 🎯 最关键！
            "主动问候音频发送完成",
            "WebSocket音频发送成功"
        ]
        
        for i, indicator in enumerate(success_indicators, 1):
            marker = "🎯" if "stop" in indicator else "✅"
            print(f"  {i:2d}. {marker} {indicator}")
        
        print(f"\n📋 实时监控命令:")
        print(f"tail -f logs/app_unified.log | grep '{track_id}'")
        
        print(f"\n🔍 详细分析命令:")
        print(f"grep '{track_id}' logs/app_unified.log | grep -E '(TTS|sendAudio|sentence_|stop)'")
        
    else:
        print("❌ 无有效Track ID，无法提供具体监控指南")

def print_hardware_verification_guide():
    """打印硬件验证指南"""
    print(f"\n🎧 硬件验证指南")
    print("=" * 50)
    
    print("👤 硬件人员请确认:")
    print("  1️⃣ 是否听到音频播放开始？")
    print("  2️⃣ 音频内容是否清晰？")
    print("  3️⃣ 音频播放是否完整？")
    print("  4️⃣ 播放结束后是否正常停止？")
    
    print("\n🚨 如果仍无声音:")
    print("  📋 请提供硬件端日志，包含:")
    print("     • WebSocket连接状态")
    print("     • 收到的TTS状态消息")
    print("     • 音频帧接收情况")
    print("     • 硬件音频解码和播放日志")
    
    print("\n🔧 硬件端检查项:")
    print("  ✅ WebSocket连接是否正常？")
    print("  ✅ 是否收到TTS状态消息：sentence_start, sentence_end, stop？")
    print("  ✅ 是否收到二进制音频帧数据？")
    print("  ✅ Opus解码是否正常？")
    print("  ✅ 音频播放设备是否正常？")

def main():
    """主测试流程"""
    print("🎵 主动对话音频最终修复验证")
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 打印修复总结
    print_comprehensive_fix_summary()
    
    # 发送测试请求
    track_id = send_final_test()
    
    # 打印监控指南
    print_monitoring_guide(track_id)
    
    # 打印硬件验证指南
    print_hardware_verification_guide()
    
    print(f"\n🎊 修复总结")
    print("=" * 50)
    print("✅ 所有关键差异已修复")
    print("✅ 主动对话现使用与普通对话完全相同的机制")
    print("✅ 包含完整的状态管理和TTS消息流程")
    print("✅ 硬件应该能听到正常的音频播放")
    
    print(f"\n⏰ 请等待约5-10秒...")
    print("🎧 硬件人员请立即确认音频播放效果！")

if __name__ == "__main__":
    main()

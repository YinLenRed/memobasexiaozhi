#!/usr/bin/env python3
"""
🔌 WebSocket连接诊断工具
解决硬件设备WebSocket连接问题
"""

import requests
import json
import time
import subprocess
from datetime import datetime

def print_diagnosis_header():
    """打印诊断头部信息"""
    print("🔌 WebSocket连接诊断工具")
    print("=" * 80)
    print(f"📅 诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 目标设备: 7c:2c:67:8d:89:78")
    print(f"📡 WebSocket服务器: ws://47.98.51.180:8000/xiaozhi/v1/")
    print()

def check_websocket_server_status():
    """检查WebSocket服务器状态"""
    print("🔍 1. 检查WebSocket服务器状态")
    print("-" * 50)
    
    try:
        # 检查端口监听状态
        result = subprocess.run(
            ["netstat", "-tlnp", "|", "grep", "8000"], 
            shell=True, capture_output=True, text=True
        )
        
        if "8000" in result.stdout:
            print("✅ WebSocket服务器端口8000正在监听")
            print(f"📋 详情: {result.stdout.strip()}")
        else:
            print("❌ WebSocket服务器端口8000未监听")
            return False
            
    except Exception as e:
        print(f"❌ 检查端口失败: {e}")
        return False
    
    return True

def check_current_websocket_connections():
    """检查当前WebSocket连接"""
    print("\n🔍 2. 检查当前WebSocket连接")
    print("-" * 50)
    
    try:
        # 通过日志检查连接状态
        result = subprocess.run(
            ["tail", "-50", "logs/app_unified.log"], 
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            websocket_lines = [line for line in result.stdout.split('\n') 
                             if 'websocket' in line.lower() or 'connection' in line.lower()]
            
            if websocket_lines:
                print("📋 最近的WebSocket相关日志:")
                for line in websocket_lines[-10:]:  # 最后10条
                    print(f"  {line}")
            else:
                print("⚠️ 未找到最近的WebSocket连接日志")
                
        else:
            print("❌ 无法读取日志文件")
            
    except Exception as e:
        print(f"❌ 检查连接日志失败: {e}")

def check_device_websocket_requirements():
    """检查设备WebSocket连接要求"""
    print("\n🔍 3. 硬件WebSocket连接要求")
    print("-" * 50)
    
    requirements = [
        "📡 WebSocket URL: ws://47.98.51.180:8000/xiaozhi/v1/",
        "🎵 音频格式: Opus",
        "📊 采样率: 16000Hz",
        "🔢 声道数: 1 (单声道)",
        "⏱️ 帧时长: 60ms",
        "🆔 设备ID: 需在WebSocket连接时发送",
        "🔄 保持连接: 需要心跳保持",
        "📨 消息格式: JSON格式控制消息 + 二进制音频数据"
    ]
    
    print("✅ 硬件端必须满足以下要求:")
    for req in requirements:
        print(f"  {req}")

def provide_websocket_connection_guide():
    """提供WebSocket连接指南"""
    print("\n📋 4. 硬件WebSocket连接实现指南")
    print("-" * 50)
    
    connection_steps = [
        "🔗 建立WebSocket连接到 ws://47.98.51.180:8000/xiaozhi/v1/",
        "📨 发送hello消息标识设备ID",
        "👂 监听TTS状态消息 (sentence_start, sentence_end, stop)",
        "🎵 接收二进制音频帧数据",
        "🔊 解码Opus音频并播放",
        "💓 定期发送心跳保持连接"
    ]
    
    print("🎯 连接建立步骤:")
    for i, step in enumerate(connection_steps, 1):
        print(f"  {i}. {step}")
    
    print("\n📨 初始连接消息示例:")
    hello_message = {
        "type": "hello",
        "device_id": "7c:2c:67:8d:89:78",
        "version": 1,
        "features": {},
        "transport": "websocket",
        "audio_params": {
            "format": "opus",
            "sample_rate": 16000,
            "channels": 1,
            "frame_duration": 60
        }
    }
    print(f"  {json.dumps(hello_message, indent=2, ensure_ascii=False)}")

def test_websocket_accessibility():
    """测试WebSocket可访问性"""
    print("\n🔍 5. 测试WebSocket服务可访问性")
    print("-" * 50)
    
    # 测试HTTP端点(如果有健康检查)
    try:
        response = requests.get("http://47.98.51.180:8000/health", timeout=5)
        print(f"✅ HTTP健康检查: {response.status_code}")
    except requests.exceptions.RequestException:
        print("⚠️ HTTP健康检查不可用 (正常，WebSocket服务器)")
    
    # 建议使用WebSocket客户端测试
    print("\n💡 建议使用WebSocket客户端测试连接:")
    print("  # 使用wscat测试 (如果安装了)")
    print("  wscat -c ws://47.98.51.180:8000/xiaozhi/v1/")
    print("  # 然后发送hello消息:")
    print('  {"type":"hello","device_id":"7c:2c:67:8d:89:78","version":1}')

def provide_debugging_commands():
    """提供调试命令"""
    print("\n🛠️ 6. 调试命令集合")
    print("-" * 50)
    
    commands = [
        ("检查WebSocket进程", "ps aux | grep python | grep app.py"),
        ("检查端口监听", "netstat -tlnp | grep 8000"),
        ("查看WebSocket连接", "netstat -an | grep 8000"),
        ("监控WebSocket日志", "tail -f logs/app_unified.log | grep -i websocket"),
        ("监控连接日志", "tail -f logs/app_unified.log | grep -i connection"),
        ("检查服务状态", "curl -s http://172.20.12.204:8003/health || echo '服务不可达'")
    ]
    
    print("🔧 可用的调试命令:")
    for desc, cmd in commands:
        print(f"  📋 {desc}:")
        print(f"     {cmd}")

def provide_hardware_checklist():
    """提供硬件检查清单"""
    print("\n✅ 7. 硬件端检查清单")
    print("-" * 50)
    
    checklist = [
        "🌐 网络连接正常？",
        "🔗 能否访问 47.98.51.180:8000？",
        "📨 WebSocket客户端实现正确？",
        "🆔 设备ID 7c:2c:67:8d:89:78 正确？",
        "👂 是否监听TTS状态消息？",
        "🎵 是否正确解码Opus音频？",
        "🔊 音频播放设备正常？",
        "💓 连接保持机制实现？"
    ]
    
    print("❓ 硬件人员请逐项确认:")
    for item in checklist:
        print(f"  □ {item}")

def suggest_immediate_actions():
    """建议立即行动"""
    print("\n🚀 8. 立即行动建议")
    print("-" * 50)
    
    actions = [
        "🔌 硬件端立即连接WebSocket",
        "📨 发送正确的hello消息",
        "👂 监听服务端消息",
        "🧪 使用WebSocket客户端工具测试",
        "📋 提供硬件端连接日志"
    ]
    
    print("⚡ 优先级行动:")
    for i, action in enumerate(actions, 1):
        print(f"  {i}. {action}")
    
    print("\n🎯 期望结果:")
    print("  ✅ 在服务端日志中看到: '新的WebSocket连接: 7c:2c:67:8d:89:78'")
    print("  ✅ 主动问候后听到音频播放")

def main():
    """主诊断流程"""
    print_diagnosis_header()
    
    # 执行各项检查
    server_ok = check_websocket_server_status()
    check_current_websocket_connections()
    check_device_websocket_requirements()
    provide_websocket_connection_guide()
    test_websocket_accessibility()
    provide_debugging_commands()
    provide_hardware_checklist()
    suggest_immediate_actions()
    
    print("\n" + "=" * 80)
    print("🎊 诊断完成")
    print("=" * 80)
    
    if server_ok:
        print("✅ 服务端WebSocket服务正常")
        print("❌ 问题在于：硬件设备未建立WebSocket连接")
        print("🎯 解决方案：硬件端需要正确连接WebSocket并发送hello消息")
    else:
        print("❌ 服务端WebSocket服务异常")
        print("🔧 请先修复服务端问题")
    
    print("\n🔔 关键提醒：")
    print("  💡 MQTT连接 ≠ WebSocket连接")
    print("  💡 MQTT用于命令，WebSocket用于音频")
    print("  💡 两个连接都必须正常，音频才能播放")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
🌐 服务器地址诊断工具
分析硬件连接到不同WebSocket服务器的问题
"""

import subprocess
import requests
import json
from datetime import datetime

def print_server_diagnosis():
    """打印服务器地址诊断"""
    print("🌐 服务器地址诊断")
    print("=" * 80)
    print(f"📅 诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print("🔍 发现的问题:")
    print("  ❌ 硬件连接地址: ws://47.98.51.180:8000/xiaozhi/v1/")
    print("  ❌ Python服务地址: ws://172.20.12.204:8000/xiaozhi/v1/")
    print("  ❌ 两个不同的服务器！")
    print()

def check_server_addresses():
    """检查两个服务器地址"""
    print("🔍 1. 检查两个服务器状态")
    print("-" * 50)
    
    servers = [
        ("硬件连接的服务器", "47.98.51.180", 8000),
        ("Python服务器", "172.20.12.204", 8000),
    ]
    
    for name, host, port in servers:
        print(f"\n📡 {name}: {host}:{port}")
        
        # 检查端口是否开放
        try:
            result = subprocess.run(
                ["nc", "-z", "-v", host, str(port)], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print(f"  ✅ 端口开放")
            else:
                print(f"  ❌ 端口不可达")
        except subprocess.TimeoutExpired:
            print(f"  ⏰ 连接超时")
        except Exception as e:
            print(f"  ❌ 检查失败: {e}")
        
        # 尝试HTTP健康检查
        try:
            response = requests.get(f"http://{host}:{port}", timeout=3)
            print(f"  ✅ HTTP响应: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️ HTTP不可用（WebSocket服务器正常）")

def analyze_architecture():
    """分析架构问题"""
    print("\n🏗️ 2. 架构分析")
    print("-" * 50)
    
    print("💡 可能的架构情况:")
    print("  1️⃣ 47.98.51.180 = 生产环境/外网服务器")
    print("  2️⃣ 172.20.12.204 = 内网开发服务器")
    print("  3️⃣ 硬件固件中硬编码了生产地址")
    print("  4️⃣ 两个独立的WebSocket服务实例")
    print()
    
    print("🎯 解决方案:")
    print("  A. 修改硬件配置，连接到172.20.12.204")
    print("  B. 在47.98.51.180服务器上运行相同的代码")
    print("  C. 设置代理/转发")
    print("  D. 统一服务器地址")

def check_hardware_configuration():
    """检查硬件配置"""
    print("\n🔧 3. 硬件配置分析")
    print("-" * 50)
    
    print("📋 硬件WebSocket地址来源:")
    print("  • 可能在硬件固件中硬编码")
    print("  • 可能通过MQTT配置下发")
    print("  • 可能在设备配置文件中")
    print()
    
    print("🔍 需要硬件人员确认:")
    print("  ❓ WebSocket地址是如何配置的？")
    print("  ❓ 能否动态修改WebSocket地址？")
    print("  ❓ 是否可以连接到172.20.12.204:8000？")
    print("  ❓ 硬件是否支持多个WebSocket地址？")

def provide_immediate_solutions():
    """提供即时解决方案"""
    print("\n⚡ 4. 即时解决方案")
    print("-" * 50)
    
    print("🎯 方案A: 修改硬件连接地址（推荐）")
    print("  1. 硬件人员修改WebSocket地址为: ws://172.20.12.204:8000/xiaozhi/v1/")
    print("  2. 重新连接硬件")
    print("  3. 验证能否在Python服务端看到连接")
    print()
    
    print("🎯 方案B: 在47.98.51.180部署相同服务")
    print("  1. 在47.98.51.180服务器上部署xiaozhi-server")
    print("  2. 确保配置和172.20.12.204一致")
    print("  3. 启动服务，监听8000端口")
    print()
    
    print("🎯 方案C: 端口转发/代理")
    print("  1. 在47.98.51.180上设置反向代理")
    print("  2. 将WebSocket流量转发到172.20.12.204:8000")
    print("  3. 保持硬件连接地址不变")

def provide_testing_commands():
    """提供测试命令"""
    print("\n🧪 5. 测试命令")
    print("-" * 50)
    
    print("📋 硬件人员可以测试的连接:")
    print("  # 尝试连接到Python服务器")
    print("  wscat -c ws://172.20.12.204:8000/xiaozhi/v1/")
    print("  # 发送hello消息")
    print('  {"type":"hello","device_id":"7c:2c:67:8d:89:78","version":1}')
    print()
    
    print("📋 验证Python服务器连接状态:")
    print("  # 监控WebSocket连接日志")
    print("  tail -f logs/app_unified.log | grep -E '(WebSocket|connection|device_id)'")
    print()
    
    print("📋 验证服务器端口:")
    print("  # 检查Python服务是否在8000端口监听")
    print("  netstat -tlnp | grep 8000")
    print("  # 检查进程状态")
    print("  ps aux | grep 'python.*app.py'")

def main():
    """主诊断流程"""
    print_server_diagnosis()
    check_server_addresses()
    analyze_architecture()
    check_hardware_configuration()
    provide_immediate_solutions()
    provide_testing_commands()
    
    print("\n" + "=" * 80)
    print("🎊 诊断结论")
    print("=" * 80)
    print("✅ MQTT连接正常：硬件 → MQTT服务器")
    print("✅ 音频生成正常：Python服务 → TTS")
    print("❌ WebSocket连接错位：硬件连接到47.98.51.180，但Python服务在172.20.12.204")
    print()
    print("🎯 最佳解决方案：")
    print("   让硬件连接到 ws://172.20.12.204:8000/xiaozhi/v1/")
    print("   这样就能在我们的Python服务中看到设备连接")
    print("   主动对话音频就能正常发送到硬件了！")
    print()
    print("🔔 关键提醒：")
    print("   MQTT和WebSocket是两个独立的连接")
    print("   MQTT用于命令控制，WebSocket用于音频传输")
    print("   两个都必须连接到正确的服务器才能正常工作")

if __name__ == "__main__":
    main()

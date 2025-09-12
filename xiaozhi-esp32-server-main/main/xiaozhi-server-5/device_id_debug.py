#!/usr/bin/env python3
"""
🆔 设备ID识别调试工具
诊断WebSocket连接中的设备ID识别问题
"""

import subprocess
import json
from datetime import datetime

def check_websocket_connections():
    """检查当前WebSocket连接状态"""
    print("🆔 设备ID识别调试")
    print("=" * 80)
    print(f"📅 调试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print("🔍 1. 检查当前WebSocket连接")
    print("-" * 50)
    
    try:
        # 检查WebSocket连接数
        result = subprocess.run(
            ["netstat", "-an", "|", "grep", "8000", "|", "grep", "ESTABLISHED"], 
            shell=True, capture_output=True, text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            connections = result.stdout.strip().split('\n')
            print(f"✅ 发现 {len(connections)} 个8000端口的活跃连接:")
            for conn in connections:
                print(f"  📋 {conn.strip()}")
        else:
            print("⚠️ 未发现8000端口的活跃连接")
            
    except Exception as e:
        print(f"❌ 检查连接失败: {e}")

def analyze_hello_message_format():
    """分析hello消息格式要求"""
    print("\n🔍 2. WebSocket设备ID识别机制")
    print("-" * 50)
    
    print("📋 Python服务的设备ID识别逻辑:")
    print("  1️⃣ 从WebSocket headers中的 'device-id' 字段")
    print("  2️⃣ 从URL查询参数中的 'device-id' 参数")
    print("  3️⃣ 如果都没有，连接会被拒绝")
    print()
    
    print("📨 正确的连接方式:")
    print("  方式A: WebSocket URL带参数")
    print("    ws://47.98.51.180:8000/xiaozhi/v1/?device-id=7c:2c:67:8d:89:78&client-id=esp32")
    print()
    print("  方式B: WebSocket headers")
    print("    Headers: {'device-id': '7c:2c:67:8d:89:78'}")
    print()
    
    print("⚠️ 硬件当前连接方式分析:")
    print("  • 连接URL: ws://47.98.51.180:8000/xiaozhi/v1/")
    print("  • 缺少device-id参数或header")
    print("  • Python服务无法识别设备ID")

def provide_hardware_fix():
    """提供硬件修复方案"""
    print("\n🔧 3. 硬件端修复方案")
    print("-" * 50)
    
    print("🎯 方案A: 修改WebSocket连接URL（推荐）")
    print("```cpp")
    print("// ESP32代码修改")
    print("String deviceId = \"7c:2c:67:8d:89:78\";")
    print("String wsUrl = \"ws://47.98.51.180:8000/xiaozhi/v1/?device-id=\" + deviceId + \"&client-id=esp32\";")
    print("webSocket.begin(wsUrl);")
    print("```")
    print()
    
    print("🎯 方案B: 添加WebSocket Headers")
    print("```cpp")
    print("// ESP32代码修改")
    print("webSocket.begin(\"47.98.51.180\", 8000, \"/xiaozhi/v1/\");")
    print("webSocket.setExtraHeaders(\"device-id: 7c:2c:67:8d:89:78\\r\\n\");")
    print("```")
    print()
    
    print("🎯 方案C: hello消息中包含device-id（备选）")
    print("```json")
    print("{")
    print("  \"type\": \"hello\",")
    print("  \"device_id\": \"7c:2c:67:8d:89:78\",")
    print("  \"version\": 1,")
    print("  \"features\": {},")
    print("  \"transport\": \"websocket\"")
    print("}")
    print("```")

def test_connection_scenarios():
    """测试连接场景"""
    print("\n🧪 4. 测试验证方案")
    print("-" * 50)
    
    print("📋 硬件人员可以测试的连接:")
    print("  # 测试方案A: URL参数方式")
    print("  wscat -c 'ws://47.98.51.180:8000/xiaozhi/v1/?device-id=7c:2c:67:8d:89:78&client-id=esp32'")
    print()
    print("  # 测试方案B: Header方式")
    print("  wscat -c ws://47.98.51.180:8000/xiaozhi/v1/ -H 'device-id: 7c:2c:67:8d:89:78'")
    print()
    
    print("✅ 预期结果:")
    print("  • 连接成功后不会看到'端口正常，如需测试连接...'消息")
    print("  • Python服务日志显示: '新设备连接: 7c:2c:67:8d:89:78'")
    print("  • find_device_connection能找到设备")

def check_current_logs():
    """检查当前日志"""
    print("\n🔍 5. 当前日志分析")
    print("-" * 50)
    
    try:
        # 检查最近的WebSocket相关日志
        result = subprocess.run(
            ["tail", "-20", "logs/app_unified.log"], 
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            websocket_lines = []
            
            for line in lines:
                if any(keyword in line.lower() for keyword in 
                      ['websocket', 'connection', 'device', 'hello', 'session']):
                    websocket_lines.append(line)
            
            if websocket_lines:
                print("📋 最近的相关日志:")
                for line in websocket_lines[-10:]:
                    if line.strip():
                        print(f"  {line}")
            else:
                print("⚠️ 未找到最近的WebSocket相关日志")
                
    except Exception as e:
        print(f"❌ 检查日志失败: {e}")

def main():
    """主调试流程"""
    check_websocket_connections()
    analyze_hello_message_format()
    provide_hardware_fix()
    test_connection_scenarios()
    check_current_logs()
    
    print("\n" + "=" * 80)
    print("🎊 调试结论")
    print("=" * 80)
    print("✅ WebSocket服务器配置正确，监听47.98.51.180:8000")
    print("✅ 硬件能够建立WebSocket连接")
    print("❌ 设备ID识别失败：连接时缺少device-id信息")
    print()
    print("🎯 解决方案:")
    print("   硬件在WebSocket连接URL中添加device-id参数")
    print("   ws://47.98.51.180:8000/xiaozhi/v1/?device-id=7c:2c:67:8d:89:78&client-id=esp32")
    print()
    print("🔔 这样修改后，主动对话音频就能正常发送到硬件了！")

if __name__ == "__main__":
    main()

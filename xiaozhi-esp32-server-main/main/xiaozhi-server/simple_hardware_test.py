#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版Python-硬件测试脚本 (无外部依赖)
只使用Python标准库进行基础MQTT和HTTP测试
"""

import socket
import json
import time
import threading
from datetime import datetime
import uuid
import sys

class SimpleMQTTClient:
    """简单的MQTT客户端实现（仅用于测试）"""
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
    
    def connect(self):
        """连接到MQTT代理"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            self.connected = True
            return True
        except Exception as e:
            print(f"❌ MQTT连接失败: {e}")
            return False
    
    def publish(self, topic, message):
        """发布消息（简化版）"""
        if not self.connected:
            return False
        
        try:
            # 这里是简化的MQTT发布实现
            # 实际项目中应该使用完整的MQTT协议
            print(f"📤 模拟发布到 {topic}: {message}")
            return True
        except Exception as e:
            print(f"❌ 发布失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
        self.connected = False

class SimpleHardwareTest:
    def __init__(self, device_id="7c:2c:67:8d:89:78"):
        self.device_id = device_id
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.python_service_host = "172.20.12.204"  # Python API服务内网地址
        self.python_service_port = 8003
        self.ws_host = "47.98.51.180"  # WebSocket公网地址
        self.ws_port = 8888  # 测试专用端口，避免冲突
        
        # 测试结果
        self.test_results = {
            "network_test": False,
            "mqtt_connection_test": False,
            "python_service_test": False,
            "command_simulation": False
        }
    
    def log(self, message, level="INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
        icon = icons.get(level, "📝")
        print(f"[{timestamp}] {icon} {message}")
    
    def test_network_connectivity(self):
        """测试网络连通性"""
        self.log("🌐 测试网络连通性...")
        
        # 测试MQTT服务器连通性
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.mqtt_host, self.mqtt_port))
            sock.close()
            
            if result == 0:
                self.log(f"✅ MQTT服务器可达: {self.mqtt_host}:{self.mqtt_port}", "SUCCESS")
                mqtt_reachable = True
            else:
                self.log(f"❌ MQTT服务器不可达: {self.mqtt_host}:{self.mqtt_port}", "ERROR")
                mqtt_reachable = False
        except Exception as e:
            self.log(f"❌ MQTT连通性测试失败: {e}", "ERROR")
            mqtt_reachable = False
        
        # 测试Python服务连通性
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.python_service_host, self.python_service_port))
            sock.close()
            
            if result == 0:
                self.log(f"✅ Python服务可达: {self.python_service_host}:{self.python_service_port}", "SUCCESS")
                python_reachable = True
            else:
                self.log(f"❌ Python服务不可达: {self.python_service_host}:{self.python_service_port}", "ERROR")
                python_reachable = False
        except Exception as e:
            self.log(f"❌ Python服务连通性测试失败: {e}", "ERROR")
            python_reachable = False
        
        # 测试WebSocket服务连通性
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.ws_host, self.ws_port))
            sock.close()
            
            if result == 0:
                self.log(f"✅ WebSocket服务可达: {self.ws_host}:{self.ws_port}", "SUCCESS")
                ws_reachable = True
            else:
                self.log(f"❌ WebSocket服务不可达: {self.ws_host}:{self.ws_port}", "ERROR")
                ws_reachable = False
        except Exception as e:
            self.log(f"❌ WebSocket服务连通性测试失败: {e}", "ERROR")
            ws_reachable = False
        
        self.test_results["network_test"] = mqtt_reachable and python_reachable and ws_reachable
        return self.test_results["network_test"]
    
    def test_mqtt_connection(self):
        """测试MQTT连接"""
        self.log("📡 测试MQTT连接...")
        
        try:
            mqtt_client = SimpleMQTTClient(self.mqtt_host, self.mqtt_port)
            if mqtt_client.connect():
                self.log("✅ MQTT连接成功", "SUCCESS")
                self.test_results["mqtt_connection_test"] = True
                mqtt_client.disconnect()
                return True
            else:
                self.log("❌ MQTT连接失败", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ MQTT连接异常: {e}", "ERROR")
            return False
    
    def test_python_service(self):
        """测试Python服务API"""
        self.log("🐍 测试Python服务API...")
        
        try:
            # 测试设备状态查询API
            import urllib.request
            import urllib.parse
            
            url = f"http://{self.python_service_host}:{self.python_service_port}/xiaozhi/greeting/status"
            params = urllib.parse.urlencode({"device_id": self.device_id})
            full_url = f"{url}?{params}"
            
            req = urllib.request.Request(full_url)
            req.add_header('User-Agent', 'PythonHardwareTest/1.0')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read().decode('utf-8')
                result = json.loads(data)
                
                self.log(f"✅ Python服务响应: {result}", "SUCCESS")
                self.test_results["python_service_test"] = True
                return True
                
        except Exception as e:
            self.log(f"❌ Python服务测试失败: {e}", "ERROR")
            return False
    
    def simulate_speak_command(self):
        """模拟SPEAK命令流程"""
        self.log("🎯 模拟SPEAK命令流程...")
        
        # 生成测试数据
        track_id = f"TEST{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"
        
        # 模拟SPEAK命令
        speak_command = {
            "type": "SPEAK",
            "track_id": track_id,
            "text": "简化版测试：这是一条Python-硬件全流程测试消息。",
            "timestamp": datetime.now().isoformat() + "Z",
            "audio_url": f"ws://{self.ws_host}:{self.ws_port}/xiaozhi/v1/",
            "expected_duration": 10
        }
        
        # 模拟ACK响应
        ack_response = {
            "evt": "CMD_RECEIVED",
            "track_id": track_id,
            "timestamp": datetime.now().strftime('%H:%M:%S'),
            "device_id": self.device_id
        }
        
        # 模拟完成事件
        complete_event = {
            "evt": "EVT_SPEAK_DONE",
            "track_id": track_id,
            "status": "completed",
            "timestamp": datetime.now().strftime('%H:%M:%S'),
            "duration_actual": 8.5,
            "device_id": self.device_id
        }
        
        # 显示流程
        self.log("📋 模拟完整SPEAK流程:")
        print(f"   📤 1. Python → 硬件 (MQTT: device/{self.device_id}/cmd)")
        print(f"      {json.dumps(speak_command, indent=6, ensure_ascii=False)}")
        print()
        
        print(f"   📥 2. 硬件 → Python (MQTT: device/{self.device_id}/ack)")
        print(f"      {json.dumps(ack_response, indent=6, ensure_ascii=False)}")
        print()
        
        print(f"   🌐 3. 硬件连接WebSocket: {speak_command['audio_url']}")
        print(f"      - 硬件应该连接到WebSocket获取音频数据")
        print(f"      - 播放音频内容")
        print()
        
        print(f"   📥 4. 硬件 → Python (MQTT: device/{self.device_id}/event)")
        print(f"      {json.dumps(complete_event, indent=6, ensure_ascii=False)}")
        print()
        
        self.test_results["command_simulation"] = True
        self.log("✅ SPEAK命令流程模拟完成", "SUCCESS")
        return True
    
    def print_test_results(self):
        """打印测试结果"""
        print("\n" + "=" * 60)
        print("📊 简化版Python-硬件测试结果")
        print("=" * 60)
        
        print(f"📱 测试设备: {self.device_id}")
        print(f"📡 MQTT服务器: {self.mqtt_host}:{self.mqtt_port}")
        print(f"🐍 Python服务: http://{self.python_service_host}:{self.python_service_port}")
        print(f"🌐 WebSocket服务: ws://{self.ws_host}:{self.ws_port}/xiaozhi/v1/")
        print()
        
        # 测试项目
        tests = [
            ("🌐 网络连通性", self.test_results["network_test"]),
            ("📡 MQTT连接", self.test_results["mqtt_connection_test"]),
            ("🐍 Python服务", self.test_results["python_service_test"]),
            ("🎯 命令流程模拟", self.test_results["command_simulation"])
        ]
        
        passed = 0
        for test_name, status in tests:
            icon = "✅" if status else "❌"
            status_text = "通过" if status else "失败"
            print(f"{icon} {test_name:<20} : {status_text}")
            if status:
                passed += 1
        
        print("-" * 60)
        print(f"📈 总体结果: {passed}/{len(tests)} 项测试通过")
        
        if passed == len(tests):
            print("🎉 基础环境测试全部通过！")
            print("💡 系统已准备好进行完整的硬件集成测试")
        else:
            print("⚠️ 部分测试未通过，请检查相关配置")
        
        print("\n💡 下一步:")
        print("   1. 如果基础测试通过，可以安装完整依赖运行详细测试")
        print("   2. 硬件端实现WebSocket客户端和事件上报功能")
        print("   3. 进行端到端的完整流程测试")
    
    def run_test(self):
        """运行完整测试"""
        print("🚀 简化版Python-硬件测试启动")
        print("="*60)
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📱 目标设备: {self.device_id}")
        print("🎯 测试内容: 基础环境 + 流程模拟")
        print()
        
        try:
            # 依次运行各项测试
            self.test_network_connectivity()
            time.sleep(1)
            
            self.test_mqtt_connection()
            time.sleep(1)
            
            self.test_python_service()
            time.sleep(1)
            
            self.simulate_speak_command()
            
            # 显示结果
            self.print_test_results()
            
            return all(self.test_results.values())
            
        except KeyboardInterrupt:
            self.log("用户中断测试", "WARNING")
            return False
        except Exception as e:
            self.log(f"测试异常: {e}", "ERROR")
            return False

def main():
    """主函数"""
    print("🎯 简化版Python-硬件测试工具")
    print("无需外部依赖，基于Python标准库")
    print()
    
    # 获取设备ID
    if len(sys.argv) > 1:
        device_id = sys.argv[1]
    else:
        device_id = input("请输入设备MAC地址 (例如: 7c:2c:67:8d:89:78): ").strip()
        if not device_id:
            device_id = "7c:2c:67:8d:89:78"
    
    print(f"📱 使用设备ID: {device_id}")
    print()
    
    # 运行测试
    tester = SimpleHardwareTest(device_id)
    success = tester.run_test()
    
    print("\n🏁 测试完成")
    if success:
        print("🎉 基础测试通过！可以进行完整流程测试")
    else:
        print("❌ 部分测试未通过，请检查系统配置")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 MQTT SPEAK命令和ACK确认测试工具
测试完整的MQTT通信流程：发送SPEAK命令 → 等待ACK确认
"""

import paho.mqtt.client as mqtt
import json
import time
import sys
import uuid
import threading
from datetime import datetime
from typing import Dict, Any, Optional

class SpeakAckTester:
    def __init__(self, device_id="7c:2c:67:8d:89:78"):
        self.device_id = device_id
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.mqtt_username = "admin"
        self.mqtt_password = "Jyxd@2025"
        
        # MQTT连接状态
        self.connected = False
        self.subscribed = False
        
        # 测试状态
        self.test_results = {}
        self.ack_received = False
        self.ack_data = None
        self.start_time = None
        
        # 主题
        self.cmd_topic = f"device/{device_id}/cmd"
        self.ack_topic = f"device/{device_id}/ack"
        self.event_topic = f"device/{device_id}/event"
        
        # 同步锁
        self.test_lock = threading.Lock()
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        icons = {
            "INFO": "ℹ️", 
            "SUCCESS": "✅", 
            "ERROR": "❌", 
            "WARNING": "⚠️",
            "DEBUG": "🔍",
            "TEST": "🧪"
        }
        icon = icons.get(level, "📝")
        print(f"[{timestamp}] {icon} {message}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.log("MQTT连接成功!", "SUCCESS")
            self.log(f"连接标志: {flags}", "DEBUG")
            
            # 订阅ACK和事件主题
            self.log(f"🔄 订阅ACK主题: {self.ack_topic}")
            result1 = client.subscribe(self.ack_topic, 1)
            self.log(f"🔄 订阅事件主题: {self.event_topic}")
            result2 = client.subscribe(self.event_topic, 1)
            
            if result1[0] == 0 and result2[0] == 0:
                self.subscribed = True
                self.log("主题订阅成功!", "SUCCESS")
            else:
                self.log(f"主题订阅失败: ACK={result1}, Event={result2}", "ERROR")
        else:
            self.log(f"MQTT连接失败，错误代码: {rc}", "ERROR")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        self.log(f"MQTT断开连接，代码: {rc}", "WARNING")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        self.log(f"订阅确认: mid={mid}, qos={granted_qos}", "DEBUG")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            self.log(f"📥 收到消息:", "SUCCESS")
            self.log(f"   主题: {topic}")
            self.log(f"   内容: {payload}")
            
            # 解析消息
            try:
                data = json.loads(payload)
                
                if topic == self.ack_topic:
                    self.handle_ack_message(data)
                elif topic == self.event_topic:
                    self.handle_event_message(data)
                    
            except json.JSONDecodeError as e:
                self.log(f"JSON解析失败: {e}", "ERROR")
                
        except Exception as e:
            self.log(f"处理消息异常: {e}", "ERROR")

    def handle_ack_message(self, data: Dict[str, Any]):
        """处理ACK消息"""
        with self.test_lock:
            self.ack_received = True
            self.ack_data = data
            
            track_id = data.get("track_id")
            evt = data.get("evt")
            timestamp = data.get("timestamp")
            
            self.log("🎉 收到ACK确认!", "SUCCESS")
            self.log(f"   事件类型: {evt}")
            self.log(f"   Track ID: {track_id}")
            self.log(f"   时间戳: {timestamp}")
            
            # 计算响应时间
            if self.start_time:
                response_time = (time.time() - self.start_time) * 1000
                self.log(f"   响应时间: {response_time:.1f}ms", "SUCCESS")

    def handle_event_message(self, data: Dict[str, Any]):
        """处理事件消息"""
        evt = data.get("evt")
        track_id = data.get("track_id")
        timestamp = data.get("timestamp")
        
        self.log("📢 收到事件通知!", "SUCCESS")
        self.log(f"   事件类型: {evt}")
        self.log(f"   Track ID: {track_id}")
        self.log(f"   时间戳: {timestamp}")
        
        if evt == "EVT_SPEAK_DONE":
            self.log("🎵 硬件播放完成!", "SUCCESS")

    def send_speak_command(self, client, text="测试语音播放", track_id=None):
        """发送SPEAK命令"""
        if not track_id:
            track_id = f"TEST{int(time.time())}{uuid.uuid4().hex[:6]}"
        
        command = {
            "cmd": "SPEAK",
            "text": text,
            "track_id": track_id,
            "audio_url": "ws://172.20.12.204:8888/xiaozhi/v1/"
        }
        
        self.log(f"📤 发送SPEAK命令:", "TEST")
        self.log(f"   Track ID: {track_id}")
        self.log(f"   文本内容: {text}")
        self.log(f"   主题: {self.cmd_topic}")
        
        # 记录开始时间
        self.start_time = time.time()
        
        # 发送消息
        result = client.publish(self.cmd_topic, json.dumps(command, ensure_ascii=False), qos=1)
        
        if result.rc == 0:
            self.log("✅ SPEAK命令发送成功!", "SUCCESS")
            return track_id
        else:
            self.log(f"❌ SPEAK命令发送失败: {result.rc}", "ERROR")
            return None

    def run_test(self, test_text="你好！这是MQTT SPEAK测试消息", timeout=30):
        """运行完整测试"""
        try:
            self.log("🚀 启动MQTT SPEAK和ACK测试...", "TEST")
            self.log(f"📡 MQTT服务器: {self.mqtt_host}:{self.mqtt_port}")
            self.log(f"👤 认证: {self.mqtt_username} / {'*' * len(self.mqtt_password)}")
            self.log(f"📱 设备ID: {self.device_id}")
            self.log(f"🎯 测试内容: {test_text}")
            self.log(f"⏱️ 超时时间: {timeout}秒")
            print()
            
            # 创建MQTT客户端
            client_id = f"speak_test_{int(time.time())}"
            client = mqtt.Client(client_id=client_id)
            client.username_pw_set(self.mqtt_username, self.mqtt_password)
            
            # 设置回调
            client.on_connect = self.on_connect
            client.on_disconnect = self.on_disconnect
            client.on_message = self.on_message
            client.on_subscribe = self.on_subscribe
            
            # 连接MQTT服务器
            self.log(f"🔗 连接MQTT服务器... (客户端ID: {client_id})")
            client.connect(self.mqtt_host, self.mqtt_port, 60)
            client.loop_start()
            
            # 等待连接和订阅
            connect_timeout = 10
            start_time = time.time()
            while (not self.connected or not self.subscribed) and (time.time() - start_time) < connect_timeout:
                time.sleep(0.1)
            
            if not self.connected:
                self.log("❌ MQTT连接超时", "ERROR")
                return False
            
            if not self.subscribed:
                self.log("❌ 主题订阅超时", "ERROR")
                return False
            
            # 等待2秒确保订阅生效
            self.log("⏳ 等待2秒确保订阅生效...")
            time.sleep(2)
            
            # 发送SPEAK命令
            track_id = self.send_speak_command(client, test_text)
            if not track_id:
                return False
            
            # 等待ACK响应
            self.log(f"⏰ 等待ACK确认... (最多{timeout}秒)")
            
            wait_start = time.time()
            while not self.ack_received and (time.time() - wait_start) < timeout:
                time.sleep(0.5)
                
                # 显示等待进度
                elapsed = time.time() - wait_start
                if int(elapsed) % 10 == 0 and elapsed > 0:
                    remaining = timeout - elapsed
                    self.log(f"⏳ 仍在等待ACK... 剩余{remaining:.0f}秒")
            
            # 等待额外5秒看是否有事件消息
            if self.ack_received:
                self.log("⏳ 等待5秒查看是否有播放完成事件...")
                time.sleep(5)
            
            client.loop_stop()
            client.disconnect()
            
            # 生成测试报告
            self.generate_report(track_id, timeout)
            
            return self.ack_received
            
        except Exception as e:
            self.log(f"❌ 测试异常: {e}", "ERROR")
            return False

    def generate_report(self, track_id, timeout):
        """生成测试报告"""
        print("\n" + "=" * 80)
        print("📊 MQTT SPEAK和ACK测试报告")
        print("=" * 80)
        
        print(f"📱 测试设备: {self.device_id}")
        print(f"🎯 Track ID: {track_id}")
        print(f"📡 MQTT服务器: {self.mqtt_host}:{self.mqtt_port}")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 测试结果
        print("🔍 测试结果:")
        print(f"  ✅ 1️⃣ MQTT连接: {'通过' if self.connected else '失败'}")
        print(f"  ✅ 2️⃣ 主题订阅: {'通过' if self.subscribed else '失败'}")
        print(f"  {'✅' if self.ack_received else '❌'} 3️⃣ SPEAK命令发送: 通过")
        print(f"  {'✅' if self.ack_received else '❌'} 4️⃣ ACK确认接收: {'通过' if self.ack_received else '失败'}")
        
        if self.ack_received and self.ack_data:
            print(f"  📋 ACK数据: {self.ack_data}")
            
            if self.start_time:
                response_time = (time.time() - self.start_time) * 1000
                print(f"  ⏱️ 响应时间: {response_time:.1f}ms")
        
        print()
        
        # 结论
        if self.ack_received:
            print("🎉 测试成功! 硬件MQTT连接正常，能够接收命令并发送ACK确认")
            print("💡 说明硬件与MQTT服务器通信正常")
        else:
            print("❌ 测试失败! 未收到ACK确认")
            print("🔧 可能原因:")
            print("   1. 硬件未连接到MQTT服务器")
            print("   2. 硬件无法接收MQTT消息")
            print("   3. 硬件无法发送ACK响应")
            print("   4. 网络连接问题")
        
        print("=" * 80)

def main():
    device_id = "7c:2c:67:8d:89:78"
    test_text = "你好！这是MQTT SPEAK和ACK测试"
    timeout = 60
    
    if len(sys.argv) > 1:
        device_id = sys.argv[1]
    if len(sys.argv) > 2:
        test_text = sys.argv[2]
    if len(sys.argv) > 3:
        timeout = int(sys.argv[3])
    
    print("🔧 MQTT SPEAK命令和ACK确认测试工具")
    print("=" * 80)
    print(f"📱 设备ID: {device_id}")
    print(f"🎯 测试内容: {test_text}")
    print(f"⏱️ 超时时间: {timeout}秒")
    print("🎯 功能: 发送SPEAK命令，等待硬件ACK确认")
    print()
    
    tester = SpeakAckTester(device_id)
    success = tester.run_test(test_text, timeout)
    
    exit_code = 0 if success else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 直接MQTT消息发送测试
绕过Python服务，直接发送MQTT消息测试调试工具是否能接收
"""

import paho.mqtt.client as mqtt
import json
import time
import sys
from datetime import datetime

class DirectMQTTTest:
    def __init__(self, device_id="7c:2c:67:8d:89:78"):
        self.device_id = device_id
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.mqtt_username = "admin"
        self.mqtt_password = "Jyxd@2025"
        self.connected = False
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
        icon = icons.get(level, "📝")
        print(f"[{timestamp}] {icon} {message}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.log("MQTT连接成功!", "SUCCESS")
        else:
            self.log(f"MQTT连接失败，错误代码: {rc}", "ERROR")

    def on_publish(self, client, userdata, mid):
        self.log(f"消息发布成功: mid={mid}", "SUCCESS")

    def send_test_message(self):
        """发送测试消息"""
        try:
            self.log("🚀 启动直接MQTT测试...")
            self.log(f"📡 服务器: {self.mqtt_host}:{self.mqtt_port}")
            self.log(f"📱 设备ID: {self.device_id}")
            
            # 创建客户端
            client_id = f"direct_test_{int(time.time())}"
            client = mqtt.Client(client_id=client_id)
            client.username_pw_set(self.mqtt_username, self.mqtt_password)
            
            client.on_connect = self.on_connect
            client.on_publish = self.on_publish
            
            # 连接MQTT服务器
            self.log(f"🔗 连接MQTT服务器... (客户端ID: {client_id})")
            client.connect(self.mqtt_host, self.mqtt_port, 60)
            client.loop_start()
            
            # 等待连接
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                self.log("连接超时", "ERROR")
                return False
            
            # 发送多个测试消息
            topic = f"device/{self.device_id}/cmd"
            
            test_messages = [
                {
                    "cmd": "SPEAK",
                    "text": "直接MQTT测试消息1 - 您好！",
                    "track_id": f"TEST{int(time.time())}_1"
                },
                {
                    "cmd": "SPEAK", 
                    "text": "直接MQTT测试消息2 - 今天吃药了吗？",
                    "track_id": f"TEST{int(time.time())}_2"
                },
                {
                    "cmd": "TEST",
                    "text": "直接MQTT测试消息3 - 简单测试",
                    "track_id": f"TEST{int(time.time())}_3"
                }
            ]
            
            self.log(f"📤 准备发送 {len(test_messages)} 条测试消息到主题: {topic}")
            
            for i, message in enumerate(test_messages, 1):
                self.log(f"🔄 发送消息 {i}: {message['text'][:30]}...")
                
                result = client.publish(topic, json.dumps(message, ensure_ascii=False))
                
                if result.rc == 0:
                    self.log(f"   ✅ 消息 {i} 发送成功", "SUCCESS")
                else:
                    self.log(f"   ❌ 消息 {i} 发送失败: {result.rc}", "ERROR")
                
                time.sleep(1)  # 间隔1秒
            
            # 等待消息发送完成
            self.log("⏳ 等待消息发送完成...")
            time.sleep(3)
            
            client.loop_stop()
            client.disconnect()
            
            self.log("🏁 直接MQTT测试完成！", "SUCCESS")
            self.log("💡 检查MQTT调试工具是否收到消息", "INFO")
            
            return True
            
        except Exception as e:
            self.log(f"❌ 测试异常: {e}", "ERROR")
            return False

def main():
    device_id = "7c:2c:67:8d:89:78"
    if len(sys.argv) > 1:
        device_id = sys.argv[1]
    
    print("🚀 直接MQTT消息发送测试")
    print("=" * 60)
    print(f"📱 设备ID: {device_id}")
    print("🎯 功能: 直接发送MQTT消息，测试调试工具接收")
    print("💡 请确保 mqtt_debug.py 正在运行")
    print()
    
    tester = DirectMQTTTest(device_id)
    success = tester.send_test_message()
    
    if success:
        print("\n✅ 如果MQTT调试工具收到消息，说明MQTT通信正常")
        print("❌ 如果没收到消息，说明有网络或配置问题")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

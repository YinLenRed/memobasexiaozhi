#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 快速MQTT连接测试
验证MQTT服务器连接和基本功能
"""

import paho.mqtt.client as mqtt
import json
import time
import sys
from datetime import datetime

class QuickMQTTTest:
    def __init__(self, device_id="7c:2c:67:8d:89:78"):
        self.device_id = device_id
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.mqtt_username = "admin"
        self.mqtt_password = "Jyxd@2025"
        
        self.connected = False
        self.message_received = False
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
        icon = icons.get(level, "📝")
        print(f"[{timestamp}] {icon} {message}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.log("MQTT连接成功!", "SUCCESS")
            
            # 订阅命令主题
            cmd_topic = f"device/{self.device_id}/cmd"
            result = client.subscribe(cmd_topic)
            if result[0] == 0:
                self.log(f"订阅主题成功: {cmd_topic}", "SUCCESS")
            else:
                self.log(f"订阅主题失败: {result}", "ERROR")
        else:
            self.log(f"MQTT连接失败，错误代码: {rc}", "ERROR")
            error_messages = {
                1: "协议版本不正确",
                2: "客户端ID无效", 
                3: "服务器不可用",
                4: "用户名或密码错误",
                5: "未授权"
            }
            if rc in error_messages:
                self.log(f"错误详情: {error_messages[rc]}", "ERROR")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            self.log("MQTT意外断开连接", "WARNING")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            self.log(f"收到消息! 主题: {topic}", "SUCCESS")
            self.log(f"消息内容: {payload}", "INFO")
            
            # 解析命令
            try:
                command = json.loads(payload)
                cmd = command.get("cmd")
                text = command.get("text", "")
                track_id = command.get("track_id", "")
                
                self.log(f"命令类型: {cmd}", "INFO")
                self.log(f"文本内容: {text}", "INFO")
                self.log(f"Track ID: {track_id}", "INFO")
                
                self.message_received = True
                
                # 发送ACK
                if track_id:
                    self.send_ack(client, track_id)
                    
            except json.JSONDecodeError as e:
                self.log(f"JSON解析失败: {e}", "ERROR")
                
        except Exception as e:
            self.log(f"处理消息异常: {e}", "ERROR")

    def send_ack(self, client, track_id):
        try:
            ack_topic = f"device/{self.device_id}/ack"
            ack_data = {
                "track_id": track_id,
                "status": "received",
                "timestamp": int(time.time() * 1000),
                "device_id": self.device_id
            }
            
            result = client.publish(ack_topic, json.dumps(ack_data))
            if result.rc == 0:
                self.log(f"ACK发送成功: {track_id}", "SUCCESS")
            else:
                self.log(f"ACK发送失败: {result.rc}", "ERROR")
                
        except Exception as e:
            self.log(f"发送ACK异常: {e}", "ERROR")

    def run_test(self, duration=30):
        try:
            self.log("🚀 开始MQTT连接测试...")
            self.log(f"📡 MQTT服务器: {self.mqtt_host}:{self.mqtt_port}")
            self.log(f"👤 用户名: {self.mqtt_username}")
            self.log(f"📱 设备ID: {self.device_id}")
            print()
            
            # 创建MQTT客户端
            client = mqtt.Client(client_id=f"test_client_{self.device_id}")
            client.username_pw_set(self.mqtt_username, self.mqtt_password)
            
            # 设置回调
            client.on_connect = self.on_connect
            client.on_disconnect = self.on_disconnect  
            client.on_message = self.on_message
            
            # 连接服务器
            self.log("🔗 正在连接MQTT服务器...")
            client.connect(self.mqtt_host, self.mqtt_port, 60)
            client.loop_start()
            
            # 等待连接建立
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                self.log("❌ MQTT连接超时", "ERROR")
                return False
            
            # 运行监听
            self.log(f"👂 开始监听消息 ({duration}秒)...")
            self.log("💡 提示: 在另一个终端运行健康提醒测试", "INFO")
            self.log("🔗 命令: python test_health_reminder.py 7c:2c:67:8d:89:78", "INFO")
            print()
            
            start_time = time.time()
            while (time.time() - start_time) < duration:
                if self.message_received:
                    self.log("🎉 消息接收测试成功!", "SUCCESS")
                    break
                    
                elapsed = time.time() - start_time
                if int(elapsed) % 10 == 0 and elapsed > 0:
                    remaining = duration - elapsed
                    self.log(f"⏰ 等待消息中... 剩余: {remaining:.0f}s", "INFO")
                
                time.sleep(1)
            
            client.loop_stop()
            client.disconnect()
            
            # 结果总结
            print("\n" + "=" * 60)
            print("📊 MQTT测试结果")
            print("=" * 60)
            
            if self.connected:
                print("✅ MQTT连接: 成功")
            else:
                print("❌ MQTT连接: 失败")
                
            if self.message_received:
                print("✅ 消息接收: 成功") 
                print("🎉 MQTT功能完全正常!")
            else:
                print("❌ 消息接收: 超时")
                print("⚠️ 请检查是否发送了测试命令")
            
            print("=" * 60)
            
            return self.connected and self.message_received
            
        except Exception as e:
            self.log(f"❌ 测试异常: {e}", "ERROR")
            return False

def main():
    device_id = "7c:2c:67:8d:89:78"
    if len(sys.argv) > 1:
        device_id = sys.argv[1]
    
    print("🔧 快速MQTT连接测试")
    print("=" * 50)
    print(f"📱 设备ID: {device_id}")
    print()
    
    tester = QuickMQTTTest(device_id)
    success = tester.run_test(60)  # 60秒测试
    
    exit_code = 0 if success else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 详细MQTT调试工具
监控所有MQTT流量，诊断消息传递问题
"""

import paho.mqtt.client as mqtt
import json
import time
import sys
from datetime import datetime

class MQTTDebugger:
    def __init__(self, device_id="7c:2c:67:8d:89:78"):
        self.device_id = device_id
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.mqtt_username = "admin"
        self.mqtt_password = "Jyxd@2025"
        
        self.connected = False
        self.message_count = 0
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️", "DEBUG": "🔍"}
        icon = icons.get(level, "📝")
        print(f"[{timestamp}] {icon} {message}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.log("MQTT连接成功!", "SUCCESS")
            self.log(f"连接标志: {flags}", "DEBUG")
            
            # 订阅多个主题进行调试
            topics = [
                f"device/{self.device_id}/cmd",
                f"device/{self.device_id}/ack", 
                f"device/{self.device_id}/event",
                f"device/+/cmd",  # 通配符：所有设备的命令
                "#"  # 通配符：所有主题
            ]
            
            for topic in topics:
                result = client.subscribe(topic)
                if result[0] == 0:
                    self.log(f"订阅成功: {topic}", "SUCCESS")
                else:
                    self.log(f"订阅失败: {topic} -> {result}", "ERROR")
        else:
            self.log(f"MQTT连接失败，错误代码: {rc}", "ERROR")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        self.log(f"MQTT断开连接，代码: {rc}", "WARNING")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        self.log(f"订阅确认: mid={mid}, qos={granted_qos}", "DEBUG")

    def on_message(self, client, userdata, msg):
        try:
            self.message_count += 1
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            qos = msg.qos
            retain = msg.retain
            
            self.log(f"🎯 消息 #{self.message_count}", "SUCCESS")
            self.log(f"   主题: {topic}", "INFO")
            self.log(f"   QoS: {qos}, Retain: {retain}", "DEBUG")
            self.log(f"   长度: {len(payload)} 字节", "DEBUG")
            self.log(f"   内容: {payload[:200]}{'...' if len(payload) > 200 else ''}", "INFO")
            
            # 尝试解析JSON
            try:
                data = json.loads(payload)
                self.log(f"   JSON解析成功:", "DEBUG")
                for key, value in data.items():
                    self.log(f"     {key}: {value}", "DEBUG")
            except:
                self.log(f"   非JSON格式", "DEBUG")
            
            # 如果是目标设备的命令，发送ACK
            if topic == f"device/{self.device_id}/cmd":
                try:
                    command = json.loads(payload)
                    track_id = command.get("track_id")
                    if track_id:
                        self.send_ack(client, track_id)
                except:
                    pass
            
            print()  # 空行分隔
                
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
            
            self.log(f"🔄 发送ACK: {track_id}", "INFO")
            result = client.publish(ack_topic, json.dumps(ack_data))
            if result.rc == 0:
                self.log(f"   ACK发送成功", "SUCCESS")
            else:
                self.log(f"   ACK发送失败: {result.rc}", "ERROR")
                
        except Exception as e:
            self.log(f"发送ACK异常: {e}", "ERROR")

    def on_publish(self, client, userdata, mid):
        self.log(f"消息发布成功: mid={mid}", "DEBUG")

    def on_log(self, client, userdata, level, buf):
        # MQTT客户端内部日志
        log_levels = {
            mqtt.MQTT_LOG_INFO: "INFO",
            mqtt.MQTT_LOG_NOTICE: "INFO", 
            mqtt.MQTT_LOG_WARNING: "WARNING",
            mqtt.MQTT_LOG_ERR: "ERROR",
            mqtt.MQTT_LOG_DEBUG: "DEBUG"
        }
        log_level = log_levels.get(level, "DEBUG")
        self.log(f"MQTT内部: {buf}", log_level)

    def run_debug(self, duration=120):
        try:
            self.log("🔍 启动详细MQTT调试...")
            self.log(f"📡 服务器: {self.mqtt_host}:{self.mqtt_port}")
            self.log(f"👤 认证: {self.mqtt_username} / {'*' * len(self.mqtt_password)}")
            self.log(f"📱 设备ID: {self.device_id}")
            self.log(f"⏱️ 调试时长: {duration}秒")
            print()
            
            # 创建MQTT客户端 - 使用唯一ID避免冲突
            client_id = f"mqtt_debugger_{int(time.time())}"
            client = mqtt.Client(client_id=client_id)
            client.username_pw_set(self.mqtt_username, self.mqtt_password)
            
            # 设置所有回调
            client.on_connect = self.on_connect
            client.on_disconnect = self.on_disconnect
            client.on_message = self.on_message
            client.on_subscribe = self.on_subscribe
            client.on_publish = self.on_publish
            client.on_log = self.on_log
            
            # 启用日志
            client.enable_logger()
            
            self.log(f"🔗 连接MQTT服务器... (客户端ID: {client_id})")
            client.connect(self.mqtt_host, self.mqtt_port, 60)
            client.loop_start()
            
            # 等待连接
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                self.log("❌ 连接超时", "ERROR")
                return False
            
            self.log("🎧 开始监听所有MQTT流量...")
            self.log("💡 现在在另一个终端运行测试命令:", "INFO")
            self.log("   python test_health_reminder.py 7c:2c:67:8d:89:78", "INFO")
            print()
            
            # 监听指定时间
            start_time = time.time()
            last_status_time = start_time
            
            while (time.time() - start_time) < duration:
                current_time = time.time()
                
                # 每30秒显示状态
                if (current_time - last_status_time) >= 30:
                    elapsed = current_time - start_time
                    remaining = duration - elapsed
                    self.log(f"📊 状态: 已接收 {self.message_count} 条消息, 剩余 {remaining:.0f}s", "INFO")
                    last_status_time = current_time
                
                time.sleep(1)
            
            client.loop_stop()
            client.disconnect()
            
            # 结果总结
            print("\n" + "=" * 80)
            print("🔍 MQTT调试总结")
            print("=" * 80)
            print(f"📊 总接收消息: {self.message_count} 条")
            print(f"🔗 连接状态: {'成功' if self.connected else '失败'}")
            
            if self.message_count == 0:
                print("❌ 未接收到任何消息")
                print("🔧 可能原因:")
                print("   1. 没有发送测试命令")
                print("   2. 主题配置不匹配")
                print("   3. MQTT权限问题")
                print("   4. 网络连接问题")
            else:
                print("✅ 接收到消息，MQTT通信正常")
            
            print("=" * 80)
            
            return self.message_count > 0
            
        except Exception as e:
            self.log(f"❌ 调试异常: {e}", "ERROR")
            return False

def main():
    device_id = "7c:2c:67:8d:89:78"
    if len(sys.argv) > 1:
        device_id = sys.argv[1]
    
    print("🔍 详细MQTT调试工具")
    print("=" * 60)
    print(f"📱 设备ID: {device_id}")
    print("🎯 功能: 监控所有MQTT流量，诊断消息传递问题")
    print()
    
    debugger = MQTTDebugger(device_id)
    success = debugger.run_debug(120)  # 2分钟调试
    
    exit_code = 0 if success else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main()

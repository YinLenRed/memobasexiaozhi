#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ 快速MQTT SPEAK测试工具
简化版本，快速测试硬件是否能接收SPEAK命令并返回ACK
"""

import paho.mqtt.client as mqtt
import json
import time
import sys
from datetime import datetime

# 全局状态
connected = False
ack_received = False
start_time = None
device_id = "7c:2c:67:8d:89:78"

def log(message, level="INFO"):
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
    icon = icons.get(level, "📝")
    print(f"[{timestamp}] {icon} {message}")

def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        connected = True
        log("MQTT连接成功!", "SUCCESS")
        
        # 订阅ACK主题
        ack_topic = f"device/{device_id}/ack"
        event_topic = f"device/{device_id}/event"
        
        client.subscribe(ack_topic, 1)
        client.subscribe(event_topic, 1)
        log(f"订阅主题: {ack_topic}, {event_topic}")
    else:
        log(f"MQTT连接失败: {rc}", "ERROR")

def on_message(client, userdata, msg):
    global ack_received, start_time
    
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        
        log(f"📥 收到消息: {topic}")
        log(f"   内容: {payload}")
        
        if "ack" in topic and "track_id" in data:
            ack_received = True
            response_time = (time.time() - start_time) * 1000 if start_time else 0
            log(f"🎉 收到ACK确认! 响应时间: {response_time:.1f}ms", "SUCCESS")
        elif "event" in topic:
            log(f"📢 收到事件: {data.get('evt')}", "SUCCESS")
            
    except Exception as e:
        log(f"处理消息异常: {e}", "ERROR")

def send_speak_command(client):
    global start_time
    
    cmd_topic = f"device/{device_id}/cmd"
    track_id = f"QUICK{int(time.time())}"
    
    command = {
        "cmd": "SPEAK",
        "text": "快速测试：你好！",
        "track_id": track_id,
        "audio_url": "ws://47.98.51.180:8000/xiaozhi/v1/"
    }
    
    log(f"📤 发送SPEAK命令到: {cmd_topic}")
    log(f"   Track ID: {track_id}")
    
    start_time = time.time()
    result = client.publish(cmd_topic, json.dumps(command, ensure_ascii=False), qos=1)
    
    if result.rc == 0:
        log("✅ SPEAK命令发送成功!", "SUCCESS")
        return True
    else:
        log(f"❌ SPEAK命令发送失败: {result.rc}", "ERROR")
        return False

def main():
    global device_id
    
    if len(sys.argv) > 1:
        device_id = sys.argv[1]
    
    print("⚡ 快速MQTT SPEAK测试")
    print("=" * 50)
    print(f"📱 设备ID: {device_id}")
    print(f"📡 MQTT: 47.97.185.142:1883")
    print()
    
    # 创建MQTT客户端（兼容新版本paho-mqtt）
    try:
        # 尝试新版本API（paho-mqtt >= 2.0）
        client = mqtt.Client(client_id=f"quick_test_{int(time.time())}", callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        # 回退到旧版本API
        client = mqtt.Client(f"quick_test_{int(time.time())}")
    client.username_pw_set("admin", "Jyxd@2025")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        # 连接
        log("🔗 连接MQTT服务器...")
        client.connect("47.97.185.142", 1883, 60)
        client.loop_start()
        
        # 等待连接
        timeout = 10
        while not connected and timeout > 0:
            time.sleep(1)
            timeout -= 1
        
        if not connected:
            log("❌ 连接超时", "ERROR")
            return False
        
        # 等待订阅生效
        time.sleep(2)
        
        # 发送命令
        if send_speak_command(client):
            # 等待ACK
            log("⏰ 等待ACK确认 (30秒)...")
            
            timeout = 30
            while not ack_received and timeout > 0:
                time.sleep(1)
                timeout -= 1
                
                if timeout % 10 == 0:
                    log(f"⏳ 还在等待... 剩余{timeout}秒")
        
        client.loop_stop()
        client.disconnect()
        
        # 结果
        print("\n" + "=" * 50)
        if ack_received:
            print("🎉 测试成功! 硬件MQTT通信正常")
            print("✅ 硬件能够接收SPEAK命令并返回ACK")
        else:
            print("❌ 测试失败! 未收到ACK确认")
            print("🔧 硬件可能无法连接MQTT或无法处理命令")
        print("=" * 50)
        
        return ack_received
        
    except Exception as e:
        log(f"❌ 测试异常: {e}", "ERROR")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

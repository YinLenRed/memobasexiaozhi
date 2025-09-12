#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 MQTT主题差异测试脚本
验证/cmd和/command主题的不同响应
"""

import paho.mqtt.client as mqtt
import json
import time
import sys
from datetime import datetime

def log(message, level="INFO"):
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
    icon = icons.get(level, "📝")
    print(f"[{timestamp}] {icon} {message}")

def test_topic(device_id, topic_suffix):
    """测试指定主题后缀"""
    log(f"🧪 测试主题: device/{device_id}/{topic_suffix}")
    
    connected = False
    ack_received = False
    
    def on_connect(client, userdata, flags, rc):
        nonlocal connected
        if rc == 0:
            connected = True
            log(f"MQTT连接成功", "SUCCESS")
            
            # 订阅ACK主题
            ack_topic = f"device/{device_id}/ack"
            client.subscribe(ack_topic, 1)
            log(f"订阅: {ack_topic}")
        else:
            log(f"MQTT连接失败: {rc}", "ERROR")

    def on_message(client, userdata, msg):
        nonlocal ack_received
        try:
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)
            
            if "ack" in msg.topic and "track_id" in data:
                ack_received = True
                log(f"🎉 收到ACK: {data.get('track_id')}", "SUCCESS")
        except Exception as e:
            log(f"处理消息异常: {e}", "ERROR")

    # 创建MQTT客户端
    client_id = f"topic_test_{int(time.time())}"
    try:
        client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        client = mqtt.Client(client_id)
    
    client.username_pw_set("admin", "Jyxd@2025")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        # 连接MQTT
        client.connect("47.97.185.142", 1883, 60)
        client.loop_start()
        
        # 等待连接
        timeout = 10
        while not connected and timeout > 0:
            time.sleep(1)
            timeout -= 1
        
        if not connected:
            log("连接超时", "ERROR")
            return False
        
        # 等待订阅生效
        time.sleep(2)
        
        # 发送测试命令
        cmd_topic = f"device/{device_id}/{topic_suffix}"
        track_id = f"TOPIC_TEST_{topic_suffix.upper()}_{int(time.time())}"
        
        command = {
            "cmd": "SPEAK",
            "text": f"主题测试: {topic_suffix}",
            "track_id": track_id,
            "audio_url": "ws://47.98.51.180:8000/xiaozhi/v1/"
        }
        
        log(f"📤 发送命令到: {cmd_topic}")
        log(f"   Track ID: {track_id}")
        
        start_time = time.time()
        result = client.publish(cmd_topic, json.dumps(command, ensure_ascii=False), qos=1)
        
        if result.rc == 0:
            log("命令发送成功", "SUCCESS")
        else:
            log(f"命令发送失败: {result.rc}", "ERROR")
            return False
        
        # 等待ACK
        log("⏰ 等待ACK (15秒)...")
        timeout = 15
        while not ack_received and timeout > 0:
            time.sleep(1)
            timeout -= 1
        
        if ack_received:
            response_time = (time.time() - start_time) * 1000
            log(f"✅ ACK响应成功! 用时: {response_time:.1f}ms", "SUCCESS")
            return True
        else:
            log("❌ 未收到ACK响应", "ERROR")
            return False
    
    except Exception as e:
        log(f"测试异常: {e}", "ERROR")
        return False
    
    finally:
        client.loop_stop()
        client.disconnect()

def main():
    if len(sys.argv) < 2:
        print("用法: python test_topic_difference.py <device_id>")
        print("示例: python test_topic_difference.py 7c:2c:67:8d:89:78")
        sys.exit(1)
    
    device_id = sys.argv[1]
    
    print("🔍 MQTT主题差异测试")
    print("=" * 50)
    print(f"📱 设备ID: {device_id}")
    print()
    
    # 测试两个主题
    results = {}
    
    print("🧪 测试1: /cmd 主题")
    print("-" * 30)
    results['cmd'] = test_topic(device_id, 'cmd')
    print()
    
    print("🧪 测试2: /command 主题")
    print("-" * 30)
    results['command'] = test_topic(device_id, 'command')
    print()
    
    # 结果总结
    print("=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)
    
    for topic, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"📡 device/{device_id}/{topic:<8} : {status}")
    
    print()
    if results['cmd'] and not results['command']:
        print("🎯 结论: 硬件只订阅了 /cmd 主题")
        print("💡 建议: 让硬件同时订阅 /command 主题")
    elif results['command'] and not results['cmd']:
        print("🎯 结论: 硬件只订阅了 /command 主题")
        print("💡 建议: 修改测试脚本使用 /command 主题")
    elif results['cmd'] and results['command']:
        print("🎯 结论: 硬件订阅了两个主题")
        print("✅ 配置正确，API和测试脚本都能正常工作")
    else:
        print("🎯 结论: 硬件可能离线或有其他问题")
        print("🔧 建议: 检查硬件连接状态")

if __name__ == "__main__":
    main()

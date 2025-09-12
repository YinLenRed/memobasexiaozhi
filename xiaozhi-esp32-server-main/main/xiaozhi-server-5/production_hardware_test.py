#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境硬件测试脚本
测试硬件连接真实的小智主服务进行音频播放
"""

import paho.mqtt.client as mqtt
import json
import time
import sys
import argparse
from datetime import datetime
import uuid

class ProductionHardwareTest:
    def __init__(self, device_id="7c:2c:67:8d:89:78", environment="production"):
        self.device_id = device_id
        self.environment = environment
        
        # 环境配置
        if environment == "production":
            self.ws_host = "47.98.51.180"
            self.ws_port = 8000
            self.test_description = "连接生产环境的小智主服务"
        else:  # test
            self.ws_host = "172.20.12.204"  
            self.ws_port = 8888
            self.test_description = "连接测试环境的模拟服务"
        
        # 服务器配置
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        
        # 测试状态跟踪
        self.test_results = {
            "mqtt_connection": False,
            "speak_command_sent": False,
            "ack_received": False,
            "websocket_test": False,
            "event_received": False,
            "flow_completed": False
        }
        
        # 流程跟踪
        self.current_track_id = None
        self.mqtt_client = None
        self.start_time = None
        self.ack_time = None
        self.completion_time = None
    
    def log(self, message, level="INFO"):
        """带时间戳和级别的日志"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️", "DEBUG": "🔍"}
        icon = icons.get(level, "📝")
        print(f"[{timestamp}] {icon} {message}")
    
    def setup_mqtt(self):
        """设置MQTT客户端"""
        client_id = f"prod_test_{int(time.time())}"
        self.mqtt_client = mqtt.Client(
            client_id=client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        
        def on_connect(client, userdata, flags, rc, properties=None):
            if rc == 0:
                self.log("MQTT连接成功", "SUCCESS")
                self.test_results["mqtt_connection"] = True
                
                # 订阅设备的ACK和EVENT主题
                ack_topic = f"device/{self.device_id}/ack"
                event_topic = f"device/{self.device_id}/event"
                
                client.subscribe(ack_topic)
                client.subscribe(event_topic)
                self.log(f"📡 订阅主题: {ack_topic}, {event_topic}")
            else:
                self.log(f"MQTT连接失败，返回码: {rc}", "ERROR")
        
        def on_message(client, userdata, msg):
            try:
                topic = msg.topic
                message = json.loads(msg.payload.decode())
                
                if "/ack" in topic:
                    self.handle_ack_message(message)
                elif "/event" in topic:
                    self.handle_event_message(message)
                    
            except json.JSONDecodeError as e:
                self.log(f"JSON解析失败: {e}", "ERROR")
        
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = on_message
        
        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            self.log(f"MQTT连接异常: {e}", "ERROR")
            return False
    
    def handle_ack_message(self, message):
        """处理硬件ACK消息"""
        track_id = message.get("track_id")
        event_type = message.get("evt")
        
        self.log(f"📥 收到ACK: {message}")
        
        if track_id == self.current_track_id and event_type == "CMD_RECEIVED":
            self.ack_time = time.time()
            self.test_results["ack_received"] = True
            self.log("✅ ACK确认成功！硬件已收到SPEAK命令", "SUCCESS")
            self.log(f"🌐 硬件将连接: ws://{self.ws_host}:{self.ws_port}/xiaozhi/v1/", "INFO")
        else:
            self.log(f"⚠️ ACK消息异常: track_id={track_id}, evt={event_type}", "WARNING")
    
    def handle_event_message(self, message):
        """处理硬件EVENT消息"""
        track_id = message.get("track_id")
        event_type = message.get("evt")
        
        self.log(f"📥 收到EVENT: {message}")
        
        if track_id == self.current_track_id:
            if event_type == "EVT_SPEAK_DONE":
                self.completion_time = time.time()
                self.test_results["event_received"] = True
                self.test_results["flow_completed"] = True
                self.log("🎉 播放完成事件收到！", "SUCCESS")
            elif event_type == "EVT_WEBSOCKET_CONNECTED":
                self.test_results["websocket_test"] = True
                self.log("🔗 硬件WebSocket连接成功！", "SUCCESS")
            elif event_type == "EVT_AUDIO_RECEIVED":
                self.log("🎵 硬件已接收音频数据", "SUCCESS")
            elif event_type == "EVT_AUDIO_PLAYING":
                self.log("🔊 硬件开始播放音频", "SUCCESS")
        else:
            self.log(f"⚠️ EVENT消息异常: track_id={track_id}, evt={event_type}", "WARNING")
    
    def send_speak_command(self):
        """发送SPEAK命令给硬件"""
        if not self.mqtt_client or not self.test_results["mqtt_connection"]:
            self.log("MQTT未连接，无法发送命令", "ERROR")
            return False
        
        # 生成唯一的track_id
        self.current_track_id = f"PROD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"
        cmd_topic = f"device/{self.device_id}/cmd"
        
        # 构建SPEAK命令
        if self.environment == "production":
            text = "生产环境测试：连接小智主服务获取真实TTS音频并播放。"
        else:
            text = "测试环境验证：连接测试服务获取模拟音频数据。"
        
        speak_command = {
            "type": "SPEAK",
            "track_id": self.current_track_id,
            "text": text,
            "timestamp": datetime.now().isoformat() + "Z",
            "audio_url": f"ws://{self.ws_host}:{self.ws_port}/xiaozhi/v1/",
            "expected_duration": 15,
            "environment": self.environment,  # 告诉硬件当前环境
            "test_mode": False if self.environment == "production" else True
        }
        
        try:
            self.mqtt_client.publish(cmd_topic, json.dumps(speak_command))
            self.start_time = time.time()
            self.test_results["speak_command_sent"] = True
            self.log(f"📤 发送SPEAK命令: track_id={self.current_track_id}", "SUCCESS")
            self.log(f"🎯 环境: {self.environment}")
            self.log(f"💬 命令内容: {text}")
            self.log(f"🌐 WebSocket地址: ws://{self.ws_host}:{self.ws_port}/xiaozhi/v1/")
            return True
        except Exception as e:
            self.log(f"发送SPEAK命令失败: {e}", "ERROR")
            return False
    
    def wait_for_completion(self, timeout=60):
        """等待测试完成"""
        self.log(f"⏰ 等待测试完成（最多{timeout}秒）...")
        
        start_wait = time.time()
        while time.time() - start_wait < timeout:
            if self.test_results["flow_completed"]:
                self.log("✅ 流程测试完成！", "SUCCESS")
                return True
            
            time.sleep(0.5)
        
        self.log("⏰ 等待超时", "WARNING")
        return False
    
    def print_test_results(self):
        """打印详细测试结果"""
        print("\n" + "=" * 60)
        print(f"📊 {'生产环境' if self.environment == 'production' else '测试环境'}硬件测试结果")
        print("=" * 60)
        
        # 基本信息
        print(f"📱 测试设备: {self.device_id}")
        print(f"🎯 测试环境: {self.environment}")
        print(f"🎯 Track ID: {self.current_track_id}")
        print(f"🌐 WebSocket服务: ws://{self.ws_host}:{self.ws_port}/xiaozhi/v1/")
        print(f"📄 测试说明: {self.test_description}")
        print()
        
        # 测试步骤结果
        steps = [
            ("📡 MQTT连接", self.test_results["mqtt_connection"]),
            ("📤 SPEAK命令发送", self.test_results["speak_command_sent"]),
            ("📥 硬件ACK确认", self.test_results["ack_received"]),
            ("🌐 WebSocket连接", self.test_results["websocket_test"]),
            ("📥 播放完成事件", self.test_results["event_received"]),
            ("🎯 全流程完成", self.test_results["flow_completed"])
        ]
        
        passed = 0
        for step_name, status in steps:
            icon = "✅" if status else "❌"
            status_text = "通过" if status else "失败"
            print(f"{icon} {step_name:<20} : {status_text}")
            if status:
                passed += 1
        
        print("-" * 60)
        
        # 时间统计
        if self.start_time and self.ack_time:
            ack_delay = (self.ack_time - self.start_time) * 1000
            print(f"⏱️ SPEAK → ACK: {ack_delay:.1f}ms")
            
            if self.completion_time:
                total_time = self.completion_time - self.start_time
                print(f"⏱️ 总流程时间: {total_time:.1f}s")
            print()
        
        # 总体评估
        print(f"📈 总体结果: {passed}/{len(steps)} 步骤通过")
        
        if self.environment == "production":
            if passed >= 5:
                print("🎉 恭喜！生产环境测试成功！")
                print("💡 硬件已能正确连接小智主服务并播放真实音频")
            else:
                print("⚠️ 生产环境测试需要优化")
                self.print_production_tips()
        else:
            if passed >= 4:
                print("✅ 测试环境验证成功！")
            else:
                print("❌ 测试环境存在问题")
    
    def print_production_tips(self):
        """打印生产环境优化建议"""
        print("\n💡 生产环境优化建议:")
        
        if not self.test_results["websocket_test"]:
            print("🔧 WebSocket连接问题:")
            print("   - 确认硬件能访问公网地址 47.98.51.180:8000")
            print("   - 检查防火墙和网络配置")
            print("   - 验证小智主服务是否正常运行")
        
        if not self.test_results["event_received"]:
            print("🔧 音频播放问题:")
            print("   - 确认硬件WebSocket客户端实现")
            print("   - 检查音频数据解析和播放功能")
            print("   - 验证播放完成事件上报逻辑")
        
        print("\n🌐 生产环境地址:")
        print(f"   WebSocket: ws://47.98.51.180:8000/xiaozhi/v1/")
        print(f"   MQTT: 47.97.185.142:1883")
    
    def run_test(self):
        """运行生产环境测试"""
        env_name = "生产环境" if self.environment == "production" else "测试环境"
        print(f"🚀 {env_name}硬件测试启动")
        print("="*60)
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📱 目标设备: {self.device_id}")
        print(f"🎯 测试环境: {self.environment}")
        print(f"🌐 WebSocket: ws://{self.ws_host}:{self.ws_port}/xiaozhi/v1/")
        print(f"📄 测试说明: {self.test_description}")
        print()
        
        try:
            # 步骤1: 连接MQTT
            self.log("🔧 步骤1: 连接MQTT服务器...")
            if not self.setup_mqtt():
                self.log("MQTT连接失败，测试终止", "ERROR")
                return False
            
            time.sleep(2)  # 等待连接稳定
            
            # 步骤2: 发送SPEAK命令
            self.log("🔧 步骤2: 发送SPEAK命令...")
            if not self.send_speak_command():
                self.log("SPEAK命令发送失败，测试终止", "ERROR")
                return False
            
            # 步骤3: 等待完成
            self.log("🔧 步骤3: 等待硬件响应和完整流程...")
            timeout = 120 if self.environment == "production" else 60
            success = self.wait_for_completion(timeout)
            
            # 步骤4: 输出结果
            self.print_test_results()
            
            return success
            
        except KeyboardInterrupt:
            self.log("用户中断测试", "WARNING")
            return False
        except Exception as e:
            self.log(f"测试异常: {e}", "ERROR")
            return False
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生产环境硬件测试工具')
    parser.add_argument('device_id', nargs='?', default='7c:2c:67:8d:89:78', 
                        help='设备MAC地址')
    parser.add_argument('--env', choices=['production', 'test'], 
                        default='production', help='测试环境')
    
    args = parser.parse_args()
    
    print("🎯 生产环境硬件测试工具")
    print("测试硬件连接真实的小智主服务进行音频播放")
    print()
    
    # 显示环境说明
    env_descriptions = {
        'production': '连接生产环境的小智主服务 (ws://47.98.51.180:8000)',
        'test': '连接测试环境的模拟服务 (ws://172.20.12.204:8888)'
    }
    
    print(f"📱 设备ID: {args.device_id}")
    print(f"🎯 测试环境: {args.env} - {env_descriptions[args.env]}")
    print()
    
    # 运行测试
    tester = ProductionHardwareTest(args.device_id, args.env)
    success = tester.run_test()
    
    print("\n🏁 测试完成")
    if success:
        print("🎉 测试成功！硬件音频播放功能正常！")
    else:
        print("❌ 测试未完全通过，请检查硬件WebSocket实现")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())

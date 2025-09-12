#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 完整硬件音频播放测试脚本
测试从Python服务到硬件真实播放的完整流程
包含健康提醒内容播放测试
"""

import requests
import paho.mqtt.client as mqtt
import json
import time
import sys
import argparse
from datetime import datetime
import threading

class CompleteHardwareTest:
    def __init__(self, device_id="f0:9e:9e:04:8a:44"):
        self.device_id = device_id
        self.api_base = "http://172.20.12.204:8003"
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.mqtt_user = "admin"
        self.mqtt_pass = "Jyxd@2025"
        
        # 测试状态跟踪
        self.current_track_id = None
        self.test_start_time = None
        self.ack_received_time = None
        self.completion_time = None
        self.flow_completed = False
        self.ack_received = False
        
        # 健康提醒内容选项
        self.health_reminders = [
            "现在是吃饭时间了，记得按时用餐保持身体健康。用餐后请不要忘记按时服药哦！",
            "今天该吃午饭了，营养均衡很重要。吃完饭半小时后记得服用您的常用药物。",
            "亲爱的，现在是用餐时间，请记得好好吃饭。餐后请按医嘱及时服用药物，保持身体健康。",
            "该吃晚饭啦！记得荤素搭配营养均衡。用餐后请按时服药，这对您的健康很重要。",
            "现在是用药时间提醒：请记得按时服药，如果刚用完餐请间隔适当时间再服用。"
        ]
        
        self.mqtt_client = None
        
    def log(self, message, level="INFO"):
        """带时间戳和级别的日志"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️", "DEBUG": "🔍"}
        icon = icons.get(level, "📝")
        print(f"[{timestamp}] {icon} {message}")
    
    def setup_mqtt_monitor(self):
        """设置MQTT监控，监听硬件响应"""
        try:
            client_id = f"complete_test_{int(time.time())}"
            self.mqtt_client = mqtt.Client(
                client_id=client_id,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
            
            def on_connect(client, userdata, flags, rc, properties=None):
                if rc == 0:
                    self.log("MQTT监控连接成功", "SUCCESS")
                    # 订阅设备的ACK和EVENT主题
                    ack_topic = f"device/{self.device_id}/ack"
                    event_topic = f"device/{self.device_id}/event"
                    
                    client.subscribe(ack_topic)
                    client.subscribe(event_topic)
                    self.log(f"📡 已订阅主题: {ack_topic}, {event_topic}")
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
            self.mqtt_client.username_pw_set(self.mqtt_user, self.mqtt_pass)
            
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            
            # 等待连接建立
            time.sleep(2)
            return True
            
        except Exception as e:
            self.log(f"MQTT监控设置失败: {e}", "ERROR")
            return False
    
    def handle_ack_message(self, message):
        """处理硬件ACK消息"""
        track_id = message.get("track_id")
        event_type = message.get("evt")
        
        self.log(f"📥 收到ACK: {message}")
        
        if track_id == self.current_track_id and event_type == "CMD_RECEIVED":
            self.ack_received_time = time.time()
            self.ack_received = True
            ack_delay = (self.ack_received_time - self.test_start_time) * 1000
            self.log(f"✅ 硬件ACK确认成功! 响应时间: {ack_delay:.1f}ms", "SUCCESS")
            self.log("🌐 硬件正在连接WebSocket接收音频...", "INFO")
        else:
            self.log(f"⚠️ 收到其他设备或track_id的ACK: {track_id}", "WARNING")
    
    def handle_event_message(self, message):
        """处理硬件EVENT消息"""
        track_id = message.get("track_id")
        event_type = message.get("evt")
        
        self.log(f"📥 收到EVENT: {message}")
        
        if track_id == self.current_track_id:
            if event_type == "EVT_SPEAK_DONE":
                self.completion_time = time.time()
                self.flow_completed = True
                total_time = self.completion_time - self.test_start_time
                self.log(f"🎉 音频播放完成! 总用时: {total_time:.1f}秒", "SUCCESS")
            elif event_type == "EVT_WEBSOCKET_CONNECTED":
                self.log("🔗 硬件WebSocket连接成功!", "SUCCESS")
            elif event_type == "EVT_AUDIO_RECEIVED":
                self.log("🎵 硬件已接收音频数据", "SUCCESS")
            elif event_type == "EVT_AUDIO_PLAYING":
                self.log("🔊 硬件开始播放音频", "SUCCESS")
        else:
            self.log(f"⚠️ 收到其他track_id的EVENT: {track_id}", "WARNING")
    
    def send_health_reminder(self, reminder_text=None):
        """发送健康提醒API请求"""
        if not reminder_text:
            # 随机选择一个健康提醒内容
            import random
            reminder_text = random.choice(self.health_reminders)
        
        self.log(f"📝 健康提醒内容: {reminder_text}")
        
        # 构建API请求
        api_url = f"{self.api_base}/xiaozhi/greeting/send"
        payload = {
            "device_id": self.device_id,
            "initial_content": reminder_text,
            "category": "system_reminder",
            "user_info": {
                "name": "测试用户",
                "age": 65,
                "location": "测试环境"
            }
        }
        
        try:
            self.log("🚀 发送健康提醒API请求...", "INFO")
            self.test_start_time = time.time()
            
            response = requests.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.current_track_id = result.get("track_id")
                    self.log(f"✅ API调用成功! Track ID: {self.current_track_id}", "SUCCESS")
                    return True
                else:
                    self.log(f"❌ API返回错误: {result}", "ERROR")
                    return False
            else:
                self.log(f"❌ HTTP请求失败: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ API请求异常: {e}", "ERROR")
            return False
    
    def wait_for_completion(self, timeout=300):
        """等待测试完成，支持更长的超时时间"""
        self.log(f"⏰ 等待完整流程完成（最多{timeout}秒）...")
        
        start_wait = time.time()
        last_status_time = start_wait
        
        while time.time() - start_wait < timeout:
            current_time = time.time()
            
            # 每30秒显示一次状态
            if current_time - last_status_time >= 30:
                elapsed = current_time - self.test_start_time
                self.log(f"⏳ 流程进行中... 已用时: {elapsed:.1f}秒")
                self.log(f"📊 当前状态: ACK={self.ack_received}, 完成={self.flow_completed}")
                last_status_time = current_time
            
            if self.flow_completed:
                self.log("✅ 完整流程测试成功!", "SUCCESS")
                return True
            
            time.sleep(1)
        
        elapsed = time.time() - start_wait
        self.log(f"⏰ 等待超时 ({elapsed:.1f}秒)", "WARNING")
        
        # 检查超时时的状态
        self.check_timeout_status()
        return False
    
    def check_timeout_status(self):
        """检查超时时的状态"""
        self.log("🔍 检查超时状态...", "DEBUG")
        
        if not self.ack_received:
            self.log("❌ 硬件未响应ACK，可能设备离线或MQTT连接问题", "ERROR")
        elif self.ack_received and not self.flow_completed:
            self.log("⚠️ 硬件已收到命令但音频播放未完成", "WARNING")
            self.log("💡 可能原因: 音频较长、网络延迟、或TTS生成时间较长", "INFO")
            
            # 尝试查询服务器状态
            self.check_server_status()
    
    def check_server_status(self):
        """查询服务器端任务状态"""
        try:
            status_url = f"{self.api_base}/xiaozhi/greeting/status"
            params = {"device_id": self.device_id}
            
            response = requests.get(status_url, params=params, timeout=10)
            if response.status_code == 200:
                status_data = response.json()
                self.log(f"📊 服务器状态: {status_data}", "DEBUG")
                
                # 检查是否有我们的track_id
                if "state" in status_data and self.current_track_id:
                    task_status = status_data["state"].get(self.current_track_id)
                    if task_status:
                        self.log(f"🔍 任务状态: {task_status}", "INFO")
                        if task_status.get("status") == "completed":
                            self.log("✅ 服务器确认任务已完成", "SUCCESS")
                            self.flow_completed = True
                            return True
            else:
                self.log(f"⚠️ 无法获取服务器状态: {response.status_code}", "WARNING")
                
        except Exception as e:
            self.log(f"❌ 查询服务器状态失败: {e}", "ERROR")
        
        return False
    
    def print_final_results(self):
        """打印最终测试结果"""
        print("\n" + "=" * 80)
        print("🎯 完整硬件音频播放测试结果")
        print("=" * 80)
        
        # 基本信息
        print(f"📱 测试设备: {self.device_id}")
        print(f"🎯 Track ID: {self.current_track_id}")
        print(f"📅 测试时间: {datetime.fromtimestamp(self.test_start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 测试步骤结果
        steps = [
            ("🚀 API调用", bool(self.current_track_id)),
            ("📡 MQTT监控", bool(self.mqtt_client)),
            ("📥 硬件ACK确认", self.ack_received),
            ("🎵 音频播放完成", self.flow_completed)
        ]
        
        passed = 0
        for step_name, status in steps:
            icon = "✅" if status else "❌"
            status_text = "成功" if status else "失败"
            print(f"{icon} {step_name:<15} : {status_text}")
            if status:
                passed += 1
        
        print("-" * 80)
        
        # 时间统计
        if self.test_start_time:
            if self.ack_received_time:
                ack_delay = (self.ack_received_time - self.test_start_time) * 1000
                print(f"⏱️ API → ACK: {ack_delay:.1f}ms")
            
            if self.completion_time:
                total_time = self.completion_time - self.test_start_time
                print(f"⏱️ 总流程时间: {total_time:.1f}秒")
                
                # 性能评级
                if total_time < 30:
                    print("🚀 性能评级: 优秀")
                elif total_time < 60:
                    print("⚡ 性能评级: 良好")
                elif total_time < 120:
                    print("📊 性能评级: 一般")
                else:
                    print("🐌 性能评级: 需优化")
        
        # 总体评估
        print(f"\n📈 总体结果: {passed}/{len(steps)} 步骤成功")
        
        if passed == len(steps):
            print("🎉 恭喜！完整的硬件音频播放测试成功！")
            print("✅ 硬件能够正常接收并播放健康提醒音频")
        elif passed >= 2:
            print("⚠️ 部分功能正常，建议检查音频播放环节")
        else:
            print("❌ 测试失败，请检查设备连接和服务状态")
        
        print("=" * 80)
    
    def run_complete_test(self, custom_text=None, timeout=300):
        """运行完整测试"""
        print("🎯 完整硬件音频播放测试")
        print("📋 测试内容: 健康提醒音频播放")
        print("🔄 测试流程: API → LLM → TTS → MQTT → WebSocket → 硬件播放")
        print("=" * 80)
        
        try:
            # 步骤1: 设置MQTT监控
            self.log("🔧 步骤1: 设置MQTT监控...")
            if not self.setup_mqtt_monitor():
                self.log("MQTT监控设置失败，测试终止", "ERROR")
                return False
            
            # 步骤2: 发送健康提醒
            self.log("🔧 步骤2: 发送健康提醒API...")
            if not self.send_health_reminder(custom_text):
                self.log("健康提醒发送失败，测试终止", "ERROR")
                return False
            
            # 步骤3: 等待完整流程完成
            self.log("🔧 步骤3: 等待硬件音频播放完成...")
            success = self.wait_for_completion(timeout)
            
            return success
            
        except KeyboardInterrupt:
            self.log("用户中断测试", "WARNING")
            return False
        except Exception as e:
            self.log(f"测试异常: {e}", "ERROR")
            return False
        finally:
            # 清理资源
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            
            # 打印最终结果
            self.print_final_results()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="完整硬件音频播放测试")
    parser.add_argument("device_id", nargs="?", default="f0:9e:9e:04:8a:44", 
                       help="设备ID (默认: f0:9e:9e:04:8a:44)")
    parser.add_argument("--text", "-t", help="自定义测试文本")
    parser.add_argument("--timeout", type=int, default=300, 
                       help="超时时间(秒，默认300)")
    
    args = parser.parse_args()
    
    print(f"📱 目标设备: {args.device_id}")
    if args.text:
        print(f"📝 自定义内容: {args.text}")
    print()
    
    # 创建并运行测试
    tester = CompleteHardwareTest(args.device_id)
    success = tester.run_complete_test(args.text, args.timeout)
    
    # 退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
灵活的硬件测试脚本
支持测试模式和生产模式切换
"""

import paho.mqtt.client as mqtt
import json
import time
import sys
import argparse
from datetime import datetime
import uuid

class FlexibleHardwareTest:
    def __init__(self, device_id="7c:2c:67:8d:89:78", mode="test"):
        self.device_id = device_id
        self.mode = mode
        
        # MQTT配置
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        
        # 根据模式配置WebSocket地址
        if mode == "production":
            # 生产模式：硬件连接真实的小智主服务
            self.audio_url = "ws://47.98.51.180:8000/xiaozhi/v1/"
            self.description = "硬件连接生产环境小智主服务"
        elif mode == "test_internal":
            # 内网测试模式：硬件连接测试脚本
            self.audio_url = "ws://172.20.12.204:8888/xiaozhi/v1/"
            self.description = "硬件连接内网测试脚本"
        else:  # test
            # 默认测试模式 - 使用生产环境WebSocket地址
            self.audio_url = "ws://47.98.51.180:8000/xiaozhi/v1/"
            self.description = "硬件连接生产环境WebSocket服务"
        
        # 测试状态跟踪
        self.test_results = {
            "mqtt_connection": False,
            "speak_command_sent": False,
            "ack_received": False,
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
        client_id = f"flexible_test_{int(time.time())}"
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
            self.log(f"🌐 硬件将连接: {self.audio_url}")
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
        self.current_track_id = f"FLEX{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"
        cmd_topic = f"device/{self.device_id}/cmd"
        
        # 根据模式构建不同的测试文本
        if self.mode == "production":
            text = f"生产环境测试：硬件连接小智主服务获取真实TTS音频。模式：{self.mode}"
        else:
            text = f"测试环境验证：硬件连接测试脚本获取模拟音频。模式：{self.mode}"
        
        # 构建SPEAK命令
        speak_command = {
            "type": "SPEAK",
            "track_id": self.current_track_id,
            "text": text,
            "timestamp": datetime.now().isoformat() + "Z",
            "audio_url": self.audio_url,  # 根据模式使用不同地址
            "expected_duration": 10,
            "test_mode": self.mode,
            "description": self.description
        }
        
        try:
            self.mqtt_client.publish(cmd_topic, json.dumps(speak_command))
            self.start_time = time.time()
            self.test_results["speak_command_sent"] = True
            self.log(f"📤 发送SPEAK命令: track_id={self.current_track_id}", "SUCCESS")
            self.log(f"🎯 测试模式: {self.mode}")
            self.log(f"🌐 音频地址: {self.audio_url}")
            self.log(f"💬 测试内容: {text}")
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
        
        elapsed = time.time() - start_wait
        self.log(f"⏰ 等待超时 ({elapsed:.1f}秒)", "WARNING")
        
        # 超时后检查服务器状态
        self.log("🔍 检查服务器状态...")
        self.check_server_status()
        return False
    
    def print_test_results(self):
        """打印详细测试结果"""
        print("\n" + "=" * 60)
        print(f"📊 灵活硬件测试结果 - {self.mode.upper()}模式")
        print("=" * 60)
        
        # 基本信息
        print(f"📱 测试设备: {self.device_id}")
        print(f"🎯 测试模式: {self.mode}")
        print(f"🎯 Track ID: {self.current_track_id}")
        print(f"🌐 音频地址: {self.audio_url}")
        print(f"📄 测试说明: {self.description}")
        print()
        
        # 测试步骤结果
        steps = [
            ("📡 MQTT连接", self.test_results["mqtt_connection"]),
            ("📤 SPEAK命令发送", self.test_results["speak_command_sent"]),
            ("📥 硬件ACK确认", self.test_results["ack_received"]),
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
                
                # 性能分析
                if total_time < 10:
                    print("🚀 性能评级: 优秀 (TTS服务预热状态)")
                elif total_time < 30:
                    print("⚡ 性能评级: 良好 (正常服务状态)")  
                elif total_time < 60:
                    print("📊 性能评级: 一般 (服务负载较高)")
                else:
                    print("🐌 性能评级: 需优化 (TTS冷启动或网络延迟)")
                    print("💡 建议: 检查TTS服务状态和网络连接")
            print()
        
        # 总体评估
        print(f"📈 总体结果: {passed}/{len(steps)} 步骤通过")
        
        if self.mode == "production":
            if passed >= 4:
                print("🎉 恭喜！生产环境测试成功！")
                print("💡 硬件已能正确连接小智主服务")
            else:
                print("⚠️ 生产环境测试需要优化")
        else:
            if passed >= 4:
                print("✅ 测试环境验证成功！")
            else:
                print("❌ 测试环境存在问题")
    
    def run_test(self):
        """运行灵活测试"""
        print(f"🚀 灵活硬件测试启动 - {self.mode.upper()}模式")
        print("="*60)
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📱 目标设备: {self.device_id}")
        print(f"🎯 测试模式: {self.mode}")
        print(f"🌐 音频地址: {self.audio_url}")
        print(f"📄 测试说明: {self.description}")
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
            timeout = 360 if self.mode == "production" else 60  # 生产模式等待6分钟
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
    
    def check_server_status(self):
        """检查服务器状态，看硬件是否实际完成了任务"""
        try:
            import requests
            url = f"http://172.20.12.204:8003/xiaozhi/greeting/status?device_id={self.device_id}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                track_state = data.get("state", {}).get(self.current_track_id)
                
                if track_state:
                    status = track_state.get("status")
                    completed_time = track_state.get("completed_timestamp")
                    
                    if status == "speak_done" and completed_time:
                        self.log("🎉 服务器确认：硬件已完成任务！", "SUCCESS")
                        self.log(f"📅 完成时间: {completed_time}")
                        self.log("💡 测试脚本超时，但硬件功能正常", "WARNING")
                        # 手动标记为完成
                        self.test_results["event_received"] = True
                        self.test_results["flow_completed"] = True
                        return True
                    else:
                        self.log(f"📊 服务器状态: {status}")
                else:
                    self.log("📋 服务器无该任务记录")
            else:
                self.log(f"❌ 服务器状态检查失败: {response.status_code}")
                
        except Exception as e:
            self.log(f"❌ 状态检查异常: {e}", "ERROR")
        
        return False
    
    def cleanup(self):
        """清理资源"""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='灵活的硬件测试工具')
    parser.add_argument('device_id', nargs='?', default='7c:2c:67:8d:89:78', 
                        help='设备MAC地址')
    parser.add_argument('--mode', choices=['test', 'test_internal', 'production'], 
                        default='test', help='测试模式')
    
    args = parser.parse_args()
    
    print("🎯 灵活硬件测试工具")
    print("支持测试模式和生产模式切换")
    print()
    
    # 显示模式说明
    mode_descriptions = {
        'test': '测试模式 - 硬件连接测试脚本 (ws://172.20.12.204:8888)',
        'test_internal': '内网测试模式 - 硬件连接内网测试脚本',
        'production': '生产模式 - 硬件连接小智主服务 (ws://47.98.51.180:8000)'
    }
    
    print(f"📱 设备ID: {args.device_id}")
    print(f"🎯 测试模式: {args.mode} - {mode_descriptions[args.mode]}")
    print()
    
    # 运行测试
    tester = FlexibleHardwareTest(args.device_id, args.mode)
    success = tester.run_test()
    
    print("\n🏁 测试完成")
    if success:
        print("🎉 测试成功！硬件功能正常！")
    else:
        print("❌ 测试未完全通过，请检查相关问题")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())

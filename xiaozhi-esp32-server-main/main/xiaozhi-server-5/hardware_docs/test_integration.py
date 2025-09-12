#!/usr/bin/env python3
"""
硬件集成测试脚本
用于验证硬件设备的主动问候功能实现
"""

import paho.mqtt.client as mqtt
import json
import time
import threading
from datetime import datetime
import websocket

class HardwareIntegrationTest:
    def __init__(self, device_id="00:0c:29:fc:b7:b9"):
        self.device_id = device_id
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.ws_url = f"ws://172.20.12.204:8000/xiaozhi/v1/?device-id={device_id}&client-id=test-client"
        
        # 测试状态跟踪
        self.test_results = {
            "mqtt_connection": False,
            "cmd_sent": False,
            "ack_received": False,
            "event_received": False,
            "websocket_connection": False
        }
        
        self.current_track_id = None
        self.mqtt_client = None
        self.ws_client = None
        
    def log(self, message):
        """带时间戳的日志"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def setup_mqtt(self):
        """设置MQTT客户端"""
        self.mqtt_client = mqtt.Client(
            client_id=f"test_integration_{int(time.time())}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.log("✅ MQTT连接成功")
                self.test_results["mqtt_connection"] = True
                
                # 订阅设备的ACK和EVENT主题
                ack_topic = f"device/{self.device_id}/ack"
                event_topic = f"device/{self.device_id}/event"
                
                client.subscribe(ack_topic)
                client.subscribe(event_topic)
                self.log(f"📡 订阅主题: {ack_topic}, {event_topic}")
            else:
                self.log(f"❌ MQTT连接失败，返回码: {rc}")
        
        def on_message(client, userdata, msg):
            topic = msg.topic
            try:
                message = json.loads(msg.payload.decode())
                self.log(f"📥 收到消息 {topic}: {message}")
                
                if "/ack" in topic:
                    self.handle_ack_message(message)
                elif "/event" in topic:
                    self.handle_event_message(message)
                    
            except json.JSONDecodeError:
                self.log(f"❌ JSON解析失败: {msg.payload.decode()}")
        
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = on_message
        
        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            self.log(f"❌ MQTT连接异常: {e}")
            return False
    
    def handle_ack_message(self, message):
        """处理ACK消息"""
        track_id = message.get("track_id")
        event_type = message.get("evt")
        
        if track_id == self.current_track_id and event_type == "CMD_RECEIVED":
            self.log("✅ 收到正确的ACK确认")
            self.test_results["ack_received"] = True
        else:
            self.log(f"⚠️ ACK消息异常: track_id={track_id}, evt={event_type}")
    
    def handle_event_message(self, message):
        """处理EVENT消息"""
        track_id = message.get("track_id")
        event_type = message.get("evt")
        
        if track_id == self.current_track_id and event_type == "EVT_SPEAK_DONE":
            self.log("✅ 收到播放完成事件")
            self.test_results["event_received"] = True
        else:
            self.log(f"⚠️ EVENT消息异常: track_id={track_id}, evt={event_type}")
    
    def send_test_command(self):
        """发送测试命令给设备"""
        if not self.mqtt_client or not self.test_results["mqtt_connection"]:
            self.log("❌ MQTT未连接，无法发送命令")
            return False
        
        # 生成测试命令
        self.current_track_id = f"TEST{int(time.time())}"
        cmd_topic = f"device/{self.device_id}/cmd"
        
        test_command = {
            "cmd": "SPEAK",
            "text": "硬件测试：这是一条主动问候测试消息，请确认收到并播放。",
            "track_id": self.current_track_id
        }
        
        try:
            self.mqtt_client.publish(cmd_topic, json.dumps(test_command))
            self.log(f"📤 发送测试命令: {test_command}")
            self.test_results["cmd_sent"] = True
            return True
        except Exception as e:
            self.log(f"❌ 发送命令失败: {e}")
            return False
    
    def setup_websocket(self):
        """设置WebSocket连接"""
        def on_open(ws):
            self.log("✅ WebSocket连接成功")
            self.test_results["websocket_connection"] = True
        
        def on_message(ws, message):
            self.log(f"📥 WebSocket消息: {message}")
        
        def on_error(ws, error):
            self.log(f"❌ WebSocket错误: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            self.log("🔌 WebSocket连接关闭")
        
        try:
            self.ws_client = websocket.WebSocketApp(
                self.ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # 在后台线程运行WebSocket
            ws_thread = threading.Thread(target=self.ws_client.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            return True
        except Exception as e:
            self.log(f"❌ WebSocket连接异常: {e}")
            return False
    
    def wait_for_responses(self, timeout=30):
        """等待设备响应"""
        self.log(f"⏰ 等待设备响应（最多{timeout}秒）...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # 检查是否收到了ACK和EVENT
            if self.test_results["ack_received"] and self.test_results["event_received"]:
                self.log("✅ 设备响应完整，测试成功！")
                return True
            
            time.sleep(1)
        
        self.log("⏰ 等待超时")
        return False
    
    def run_full_test(self):
        """运行完整测试流程"""
        print("🧪 硬件集成测试开始")
        print("=" * 50)
        print(f"📱 测试设备ID: {self.device_id}")
        print(f"📡 MQTT服务器: {self.mqtt_host}:{self.mqtt_port}")
        print(f"🌐 WebSocket地址: {self.ws_url}")
        print("")
        
        # Step 1: 连接MQTT
        self.log("🔧 步骤1: 连接MQTT服务器...")
        if not self.setup_mqtt():
            self.log("❌ MQTT连接失败，测试终止")
            return False
        
        time.sleep(2)  # 等待连接稳定
        
        # Step 2: 连接WebSocket
        self.log("🔧 步骤2: 连接WebSocket服务器...")
        self.setup_websocket()
        time.sleep(2)  # 等待连接稳定
        
        # Step 3: 发送测试命令
        self.log("🔧 步骤3: 发送测试命令...")
        if not self.send_test_command():
            self.log("❌ 命令发送失败，测试终止")
            return False
        
        # Step 4: 等待设备响应
        self.log("🔧 步骤4: 等待设备响应...")
        success = self.wait_for_responses()
        
        # Step 5: 输出测试结果
        self.print_test_results()
        
        # 清理资源
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        if self.ws_client:
            self.ws_client.close()
        
        return success
    
    def print_test_results(self):
        """打印测试结果"""
        print("\n" + "=" * 50)
        print("📊 测试结果汇总")
        print("=" * 50)
        
        results = [
            ("MQTT连接", self.test_results["mqtt_connection"]),
            ("命令发送", self.test_results["cmd_sent"]),
            ("ACK确认", self.test_results["ack_received"]),
            ("播放完成事件", self.test_results["event_received"]),
            ("WebSocket连接", self.test_results["websocket_connection"])
        ]
        
        passed = 0
        for name, status in results:
            icon = "✅" if status else "❌"
            print(f"{icon} {name:15} : {'通过' if status else '失败'}")
            if status:
                passed += 1
        
        print("-" * 50)
        print(f"📈 总体结果: {passed}/{len(results)} 通过")
        
        if passed == len(results):
            print("🎉 恭喜！硬件设备集成测试完全成功！")
            print("💡 设备已经可以正常接收和处理主动问候功能")
        elif passed >= 3:
            print("⚠️ 基本功能正常，但仍有部分问题需要解决")
            self.print_troubleshooting_tips()
        else:
            print("❌ 测试失败，请检查硬件设备实现")
            self.print_troubleshooting_tips()
    
    def print_troubleshooting_tips(self):
        """打印故障排除建议"""
        print("\n💡 故障排除建议:")
        
        if not self.test_results["mqtt_connection"]:
            print("🔧 MQTT连接问题:")
            print("   - 检查网络连接")
            print("   - 确认MQTT服务器地址和端口")
            print("   - 检查防火墙设置")
        
        if not self.test_results["ack_received"]:
            print("🔧 ACK确认问题:")
            print("   - 检查设备是否正确订阅了cmd主题")
            print("   - 确认设备能够解析JSON格式")
            print("   - 检查track_id是否正确回复")
        
        if not self.test_results["event_received"]:
            print("🔧 事件上报问题:")
            print("   - 检查播放完成后是否上报事件")
            print("   - 确认事件消息格式正确")
            print("   - 检查track_id是否一致")
        
        if not self.test_results["websocket_connection"]:
            print("🔧 WebSocket连接问题:")
            print("   - 检查认证参数格式")
            print("   - 确认WebSocket服务器地址")
            print("   - 检查device-id和client-id参数")

def main():
    """主函数"""
    import sys
    
    print("🚀 小智硬件集成测试工具")
    print("适用于主动问候功能验证")
    print("")
    
    # 获取设备ID
    if len(sys.argv) > 1:
        device_id = sys.argv[1]
    else:
        device_id = input("请输入设备MAC地址 (例如: 00:0c:29:fc:b7:b9): ").strip()
        if not device_id:
            device_id = "00:0c:29:fc:b7:b9"  # 默认测试设备ID
    
    print(f"📱 使用设备ID: {device_id}")
    print("")
    
    # 创建并运行测试
    tester = HardwareIntegrationTest(device_id)
    success = tester.run_full_test()
    
    print("\n🏁 测试完成")
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python-硬件全流程测试脚本
测试完整的主动问候流程：Python发送命令 → 硬件响应 → WebSocket音频 → 完成事件
"""

import paho.mqtt.client as mqtt
import json
import time
import threading
import asyncio
import websockets
import base64
import wave
import io
from datetime import datetime
import uuid
from typing import Dict, Any

class PythonHardwareFlowTest:
    def __init__(self, device_id="7c:2c:67:8d:89:78"):
        self.device_id = device_id
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.ws_host = "172.20.12.204"  # 内网地址（测试脚本实际运行地址）
        self.ws_port = 8888  # 测试专用端口，避免冲突
        
        # 测试状态跟踪
        self.test_results = {
            "mqtt_connection": False,
            "speak_command_sent": False,
            "ack_received": False,
            "websocket_connection": False,
            "audio_sent": False,
            "event_received": False,
            "flow_completed": False
        }
        
        # 流程跟踪
        self.current_track_id = None
        self.mqtt_client = None
        self.ws_server = None
        self.start_time = None
        self.ack_time = None
        self.audio_time = None
        self.completion_time = None
        
        # 配置
        self.test_timeout = 60  # 60秒超时
        self.audio_wait_time = 3  # ACK后等待3秒再发音频
        
    def log(self, message, level="INFO"):
        """带时间戳和级别的日志"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️", "DEBUG": "🔍"}
        icon = icons.get(level, "📝")
        print(f"[{timestamp}] {icon} {message}")
    
    def generate_test_audio(self) -> bytes:
        """生成测试音频数据（WAV格式）"""
        try:
            # 生成5秒的440Hz正弦波
            import numpy as np
            
            sample_rate = 16000
            duration = 5.0
            frequency = 440
            
            # 生成正弦波
            t = np.linspace(0, duration, int(sample_rate * duration))
            audio_data = np.sin(2 * np.pi * frequency * t) * 0.3
            audio_data = (audio_data * 32767).astype(np.int16)
            
            # 转换为WAV格式
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            
            wav_data = buffer.getvalue()
            self.log(f"🎵 生成测试音频: {len(wav_data)} bytes, {duration}秒", "DEBUG")
            return wav_data
            
        except ImportError:
            # 如果没有numpy，生成简单的静音WAV
            self.log("⚠️ numpy未安装，生成简单测试音频", "WARNING")
            return self.generate_simple_wav()
    
    def generate_simple_wav(self) -> bytes:
        """生成简单的WAV测试音频"""
        # 创建简单的WAV文件头 + 3秒静音
        sample_rate = 16000
        duration = 3
        samples = sample_rate * duration
        
        # WAV文件头
        wav_header = bytearray([
            0x52, 0x49, 0x46, 0x46,  # "RIFF"
            0x00, 0x00, 0x00, 0x00,  # 文件长度 (稍后填写)
            0x57, 0x41, 0x56, 0x45,  # "WAVE"
            0x66, 0x6D, 0x74, 0x20,  # "fmt "
            0x10, 0x00, 0x00, 0x00,  # fmt chunk size (16)
            0x01, 0x00,              # 音频格式 (PCM)
            0x01, 0x00,              # 声道数 (1)
            0x80, 0x3E, 0x00, 0x00,  # 采样率 (16000)
            0x00, 0x7D, 0x00, 0x00,  # 字节率
            0x02, 0x00,              # 块对齐
            0x10, 0x00,              # 位深度 (16)
            0x64, 0x61, 0x74, 0x61,  # "data"
            0x00, 0x00, 0x00, 0x00,  # 数据长度 (稍后填写)
        ])
        
        # 生成静音数据
        audio_data = bytes(samples * 2)  # 16bit = 2 bytes per sample
        
        # 更新文件长度
        total_size = len(wav_header) + len(audio_data) - 8
        wav_header[4:8] = total_size.to_bytes(4, 'little')
        wav_header[-4:] = len(audio_data).to_bytes(4, 'little')
        
        return bytes(wav_header) + audio_data
    
    def setup_mqtt(self):
        """设置MQTT客户端"""
        client_id = f"python_test_{int(time.time())}"
        self.mqtt_client = mqtt.Client(
            client_id=client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        
        def on_connect(client, userdata, flags, rc):
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
        
        def on_disconnect(client, userdata, rc):
            self.log("MQTT连接断开", "WARNING")
        
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = on_message
        self.mqtt_client.on_disconnect = on_disconnect
        
        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            self.log(f"MQTT连接异常: {e}", "ERROR")
            return False
    
    def handle_ack_message(self, message: Dict[str, Any]):
        """处理硬件ACK消息"""
        track_id = message.get("track_id")
        event_type = message.get("evt")
        timestamp = message.get("timestamp", "")
        
        self.log(f"📥 收到ACK: {message}")
        
        if track_id == self.current_track_id and event_type == "CMD_RECEIVED":
            self.ack_time = time.time()
            self.test_results["ack_received"] = True
            self.log("✅ ACK确认成功！硬件已收到SPEAK命令", "SUCCESS")
            
            # 等待一段时间后发送音频（模拟Python服务生成TTS的过程）
            threading.Timer(self.audio_wait_time, self.send_audio_to_device).start()
        else:
            self.log(f"⚠️ ACK消息异常: track_id={track_id}, evt={event_type}", "WARNING")
    
    def handle_event_message(self, message: Dict[str, Any]):
        """处理硬件EVENT消息"""
        track_id = message.get("track_id")
        event_type = message.get("evt")
        status = message.get("status", "")
        
        self.log(f"📥 收到EVENT: {message}")
        
        if track_id == self.current_track_id and event_type == "EVT_SPEAK_DONE":
            self.completion_time = time.time()
            self.test_results["event_received"] = True
            self.test_results["flow_completed"] = True
            self.log("🎉 播放完成事件收到！全流程测试成功！", "SUCCESS")
        else:
            self.log(f"⚠️ EVENT消息异常: track_id={track_id}, evt={event_type}", "WARNING")
    
    def send_speak_command(self):
        """发送SPEAK命令给硬件"""
        if not self.mqtt_client or not self.test_results["mqtt_connection"]:
            self.log("MQTT未连接，无法发送命令", "ERROR")
            return False
        
        # 生成唯一的track_id
        self.current_track_id = f"TEST{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"
        cmd_topic = f"device/{self.device_id}/cmd"
        
        # 构建SPEAK命令 - 生产环境使用真实的WebSocket地址
        speak_command = {
            "type": "SPEAK",
            "track_id": self.current_track_id,
            "text": "Python-硬件全流程测试：这是一条完整的主动问候测试消息，包含命令发送、ACK确认、音频传输和完成事件的全流程验证。",
            "timestamp": datetime.now().isoformat() + "Z",
            "audio_url": f"ws://{self.ws_host}:{self.ws_port}/xiaozhi/v1/",  # 测试环境地址
            "expected_duration": 15
        }
        
        try:
            self.mqtt_client.publish(cmd_topic, json.dumps(speak_command))
            self.start_time = time.time()
            self.test_results["speak_command_sent"] = True
            self.log(f"📤 发送SPEAK命令: track_id={self.current_track_id}", "SUCCESS")
            self.log(f"🎯 命令内容: {speak_command['text'][:50]}...")
            return True
        except Exception as e:
            self.log(f"发送SPEAK命令失败: {e}", "ERROR")
            return False
    
    def send_audio_to_device(self):
        """通过WebSocket发送音频给硬件"""
        self.log(f"⏳ 等待{self.audio_wait_time}秒后发送音频（模拟TTS生成时间）...")
        
        try:
            # 生成测试音频
            audio_data = self.generate_test_audio()
            
            # 转换为十六进制字符串（模拟实际的音频传输格式）
            hex_audio = audio_data.hex().upper()
            
            # 构建WebSocket音频消息
            audio_message = {
                "type": "audio",
                "track_id": self.current_track_id,
                "device_id": self.device_id,
                "audio_data": hex_audio,
                "format": "wav",
                "sample_rate": 16000,
                "channels": 1,
                "duration": 5.0,
                "timestamp": datetime.now().isoformat() + "Z"
            }
            
            # 启动WebSocket服务器模拟音频发送
            self.start_websocket_audio_server(audio_message)
            
        except Exception as e:
            self.log(f"生成音频数据失败: {e}", "ERROR")
    
    def start_websocket_audio_server(self, audio_message):
        """启动混合HTTP/WebSocket服务器发送音频"""
        async def audio_server():
            try:
                # 使用原生asyncio创建更兼容的服务器
                async def handle_connection(reader, writer):
                    try:
                        client_addr = writer.get_extra_info('peername')
                        self.log(f"🔌 客户端连接: {client_addr}")
                        
                        # 读取请求头
                        request_line = await reader.readline()
                        request = request_line.decode().strip()
                        self.log(f"📋 请求: {request}")
                        
                        # 读取所有请求头
                        headers = {}
                        while True:
                            line = await reader.readline()
                            if line == b'\r\n' or line == b'\n':
                                break
                            if line:
                                header = line.decode().strip()
                                if ':' in header:
                                    key, value = header.split(':', 1)
                                    headers[key.strip().lower()] = value.strip()
                        
                        # 处理健康检查请求
                        if 'GET /check/hello' in request:
                            self.log("✅ 硬件健康检查请求", "SUCCESS")
                            response = (
                                "HTTP/1.1 200 OK\r\n"
                                "Content-Type: text/plain\r\n"
                                "Content-Length: 2\r\n"
                                "Connection: close\r\n"
                                "\r\n"
                                "OK"
                            )
                            writer.write(response.encode())
                            await writer.drain()
                            writer.close()
                            await writer.wait_closed()
                            return
                        
                        # 处理WebSocket升级请求
                        if 'upgrade' in headers and headers['upgrade'].lower() == 'websocket':
                            self.log("🔗 WebSocket升级请求", "SUCCESS")
                            self.test_results["websocket_connection"] = True
                            
                            # 简化的WebSocket握手响应
                            websocket_key = headers.get('sec-websocket-key', '')
                            if websocket_key:
                                import hashlib
                                import base64
                                
                                magic_string = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
                                accept_key = base64.b64encode(
                                    hashlib.sha1((websocket_key + magic_string).encode()).digest()
                                ).decode()
                                
                                response = (
                                    "HTTP/1.1 101 Switching Protocols\r\n"
                                    "Upgrade: websocket\r\n"
                                    "Connection: Upgrade\r\n"
                                    f"Sec-WebSocket-Accept: {accept_key}\r\n"
                                    "\r\n"
                                )
                                writer.write(response.encode())
                                await writer.drain()
                                
                                # 发送音频数据（简化的WebSocket帧）
                                audio_json = json.dumps(audio_message)
                                payload = audio_json.encode()
                                payload_len = len(payload)
                                
                                # WebSocket数据帧 (简化版)
                                if payload_len < 126:
                                    frame = bytes([0x81, payload_len]) + payload
                                else:
                                    frame = bytes([0x81, 126]) + payload_len.to_bytes(2, 'big') + payload
                                
                                writer.write(frame)
                                await writer.drain()
                                
                                self.audio_time = time.time()
                                self.test_results["audio_sent"] = True
                                self.log(f"🎵 音频数据已发送: {len(audio_message['audio_data'])} hex chars", "SUCCESS")
                                
                                # 等待响应
                                try:
                                    response_data = await asyncio.wait_for(reader.read(1024), timeout=5)
                                    if response_data:
                                        self.log(f"📥 WebSocket收到响应: {len(response_data)} bytes")
                                except asyncio.TimeoutError:
                                    self.log("⏰ WebSocket响应超时（正常，硬件可能不回复）")
                            
                        else:
                            # 普通HTTP请求
                            response = (
                                "HTTP/1.1 404 Not Found\r\n"
                                "Content-Type: text/plain\r\n"
                                "Content-Length: 9\r\n"
                                "Connection: close\r\n"
                                "\r\n"
                                "Not Found"
                            )
                            writer.write(response.encode())
                            await writer.drain()
                        
                        writer.close()
                        await writer.wait_closed()
                        
                    except Exception as e:
                        self.log(f"连接处理异常: {e}", "ERROR")
                        try:
                            writer.close()
                            await writer.wait_closed()
                        except:
                            pass
                
                # 启动服务器
                local_host = "0.0.0.0"
                self.log(f"🌐 启动混合HTTP/WebSocket服务器: {local_host}:{self.ws_port}")
                self.log(f"🌐 硬件应连接: ws://{self.ws_host}:{self.ws_port}/xiaozhi/v1/")
                self.log(f"🩺 健康检查地址: http://{self.ws_host}:{self.ws_port}/check/hello")
                
                server = await asyncio.start_server(
                    handle_connection, 
                    local_host, 
                    self.ws_port
                )
                
                # 保持服务器运行30秒
                async with server:
                    await asyncio.sleep(30)
                
            except Exception as e:
                self.log(f"服务器启动失败: {e}", "ERROR")
        
        # 在新线程中运行WebSocket服务器
        def run_server():
            asyncio.run(audio_server())
        
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()
    
    def wait_for_completion(self, timeout=None):
        """等待测试完成"""
        if timeout is None:
            timeout = self.test_timeout
        
        self.log(f"⏰ 等待测试完成（最多{timeout}秒）...")
        
        start_wait = time.time()
        while time.time() - start_wait < timeout:
            if self.test_results["flow_completed"]:
                self.log("🎉 全流程测试完成！", "SUCCESS")
                return True
            
            time.sleep(0.5)
        
        self.log("⏰ 等待超时", "WARNING")
        return False
    
    def print_test_results(self):
        """打印详细测试结果"""
        print("\n" + "=" * 60)
        print("📊 Python-硬件全流程测试结果")
        print("=" * 60)
        
        # 基本信息
        print(f"📱 测试设备: {self.device_id}")
        print(f"🎯 Track ID: {self.current_track_id}")
        print(f"📡 MQTT服务器: {self.mqtt_host}:{self.mqtt_port}")
        print(f"🌐 WebSocket服务器: ws://{self.ws_host}:{self.ws_port}")
        print()
        
        # 测试步骤结果
        steps = [
            ("1️⃣ MQTT连接", self.test_results["mqtt_connection"]),
            ("2️⃣ SPEAK命令发送", self.test_results["speak_command_sent"]),
            ("3️⃣ 硬件ACK确认", self.test_results["ack_received"]),
            ("4️⃣ WebSocket连接", self.test_results["websocket_connection"]),
            ("5️⃣ 音频数据发送", self.test_results["audio_sent"]),
            ("6️⃣ 播放完成事件", self.test_results["event_received"]),
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
        if self.start_time:
            print("⏱️ 时间统计:")
            if self.ack_time:
                ack_delay = (self.ack_time - self.start_time) * 1000
                print(f"   📤➡️📥 SPEAK → ACK: {ack_delay:.1f}ms")
            
            if self.audio_time:
                audio_delay = (self.audio_time - self.start_time) * 1000
                print(f"   📤➡️🎵 SPEAK → 音频: {audio_delay:.1f}ms")
            
            if self.completion_time:
                total_time = self.completion_time - self.start_time
                print(f"   📤➡️🏁 总流程时间: {total_time:.1f}s")
            print()
        
        # 总体评估
        print(f"📈 总体结果: {passed}/{len(steps)} 步骤通过")
        
        if self.test_results["flow_completed"]:
            print("🎉 恭喜！Python-硬件全流程测试完全成功！")
            print("💡 主动问候功能的完整流程已验证通过")
        elif passed >= 4:
            print("⚠️ 基本流程正常，但部分功能需要完善")
            self.print_troubleshooting_tips()
        else:
            print("❌ 测试失败，请检查系统配置")
            self.print_troubleshooting_tips()
    
    def print_troubleshooting_tips(self):
        """打印故障排除建议"""
        print("\n💡 故障排除建议:")
        
        if not self.test_results["mqtt_connection"]:
            print("🔧 MQTT连接问题:")
            print("   - 检查MQTT服务器地址和端口")
            print("   - 确认网络连通性")
            print("   - 检查防火墙设置")
        
        if not self.test_results["ack_received"]:
            print("🔧 ACK确认问题:")
            print("   - 确认硬件正确订阅了cmd主题")
            print("   - 检查硬件JSON解析功能")
            print("   - 验证track_id返回是否正确")
        
        if not self.test_results["websocket_connection"]:
            print("🔧 WebSocket连接问题:")
            print("   - 检查硬件WebSocket客户端实现")
            print("   - 确认连接URL格式正确")
            print("   - 验证网络连接")
        
        if not self.test_results["event_received"]:
            print("🔧 完成事件问题:")
            print("   - 检查硬件播放完成后的事件上报")
            print("   - 确认EVENT消息格式正确")
            print("   - 验证track_id一致性")
    
    def run_full_test(self):
        """运行完整的全流程测试"""
        print("🚀 Python-硬件全流程测试启动")
        print("="*60)
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📱 目标设备: {self.device_id}")
        print(f"🎯 测试内容: SPEAK命令 → ACK确认 → WebSocket音频 → 完成事件")
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
            
            # 步骤3: 等待完整流程完成
            self.log("🔧 步骤3: 等待硬件响应和完整流程...")
            success = self.wait_for_completion()
            
            # 步骤4: 输出测试结果
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
        
        if self.ws_server:
            try:
                self.ws_server.close()
            except:
                pass

def main():
    """主函数"""
    import sys
    
    print("🎯 Python-硬件全流程测试工具")
    print("测试完整的主动问候流程")
    print()
    
    # 获取设备ID
    if len(sys.argv) > 1:
        device_id = sys.argv[1]
    else:
        device_id = input("请输入设备MAC地址 (例如: 7c:2c:67:8d:89:78): ").strip()
        if not device_id:
            device_id = "7c:2c:67:8d:89:78"  # 从截图中看到的设备ID
    
    print(f"📱 使用设备ID: {device_id}")
    print()
    
    # 运行测试
    tester = PythonHardwareFlowTest(device_id)
    success = tester.run_full_test()
    
    print("\n🏁 测试完成")
    if success:
        print("🎉 全流程测试成功！系统工作正常！")
    else:
        print("❌ 测试未完全通过，请检查相关问题")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())

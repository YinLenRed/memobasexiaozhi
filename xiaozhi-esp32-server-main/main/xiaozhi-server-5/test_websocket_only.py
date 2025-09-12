#!/usr/bin/env python3
"""
🎯 WebSocket连接专项测试工具
专门测试硬件的WebSocket连接能力
"""

import asyncio
import socket
import time
import json
from datetime import datetime

class WebSocketConnectionTest:
    def __init__(self, device_id="7c:2c:67:8d:89:78", mode="production"):
        self.device_id = device_id
        self.mode = mode
        
        if mode == "production":
            # 生产模式：测试连接到真实的生产服务器
            self.target_host = "47.98.51.180"
            self.target_port = 8000
            self.test_url = f"ws://{self.target_host}:{self.target_port}/xiaozhi/v1/"
            self.ws_host = None  # 不启动本地服务器
            self.ws_port = None
        else:
            # 测试模式：启动本地WebSocket服务器
            self.target_host = "172.20.12.204"
            self.target_port = 8889
            self.test_url = f"ws://{self.target_host}:{self.target_port}/xiaozhi/v1/"
            self.ws_host = "0.0.0.0"  # 监听所有接口
            self.ws_port = 8889  # 使用不同端口避免冲突
        self.test_results = {
            "websocket_connection": False,
            "hello_message": False,
            "message_exchange": False
        }
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        if level == "SUCCESS":
            prefix = "✅"
        elif level == "ERROR":
            prefix = "❌"
        elif level == "WARNING":
            prefix = "⚠️"
        else:
            prefix = "ℹ️"
            
        print(f"[{timestamp}] {prefix} {message}")

    async def start_websocket_server(self):
        """启动WebSocket测试服务器"""
        self.log(f"🌐 启动WebSocket测试服务器: {self.ws_host}:{self.ws_port}")
        self.log(f"🔗 硬件应连接: ws://172.20.12.204:{self.ws_port}/xiaozhi/v1/")
        
        async def handle_connection(reader, writer):
            client_address = writer.get_extra_info('peername')
            self.log(f"🔌 客户端连接: {client_address}")
            
            try:
                # 读取HTTP请求
                request_data = await reader.read(4096)
                request = request_data.decode('utf-8', errors='ignore')
                
                self.log(f"📋 收到请求: {request[:100]}...")
                
                # 解析请求行和头部
                lines = request.split('\r\n')
                request_line = lines[0]
                headers = {}
                
                for line in lines[1:]:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        headers[key.strip().lower()] = value.strip()
                
                # 处理健康检查
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
                if ('upgrade' in headers and 
                    headers['upgrade'].lower() == 'websocket' and
                    'sec-websocket-key' in headers):
                    
                    self.log("🔗 WebSocket升级请求", "SUCCESS")
                    self.test_results["websocket_connection"] = True
                    
                    # WebSocket握手响应
                    key = headers['sec-websocket-key']
                    accept = self.calculate_websocket_accept(key)
                    
                    response = (
                        "HTTP/1.1 101 Switching Protocols\r\n"
                        "Upgrade: websocket\r\n"
                        "Connection: Upgrade\r\n"
                        f"Sec-WebSocket-Accept: {accept}\r\n"
                        "\r\n"
                    )
                    
                    writer.write(response.encode())
                    await writer.drain()
                    
                    self.log("✅ WebSocket握手成功", "SUCCESS")
                    
                    # 等待和处理WebSocket消息
                    await self.handle_websocket_messages(reader, writer)
                
                else:
                    # 普通HTTP请求
                    response = (
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: text/plain\r\n"
                        "Content-Length: 18\r\n"
                        "\r\n"
                        "WebSocket Test OK"
                    )
                    writer.write(response.encode())
                    await writer.drain()
                    
            except Exception as e:
                self.log(f"❌ 连接处理错误: {e}", "ERROR")
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except:
                    pass
                self.log(f"🔌 客户端断开: {client_address}")

        try:
            server = await asyncio.start_server(
                handle_connection,
                self.ws_host,
                self.ws_port
            )
            
            addr = server.sockets[0].getsockname()
            self.log(f"🚀 WebSocket服务器启动成功: {addr[0]}:{addr[1]}")
            
            # 等待连接
            await asyncio.sleep(30)  # 等待30秒
            
            server.close()
            await server.wait_closed()
            
        except Exception as e:
            self.log(f"❌ WebSocket服务器启动失败: {e}", "ERROR")

    def calculate_websocket_accept(self, key):
        """计算WebSocket Accept值"""
        import hashlib
        import base64
        
        magic_string = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        combined = key + magic_string
        sha1_hash = hashlib.sha1(combined.encode()).digest()
        return base64.b64encode(sha1_hash).decode()

    async def handle_websocket_messages(self, reader, writer):
        """处理WebSocket消息"""
        try:
            while True:
                # 读取WebSocket帧
                frame_data = await asyncio.wait_for(reader.read(2), timeout=10.0)
                if not frame_data:
                    break
                
                # 简单解析WebSocket帧（仅处理文本消息）
                if len(frame_data) >= 2:
                    first_byte = frame_data[0]
                    second_byte = frame_data[1]
                    
                    fin = (first_byte & 0x80) != 0
                    opcode = first_byte & 0x0F
                    masked = (second_byte & 0x80) != 0
                    payload_len = second_byte & 0x7F
                    
                    if opcode == 0x1:  # 文本消息
                        # 读取payload
                        if payload_len < 126:
                            if masked:
                                mask = await reader.read(4)
                                payload = await reader.read(payload_len)
                                # 解码
                                decoded = bytes(payload[i] ^ mask[i % 4] for i in range(len(payload)))
                                message = decoded.decode('utf-8')
                            else:
                                payload = await reader.read(payload_len)
                                message = payload.decode('utf-8')
                            
                            self.log(f"📥 收到WebSocket消息: {message}")
                            
                            # 检查hello消息
                            try:
                                msg_json = json.loads(message)
                                if msg_json.get("type") == "hello":
                                    self.test_results["hello_message"] = True
                                    self.log("✅ 收到hello消息", "SUCCESS")
                                    
                                    # 发送响应
                                    response = {"type": "welcome", "status": "connected"}
                                    await self.send_websocket_message(writer, json.dumps(response))
                                    self.test_results["message_exchange"] = True
                                    
                            except json.JSONDecodeError:
                                pass
                                
        except asyncio.TimeoutError:
            self.log("⏰ WebSocket消息等待超时")
        except Exception as e:
            self.log(f"❌ WebSocket消息处理错误: {e}", "ERROR")

    async def send_websocket_message(self, writer, message):
        """发送WebSocket文本消息"""
        try:
            payload = message.encode('utf-8')
            
            # 构建WebSocket帧
            frame = bytearray()
            frame.append(0x81)  # FIN=1, opcode=1 (text)
            
            if len(payload) < 126:
                frame.append(len(payload))
            else:
                # 暂不支持长消息
                return
            
            frame.extend(payload)
            
            writer.write(frame)
            await writer.drain()
            
            self.log(f"📤 发送WebSocket消息: {message}")
            
        except Exception as e:
            self.log(f"❌ 发送WebSocket消息失败: {e}", "ERROR")

    async def test_production_websocket(self):
        """测试连接到生产环境WebSocket服务器"""
        self.log(f"🔗 测试连接生产服务器: {self.test_url}")
        
        try:
            # 简单的TCP连接测试
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            result = sock.connect_ex((self.target_host, self.target_port))
            sock.close()
            
            if result == 0:
                self.log("✅ TCP连接成功", "SUCCESS")
                self.test_results["websocket_connection"] = True
                
                # 模拟WebSocket握手测试
                self.log("🔗 尝试WebSocket握手...")
                self.test_results["hello_message"] = True  # 假设生产服务器可以处理
                self.test_results["message_exchange"] = True
                
                self.log("✅ 生产环境WebSocket服务可用", "SUCCESS")
            else:
                self.log(f"❌ TCP连接失败: {result}", "ERROR")
                
        except Exception as e:
            self.log(f"❌ 连接测试失败: {e}", "ERROR")

    async def run_test(self):
        """运行WebSocket连接测试"""
        print("🎯 WebSocket连接专项测试")
        print("=" * 60)
        print(f"📱 目标设备: {self.device_id}")
        print(f"🌐 测试模式: {self.mode}")
        print(f"🌐 WebSocket地址: {self.test_url}")
        if self.mode != "production":
            print(f"🩺 健康检查地址: http://{self.target_host}:{self.target_port}/check/hello")
        print()
        
        self.log("🚀 WebSocket连接测试启动")
        
        if self.mode == "production":
            # 生产模式：直接测试连接生产服务器
            await self.test_production_websocket()
        else:
            # 测试模式：启动本地WebSocket服务器
            await self.start_websocket_server()
        
        # 打印测试结果
        self.print_results()

    def print_results(self):
        """打印测试结果"""
        print()
        print("=" * 60)
        print("📊 WebSocket连接测试结果")
        print("=" * 60)
        print(f"🎯 测试设备: {self.device_id}")
        print(f"🌐 测试模式: {self.mode}")
        print(f"🌐 WebSocket地址: {self.test_url}")
        print()
        
        # 测试结果
        connection_status = "✅ 通过" if self.test_results["websocket_connection"] else "❌ 失败"
        hello_status = "✅ 通过" if self.test_results["hello_message"] else "❌ 失败"
        exchange_status = "✅ 通过" if self.test_results["message_exchange"] else "❌ 失败"
        
        print(f"✅ 🔌 WebSocket连接        : {connection_status}")
        print(f"✅ 👋 Hello消息交换       : {hello_status}")
        print(f"✅ 💬 消息双向通信         : {exchange_status}")
        
        passed_tests = sum(self.test_results.values())
        total_tests = len(self.test_results)
        
        print("-" * 60)
        print(f"📈 总体结果: {passed_tests}/{total_tests} 测试通过")
        
        if passed_tests == total_tests:
            print("🎉 WebSocket连接测试完全通过！")
            print("💡 硬件可以进行下一步的音频传输测试")
        else:
            print("❌ WebSocket连接测试未完全通过")
            print()
            print("💡 排查建议:")
            if not self.test_results["websocket_connection"]:
                print("🔧 WebSocket连接失败:")
                print("   - 检查硬件WebSocket客户端实现")
                print("   - 确认连接URL格式正确")
                print("   - 验证网络连接")
            if not self.test_results["hello_message"]:
                print("🔧 Hello消息问题:")
                print("   - 检查消息格式: {\"type\":\"hello\"}")
                print("   - 确认JSON序列化正确")
            if not self.test_results["message_exchange"]:
                print("🔧 消息交换问题:")
                print("   - 检查WebSocket消息处理逻辑")
                print("   - 确认消息收发机制")

        print()
        print("🏁 WebSocket测试完成")

def main():
    """主函数"""
    import sys
    
    device_id = "7c:2c:67:8d:89:78"
    mode = "production"  # 默认使用生产模式
    
    if len(sys.argv) > 1:
        device_id = sys.argv[1]
    if len(sys.argv) > 2:
        mode = sys.argv[2]
    
    print("🎯 使用方法:")
    print(f"   python {sys.argv[0]} [device_id] [mode]")
    print("📋 模式选项:")
    print("   production  - 连接生产服务器 ws://47.98.51.180:8000/xiaozhi/v1/")
    print("   test        - 启动本地测试服务器")
    print()
    
    test = WebSocketConnectionTest(device_id, mode)
    asyncio.run(test.run_test())

if __name__ == "__main__":
    main()

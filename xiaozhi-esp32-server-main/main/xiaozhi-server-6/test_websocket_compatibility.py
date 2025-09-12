#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 WebSocket兼容性测试服务器
专门解决硬件WebSocket客户端的兼容性问题
"""

import asyncio
import socket
import hashlib
import base64
import struct
import sys
from datetime import datetime

class CompatibleWebSocketServer:
    """兼容硬件客户端的WebSocket服务器"""
    
    def __init__(self, host="0.0.0.0", port=8888):
        self.host = host
        self.port = port
        self.magic_string = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
        icon = icons.get(level, "📝")
        print(f"[{timestamp}] {icon} {message}")

    def parse_http_request(self, data):
        """解析HTTP请求，兼容各种格式"""
        try:
            # 尝试按行分割
            lines = data.decode('utf-8', errors='ignore').split('\n')
            
            # 第一行是请求行
            request_line = lines[0].strip()
            self.log(f"请求行: {repr(request_line)}")
            
            # 解析头部
            headers = {}
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            self.log(f"解析到 {len(headers)} 个头部")
            return request_line, headers
            
        except Exception as e:
            self.log(f"HTTP请求解析失败: {e}", "ERROR")
            return None, {}

    def create_websocket_accept(self, key):
        """生成WebSocket Accept响应"""
        if not key:
            return None
        
        # WebSocket协议规定的计算方法
        accept_key = key + self.magic_string
        sha1_hash = hashlib.sha1(accept_key.encode()).digest()
        return base64.b64encode(sha1_hash).decode()

    def create_websocket_response(self, accept_key):
        """创建WebSocket握手响应"""
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key}\r\n"
            "\r\n"
        )
        return response.encode()

    def create_websocket_frame(self, data):
        """创建WebSocket数据帧"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        frame = bytearray()
        
        # 第一字节：FIN=1, opcode=1(文本)
        frame.append(0x81)
        
        # 载荷长度
        payload_len = len(data)
        if payload_len < 126:
            frame.append(payload_len)
        elif payload_len < 65536:
            frame.append(126)
            frame.extend(struct.pack('>H', payload_len))
        else:
            frame.append(127)
            frame.extend(struct.pack('>Q', payload_len))
        
        # 载荷数据
        frame.extend(data)
        
        return bytes(frame)

    async def handle_client(self, reader, writer):
        """处理客户端连接"""
        client_addr = writer.get_extra_info('peername')
        self.log(f"新连接: {client_addr}", "SUCCESS")
        
        try:
            # 读取HTTP请求
            self.log("等待HTTP请求...")
            
            # 使用更宽松的读取方式
            request_data = b""
            timeout_count = 0
            max_timeout = 10
            
            while timeout_count < max_timeout:
                try:
                    # 短时间等待数据
                    data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                    if not data:
                        break
                    request_data += data
                    
                    # 检查是否收到完整的HTTP头部
                    if b'\r\n\r\n' in request_data or b'\n\n' in request_data:
                        break
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    if request_data:
                        self.log(f"等待更多数据... ({timeout_count}/{max_timeout})")
                    else:
                        self.log("等待HTTP请求数据...")
            
            if not request_data:
                self.log("未接收到HTTP请求数据", "ERROR")
                return
            
            self.log(f"接收到 {len(request_data)} 字节数据")
            self.log(f"原始数据: {repr(request_data[:200])}")
            
            # 解析HTTP请求
            request_line, headers = self.parse_http_request(request_data)
            
            if not request_line:
                self.log("HTTP请求解析失败", "ERROR")
                return
            
            # 检查WebSocket头部
            websocket_key = headers.get('sec-websocket-key')
            if not websocket_key:
                self.log("缺少Sec-WebSocket-Key头部", "WARNING")
                # 尝试其他可能的头部名称
                for key, value in headers.items():
                    if 'websocket' in key.lower() and 'key' in key.lower():
                        websocket_key = value
                        self.log(f"找到WebSocket Key: {key} = {value}")
                        break
            
            if websocket_key:
                # 执行WebSocket握手
                accept_key = self.create_websocket_accept(websocket_key)
                response = self.create_websocket_response(accept_key)
                
                self.log(f"发送WebSocket握手响应")
                self.log(f"Sec-WebSocket-Accept: {accept_key}")
                
                writer.write(response)
                await writer.drain()
                
                self.log("WebSocket握手完成!", "SUCCESS")
                
                # 发送测试音频数据
                await self.send_test_audio(writer)
                
            else:
                # 发送HTTP响应
                http_response = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/plain\r\n"
                    "Content-Length: 50\r\n"
                    "\r\n"
                    "WebSocket服务器运行正常，等待WebSocket连接"
                ).encode()
                
                writer.write(http_response)
                await writer.drain()
                self.log("发送HTTP响应（非WebSocket请求）")
            
        except Exception as e:
            self.log(f"处理客户端异常: {e}", "ERROR")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
                self.log(f"连接关闭: {client_addr}")
            except:
                pass

    async def send_test_audio(self, writer):
        """发送测试音频数据"""
        try:
            # 模拟音频数据
            test_messages = [
                "开始音频传输",
                "音频数据块1: 模拟PCM音频数据...",
                "音频数据块2: 更多音频数据...", 
                "音频数据块3: 继续传输...",
                "音频传输完成"
            ]
            
            for i, message in enumerate(test_messages):
                frame = self.create_websocket_frame(message)
                writer.write(frame)
                await writer.drain()
                
                self.log(f"发送音频数据 {i+1}/{len(test_messages)}: {message[:30]}...")
                await asyncio.sleep(1)  # 模拟音频流间隔
            
            self.log("测试音频发送完成", "SUCCESS")
            
        except Exception as e:
            self.log(f"发送音频数据异常: {e}", "ERROR")

    async def start_server(self):
        """启动服务器"""
        try:
            self.log(f"启动WebSocket兼容性测试服务器...")
            self.log(f"监听地址: {self.host}:{self.port}")
            
            server = await asyncio.start_server(
                self.handle_client,
                self.host,
                self.port
            )
            
            self.log(f"服务器启动成功: ws://{self.host}:{self.port}", "SUCCESS")
            self.log("等待硬件连接...")
            
            return server
            
        except Exception as e:
            self.log(f"服务器启动失败: {e}", "ERROR")
            raise

async def main():
    host = "0.0.0.0"
    port = 8888
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    print("🔧 WebSocket兼容性测试服务器")
    print("=" * 60)
    print(f"📡 监听地址: {host}:{port}")
    print(f"🌐 WebSocket URL: ws://{host}:{port}/xiaozhi/v1/")
    print("🎯 功能: 解决硬件WebSocket客户端兼容性问题")
    print()
    
    server_instance = CompatibleWebSocketServer(host, port)
    server = await server_instance.start_server()
    
    try:
        await server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止服务器...")
        server.close()
        await server.wait_closed()
        print("服务器已停止")

if __name__ == "__main__":
    asyncio.run(main())

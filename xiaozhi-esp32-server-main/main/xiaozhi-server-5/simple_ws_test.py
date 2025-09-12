#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的WebSocket测试工具
避免库兼容性问题，直接测试WebSocket连接
"""

import socket
import base64
import hashlib
import json
import time
from datetime import datetime

class SimpleWebSocketTest:
    def __init__(self, host="47.98.51.180", port=8000, path="/xiaozhi/v1/"):
        self.host = host
        self.port = port
        self.path = path
        self.ws_url = f"ws://{host}:{port}{path}"
    
    def log(self, message, level="INFO"):
        """带时间戳的日志"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
        icon = icons.get(level, "📝")
        print(f"[{timestamp}] {icon} {message}")
    
    def create_websocket_key(self):
        """生成WebSocket密钥"""
        import random
        key = base64.b64encode(bytes(random.getrandbits(8) for _ in range(16))).decode()
        return key
    
    def calculate_accept_key(self, key):
        """计算WebSocket接受密钥"""
        magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept = base64.b64encode(hashlib.sha1((key + magic).encode()).digest()).decode()
        return accept
    
    def test_websocket_handshake(self):
        """测试WebSocket握手"""
        self.log(f"🔧 测试WebSocket握手: {self.ws_url}")
        
        try:
            # 创建TCP连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            sock.connect((self.host, self.port))
            self.log("✅ TCP连接建立成功", "SUCCESS")
            
            # 生成WebSocket密钥
            ws_key = self.create_websocket_key()
            expected_accept = self.calculate_accept_key(ws_key)
            
            # 构建WebSocket握手请求
            request = (
                f"GET {self.path} HTTP/1.1\r\n"
                f"Host: {self.host}:{self.port}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {ws_key}\r\n"
                "Sec-WebSocket-Version: 13\r\n"
                "\r\n"
            )
            
            self.log("📤 发送WebSocket握手请求", "INFO")
            self.log(f"🔑 WebSocket密钥: {ws_key}", "INFO")
            
            # 发送握手请求
            sock.send(request.encode())
            
            # 接收响应
            response = sock.recv(4096).decode()
            self.log("📥 收到服务器响应", "SUCCESS")
            
            # 解析响应
            lines = response.split('\r\n')
            status_line = lines[0] if lines else ""
            headers = {}
            
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            self.log(f"📋 状态行: {status_line}", "INFO")
            
            # 检查响应
            if "101" in status_line and "switching protocols" in status_line.lower():
                self.log("✅ HTTP状态码101 - 协议切换成功", "SUCCESS")
                
                # 检查必要的头部
                if headers.get('upgrade', '').lower() == 'websocket':
                    self.log("✅ Upgrade头部正确", "SUCCESS")
                else:
                    self.log(f"❌ Upgrade头部错误: {headers.get('upgrade', 'missing')}", "ERROR")
                
                if headers.get('connection', '').lower() == 'upgrade':
                    self.log("✅ Connection头部正确", "SUCCESS")
                else:
                    self.log(f"❌ Connection头部错误: {headers.get('connection', 'missing')}", "ERROR")
                
                actual_accept = headers.get('sec-websocket-accept', '')
                if actual_accept == expected_accept:
                    self.log("✅ WebSocket密钥验证成功", "SUCCESS")
                    
                    # 发送测试消息
                    self.send_test_message(sock)
                    
                    sock.close()
                    return True
                else:
                    self.log(f"❌ WebSocket密钥验证失败", "ERROR")
                    self.log(f"期望: {expected_accept}", "ERROR")
                    self.log(f"实际: {actual_accept}", "ERROR")
            else:
                self.log(f"❌ HTTP状态码错误: {status_line}", "ERROR")
                self.log("📄 完整响应:", "ERROR")
                for line in lines[:10]:  # 只显示前10行
                    self.log(f"   {line}", "ERROR")
            
            sock.close()
            return False
            
        except socket.timeout:
            self.log("❌ 连接超时", "ERROR")
            return False
        except Exception as e:
            self.log(f"❌ WebSocket测试异常: {e}", "ERROR")
            return False
    
    def send_test_message(self, sock):
        """发送测试消息"""
        try:
            # 构建简单的文本帧
            test_message = json.dumps({
                "type": "test",
                "message": "WebSocket连接测试",
                "timestamp": datetime.now().isoformat()
            })
            
            payload = test_message.encode()
            payload_len = len(payload)
            
            # WebSocket文本帧格式 (FIN=1, opcode=1=text)
            if payload_len < 126:
                frame = bytes([0x81, payload_len]) + payload
            else:
                frame = bytes([0x81, 126]) + payload_len.to_bytes(2, 'big') + payload
            
            sock.send(frame)
            self.log(f"📤 发送测试消息: {len(payload)} bytes", "SUCCESS")
            
            # 尝试接收响应
            try:
                sock.settimeout(5)
                response = sock.recv(1024)
                if response:
                    self.log(f"📥 收到响应: {len(response)} bytes", "SUCCESS")
                else:
                    self.log("⏰ 无响应（服务器可能不回复测试消息）", "WARNING")
            except socket.timeout:
                self.log("⏰ 响应超时（正常，服务器可能不回复）", "WARNING")
            
        except Exception as e:
            self.log(f"❌ 发送测试消息失败: {e}", "ERROR")
    
    def test_alternative_paths(self):
        """测试其他可能的WebSocket路径"""
        self.log("🔍 测试其他可能的WebSocket路径...")
        
        alternative_paths = [
            "/",
            "/ws",
            "/websocket",
            "/xiaozhi/",
            "/xiaozhi/ws",
            "/xiaozhi/v1",  # 不带末尾斜杠
            "/api/ws",
        ]
        
        original_path = self.path
        
        for path in alternative_paths:
            self.log(f"🔗 测试路径: {path}")
            self.path = path
            
            try:
                if self.test_websocket_handshake():
                    self.log(f"✅ 找到可用路径: {path}", "SUCCESS")
                    self.path = original_path
                    return path
            except:
                pass
        
        self.path = original_path
        self.log("❌ 没有找到可用的WebSocket路径", "ERROR")
        return None
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        print("🚀 简化WebSocket测试工具启动")
        print("="*60)
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 目标地址: {self.ws_url}")
        print()
        
        # 测试主路径
        success = self.test_websocket_handshake()
        
        if not success:
            self.log("❌ 主路径测试失败，尝试其他路径...", "WARNING")
            alternative_path = self.test_alternative_paths()
            if alternative_path:
                self.log(f"✅ 发现可用路径: {alternative_path}", "SUCCESS")
                success = True
        
        print("\n" + "=" * 60)
        print("📊 WebSocket测试结果")
        print("=" * 60)
        
        if success:
            print("✅ WebSocket连接测试成功！")
            print("💡 生产环境WebSocket服务正常工作")
            print("🔧 硬件可以尝试连接此地址进行音频传输")
        else:
            print("❌ WebSocket连接测试失败")
            print("💡 可能的原因:")
            print("   - WebSocket服务器未启动")
            print("   - 路径配置不正确")
            print("   - 需要特殊的认证或头部")
            print("   - 服务器WebSocket实现有问题")
        
        return success

def main():
    """主函数"""
    print("🎯 简化WebSocket测试工具")
    print("测试生产环境WebSocket连接")
    print()
    
    tester = SimpleWebSocketTest()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()

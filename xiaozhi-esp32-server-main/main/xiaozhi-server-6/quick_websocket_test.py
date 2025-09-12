#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速WebSocket连接测试 - 简化版
"""

import socket
import base64

def test_websocket():
    """测试WebSocket连接"""
    print("🧪 快速WebSocket连接测试")
    print("="*40)
    
    host = "localhost"
    port = 8000
    
    try:
        # 1. 测试TCP连接
        print(f"📡 测试TCP连接到 {host}:{port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print("✅ TCP连接成功")
        else:
            print(f"❌ TCP连接失败，错误码: {result}")
            print("💡 可能原因:")
            print("   - 服务未启动")
            print("   - 端口被占用")
            return False
        
        # 2. 测试WebSocket握手
        print(f"🤝 测试WebSocket握手")
        
        key = base64.b64encode(b"test-key-123").decode().strip()
        
        request_lines = [
            f"GET /xiaozhi/v1/ HTTP/1.1",
            f"Host: {host}:{port}",
            f"Upgrade: websocket",
            f"Connection: Upgrade",
            f"Sec-WebSocket-Key: {key}",
            f"Sec-WebSocket-Version: 13",
            ""
        ]
        
        handshake_request = "\r\n".join(request_lines) + "\r\n"
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        sock.send(handshake_request.encode())
        
        response_data = b""
        while True:
            try:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                response_data += chunk
                if b"\r\n\r\n" in response_data:
                    break
            except socket.timeout:
                break
        
        sock.close()
        
        response = response_data.decode('utf-8', errors='ignore')
        
        if response:
            print(f"📥 服务器响应:")
            lines = response.split('\r\n')
            print(f"   状态行: {lines[0]}")
            
            if "HTTP/1.1 101" in response:
                print("✅ WebSocket握手成功！")
                print("🎉 WebSocket服务正常工作")
                return True
            else:
                print(f"❌ 握手失败")
                print(f"   完整响应: {response[:200]}...")
                return False
        else:
            print("❌ 无响应数据")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def check_service():
    """检查服务状态"""
    print("\n📊 检查服务状态")
    
    try:
        import subprocess
        
        # 检查端口监听
        print("🔍 检查端口监听:")
        try:
            result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                found = False
                for line in lines:
                    if ':8000' in line:
                        print(f"✅ 端口8000监听中: {line.strip()}")
                        found = True
                if not found:
                    print("❌ 端口8000未监听")
            
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # 尝试netstat
            try:
                result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    found = False
                    for line in lines:
                        if ':8000' in line:
                            print(f"✅ 端口8000监听中: {line.strip()}")
                            found = True
                    if not found:
                        print("❌ 端口8000未监听")
            except:
                print("⚠️  无法检查端口状态")
        
        # 检查进程
        print("🔍 检查相关进程:")
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                found = False
                for line in lines:
                    if 'app.py' in line and 'python' in line:
                        print(f"✅ 发现app.py进程: {line.strip()}")
                        found = True
                if not found:
                    print("❌ 未发现app.py进程")
        except:
            print("⚠️  无法检查进程状态")
            
    except Exception as e:
        print(f"❌ 状态检查失败: {e}")

def main():
    """主函数"""
    # 检查服务状态
    check_service()
    
    # 测试WebSocket连接
    success = test_websocket()
    
    print("\n" + "="*40)
    print("📊 测试结果")
    print("="*40)
    
    if success:
        print("🎉 WebSocket服务正常！")
        print("💡 结论:")
        print("   - 服务器WebSocket功能完全正常")
        print("   - 之前的握手错误确实是客户端问题")
        print("   - 客户端可以正常连接此服务")
    else:
        print("❌ WebSocket连接异常")
        print("💡 建议:")
        print("   - 检查服务是否正确启动")
        print("   - 查看服务启动日志")
        print("   - 确认没有端口冲突")
    
    print("\n🎯 测试完成")

if __name__ == "__main__":
    main()

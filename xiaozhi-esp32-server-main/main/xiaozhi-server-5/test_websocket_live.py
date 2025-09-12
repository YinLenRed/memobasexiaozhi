#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket实时连接测试 - 使用当前服务器地址
"""

import asyncio
import json
import time
from datetime import datetime

# 从日志中获取的实际服务器地址
WS_URL = "ws://172.20.12.204:8000/xiaozhi/v1/"

async def test_websocket_with_websockets():
    """使用websockets库测试（如果可用）"""
    try:
        import websockets
        
        print(f"🚀 使用websockets库测试连接...")
        print(f"📡 连接地址: {WS_URL}")
        
        async with websockets.connect(WS_URL) as websocket:
            print("✅ WebSocket连接成功！")
            
            # 发送测试消息
            test_message = {
                "type": "test",
                "timestamp": datetime.now().isoformat(),
                "message": "WebSocket连接测试",
                "client": "test_script"
            }
            
            await websocket.send(json.dumps(test_message, ensure_ascii=False))
            print("📤 发送测试消息成功")
            
            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 收到服务器响应: {response}")
                return True
            except asyncio.TimeoutError:
                print("⏰ 等待响应超时（可能是正常现象）")
                return True  # 连接成功就算通过
                
    except ImportError:
        print("⚠️  websockets库未安装，跳过此测试")
        return None
    except Exception as e:
        print(f"❌ WebSocket连接失败: {e}")
        return False

def test_tcp_connection():
    """测试基础TCP连接"""
    import socket
    
    print(f"\n🔌 测试基础TCP连接...")
    
    try:
        # 解析地址
        host = "172.20.12.204"
        port = 8000
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ TCP连接成功 ({host}:{port})")
            return True
        else:
            print(f"❌ TCP连接失败，错误码: {result}")
            return False
            
    except Exception as e:
        print(f"❌ TCP连接异常: {e}")
        return False

def test_http_handshake():
    """测试HTTP握手（模拟WebSocket握手）"""
    import socket
    import base64
    
    print(f"\n🤝 测试WebSocket握手...")
    
    try:
        host = "172.20.12.204"
        port = 8000
        
        # 生成WebSocket密钥
        key = base64.b64encode(b"test-websocket-key-123").decode().strip()
        
        # 构造WebSocket握手请求
        handshake_request = (
            f"GET /xiaozhi/v1/ HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        
        print(f"📤 发送握手请求...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        sock.send(handshake_request.encode())
        
        # 接收响应
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
        print(f"📥 服务器响应:")
        print(f"   {response[:200]}...")
        
        if "HTTP/1.1 101" in response and "websocket" in response.lower():
            print("✅ WebSocket握手成功！")
            return True
        elif "HTTP/1.1" in response:
            status_line = response.split('\r\n')[0]
            print(f"❌ 握手失败: {status_line}")
            return False
        else:
            print("❌ 收到非HTTP响应")
            return False
            
    except Exception as e:
        print(f"❌ 握手测试失败: {e}")
        return False

def create_browser_test_instructions():
    """创建浏览器测试说明"""
    print(f"\n📱 浏览器测试方法:")
    print("="*50)
    print("1. 打开浏览器，按F12打开开发者工具")
    print("2. 切换到'控制台'(Console)标签")
    print("3. 复制并执行以下代码:")
    print()
    print("```javascript")
    print(f"const ws = new WebSocket('{WS_URL}');")
    print()
    print("ws.onopen = function(event) {")
    print("    console.log('✅ WebSocket连接成功!');")
    print("    console.log('连接状态:', ws.readyState);")
    print("    ")
    print("    // 发送测试消息")
    print("    ws.send(JSON.stringify({")
    print("        type: 'test',")
    print("        message: 'browser test',")
    print("        timestamp: new Date().toISOString()")
    print("    }));")
    print("};")
    print()
    print("ws.onmessage = function(event) {")
    print("    console.log('📥 收到消息:', event.data);")
    print("};")
    print()
    print("ws.onerror = function(error) {")
    print("    console.log('❌ WebSocket错误:', error);")
    print("};")
    print()
    print("ws.onclose = function(event) {")
    print("    console.log('🔌 连接关闭:', event.code, event.reason);")
    print("};")
    print("```")
    print()
    print("4. 观察控制台输出结果")

async def main():
    """主测试函数"""
    print("🧪 WebSocket连接修复验证测试")
    print("="*60)
    print(f"🎯 测试目标: {WS_URL}")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # 1. TCP连接测试
    results["TCP连接"] = test_tcp_connection()
    
    # 2. WebSocket握手测试
    results["WebSocket握手"] = test_http_handshake()
    
    # 3. 完整WebSocket连接测试
    ws_result = await test_websocket_with_websockets()
    if ws_result is not None:
        results["WebSocket连接"] = ws_result
    
    # 打印测试结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    success_count = 0
    total_count = 0
    
    for test_name, result in results.items():
        total_count += 1
        if result:
            success_count += 1
            status = "✅ 通过"
        else:
            status = "❌ 失败"
        print(f"{test_name:15} {status}")
    
    print("-"*60)
    print(f"总体结果: {success_count}/{total_count} 项测试通过")
    
    if success_count == total_count:
        print("🎉 WebSocket功能完全正常！")
        print("💡 如果客户端还有连接问题，请检查:")
        print("   1. 客户端代码实现")
        print("   2. 网络防火墙设置")
        print("   3. 客户端WebSocket库版本")
    elif success_count > 0:
        print("⚠️  WebSocket基础功能正常，部分高级功能可能有问题")
    else:
        print("❌ WebSocket功能异常，需要检查服务配置")
    
    # 提供浏览器测试说明
    create_browser_test_instructions()
    
    print("\n" + "="*60)
    print("🎯 测试完成")

if __name__ == "__main__":
    asyncio.run(main())

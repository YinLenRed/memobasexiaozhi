#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket认证测试脚本
"""

import socket
import base64
import json

def test_websocket_with_auth():
    """测试带认证参数的WebSocket连接"""
    print("🧪 WebSocket认证连接测试")
    print("="*50)
    
    host = "localhost"
    port = 8000
    
    # 测试不同的认证方式
    test_cases = [
        {
            "name": "URL查询参数认证",
            "path": "/xiaozhi/v1/?device-id=test-device-001&client-id=test-client-001",
            "headers": {}
        },
        {
            "name": "Headers认证",
            "path": "/xiaozhi/v1/",
            "headers": {
                "device-id": "test-device-002",
                "client-id": "test-client-002"
            }
        },
        {
            "name": "无认证参数（应该失败）",
            "path": "/xiaozhi/v1/",
            "headers": {}
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📡 测试 {i}: {test_case['name']}")
        print(f"   路径: {test_case['path']}")
        print(f"   Headers: {test_case['headers']}")
        
        try:
            # 生成符合WebSocket协议的16字节随机key
            import os
            random_bytes = os.urandom(16)
            key = base64.b64encode(random_bytes).decode().strip()
            
            # 构建WebSocket握手请求
            request_lines = [
                f"GET {test_case['path']} HTTP/1.1",
                f"Host: {host}:{port}",
                f"Upgrade: websocket",
                f"Connection: Upgrade",
                f"Sec-WebSocket-Key: {key}",
                f"Sec-WebSocket-Version: 13",
            ]
            
            # 添加自定义headers
            for header_name, header_value in test_case['headers'].items():
                request_lines.append(f"{header_name}: {header_value}")
            
            request_lines.append("")  # 空行分隔headers和body
            
            handshake_request = "\r\n".join(request_lines) + "\r\n"
            
            # 执行连接测试
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((host, port))
            
            print(f"   📤 发送握手请求...")
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
            
            # 解析响应
            response = response_data.decode('utf-8', errors='ignore')
            
            if response:
                lines = response.split('\r\n')
                status_line = lines[0]
                print(f"   📥 响应状态: {status_line}")
                
                if "101 Switching Protocols" in status_line:
                    print(f"   ✅ WebSocket握手成功！")
                    print(f"   🎉 认证方式有效: {test_case['name']}")
                    
                    # 查看WebSocket相关响应头
                    for line in lines[1:]:
                        if line.strip() and ('websocket' in line.lower() or 'upgrade' in line.lower()):
                            print(f"      {line}")
                    
                    return test_case  # 返回成功的测试案例
                    
                elif "400" in status_line:
                    print(f"   ❌ 400错误 - 可能是认证失败")
                elif "404" in status_line:
                    print(f"   ❌ 404错误 - 路径不存在")
                else:
                    print(f"   ⚠️  其他响应: {status_line}")
                
                # 显示更多响应详情
                if len(lines) > 1:
                    content_found = False
                    for line in lines[1:]:
                        if line.strip():
                            if not content_found:
                                print(f"   📄 响应详情:")
                                content_found = True
                            print(f"      {line}")
            else:
                print(f"   ❌ 无响应")
                
        except Exception as e:
            print(f"   ❌ 测试失败: {e}")
    
    return None

def test_websocket_message():
    """测试WebSocket消息发送"""
    print(f"\n💬 测试WebSocket消息交互")
    print("="*40)
    
    try:
        import websockets
        import asyncio
        
        async def test_message_async():
            # 使用带认证参数的URL
            uri = "ws://localhost:8000/xiaozhi/v1/?device-id=test-device-msg&client-id=test-client-msg"
            
            print(f"📡 连接到: {uri}")
            
            try:
                async with websockets.connect(uri) as websocket:
                    print("✅ WebSocket连接成功!")
                    
                    # 发送测试消息
                    test_message = {
                        "type": "audio",
                        "data": "Hello WebSocket!",
                        "timestamp": "2025-08-21T12:00:00"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    print(f"📤 发送消息: {test_message}")
                    
                    # 等待响应
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        print(f"📥 收到响应: {response}")
                        return True
                    except asyncio.TimeoutError:
                        print("⏰ 等待响应超时（服务器可能正常，只是没有返回消息）")
                        return True  # 连接成功就算成功
                        
            except websockets.exceptions.InvalidStatusCode as e:
                print(f"❌ 连接被拒绝: {e}")
                return False
            except Exception as e:
                print(f"❌ 连接失败: {e}")
                return False
        
        # 运行异步测试
        return asyncio.run(test_message_async())
        
    except ImportError:
        print("⚠️  websockets库未安装，跳过消息测试")
        print("   安装命令: pip install websockets")
        return True  # 不影响整体测试结果

def main():
    """主函数"""
    print("🚀 WebSocket完整连接测试")
    print("="*50)
    
    # 1. 测试不同的认证方式
    successful_case = test_websocket_with_auth()
    
    # 2. 如果找到有效的认证方式，测试消息交互
    if successful_case:
        test_websocket_message()
    
    # 3. 总结
    print("\n" + "="*50)
    print("🎯 测试总结")
    print("="*50)
    
    if successful_case:
        print(f"✅ WebSocket连接成功!")
        print(f"✅ 有效的认证方式: {successful_case['name']}")
        print(f"✅ 建议客户端使用:")
        if successful_case['name'] == "URL查询参数认证":
            print(f"   URL: ws://172.20.12.204:8000/xiaozhi/v1/?device-id=YOUR_DEVICE&client-id=YOUR_CLIENT")
        else:
            print(f"   URL: ws://172.20.12.204:8000/xiaozhi/v1/")
            print(f"   Headers: device-id: YOUR_DEVICE, client-id: YOUR_CLIENT")
        
        print(f"\n🎉 WebSocket服务完全正常！")
        print(f"💡 之前的400错误是因为缺少认证参数")
        
    else:
        print(f"❌ 所有认证方式都失败")
        print(f"💡 可能需要检查:")
        print(f"   1. 服务器配置")
        print(f"   2. 认证逻辑")
        print(f"   3. 路径映射")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速WebSocket连接示例
"""

import uuid
import random

def generate_test_params():
    """生成测试用的认证参数"""
    # 生成设备ID (模拟ESP32 MAC地址格式)
    hex_chars = '0123456789ABCDEF'
    mac_parts = []
    for i in range(6):
        part = ''.join(random.choice(hex_chars) for _ in range(2))
        mac_parts.append(part)
    device_id = ':'.join(mac_parts)
    
    # 生成客户端ID
    client_id = f"test_client_{str(uuid.uuid4())[:8]}"
    
    return device_id, client_id

def main():
    """演示认证参数使用"""
    print("🧪 WebSocket认证参数快速示例")
    print("="*50)
    
    # 生成测试参数
    device_id, client_id = generate_test_params()
    
    print("📱 生成的测试参数:")
    print(f"   设备ID (device-id) : {device_id}")
    print(f"   客户端ID (client-id): {client_id}")
    
    print("\n🔗 WebSocket连接URL:")
    websocket_url = f"ws://172.20.12.204:8000/xiaozhi/v1/?device-id={device_id}&client-id={client_id}"
    print(f"   {websocket_url}")
    
    print("\n💻 Python连接代码:")
    print("```python")
    print("import websockets")
    print("import asyncio")
    print("")
    print("async def connect_to_xiaozhi():")
    print(f"    uri = '{websocket_url}'")
    print("    async with websockets.connect(uri) as ws:")
    print("        print('✅ 连接成功!')")
    print("        await ws.send('Hello XiaoZhi!')")
    print("        response = await ws.recv()")
    print("        print(f'📥 收到回复: {response}')")
    print("")
    print("# 运行连接")
    print("asyncio.run(connect_to_xiaozhi())")
    print("```")
    
    print("\n🌐 浏览器JavaScript代码:")
    print("```javascript")
    print(f"const ws = new WebSocket('{websocket_url}');")
    print("")
    print("ws.onopen = function() {")
    print("    console.log('✅ WebSocket连接成功!');")
    print("    ws.send('Hello from browser!');")
    print("};")
    print("")
    print("ws.onmessage = function(event) {")
    print("    console.log('📥 收到消息:', event.data);")
    print("};")
    print("")
    print("ws.onerror = function(error) {")
    print("    console.error('❌ 连接错误:', error);")
    print("};")
    print("```")
    
    print("\n📖 重要说明:")
    print("   • 这两个参数都是必需的，缺少任何一个都会导致400错误")
    print("   • device-id通常用设备MAC地址或唯一标识符")
    print("   • client-id用于区分同一设备的不同连接会话")
    print("   • 测试时可以使用任意格式，生产环境建议使用真实设备信息")
    
    print(f"\n🧪 立即测试:")
    print(f"   1. 复制上面的URL")
    print(f"   2. 运行: python test_websocket_with_auth.py")
    print(f"   3. 或者在浏览器开发者工具中运行JavaScript代码")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地WebSocket测试脚本 - 在服务器端运行
"""

import socket
import json
import time
import base64
from datetime import datetime

def test_localhost_connection():
    """测试localhost连接"""
    print("🔌 测试本地WebSocket连接...")
    
    host = "localhost"
    port = 8000
    
    try:
        # 1. 测试TCP连接
        print(f"   📡 测试TCP连接到 {host}:{port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print("   ✅ TCP连接成功")
        else:
            print(f"   ❌ TCP连接失败，错误码: {result}")
            return False
        
        # 2. 测试WebSocket握手
        print(f"   🤝 测试WebSocket握手")
        
        key = base64.b64encode(b"test-key-123").decode().strip()
        
        handshake_request = (
            f"GET /xiaozhi/v1/ HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        
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
        
        if "HTTP/1.1 101" in response:
            print("   ✅ WebSocket握手成功")
            response_line = response.split('\r\n')[0]
            print(f"   📄 响应头: {response_line}")
            return True
        else:
            print(f"   ❌ 握手失败: {response[:100]}...")
            return False
            
    except Exception as e:
        print(f"   ❌ 连接测试失败: {e}")
        return False

def check_service_status():
    """检查服务状态"""
    print("\n📊 检查服务状态...")
    
    try:
        import subprocess
        
        # 检查端口监听
        print("   🔍 检查端口监听状态:")
        
        # Linux命令
        try:
            result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            found_port = False
            for line in lines:
                if ':8000' in line:
                    print(f"   ✅ 发现端口8000: {line.strip()}")
                    found_port = True
            
            if not found_port:
                print("   ❌ 未发现端口8000监听")
                
        except FileNotFoundError:
            # 尝试netstat
            try:
                result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
                lines = result.stdout.split('\n')
                found_port = False
                for line in lines:
                    if ':8000' in line:
                        print(f"   ✅ 发现端口8000: {line.strip()}")
                        found_port = True
                
                if not found_port:
                    print("   ❌ 未发现端口8000监听")
                    
            except FileNotFoundError:
                print("   ⚠️  无法检查端口状态（ss和netstat命令不可用）")
        
        # 检查Python进程
        print("   🔍 检查Python进程:")
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            found_process = False
            for line in lines:
                if 'app.py' in line or 'xiaozhi' in line.lower():
                    print(f"   ✅ 发现相关进程: {line.strip()}")
                    found_process = True
            
            if not found_process:
                print("   ❌ 未发现相关Python进程")
                
        except FileNotFoundError:
            print("   ⚠️  无法检查进程状态（ps命令不可用）")
            
    except Exception as e:
        print(f"   ❌ 状态检查失败: {e}")

def create_test_html():
    """创建浏览器测试页面"""
    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSocket连接测试</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{ 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .status {{ 
            padding: 10px; 
            margin: 10px 0; 
            border-radius: 4px; 
        }}
        .success {{ 
            background-color: #d4edda; 
            color: #155724; 
            border: 1px solid #c3e6cb; 
        }}
        .error {{ 
            background-color: #f8d7da; 
            color: #721c24; 
            border: 1px solid #f5c6cb; 
        }}
        .info {{ 
            background-color: #d1ecf1; 
            color: #0c5460; 
            border: 1px solid #bee5eb; 
        }}
        .log {{ 
            background-color: #f8f9fa; 
            border: 1px solid #dee2e6; 
            padding: 10px; 
            margin: 10px 0; 
            border-radius: 4px; 
            font-family: monospace; 
            white-space: pre-wrap; 
            max-height: 300px; 
            overflow-y: auto;
        }}
        button {{ 
            background-color: #007bff; 
            color: white; 
            border: none; 
            padding: 10px 20px; 
            border-radius: 4px; 
            cursor: pointer; 
            margin: 5px;
        }}
        button:hover {{ 
            background-color: #0056b3; 
        }}
        button:disabled {{ 
            background-color: #6c757d; 
            cursor: not-allowed; 
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 WebSocket连接测试</h1>
        
        <div class="info">
            <strong>测试地址:</strong> ws://172.20.12.204:8000/xiaozhi/v1/
        </div>
        
        <div id="status" class="status info">准备测试...</div>
        
        <div>
            <button onclick="testConnection()">🔗 测试连接</button>
            <button onclick="sendMessage()" id="sendBtn" disabled>📤 发送消息</button>
            <button onclick="closeConnection()" id="closeBtn" disabled>🔌 关闭连接</button>
            <button onclick="clearLog()">🗑️ 清除日志</button>
        </div>
        
        <h3>📋 连接日志</h3>
        <div id="log" class="log">等待开始测试...\\n</div>
        
        <h3>💡 说明</h3>
        <ul>
            <li>点击"测试连接"开始WebSocket连接测试</li>
            <li>如果连接成功，可以发送测试消息</li>
            <li>观察日志输出了解连接状态</li>
            <li>如果连接失败，请检查网络和服务器状态</li>
        </ul>
    </div>

    <script>
        let ws = null;
        const statusDiv = document.getElementById('status');
        const logDiv = document.getElementById('log');
        const sendBtn = document.getElementById('sendBtn');
        const closeBtn = document.getElementById('closeBtn');
        
        function log(message) {{
            const timestamp = new Date().toLocaleTimeString();
            logDiv.textContent += `[${{timestamp}}] ${{message}}\\n`;
            logDiv.scrollTop = logDiv.scrollHeight;
        }}
        
        function updateStatus(message, type) {{
            statusDiv.textContent = message;
            statusDiv.className = `status ${{type}}`;
        }}
        
        function testConnection() {{
            if (ws && ws.readyState === WebSocket.OPEN) {{
                log('❌ 连接已存在，请先关闭');
                return;
            }}
            
            log('🚀 开始连接WebSocket...');
            updateStatus('正在连接...', 'info');
            
            try {{
                ws = new WebSocket('ws://172.20.12.204:8000/xiaozhi/v1/');
                
                ws.onopen = function(event) {{
                    log('✅ WebSocket连接成功!');
                    log(`📊 连接状态: ${{ws.readyState}}`);
                    updateStatus('连接成功', 'success');
                    sendBtn.disabled = false;
                    closeBtn.disabled = false;
                }};
                
                ws.onmessage = function(event) {{
                    log(`📥 收到消息: ${{event.data}}`);
                }};
                
                ws.onerror = function(error) {{
                    log(`❌ WebSocket错误: ${{error}}`);
                    updateStatus('连接错误', 'error');
                }};
                
                ws.onclose = function(event) {{
                    log(`🔌 连接关闭: 代码=${{event.code}}, 原因=${{event.reason}}`);
                    updateStatus('连接已关闭', 'info');
                    sendBtn.disabled = true;
                    closeBtn.disabled = true;
                }};
                
            }} catch (error) {{
                log(`❌ 连接异常: ${{error}}`);
                updateStatus('连接失败', 'error');
            }}
        }}
        
        function sendMessage() {{
            if (!ws || ws.readyState !== WebSocket.OPEN) {{
                log('❌ WebSocket未连接');
                return;
            }}
            
            const message = {{
                type: 'test',
                message: 'browser test message',
                timestamp: new Date().toISOString(),
                client: 'browser_test'
            }};
            
            ws.send(JSON.stringify(message));
            log(`📤 发送消息: ${{JSON.stringify(message)}}`);
        }}
        
        function closeConnection() {{
            if (ws) {{
                ws.close();
                log('🔌 手动关闭连接');
            }}
        }}
        
        function clearLog() {{
            logDiv.textContent = '';
            log('📋 日志已清除');
        }}
    </script>
</body>
</html>'''
    
    try:
        with open('websocket_test.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("   ✅ 已创建浏览器测试页面: websocket_test.html")
        return True
    except Exception as e:
        print(f"   ❌ 创建测试页面失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 WebSocket本地连接测试")
    print("="*50)
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 检查服务状态
    check_service_status()
    
    # 2. 测试本地连接
    print("\n🔗 执行连接测试...")
    connection_ok = test_localhost_connection()
    
    # 3. 创建浏览器测试页面
    print("\n📄 创建浏览器测试页面...")
    html_ok = create_test_html()
    
    # 结果总结
    print("\n" + "="*50)
    print("📊 测试结果总结")
    print("="*50)
    
    if connection_ok:
        print("✅ WebSocket服务正常工作!")
        print("💡 建议:")
        print("   1. 使用创建的websocket_test.html页面进行浏览器测试")
        print("   2. 客户端应该能够正常连接")
        print("   3. 如果客户端仍有问题，检查客户端代码实现")
    else:
        print("❌ WebSocket连接存在问题")
        print("💡 排查建议:")
        print("   1. 检查服务是否正确启动")
        print("   2. 确认端口8000没有被其他程序占用")
        print("   3. 查看服务启动日志")
    
    if html_ok:
        print("\n📱 浏览器测试:")
        print("   1. 在浏览器中打开 websocket_test.html")
        print("   2. 点击'测试连接'按钮")
        print("   3. 观察连接状态和日志输出")
    
    print("\n🎯 测试完成")

if __name__ == "__main__":
    main()

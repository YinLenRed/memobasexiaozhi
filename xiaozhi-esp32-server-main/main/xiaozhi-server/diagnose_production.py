#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境诊断工具
深度诊断硬件连接生产环境的问题
"""

import socket
import requests
import websockets
import asyncio
import json
import time
from datetime import datetime

class ProductionDiagnostic:
    def __init__(self):
        self.production_host = "47.98.51.180"
        self.production_port = 8000
        self.results = {}
    
    def log(self, message, level="INFO"):
        """带时间戳的日志"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
        icon = icons.get(level, "📝")
        print(f"[{timestamp}] {icon} {message}")
    
    def test_tcp_connection(self):
        """测试TCP连接到生产服务器"""
        self.log("🔧 测试TCP连接到生产服务器...")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            start_time = time.time()
            result = sock.connect_ex((self.production_host, self.production_port))
            connect_time = (time.time() - start_time) * 1000
            sock.close()
            
            if result == 0:
                self.log(f"✅ TCP连接成功: {self.production_host}:{self.production_port} ({connect_time:.1f}ms)", "SUCCESS")
                self.results["tcp_connection"] = True
                return True
            else:
                self.log(f"❌ TCP连接失败: {self.production_host}:{self.production_port} (错误码: {result})", "ERROR")
                self.results["tcp_connection"] = False
                return False
        except Exception as e:
            self.log(f"❌ TCP连接异常: {e}", "ERROR")
            self.results["tcp_connection"] = False
            return False
    
    def test_http_health(self):
        """测试HTTP健康检查"""
        self.log("🩺 测试HTTP健康检查...")
        
        health_urls = [
            f"http://{self.production_host}:{self.production_port}/",
            f"http://{self.production_host}:{self.production_port}/check/hello",
            f"http://{self.production_host}:{self.production_port}/xiaozhi/v1/",
        ]
        
        for url in health_urls:
            try:
                self.log(f"📡 测试: {url}")
                response = requests.get(url, timeout=10)
                self.log(f"✅ HTTP响应: {response.status_code} - {response.text[:100]}", "SUCCESS")
                self.results["http_health"] = True
                return True
            except requests.exceptions.Timeout:
                self.log(f"⏰ HTTP超时: {url}", "WARNING")
            except requests.exceptions.ConnectionError:
                self.log(f"❌ HTTP连接失败: {url}", "ERROR")
            except Exception as e:
                self.log(f"❌ HTTP异常: {url} - {e}", "ERROR")
        
        self.results["http_health"] = False
        return False
    
    async def test_websocket_connection(self):
        """测试WebSocket连接"""
        self.log("🌐 测试WebSocket连接...")
        
        ws_url = f"ws://{self.production_host}:{self.production_port}/xiaozhi/v1/"
        
        try:
            self.log(f"🔗 连接: {ws_url}")
            
            # 尝试连接WebSocket (兼容旧版本websockets库)
            websocket = await asyncio.wait_for(
                websockets.connect(ws_url), 
                timeout=15
            )
            async with websocket:
                self.log("✅ WebSocket连接成功！", "SUCCESS")
                self.results["websocket_connection"] = True
                
                # 发送测试消息
                test_message = {
                    "type": "test",
                    "message": "生产环境诊断测试",
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                self.log("📤 发送测试消息", "SUCCESS")
                
                # 等待响应
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    self.log(f"📥 收到响应: {response}", "SUCCESS")
                except asyncio.TimeoutError:
                    self.log("⏰ WebSocket响应超时（可能正常，服务器不回复测试消息）", "WARNING")
                
                return True
                
        except websockets.exceptions.InvalidStatusCode as e:
            self.log(f"❌ WebSocket状态码错误: {e}", "ERROR")
            self.results["websocket_connection"] = False
        except websockets.exceptions.ConnectionClosedError as e:
            self.log(f"❌ WebSocket连接关闭: {e}", "ERROR")
            self.results["websocket_connection"] = False
        except asyncio.TimeoutError:
            self.log("❌ WebSocket连接超时", "ERROR")
            self.results["websocket_connection"] = False
        except Exception as e:
            self.log(f"❌ WebSocket连接异常: {e}", "ERROR")
            self.results["websocket_connection"] = False
        
        return False
    
    def test_port_scan(self):
        """扫描相关端口状态"""
        self.log("🔍 扫描相关端口状态...")
        
        ports_to_test = [8000, 8001, 8002, 8003, 8080, 8888]
        open_ports = []
        
        for port in ports_to_test:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((self.production_host, port))
                sock.close()
                
                if result == 0:
                    self.log(f"✅ 端口 {port} 开放", "SUCCESS")
                    open_ports.append(port)
                else:
                    self.log(f"❌ 端口 {port} 关闭", "WARNING")
            except Exception as e:
                self.log(f"❌ 端口 {port} 测试异常: {e}", "ERROR")
        
        self.results["open_ports"] = open_ports
        return open_ports
    
    def check_xiaozhi_service_status(self):
        """检查小智主服务状态"""
        self.log("🔍 检查小智主服务状态...")
        
        # 尝试访问可能的API端点
        api_endpoints = [
            f"http://{self.production_host}:{self.production_port}/",
            f"http://{self.production_host}:{self.production_port}/status",
            f"http://{self.production_host}:{self.production_port}/health",
            f"http://{self.production_host}:{self.production_port}/api/status",
        ]
        
        for endpoint in api_endpoints:
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    self.log(f"✅ 服务端点可用: {endpoint}", "SUCCESS")
                    self.log(f"📄 响应内容: {response.text[:200]}", "INFO")
                    self.results["service_status"] = True
                    return True
                else:
                    self.log(f"⚠️ 服务端点返回: {endpoint} - {response.status_code}", "WARNING")
            except Exception as e:
                self.log(f"❌ 服务端点异常: {endpoint} - {e}", "ERROR")
        
        self.results["service_status"] = False
        return False
    
    def print_diagnostic_summary(self):
        """打印诊断总结"""
        print("\n" + "=" * 60)
        print("📊 生产环境诊断结果")
        print("=" * 60)
        
        print(f"🎯 目标服务器: {self.production_host}:{self.production_port}")
        print(f"🌐 WebSocket地址: ws://{self.production_host}:{self.production_port}/xiaozhi/v1/")
        print()
        
        # 测试结果
        tests = [
            ("🔌 TCP连接", self.results.get("tcp_connection", False)),
            ("🩺 HTTP健康检查", self.results.get("http_health", False)),
            ("🌐 WebSocket连接", self.results.get("websocket_connection", False)),
            ("🔧 小智服务状态", self.results.get("service_status", False)),
        ]
        
        passed = 0
        for test_name, status in tests:
            icon = "✅" if status else "❌"
            status_text = "通过" if status else "失败"
            print(f"{icon} {test_name:<20} : {status_text}")
            if status:
                passed += 1
        
        print("-" * 60)
        
        # 开放端口
        open_ports = self.results.get("open_ports", [])
        if open_ports:
            print(f"🔍 开放端口: {', '.join(map(str, open_ports))}")
        else:
            print("❌ 没有发现开放的端口")
        
        print()
        print(f"📈 总体结果: {passed}/{len(tests)} 项测试通过")
        
        # 问题分析和建议
        self.print_recommendations()
    
    def print_recommendations(self):
        """打印建议"""
        print("\n💡 问题分析和建议:")
        
        if not self.results.get("tcp_connection", False):
            print("🔧 TCP连接问题:")
            print("   - 检查网络连接和防火墙设置")
            print("   - 确认服务器IP地址是否正确")
            print("   - 验证端口8000是否开放")
        
        if not self.results.get("websocket_connection", False):
            print("🔧 WebSocket连接问题:")
            print("   - 小智主服务可能没有运行")
            print("   - WebSocket服务器可能没有启动")
            print("   - 检查服务器配置和日志")
            print("   - 确认/xiaozhi/v1/路径是否正确")
        
        if not self.results.get("service_status", False):
            print("🔧 小智服务问题:")
            print("   - 小智主服务可能没有正常运行")
            print("   - 检查服务器上的Python进程")
            print("   - 查看服务器日志: logs/app_unified.log")
            print("   - 确认TTS和WebSocket功能是否启用")
        
        print("\n🚀 建议的解决步骤:")
        print("1. 联系服务器管理员检查小智主服务状态")
        print("2. 确认WebSocket服务器是否在8000端口运行")
        print("3. 检查服务器防火墙和网络配置")
        print("4. 先用内网测试验证硬件WebSocket功能")
        print("5. 确认硬件能否访问公网地址")
    
    async def run_full_diagnostic(self):
        """运行完整诊断"""
        print("🚀 生产环境诊断工具启动")
        print("="*60)
        print(f"📅 诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 目标服务器: {self.production_host}:{self.production_port}")
        print()
        
        try:
            # 依次执行各项测试
            self.test_tcp_connection()
            time.sleep(1)
            
            self.test_port_scan()
            time.sleep(1)
            
            self.test_http_health()
            time.sleep(1)
            
            await self.test_websocket_connection()
            time.sleep(1)
            
            self.check_xiaozhi_service_status()
            
            # 输出诊断结果
            self.print_diagnostic_summary()
            
        except KeyboardInterrupt:
            self.log("用户中断诊断", "WARNING")
        except Exception as e:
            self.log(f"诊断异常: {e}", "ERROR")

async def main():
    """主函数"""
    diagnostic = ProductionDiagnostic()
    await diagnostic.run_full_diagnostic()

if __name__ == "__main__":
    asyncio.run(main())

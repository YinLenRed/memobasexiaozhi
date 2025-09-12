#!/usr/bin/env python3
"""
集成天气功能到主app.py - 避免MQTT客户端冲突
使用单一MQTT客户端处理所有功能
"""

import asyncio
import sys
import subprocess
import signal
import time
from datetime import datetime
from pathlib import Path

class IntegratedWeatherService:
    """集成天气服务管理器"""
    
    def __init__(self):
        self.app_process = None
        self.running = False
        
    async def start(self):
        """启动集成的天气服务（通过app.py）"""
        print("🎉 启动集成天气服务")
        print("=" * 50)
        
        try:
            print("🚀 1. 启动主服务 (app.py)...")
            print("   📡 MQTT客户端: 统一管理")  
            print("   🌤️ 天气功能: 自动集成")
            print("   🤖 主服务: 语音对话")
            print("   🌐 Web服务: HTTP/WebSocket")
            
            # 启动app.py作为子进程
            self.app_process = subprocess.Popen(
                [sys.executable, "app.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            print(f"   ✅ 主服务已启动 (PID: {self.app_process.pid})")
            
            self.running = True
            
            print("\n🎯 服务状态:")
            print("   📡 单一MQTT客户端 - 避免连接冲突") 
            print("   🌤️ 天气数据通过主服务MQTT发布")
            print("   🔧 如需天气功能，请在app.py中启用")
            
            print("\n💡 硬件对接:")
            print("   📋 MQTT订阅: xiaozhi/weather/+")
            print("   📋 设备通信: xiaozhi/device/+")
            print("   📋 完整文档: HARDWARE_MQTT_GUIDE.md")
            
            print(f"\n🔄 按Ctrl+C停止所有服务")
            
            # 监控主服务输出
            asyncio.create_task(self._monitor_app_output())
            
            # 保持运行
            try:
                while self.running and self.app_process and self.app_process.poll() is None:
                    await asyncio.sleep(1)
                    
                if self.app_process and self.app_process.poll() is not None:
                    print(f"\n❌ 主服务意外退出，退出码: {self.app_process.returncode}")
                    self.running = False
                    
            except KeyboardInterrupt:
                print(f"\n⏹️ 收到停止信号...")
                await self.stop()
                
        except Exception as e:
            print(f"❌ 服务启动失败: {e}")
            await self.stop()
    
    async def _monitor_app_output(self):
        """监控app.py输出"""
        if not self.app_process:
            return
            
        try:
            while self.running and self.app_process and self.app_process.poll() is None:
                line = self.app_process.stdout.readline()
                if line:
                    # 过滤重要日志显示
                    line = line.strip()
                    if any(keyword in line.lower() for keyword in ['error', 'fail', 'exception', 'mqtt', 'weather']):
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] {line}")
                        
                await asyncio.sleep(0.1)
        except Exception as e:
            print(f"⚠️ 日志监控异常: {e}")
    
    async def stop(self):
        """停止集成服务"""
        print("🛑 正在停止集成天气服务...")
        self.running = False
        
        if self.app_process:
            try:
                print("   🛑 停止主服务...")
                self.app_process.terminate()
                
                # 等待优雅关闭
                try:
                    self.app_process.wait(timeout=10)
                    print("   ✅ 主服务已正常停止")
                except subprocess.TimeoutExpired:
                    print("   ⚠️ 强制终止主服务...")
                    self.app_process.kill()
                    self.app_process.wait()
                    print("   ✅ 主服务已强制停止")
                    
            except Exception as e:
                print(f"   ❌ 停止服务时出错: {e}")
        
        print("✅ 集成天气服务已停止")
    
    def get_status(self):
        """获取服务状态"""
        if self.app_process and self.app_process.poll() is None:
            return {
                "status": "running",
                "pid": self.app_process.pid,
                "message": "集成服务运行正常"
            }
        else:
            return {
                "status": "stopped", 
                "pid": None,
                "message": "集成服务已停止"
            }

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="集成天气服务 - 避免MQTT冲突")
    parser.add_argument("--action", choices=["start", "status"], default="start",
                       help="操作类型")
    
    args = parser.parse_args()
    
    service = IntegratedWeatherService()
    
    # 信号处理
    def signal_handler(signum, frame):
        print(f"\n⚠️ 收到信号 {signum}")
        asyncio.create_task(service.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.action == "start":
            await service.start()
        elif args.action == "status":
            status = service.get_status()
            print(f"📊 服务状态: {status['message']}")
            if status['pid']:
                print(f"🔢 进程ID: {status['pid']}")
                
    except Exception as e:
        print(f"❌ 运行异常: {e}")
        import traceback
        print(f"错误详情: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 服务已手动停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

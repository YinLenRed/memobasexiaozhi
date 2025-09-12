#!/usr/bin/env python3
"""
一键启动所有小智服务
包括：天气MQTT服务 + 主应用服务(app.py)
"""

import os
import sys
import time
import signal
import subprocess
import threading
from datetime import datetime

class ServiceManager:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def log(self, message, level="INFO"):
        """统一日志输出"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def start_service(self, script_name, service_name):
        """启动单个服务"""
        try:
            self.log(f"🚀 启动 {service_name}...")
            
            # 启动Python脚本
            process = subprocess.Popen(
                [sys.executable, script_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes.append({
                'process': process,
                'name': service_name,
                'script': script_name
            })
            
            self.log(f"✅ {service_name} 启动成功 (PID: {process.pid})")
            
            # 启动输出监控线程
            threading.Thread(
                target=self.monitor_output,
                args=(process, service_name),
                daemon=True
            ).start()
            
            return True
            
        except Exception as e:
            self.log(f"❌ 启动 {service_name} 失败: {e}", "ERROR")
            return False
    
    def monitor_output(self, process, service_name):
        """监控服务输出"""
        try:
            while self.running and process.poll() is None:
                output = process.stdout.readline()
                if output:
                    # 过滤和格式化输出
                    line = output.strip()
                    if line and not self.is_noise_log(line):
                        self.log(f"[{service_name}] {line}")
        except:
            pass
    
    def is_noise_log(self, line):
        """过滤噪音日志"""
        noise_patterns = [
            "DEBUG",
            "keepalive",
            "heartbeat",
            "ping",
            "pong"
        ]
        return any(pattern.lower() in line.lower() for pattern in noise_patterns)
    
    def check_services_health(self):
        """检查服务健康状态"""
        self.log("🔍 检查服务状态...")
        
        healthy_count = 0
        for service in self.processes:
            if service['process'].poll() is None:
                self.log(f"✅ {service['name']} 运行正常 (PID: {service['process'].pid})")
                healthy_count += 1
            else:
                self.log(f"❌ {service['name']} 已停止", "ERROR")
        
        self.log(f"📊 健康服务: {healthy_count}/{len(self.processes)}")
        return healthy_count == len(self.processes)
    
    def stop_all_services(self):
        """停止所有服务"""
        self.log("🛑 正在停止所有服务...")
        self.running = False
        
        for service in self.processes:
            try:
                if service['process'].poll() is None:
                    self.log(f"🛑 停止 {service['name']}...")
                    service['process'].terminate()
                    
                    # 等待graceful shutdown
                    try:
                        service['process'].wait(timeout=5)
                        self.log(f"✅ {service['name']} 已正常停止")
                    except subprocess.TimeoutExpired:
                        self.log(f"⚠️  {service['name']} 强制终止...")
                        service['process'].kill()
                        service['process'].wait()
                        
            except Exception as e:
                self.log(f"❌ 停止 {service['name']} 时出错: {e}", "ERROR")
    
    def signal_handler(self, signum, frame):
        """处理系统信号"""
        self.log("📡 接收到停止信号...")
        self.stop_all_services()
        sys.exit(0)

def main():
    """主函数"""
    print("=" * 60)
    print("🎉 小智一键启动服务管理器")
    print("=" * 60)
    
    # 检查必要文件
    required_files = [
        "start_weather_mqtt_service.py",
        "app.py"
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ 缺少必要文件: {file}")
            print("请确保在正确的目录下运行此脚本")
            return False
    
    # 创建服务管理器
    manager = ServiceManager()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, manager.signal_handler)
    signal.signal(signal.SIGTERM, manager.signal_handler)
    
    try:
        # 启动服务
        services = [
            ("start_weather_mqtt_service.py", "天气MQTT服务"),
            ("app.py", "小智主服务")
        ]
        
        success_count = 0
        for script, name in services:
            if manager.start_service(script, name):
                success_count += 1
                time.sleep(2)  # 给服务启动时间
        
        if success_count == 0:
            manager.log("❌ 没有服务启动成功", "ERROR")
            return False
        
        manager.log(f"🎉 成功启动 {success_count}/{len(services)} 个服务")
        
        # 等待一下，然后检查服务状态
        time.sleep(5)
        manager.check_services_health()
        
        manager.log("🎯 所有服务已启动！")
        manager.log("💡 按 Ctrl+C 停止所有服务")
        manager.log("📊 服务状态监控中...")
        
        # 主循环 - 监控服务
        while manager.running:
            time.sleep(30)  # 每30秒检查一次
            if not manager.check_services_health():
                manager.log("⚠️  发现服务异常，建议重启", "WARN")
        
    except KeyboardInterrupt:
        manager.log("👋 用户中断...")
    except Exception as e:
        manager.log(f"❌ 运行时错误: {e}", "ERROR")
    finally:
        manager.stop_all_services()
        manager.log("🏁 所有服务已停止")

if __name__ == "__main__":
    main()

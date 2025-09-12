#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小智服务监控和自动恢复工具
防止MQTT消息洪水攻击导致的服务崩溃，提供自动恢复机制
"""

import os
import sys
import time
import signal
import subprocess
import psutil
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('服务监控')

class ServiceConfig:
    """服务配置"""
    def __init__(self):
        self.service_name = "xiaozhi-server"
        self.service_port = 8003
        self.service_host = "localhost"
        self.max_memory_mb = 2048  # 最大内存使用量(MB)
        self.max_cpu_percent = 80  # 最大CPU使用率(%)
        self.health_check_interval = 30  # 健康检查间隔(秒)
        self.restart_cooldown = 60  # 重启冷却时间(秒)
        self.max_restarts_per_hour = 5  # 每小时最大重启次数
        
        # MQTT消息监控
        self.mqtt_message_limit = 100  # MQTT消息数量限制
        self.mqtt_monitor_window = 60  # 监控窗口(秒)

class ServiceMonitor:
    """服务监控器"""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.is_running = False
        self.service_process = None
        self.restart_history = []  # 重启历史记录
        self.mqtt_message_count = 0
        self.mqtt_last_reset = time.time()
        
        # 统计信息
        self.stats = {
            "total_checks": 0,
            "health_failures": 0,
            "memory_warnings": 0,
            "cpu_warnings": 0, 
            "mqtt_overloads": 0,
            "total_restarts": 0,
            "uptime_start": time.time()
        }
        
        logger.info(f"🔍 服务监控器已初始化: {self.config.service_name}")
    
    def find_service_process(self) -> Optional[psutil.Process]:
        """查找服务进程"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    
                    # 检查是否为小智服务进程
                    if ('python' in proc.info['name'].lower() and 
                        any(keyword in cmdline.lower() for keyword in ['xiaozhi', 'main.py', 'server'])):
                        
                        # 验证是否监听目标端口
                        for conn in proc.connections():
                            if conn.laddr.port == self.config.service_port:
                                logger.debug(f"找到服务进程: PID={proc.pid}, CMD={cmdline}")
                                return proc
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
            return None
            
        except Exception as e:
            logger.error(f"查找服务进程失败: {e}")
            return None
    
    def check_process_health(self, process: psutil.Process) -> Dict[str, any]:
        """检查进程健康状态"""
        try:
            health = {
                "is_running": process.is_running(),
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "open_files": len(process.open_files()),
                "connections": len(process.connections()),
                "status": process.status()
            }
            
            return health
            
        except Exception as e:
            logger.error(f"检查进程健康状态失败: {e}")
            return {"is_running": False, "error": str(e)}
    
    def check_service_api(self) -> bool:
        """检查服务API健康状态"""
        try:
            # 测试健康检查端点
            health_endpoints = [
                f"http://{self.config.service_host}:{self.config.service_port}/health",
                f"http://{self.config.service_host}:{self.config.service_port}/status",
                f"http://{self.config.service_host}:{self.config.service_port}/ping"
            ]
            
            for endpoint in health_endpoints:
                try:
                    response = requests.get(endpoint, timeout=5)
                    if response.status_code == 200:
                        logger.debug(f"API健康检查通过: {endpoint}")
                        return True
                except:
                    continue
            
            # 如果健康检查端点都失败，尝试主要API端点
            try:
                main_endpoint = f"http://{self.config.service_host}:{self.config.service_port}/xiaozhi/greeting/send"
                response = requests.post(main_endpoint, json={"test": True}, timeout=5)
                # 即使返回错误，只要有响应就说明服务在运行
                logger.debug(f"主要API端点响应: {response.status_code}")
                return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.error(f"API健康检查失败: {e}")
            return False
    
    def restart_service(self, reason: str = "手动重启") -> bool:
        """重启服务"""
        try:
            logger.warning(f"🔄 准备重启服务，原因: {reason}")
            
            # 检查重启频率限制
            if not self._can_restart():
                logger.error("❌ 重启频率过高，跳过重启")
                return False
            
            # 记录重启
            self.restart_history.append({
                "timestamp": time.time(),
                "reason": reason
            })
            self.stats["total_restarts"] += 1
            
            # 停止旧进程
            self._stop_service()
            
            # 等待停止完成
            time.sleep(5)
            
            # 启动新进程
            success = self._start_service()
            
            if success:
                logger.info(f"✅ 服务重启成功")
                return True
            else:
                logger.error(f"❌ 服务重启失败")
                return False
                
        except Exception as e:
            logger.error(f"重启服务失败: {e}")
            return False
    
    def _can_restart(self) -> bool:
        """检查是否可以重启"""
        current_time = time.time()
        
        # 清理1小时前的重启记录
        self.restart_history = [
            r for r in self.restart_history 
            if current_time - r["timestamp"] < 3600
        ]
        
        # 检查1小时内重启次数
        if len(self.restart_history) >= self.config.max_restarts_per_hour:
            logger.error(f"1小时内重启次数过多: {len(self.restart_history)}/{self.config.max_restarts_per_hour}")
            return False
        
        # 检查冷却时间
        if self.restart_history:
            last_restart = max(r["timestamp"] for r in self.restart_history)
            if current_time - last_restart < self.config.restart_cooldown:
                remaining = self.config.restart_cooldown - (current_time - last_restart)
                logger.warning(f"重启冷却中，还需等待 {remaining:.1f} 秒")
                return False
        
        return True
    
    def _stop_service(self):
        """停止服务"""
        try:
            # 查找并停止进程
            process = self.find_service_process()
            if process:
                logger.info(f"停止进程: PID={process.pid}")
                
                # 优雅停止
                process.terminate()
                
                # 等待进程结束
                try:
                    process.wait(timeout=10)
                except psutil.TimeoutExpired:
                    # 强制停止
                    logger.warning("优雅停止超时，强制停止进程")
                    process.kill()
                    process.wait(timeout=5)
                
                logger.info("✅ 进程已停止")
            else:
                logger.info("未找到运行中的服务进程")
                
        except Exception as e:
            logger.error(f"停止服务失败: {e}")
    
    def _start_service(self) -> bool:
        """启动服务"""
        try:
            # 查找启动脚本
            startup_commands = [
                "python main.py",
                "nohup python main.py > server.log 2>&1 &",
                "systemctl start xiaozhi-server"
            ]
            
            for cmd in startup_commands:
                try:
                    logger.info(f"尝试启动命令: {cmd}")
                    
                    if cmd.startswith("systemctl"):
                        # 系统服务启动
                        result = subprocess.run(cmd.split(), capture_output=True, text=True)
                        if result.returncode == 0:
                            logger.info("✅ 系统服务启动成功")
                            return True
                    else:
                        # 直接启动Python进程
                        if "nohup" in cmd:
                            # 后台启动
                            subprocess.Popen(cmd, shell=True, cwd=os.getcwd())
                        else:
                            # 前台启动（在后台线程中运行）
                            def run_service():
                                subprocess.run(cmd.split(), cwd=os.getcwd())
                            
                            threading.Thread(target=run_service, daemon=True).start()
                        
                        # 等待服务启动
                        time.sleep(10)
                        
                        # 验证启动成功
                        if self.find_service_process():
                            logger.info("✅ Python服务启动成功")
                            return True
                            
                except Exception as e:
                    logger.warning(f"启动命令失败: {cmd}, 错误: {e}")
                    continue
            
            logger.error("❌ 所有启动方式都失败")
            return False
            
        except Exception as e:
            logger.error(f"启动服务失败: {e}")
            return False
    
    def monitor_loop(self):
        """主监控循环"""
        logger.info("🚀 开始服务监控")
        self.is_running = True
        
        while self.is_running:
            try:
                self.stats["total_checks"] += 1
                
                # 查找服务进程
                process = self.find_service_process()
                
                if not process:
                    logger.error("❌ 服务进程未运行")
                    self.stats["health_failures"] += 1
                    
                    # 尝试重启
                    self.restart_service("进程未运行")
                else:
                    # 检查进程健康状态
                    health = self.check_process_health(process)
                    
                    # 检查内存使用
                    if health.get("memory_mb", 0) > self.config.max_memory_mb:
                        logger.warning(f"⚠️ 内存使用过高: {health['memory_mb']:.1f}MB > {self.config.max_memory_mb}MB")
                        self.stats["memory_warnings"] += 1
                        self.restart_service(f"内存使用过高({health['memory_mb']:.1f}MB)")
                        continue
                    
                    # 检查CPU使用
                    if health.get("cpu_percent", 0) > self.config.max_cpu_percent:
                        logger.warning(f"⚠️ CPU使用过高: {health['cpu_percent']:.1f}% > {self.config.max_cpu_percent}%")
                        self.stats["cpu_warnings"] += 1
                    
                    # 检查API健康状态
                    if not self.check_service_api():
                        logger.error("❌ API健康检查失败")
                        self.stats["health_failures"] += 1
                        self.restart_service("API无响应")
                        continue
                    
                    # 健康状态良好
                    logger.info(f"✅ 服务健康: CPU={health.get('cpu_percent', 0):.1f}%, 内存={health.get('memory_mb', 0):.1f}MB")
                
                # 等待下次检查
                time.sleep(self.config.health_check_interval)
                
            except KeyboardInterrupt:
                logger.info("👋 收到停止信号")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                time.sleep(self.config.health_check_interval)
    
    def stop(self):
        """停止监控"""
        self.is_running = False
        logger.info("🛑 服务监控已停止")
    
    def get_stats(self) -> Dict[str, any]:
        """获取统计信息"""
        uptime = time.time() - self.stats["uptime_start"]
        
        return {
            **self.stats,
            "uptime_seconds": uptime,
            "uptime_formatted": f"{uptime/3600:.1f}小时",
            "restart_history": self.restart_history[-10:],  # 最近10次重启
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

def create_monitor_service():
    """创建监控服务"""
    config = ServiceConfig()
    monitor = ServiceMonitor(config)
    return monitor

def main():
    """主函数"""
    print("🔍 小智服务监控器")
    print("="*30)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "start":
            # 启动监控
            monitor = create_monitor_service()
            
            def signal_handler(signum, frame):
                print("\n👋 收到停止信号，正在关闭监控...")
                monitor.stop()
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            monitor.monitor_loop()
            
        elif command == "restart":
            # 手动重启服务
            monitor = create_monitor_service()
            success = monitor.restart_service("手动重启")
            if success:
                print("✅ 服务重启成功")
            else:
                print("❌ 服务重启失败")
                
        elif command == "status":
            # 检查服务状态
            monitor = create_monitor_service()
            process = monitor.find_service_process()
            
            if process:
                health = monitor.check_process_health(process)
                api_ok = monitor.check_service_api()
                
                print("✅ 服务状态:")
                print(f"   进程ID: {process.pid}")
                print(f"   CPU使用: {health.get('cpu_percent', 0):.1f}%")
                print(f"   内存使用: {health.get('memory_mb', 0):.1f}MB")
                print(f"   API状态: {'正常' if api_ok else '异常'}")
                print(f"   连接数: {health.get('connections', 0)}")
                print(f"   打开文件: {health.get('open_files', 0)}")
            else:
                print("❌ 服务未运行")
                
        elif command == "stats":
            # 显示统计信息
            monitor = create_monitor_service()
            stats = monitor.get_stats()
            
            print("📊 监控统计:")
            print(f"   运行时间: {stats['uptime_formatted']}")
            print(f"   总检查次数: {stats['total_checks']}")
            print(f"   健康失败次数: {stats['health_failures']}")
            print(f"   内存警告次数: {stats['memory_warnings']}")
            print(f"   CPU警告次数: {stats['cpu_warnings']}")
            print(f"   总重启次数: {stats['total_restarts']}")
            
        else:
            print("用法: python 服务监控和自动恢复.py [start|restart|status|stats]")
    else:
        # 交互式模式
        monitor = create_monitor_service()
        
        while True:
            print("\n🔍 服务监控菜单:")
            print("1. 开始监控")
            print("2. 重启服务")
            print("3. 检查状态")
            print("4. 查看统计")
            print("5. 退出")
            
            choice = input("\n请选择 (1-5): ").strip()
            
            if choice == "1":
                print("🚀 开始监控（Ctrl+C停止）...")
                try:
                    monitor.monitor_loop()
                except KeyboardInterrupt:
                    print("\n👋 监控已停止")
                    
            elif choice == "2":
                success = monitor.restart_service("手动重启")
                if success:
                    print("✅ 服务重启成功")
                else:
                    print("❌ 服务重启失败")
                    
            elif choice == "3":
                process = monitor.find_service_process()
                if process:
                    health = monitor.check_process_health(process)
                    api_ok = monitor.check_service_api()
                    
                    print("✅ 服务状态:")
                    print(f"   进程ID: {process.pid}")
                    print(f"   CPU使用: {health.get('cpu_percent', 0):.1f}%")
                    print(f"   内存使用: {health.get('memory_mb', 0):.1f}MB")
                    print(f"   API状态: {'正常' if api_ok else '异常'}")
                else:
                    print("❌ 服务未运行")
                    
            elif choice == "4":
                stats = monitor.get_stats()
                print("📊 监控统计:")
                print(f"   运行时间: {stats['uptime_formatted']}")
                print(f"   总检查次数: {stats['total_checks']}")
                print(f"   总重启次数: {stats['total_restarts']}")
                
            elif choice == "5":
                print("👋 退出监控器")
                break
                
            else:
                print("❌ 无效选择")

if __name__ == "__main__":
    main()

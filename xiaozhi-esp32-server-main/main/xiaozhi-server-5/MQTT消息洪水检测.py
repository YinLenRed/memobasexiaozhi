#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT消息洪水攻击检测和防护工具
实时监控MQTT消息流量，自动识别和处理洪水攻击
"""

import time
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import threading
import signal
import os
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('MQTT洪水检测')

class FloodDetectionConfig:
    """洪水检测配置"""
    def __init__(self):
        # 基础阈值设置
        self.normal_rate_per_second = 2      # 正常速率：每秒2条消息
        self.warning_rate_per_second = 10    # 警告速率：每秒10条消息  
        self.critical_rate_per_second = 20   # 危险速率：每秒20条消息
        self.flood_rate_per_second = 50      # 洪水攻击：每秒50条消息
        
        # 时间窗口设置
        self.detection_window_seconds = 10   # 检测窗口：10秒
        self.analysis_window_minutes = 5     # 分析窗口：5分钟
        
        # 防护动作设置
        self.enable_auto_protection = True   # 是否启用自动防护
        self.protection_duration_seconds = 300  # 防护持续时间：5分钟
        
        # 告警设置
        self.enable_alerts = True            # 是否启用告警
        self.alert_cooldown_minutes = 10     # 告警冷却时间：10分钟

class MessageStats:
    """消息统计"""
    def __init__(self):
        self.total_messages = 0
        self.messages_per_device = defaultdict(int)
        self.messages_per_topic = defaultdict(int)
        self.message_timestamps = deque()  # 用于计算速率
        self.flood_events = []  # 洪水事件记录
        self.start_time = time.time()
    
    def add_message(self, device_id: str, topic: str, message_size: int = 0):
        """添加消息统计"""
        current_time = time.time()
        
        self.total_messages += 1
        self.messages_per_device[device_id] += 1
        self.messages_per_topic[topic] += 1
        self.message_timestamps.append(current_time)
        
        # 保持时间戳队列在合理大小
        while (self.message_timestamps and 
               current_time - self.message_timestamps[0] > 3600):  # 保留1小时数据
            self.message_timestamps.popleft()
    
    def get_current_rate(self, window_seconds: int = 10) -> float:
        """获取当前消息速率（条/秒）"""
        if not self.message_timestamps:
            return 0.0
        
        current_time = time.time()
        recent_messages = sum(1 for ts in self.message_timestamps 
                             if current_time - ts <= window_seconds)
        
        return recent_messages / window_seconds
    
    def get_device_rate(self, device_id: str, window_seconds: int = 10) -> float:
        """获取特定设备的消息速率"""
        # 这里简化实现，实际应该为每个设备维护独立的时间戳队列
        total_rate = self.get_current_rate(window_seconds)
        device_proportion = self.messages_per_device[device_id] / max(self.total_messages, 1)
        return total_rate * device_proportion

class FloodDetector:
    """洪水攻击检测器"""
    
    def __init__(self, config: FloodDetectionConfig):
        self.config = config
        self.stats = MessageStats()
        self.is_monitoring = False
        self.protection_active = False
        self.protection_end_time = 0
        self.last_alert_time = 0
        
        # 检测状态
        self.current_level = "NORMAL"  # NORMAL, WARNING, CRITICAL, FLOOD
        self.consecutive_high_rate_count = 0
        
        logger.info(f"🛡️ MQTT洪水检测器已初始化")
        logger.info(f"   正常速率: {config.normal_rate_per_second} 条/秒")
        logger.info(f"   警告速率: {config.warning_rate_per_second} 条/秒") 
        logger.info(f"   危险速率: {config.critical_rate_per_second} 条/秒")
        logger.info(f"   洪水速率: {config.flood_rate_per_second} 条/秒")
    
    def process_message(self, topic: str, payload: str, device_id: str = None) -> bool:
        """
        处理接收到的MQTT消息
        
        Returns:
            bool: 是否允许处理该消息（False表示被防护机制阻断）
        """
        # 提取设备ID（如果未提供）
        if not device_id:
            device_id = self._extract_device_id(topic)
        
        # 添加到统计
        self.stats.add_message(device_id or "unknown", topic, len(payload))
        
        # 检查是否在防护模式
        if self.protection_active:
            if time.time() < self.protection_end_time:
                logger.debug(f"🚫 消息被防护模式阻断: {topic}")
                return False
            else:
                # 防护时间结束
                self._deactivate_protection()
        
        # 实时检测
        self._detect_flood()
        
        return True
    
    def _extract_device_id(self, topic: str) -> Optional[str]:
        """从topic提取设备ID"""
        try:
            if "device/" in topic:
                parts = topic.split("/")
                if len(parts) >= 2 and parts[0] == "device":
                    return parts[1]
            return None
        except:
            return None
    
    def _detect_flood(self):
        """检测洪水攻击"""
        current_rate = self.stats.get_current_rate(self.config.detection_window_seconds)
        new_level = self._classify_rate(current_rate)
        
        # 检测级别变化
        if new_level != self.current_level:
            self._handle_level_change(self.current_level, new_level, current_rate)
            self.current_level = new_level
        
        # 连续高速率检测
        if new_level in ["CRITICAL", "FLOOD"]:
            self.consecutive_high_rate_count += 1
            
            # 如果连续检测到高速率，激活防护
            if (self.consecutive_high_rate_count >= 3 and 
                self.config.enable_auto_protection and 
                not self.protection_active):
                self._activate_protection(f"连续{self.consecutive_high_rate_count}次检测到{new_level}级别")
        else:
            self.consecutive_high_rate_count = 0
    
    def _classify_rate(self, rate: float) -> str:
        """分类消息速率等级"""
        if rate >= self.config.flood_rate_per_second:
            return "FLOOD"
        elif rate >= self.config.critical_rate_per_second:
            return "CRITICAL"
        elif rate >= self.config.warning_rate_per_second:
            return "WARNING"
        else:
            return "NORMAL"
    
    def _handle_level_change(self, old_level: str, new_level: str, rate: float):
        """处理检测级别变化"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if new_level == "FLOOD":
            logger.error(f"🚨 [{timestamp}] 检测到MQTT消息洪水攻击! 速率: {rate:.1f} 条/秒")
            self._send_alert("MQTT洪水攻击", f"消息速率达到 {rate:.1f} 条/秒，超出洪水阈值")
            
        elif new_level == "CRITICAL":
            logger.error(f"⚠️ [{timestamp}] MQTT消息速率危险! 速率: {rate:.1f} 条/秒")
            self._send_alert("MQTT消息速率危险", f"消息速率达到 {rate:.1f} 条/秒")
            
        elif new_level == "WARNING":
            logger.warning(f"🔶 [{timestamp}] MQTT消息速率警告! 速率: {rate:.1f} 条/秒")
            
        elif new_level == "NORMAL" and old_level != "NORMAL":
            logger.info(f"✅ [{timestamp}] MQTT消息速率恢复正常: {rate:.1f} 条/秒")
    
    def _activate_protection(self, reason: str):
        """激活防护模式"""
        self.protection_active = True
        self.protection_end_time = time.time() + self.config.protection_duration_seconds
        
        logger.error(f"🛡️ 激活MQTT洪水防护模式")
        logger.error(f"   原因: {reason}")
        logger.error(f"   持续时间: {self.config.protection_duration_seconds} 秒")
        logger.error(f"   结束时间: {datetime.fromtimestamp(self.protection_end_time).strftime('%H:%M:%S')}")
        
        # 记录洪水事件
        self.stats.flood_events.append({
            "start_time": time.time(),
            "reason": reason,
            "rate": self.stats.get_current_rate(),
            "protection_duration": self.config.protection_duration_seconds
        })
        
        self._send_alert("MQTT洪水防护激活", f"原因: {reason}, 持续{self.config.protection_duration_seconds}秒")
    
    def _deactivate_protection(self):
        """停用防护模式"""
        if self.protection_active:
            self.protection_active = False
            self.consecutive_high_rate_count = 0
            logger.info(f"🔓 MQTT洪水防护模式已停用，恢复正常处理")
    
    def _send_alert(self, title: str, message: str):
        """发送告警"""
        if not self.config.enable_alerts:
            return
        
        current_time = time.time()
        
        # 告警冷却
        if (current_time - self.last_alert_time) < (self.config.alert_cooldown_minutes * 60):
            logger.debug("告警在冷却期，跳过发送")
            return
        
        self.last_alert_time = current_time
        
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "message": message,
            "current_rate": self.stats.get_current_rate(),
            "total_messages": self.stats.total_messages,
            "protection_active": self.protection_active
        }
        
        logger.error(f"📧 发送告警: {title} - {message}")
        
        # 这里可以集成真实的告警系统（邮件、微信、钉钉等）
        self._save_alert_to_file(alert_data)
    
    def _save_alert_to_file(self, alert_data: Dict):
        """保存告警到文件"""
        try:
            alert_file = "mqtt_flood_alerts.log"
            with open(alert_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert_data, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"保存告警失败: {e}")
    
    def get_status_report(self) -> Dict[str, Any]:
        """获取状态报告"""
        current_time = time.time()
        uptime = current_time - self.stats.start_time
        current_rate = self.stats.get_current_rate()
        
        # Top设备统计
        top_devices = sorted(
            self.stats.messages_per_device.items(),
            key=lambda x: x[1], reverse=True
        )[:5]
        
        # Top主题统计
        top_topics = sorted(
            self.stats.messages_per_topic.items(),
            key=lambda x: x[1], reverse=True
        )[:5]
        
        return {
            "运行状态": {
                "运行时间": f"{uptime/3600:.1f}小时",
                "当前级别": self.current_level,
                "防护状态": "激活" if self.protection_active else "正常",
                "防护剩余": f"{max(0, self.protection_end_time - current_time):.0f}秒" if self.protection_active else "N/A"
            },
            "消息统计": {
                "总消息数": self.stats.total_messages,
                "当前速率": f"{current_rate:.1f} 条/秒",
                "平均速率": f"{self.stats.total_messages / uptime:.1f} 条/秒" if uptime > 0 else "0 条/秒",
                "洪水事件数": len(self.stats.flood_events)
            },
            "Top设备": [{"设备": d, "消息数": c} for d, c in top_devices],
            "Top主题": [{"主题": t, "消息数": c} for t, c in top_topics],
            "检测配置": {
                "正常阈值": f"{self.config.normal_rate_per_second} 条/秒",
                "警告阈值": f"{self.config.warning_rate_per_second} 条/秒",
                "危险阈值": f"{self.config.critical_rate_per_second} 条/秒",
                "洪水阈值": f"{self.config.flood_rate_per_second} 条/秒"
            }
        }

class MQTTFloodMonitor:
    """MQTT洪水攻击监控服务"""
    
    def __init__(self):
        self.config = FloodDetectionConfig()
        self.detector = FloodDetector(self.config)
        self.is_running = False
        self._monitor_thread = None
    
    def start_monitoring(self):
        """开始监控"""
        if self.is_running:
            logger.warning("监控已在运行中")
            return
        
        self.is_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("🚀 MQTT洪水攻击监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        logger.info("🛑 MQTT洪水攻击监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                # 定期输出状态报告
                report = self.detector.get_status_report()
                
                status_msg = (f"📊 MQTT状态: {report['运行状态']['当前级别']} | "
                            f"速率: {report['消息统计']['当前速率']} | "
                            f"总消息: {report['消息统计']['总消息数']}")
                
                if report['运行状态']['防护状态'] == "激活":
                    status_msg += f" | 🛡️防护中({report['运行状态']['防护剩余']})"
                
                logger.info(status_msg)
                
                time.sleep(30)  # 每30秒输出一次状态
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                time.sleep(10)
    
    def simulate_flood_attack(self, duration_seconds: int = 60, rate: int = 100):
        """模拟洪水攻击（测试用）"""
        logger.warning(f"🧪 开始模拟洪水攻击: {rate} 条/秒，持续 {duration_seconds} 秒")
        
        start_time = time.time()
        message_count = 0
        
        while time.time() - start_time < duration_seconds:
            # 模拟高频消息
            for _ in range(rate):
                topic = f"device/test_device_001/event"
                payload = f'{{"test_message": {message_count}, "timestamp": {time.time()}}}'
                
                allowed = self.detector.process_message(topic, payload, "test_device_001")
                message_count += 1
                
                if not allowed:
                    logger.debug(f"模拟消息被阻断: {message_count}")
            
            time.sleep(1)  # 等待1秒
        
        logger.warning(f"🧪 洪水攻击模拟结束，共发送 {message_count} 条消息")
        
        # 输出最终报告
        report = self.detector.get_status_report()
        logger.info("🔍 最终状态报告:")
        for category, data in report.items():
            if isinstance(data, dict):
                logger.info(f"  {category}:")
                for key, value in data.items():
                    logger.info(f"    {key}: {value}")

def main():
    """主函数"""
    print("🛡️ MQTT洪水攻击检测器")
    print("="*30)
    
    monitor = MQTTFloodMonitor()
    
    def signal_handler(signum, frame):
        print("\n👋 收到停止信号...")
        monitor.stop_monitoring()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "monitor":
            # 开始监控
            monitor.start_monitoring()
            print("🚀 监控已启动，按Ctrl+C停止...")
            
            try:
                while monitor.is_running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
                
        elif command == "simulate":
            # 模拟洪水攻击
            monitor.start_monitoring()
            
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            rate = int(sys.argv[3]) if len(sys.argv) > 3 else 100
            
            monitor.simulate_flood_attack(duration, rate)
            
            time.sleep(5)  # 等待处理完成
            monitor.stop_monitoring()
            
        elif command == "status":
            # 显示当前状态
            report = monitor.detector.get_status_report()
            print("📊 当前状态:")
            print(json.dumps(report, ensure_ascii=False, indent=2))
            
        else:
            print("用法: python MQTT消息洪水检测.py [monitor|simulate [持续秒数] [消息速率]|status]")
    else:
        # 交互式模式
        while True:
            print("\n🛡️ MQTT洪水检测菜单:")
            print("1. 开始监控")
            print("2. 模拟攻击")
            print("3. 查看状态")
            print("4. 退出")
            
            choice = input("\n请选择 (1-4): ").strip()
            
            if choice == "1":
                monitor.start_monitoring()
                print("🚀 监控已启动，按Ctrl+C停止...")
                try:
                    while monitor.is_running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    monitor.stop_monitoring()
                    
            elif choice == "2":
                duration = input("持续时间(秒，默认60): ").strip()
                rate = input("消息速率(条/秒，默认100): ").strip()
                
                duration = int(duration) if duration else 60
                rate = int(rate) if rate else 100
                
                monitor.start_monitoring()
                monitor.simulate_flood_attack(duration, rate)
                monitor.stop_monitoring()
                
            elif choice == "3":
                report = monitor.detector.get_status_report()
                print("📊 当前状态:")
                print(json.dumps(report, ensure_ascii=False, indent=2))
                
            elif choice == "4":
                print("👋 退出检测器")
                break
                
            else:
                print("❌ 无效选择")

if __name__ == "__main__":
    main()

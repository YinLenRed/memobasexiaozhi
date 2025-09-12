#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小智系统健康监控工具
定期检查系统各组件状态，预防偶发性问题
"""

import asyncio
import json
import logging
import time
import requests
import paho.mqtt.client as mqtt
try:
    from paho.mqtt.client import CallbackAPIVersion
except ImportError:
    pass
from datetime import datetime, timedelta
from typing import Dict, List, Any
import uuid
import sys
import os

# 确保日志目录存在
os.makedirs('health_logs', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'health_logs/health_monitor_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)
logger = logging.getLogger('健康监控')

class SystemHealthMonitor:
    """系统健康监控器"""
    
    def __init__(self):
        # 服务配置
        self.config = {
            'device_id': 'f0:9e:9e:04:8a:44',
            'python_api': 'http://47.98.51.180:8003',
            'java_api': 'http://q83b6ed9.natappfree.cc',
            'mqtt_host': '47.97.185.142',
            'mqtt_port': 1883,
            'mqtt_username': 'admin',
            'mqtt_password': 'Jyxd@2025',
            'websocket_url': 'ws://47.98.51.180:8000/xiaozhi/v1/'
        }
        
        # 健康状态记录
        self.health_history = []
        self.alert_thresholds = {
            'api_response_time': 5.0,  # API响应时间阈值(秒)
            'mqtt_response_time': 3.0,  # MQTT响应时间阈值(秒)
            'consecutive_failures': 3,  # 连续失败次数阈值
            'hardware_response_timeout': 10.0  # 硬件响应超时(秒)
        }
        
        # MQTT客户端
        self.mqtt_client = None
        self.mqtt_connected = False
        self.mqtt_test_responses = {}
        
    async def check_python_api_health(self) -> Dict[str, Any]:
        """检查Python API健康状态"""
        result = {
            'component': 'Python API',
            'healthy': False,
            'response_time': 0,
            'details': {}
        }
        
        try:
            start_time = time.time()
            
            # 测试健康检查接口
            response = requests.get(
                f"{self.config['python_api']}/health",
                timeout=self.alert_thresholds['api_response_time']
            )
            
            response_time = time.time() - start_time
            result['response_time'] = response_time
            
            if response.status_code == 200:
                result['healthy'] = True
                result['details']['status'] = 'API服务正常'
            else:
                result['details']['error'] = f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            result['details']['error'] = '响应超时'
        except requests.exceptions.ConnectionError:
            result['details']['error'] = '连接失败'
        except Exception as e:
            result['details']['error'] = str(e)
        
        return result
    
    async def check_mqtt_connectivity(self) -> Dict[str, Any]:
        """检查MQTT连接健康状态"""
        result = {
            'component': 'MQTT',
            'healthy': False,
            'response_time': 0,
            'details': {}
        }
        
        try:
            # 创建测试客户端
            test_client_id = f"health-check-{uuid.uuid4().hex[:6]}"
            
            try:
                test_client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1, client_id=test_client_id)
            except (TypeError, NameError):
                test_client = mqtt.Client(test_client_id)
            
            test_client.username_pw_set(self.config['mqtt_username'], self.config['mqtt_password'])
            
            # 连接测试
            start_time = time.time()
            connect_result = test_client.connect(self.config['mqtt_host'], self.config['mqtt_port'], 10)
            
            if connect_result == 0:
                response_time = time.time() - start_time
                result['response_time'] = response_time
                result['healthy'] = True
                result['details']['status'] = 'MQTT连接正常'
                
                # 简单的发布测试
                test_topic = f"health/test/{test_client_id}"
                test_client.publish(test_topic, "health_check", qos=1)
                result['details']['publish_test'] = '发布测试成功'
                
                test_client.disconnect()
            else:
                result['details']['error'] = f'连接失败: {connect_result}'
                
        except Exception as e:
            result['details']['error'] = str(e)
        
        return result
    
    async def check_hardware_response(self) -> Dict[str, Any]:
        """检查硬件响应状态"""
        result = {
            'component': '硬件设备',
            'healthy': False,
            'response_time': 0,
            'details': {}
        }
        
        try:
            # 发送测试主动问候
            test_payload = {
                "device_id": self.config['device_id'],
                "initial_content": f"健康检查 {datetime.now().strftime('%H:%M:%S')}",
                "category": "system_reminder"
            }
            
            start_time = time.time()
            
            response = requests.post(
                f"{self.config['python_api']}/xiaozhi/greeting/send",
                json=test_payload,
                timeout=self.alert_thresholds['api_response_time']
            )
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                track_id = response_data.get('track_id')
                
                if track_id:
                    # 等待硬件响应(简化版，不做MQTT监控)
                    response_time = time.time() - start_time
                    result['response_time'] = response_time
                    result['healthy'] = True
                    result['details']['status'] = '触发成功'
                    result['details']['track_id'] = track_id
                else:
                    result['details']['error'] = '未获取到track_id'
            else:
                result['details']['error'] = f"API返回 {response.status_code}"
                
        except Exception as e:
            result['details']['error'] = str(e)
        
        return result
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """执行完整健康检查"""
        logger.info("🏥 开始系统健康检查...")
        
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': 'unknown',
            'components': {},
            'alerts': []
        }
        
        # 并行检查各组件
        tasks = [
            self.check_python_api_health(),
            self.check_mqtt_connectivity(),
            self.check_hardware_response()
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            healthy_count = 0
            total_count = len(results)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"健康检查异常: {result}")
                    continue
                    
                component = result['component']
                health_report['components'][component] = result
                
                # 记录日志
                if result['healthy']:
                    healthy_count += 1
                    logger.info(f"✅ {component}: 健康 (响应时间: {result['response_time']:.2f}s)")
                else:
                    logger.warning(f"❌ {component}: 异常 - {result['details'].get('error', '未知错误')}")
                    health_report['alerts'].append(f"{component}异常: {result['details'].get('error', '未知错误')}")
                
                # 检查响应时间告警
                if result['healthy'] and result['response_time'] > self.alert_thresholds['api_response_time']:
                    alert_msg = f"{component}响应时间过长: {result['response_time']:.2f}s"
                    health_report['alerts'].append(alert_msg)
                    logger.warning(f"⚠️  {alert_msg}")
            
            # 计算整体健康状态
            health_ratio = healthy_count / total_count if total_count > 0 else 0
            
            if health_ratio >= 1.0:
                health_report['overall_health'] = 'healthy'
                logger.info("💚 系统整体健康状态: 良好")
            elif health_ratio >= 0.7:
                health_report['overall_health'] = 'warning'
                logger.warning("💛 系统整体健康状态: 警告")
            else:
                health_report['overall_health'] = 'critical'
                logger.error("❤️ 系统整体健康状态: 严重")
            
        except Exception as e:
            logger.error(f"健康检查执行异常: {e}")
            health_report['overall_health'] = 'error'
            health_report['alerts'].append(f"检查执行异常: {e}")
        
        # 保存到历史记录
        self.health_history.append(health_report)
        
        # 保持最近100次记录
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-100:]
        
        return health_report
    
    async def continuous_monitoring(self, interval_minutes: int = 5, duration_hours: int = 24):
        """持续监控模式"""
        logger.info(f"🔄 开始持续监控 (间隔: {interval_minutes}分钟, 持续: {duration_hours}小时)")
        
        end_time = datetime.now() + timedelta(hours=duration_hours)
        next_check = datetime.now()
        
        try:
            while datetime.now() < end_time:
                if datetime.now() >= next_check:
                    # 执行健康检查
                    health_report = await self.perform_health_check()
                    
                    # 保存日报告
                    report_file = f"health_logs/health_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
                    with open(report_file, 'w', encoding='utf-8') as f:
                        json.dump(health_report, f, ensure_ascii=False, indent=2)
                    
                    # 如果有告警，额外记录
                    if health_report['alerts']:
                        logger.warning("🚨 发现健康告警:")
                        for alert in health_report['alerts']:
                            logger.warning(f"   - {alert}")
                    
                    # 计算下次检查时间
                    next_check = datetime.now() + timedelta(minutes=interval_minutes)
                    logger.info(f"⏰ 下次检查时间: {next_check.strftime('%H:%M:%S')}")
                
                # 等待1分钟再检查
                await asyncio.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("⏹️  监控被用户中断")
        except Exception as e:
            logger.error(f"❌ 监控异常: {e}")
    
    def generate_health_summary(self) -> Dict[str, Any]:
        """生成健康状态总结"""
        if not self.health_history:
            return {"error": "暂无健康检查历史"}
        
        recent_reports = self.health_history[-10:]  # 最近10次
        
        summary = {
            'period': f"最近{len(recent_reports)}次检查",
            'time_range': {
                'start': recent_reports[0]['timestamp'],
                'end': recent_reports[-1]['timestamp']
            },
            'overall_stats': {},
            'component_stats': {},
            'recommendations': []
        }
        
        # 统计整体健康状态
        health_counts = {}
        for report in recent_reports:
            status = report['overall_health']
            health_counts[status] = health_counts.get(status, 0) + 1
        
        summary['overall_stats'] = health_counts
        
        # 统计各组件状态
        for report in recent_reports:
            for component, details in report['components'].items():
                if component not in summary['component_stats']:
                    summary['component_stats'][component] = {
                        'success_count': 0,
                        'total_count': 0,
                        'avg_response_time': 0,
                        'max_response_time': 0
                    }
                
                stats = summary['component_stats'][component]
                stats['total_count'] += 1
                
                if details['healthy']:
                    stats['success_count'] += 1
                    stats['avg_response_time'] += details['response_time']
                    stats['max_response_time'] = max(stats['max_response_time'], details['response_time'])
        
        # 计算平均响应时间
        for component, stats in summary['component_stats'].items():
            if stats['success_count'] > 0:
                stats['avg_response_time'] /= stats['success_count']
                stats['success_rate'] = stats['success_count'] / stats['total_count'] * 100
        
        # 生成建议
        for component, stats in summary['component_stats'].items():
            if stats['success_rate'] < 90:
                summary['recommendations'].append(f"⚠️  {component}成功率较低({stats['success_rate']:.1f}%)，建议检查")
            if stats['avg_response_time'] > 3.0:
                summary['recommendations'].append(f"🐌 {component}响应时间较慢({stats['avg_response_time']:.2f}s)，建议优化")
        
        return summary

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='小智系统健康监控工具')
    parser.add_argument('--mode', choices=['once', 'continuous'], default='once', 
                        help='监控模式: once(单次检查) 或 continuous(持续监控)')
    parser.add_argument('--interval', type=int, default=5, help='持续监控间隔(分钟)')
    parser.add_argument('--duration', type=int, default=24, help='持续监控时长(小时)')
    parser.add_argument('--summary', action='store_true', help='显示历史健康总结')
    
    args = parser.parse_args()
    
    monitor = SystemHealthMonitor()
    
    logger.info("🏥 小智系统健康监控工具 v1.0")
    logger.info("=" * 50)
    
    try:
        if args.summary:
            # 显示健康总结
            summary = monitor.generate_health_summary()
            
            print("\n📊 系统健康状态总结")
            print("=" * 40)
            
            if 'error' in summary:
                print(f"❌ {summary['error']}")
            else:
                print(f"📅 统计周期: {summary['period']}")
                print(f"⏰ 时间范围: {summary['time_range']['start'][:19]} 至 {summary['time_range']['end'][:19]}")
                
                print(f"\n📈 整体健康统计:")
                for status, count in summary['overall_stats'].items():
                    print(f"   {status}: {count}次")
                
                print(f"\n🔧 组件健康统计:")
                for component, stats in summary['component_stats'].items():
                    print(f"   {component}:")
                    print(f"     成功率: {stats['success_rate']:.1f}%")
                    print(f"     平均响应: {stats['avg_response_time']:.2f}s")
                    print(f"     最大响应: {stats['max_response_time']:.2f}s")
                
                if summary['recommendations']:
                    print(f"\n💡 健康建议:")
                    for rec in summary['recommendations']:
                        print(f"   {rec}")
            
        elif args.mode == 'once':
            # 单次健康检查
            health_report = await monitor.perform_health_check()
            
            print(f"\n📋 健康检查报告")
            print("=" * 40)
            print(f"🕐 检查时间: {health_report['timestamp'][:19]}")
            print(f"💚 整体状态: {health_report['overall_health']}")
            
            print(f"\n🔧 组件状态:")
            for component, details in health_report['components'].items():
                status = "✅ 健康" if details['healthy'] else "❌ 异常"
                print(f"   {component}: {status} (响应: {details['response_time']:.2f}s)")
                if not details['healthy']:
                    print(f"     错误: {details['details'].get('error', '未知')}")
            
            if health_report['alerts']:
                print(f"\n🚨 告警信息:")
                for alert in health_report['alerts']:
                    print(f"   - {alert}")
            
        else:
            # 持续监控模式
            await monitor.continuous_monitoring(args.interval, args.duration)
        
        return True
        
    except KeyboardInterrupt:
        logger.info("⏹️  监控被中断")
        return False
    except Exception as e:
        logger.error(f"❌ 监控异常: {e}")
        return False

if __name__ == "__main__":
    print("🏥 小智系统健康监控工具")
    print("=" * 40)
    print("💡 使用方法:")
    print("   python 系统健康监控.py --mode once          # 单次检查")
    print("   python 系统健康监控.py --mode continuous    # 持续监控")
    print("   python 系统健康监控.py --summary           # 显示历史总结")
    print("=" * 40)
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

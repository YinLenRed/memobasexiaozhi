#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小智系统全套测试一键运行脚本
自动化运行所有测试组件并生成综合报告
"""

import asyncio
import json
import logging
import time
import sys
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'test_logs/master_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger('MasterTest')

class TestSuiteConfig:
    """测试套件配置"""
    
    def __init__(self):
        # 服务配置
        self.java_api_url = "http://q83b6ed9.natappfree.cc"
        self.python_api_url = "http://47.98.51.180:8003"
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.websocket_url = "ws://47.98.51.180:8000/xiaozhi/v1/"
        
        # 设备配置
        self.test_device_id = "f0:9e:9e:04:8a:44"
        
        # 测试配置
        self.enable_hardware_simulator = True
        self.enable_stress_tests = True
        self.concurrent_tests = 3
        self.test_timeout = 300  # 5分钟超时
        
        # 文件路径
        self.test_scripts = {
            'java_api': 'test_java_api.py',
            'mqtt': 'test_mqtt_communication.py',
            'websocket': 'test_websocket_audio.py',
            'full_flow': 'test_full_flow.py'
        }
        self.simulator_script = 'hardware_simulator.py'
        
        # 报告配置
        self.output_dir = 'test_reports'
        self.individual_reports = True
        self.generate_html_report = True

class TestRunner:
    """测试运行器"""
    
    def __init__(self, config: TestSuiteConfig):
        self.config = config
        self.test_results = {}
        self.simulator_process = None
        self.start_time = None
        self.end_time = None
        
        # 确保输出目录存在
        os.makedirs(self.config.output_dir, exist_ok=True)
        os.makedirs('test_logs', exist_ok=True)
    
    async def setup_environment(self) -> bool:
        """环境准备"""
        logger.info("🔧 开始环境准备...")
        
        try:
            # 检查必要的脚本文件
            missing_scripts = []
            for test_name, script_path in self.config.test_scripts.items():
                if not os.path.exists(script_path):
                    missing_scripts.append(script_path)
            
            if missing_scripts:
                logger.error(f"❌ 缺少测试脚本: {', '.join(missing_scripts)}")
                return False
            
            # 启动硬件模拟器
            if self.config.enable_hardware_simulator:
                await self._start_hardware_simulator()
            
            # 等待服务准备就绪
            await self._wait_for_services()
            
            logger.info("✅ 环境准备完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 环境准备失败: {e}")
            return False
    
    async def _start_hardware_simulator(self):
        """启动硬件模拟器"""
        try:
            if not os.path.exists(self.config.simulator_script):
                logger.warning(f"⚠️  硬件模拟器脚本不存在: {self.config.simulator_script}")
                return
            
            logger.info("🤖 启动硬件设备模拟器...")
            
            # 启动模拟器进程
            self.simulator_process = subprocess.Popen([
                sys.executable, self.config.simulator_script,
                self.config.test_device_id
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 等待模拟器启动
            await asyncio.sleep(5)
            
            # 检查进程状态
            if self.simulator_process.poll() is None:
                logger.info("✅ 硬件模拟器启动成功")
            else:
                logger.error("❌ 硬件模拟器启动失败")
                self.simulator_process = None
            
        except Exception as e:
            logger.error(f"❌ 启动硬件模拟器异常: {e}")
    
    async def _wait_for_services(self):
        """等待服务准备就绪"""
        import requests
        
        services = [
            ("Java API", self.config.java_api_url + "/actuator/health"),
            ("Python API", self.config.python_api_url + "/check/hello")
        ]
        
        for service_name, health_url in services:
            logger.info(f"⏳ 等待 {service_name} 准备就绪...")
            
            for attempt in range(30):  # 最多等待30秒
                try:
                    response = requests.get(health_url, timeout=2)
                    if response.status_code == 200:
                        logger.info(f"✅ {service_name} 已就绪")
                        break
                except:
                    pass
                
                await asyncio.sleep(1)
            else:
                logger.warning(f"⚠️  {service_name} 健康检查超时")
    
    async def run_single_test(self, test_name: str, script_path: str, args: List[str] = None) -> Dict:
        """运行单个测试"""
        logger.info(f"🧪 开始运行测试: {test_name}")
        
        start_time = time.time()
        
        try:
            # 构建命令行参数
            cmd = [sys.executable, script_path]
            if args:
                cmd.extend(args)
            
            # 添加通用参数
            cmd.extend([
                '--device-id', self.config.test_device_id,
                '--report', os.path.join(self.config.output_dir, f'{test_name}_report.json')
            ])
            
            # 根据测试类型添加特定参数
            if test_name == 'java_api':
                cmd.extend([
                    '--java-url', self.config.java_api_url,
                    '--python-url', self.config.python_api_url
                ])
            elif test_name == 'mqtt':
                cmd.extend([
                    '--host', self.config.mqtt_host,
                    '--port', str(self.config.mqtt_port),
                    '--concurrent', str(self.config.concurrent_tests)
                ])
            elif test_name == 'websocket':
                cmd.extend([
                    '--websocket-url', self.config.websocket_url,
                    '--concurrent', str(self.config.concurrent_tests)
                ])
            
            logger.info(f"📤 执行命令: {' '.join(cmd)}")
            
            # 运行测试脚本
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 等待测试完成，带超时
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.test_timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise Exception(f"测试超时（{self.config.test_timeout}秒）")
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 分析测试结果
            success = process.returncode == 0
            stdout_text = stdout.decode('utf-8') if stdout else ""
            stderr_text = stderr.decode('utf-8') if stderr else ""
            
            result = {
                'test_name': test_name,
                'success': success,
                'duration': duration,
                'return_code': process.returncode,
                'stdout': stdout_text,
                'stderr': stderr_text,
                'command': ' '.join(cmd),
                'start_time': start_time,
                'end_time': end_time
            }
            
            # 尝试读取详细报告
            report_file = os.path.join(self.config.output_dir, f'{test_name}_report.json')
            if os.path.exists(report_file):
                try:
                    with open(report_file, 'r', encoding='utf-8') as f:
                        detailed_report = json.load(f)
                        result['detailed_report'] = detailed_report
                except Exception as e:
                    logger.warning(f"⚠️  读取详细报告失败 {test_name}: {e}")
            
            if success:
                logger.info(f"✅ 测试完成: {test_name} (耗时: {duration:.1f}秒)")
            else:
                logger.error(f"❌ 测试失败: {test_name} (耗时: {duration:.1f}秒)")
                if stderr_text:
                    logger.error(f"   错误信息: {stderr_text[:500]}...")
            
            return result
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            logger.error(f"❌ 测试异常: {test_name} - {e}")
            
            return {
                'test_name': test_name,
                'success': False,
                'duration': duration,
                'error': str(e),
                'start_time': start_time,
                'end_time': end_time
            }
    
    async def run_all_tests(self) -> Dict:
        """运行所有测试"""
        logger.info("🚀 开始运行完整测试套件")
        self.start_time = time.time()
        
        try:
            # 环境准备
            if not await self.setup_environment():
                return {"success": False, "error": "环境准备失败"}
            
            # 按顺序运行测试
            test_order = ['java_api', 'mqtt', 'websocket', 'full_flow']
            
            for test_name in test_order:
                if test_name in self.config.test_scripts:
                    script_path = self.config.test_scripts[test_name]
                    result = await self.run_single_test(test_name, script_path)
                    self.test_results[test_name] = result
                    
                    # 测试失败后是否继续
                    if not result['success']:
                        logger.warning(f"⚠️  {test_name} 测试失败，但继续执行后续测试")
                        
                    # 测试间隔
                    await asyncio.sleep(2)
            
            self.end_time = time.time()
            
            # 生成综合报告
            comprehensive_report = await self.generate_comprehensive_report()
            
            return comprehensive_report
            
        except Exception as e:
            logger.error(f"❌ 测试套件执行异常: {e}")
            return {"success": False, "error": str(e)}
        
        finally:
            await self.cleanup()
    
    async def generate_comprehensive_report(self) -> Dict:
        """生成综合测试报告"""
        logger.info("📊 生成综合测试报告...")
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results.values() if r['success'])
        failed_tests = total_tests - successful_tests
        
        total_duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        # 收集各测试的详细统计
        test_statistics = {}
        for test_name, result in self.test_results.items():
            detailed = result.get('detailed_report', {})
            test_summary = detailed.get('test_summary', {})
            
            test_statistics[test_name] = {
                'success': result['success'],
                'duration': result['duration'],
                'sub_tests': test_summary.get('total_tests', 0),
                'sub_successful': test_summary.get('successful_tests', 0),
                'sub_success_rate': test_summary.get('success_rate', 0),
                'error': result.get('error'),
                'return_code': result.get('return_code')
            }
        
        # 构建综合报告
        comprehensive_report = {
            'master_summary': {
                'test_suite_version': '1.0.0',
                'total_test_categories': total_tests,
                'successful_categories': successful_tests,
                'failed_categories': failed_tests,
                'overall_success_rate': successful_tests / total_tests * 100 if total_tests > 0 else 0,
                'total_execution_time': total_duration,
                'start_time': datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
                'end_time': datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None
            },
            'test_configuration': {
                'java_api_url': self.config.java_api_url,
                'python_api_url': self.config.python_api_url,
                'mqtt_server': f"{self.config.mqtt_host}:{self.config.mqtt_port}",
                'websocket_url': self.config.websocket_url,
                'test_device_id': self.config.test_device_id,
                'hardware_simulator_used': self.simulator_process is not None,
                'concurrent_tests': self.config.concurrent_tests,
                'test_timeout': self.config.test_timeout
            },
            'test_category_results': test_statistics,
            'detailed_test_results': self.test_results,
            'system_recommendations': self._generate_recommendations()
        }
        
        # 保存综合报告
        master_report_file = os.path.join(
            self.config.output_dir,
            f'master_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        
        with open(master_report_file, 'w', encoding='utf-8') as f:
            json.dump(comprehensive_report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📋 综合报告已保存: {master_report_file}")
        
        # 生成HTML报告
        if self.config.generate_html_report:
            html_report_file = master_report_file.replace('.json', '.html')
            self._generate_html_report(comprehensive_report, html_report_file)
        
        return comprehensive_report
    
    def _generate_recommendations(self) -> List[str]:
        """基于测试结果生成建议"""
        recommendations = []
        
        for test_name, result in self.test_results.items():
            if not result['success']:
                if test_name == 'java_api':
                    recommendations.append("检查Java API服务是否正常运行，端口是否正确")
                elif test_name == 'mqtt':
                    recommendations.append("检查MQTT服务器连接，确认用户名密码正确")
                elif test_name == 'websocket':
                    recommendations.append("检查WebSocket服务器状态，确认音频传输功能")
                elif test_name == 'full_flow':
                    recommendations.append("检查端到端流程，可能需要硬件设备或模拟器")
            
            detailed = result.get('detailed_report', {})
            if detailed:
                # 分析详细报告中的问题
                test_summary = detailed.get('test_summary', {})
                success_rate = test_summary.get('success_rate', 100)
                
                if success_rate < 100:
                    recommendations.append(f"{test_name}测试成功率{success_rate:.1f}%，建议检查相关配置")
        
        if not recommendations:
            recommendations.append("所有测试通过，系统运行正常！")
        
        return recommendations
    
    def _generate_html_report(self, report_data: Dict, html_file: str):
        """生成HTML格式的报告"""
        try:
            html_content = self._create_html_content(report_data)
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"📄 HTML报告已生成: {html_file}")
        except Exception as e:
            logger.error(f"❌ HTML报告生成失败: {e}")
    
    def _create_html_content(self, report_data: Dict) -> str:
        """创建HTML报告内容"""
        master_summary = report_data['master_summary']
        test_results = report_data['test_category_results']
        recommendations = report_data['system_recommendations']
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小智系统测试报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 20px; margin-bottom: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .summary-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .summary-card h3 {{ margin: 0; font-size: 2em; }}
        .summary-card p {{ margin: 5px 0 0 0; }}
        .test-results {{ margin-bottom: 30px; }}
        .test-item {{ background-color: #f8f9fa; margin: 10px 0; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; }}
        .test-item.success {{ border-left-color: #28a745; }}
        .test-item.failure {{ border-left-color: #dc3545; }}
        .test-title {{ font-weight: bold; margin-bottom: 10px; }}
        .test-details {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; font-size: 0.9em; }}
        .recommendations {{ background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 20px; }}
        .recommendations h3 {{ color: #856404; margin-top: 0; }}
        .recommendations ul {{ margin: 10px 0; }}
        .recommendations li {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 小智系统测试报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>{master_summary['successful_categories']}/{master_summary['total_test_categories']}</h3>
                <p>测试通过率</p>
            </div>
            <div class="summary-card">
                <h3>{master_summary['overall_success_rate']:.1f}%</h3>
                <p>综合成功率</p>
            </div>
            <div class="summary-card">
                <h3>{master_summary['total_execution_time']:.1f}s</h3>
                <p>总执行时间</p>
            </div>
        </div>
        
        <div class="test-results">
            <h2>📊 测试结果详情</h2>
        """
        
        for test_name, result in test_results.items():
            success_class = 'success' if result['success'] else 'failure'
            status_icon = '✅' if result['success'] else '❌'
            
            html += f"""
            <div class="test-item {success_class}">
                <div class="test-title">
                    {status_icon} {test_name.upper()} 测试
                </div>
                <div class="test-details">
                    <div><strong>状态:</strong> {'通过' if result['success'] else '失败'}</div>
                    <div><strong>耗时:</strong> {result['duration']:.1f}秒</div>
                    <div><strong>子测试数:</strong> {result['sub_tests']}</div>
                    <div><strong>子测试成功率:</strong> {result['sub_success_rate']:.1f}%</div>
                </div>
            """
            
            if not result['success'] and result.get('error'):
                html += f"<div style='margin-top: 10px; color: #dc3545;'><strong>错误信息:</strong> {result['error']}</div>"
            
            html += "</div>"
        
        html += f"""
        </div>
        
        <div class="recommendations">
            <h3>💡 系统建议</h3>
            <ul>
        """
        
        for rec in recommendations:
            html += f"<li>{rec}</li>"
        
        html += """
            </ul>
        </div>
        
    </div>
</body>
</html>
        """
        
        return html
    
    async def cleanup(self):
        """清理资源"""
        logger.info("🧹 清理资源...")
        
        # 停止硬件模拟器
        if self.simulator_process:
            try:
                self.simulator_process.terminate()
                await asyncio.sleep(2)
                if self.simulator_process.poll() is None:
                    self.simulator_process.kill()
                logger.info("✅ 硬件模拟器已停止")
            except Exception as e:
                logger.error(f"❌ 停止硬件模拟器异常: {e}")

def print_final_summary(report: Dict):
    """打印最终测试总结"""
    print("\n" + "="*80)
    print("🎯 小智系统全套测试总结")
    print("="*80)
    
    summary = report['master_summary']
    
    print(f"📊 总体结果:")
    print(f"  测试类别数: {summary['total_test_categories']}")
    print(f"  成功类别数: {summary['successful_categories']}")
    print(f"  失败类别数: {summary['failed_categories']}")
    print(f"  综合成功率: {summary['overall_success_rate']:.1f}%")
    print(f"  总执行时间: {summary['total_execution_time']:.1f}秒")
    
    print(f"\n📋 各测试类别:")
    for test_name, result in report['test_category_results'].items():
        status = "✅ 通过" if result['success'] else "❌ 失败"
        print(f"  {test_name.upper()}: {status} (耗时: {result['duration']:.1f}s, 成功率: {result['sub_success_rate']:.1f}%)")
    
    print(f"\n💡 系统建议:")
    for i, rec in enumerate(report['system_recommendations'], 1):
        print(f"  {i}. {rec}")
    
    # 判断整体是否成功
    overall_success = summary['overall_success_rate'] >= 80
    
    if overall_success:
        print(f"\n🎉 恭喜！小智系统测试整体通过！")
        print(f"   系统运行状况良好，可以投入使用。")
    else:
        print(f"\n⚠️  小智系统存在一些问题需要解决。")
        print(f"   请根据上述建议进行排查和修复。")
    
    print("="*80)

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='小智系统全套测试一键运行')
    parser.add_argument('--java-url', default='http://q83b6ed9.natappfree.cc', help='Java API服务URL')
    parser.add_argument('--python-url', default='http://47.98.51.180:8003', help='Python API服务URL')
    parser.add_argument('--mqtt-host', default='47.97.185.142', help='MQTT服务器地址')
    parser.add_argument('--mqtt-port', type=int, default=1883, help='MQTT服务器端口')
    parser.add_argument('--websocket-url', default='ws://47.98.51.180:8000/xiaozhi/v1/', help='WebSocket服务器URL')
    parser.add_argument('--device-id', default='f0:9e:9e:04:8a:44', help='测试设备ID')
    parser.add_argument('--no-simulator', action='store_true', help='不启动硬件模拟器')
    parser.add_argument('--no-stress', action='store_true', help='不运行压力测试')
    parser.add_argument('--concurrent', type=int, default=3, help='并发测试数量')
    parser.add_argument('--timeout', type=int, default=300, help='单个测试超时时间(秒)')
    parser.add_argument('--output-dir', default='test_reports', help='测试报告输出目录')
    
    args = parser.parse_args()
    
    # 创建配置
    config = TestSuiteConfig()
    config.java_api_url = args.java_url
    config.python_api_url = args.python_url
    config.mqtt_host = args.mqtt_host
    config.mqtt_port = args.mqtt_port
    config.websocket_url = args.websocket_url
    config.test_device_id = args.device_id
    config.enable_hardware_simulator = not args.no_simulator
    config.enable_stress_tests = not args.no_stress
    config.concurrent_tests = args.concurrent
    config.test_timeout = args.timeout
    config.output_dir = args.output_dir
    
    # 创建测试运行器
    runner = TestRunner(config)
    
    try:
        print("🚀 小智系统全套测试启动")
        print(f"📋 配置信息:")
        print(f"  Java API: {config.java_api_url}")
        print(f"  Python API: {config.python_api_url}")
        print(f"  MQTT: {config.mqtt_host}:{config.mqtt_port}")
        print(f"  WebSocket: {config.websocket_url}")
        print(f"  测试设备: {config.test_device_id}")
        print(f"  硬件模拟器: {'启用' if config.enable_hardware_simulator else '禁用'}")
        print(f"  并发测试数: {config.concurrent_tests}")
        print(f"  测试超时: {config.test_timeout}秒")
        print(f"  输出目录: {config.output_dir}")
        print("-" * 60)
        
        # 运行所有测试
        comprehensive_report = await runner.run_all_tests()
        
        if comprehensive_report.get("success", True):
            # 打印最终总结
            print_final_summary(comprehensive_report)
            
            # 返回成功状态
            overall_success_rate = comprehensive_report.get('master_summary', {}).get('overall_success_rate', 0)
            return overall_success_rate >= 80
        else:
            print(f"\n❌ 测试套件执行失败: {comprehensive_report.get('error', '未知错误')}")
            return False
        
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 测试套件执行异常: {e}")
        return False

if __name__ == "__main__":
    print("🤖 小智系统全套测试套件 v1.0.0")
    print("=" * 80)
    
    success = asyncio.run(main())
    
    if success:
        print("\n🎉 测试套件执行成功！")
        sys.exit(0)
    else:
        print("\n❌ 测试套件执行失败！")
        sys.exit(1)

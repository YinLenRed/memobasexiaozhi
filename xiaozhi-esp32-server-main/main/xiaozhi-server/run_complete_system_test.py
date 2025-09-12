#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python系统完整测试脚本
一键测试所有功能，确保交给硬件人员前Python端无问题
"""

import asyncio
import time
import sys
import json
import subprocess
import traceback
from datetime import datetime
from typing import Dict, List, Tuple
from config.config_loader import load_config
from core.tools.java_backend_weather import JavaBackendWeatherService, ProactiveWeatherGreetingService
from core.mqtt.mqtt_client import MQTTClient
from test_mqtt_client import TestMQTTClient

class SystemTestRunner:
    """系统测试运行器"""
    
    def __init__(self):
        self.config = load_config()
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.start_time = datetime.now()
        
    def log_test_result(self, test_name: str, success: bool, message: str = "", details: str = ""):
        """记录测试结果"""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
        
        self.test_results[test_name] = {
            "status": status,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"{status} {test_name}")
        if message:
            print(f"    📝 {message}")
        if details and not success:
            print(f"    🔍 {details}")
        print()
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🧪 Python系统完整测试")
        print("=" * 60)
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 第一阶段：基础环境测试
        print("📋 第一阶段：基础环境测试")
        print("-" * 40)
        await self.test_environment()
        await self.test_configuration()
        await self.test_network_connectivity()
        
        # 第二阶段：Java API测试
        print("\n📋 第二阶段：Java API测试")
        print("-" * 40)
        await self.test_java_api_connection()
        await self.test_weather_data_quality()
        await self.test_fallback_mechanism()
        
        # 第三阶段：MQTT功能测试
        print("\n📋 第三阶段：MQTT功能测试")
        print("-" * 40)
        await self.test_mqtt_connection()
        await self.test_mqtt_publishing()
        await self.test_mqtt_subscription()
        
        # 第四阶段：业务功能测试
        print("\n📋 第四阶段：业务功能测试")
        print("-" * 40)
        await self.test_weather_greeting_generation()
        await self.test_proactive_greeting_flow()
        await self.test_multi_device_support()
        
        # 第五阶段：稳定性测试
        print("\n📋 第五阶段：稳定性测试")
        print("-" * 40)
        await self.test_error_handling()
        await self.test_service_stability()
        
        # 生成测试报告
        self.generate_test_report()
    
    async def test_environment(self):
        """测试环境检查"""
        try:
            # 检查Python版本
            import sys
            python_version = sys.version
            if sys.version_info >= (3, 7):
                self.log_test_result("Python版本检查", True, f"Python {sys.version_info.major}.{sys.version_info.minor}")
            else:
                self.log_test_result("Python版本检查", False, f"Python版本过低: {python_version}")
            
            # 检查关键包
            try:
                import aiohttp
                import paho.mqtt.client as mqtt
                self.log_test_result("依赖包检查", True, "关键包已安装")
            except ImportError as e:
                self.log_test_result("依赖包检查", False, f"缺少依赖包: {e}")
                
        except Exception as e:
            self.log_test_result("环境检查", False, f"环境检查失败: {e}")
    
    async def test_configuration(self):
        """测试配置文件"""
        try:
            config = self.config
            
            # 检查关键配置项
            required_configs = [
                ("manager-api.url", "Java API地址"),
                ("mqtt.host", "MQTT服务器地址"),
                ("mqtt.username", "MQTT用户名"),
                ("mqtt.password", "MQTT密码")
            ]
            
            missing_configs = []
            for config_path, desc in required_configs:
                keys = config_path.split('.')
                value = config
                for key in keys:
                    value = value.get(key, {})
                
                if not value:
                    missing_configs.append(desc)
            
            if missing_configs:
                self.log_test_result("配置文件检查", False, f"缺少配置: {', '.join(missing_configs)}")
            else:
                self.log_test_result("配置文件检查", True, "所有必要配置项存在")
                
        except Exception as e:
            self.log_test_result("配置文件检查", False, f"配置加载失败: {e}")
    
    async def test_network_connectivity(self):
        """测试网络连通性"""
        import aiohttp
        
        # 测试MQTT服务器
        try:
            mqtt_host = self.config.get("mqtt", {}).get("host", "")
            mqtt_port = self.config.get("mqtt", {}).get("port", 1883)
            
            import socket
            sock = socket.create_connection((mqtt_host, mqtt_port), timeout=5)
            sock.close()
            self.log_test_result("MQTT服务器连通性", True, f"{mqtt_host}:{mqtt_port} 可达")
        except Exception as e:
            self.log_test_result("MQTT服务器连通性", False, f"无法连接: {e}")
        
        # 测试Java API
        try:
            java_api_url = self.config.get("manager-api", {}).get("url", "")
            async with aiohttp.ClientSession() as session:
                async with session.get(java_api_url, timeout=5) as response:
                    if response.status < 500:
                        self.log_test_result("Java API连通性", True, f"{java_api_url} 可达")
                    else:
                        self.log_test_result("Java API连通性", False, f"返回状态码: {response.status}")
        except Exception as e:
            self.log_test_result("Java API连通性", False, f"连接失败: {e}")
    
    async def test_java_api_connection(self):
        """测试Java API连接"""
        try:
            weather_service = JavaBackendWeatherService(self.config)
            
            # 测试实时天气获取
            weather_data = await weather_service.get_current_weather("ESP32_001")
            
            if weather_data and weather_data.get("temperature") and weather_data.get("temperature") != "适宜":
                self.log_test_result("Java API实时天气", True, f"获取到真实数据: {weather_data.get('city')} {weather_data.get('temperature')}℃")
            else:
                self.log_test_result("Java API实时天气", False, "未获取到真实天气数据", str(weather_data))
                
        except Exception as e:
            self.log_test_result("Java API实时天气", False, f"API调用失败: {e}")
    
    async def test_weather_data_quality(self):
        """测试天气数据质量"""
        try:
            weather_service = JavaBackendWeatherService(self.config)
            
            # 测试多个设备的天气数据
            test_devices = ["ESP32_001", "ESP32_002", "00:0c:29:fc:b7:b9"]
            valid_data_count = 0
            
            for device_id in test_devices:
                try:
                    weather_data = await weather_service.get_current_weather(device_id)
                    
                    # 检查数据完整性
                    required_fields = ["city", "temperature", "weather"]
                    if all(weather_data.get(field) for field in required_fields):
                        if weather_data.get("temperature") != "适宜":  # 不是默认数据
                            valid_data_count += 1
                            
                except Exception:
                    continue
            
            if valid_data_count >= 1:
                self.log_test_result("天气数据质量", True, f"{valid_data_count}/{len(test_devices)} 设备获取到真实数据")
            else:
                self.log_test_result("天气数据质量", False, "所有设备都未获取到真实天气数据")
                
        except Exception as e:
            self.log_test_result("天气数据质量", False, f"数据质量检查失败: {e}")
    
    async def test_fallback_mechanism(self):
        """测试回退机制"""
        try:
            weather_service = JavaBackendWeatherService(self.config)
            
            # 测试无效设备ID的回退
            weather_data = await weather_service.get_current_weather("INVALID_DEVICE_123")
            
            if weather_data and weather_data.get("city") and weather_data.get("temperature"):
                self.log_test_result("回退机制测试", True, f"无效设备ID回退成功: {weather_data.get('city')}")
            else:
                self.log_test_result("回退机制测试", False, "回退机制未正常工作")
                
        except Exception as e:
            self.log_test_result("回退机制测试", False, f"回退测试失败: {e}")
    
    async def test_mqtt_connection(self):
        """测试MQTT连接"""
        try:
            mqtt_client = TestMQTTClient(self.config)
            await mqtt_client.connect()
            
            if mqtt_client.is_connected():
                self.log_test_result("MQTT连接测试", True, "MQTT连接成功")
            else:
                self.log_test_result("MQTT连接测试", False, "MQTT连接失败")
            
            await mqtt_client.disconnect()
            
        except Exception as e:
            self.log_test_result("MQTT连接测试", False, f"MQTT连接异常: {e}")
    
    async def test_mqtt_publishing(self):
        """测试MQTT发布功能"""
        try:
            mqtt_client = TestMQTTClient(self.config)
            await mqtt_client.connect()
            
            # 发布测试消息
            test_topic = "test/weather/ESP32_001"
            test_message = {
                "timestamp": datetime.now().isoformat(),
                "city": "测试城市",
                "temperature": "25",
                "device_id": "ESP32_001"
            }
            
            success = await mqtt_client.publish(test_topic, json.dumps(test_message, ensure_ascii=False))
            if success:
                self.log_test_result("MQTT发布测试", True, f"消息发布到 {test_topic}")
            else:
                self.log_test_result("MQTT发布测试", False, "消息发布失败")
            
            await mqtt_client.disconnect()
            
        except Exception as e:
            self.log_test_result("MQTT发布测试", False, f"发布失败: {e}")
    
    async def test_mqtt_subscription(self):
        """测试MQTT订阅功能"""
        try:
            mqtt_client = TestMQTTClient(self.config)
            received_messages = []
            
            # 设置消息回调
            def message_callback(topic, payload):
                received_messages.append((topic, payload))
            
            mqtt_client.set_message_callback(message_callback)
            await mqtt_client.connect()
            
            # 订阅测试主题
            test_topic = "test/weather/subscription"
            await mqtt_client.subscribe(test_topic)
            
            # 发布测试消息
            test_message = "test_subscription_message"
            await mqtt_client.publish(test_topic, test_message)
            
            # 等待消息接收
            await asyncio.sleep(2)
            
            if received_messages:
                self.log_test_result("MQTT订阅测试", True, f"收到 {len(received_messages)} 条消息")
            else:
                self.log_test_result("MQTT订阅测试", False, "未收到订阅消息")
            
            await mqtt_client.disconnect()
            
        except Exception as e:
            self.log_test_result("MQTT订阅测试", False, f"订阅测试失败: {e}")
    
    async def test_weather_greeting_generation(self):
        """测试天气问候生成"""
        try:
            weather_service = JavaBackendWeatherService(self.config)
            greeting_service = ProactiveWeatherGreetingService(self.config, weather_service)
            
            # 生成不同时段的问候
            greeting_types = ["morning", "afternoon", "evening"]
            successful_greetings = 0
            
            for greeting_type in greeting_types:
                try:
                    greeting = await greeting_service.generate_weather_greeting("ESP32_001", greeting_type)
                    
                    # 检查问候质量
                    if greeting and len(greeting) > 20 and "当前城市" not in greeting:
                        successful_greetings += 1
                        
                except Exception:
                    continue
            
            if successful_greetings >= 2:
                self.log_test_result("天气问候生成", True, f"{successful_greetings}/{len(greeting_types)} 类型问候生成成功")
            else:
                self.log_test_result("天气问候生成", False, "问候生成质量不达标")
                
        except Exception as e:
            self.log_test_result("天气问候生成", False, f"问候生成失败: {e}")
    
    async def test_proactive_greeting_flow(self):
        """测试主动问候流程"""
        try:
            # 这里模拟主动问候的关键步骤
            # 1. 天气数据获取
            weather_service = JavaBackendWeatherService(self.config)
            weather_summary = await weather_service.get_weather_summary("ESP32_001")
            
            # 2. 问候内容生成
            greeting_text = weather_service.format_weather_for_greeting(weather_summary)
            
            # 3. MQTT客户端准备
            mqtt_client = MQTTClient(self.config)
            await mqtt_client.start()
            
            # 4. 模拟发送唤醒指令
            awaken_message = {
                "action": "awaken",
                "content": "天气问候",
                "timestamp": datetime.now().isoformat()
            }
            
            # 使用MQTTClient的内置方法发送唤醒指令
            track_id = await mqtt_client.send_awaken_command("ESP32_001", "天气问候", "weather")
            
            await mqtt_client.stop()
            
            if weather_summary and greeting_text and len(greeting_text) > 10 and track_id:
                self.log_test_result("主动问候流程", True, "问候流程各环节正常")
            else:
                self.log_test_result("主动问候流程", False, "问候流程存在问题")
                
        except Exception as e:
            self.log_test_result("主动问候流程", False, f"问候流程测试失败: {e}")
    
    async def test_multi_device_support(self):
        """测试多设备支持"""
        try:
            weather_service = JavaBackendWeatherService(self.config)
            
            # 测试配置中的所有设备
            devices = self.config.get("proactive_greeting", {}).get("weather", {}).get("devices", ["ESP32_001", "ESP32_002"])
            successful_devices = 0
            
            for device_id in devices:
                try:
                    weather_data = await weather_service.get_current_weather(device_id)
                    if weather_data and weather_data.get("city") and weather_data.get("temperature"):
                        successful_devices += 1
                except Exception:
                    continue
            
            if successful_devices >= len(devices) * 0.8:  # 80%的设备成功
                self.log_test_result("多设备支持", True, f"{successful_devices}/{len(devices)} 设备数据获取成功")
            else:
                self.log_test_result("多设备支持", False, f"仅 {successful_devices}/{len(devices)} 设备成功")
                
        except Exception as e:
            self.log_test_result("多设备支持", False, f"多设备测试失败: {e}")
    
    async def test_error_handling(self):
        """测试错误处理"""
        try:
            weather_service = JavaBackendWeatherService(self.config)
            
            # 测试各种异常情况
            error_scenarios = [
                ("空设备ID", ""),
                ("None设备ID", None),
                ("特殊字符设备ID", "!!!@@@###"),
                ("超长设备ID", "A" * 1000)
            ]
            
            handled_errors = 0
            for scenario_name, device_id in error_scenarios:
                try:
                    weather_data = await weather_service.get_current_weather(device_id)
                    if weather_data:  # 只要返回了数据就算处理了错误
                        handled_errors += 1
                except Exception:
                    continue  # 异常也算是一种处理方式
            
            if handled_errors >= len(error_scenarios) * 0.75:
                self.log_test_result("错误处理机制", True, f"{handled_errors}/{len(error_scenarios)} 错误场景正常处理")
            else:
                self.log_test_result("错误处理机制", False, f"错误处理不够健壮")
                
        except Exception as e:
            self.log_test_result("错误处理机制", False, f"错误处理测试失败: {e}")
    
    async def test_service_stability(self):
        """测试服务稳定性（短时间运行测试）"""
        try:
            # 短时间内多次调用API测试稳定性
            weather_service = JavaBackendWeatherService(self.config)
            
            successful_calls = 0
            total_calls = 10
            
            for i in range(total_calls):
                try:
                    weather_data = await weather_service.get_current_weather("ESP32_001")
                    if weather_data and weather_data.get("city"):
                        successful_calls += 1
                    
                    # 短暂等待避免过于频繁
                    await asyncio.sleep(0.5)
                    
                except Exception:
                    continue
            
            success_rate = successful_calls / total_calls
            if success_rate >= 0.8:
                self.log_test_result("服务稳定性", True, f"成功率: {success_rate:.1%} ({successful_calls}/{total_calls})")
            else:
                self.log_test_result("服务稳定性", False, f"成功率过低: {success_rate:.1%}")
                
        except Exception as e:
            self.log_test_result("服务稳定性", False, f"稳定性测试失败: {e}")
    
    def generate_test_report(self):
        """生成测试报告"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        print("\n" + "=" * 60)
        print("🏁 测试完成 - 系统测试报告")
        print("=" * 60)
        
        print(f"📊 测试统计:")
        print(f"   总测试数: {self.total_tests}")
        print(f"   通过数: {self.passed_tests}")
        print(f"   失败数: {self.failed_tests}")
        print(f"   成功率: {self.passed_tests/self.total_tests:.1%}")
        print(f"   测试时长: {duration.total_seconds():.1f}秒")
        
        print(f"\n📋 详细结果:")
        for test_name, result in self.test_results.items():
            print(f"   {result['status']} {test_name}")
            if result['message']:
                print(f"      📝 {result['message']}")
        
        if self.failed_tests > 0:
            print(f"\n❌ 存在失败的测试，需要修复后再交给硬件人员:")
            for test_name, result in self.test_results.items():
                if not result['success']:
                    print(f"   🔧 {test_name}: {result['message']}")
                    if result['details']:
                        print(f"      📋 详情: {result['details']}")
        else:
            print(f"\n🎉 所有测试通过！Python端功能正常，可以交给硬件人员了！")
        
        # 保存详细报告
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "summary": {
                        "total_tests": self.total_tests,
                        "passed_tests": self.passed_tests,
                        "failed_tests": self.failed_tests,
                        "success_rate": self.passed_tests/self.total_tests,
                        "start_time": self.start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "duration_seconds": duration.total_seconds()
                    },
                    "results": self.test_results
                }, f, ensure_ascii=False, indent=2)
            
            print(f"\n📄 详细测试报告已保存到: {report_file}")
            
        except Exception as e:
            print(f"\n⚠️ 保存测试报告失败: {e}")
        
        print(f"\n💡 下一步建议:")
        if self.failed_tests == 0:
            print(f"   1. 启动天气服务: python start_weather_mqtt_service.py")
            print(f"   2. 提供硬件文档: HARDWARE_MQTT_GUIDE.md")
            print(f"   3. 协助硬件调试: python test_mqtt_subscription.py")
        else:
            print(f"   1. 修复失败的测试项")
            print(f"   2. 重新运行测试确认修复")
            print(f"   3. 所有测试通过后再交给硬件人员")

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Python系统完整测试")
    parser.add_argument("--quick", action="store_true", 
                       help="快速测试（跳过稳定性测试）")
    parser.add_argument("--report-only", action="store_true",
                       help="仅生成上次测试的报告")
    
    args = parser.parse_args()
    
    if args.report_only:
        print("📄 查找最近的测试报告...")
        import glob
        reports = glob.glob("test_report_*.json")
        if reports:
            latest_report = max(reports)
            with open(latest_report, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"📊 最近测试报告 ({latest_report}):")
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("❌ 未找到测试报告")
        return
    
    try:
        print("🚀 正在启动Python系统完整测试...")
        print("⏰ 预计耗时: 2-5分钟")
        print()
        
        tester = SystemTestRunner()
        
        if args.quick:
            print("⚡ 快速测试模式（跳过部分稳定性测试）")
            # 可以在这里跳过某些测试
        
        await tester.run_all_tests()
        
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

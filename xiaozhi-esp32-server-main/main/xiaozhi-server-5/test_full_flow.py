#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小智系统全流程端到端测试脚本
测试完整的 Java API -> Python -> MQTT -> 硬件 -> WebSocket -> Python 流程
"""

import asyncio
import json
import time
import logging
import requests
import websockets
import paho.mqtt.client as mqtt
try:
    from paho.mqtt.client import CallbackAPIVersion
except ImportError:
    # paho-mqtt 1.x版本没有CallbackAPIVersion
    pass
from datetime import datetime
from typing import Dict, List, Optional
import uuid

# 确保测试目录存在
import os
os.makedirs('test_logs', exist_ok=True)
os.makedirs('test_reports', exist_ok=True)
os.makedirs('test_audio_data', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'test_logs/full_flow_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

class SystemTestConfig:
    """系统测试配置"""
    
    # Java API配置
    JAVA_API_BASE = "http://q83b6ed9.natappfree.cc"
    
    # Python服务配置
    PYTHON_API_BASE = "http://47.98.51.180:8003"
    
    # MQTT配置
    MQTT_HOST = "47.97.185.142"
    MQTT_PORT = 1883
    MQTT_USERNAME = "admin"
    MQTT_PASSWORD = "Jyxd@2025"
    
    # WebSocket配置
    WEBSOCKET_URL = "ws://47.98.51.180:8000/xiaozhi/v1/"
    
    # 测试设备配置
    TEST_DEVICE_ID = "f0:9e:9e:04:8a:44"
    
    # 超时配置
    MQTT_ACK_TIMEOUT = 10  # MQTT ACK超时时间(秒)
    AUDIO_COMPLETE_TIMEOUT = 30  # 音频播放完成超时时间(秒)
    WEBSOCKET_CONNECT_TIMEOUT = 5  # WebSocket连接超时时间(秒)

class TestResult:
    """测试结果记录"""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = time.time()
        self.end_time = None
        self.success = False
        self.error_message = None
        self.details = {}
        
    def finish(self, success: bool, error_message: str = None, **details):
        self.end_time = time.time()
        self.success = success
        self.error_message = error_message
        self.details.update(details)
        
    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
        
    def to_dict(self) -> dict:
        return {
            "test_name": self.test_name,
            "success": self.success,
            "duration": self.duration,
            "error_message": self.error_message,
            "details": self.details,
            "timestamp": datetime.fromtimestamp(self.start_time).isoformat()
        }

class MQTTTestClient:
    """MQTT测试客户端"""
    
    def __init__(self, config: SystemTestConfig):
        self.config = config
        # MQTT客户端 (兼容paho-mqtt 2.0+)
        try:
            # paho-mqtt 2.0+ 版本
            self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1)
        except (TypeError, NameError):
            # paho-mqtt 1.x 版本向后兼容
            self.client = mqtt.Client()
        self.received_messages = []
        self.ack_received = asyncio.Event()
        self.event_received = asyncio.Event()
        
    def setup(self):
        """设置MQTT客户端"""
        self.client.username_pw_set(self.config.MQTT_USERNAME, self.config.MQTT_PASSWORD)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT客户端连接成功")
            # 订阅ACK和Event主题
            ack_topic = f"device/{self.config.TEST_DEVICE_ID}/ack"
            event_topic = f"device/{self.config.TEST_DEVICE_ID}/event"
            client.subscribe(ack_topic)
            client.subscribe(event_topic)
            logger.info(f"订阅主题: {ack_topic}, {event_topic}")
        else:
            logger.error(f"MQTT连接失败，错误代码: {rc}")
            
    def _on_message(self, client, userdata, msg):
        """处理接收到的消息"""
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            logger.info(f"收到MQTT消息: {topic} -> {payload}")
            
            self.received_messages.append({
                'topic': topic,
                'payload': payload,
                'timestamp': time.time()
            })
            
            # 检查是否是ACK消息
            if topic.endswith('/ack') and payload.get('evt') == 'CMD_RECEIVED':
                logger.info(f"收到ACK确认: {payload.get('track_id')}")
                self.ack_received.set()
                
            # 检查是否是播放完成事件
            if topic.endswith('/event') and payload.get('evt') == 'EVT_SPEAK_DONE':
                logger.info(f"收到播放完成事件: {payload.get('track_id')}")
                self.event_received.set()
                
        except json.JSONDecodeError:
            logger.error(f"无法解析JSON消息: {msg.payload}")
            
    def _on_disconnect(self, client, userdata, rc):
        logger.info(f"MQTT客户端断开连接，代码: {rc}")
        
    async def connect(self) -> bool:
        """连接MQTT服务器"""
        try:
            self.client.connect(self.config.MQTT_HOST, self.config.MQTT_PORT, 60)
            self.client.loop_start()
            
            # 等待连接建立
            for _ in range(50):  # 最多等待5秒
                if self.client.is_connected():
                    return True
                await asyncio.sleep(0.1)
                
            return False
        except Exception as e:
            logger.error(f"MQTT连接异常: {e}")
            return False
            
    def disconnect(self):
        """断开MQTT连接"""
        self.client.loop_stop()
        self.client.disconnect()

class FullFlowTester:
    """全流程测试器"""
    
    def __init__(self):
        self.config = SystemTestConfig()
        self.mqtt_client = MQTTTestClient(self.config)
        self.test_results: List[TestResult] = []
        self.current_track_id = None
        
    async def run_all_tests(self) -> Dict:
        """运行所有测试"""
        logger.info("🚀 开始全流程测试")
        
        # 1. 环境准备测试
        await self._test_environment_setup()
        
        # 2. Java API测试  
        await self._test_java_api()
        
        # 3. Python服务测试
        await self._test_python_service()
        
        # 4. MQTT通信测试
        await self._test_mqtt_communication()
        
        # 5. 完整端到端流程测试
        await self._test_complete_e2e_flow()
        
        # 6. 性能测试
        await self._test_performance()
        
        # 生成测试报告
        return self._generate_test_report()
        
    async def _test_environment_setup(self):
        """测试环境准备"""
        result = TestResult("环境准备测试")
        
        try:
            logger.info("🔧 测试环境准备...")
            
            # 测试Java API可达性
            java_health = await self._check_service_health(
                f"{self.config.JAVA_API_BASE}/actuator/health", "Java API"
            )
            
            # 测试Python服务可达性
            python_health = await self._check_service_health(
                f"{self.config.PYTHON_API_BASE}/check/hello", "Python服务"
            )
            
            # 测试MQTT连接
            mqtt_connected = await self._test_mqtt_connection()
            
            all_ready = java_health and python_health and mqtt_connected
            
            result.finish(
                success=all_ready,
                error_message=None if all_ready else "部分服务不可达",
                java_api_health=java_health,
                python_service_health=python_health,
                mqtt_connected=mqtt_connected
            )
            
        except Exception as e:
            logger.error(f"环境准备测试异常: {e}")
            result.finish(False, str(e))
            
        self.test_results.append(result)
        logger.info(f"✅ 环境准备测试完成: {'通过' if result.success else '失败'}")
        
    async def _check_service_health(self, url: str, service_name: str) -> bool:
        """检查服务健康状态"""
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ {service_name} 健康检查通过")
                return True
            else:
                logger.error(f"❌ {service_name} 健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ {service_name} 健康检查异常: {e}")
            return False
            
    async def _test_mqtt_connection(self) -> bool:
        """测试MQTT连接"""
        try:
            self.mqtt_client.setup()
            connected = await self.mqtt_client.connect()
            if not connected:
                logger.error("❌ MQTT连接失败")
                return False
            logger.info("✅ MQTT连接成功")
            return True
        except Exception as e:
            logger.error(f"❌ MQTT连接测试异常: {e}")
            return False
    
    async def _test_java_api(self):
        """测试Java API"""
        result = TestResult("Java API测试")
        
        try:
            logger.info("🔧 测试Java API接口...")
            
            # 测试配置获取接口
            config_response = requests.post(f"{self.config.JAVA_API_BASE}/config/server-base")
            config_success = config_response.status_code == 200
            
            # 测试主动问候触发接口 (如果存在)
            # 这里需要根据实际的Java API接口调整
            
            result.finish(
                success=config_success,
                error_message=None if config_success else f"API调用失败: {config_response.status_code}",
                config_api_status=config_response.status_code,
                config_response=config_response.text[:200] if config_success else None
            )
            
        except Exception as e:
            logger.error(f"Java API测试异常: {e}")
            result.finish(False, str(e))
            
        self.test_results.append(result)
        logger.info(f"✅ Java API测试完成: {'通过' if result.success else '失败'}")
    
    async def _test_python_service(self):
        """测试Python服务"""
        result = TestResult("Python服务测试")
        
        try:
            logger.info("🔧 测试Python服务...")
            
            # 测试健康检查
            health_response = requests.get(f"{self.config.PYTHON_API_BASE}/check/hello", timeout=5)
            health_success = health_response.status_code == 200
            
            # 测试WebSocket连接 (简单连接测试)
            websocket_success = await self._test_websocket_connection()
            
            all_success = health_success and websocket_success
            
            result.finish(
                success=all_success,
                error_message=None if all_success else "Python服务测试失败",
                health_check=health_success,
                websocket_connection=websocket_success
            )
            
        except Exception as e:
            logger.error(f"Python服务测试异常: {e}")
            result.finish(False, str(e))
            
        self.test_results.append(result)
        logger.info(f"✅ Python服务测试完成: {'通过' if result.success else '失败'}")
    
    async def _test_websocket_connection(self) -> bool:
        """测试WebSocket连接"""
        try:
            async with websockets.connect(
                self.config.WEBSOCKET_URL,
                extra_headers={"Device-ID": self.config.TEST_DEVICE_ID}
            ) as websocket:
                # 发送hello消息
                hello_msg = json.dumps({"type": "hello"})
                await websocket.send(hello_msg)
                logger.info("✅ WebSocket连接测试成功")
                return True
                
        except Exception as e:
            logger.error(f"❌ WebSocket连接测试失败: {e}")
            return False
    
    async def _test_mqtt_communication(self):
        """测试MQTT通信"""
        result = TestResult("MQTT通信测试")
        
        try:
            logger.info("🔧 测试MQTT通信...")
            
            # 生成测试用的track_id
            test_track_id = f"TEST_{int(time.time())}"
            
            # 构建SPEAK命令
            speak_command = {
                "cmd": "SPEAK",
                "text": "这是一个测试消息",
                "track_id": test_track_id,
                "audio_url": self.config.WEBSOCKET_URL,
                "timestamp": datetime.now().isoformat()
            }
            
            # 发布SPEAK命令到设备
            command_topic = f"device/{self.config.TEST_DEVICE_ID}/command"
            self.mqtt_client.client.publish(command_topic, json.dumps(speak_command))
            logger.info(f"📤 发送SPEAK命令: {test_track_id}")
            
            # 等待ACK响应
            self.mqtt_client.ack_received.clear()
            try:
                await asyncio.wait_for(
                    self.mqtt_client.ack_received.wait(), 
                    timeout=self.config.MQTT_ACK_TIMEOUT
                )
                ack_received = True
                logger.info("✅ 收到ACK确认")
            except asyncio.TimeoutError:
                ack_received = False
                logger.error("❌ ACK确认超时")
            
            result.finish(
                success=ack_received,
                error_message=None if ack_received else "ACK确认超时",
                track_id=test_track_id,
                ack_received=ack_received,
                command_sent=True
            )
            
        except Exception as e:
            logger.error(f"MQTT通信测试异常: {e}")
            result.finish(False, str(e))
            
        self.test_results.append(result)
        logger.info(f"✅ MQTT通信测试完成: {'通过' if result.success else '失败'}")
    
    async def _test_complete_e2e_flow(self):
        """完整端到端流程测试"""
        result = TestResult("端到端流程测试")
        
        try:
            logger.info("🚀 开始端到端流程测试...")
            
            # 生成测试用的track_id
            self.current_track_id = f"E2E_TEST_{int(time.time())}"
            
            # 模拟Java API触发主动问候
            # 这里需要调用实际的Java API触发接口
            trigger_success = await self._trigger_proactive_greeting()
            
            if not trigger_success:
                result.finish(False, "主动问候触发失败")
                self.test_results.append(result)
                return
            
            # 等待完整流程完成
            flow_success = await self._wait_for_complete_flow()
            
            result.finish(
                success=flow_success,
                error_message=None if flow_success else "端到端流程未完成",
                track_id=self.current_track_id,
                trigger_success=trigger_success,
                flow_completed=flow_success
            )
            
        except Exception as e:
            logger.error(f"端到端流程测试异常: {e}")
            result.finish(False, str(e))
            
        self.test_results.append(result)
        logger.info(f"✅ 端到端流程测试完成: {'通过' if result.success else '失败'}")
    
    async def _trigger_proactive_greeting(self) -> bool:
        """触发主动问候"""
        try:
            # 这里需要根据实际的Java API接口调整
            # 暂时使用直接调用Python服务的方式
            
            # 或者直接通过Python测试脚本触发
            logger.info("🔔 触发主动问候...")
            
            # 模拟策略保存触发
            test_strategy = {
                "user_request": "测试主动问候功能",
                "device_id": self.config.TEST_DEVICE_ID,
                "task_type": "test"
            }
            
            # 这里可以调用实际的触发接口
            return True
            
        except Exception as e:
            logger.error(f"主动问候触发异常: {e}")
            return False
    
    async def _wait_for_complete_flow(self) -> bool:
        """等待完整流程完成"""
        try:
            # 重置事件状态
            self.mqtt_client.ack_received.clear()
            self.mqtt_client.event_received.clear()
            
            # 等待ACK确认
            try:
                await asyncio.wait_for(
                    self.mqtt_client.ack_received.wait(),
                    timeout=self.config.MQTT_ACK_TIMEOUT
                )
                logger.info("✅ 收到ACK确认")
            except asyncio.TimeoutError:
                logger.error("❌ ACK确认超时")
                return False
            
            # 等待播放完成事件
            try:
                await asyncio.wait_for(
                    self.mqtt_client.event_received.wait(),
                    timeout=self.config.AUDIO_COMPLETE_TIMEOUT
                )
                logger.info("✅ 收到播放完成事件")
                return True
            except asyncio.TimeoutError:
                logger.error("❌ 播放完成事件超时")
                return False
                
        except Exception as e:
            logger.error(f"等待流程完成异常: {e}")
            return False
    
    async def _test_performance(self):
        """性能测试"""
        result = TestResult("性能测试")
        
        try:
            logger.info("⚡ 开始性能测试...")
            
            # 测试多个并发请求
            concurrent_tests = 3
            test_tasks = []
            
            for i in range(concurrent_tests):
                task = asyncio.create_task(self._single_performance_test(i))
                test_tasks.append(task)
            
            # 等待所有测试完成
            results = await asyncio.gather(*test_tasks, return_exceptions=True)
            
            successful_tests = sum(1 for r in results if r is True)
            avg_success_rate = successful_tests / concurrent_tests * 100
            
            result.finish(
                success=avg_success_rate >= 80,  # 80%成功率为通过
                error_message=None if avg_success_rate >= 80 else f"成功率过低: {avg_success_rate}%",
                concurrent_tests=concurrent_tests,
                successful_tests=successful_tests,
                success_rate=avg_success_rate
            )
            
        except Exception as e:
            logger.error(f"性能测试异常: {e}")
            result.finish(False, str(e))
            
        self.test_results.append(result)
        logger.info(f"✅ 性能测试完成: {'通过' if result.success else '失败'}")
    
    async def _single_performance_test(self, test_id: int) -> bool:
        """单个性能测试"""
        try:
            start_time = time.time()
            
            # 执行一个简化的流程测试
            test_track_id = f"PERF_TEST_{test_id}_{int(time.time())}"
            
            # 模拟MQTT命令发送和ACK接收
            speak_command = {
                "cmd": "SPEAK",
                "text": f"性能测试 {test_id}",
                "track_id": test_track_id,
                "audio_url": self.config.WEBSOCKET_URL
            }
            
            command_topic = f"device/{self.config.TEST_DEVICE_ID}/command"
            self.mqtt_client.client.publish(command_topic, json.dumps(speak_command))
            
            # 简化版等待 - 只等待ACK
            try:
                await asyncio.wait_for(
                    self.mqtt_client.ack_received.wait(),
                    timeout=5
                )
                
                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"性能测试 {test_id} 完成，耗时: {duration:.2f}s")
                return True
                
            except asyncio.TimeoutError:
                logger.error(f"性能测试 {test_id} 超时")
                return False
                
        except Exception as e:
            logger.error(f"性能测试 {test_id} 异常: {e}")
            return False
    
    def _generate_test_report(self) -> Dict:
        """生成测试报告"""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.success)
        failed_tests = total_tests - successful_tests
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": successful_tests / total_tests * 100 if total_tests > 0 else 0,
                "total_duration": sum(r.duration for r in self.test_results)
            },
            "test_results": [r.to_dict() for r in self.test_results],
            "system_info": {
                "test_device_id": self.config.TEST_DEVICE_ID,
                "mqtt_server": f"{self.config.MQTT_HOST}:{self.config.MQTT_PORT}",
                "websocket_url": self.config.WEBSOCKET_URL,
                "test_timestamp": datetime.now().isoformat()
            }
        }
        
        return report
    
    def cleanup(self):
        """清理资源"""
        try:
            self.mqtt_client.disconnect()
        except:
            pass

async def main():
    """主测试函数"""
    tester = FullFlowTester()
    
    try:
        # 运行所有测试
        report = await tester.run_all_tests()
        
        # 输出测试报告
        logger.info("\n" + "="*50)
        logger.info("📊 测试报告")
        logger.info("="*50)
        
        summary = report["test_summary"]
        logger.info(f"总测试数: {summary['total_tests']}")
        logger.info(f"成功测试数: {summary['successful_tests']}")
        logger.info(f"失败测试数: {summary['failed_tests']}")
        logger.info(f"成功率: {summary['success_rate']:.1f}%")
        logger.info(f"总耗时: {summary['total_duration']:.2f}s")
        
        # 保存详细报告到文件
        report_file = f"test_reports/full_flow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        import os
        os.makedirs("test_reports", exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"详细报告已保存到: {report_file}")
        
        # 输出失败的测试
        failed_results = [r for r in tester.test_results if not r.success]
        if failed_results:
            logger.info("\n❌ 失败的测试:")
            for result in failed_results:
                logger.error(f"  - {result.test_name}: {result.error_message}")
        
        return summary['success_rate'] >= 80  # 80%以上成功率为整体通过
        
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        return False
        
    except Exception as e:
        logger.error(f"测试执行异常: {e}")
        return False
        
    finally:
        tester.cleanup()

if __name__ == "__main__":
    # 创建必要的目录
    import os
    os.makedirs("test_logs", exist_ok=True)
    os.makedirs("test_reports", exist_ok=True)
    
    # 运行测试
    success = asyncio.run(main())
    
    if success:
        print("\n🎉 全流程测试通过!")
        exit(0)
    else:
        print("\n❌ 全流程测试失败!")
        exit(1)

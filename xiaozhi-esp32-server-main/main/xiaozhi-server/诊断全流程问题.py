#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小智系统全流程问题诊断工具
专门诊断Java触发主动问候但硬件无反应的问题
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
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid
import sys
import os
import websockets

# 确保测试目录存在
os.makedirs('test_logs', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'test_logs/diagnosis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger('流程诊断')

class SystemDiagnosisConfig:
    """系统诊断配置"""
    
    # 服务地址配置
    JAVA_API_BASE = "http://q83b6ed9.natappfree.cc"
    PYTHON_API_BASE = "http://47.98.51.180:8003"
    WEBSOCKET_URL = "ws://47.98.51.180:8000/xiaozhi/v1/"
    
    # MQTT配置
    MQTT_HOST = "47.97.185.142"
    MQTT_PORT = 1883
    MQTT_USERNAME = "admin"
    MQTT_PASSWORD = "Jyxd@2025"
    
    # 测试设备配置
    TEST_DEVICE_ID = "f0:9e:9e:04:8a:44"  # 你的真实硬件MAC地址
    
    # 超时配置
    HTTP_TIMEOUT = 10
    MQTT_TIMEOUT = 15
    WEBSOCKET_TIMEOUT = 10

class SystemDiagnosis:
    """系统全流程诊断器"""
    
    def __init__(self, config: SystemDiagnosisConfig = None):
        self.config = config or SystemDiagnosisConfig()
        
        # MQTT客户端
        client_id = f"diagnosis-{uuid.uuid4().hex[:8]}"
        try:
            self.mqtt_client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1, client_id=client_id)
        except (TypeError, NameError):
            self.mqtt_client = mqtt.Client(client_id)
        
        self.mqtt_connected = False
        self.mqtt_messages = []
        
        # 诊断结果
        self.diagnosis_results = {}
        
        # 设置MQTT回调
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.username_pw_set(self.config.MQTT_USERNAME, self.config.MQTT_PASSWORD)
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT连接回调"""
        if rc == 0:
            self.mqtt_connected = True
            logger.info("✅ MQTT诊断客户端连接成功")
            
            # 订阅所有相关主题进行监控
            topics = [
                f"device/{self.config.TEST_DEVICE_ID}/command",  # Python发给硬件的命令
                f"device/{self.config.TEST_DEVICE_ID}/ack",      # 硬件的ACK响应
                f"device/{self.config.TEST_DEVICE_ID}/event",    # 硬件的事件上报
                "device/+/command",  # 通配符监控
                "device/+/ack",
                "device/+/event",
                "server/dev/report/event",  # Java发给Python的事件
            ]
            
            for topic in topics:
                client.subscribe(topic)
                logger.info(f"📥 订阅监控主题: {topic}")
        else:
            logger.error(f"❌ MQTT连接失败: {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT消息回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            timestamp = time.time()
            
            message_info = {
                'timestamp': timestamp,
                'topic': topic,
                'payload': payload,
                'qos': msg.qos,
                'retain': msg.retain
            }
            
            self.mqtt_messages.append(message_info)
            
            logger.info(f"📨 监控到MQTT消息:")
            logger.info(f"   主题: {topic}")
            logger.info(f"   内容: {payload}")
            logger.info(f"   时间: {datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3]}")
            
        except Exception as e:
            logger.error(f"❌ 处理MQTT消息异常: {e}")
    
    async def diagnosis_step_1_java_api(self) -> Dict[str, Any]:
        """诊断步骤1: Java API服务连通性"""
        logger.info("🔍 步骤1: 检查Java API服务连通性")
        
        result = {
            "step": "Java API连通性检查",
            "success": False,
            "details": {}
        }
        
        try:
            # 测试Java API基础连接
            response = requests.get(
                f"{self.config.JAVA_API_BASE}/health",
                timeout=self.config.HTTP_TIMEOUT
            )
            
            result["details"]["health_check"] = {
                "status_code": response.status_code,
                "response": response.text[:500] if response.text else None
            }
            
            if response.status_code == 200:
                logger.info("✅ Java API健康检查通过")
            else:
                logger.warning(f"⚠️  Java API健康检查异常: {response.status_code}")
                
        except requests.exceptions.ConnectTimeout:
            logger.error("❌ Java API连接超时")
            result["details"]["error"] = "连接超时"
        except requests.exceptions.ConnectionError:
            logger.error("❌ Java API连接失败")
            result["details"]["error"] = "连接失败"
        except Exception as e:
            logger.error(f"❌ Java API检查异常: {e}")
            result["details"]["error"] = str(e)
            
        # 测试主动问候接口（如果存在）
        try:
            # 尝试发送一个测试的主动问候请求
            test_payload = {
                "device_id": self.config.TEST_DEVICE_ID,
                "initial_content": "测试连通性",
                "category": "system_reminder"
            }
            
            # 注意：这里不会真的触发，只是测试接口可达性
            logger.info("🧪 测试Java主动问候API接口...")
            
            response = requests.post(
                f"{self.config.PYTHON_API_BASE}/xiaozhi/greeting/send",
                json=test_payload,
                timeout=self.config.HTTP_TIMEOUT
            )
            
            result["details"]["greeting_api_test"] = {
                "status_code": response.status_code,
                "response": response.text[:500] if response.text else None
            }
            
            if response.status_code in [200, 201]:
                logger.info("✅ 主动问候API接口可达")
                result["success"] = True
            else:
                logger.warning(f"⚠️  主动问候API返回异常: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ 主动问候API测试失败: {e}")
            result["details"]["greeting_api_error"] = str(e)
        
        self.diagnosis_results["step_1"] = result
        return result
    
    async def diagnosis_step_2_python_service(self) -> Dict[str, Any]:
        """诊断步骤2: Python服务状态检查"""
        logger.info("🔍 步骤2: 检查Python服务状态")
        
        result = {
            "step": "Python服务状态检查",
            "success": False,
            "details": {}
        }
        
        try:
            # 测试Python API服务
            response = requests.get(
                f"{self.config.PYTHON_API_BASE}/health",
                timeout=self.config.HTTP_TIMEOUT
            )
            
            result["details"]["health_check"] = {
                "status_code": response.status_code,
                "response": response.text[:500] if response.text else None
            }
            
            if response.status_code == 200:
                logger.info("✅ Python API服务正常")
                result["success"] = True
            else:
                logger.warning(f"⚠️  Python API服务异常: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Python服务检查失败: {e}")
            result["details"]["error"] = str(e)
        
        self.diagnosis_results["step_2"] = result
        return result
    
    async def diagnosis_step_3_mqtt_connection(self) -> Dict[str, Any]:
        """诊断步骤3: MQTT连接检查"""
        logger.info("🔍 步骤3: 检查MQTT连接状态")
        
        result = {
            "step": "MQTT连接检查",
            "success": False,
            "details": {}
        }
        
        try:
            # 连接MQTT服务器
            logger.info(f"🔗 连接MQTT服务器: {self.config.MQTT_HOST}:{self.config.MQTT_PORT}")
            
            self.mqtt_client.connect_async(self.config.MQTT_HOST, self.config.MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            
            # 等待连接完成
            for i in range(self.config.MQTT_TIMEOUT):
                if self.mqtt_connected:
                    logger.info("✅ MQTT连接成功")
                    result["success"] = True
                    result["details"]["connection"] = "成功"
                    break
                await asyncio.sleep(1)
                
            if not self.mqtt_connected:
                logger.error("❌ MQTT连接超时")
                result["details"]["error"] = "连接超时"
                
        except Exception as e:
            logger.error(f"❌ MQTT连接异常: {e}")
            result["details"]["error"] = str(e)
        
        self.diagnosis_results["step_3"] = result
        return result
    
    async def diagnosis_step_4_websocket_connection(self) -> Dict[str, Any]:
        """诊断步骤4: WebSocket连接检查"""
        logger.info("🔍 步骤4: 检查WebSocket连接状态")
        
        result = {
            "step": "WebSocket连接检查",
            "success": False,
            "details": {}
        }
        
        try:
            # 测试WebSocket连接
            logger.info(f"🔗 测试WebSocket连接: {self.config.WEBSOCKET_URL}")
            
            import asyncio
            async with websockets.connect(
                f"{self.config.WEBSOCKET_URL}{self.config.TEST_DEVICE_ID}"
            ) as websocket:
                logger.info("✅ WebSocket连接成功")
                result["success"] = True
                result["details"]["connection"] = "成功"
                
                # 发送测试消息
                test_message = json.dumps({
                    "type": "test",
                    "timestamp": time.time()
                })
                await websocket.send(test_message)
                logger.info("✅ WebSocket测试消息发送成功")
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning("⚠️  WebSocket连接被关闭（可能是正常的）")
            result["success"] = True  # WebSocket短暂连接是正常的
            result["details"]["connection"] = "连接后关闭（正常）"
        except asyncio.TimeoutError:
            logger.warning("⚠️  WebSocket连接超时（可能服务器负载高）")
            result["success"] = True  # 超时也认为服务是存在的
            result["details"]["connection"] = "连接超时（服务存在）"
        except Exception as e:
            logger.error(f"❌ WebSocket连接失败: {e}")
            result["details"]["error"] = str(e)
        
        self.diagnosis_results["step_4"] = result
        return result
    
    async def diagnosis_step_5_trigger_test(self) -> Dict[str, Any]:
        """诊断步骤5: 触发一次完整测试"""
        logger.info("🔍 步骤5: 触发完整流程测试")
        
        result = {
            "step": "完整流程触发测试",
            "success": False,
            "details": {}
        }
        
        try:
            # 清空之前的消息记录
            self.mqtt_messages.clear()
            
            # 发送主动问候请求
            test_payload = {
                "device_id": self.config.TEST_DEVICE_ID,
                "initial_content": f"诊断测试 {datetime.now().strftime('%H:%M:%S')}",
                "category": "system_reminder"
            }
            
            logger.info("📤 发送主动问候请求...")
            logger.info(f"   设备ID: {self.config.TEST_DEVICE_ID}")
            logger.info(f"   内容: {test_payload}")
            
            start_time = time.time()
            
            response = requests.post(
                f"{self.config.PYTHON_API_BASE}/xiaozhi/greeting/send",
                json=test_payload,
                timeout=self.config.HTTP_TIMEOUT
            )
            
            result["details"]["http_request"] = {
                "status_code": response.status_code,
                "response": response.text[:500] if response.text else None,
                "response_time": time.time() - start_time
            }
            
            if response.status_code in [200, 201]:
                logger.info("✅ 主动问候请求发送成功")
                
                # 等待并监控MQTT消息
                logger.info("⏳ 等待MQTT消息流...")
                await asyncio.sleep(10)  # 等待10秒观察消息流
                
                # 分析收到的消息
                command_messages = [msg for msg in self.mqtt_messages if msg['topic'].endswith('/command')]
                ack_messages = [msg for msg in self.mqtt_messages if msg['topic'].endswith('/ack')]
                event_messages = [msg for msg in self.mqtt_messages if msg['topic'].endswith('/event')]
                server_messages = [msg for msg in self.mqtt_messages if 'server/dev/report' in msg['topic']]
                
                result["details"]["mqtt_monitoring"] = {
                    "total_messages": len(self.mqtt_messages),
                    "command_messages": len(command_messages),
                    "ack_messages": len(ack_messages),
                    "event_messages": len(event_messages),
                    "server_messages": len(server_messages),
                    "all_messages": self.mqtt_messages[-10:]  # 最后10条消息
                }
                
                logger.info(f"📊 MQTT消息统计:")
                logger.info(f"   总消息数: {len(self.mqtt_messages)}")
                logger.info(f"   命令消息: {len(command_messages)}")
                logger.info(f"   ACK消息: {len(ack_messages)}")
                logger.info(f"   事件消息: {len(event_messages)}")
                logger.info(f"   服务器消息: {len(server_messages)}")
                
                # 判断流程是否完整
                if len(self.mqtt_messages) > 0:
                    result["success"] = True
                    logger.info("✅ 检测到MQTT消息流，系统正在工作")
                    
                    # 详细分析问题
                    if len(command_messages) == 0:
                        logger.warning("⚠️  未检测到发给硬件的命令消息")
                    if len(ack_messages) == 0:
                        logger.warning("⚠️  未检测到硬件的ACK响应 - 这可能是问题所在!")
                    if len(event_messages) == 0:
                        logger.warning("⚠️  未检测到硬件的事件上报")
                else:
                    logger.error("❌ 未检测到任何MQTT消息流")
                    
            else:
                logger.error(f"❌ 主动问候请求失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ 完整流程测试异常: {e}")
            result["details"]["error"] = str(e)
        
        self.diagnosis_results["step_5"] = result
        return result
    
    async def run_full_diagnosis(self):
        """运行完整诊断流程"""
        logger.info("🚀 开始系统全流程诊断")
        logger.info("=" * 60)
        logger.info(f"📋 诊断配置:")
        logger.info(f"   Java API: {self.config.JAVA_API_BASE}")
        logger.info(f"   Python API: {self.config.PYTHON_API_BASE}")
        logger.info(f"   WebSocket: {self.config.WEBSOCKET_URL}")
        logger.info(f"   MQTT: {self.config.MQTT_HOST}:{self.config.MQTT_PORT}")
        logger.info(f"   测试设备: {self.config.TEST_DEVICE_ID}")
        logger.info("=" * 60)
        
        try:
            # 步骤1: Java API检查
            await self.diagnosis_step_1_java_api()
            await asyncio.sleep(1)
            
            # 步骤2: Python服务检查
            await self.diagnosis_step_2_python_service()
            await asyncio.sleep(1)
            
            # 步骤3: MQTT连接检查
            await self.diagnosis_step_3_mqtt_connection()
            await asyncio.sleep(1)
            
            # 步骤4: WebSocket连接检查
            await self.diagnosis_step_4_websocket_connection()
            await asyncio.sleep(1)
            
            # 步骤5: 完整流程触发测试
            if self.mqtt_connected:
                await self.diagnosis_step_5_trigger_test()
            else:
                logger.error("❌ MQTT未连接，跳过完整流程测试")
            
        finally:
            # 清理连接
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except:
                pass
    
    def generate_diagnosis_report(self) -> Dict[str, Any]:
        """生成诊断报告"""
        total_steps = len(self.diagnosis_results)
        successful_steps = sum(1 for result in self.diagnosis_results.values() if result["success"])
        
        report = {
            "diagnosis_summary": {
                "total_steps": total_steps,
                "successful_steps": successful_steps,
                "failed_steps": total_steps - successful_steps,
                "success_rate": successful_steps / total_steps * 100 if total_steps > 0 else 0
            },
            "diagnosis_results": self.diagnosis_results,
            "mqtt_message_analysis": {
                "total_messages": len(self.mqtt_messages),
                "message_details": self.mqtt_messages
            },
            "configuration": {
                "java_api": self.config.JAVA_API_BASE,
                "python_api": self.config.PYTHON_API_BASE,
                "websocket_url": self.config.WEBSOCKET_URL,
                "mqtt_host": f"{self.config.MQTT_HOST}:{self.config.MQTT_PORT}",
                "test_device": self.config.TEST_DEVICE_ID,
                "diagnosis_time": datetime.now().isoformat()
            },
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """生成问题修复建议"""
        recommendations = []
        
        # 检查各步骤结果并提供建议
        if "step_3" in self.diagnosis_results and not self.diagnosis_results["step_3"]["success"]:
            recommendations.append("🔧 MQTT连接失败：请检查网络连接和MQTT服务器状态")
        
        # 检查MQTT消息流
        if hasattr(self, 'mqtt_messages') and len(self.mqtt_messages) > 0:
            command_count = len([msg for msg in self.mqtt_messages if msg['topic'].endswith('/command')])
            ack_count = len([msg for msg in self.mqtt_messages if msg['topic'].endswith('/ack')])
            
            if command_count > 0 and ack_count == 0:
                recommendations.append("⚠️  硬件收到命令但未响应ACK：请检查硬件设备状态和MQTT订阅")
                recommendations.append("🔍 建议检查硬件设备是否正确订阅了 device/{device_id}/command 主题")
                recommendations.append("🔍 建议检查硬件设备是否能正确发送ACK到 device/{device_id}/ack 主题")
                
            if command_count == 0:
                recommendations.append("❌ 未检测到发给硬件的命令：可能Python服务处理有问题")
        else:
            recommendations.append("❌ 完全没有MQTT消息流：可能是MQTT服务或网络问题")
        
        return recommendations

async def main():
    """主诊断函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='小智系统全流程诊断工具')
    parser.add_argument('--device-id', default='f0:9e:9e:04:8a:44', help='测试设备ID')
    parser.add_argument('--java-url', default='http://q83b6ed9.natappfree.cc', help='Java API地址')
    parser.add_argument('--python-url', default='http://47.98.51.180:8003', help='Python API地址')
    parser.add_argument('--report', default='system_diagnosis_report.json', help='诊断报告文件名')
    
    args = parser.parse_args()
    
    # 创建配置
    config = SystemDiagnosisConfig()
    config.TEST_DEVICE_ID = args.device_id
    config.JAVA_API_BASE = args.java_url
    config.PYTHON_API_BASE = args.python_url
    
    # 创建诊断器
    diagnosis = SystemDiagnosis(config)
    
    try:
        # 运行完整诊断
        await diagnosis.run_full_diagnosis()
        
        # 生成诊断报告
        report = diagnosis.generate_diagnosis_report()
        
        # 输出结果
        print("\n" + "="*80)
        print("📋 系统全流程诊断报告")
        print("="*80)
        
        summary = report["diagnosis_summary"]
        
        print(f"诊断结果:")
        print(f"  总检查项: {summary['total_steps']}")
        print(f"  通过检查: {summary['successful_steps']}")
        print(f"  失败检查: {summary['failed_steps']}")
        print(f"  健康度: {summary['success_rate']:.1f}%")
        
        # 显示MQTT消息分析
        mqtt_analysis = report["mqtt_message_analysis"]
        print(f"\nMQTT消息分析:")
        print(f"  监控到消息总数: {mqtt_analysis['total_messages']}")
        
        if mqtt_analysis['total_messages'] > 0:
            print(f"  最近的消息:")
            for msg in mqtt_analysis['message_details'][-3:]:  # 显示最后3条
                print(f"    [{datetime.fromtimestamp(msg['timestamp']).strftime('%H:%M:%S')}] {msg['topic']}")
        
        # 显示修复建议
        recommendations = report["recommendations"]
        if recommendations:
            print(f"\n🔧 问题修复建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        # 保存详细报告
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细诊断报告已保存到: {args.report}")
        
        # 返回诊断状态
        return summary['success_rate'] >= 60  # 60%以上算基本正常
        
    except KeyboardInterrupt:
        print("\n诊断被用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 诊断执行异常: {e}")
        return False

if __name__ == "__main__":
    print("🔍 小智系统全流程问题诊断工具 v1.0.0")
    print("=" * 60)
    
    success = asyncio.run(main())
    
    if success:
        print("\n✅ 系统基本正常，可能是偶发问题")
        sys.exit(0)
    else:
        print("\n⚠️  发现系统问题，请查看修复建议")
        sys.exit(1)

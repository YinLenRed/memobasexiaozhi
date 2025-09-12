#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比Java触发和Python测试脚本的差异
找出为什么Java触发没声音，Python测试有声音
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
from typing import Dict, List, Any
import uuid
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('差异对比')

class TriggerDifferenceAnalyzer:
    """触发差异分析器"""
    
    def __init__(self):
        self.device_id = "f0:9e:9e:04:8a:44"
        self.python_api = "http://47.98.51.180:8003"
        
        # MQTT配置
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.mqtt_username = "admin"
        self.mqtt_password = "Jyxd@2025"
        
        # MQTT客户端
        client_id = f"diff-analyzer-{uuid.uuid4().hex[:6]}"
        try:
            self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1, client_id=client_id)
        except (TypeError, NameError):
            self.client = mqtt.Client(client_id)
        
        self.connected = False
        self.test_results = {
            'python_test': {},
            'java_trigger': {}
        }
        
        # 设置MQTT回调
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.connected = True
            logger.info("✅ MQTT分析连接成功")
            
            # 订阅所有相关主题
            topics = [
                f"device/{self.device_id}/command",
                f"device/{self.device_id}/ack", 
                f"device/{self.device_id}/event",
                "server/dev/report/event",
            ]
            
            for topic in topics:
                client.subscribe(topic)
                logger.info(f"📥 订阅: {topic}")
        else:
            logger.error(f"❌ MQTT连接失败: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """消息回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            timestamp = time.time()
            
            message_info = {
                'timestamp': timestamp,
                'time_str': datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3],
                'topic': topic,
                'payload': payload
            }
            
            # 根据当前测试阶段记录消息
            current_test = getattr(self, 'current_test_phase', None)
            if current_test:
                if 'messages' not in self.test_results[current_test]:
                    self.test_results[current_test]['messages'] = []
                self.test_results[current_test]['messages'].append(message_info)
            
            # 实时显示重要消息
            try:
                data = json.loads(payload)
                
                if topic.endswith('/command') and self.device_id in topic:
                    logger.info(f"📤 [{message_info['time_str']}] 命令: {data.get('cmd')}")
                    logger.info(f"   Track: {data.get('track_id')}")
                    logger.info(f"   文本: {data.get('text', '')[:40]}...")
                    logger.info(f"   音频URL: {data.get('audio_url')}")
                    
                elif topic.endswith('/ack') and self.device_id in topic:
                    logger.info(f"✅ [{message_info['time_str']}] ACK: {data.get('evt')}")
                    
                elif topic.endswith('/event') and self.device_id in topic:
                    logger.info(f"📢 [{message_info['time_str']}] 事件: {data.get('evt')}")
                    
            except json.JSONDecodeError:
                pass
                
        except Exception as e:
            logger.error(f"❌ 处理消息异常: {e}")
    
    async def connect_mqtt(self):
        """连接MQTT"""
        try:
            logger.info("🔗 建立分析连接...")
            self.client.connect_async(self.mqtt_host, self.mqtt_port, 60)
            self.client.loop_start()
            
            for i in range(10):
                if self.connected:
                    return True
                await asyncio.sleep(1)
            
            return False
            
        except Exception as e:
            logger.error(f"❌ MQTT连接异常: {e}")
            return False
    
    async def test_python_script_trigger(self):
        """测试Python脚本触发（有声音的）"""
        logger.info("🐍 测试Python脚本触发（参照组）")
        logger.info("="*50)
        
        self.current_test_phase = 'python_test'
        
        # Python测试用的参数（模拟检查音频问题.py的调用）
        test_payload = {
            "device_id": self.device_id,
            "initial_content": f"Python测试音频 {datetime.now().strftime('%H:%M:%S')}",
            "category": "system_reminder"
        }
        
        logger.info("📤 发送Python测试请求...")
        logger.info(f"   参数: {test_payload}")
        
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.python_api}/xiaozhi/greeting/send",
                json=test_payload,
                timeout=15
            )
            
            response_time = time.time() - start_time
            
            # 记录请求结果
            self.test_results['python_test'] = {
                'request_payload': test_payload,
                'response_status': response.status_code,
                'response_time': response_time,
                'response_data': response.json() if response.status_code in [200, 201] else response.text,
                'messages': []
            }
            
            logger.info(f"📊 Python测试结果:")
            logger.info(f"   状态码: {response.status_code}")
            logger.info(f"   响应时间: {response_time:.2f}秒")
            
            if response.status_code in [200, 201]:
                result = response.json()
                track_id = result.get('track_id')
                logger.info(f"   Track ID: {track_id}")
                logger.info("✅ Python测试请求成功")
                
                # 等待MQTT消息流
                logger.info("⏳ 收集Python测试的MQTT消息流...")
                await asyncio.sleep(15)  # 等待15秒收集消息
                
                return True
            else:
                logger.error(f"❌ Python测试失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Python测试异常: {e}")
            return False
    
    async def wait_for_java_trigger(self, timeout=60):
        """等待Java触发（没声音的）"""
        logger.info("☕ 等待Java后端触发（问题组）")
        logger.info("="*50)
        
        self.current_test_phase = 'java_trigger'
        
        logger.info("💡 请现在通过Java后端触发一次主动问候...")
        logger.info("⏳ 等待Java触发...")
        
        start_time = time.time()
        java_triggered = False
        
        # 初始化Java测试结果
        self.test_results['java_trigger'] = {
            'detected': False,
            'messages': []
        }
        
        while time.time() - start_time < timeout:
            await asyncio.sleep(2)
            
            # 检查是否有Java触发的迹象
            messages = self.test_results['java_trigger'].get('messages', [])
            
            # 查找命令消息
            command_messages = [msg for msg in messages if msg['topic'].endswith('/command')]
            server_messages = [msg for msg in messages if 'server/dev/report' in msg['topic']]
            
            if command_messages or server_messages:
                if not java_triggered:
                    logger.info("✅ 检测到Java触发!")
                    java_triggered = True
                    self.test_results['java_trigger']['detected'] = True
                    
                    # 继续收集15秒的消息
                    logger.info("⏳ 收集Java触发的MQTT消息流...")
                    await asyncio.sleep(15)
                    break
            
            # 显示等待状态
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                logger.info(f"⏳ 已等待 {elapsed}/{timeout} 秒...")
        
        if not java_triggered:
            logger.warning("⚠️  未检测到Java触发")
            return False
        
        return True
    
    def analyze_differences(self):
        """分析两种触发方式的差异"""
        logger.info("\n" + "="*60)
        logger.info("🔍 Java vs Python 触发差异分析")
        logger.info("="*60)
        
        python_result = self.test_results.get('python_test', {})
        java_result = self.test_results.get('java_trigger', {})
        
        # 基础信息对比
        logger.info("📋 基础对比:")
        logger.info(f"   Python测试检测: {'✅' if python_result else '❌'}")
        logger.info(f"   Java触发检测: {'✅' if java_result.get('detected') else '❌'}")
        
        if not python_result or not java_result.get('detected'):
            logger.error("❌ 缺少对比数据，无法进行分析")
            return
        
        # 分析MQTT消息差异
        logger.info(f"\n📨 MQTT消息流对比:")
        
        python_messages = python_result.get('messages', [])
        java_messages = java_result.get('messages', [])
        
        logger.info(f"   Python测试消息数: {len(python_messages)}")
        logger.info(f"   Java触发消息数: {len(java_messages)}")
        
        # 分析命令消息差异
        python_commands = [msg for msg in python_messages if msg['topic'].endswith('/command')]
        java_commands = [msg for msg in java_messages if msg['topic'].endswith('/command')]
        
        logger.info(f"\n📤 命令消息对比:")
        logger.info(f"   Python测试命令: {len(python_commands)}")
        logger.info(f"   Java触发命令: {len(java_commands)}")
        
        if python_commands and java_commands:
            logger.info(f"\n🔍 命令内容对比:")
            
            # 解析Python命令
            try:
                python_cmd = json.loads(python_commands[0]['payload'])
                logger.info(f"   Python命令:")
                logger.info(f"     文本: {python_cmd.get('text', '')[:50]}...")
                logger.info(f"     音频URL: {python_cmd.get('audio_url')}")
                logger.info(f"     Track ID: {python_cmd.get('track_id')}")
            except:
                logger.error("   ❌ Python命令解析失败")
            
            # 解析Java命令
            try:
                java_cmd = json.loads(java_commands[0]['payload'])
                logger.info(f"   Java命令:")
                logger.info(f"     文本: {java_cmd.get('text', '')[:50]}...")
                logger.info(f"     音频URL: {java_cmd.get('audio_url')}")
                logger.info(f"     Track ID: {java_cmd.get('track_id')}")
                
                # 关键差异检查
                logger.info(f"\n⚠️  关键差异检查:")
                
                if python_cmd.get('audio_url') and not java_cmd.get('audio_url'):
                    logger.error("❌ 关键问题: Java触发的命令没有audio_url!")
                    logger.error("   这就是没有声音的原因!")
                elif not python_cmd.get('audio_url') and not java_cmd.get('audio_url'):
                    logger.warning("⚠️  两者都没有audio_url，可能音频URL字段名不同")
                elif python_cmd.get('audio_url') != java_cmd.get('audio_url'):
                    logger.warning("⚠️  音频URL不同:")
                    logger.warning(f"     Python: {python_cmd.get('audio_url')}")
                    logger.warning(f"     Java: {java_cmd.get('audio_url')}")
                else:
                    logger.info("✅ 音频URL字段正常")
                
                # 文本内容对比
                if len(python_cmd.get('text', '')) > len(java_cmd.get('text', '')) * 2:
                    logger.warning("⚠️  Python生成的文本比Java的长很多")
                elif len(java_cmd.get('text', '')) > len(python_cmd.get('text', '')) * 2:
                    logger.warning("⚠️  Java生成的文本比Python的长很多")
                
            except:
                logger.error("   ❌ Java命令解析失败")
        
        elif python_commands and not java_commands:
            logger.error("❌ 关键问题: Java触发没有产生命令消息!")
            logger.error("   Python服务可能没有正确处理Java的请求")
        
        # 分析ACK和事件差异
        python_acks = [msg for msg in python_messages if msg['topic'].endswith('/ack')]
        java_acks = [msg for msg in java_messages if msg['topic'].endswith('/ack')]
        
        python_events = [msg for msg in python_messages if msg['topic'].endswith('/event')]
        java_events = [msg for msg in java_messages if msg['topic'].endswith('/event')]
        
        logger.info(f"\n📨 响应对比:")
        logger.info(f"   Python ACK数: {len(python_acks)} | Java ACK数: {len(java_acks)}")
        logger.info(f"   Python 事件数: {len(python_events)} | Java 事件数: {len(java_events)}")
        
        # 总结和建议
        logger.info(f"\n💡 问题分析总结:")
        
        if python_commands and java_commands:
            try:
                python_cmd = json.loads(python_commands[0]['payload'])
                java_cmd = json.loads(java_commands[0]['payload'])
                
                if python_cmd.get('audio_url') and not java_cmd.get('audio_url'):
                    logger.error("🚨 根本原因: Java触发时音频URL缺失!")
                    logger.error("🔧 修复建议:")
                    logger.error("   1. 检查Java调用的API参数")
                    logger.error("   2. 检查Python服务处理Java请求的代码路径")
                    logger.error("   3. 确认TTS音频生成在Java触发时是否被跳过")
                    logger.error("   4. 比较Java和Python测试的category参数")
                elif not python_cmd.get('audio_url') and not java_cmd.get('audio_url'):
                    logger.warning("⚠️  两种触发都没有audio_url，但Python有声音")
                    logger.warning("   可能原因:")
                    logger.warning("   1. 音频传输使用了其他机制")
                    logger.warning("   2. WebSocket连接方式不同")
                    logger.warning("   3. TTS处理逻辑有差异")
                else:
                    logger.info("✅ 音频URL字段看起来正常，需要更深入分析")
                    
            except:
                logger.error("❌ 无法解析命令内容")
        
        elif not java_commands:
            logger.error("🚨 根本原因: Java触发没有生成MQTT命令!")
            logger.error("🔧 修复建议:")
            logger.error("   1. 检查Java后端是否正确调用Python API")
            logger.error("   2. 检查Python服务是否正确处理Java的请求")
            logger.error("   3. 查看Python服务日志中的错误信息")

async def main():
    """主分析函数"""
    logger.info("🔍 Java vs Python 触发差异分析工具")
    logger.info("="*50)
    logger.info("🎯 目标:")
    logger.info("   找出为什么Python测试有声音，Java触发没声音")
    logger.info("="*50)
    
    analyzer = TriggerDifferenceAnalyzer()
    
    try:
        # 连接MQTT
        if not await analyzer.connect_mqtt():
            logger.error("❌ 无法建立MQTT连接")
            return False
        
        logger.info("✅ 开始差异分析...")
        
        # 1. 先测试Python脚本触发（作为参照组）
        python_success = await analyzer.test_python_script_trigger()
        
        if not python_success:
            logger.error("❌ Python测试失败，无法进行对比")
            return False
        
        logger.info("\n" + "="*50)
        
        # 2. 等待Java触发（问题组）
        java_success = await analyzer.wait_for_java_trigger(timeout=90)
        
        # 3. 分析差异
        analyzer.analyze_differences()
        
        return python_success and java_success
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  分析被中断")
        analyzer.analyze_differences()
        return False
    except Exception as e:
        logger.error(f"\n❌ 分析异常: {e}")
        return False
    finally:
        try:
            analyzer.client.loop_stop()
            analyzer.client.disconnect()
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(main())
    
    if success:
        print("\n✅ 差异分析完成")
    else:
        print("\n⚠️  分析未完全完成")
    
    sys.exit(0 if success else 1)

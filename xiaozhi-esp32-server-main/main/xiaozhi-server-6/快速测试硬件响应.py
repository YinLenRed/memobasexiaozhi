#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试硬件响应 - 专门测试当前Java触发的硬件反应问题
基于你提供的日志，Java确实在推送，需要验证硬件端响应
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
logger = logging.getLogger('快速测试')

class QuickHardwareTest:
    """快速硬件响应测试"""
    
    def __init__(self):
        self.device_id = "f0:9e:9e:04:8a:44"
        self.python_api = "http://47.98.51.180:8003"
        
        # MQTT配置
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.mqtt_username = "admin"
        self.mqtt_password = "Jyxd@2025"
        
        # MQTT客户端
        client_id = f"quick-test-{uuid.uuid4().hex[:6]}"
        try:
            self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1, client_id=client_id)
        except (TypeError, NameError):
            self.client = mqtt.Client(client_id)
        
        self.connected = False
        self.messages = []
        self.test_track_id = None
        
        # 设置MQTT回调
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.connected = True
            logger.info("✅ MQTT监控连接成功")
            
            # 订阅硬件相关的所有主题
            topics = [
                f"device/{self.device_id}/command",
                f"device/{self.device_id}/ack", 
                f"device/{self.device_id}/event",
                "device/+/command",  # 监控所有设备
                "device/+/ack",
                "device/+/event"
            ]
            
            for topic in topics:
                client.subscribe(topic)
                logger.info(f"📥 订阅监控: {topic}")
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
            
            self.messages.append(message_info)
            
            # 实时显示
            logger.info(f"📨 [{message_info['time_str']}] {topic}")
            
            try:
                data = json.loads(payload)
                if topic.endswith('/command'):
                    logger.info(f"   🎯 命令: {data.get('cmd')} | Track: {data.get('track_id')}")
                    logger.info(f"   💬 内容: {data.get('text', '')[:30]}...")
                elif topic.endswith('/ack'):
                    logger.info(f"   ✅ ACK: {data.get('evt')} | Track: {data.get('track_id')}")
                elif topic.endswith('/event'):
                    logger.info(f"   📢 事件: {data.get('evt')} | Track: {data.get('track_id')}")
            except:
                logger.info(f"   📄 原始: {payload[:50]}...")
                
        except Exception as e:
            logger.error(f"❌ 处理消息失败: {e}")
    
    async def connect_and_monitor(self):
        """连接并开始监控"""
        logger.info("🔗 连接MQTT监控...")
        
        try:
            self.client.connect_async(self.mqtt_host, self.mqtt_port, 60)
            self.client.loop_start()
            
            # 等待连接
            for i in range(10):
                if self.connected:
                    break
                await asyncio.sleep(1)
            
            if not self.connected:
                logger.error("❌ MQTT连接失败")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ 连接异常: {e}")
            return False
    
    async def trigger_test_greeting(self):
        """触发一次测试主动问候"""
        logger.info("🚀 触发测试主动问候...")
        
        test_payload = {
            "device_id": self.device_id,
            "initial_content": f"硬件响应测试 {datetime.now().strftime('%H:%M:%S')}",
            "category": "system_reminder"  # 使用正确的类别
        }
        
        try:
            response = requests.post(
                f"{self.python_api}/xiaozhi/greeting/send",
                json=test_payload,
                timeout=10
            )
            
            logger.info(f"📤 API响应: {response.status_code}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                self.test_track_id = result.get('track_id')
                logger.info(f"✅ 触发成功! Track ID: {self.test_track_id}")
                return True
            else:
                logger.error(f"❌ 触发失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 触发异常: {e}")
            return False
    
    async def analyze_flow(self, duration=30):
        """分析消息流"""
        logger.info(f"⏳ 开始监控硬件响应 ({duration}秒)...")
        
        start_time = time.time()
        self.messages.clear()
        
        # 先触发一次测试
        success = await self.trigger_test_greeting()
        if not success:
            logger.error("❌ 无法触发测试，请检查Python API服务")
            return
        
        # 监控指定时间
        while time.time() - start_time < duration:
            await asyncio.sleep(2)
            
            # 显示当前状态
            current_time = time.time() - start_time
            if int(current_time) % 10 == 0:  # 每10秒显示一次
                logger.info(f"⏱️  监控中... {int(current_time)}/{duration}秒 | 收到消息: {len(self.messages)}")
        
        # 分析结果
        await self.analyze_results()
    
    async def analyze_results(self):
        """分析测试结果"""
        logger.info("\n" + "="*60)
        logger.info("📊 硬件响应分析结果")
        logger.info("="*60)
        
        # 统计消息
        total = len(self.messages)
        commands = [m for m in self.messages if m['topic'].endswith('/command') and self.device_id in m['topic']]
        acks = [m for m in self.messages if m['topic'].endswith('/ack') and self.device_id in m['topic']]
        events = [m for m in self.messages if m['topic'].endswith('/event') and self.device_id in m['topic']]
        
        logger.info(f"📈 消息统计:")
        logger.info(f"   总消息数: {total}")
        logger.info(f"   发给硬件的命令: {len(commands)}")
        logger.info(f"   硬件的ACK响应: {len(acks)}")
        logger.info(f"   硬件的事件上报: {len(events)}")
        
        # 详细分析
        logger.info(f"\n🔍 详细分析:")
        
        if len(commands) == 0:
            logger.error("❌ 硬件没有收到任何命令!")
            logger.error("   问题可能在于:")
            logger.error("   1. Python服务没有正确处理API请求")
            logger.error("   2. MQTT发布失败")
            logger.error("   3. 设备ID不匹配")
            
        elif len(acks) == 0:
            logger.error("❌ 硬件收到命令但没有ACK响应!")
            logger.error("   这就是无反应的主要原因!")
            logger.error("   硬件问题可能包括:")
            logger.error("   1. 设备离线或网络问题")
            logger.error("   2. 没有正确订阅command主题")
            logger.error("   3. 消息解析失败")
            logger.error("   4. ACK发送逻辑有问题")
            
            # 显示收到的命令详情
            if commands:
                logger.info(f"\n📝 硬件收到的命令详情:")
                for cmd in commands[-3:]:  # 显示最后3条
                    try:
                        data = json.loads(cmd['payload'])
                        logger.info(f"   [{cmd['time_str']}] 命令: {data.get('cmd')}")
                        logger.info(f"     Track ID: {data.get('track_id')}")
                        logger.info(f"     文本: {data.get('text', '')[:50]}...")
                    except:
                        pass
                        
        elif len(events) == 0:
            logger.warning("⚠️  有ACK但没有播放完成事件")
            logger.warning("   可能是音频播放环节的问题")
            
        else:
            logger.info("✅ 硬件响应完全正常!")
        
        # 跟踪特定测试
        if self.test_track_id:
            test_commands = [m for m in commands if self.test_track_id in m['payload']]
            test_acks = [m for m in acks if self.test_track_id in m['payload']]
            test_events = [m for m in events if self.test_track_id in m['payload']]
            
            logger.info(f"\n🎯 测试Track ID ({self.test_track_id[:10]}...) 追踪:")
            logger.info(f"   命令发送: {'✅' if test_commands else '❌'}")
            logger.info(f"   ACK响应: {'✅' if test_acks else '❌'}")
            logger.info(f"   事件上报: {'✅' if test_events else '❌'}")
        
        # 给出建议
        logger.info(f"\n💡 修复建议:")
        if len(commands) > 0 and len(acks) == 0:
            logger.info("   🔧 重点检查硬件设备:")
            logger.info("      1. 确认设备在线且网络正常")
            logger.info("      2. 检查MQTT客户端订阅代码")
            logger.info("      3. 检查命令解析和ACK发送逻辑")
            logger.info("      4. 确认设备ID完全匹配")
        elif len(commands) == 0:
            logger.info("   🔧 重点检查Python服务:")
            logger.info("      1. 查看Python服务日志")
            logger.info("      2. 检查MQTT客户端连接")
            logger.info("      3. 验证API处理逻辑")

async def main():
    """主测试函数"""
    logger.info("🚀 快速硬件响应测试工具")
    logger.info("="*50)
    logger.info("📋 测试目标:")
    logger.info("   设备ID: f0:9e:9e:04:8a:44")
    logger.info("   验证: Java触发 → Python处理 → 硬件响应")
    logger.info("="*50)
    
    tester = QuickHardwareTest()
    
    try:
        # 连接MQTT监控
        if not await tester.connect_and_monitor():
            logger.error("❌ 无法建立MQTT监控连接")
            return False
        
        logger.info("✅ 监控连接就绪")
        logger.info("💡 现在可以:")
        logger.info("   1. 我会自动触发一次测试")
        logger.info("   2. 你也可以手动通过Java触发")
        logger.info("   3. 观察硬件的实时响应")
        logger.info("-"*50)
        
        # 开始监控和分析
        await tester.analyze_flow(duration=45)  # 监控45秒
        
        # 根据结果判断
        commands = [m for m in tester.messages if m['topic'].endswith('/command') and tester.device_id in m['topic']]
        acks = [m for m in tester.messages if m['topic'].endswith('/ack') and tester.device_id in m['topic']]
        
        if len(commands) > 0 and len(acks) == 0:
            logger.info("\n🚨 确认问题: 硬件无反应!")
            return False
        elif len(commands) == 0:
            logger.info("\n🔍 问题在前端: 命令未到达硬件")
            return False
        else:
            logger.info("\n✅ 硬件响应正常!")
            return True
            
    except KeyboardInterrupt:
        logger.info("\n⏹️  测试被中断")
        return False
    except Exception as e:
        logger.error(f"\n❌ 测试异常: {e}")
        return False
    finally:
        try:
            tester.client.loop_stop()
            tester.client.disconnect()
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(main())
    
    if success:
        print("\n✅ 测试完成，系统正常工作")
    else:
        print("\n⚠️  发现问题，请根据上述分析进行修复")
    
    sys.exit(0 if success else 1)

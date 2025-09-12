#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硬件无反应专项检测工具
专门诊断Java触发但硬件设备无反应的问题
"""

import asyncio
import json
import logging
import time
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
logger = logging.getLogger('硬件检测')

class HardwareResponseChecker:
    """硬件响应专项检测器"""
    
    def __init__(self, device_id: str = "f0:9e:9e:04:8a:44"):
        self.device_id = device_id
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.mqtt_username = "admin"
        self.mqtt_password = "Jyxd@2025"
        
        # MQTT客户端
        client_id = f"hw-checker-{uuid.uuid4().hex[:6]}"
        try:
            self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1, client_id=client_id)
        except (TypeError, NameError):
            self.client = mqtt.Client(client_id)
        
        self.connected = False
        self.received_messages = []
        self.connection_event = asyncio.Event()
        
        # 设置MQTT回调
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.connected = True
            logger.info(f"✅ MQTT连接成功")
            
            # 订阅相关主题
            topics = [
                f"device/{self.device_id}/command",   # Python发给硬件的命令
                f"device/{self.device_id}/ack",       # 硬件的ACK响应
                f"device/{self.device_id}/event",     # 硬件的事件上报
                f"device/+/command",                  # 监听所有设备命令
                f"device/+/ack",                      # 监听所有设备响应
                f"device/+/event",                    # 监听所有设备事件
                "server/dev/report/event",            # Java发给Python的触发
            ]
            
            for topic in topics:
                result = client.subscribe(topic)
                logger.info(f"📥 订阅主题: {topic} -> {result}")
            
            self.connection_event.set()
        else:
            logger.error(f"❌ MQTT连接失败: {rc}")
            self.connection_event.set()
    
    def _on_message(self, client, userdata, msg):
        """消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            timestamp = time.time()
            
            message_info = {
                'timestamp': timestamp,
                'time_str': datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3],
                'topic': topic,
                'payload': payload,
                'qos': msg.qos,
                'retain': msg.retain
            }
            
            self.received_messages.append(message_info)
            
            # 实时显示收到的消息
            logger.info(f"📨 [{message_info['time_str']}] {topic}")
            
            # 解析并显示消息内容
            try:
                payload_json = json.loads(payload)
                
                if topic.endswith('/command'):
                    logger.info(f"   🎯 命令类型: {payload_json.get('cmd')}")
                    logger.info(f"   🏷️  Track ID: {payload_json.get('track_id')}")
                    logger.info(f"   💬 文本内容: {payload_json.get('text', '')[:50]}...")
                    
                elif topic.endswith('/ack'):
                    logger.info(f"   ✅ ACK事件: {payload_json.get('evt')}")
                    logger.info(f"   🏷️  Track ID: {payload_json.get('track_id')}")
                    
                elif topic.endswith('/event'):
                    logger.info(f"   📢 事件类型: {payload_json.get('evt')}")
                    logger.info(f"   🏷️  Track ID: {payload_json.get('track_id')}")
                    
                elif 'server/dev/report' in topic:
                    logger.info(f"   🚀 Java触发: {payload_json.get('title')}")
                    logger.info(f"   📱 目标设备: {payload_json.get('device_id')}")
                    
            except json.JSONDecodeError:
                logger.info(f"   📄 原始内容: {payload[:100]}...")
                
        except Exception as e:
            logger.error(f"❌ 处理消息异常: {e}")
    
    async def connect_mqtt(self) -> bool:
        """连接MQTT服务器"""
        try:
            logger.info(f"🔗 连接MQTT服务器: {self.mqtt_host}:{self.mqtt_port}")
            
            self.client.connect_async(self.mqtt_host, self.mqtt_port, 60)
            self.client.loop_start()
            
            # 等待连接完成
            try:
                await asyncio.wait_for(self.connection_event.wait(), timeout=10)
                return self.connected
            except asyncio.TimeoutError:
                logger.error("❌ MQTT连接超时")
                return False
                
        except Exception as e:
            logger.error(f"❌ MQTT连接异常: {e}")
            return False
    
    def send_test_command(self) -> str:
        """发送测试命令给硬件"""
        track_id = f"TEST_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        
        command = {
            "cmd": "SPEAK",
            "text": f"硬件响应测试 {datetime.now().strftime('%H:%M:%S')}",
            "track_id": track_id,
            "timestamp": datetime.now().isoformat(),
            "audio_url": "ws://47.98.51.180:8000/xiaozhi/v1/"
        }
        
        topic = f"device/{self.device_id}/command"
        message = json.dumps(command)
        
        result = self.client.publish(topic, message, qos=1)
        logger.info(f"📤 发送测试命令: {track_id}")
        logger.info(f"   主题: {topic}")
        logger.info(f"   发布结果: {result}")
        
        return track_id
    
    async def monitor_hardware_response(self, duration: int = 30):
        """监控硬件响应"""
        logger.info("=" * 60)
        logger.info("🎯 开始硬件响应专项监控")
        logger.info(f"📱 目标设备: {self.device_id}")
        logger.info(f"⏱️  监控时长: {duration}秒")
        logger.info("=" * 60)
        
        # 连接MQTT
        if not await self.connect_mqtt():
            logger.error("❌ 无法连接MQTT服务器，监控终止")
            return
        
        logger.info("✅ MQTT连接成功，开始监控...")
        logger.info("🔔 现在你可以:")
        logger.info("   1. 通过Java后端触发主动问候")
        logger.info("   2. 直接向硬件发送命令")
        logger.info("   3. 观察硬件的响应情况")
        logger.info("-" * 60)
        
        try:
            # 清空之前的消息
            self.received_messages.clear()
            
            # 发送一个测试命令
            logger.info("🧪 发送测试命令到硬件...")
            test_track_id = self.send_test_command()
            
            # 监控指定时间
            start_time = time.time()
            last_message_count = 0
            
            while time.time() - start_time < duration:
                current_count = len(self.received_messages)
                
                # 如果有新消息，显示统计
                if current_count > last_message_count:
                    logger.info(f"📊 消息统计更新: 已收到 {current_count} 条消息")
                    last_message_count = current_count
                
                await asyncio.sleep(2)
                
        except KeyboardInterrupt:
            logger.info("⏹️  监控被用户中断")
        
        finally:
            # 分析结果
            await self.analyze_results()
            
            # 清理连接
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except:
                pass
    
    async def analyze_results(self):
        """分析监控结果"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 硬件响应分析报告")
        logger.info("=" * 60)
        
        total_messages = len(self.received_messages)
        logger.info(f"总消息数: {total_messages}")
        
        if total_messages == 0:
            logger.error("❌ 完全没有收到任何MQTT消息!")
            logger.error("🔍 可能的问题:")
            logger.error("   1. MQTT服务器连接问题")
            logger.error("   2. 主题订阅问题")
            logger.error("   3. Python服务没有运行")
            logger.error("   4. Java后端没有正确触发")
            return
        
        # 分类统计消息
        command_msgs = [msg for msg in self.received_messages if msg['topic'].endswith('/command')]
        ack_msgs = [msg for msg in self.received_messages if msg['topic'].endswith('/ack')]
        event_msgs = [msg for msg in self.received_messages if msg['topic'].endswith('/event')]
        server_msgs = [msg for msg in self.received_messages if 'server/dev/report' in msg['topic']]
        
        logger.info(f"消息分类:")
        logger.info(f"  📤 命令消息 (Python->硬件): {len(command_msgs)}")
        logger.info(f"  ✅ ACK响应 (硬件->Python): {len(ack_msgs)}")
        logger.info(f"  📢 事件上报 (硬件->Python): {len(event_msgs)}")
        logger.info(f"  🚀 服务器触发 (Java->Python): {len(server_msgs)}")
        
        # 检查目标设备的消息
        target_command_msgs = [msg for msg in command_msgs if self.device_id in msg['topic']]
        target_ack_msgs = [msg for msg in ack_msgs if self.device_id in msg['topic']]
        target_event_msgs = [msg for msg in event_msgs if self.device_id in msg['topic']]
        
        logger.info(f"\n🎯 目标设备 ({self.device_id}) 专项分析:")
        logger.info(f"  收到的命令: {len(target_command_msgs)}")
        logger.info(f"  发出的ACK: {len(target_ack_msgs)}")
        logger.info(f"  发出的事件: {len(target_event_msgs)}")
        
        # 诊断问题
        logger.info(f"\n🔍 问题诊断:")
        
        if len(target_command_msgs) == 0:
            logger.warning("⚠️  硬件没有收到任何命令消息")
            logger.warning("   可能原因:")
            logger.warning("   1. Python服务没有正确处理Java的触发")
            logger.warning("   2. 设备ID不匹配")
            logger.warning("   3. MQTT发布失败")
            
        elif len(target_ack_msgs) == 0:
            logger.error("❌ 硬件收到命令但没有发送ACK响应")
            logger.error("   这是硬件无反应的主要原因!")
            logger.error("   建议检查:")
            logger.error("   1. 硬件设备是否在线")
            logger.error("   2. 硬件是否正确订阅了command主题")
            logger.error("   3. 硬件是否能正确解析命令格式")
            logger.error("   4. 硬件是否能正确发送ACK到ack主题")
            
        elif len(target_event_msgs) == 0:
            logger.warning("⚠️  硬件发送了ACK但没有事件上报")
            logger.warning("   可能原因:")
            logger.warning("   1. 音频播放过程有问题")
            logger.warning("   2. WebSocket连接问题")
            logger.warning("   3. 硬件播放完成后没有上报事件")
            
        else:
            logger.info("✅ 硬件响应基本正常")
        
        # 显示最近的消息详情
        logger.info(f"\n📝 最近的消息详情:")
        for msg in self.received_messages[-5:]:
            logger.info(f"  [{msg['time_str']}] {msg['topic']}")
            try:
                payload = json.loads(msg['payload'])
                if 'track_id' in payload:
                    logger.info(f"    Track ID: {payload['track_id']}")
                if 'cmd' in payload:
                    logger.info(f"    Command: {payload['cmd']}")
                if 'evt' in payload:
                    logger.info(f"    Event: {payload['evt']}")
            except:
                pass

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='硬件无反应专项检测工具')
    parser.add_argument('--device-id', default='f0:9e:9e:04:8a:44', help='目标设备ID')
    parser.add_argument('--duration', type=int, default=30, help='监控时长(秒)')
    
    args = parser.parse_args()
    
    checker = HardwareResponseChecker(args.device_id)
    
    logger.info("🔍 硬件无反应专项检测工具 v1.0")
    logger.info("=" * 50)
    
    try:
        await checker.monitor_hardware_response(args.duration)
        
        # 根据结果给出建议
        command_count = len([msg for msg in checker.received_messages if msg['topic'].endswith('/command') and args.device_id in msg['topic']])
        ack_count = len([msg for msg in checker.received_messages if msg['topic'].endswith('/ack') and args.device_id in msg['topic']])
        
        if command_count > 0 and ack_count == 0:
            logger.info("\n🚨 检测结果: 硬件无反应问题确认!")
            logger.info("💡 建议立即检查:")
            logger.info("   1. 硬件设备的网络连接")
            logger.info("   2. 硬件设备的MQTT订阅代码")
            logger.info("   3. 硬件设备的电源状态")
            return False
            
        elif command_count == 0:
            logger.info("\n🔍 检测结果: 问题在于命令下发环节")
            logger.info("💡 建议检查Python服务和Java触发逻辑")
            return False
            
        else:
            logger.info("\n✅ 硬件响应正常!")
            return True
            
    except KeyboardInterrupt:
        logger.info("\n⏹️  检测被用户中断")
        return False
    except Exception as e:
        logger.error(f"\n❌ 检测异常: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频问题专项检查工具
检查硬件响应正常但没有声音的问题
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
import websockets

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('音频检查')

class AudioProblemChecker:
    """音频问题检查器"""
    
    def __init__(self):
        self.device_id = "f0:9e:9e:04:8a:44"
        self.python_api = "http://47.98.51.180:8003"
        self.websocket_url = "ws://47.98.51.180:8000/xiaozhi/v1/"
        
        # MQTT配置
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.mqtt_username = "admin"
        self.mqtt_password = "Jyxd@2025"
        
        # MQTT客户端
        client_id = f"audio-check-{uuid.uuid4().hex[:6]}"
        try:
            self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1, client_id=client_id)
        except (TypeError, NameError):
            self.client = mqtt.Client(client_id)
        
        self.connected = False
        self.messages = []
        self.websocket_data = []
        
        # 设置MQTT回调
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.connected = True
            logger.info("✅ MQTT连接成功")
            
            # 订阅所有相关主题
            topics = [
                f"device/{self.device_id}/command",
                f"device/{self.device_id}/ack", 
                f"device/{self.device_id}/event"
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
            
            self.messages.append(message_info)
            
            # 分析消息内容
            try:
                data = json.loads(payload)
                if topic.endswith('/command'):
                    logger.info(f"📤 [{message_info['time_str']}] 命令发送")
                    logger.info(f"   Track ID: {data.get('track_id')}")
                    logger.info(f"   音频URL: {data.get('audio_url')}")
                    logger.info(f"   文本内容: {data.get('text', '')[:50]}...")
                    
                elif topic.endswith('/ack'):
                    logger.info(f"✅ [{message_info['time_str']}] 硬件ACK")
                    logger.info(f"   事件: {data.get('evt')}")
                    logger.info(f"   Track ID: {data.get('track_id')}")
                    
                elif topic.endswith('/event'):
                    logger.info(f"📢 [{message_info['time_str']}] 硬件事件")
                    logger.info(f"   事件: {data.get('evt')}")
                    logger.info(f"   Track ID: {data.get('track_id')}")
                    
            except json.JSONDecodeError:
                logger.info(f"📄 原始消息: {payload[:100]}...")
                
        except Exception as e:
            logger.error(f"❌ 处理消息异常: {e}")
    
    async def connect_mqtt(self):
        """连接MQTT"""
        try:
            logger.info("🔗 连接MQTT服务器...")
            self.client.connect_async(self.mqtt_host, self.mqtt_port, 60)
            self.client.loop_start()
            
            # 等待连接
            for i in range(10):
                if self.connected:
                    return True
                await asyncio.sleep(1)
            
            return False
            
        except Exception as e:
            logger.error(f"❌ MQTT连接异常: {e}")
            return False
    
    async def check_websocket_audio_flow(self, track_id: str):
        """检查WebSocket音频流"""
        logger.info("🎵 检查WebSocket音频传输...")
        
        try:
            websocket_url = f"{self.websocket_url}{self.device_id}"
            logger.info(f"🔗 连接WebSocket: {websocket_url}")
            
            async with websockets.connect(websocket_url) as websocket:
                logger.info("✅ WebSocket连接成功")
                
                # 监听音频数据
                start_time = time.time()
                audio_data_received = 0
                
                try:
                    while time.time() - start_time < 15:  # 监听15秒
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1)
                            
                            if isinstance(message, bytes):
                                audio_data_received += len(message)
                                logger.info(f"🎵 收到音频数据: {len(message)} 字节 (总计: {audio_data_received})")
                            else:
                                logger.info(f"📝 收到文本消息: {message[:100]}...")
                                
                        except asyncio.TimeoutError:
                            continue
                            
                except websockets.exceptions.ConnectionClosed:
                    logger.info("🔌 WebSocket连接关闭")
                
                logger.info(f"📊 音频数据统计:")
                logger.info(f"   总接收: {audio_data_received} 字节")
                
                if audio_data_received > 0:
                    logger.info("✅ WebSocket音频传输正常")
                    return True
                else:
                    logger.warning("⚠️  没有收到音频数据")
                    return False
                
        except Exception as e:
            logger.error(f"❌ WebSocket检查失败: {e}")
            return False
    
    async def trigger_and_analyze(self):
        """触发测试并分析完整音频链路"""
        logger.info("🎯 开始音频问题专项检查")
        logger.info("="*60)
        
        # 清空消息记录
        self.messages.clear()
        
        # 触发主动问候
        test_payload = {
            "device_id": self.device_id,
            "initial_content": f"音频测试 {datetime.now().strftime('%H:%M:%S')}",
            "category": "system_reminder"
        }
        
        logger.info("🚀 发送音频测试请求...")
        
        try:
            response = requests.post(
                f"{self.python_api}/xiaozhi/greeting/send",
                json=test_payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                track_id = result.get('track_id')
                logger.info(f"✅ 请求成功! Track ID: {track_id}")
                
                # 等待命令消息
                logger.info("⏳ 等待MQTT命令...")
                await asyncio.sleep(3)
                
                # 查找命令消息
                command_msgs = [m for m in self.messages if m['topic'].endswith('/command')]
                if command_msgs:
                    logger.info("✅ 检测到命令发送")
                    
                    # 检查WebSocket音频流
                    audio_ok = await self.check_websocket_audio_flow(track_id)
                    
                    # 等待硬件响应
                    logger.info("⏳ 等待硬件完整响应...")
                    await asyncio.sleep(10)
                    
                    return self.analyze_audio_chain()
                    
                else:
                    logger.error("❌ 没有检测到命令发送")
                    return False
                    
            else:
                logger.error(f"❌ 请求失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 请求异常: {e}")
            return False
    
    def analyze_audio_chain(self):
        """分析音频链路"""
        logger.info("\n" + "="*60)
        logger.info("📊 音频链路分析报告")
        logger.info("="*60)
        
        # 分类消息
        commands = [m for m in self.messages if m['topic'].endswith('/command')]
        acks = [m for m in self.messages if m['topic'].endswith('/ack')]
        events = [m for m in self.messages if m['topic'].endswith('/event')]
        
        logger.info(f"🔍 MQTT消息流分析:")
        logger.info(f"   命令消息: {len(commands)}")
        logger.info(f"   ACK响应: {len(acks)}")
        logger.info(f"   完成事件: {len(events)}")
        
        # 检查每个环节
        problems = []
        
        if len(commands) == 0:
            problems.append("❌ Python没有发送命令到硬件")
        else:
            logger.info("✅ 1. Python → MQTT → 硬件 命令传输正常")
        
        if len(acks) == 0:
            problems.append("❌ 硬件没有确认收到命令")
        else:
            logger.info("✅ 2. 硬件 → MQTT → Python ACK确认正常")
        
        if len(events) == 0:
            problems.append("❌ 硬件没有上报播放完成事件")
        else:
            logger.info("✅ 3. 硬件播放完成上报正常")
        
        # 分析具体问题
        logger.info(f"\n🔍 可能的音频问题:")
        
        if len(commands) > 0 and len(acks) > 0 and len(events) > 0:
            logger.warning("⚠️  MQTT流程完全正常，但没有听到声音")
            logger.warning("   可能的硬件音频问题:")
            logger.warning("   1. 🔇 硬件音量设置为0或很低")
            logger.warning("   2. 🔌 扬声器硬件故障或未连接")
            logger.warning("   3. 🎵 音频解码或播放模块问题")
            logger.warning("   4. 📡 WebSocket音频数据传输问题")
            logger.warning("   5. 🔋 硬件电源不足影响音频输出")
            
            # 提供调试建议
            logger.info(f"\n🛠️  硬件调试建议:")
            logger.info("   1. 检查硬件串口输出，查看是否有音频相关错误")
            logger.info("   2. 确认硬件音量设置和扬声器连接")
            logger.info("   3. 测试硬件是否能播放本地存储的测试音频")
            logger.info("   4. 检查WebSocket音频数据接收和解码逻辑")
            logger.info("   5. 确认硬件工作电压和电源稳定性")
            
            return False  # 有声音问题
        else:
            for problem in problems:
                logger.error(problem)
            return len(problems) == 0

async def main():
    """主检查函数"""
    logger.info("🎵 音频问题专项检查工具")
    logger.info("="*50)
    logger.info("🎯 检查目标:")
    logger.info("   硬件MQTT响应正常但没有声音输出的问题")
    logger.info("="*50)
    
    checker = AudioProblemChecker()
    
    try:
        # 连接MQTT
        if not await checker.connect_mqtt():
            logger.error("❌ 无法连接MQTT")
            return False
        
        logger.info("✅ MQTT连接就绪")
        logger.info("🎵 开始音频链路检查...")
        
        # 触发测试并分析
        result = await checker.trigger_and_analyze()
        
        if result:
            logger.info("\n✅ 音频链路检查完成，系统正常")
        else:
            logger.info("\n⚠️  发现音频问题，请参考上述建议进行排查")
        
        return result
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  检查被中断")
        return False
    except Exception as e:
        logger.error(f"\n❌ 检查异常: {e}")
        return False
    finally:
        try:
            checker.client.loop_stop()
            checker.client.disconnect()
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(main())
    
    if success:
        print("\n✅ 音频系统正常")
    else:
        print("\n🔇 可能存在音频输出问题")
    
    sys.exit(0 if success else 1)

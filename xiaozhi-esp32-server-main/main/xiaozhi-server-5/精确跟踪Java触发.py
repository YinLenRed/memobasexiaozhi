#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确跟踪Java触发的主动问候
帮助确认硬件播放的音频是否来自Java的触发
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
logger = logging.getLogger('精确跟踪')

class JavaTriggerTracker:
    """Java触发精确跟踪器"""
    
    def __init__(self):
        self.device_id = "f0:9e:9e:04:8a:44"
        self.python_api = "http://47.98.51.180:8003"
        
        # MQTT配置
        self.mqtt_host = "47.97.185.142"
        self.mqtt_port = 1883
        self.mqtt_username = "admin"
        self.mqtt_password = "Jyxd@2025"
        
        # MQTT客户端
        client_id = f"java-tracker-{uuid.uuid4().hex[:6]}"
        try:
            self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1, client_id=client_id)
        except (TypeError, NameError):
            self.client = mqtt.Client(client_id)
        
        self.connected = False
        self.tracked_triggers = {}  # 跟踪每次Java触发
        self.all_messages = []
        
        # 设置MQTT回调
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.connected = True
            logger.info("✅ MQTT跟踪连接成功")
            
            # 订阅所有相关主题
            topics = [
                f"device/{self.device_id}/command",
                f"device/{self.device_id}/ack", 
                f"device/{self.device_id}/event",
                "server/dev/report/event",  # Java发给Python的触发事件
                "device/+/command",  # 监控所有设备
            ]
            
            for topic in topics:
                client.subscribe(topic)
                logger.info(f"📥 订阅跟踪: {topic}")
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
            
            self.all_messages.append(message_info)
            
            # 特别关注的消息类型
            try:
                data = json.loads(payload)
                
                if 'server/dev/report' in topic:
                    logger.info(f"🚀 [{message_info['time_str']}] Java触发事件!")
                    logger.info(f"   标题: {data.get('title', 'N/A')}")
                    logger.info(f"   设备: {data.get('device_id', 'N/A')}")
                    logger.info(f"   内容: {str(data)[:100]}...")
                
                elif topic.endswith('/command') and self.device_id in topic:
                    track_id = data.get('track_id')
                    text_content = data.get('text', '')
                    
                    logger.info(f"📤 [{message_info['time_str']}] 命令发送到硬件")
                    logger.info(f"   🎯 Track ID: {track_id}")
                    logger.info(f"   💬 内容: {text_content[:50]}...")
                    logger.info(f"   🔊 音频URL: {data.get('audio_url', 'None')}")
                    
                    # 记录这次跟踪
                    if track_id:
                        self.tracked_triggers[track_id] = {
                            'command_time': timestamp,
                            'command_text': text_content,
                            'ack_time': None,
                            'done_time': None,
                            'audio_url': data.get('audio_url')
                        }
                
                elif topic.endswith('/ack') and self.device_id in topic:
                    track_id = data.get('track_id')
                    event_type = data.get('evt')
                    
                    logger.info(f"✅ [{message_info['time_str']}] 硬件ACK确认")
                    logger.info(f"   🎯 Track ID: {track_id}")
                    logger.info(f"   📨 事件: {event_type}")
                    
                    # 更新跟踪记录
                    if track_id in self.tracked_triggers:
                        self.tracked_triggers[track_id]['ack_time'] = timestamp
                
                elif topic.endswith('/event') and self.device_id in topic:
                    track_id = data.get('track_id')
                    event_type = data.get('evt')
                    
                    logger.info(f"📢 [{message_info['time_str']}] 硬件事件上报")
                    logger.info(f"   🎯 Track ID: {track_id}")
                    logger.info(f"   📨 事件: {event_type}")
                    
                    # 更新跟踪记录
                    if track_id in self.tracked_triggers:
                        self.tracked_triggers[track_id]['done_time'] = timestamp
                        
                        # 计算整个流程时间
                        trigger_info = self.tracked_triggers[track_id]
                        total_time = timestamp - trigger_info['command_time']
                        
                        logger.info(f"⏱️  完整流程耗时: {total_time:.2f}秒")
                        
                        if event_type == 'EVT_SPEAK_DONE':
                            logger.info(f"🎉 Track {track_id[:10]}... 播放完成！")
                            logger.info(f"   📝 内容: {trigger_info['command_text'][:30]}...")
                            logger.info(f"   ⏰ 总时长: {total_time:.1f}秒")
                
            except json.JSONDecodeError:
                logger.info(f"📄 [{message_info['time_str']}] {topic}: {payload[:50]}...")
                
        except Exception as e:
            logger.error(f"❌ 处理消息异常: {e}")
    
    async def connect_mqtt(self):
        """连接MQTT"""
        try:
            logger.info("🔗 建立MQTT跟踪连接...")
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
    
    async def manual_trigger_test(self):
        """手动触发一次测试，用于对比"""
        logger.info("🧪 手动触发测试（用于对比）...")
        
        # 生成一个特殊的测试内容，方便识别
        test_content = f"手动测试触发 - {datetime.now().strftime('%H时%M分%S秒')}"
        
        test_payload = {
            "device_id": self.device_id,
            "initial_content": test_content,
            "category": "system_reminder"
        }
        
        logger.info(f"📤 发送测试请求...")
        logger.info(f"   🎯 特殊标识: {test_content}")
        
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.python_api}/xiaozhi/greeting/send",
                json=test_payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                track_id = result.get('track_id')
                
                logger.info(f"✅ 手动测试触发成功!")
                logger.info(f"   🎯 Track ID: {track_id}")
                logger.info(f"   💬 请注意听硬件是否播放: '{test_content}'")
                
                return track_id
            else:
                logger.error(f"❌ 手动测试失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 手动测试异常: {e}")
            return None
    
    async def start_tracking(self, duration=120):
        """开始跟踪Java触发"""
        logger.info("🎯 开始精确跟踪Java触发")
        logger.info("="*60)
        logger.info(f"📱 目标设备: {self.device_id}")
        logger.info(f"⏱️  跟踪时长: {duration}秒")
        logger.info("="*60)
        
        # 清空记录
        self.tracked_triggers.clear()
        self.all_messages.clear()
        
        logger.info("✅ 跟踪已启动")
        logger.info("💡 现在可以:")
        logger.info("   1. 通过Java后端触发主动问候")
        logger.info("   2. 观察硬件的音频播放")
        logger.info("   3. 我会自动关联触发和播放")
        logger.info("-"*60)
        
        # 10秒后发送一次手动测试
        await asyncio.sleep(10)
        test_track_id = await self.manual_trigger_test()
        
        # 继续监控
        start_time = time.time()
        last_summary_time = time.time()
        
        while time.time() - start_time < duration:
            await asyncio.sleep(2)
            
            # 每30秒显示一次摘要
            if time.time() - last_summary_time >= 30:
                self.show_tracking_summary()
                last_summary_time = time.time()
        
        # 最终分析
        self.final_analysis()
    
    def show_tracking_summary(self):
        """显示跟踪摘要"""
        logger.info(f"\n📊 跟踪摘要 ({len(self.tracked_triggers)} 个触发):")
        
        for track_id, info in list(self.tracked_triggers.items())[-3:]:  # 显示最近3个
            status = "⏳ 进行中"
            if info['done_time']:
                total_time = info['done_time'] - info['command_time']
                status = f"✅ 完成 ({total_time:.1f}s)"
            elif info['ack_time']:
                status = "🔄 已ACK"
            
            logger.info(f"   {track_id[:10]}... {status}")
            logger.info(f"      💬 {info['command_text'][:25]}...")
    
    def final_analysis(self):
        """最终分析"""
        logger.info("\n" + "="*60)
        logger.info("📊 Java触发跟踪分析报告")
        logger.info("="*60)
        
        total_triggers = len(self.tracked_triggers)
        completed_triggers = len([t for t in self.tracked_triggers.values() if t['done_time']])
        
        logger.info(f"📈 统计数据:")
        logger.info(f"   总触发次数: {total_triggers}")
        logger.info(f"   完成播放次数: {completed_triggers}")
        logger.info(f"   完成率: {completed_triggers/total_triggers*100:.1f}%" if total_triggers > 0 else "   完成率: N/A")
        
        if total_triggers == 0:
            logger.warning("⚠️  监控期间没有检测到任何Java触发!")
            logger.warning("   可能原因:")
            logger.warning("   1. Java后端没有触发主动问候")
            logger.warning("   2. Python服务没有处理Java请求")
            logger.warning("   3. MQTT消息订阅有问题")
            return
        
        logger.info(f"\n🔍 详细分析:")
        
        for track_id, info in self.tracked_triggers.items():
            logger.info(f"\n🎯 Track ID: {track_id}")
            logger.info(f"   💬 内容: {info['command_text'][:50]}...")
            logger.info(f"   🕐 命令时间: {datetime.fromtimestamp(info['command_time']).strftime('%H:%M:%S')}")
            
            if info['ack_time']:
                ack_delay = info['ack_time'] - info['command_time']
                logger.info(f"   ✅ ACK时间: {datetime.fromtimestamp(info['ack_time']).strftime('%H:%M:%S')} (+{ack_delay:.2f}s)")
            else:
                logger.info(f"   ❌ 无ACK响应")
            
            if info['done_time']:
                total_time = info['done_time'] - info['command_time']
                logger.info(f"   🎉 完成时间: {datetime.fromtimestamp(info['done_time']).strftime('%H:%M:%S')} (总计{total_time:.1f}s)")
                logger.info(f"   🔊 硬件应该在 {datetime.fromtimestamp(info['command_time']).strftime('%H:%M:%S')} 开始播放")
            else:
                logger.info(f"   ⏳ 未完成")
        
        # 关键提示
        logger.info(f"\n💡 重要提示:")
        logger.info("   🎵 如果硬件有声音但你感觉不是'主动问候'：")
        logger.info("   1. 请对比上面的时间，确认声音是否在这些时间点播放")
        logger.info("   2. 请注意听声音内容是否包含上面显示的文字")
        logger.info("   3. 可能硬件音量很小，或者播放速度很快")
        logger.info("   4. 可能存在多个音频源，需要区分哪个是主动问候")

async def main():
    """主跟踪函数"""
    logger.info("🎯 Java触发精确跟踪工具")
    logger.info("="*50)
    logger.info("🎯 目标:")
    logger.info("   精确跟踪Java触发，确认硬件音频是否来自Java")
    logger.info("="*50)
    
    tracker = JavaTriggerTracker()
    
    try:
        # 连接MQTT
        if not await tracker.connect_mqtt():
            logger.error("❌ 无法建立MQTT跟踪连接")
            return False
        
        # 开始跟踪
        await tracker.start_tracking(duration=120)  # 跟踪2分钟
        
        return True
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  跟踪被中断")
        logger.info("📊 显示当前跟踪结果...")
        tracker.final_analysis()
        return False
    except Exception as e:
        logger.error(f"\n❌ 跟踪异常: {e}")
        return False
    finally:
        try:
            tracker.client.loop_stop()
            tracker.client.disconnect()
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(main())
    
    if success:
        print("\n✅ 跟踪完成")
    else:
        print("\n⚠️  跟踪中断或异常")
    
    sys.exit(0 if success else 1)

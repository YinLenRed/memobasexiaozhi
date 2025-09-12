#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小智硬件设备模拟器
模拟ESP32设备的MQTT和WebSocket通信行为，用于系统测试
"""

import asyncio
import json
import logging
import time
import websockets
import paho.mqtt.client as mqtt
try:
    from paho.mqtt.client import CallbackAPIVersion
except ImportError:
    # paho-mqtt 1.x版本没有CallbackAPIVersion
    pass
from datetime import datetime
from typing import Optional, Dict
import uuid
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('HardwareSimulator')

class HardwareSimulatorConfig:
    """硬件模拟器配置"""
    
    # MQTT配置
    MQTT_HOST = "47.97.185.142"
    MQTT_PORT = 1883
    MQTT_USERNAME = "admin"
    MQTT_PASSWORD = "Jyxd@2025"
    
    # WebSocket配置
    WEBSOCKET_URL = "ws://47.98.51.180:8000/xiaozhi/v1/"
    
    # 设备配置
    DEVICE_ID = "f0:9e:9e:04:8a:44"  # 模拟设备MAC地址
    CLIENT_ID = f"esp32-simulator-{uuid.uuid4().hex[:8]}"
    
    # 行为配置
    ACK_DELAY_MS = 50  # ACK响应延迟(毫秒)
    AUDIO_PLAY_DURATION = 3  # 模拟音频播放时长(秒)
    SIMULATE_AUDIO_PLAYBACK = True  # 是否模拟音频播放
    
    # 故障模拟
    SIMULATE_ACK_FAILURE_RATE = 0.0  # ACK失败率 (0.0-1.0)
    SIMULATE_AUDIO_FAILURE_RATE = 0.0  # 音频播放失败率
    SIMULATE_NETWORK_DELAY_MS = 0  # 网络延迟模拟(毫秒)

class HardwareSimulator:
    """硬件设备模拟器主类"""
    
    def __init__(self, config: HardwareSimulatorConfig = None):
        self.config = config or HardwareSimulatorConfig()
        
        # MQTT客户端 (兼容paho-mqtt 2.0+)
        try:
            # paho-mqtt 2.0+ 版本
            self.mqtt_client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1, client_id=self.config.CLIENT_ID)
        except (TypeError, NameError):
            # paho-mqtt 1.x 版本向后兼容
            self.mqtt_client = mqtt.Client(self.config.CLIENT_ID)
        self.mqtt_connected = False
        
        # WebSocket相关
        self.websocket_connection = None
        self.websocket_connected = False
        self.audio_playing = False
        
        # 状态跟踪
        self.current_track_id = None
        self.device_status = "idle"  # idle, receiving_command, playing_audio
        self.received_commands = []
        
        # 控制标志
        self.running = False
        self.websocket_task = None
        
    def setup_mqtt(self):
        """设置MQTT客户端"""
        self.mqtt_client.username_pw_set(
            self.config.MQTT_USERNAME, 
            self.config.MQTT_PASSWORD
        )
        
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        self.mqtt_client.on_message = self._on_mqtt_message
        
        logger.info(f"MQTT客户端设置完成: {self.config.CLIENT_ID}")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT连接回调"""
        if rc == 0:
            self.mqtt_connected = True
            logger.info(f"✅ MQTT连接成功: {self.config.MQTT_HOST}:{self.config.MQTT_PORT}")
            
            # 订阅命令主题
            command_topics = [
                f"device/{self.config.DEVICE_ID}/command",
                f"device/{self.config.DEVICE_ID}/cmd"  # 支持两种主题格式
            ]
            
            for topic in command_topics:
                result = client.subscribe(topic)
                logger.info(f"📥 订阅主题: {topic} (result: {result})")
                
        else:
            self.mqtt_connected = False
            logger.error(f"❌ MQTT连接失败，错误代码: {rc}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT断开回调"""
        self.mqtt_connected = False
        if rc != 0:
            logger.warning(f"⚠️  MQTT意外断开连接，错误代码: {rc}")
        else:
            logger.info("📴 MQTT正常断开连接")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT消息接收回调"""
        try:
            topic = msg.topic
            payload_str = msg.payload.decode('utf-8')
            
            logger.info(f"📨 收到MQTT消息:")
            logger.info(f"   主题: {topic}")
            logger.info(f"   内容: {payload_str}")
            
            # 解析JSON消息
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON解析失败: {e}")
                return
            
            # 处理不同类型的命令
            if payload.get("cmd") == "SPEAK":
                asyncio.run_coroutine_threadsafe(
                    self._handle_speak_command(payload),
                    asyncio.get_event_loop()
                )
            else:
                logger.warning(f"⚠️  未知命令类型: {payload.get('cmd')}")
                
        except Exception as e:
            logger.error(f"❌ MQTT消息处理异常: {e}")
    
    async def _handle_speak_command(self, command: Dict):
        """处理SPEAK命令"""
        try:
            track_id = command.get("track_id", "unknown")
            text = command.get("text", "")
            audio_url = command.get("audio_url", "")
            
            logger.info(f"🔊 处理SPEAK命令:")
            logger.info(f"   Track ID: {track_id}")
            logger.info(f"   文本: {text}")
            logger.info(f"   音频URL: {audio_url}")
            
            self.current_track_id = track_id
            self.device_status = "receiving_command"
            
            # 记录接收到的命令
            self.received_commands.append({
                'timestamp': time.time(),
                'command': command
            })
            
            # 模拟网络延迟
            if self.config.SIMULATE_NETWORK_DELAY_MS > 0:
                await asyncio.sleep(self.config.SIMULATE_NETWORK_DELAY_MS / 1000)
            
            # 模拟ACK响应延迟
            if self.config.ACK_DELAY_MS > 0:
                await asyncio.sleep(self.config.ACK_DELAY_MS / 1000)
            
            # 发送ACK确认
            await self._send_ack_confirmation(track_id)
            
            # 如果启用音频播放模拟，处理音频
            if self.config.SIMULATE_AUDIO_PLAYBACK:
                await self._simulate_audio_playback(track_id, audio_url, text)
            
        except Exception as e:
            logger.error(f"❌ SPEAK命令处理异常: {e}")
            # 发送错误事件
            await self._send_error_event(track_id, str(e))
    
    async def _send_ack_confirmation(self, track_id: str):
        """发送ACK确认消息"""
        try:
            # 模拟ACK失败
            if self.config.SIMULATE_ACK_FAILURE_RATE > 0:
                import random
                if random.random() < self.config.SIMULATE_ACK_FAILURE_RATE:
                    logger.warning(f"🎭 模拟ACK失败: {track_id}")
                    return
            
            ack_topic = f"device/{self.config.DEVICE_ID}/ack"
            ack_payload = {
                "evt": "CMD_RECEIVED",
                "track_id": track_id,
                "timestamp": datetime.now().isoformat(),
                "device_id": self.config.DEVICE_ID,
                "client_id": self.config.CLIENT_ID
            }
            
            ack_message = json.dumps(ack_payload)
            result = self.mqtt_client.publish(ack_topic, ack_message)
            
            logger.info(f"✅ 发送ACK确认:")
            logger.info(f"   主题: {ack_topic}")
            logger.info(f"   内容: {ack_message}")
            logger.info(f"   结果: {result}")
            
        except Exception as e:
            logger.error(f"❌ ACK确认发送异常: {e}")
    
    async def _simulate_audio_playback(self, track_id: str, audio_url: str, text: str):
        """模拟音频播放过程"""
        try:
            self.device_status = "playing_audio"
            self.audio_playing = True
            
            logger.info(f"🎵 开始模拟音频播放:")
            logger.info(f"   Track ID: {track_id}")
            logger.info(f"   文本: {text}")
            logger.info(f"   音频URL: {audio_url}")
            
            # 如果提供了WebSocket URL，尝试连接接收音频
            if audio_url and audio_url.startswith("ws"):
                await self._connect_and_receive_audio(audio_url, track_id)
            
            # 模拟播放时长
            play_duration = self.config.AUDIO_PLAY_DURATION
            logger.info(f"⏱️  模拟播放时长: {play_duration}秒")
            
            # 分段模拟播放进度
            steps = 10
            step_duration = play_duration / steps
            
            for i in range(steps):
                await asyncio.sleep(step_duration)
                progress = (i + 1) / steps * 100
                logger.info(f"🎵 播放进度: {progress:.0f}%")
            
            # 模拟音频播放失败
            if self.config.SIMULATE_AUDIO_FAILURE_RATE > 0:
                import random
                if random.random() < self.config.SIMULATE_AUDIO_FAILURE_RATE:
                    logger.warning(f"🎭 模拟播放失败: {track_id}")
                    await self._send_error_event(track_id, "模拟播放失败")
                    return
            
            # 播放完成
            self.audio_playing = False
            self.device_status = "idle"
            
            logger.info(f"✅ 音频播放完成: {track_id}")
            
            # 发送播放完成事件
            await self._send_playback_complete_event(track_id)
            
        except Exception as e:
            logger.error(f"❌ 音频播放模拟异常: {e}")
            self.audio_playing = False
            self.device_status = "idle"
            await self._send_error_event(track_id, str(e))
    
    async def _connect_and_receive_audio(self, audio_url: str, track_id: str):
        """连接WebSocket接收音频数据"""
        try:
            logger.info(f"🌐 尝试连接WebSocket: {audio_url}")
            
            # 构建WebSocket连接头
            headers = {
                "Device-ID": self.config.DEVICE_ID,
                "Client-ID": self.config.CLIENT_ID,
                "Track-ID": track_id
            }
            
            async with websockets.connect(audio_url, extra_headers=headers) as websocket:
                logger.info("✅ WebSocket连接成功")
                
                # 发送hello消息
                hello_msg = json.dumps({
                    "type": "hello",
                    "device_id": self.config.DEVICE_ID,
                    "track_id": track_id
                })
                await websocket.send(hello_msg)
                logger.info(f"📤 发送hello消息: {hello_msg}")
                
                # 接收音频数据
                audio_chunks_received = 0
                total_audio_size = 0
                
                try:
                    while self.audio_playing:
                        # 设置接收超时
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        
                        if isinstance(message, bytes):
                            # 二进制音频数据
                            audio_chunks_received += 1
                            total_audio_size += len(message)
                            logger.info(f"🎵 接收音频数据块 #{audio_chunks_received}, 大小: {len(message)} 字节")
                            
                        else:
                            # 文本消息
                            try:
                                text_msg = json.loads(message)
                                logger.info(f"📥 接收WebSocket文本消息: {text_msg}")
                            except json.JSONDecodeError:
                                logger.info(f"📥 接收WebSocket文本: {message}")
                
                except asyncio.TimeoutError:
                    # 接收超时，正常情况
                    pass
                except websockets.exceptions.ConnectionClosed:
                    logger.info("🔌 WebSocket连接已关闭")
                
                logger.info(f"🎵 音频接收完成: 共接收 {audio_chunks_received} 个数据块, 总大小: {total_audio_size} 字节")
                
        except Exception as e:
            logger.error(f"❌ WebSocket音频接收异常: {e}")
    
    async def _send_playback_complete_event(self, track_id: str):
        """发送播放完成事件"""
        try:
            event_topic = f"device/{self.config.DEVICE_ID}/event"
            event_payload = {
                "evt": "EVT_SPEAK_DONE",
                "track_id": track_id,
                "timestamp": datetime.now().isoformat(),
                "device_id": self.config.DEVICE_ID,
                "client_id": self.config.CLIENT_ID,
                "duration": self.config.AUDIO_PLAY_DURATION,
                "status": "success"
            }
            
            event_message = json.dumps(event_payload)
            result = self.mqtt_client.publish(event_topic, event_message)
            
            logger.info(f"✅ 发送播放完成事件:")
            logger.info(f"   主题: {event_topic}")
            logger.info(f"   内容: {event_message}")
            logger.info(f"   结果: {result}")
            
        except Exception as e:
            logger.error(f"❌ 播放完成事件发送异常: {e}")
    
    async def _send_error_event(self, track_id: str, error_message: str):
        """发送错误事件"""
        try:
            event_topic = f"device/{self.config.DEVICE_ID}/event"
            event_payload = {
                "evt": "EVT_ERROR",
                "track_id": track_id,
                "timestamp": datetime.now().isoformat(),
                "device_id": self.config.DEVICE_ID,
                "client_id": self.config.CLIENT_ID,
                "error": error_message,
                "status": "error"
            }
            
            event_message = json.dumps(event_payload)
            result = self.mqtt_client.publish(event_topic, event_message)
            
            logger.error(f"❌ 发送错误事件:")
            logger.error(f"   主题: {event_topic}")
            logger.error(f"   内容: {event_message}")
            
        except Exception as e:
            logger.error(f"❌ 错误事件发送异常: {e}")
    
    async def start(self):
        """启动硬件模拟器"""
        try:
            logger.info("🚀 启动硬件模拟器...")
            logger.info(f"   设备ID: {self.config.DEVICE_ID}")
            logger.info(f"   客户端ID: {self.config.CLIENT_ID}")
            logger.info(f"   MQTT服务器: {self.config.MQTT_HOST}:{self.config.MQTT_PORT}")
            logger.info(f"   WebSocket URL: {self.config.WEBSOCKET_URL}")
            
            self.running = True
            
            # 设置并连接MQTT
            self.setup_mqtt()
            
            # 在线程中运行MQTT客户端
            mqtt_thread = threading.Thread(target=self._run_mqtt_client, daemon=True)
            mqtt_thread.start()
            
            # 等待MQTT连接
            for _ in range(50):  # 最多等待5秒
                if self.mqtt_connected:
                    break
                await asyncio.sleep(0.1)
            
            if not self.mqtt_connected:
                raise Exception("MQTT连接超时")
            
            logger.info("✅ 硬件模拟器启动成功")
            
            # 发送上线事件
            await self._send_device_online_event()
            
            # 保持运行状态
            while self.running:
                await asyncio.sleep(1)
                
                # 定期输出状态信息
                if int(time.time()) % 30 == 0:  # 每30秒输出一次状态
                    await self._report_status()
                    await asyncio.sleep(1)  # 避免重复输出
                    
        except KeyboardInterrupt:
            logger.info("收到中断信号，准备关闭...")
        except Exception as e:
            logger.error(f"❌ 硬件模拟器运行异常: {e}")
        finally:
            await self.stop()
    
    def _run_mqtt_client(self):
        """在线程中运行MQTT客户端"""
        try:
            self.mqtt_client.connect(self.config.MQTT_HOST, self.config.MQTT_PORT, 60)
            self.mqtt_client.loop_forever()
        except Exception as e:
            logger.error(f"❌ MQTT客户端运行异常: {e}")
    
    async def _send_device_online_event(self):
        """发送设备上线事件"""
        try:
            event_topic = f"device/{self.config.DEVICE_ID}/event"
            event_payload = {
                "evt": "EVT_DEVICE_ONLINE",
                "timestamp": datetime.now().isoformat(),
                "device_id": self.config.DEVICE_ID,
                "client_id": self.config.CLIENT_ID,
                "simulator_version": "1.0.0",
                "capabilities": [
                    "MQTT_COMMAND_RECEIVING",
                    "WEBSOCKET_AUDIO_RECEIVING",
                    "AUDIO_PLAYBACK_SIMULATION"
                ]
            }
            
            event_message = json.dumps(event_payload)
            self.mqtt_client.publish(event_topic, event_message)
            
            logger.info(f"📢 发送设备上线事件: {event_payload['evt']}")
            
        except Exception as e:
            logger.error(f"❌ 设备上线事件发送异常: {e}")
    
    async def _report_status(self):
        """报告设备状态"""
        logger.info("📊 设备状态:")
        logger.info(f"   MQTT连接: {'✅' if self.mqtt_connected else '❌'}")
        logger.info(f"   WebSocket连接: {'✅' if self.websocket_connected else '❌'}")
        logger.info(f"   设备状态: {self.device_status}")
        logger.info(f"   当前Track ID: {self.current_track_id}")
        logger.info(f"   接收命令数: {len(self.received_commands)}")
        logger.info(f"   音频播放中: {'是' if self.audio_playing else '否'}")
    
    async def stop(self):
        """停止硬件模拟器"""
        logger.info("🛑 停止硬件模拟器...")
        
        self.running = False
        
        # 发送设备下线事件
        try:
            await self._send_device_offline_event()
        except:
            pass
        
        # 断开MQTT连接
        try:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        except:
            pass
        
        logger.info("✅ 硬件模拟器已停止")
    
    async def _send_device_offline_event(self):
        """发送设备下线事件"""
        try:
            event_topic = f"device/{self.config.DEVICE_ID}/event"
            event_payload = {
                "evt": "EVT_DEVICE_OFFLINE",
                "timestamp": datetime.now().isoformat(),
                "device_id": self.config.DEVICE_ID,
                "client_id": self.config.CLIENT_ID,
                "uptime": time.time() - getattr(self, 'start_time', time.time()),
                "total_commands_received": len(self.received_commands)
            }
            
            event_message = json.dumps(event_payload)
            self.mqtt_client.publish(event_topic, event_message)
            
            logger.info(f"📢 发送设备下线事件: {event_payload['evt']}")
            
        except Exception as e:
            logger.error(f"❌ 设备下线事件发送异常: {e}")

def create_simulator_with_config(**kwargs):
    """创建配置自定义的模拟器"""
    config = HardwareSimulatorConfig()
    
    # 更新配置
    for key, value in kwargs.items():
        if hasattr(config, key.upper()):
            setattr(config, key.upper(), value)
        elif hasattr(config, key):
            setattr(config, key, value)
    
    return HardwareSimulator(config)

async def main():
    """主函数 - 演示如何使用硬件模拟器"""
    import sys
    
    # 解析命令行参数
    device_id = "7c:2c:67:8d:89:78"
    if len(sys.argv) > 1:
        device_id = sys.argv[1]
    
    # 创建模拟器配置
    config = HardwareSimulatorConfig()
    config.DEVICE_ID = device_id
    
    # 可以在这里调整模拟器行为
    # config.SIMULATE_ACK_FAILURE_RATE = 0.1  # 10% ACK失败率
    # config.SIMULATE_AUDIO_FAILURE_RATE = 0.05  # 5% 音频播放失败率
    # config.ACK_DELAY_MS = 100  # 100ms ACK延迟
    
    # 创建并启动模拟器
    simulator = HardwareSimulator(config)
    simulator.start_time = time.time()
    
    try:
        await simulator.start()
    except KeyboardInterrupt:
        print("\n收到中断信号，正在关闭模拟器...")
    finally:
        await simulator.stop()

if __name__ == "__main__":
    print("🤖 小智硬件设备模拟器 v1.0.0")
    print("按 Ctrl+C 停止模拟器")
    print("-" * 50)
    
    asyncio.run(main())

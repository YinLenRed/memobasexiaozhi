import json
import uuid
import time
import asyncio
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from paho.mqtt import client as mqtt_client
from config.logger import setup_logging

TAG = __name__


class MQTTClient:
    """MQTT客户端，用于与ESP32设备通信"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()
        
        # MQTT配置
        self.broker_host = config.get("mqtt", {}).get("host", "47.98.51.180")
        self.broker_port = config.get("mqtt", {}).get("port", 1883)
        self.username = config.get("mqtt", {}).get("username", "")
        self.password = config.get("mqtt", {}).get("password", "")
        self.client_id = config.get("mqtt", {}).get("client_id", f"xiaozhi-server-{uuid.uuid4().hex[:8]}")
        
        # MQTT客户端
        self.client = None
        self.connected = False
        self.running = False
        
        # 消息处理器
        self.message_handlers: Dict[str, Callable] = {}
        self.device_ack_handlers: Dict[str, Callable] = {}
        
        # 设备状态跟踪
        self.device_states: Dict[str, Dict] = {}
        
        # 线程安全锁
        self.lock = threading.Lock()
        
    async def start(self):
        """启动MQTT客户端"""
        if self.running:
            return
            
        self.running = True
        self.client = mqtt_client.Client(client_id=self.client_id)
        
        # 设置用户名密码
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        # 设置回调函数
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        try:
            # 连接到MQTT代理
            self.logger.bind(tag=TAG).info(f"连接MQTT代理: {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            
            # 启动网络循环线程
            self.client.loop_start()
            
            # 等待连接建立
            for _ in range(30):  # 最多等待30秒
                if self.connected:
                    break
                await asyncio.sleep(1)
            
            if not self.connected:
                raise Exception("MQTT连接超时")
                
            self.logger.bind(tag=TAG).info("MQTT客户端启动成功")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MQTT客户端启动失败: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """停止MQTT客户端"""
        if not self.running:
            return
            
        self.running = False
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            
        self.connected = False
        self.logger.bind(tag=TAG).info("MQTT客户端已停止")
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接成功回调"""
        if rc == 0:
            self.connected = True
            self.logger.bind(tag=TAG).info("MQTT连接成功")
            
            # 订阅设备回复和事件主题
            client.subscribe("device/+/ack")
            client.subscribe("device/+/event")
            self.logger.bind(tag=TAG).info("已订阅设备主题: device/+/ack, device/+/event")
        else:
            self.logger.bind(tag=TAG).error(f"MQTT连接失败，返回码: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self.connected = False
        if rc != 0:
            self.logger.bind(tag=TAG).warning(f"MQTT意外断开连接，返回码: {rc}")
        else:
            self.logger.bind(tag=TAG).info("MQTT正常断开连接")
    
    def _on_message(self, client, userdata, msg):
        """消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            self.logger.bind(tag=TAG).debug(f"收到MQTT消息: {topic} -> {payload}")
            
            # 解析设备ID
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3:
                device_id = topic_parts[1]
                message_type = topic_parts[2]
                
                # 解析消息内容
                try:
                    message_data = json.loads(payload)
                except json.JSONDecodeError:
                    self.logger.bind(tag=TAG).error(f"无法解析JSON消息: {payload}")
                    return
                
                # 处理不同类型的消息
                if message_type == "ack":
                    self._handle_device_ack(device_id, message_data)
                elif message_type == "event":
                    self._handle_device_event(device_id, message_data)
                    
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理MQTT消息失败: {e}")
    
    def _handle_device_ack(self, device_id: str, message_data: Dict):
        """处理设备ACK消息"""
        track_id = message_data.get("track_id")
        
        if track_id:
            # 更新设备状态
            with self.lock:
                if device_id not in self.device_states:
                    self.device_states[device_id] = {}
                self.device_states[device_id][track_id] = {
                    "status": "ack_received",
                    "timestamp": datetime.now().isoformat()
                }
            
            # 调用注册的ACK处理器
            if track_id in self.device_ack_handlers:
                try:
                    self.device_ack_handlers[track_id](device_id, message_data)
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"处理设备ACK失败: {e}")
        
        self.logger.bind(tag=TAG).info(f"设备 {device_id} ACK: {message_data}")
    
    def _handle_device_event(self, device_id: str, message_data: Dict):
        """处理设备事件消息"""
        event_type = message_data.get("evt")
        track_id = message_data.get("track_id")
        
        if event_type == "EVT_SPEAK_DONE" and track_id:
            # 更新设备状态
            with self.lock:
                if device_id in self.device_states and track_id in self.device_states[device_id]:
                    self.device_states[device_id][track_id]["status"] = "speak_done"
                    self.device_states[device_id][track_id]["completed_timestamp"] = datetime.now().isoformat()
        
        # 调用注册的消息处理器
        for handler in self.message_handlers.values():
            try:
                handler(device_id, event_type, message_data)
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"处理设备事件失败: {e}")
        
        self.logger.bind(tag=TAG).info(f"设备 {device_id} 事件: {message_data}")
    
    async def send_speak_command(self, device_id: str, text: str, track_id: str = None) -> str:
        """发送语音播放命令"""
        if not self.connected:
            raise Exception("MQTT未连接")
        
        if not track_id:
            track_id = f"WX{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"
        
        command = {
            "cmd": "SPEAK",
            "text": text,
            "track_id": track_id
        }
        
        topic = f"device/{device_id}/cmd"
        
        # 记录发送状态
        with self.lock:
            if device_id not in self.device_states:
                self.device_states[device_id] = {}
            self.device_states[device_id][track_id] = {
                "status": "command_sent",
                "timestamp": datetime.now().isoformat(),
                "text": text
            }
        
        # 发送MQTT消息
        result = self.client.publish(topic, json.dumps(command, ensure_ascii=False))
        
        if result.rc == 0:
            self.logger.bind(tag=TAG).info(f"发送语音命令成功: {device_id} -> {text[:50]}...")
            return track_id
        else:
            raise Exception(f"发送MQTT消息失败，返回码: {result.rc}")
    
    def register_ack_handler(self, track_id: str, handler: Callable):
        """注册ACK处理器"""
        self.device_ack_handlers[track_id] = handler
    
    def register_message_handler(self, name: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[name] = handler
    
    def get_device_state(self, device_id: str, track_id: str = None) -> Dict:
        """获取设备状态"""
        with self.lock:
            if device_id not in self.device_states:
                return {}
            
            if track_id:
                return self.device_states[device_id].get(track_id, {})
            
            return self.device_states[device_id]
    
    def cleanup_old_states(self, max_age_hours: int = 24):
        """清理旧状态记录"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        with self.lock:
            for device_id in list(self.device_states.keys()):
                device_tracks = self.device_states[device_id]
                for track_id in list(device_tracks.keys()):
                    track_info = device_tracks[track_id]
                    track_time = datetime.fromisoformat(track_info["timestamp"]).timestamp()
                    
                    if track_time < cutoff_time:
                        del device_tracks[track_id]
                
                # 如果设备没有任何跟踪记录，删除设备记录
                if not device_tracks:
                    del self.device_states[device_id]

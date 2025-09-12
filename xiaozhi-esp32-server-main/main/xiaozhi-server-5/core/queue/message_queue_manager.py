#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硬件消息队列管理器
确保硬件按顺序完整播放每条消息，避免被新消息打断
"""

import asyncio
import json
import time
import uuid
from collections import deque
from datetime import datetime
from typing import Dict, Any, Optional, Deque
from enum import Enum
from config.logger import setup_logging

TAG = __name__

class MessageStatus(Enum):
    """消息状态枚举"""
    QUEUED = "queued"           # 排队中
    PLAYING = "playing"         # 播放中  
    COMPLETED = "completed"     # 播放完成
    FAILED = "failed"           # 播放失败
    CANCELLED = "cancelled"     # 已取消

class QueuedMessage:
    """队列消息对象"""
    
    def __init__(self, device_id: str, content: str, category: str = "default", 
                 priority: int = 0, user_info: Dict = None):
        self.message_id = f"MSG_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        self.device_id = device_id
        self.content = content
        self.category = category
        self.priority = priority  # 优先级，数字越小优先级越高
        self.user_info = user_info or {}
        
        # 状态跟踪
        self.status = MessageStatus.QUEUED
        self.track_id = None
        self.created_time = datetime.now().isoformat()
        self.start_time = None
        self.complete_time = None
        
        # 重试机制
        self.retry_count = 0
        self.max_retries = 3
        
    def __lt__(self, other):
        """优先级比较（用于优先队列）"""
        return self.priority < other.priority
    
    def to_dict(self):
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "device_id": self.device_id,
            "content": self.content,
            "category": self.category,
            "priority": self.priority,
            "status": self.status.value,
            "track_id": self.track_id,
            "created_time": self.created_time,
            "start_time": self.start_time,
            "complete_time": self.complete_time,
            "retry_count": self.retry_count
        }

class DeviceMessageQueue:
    """单设备消息队列"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.queue: Deque[QueuedMessage] = deque()
        self.current_message: Optional[QueuedMessage] = None
        self.is_playing = False
        self.total_messages = 0
        self.completed_messages = 0
        self.failed_messages = 0
        
    def add_message(self, message: QueuedMessage):
        """添加消息到队列"""
        # 根据优先级插入到合适位置
        inserted = False
        for i, queued_msg in enumerate(self.queue):
            if message.priority < queued_msg.priority:
                self.queue.insert(i, message)
                inserted = True
                break
        
        if not inserted:
            self.queue.append(message)
        
        self.total_messages += 1
        
    def get_next_message(self) -> Optional[QueuedMessage]:
        """获取下一条消息"""
        if self.queue and not self.is_playing:
            return self.queue.popleft()
        return None
    
    def start_playing(self, message: QueuedMessage):
        """开始播放消息"""
        self.current_message = message
        self.is_playing = True
        message.status = MessageStatus.PLAYING
        message.start_time = datetime.now().isoformat()
    
    def complete_playing(self):
        """完成播放"""
        if self.current_message:
            self.current_message.status = MessageStatus.COMPLETED
            self.current_message.complete_time = datetime.now().isoformat()
            self.completed_messages += 1
            self.current_message = None
        self.is_playing = False
    
    def fail_playing(self):
        """播放失败"""
        if self.current_message:
            self.current_message.status = MessageStatus.FAILED
            self.current_message.complete_time = datetime.now().isoformat()
            self.failed_messages += 1
            self.current_message = None
        self.is_playing = False
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        return {
            "device_id": self.device_id,
            "queue_length": len(self.queue),
            "is_playing": self.is_playing,
            "current_message": self.current_message.to_dict() if self.current_message else None,
            "total_messages": self.total_messages,
            "completed_messages": self.completed_messages,
            "failed_messages": self.failed_messages,
            "pending_messages": [msg.to_dict() for msg in list(self.queue)[:5]]  # 只显示前5条
        }

class MessageQueueManager:
    """全局消息队列管理器"""
    
    def __init__(self, unified_event_service=None):
        self.logger = setup_logging()
        self.unified_event_service = unified_event_service
        
        # 每个设备的消息队列
        self.device_queues: Dict[str, DeviceMessageQueue] = {}
        
        # 队列处理任务
        self.queue_tasks: Dict[str, asyncio.Task] = {}
        
        # 统计信息
        self.total_messages_processed = 0
        self.start_time = datetime.now()
        
        # 配置
        self.max_queue_size = 50  # 每个设备最大队列长度
        self.message_timeout = 60  # 消息播放超时时间（秒）
        
    def add_message(self, device_id: str, content: str, category: str = "default", 
                   priority: int = 0, user_info: Dict = None) -> str:
        """添加消息到设备队列"""
        try:
            # 创建队列消息
            message = QueuedMessage(device_id, content, category, priority, user_info)
            
            # 获取或创建设备队列
            if device_id not in self.device_queues:
                self.device_queues[device_id] = DeviceMessageQueue(device_id)
            
            device_queue = self.device_queues[device_id]
            
            # 检查队列长度限制
            if len(device_queue.queue) >= self.max_queue_size:
                self.logger.bind(tag=TAG).warning(f"设备队列已满: {device_id}, 丢弃最旧消息")
                oldest_message = device_queue.queue.popleft()
                oldest_message.status = MessageStatus.CANCELLED
            
            # 添加消息到队列
            device_queue.add_message(message)
            
            self.logger.bind(tag=TAG).info(
                f"🎵 消息入队: {device_id}, 消息ID: {message.message_id}, "
                f"内容: {content[:30]}..., 队列长度: {len(device_queue.queue)}"
            )
            
            # 启动或确保队列处理任务运行
            self._ensure_queue_processor(device_id)
            
            return message.message_id
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"添加消息失败: {e}")
            return None
    
    def _ensure_queue_processor(self, device_id: str):
        """确保队列处理任务运行"""
        if device_id not in self.queue_tasks or self.queue_tasks[device_id].done():
            # 创建新的队列处理任务
            self.queue_tasks[device_id] = asyncio.create_task(
                self._process_device_queue(device_id)
            )
            self.logger.bind(tag=TAG).info(f"启动设备队列处理器: {device_id}")
    
    async def _process_device_queue(self, device_id: str):
        """处理设备消息队列"""
        device_queue = self.device_queues[device_id]
        
        while True:
            try:
                # 获取下一条消息
                message = device_queue.get_next_message()
                
                if not message:
                    # 队列为空，等待新消息
                    await asyncio.sleep(1)
                    continue
                
                # 开始播放
                device_queue.start_playing(message)
                
                self.logger.bind(tag=TAG).info(
                    f"🎬 开始播放: {device_id}, 消息ID: {message.message_id}, "
                    f"内容: {message.content[:50]}..."
                )
                
                # 发送消息给硬件
                success = await self._send_to_hardware(message)
                
                if success:
                    # 等待播放完成
                    await self._wait_for_completion(message)
                else:
                    # 发送失败
                    device_queue.fail_playing()
                    self.logger.bind(tag=TAG).error(f"发送消息失败: {message.message_id}")
                
                self.total_messages_processed += 1
                
            except asyncio.CancelledError:
                self.logger.bind(tag=TAG).info(f"队列处理器被取消: {device_id}")
                break
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"队列处理异常: {device_id}, {e}")
                if device_queue.current_message:
                    device_queue.fail_playing()
                await asyncio.sleep(5)  # 出错时等待5秒
    
    async def _send_to_hardware(self, message: QueuedMessage) -> bool:
        """发送消息到硬件（支持API消息LLM处理）"""
        try:
            if not self.unified_event_service:
                self.logger.bind(tag=TAG).error("未设置unified_event_service")
                return False
            
            # 检查是否需要LLM处理（API消息或定时提醒）
            message_type = message.user_info.get('type') if message.user_info else None
            
            if message_type in ['api_greeting', 'timer_reminder']:
                if message_type == 'api_greeting':
                    self.logger.bind(tag=TAG).info(f"🤖 处理API消息LLM生成: {message.message_id}")
                elif message_type == 'timer_reminder':
                    self.logger.bind(tag=TAG).info(f"⏰ 处理定时提醒LLM生成: {message.message_id}")
                
                # 获取用户信息和上下文
                if message_type == 'api_greeting':
                    original_user_info = message.user_info.get('original_user_info', {})
                    memory_info = message.user_info.get('memory_info', '')
                else:  # timer_reminder
                    # 为定时提醒构建上下文信息
                    original_user_info = {
                        "reminder_type": message.user_info.get('timer_type', 'relative'),
                        "reminder_content": message.user_info.get('reminder_content', ''),
                        "action_type": message.user_info.get('action_type', '提醒')
                    }
                    memory_info = f"这是一个{message.user_info.get('action_type', '提醒')}用户{message.user_info.get('reminder_content', '')}的定时提醒"
                
                # 调用ProactiveGreetingService生成智能内容
                if hasattr(self.unified_event_service, 'awaken_service') and hasattr(self.unified_event_service.awaken_service, 'greeting_service'):
                    greeting_service = self.unified_event_service.awaken_service.greeting_service
                    if hasattr(greeting_service, 'generate_greeting_content'):
                        try:
                            # 生成智能内容
                            enhanced_content = await greeting_service.generate_greeting_content(
                                message.content, 
                                message.category, 
                                original_user_info, 
                                memory_info,
                                message.device_id
                            )
                            if enhanced_content and enhanced_content.strip():
                                message.content = enhanced_content
                                if message_type == 'api_greeting':
                                    self.logger.bind(tag=TAG).info(f"✅ API消息LLM生成内容: {enhanced_content[:50]}...")
                                else:
                                    self.logger.bind(tag=TAG).info(f"✅ 定时提醒LLM生成内容: {enhanced_content[:50]}...")
                            else:
                                self.logger.bind(tag=TAG).warning("⚠️ LLM生成内容为空，使用原内容")
                        except Exception as e:
                            self.logger.bind(tag=TAG).error(f"❌ LLM生成失败: {e}，使用原内容")
            
            # 调用unified_event_service发送消息
            if hasattr(self.unified_event_service, 'awaken_service'):
                # 生成track_id
                track_id = f"QUEUE_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
                message.track_id = track_id
                
                # 注册消息到队列管理器
                self._register_message_tracking(message)
                
                # 发送speak命令（正确的参数）
                result_track_id = await self.unified_event_service.awaken_service.send_awaken_with_callback(
                    device_id=message.device_id,
                    message=message.content,
                    message_type=message.category
                )
                
                # 更新实际的track_id（如果返回值不同）
                if result_track_id and result_track_id != track_id:
                    message.track_id = result_track_id
                
                return True
            else:
                self.logger.bind(tag=TAG).error("unified_event_service没有awaken_service")
                return False
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"发送到硬件失败: {e}")
            return False
    
    def _register_message_tracking(self, message: QueuedMessage):
        """注册消息跟踪"""
        # 这里可以注册到全局跟踪系统
        pass
    
    async def _wait_for_completion(self, message: QueuedMessage):
        """等待消息播放完成"""
        timeout_time = time.time() + self.message_timeout
        
        while time.time() < timeout_time:
            if message.status == MessageStatus.COMPLETED:
                self.logger.bind(tag=TAG).info(f"✅ 播放完成: {message.message_id}")
                return
            elif message.status == MessageStatus.FAILED:
                self.logger.bind(tag=TAG).error(f"❌ 播放失败: {message.message_id}")
                return
            
            await asyncio.sleep(0.5)
        
        # 超时处理
        self.logger.bind(tag=TAG).warning(f"⏰ 播放超时: {message.message_id}")
        device_queue = self.device_queues.get(message.device_id)
        if device_queue:
            device_queue.fail_playing()
    
    def on_message_completed(self, device_id: str, track_id: str):
        """消息播放完成回调"""
        try:
            device_queue = self.device_queues.get(device_id)
            if device_queue and device_queue.current_message:
                if device_queue.current_message.track_id == track_id:
                    device_queue.complete_playing()
                    self.logger.bind(tag=TAG).info(
                        f"🎯 确认播放完成: {device_id}, track_id: {track_id}"
                    )
                else:
                    self.logger.bind(tag=TAG).warning(
                        f"track_id不匹配: 期望{device_queue.current_message.track_id}, "
                        f"实际{track_id}"
                    )
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理播放完成回调失败: {e}")
    
    def on_message_failed(self, device_id: str, track_id: str, error: str = ""):
        """消息播放失败回调"""
        try:
            device_queue = self.device_queues.get(device_id)
            if device_queue and device_queue.current_message:
                if device_queue.current_message.track_id == track_id:
                    device_queue.fail_playing()
                    self.logger.bind(tag=TAG).error(
                        f"❌ 确认播放失败: {device_id}, track_id: {track_id}, 错误: {error}"
                    )
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理播放失败回调失败: {e}")
    
    def get_device_queue_status(self, device_id: str) -> Optional[Dict]:
        """获取设备队列状态"""
        device_queue = self.device_queues.get(device_id)
        if device_queue:
            return device_queue.get_queue_status()
        return None
    
    def get_all_queues_status(self) -> Dict:
        """获取所有队列状态"""
        return {
            "total_devices": len(self.device_queues),
            "total_messages_processed": self.total_messages_processed,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "devices": {
                device_id: queue.get_queue_status() 
                for device_id, queue in self.device_queues.items()
            }
        }
    
    def clear_device_queue(self, device_id: str) -> bool:
        """清空设备队列"""
        try:
            if device_id in self.device_queues:
                device_queue = self.device_queues[device_id]
                
                # 取消所有排队消息
                for message in device_queue.queue:
                    message.status = MessageStatus.CANCELLED
                device_queue.queue.clear()
                
                self.logger.bind(tag=TAG).info(f"清空设备队列: {device_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"清空队列失败: {e}")
            return False
    
    def shutdown(self):
        """关闭队列管理器"""
        self.logger.bind(tag=TAG).info("关闭消息队列管理器...")
        
        # 取消所有队列处理任务
        for device_id, task in self.queue_tasks.items():
            if not task.done():
                task.cancel()
                self.logger.bind(tag=TAG).info(f"取消队列处理器: {device_id}")
        
        # 清空所有队列
        for device_id in list(self.device_queues.keys()):
            self.clear_device_queue(device_id)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能时间确认系统 - 多轮对话提取和确认时间信息
当用户提到模糊时间时，主动询问具体时间，直到获得明确时间才保存策略
"""

import re
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('时间确认系统')

class TimeStatus(Enum):
    """时间状态枚举"""
    CLEAR = "clear"          # 时间明确
    VAGUE = "vague"          # 时间模糊
    MISSING = "missing"      # 缺少时间
    INVALID = "invalid"      # 时间无效

class ConversationState(Enum):
    """对话状态枚举"""
    INITIAL = "initial"      # 初始状态
    WAITING_TIME = "waiting_time"  # 等待时间确认
    CONFIRMED = "confirmed"   # 已确认
    CANCELLED = "cancelled"   # 已取消

@dataclass
class TimeInfo:
    """时间信息数据类"""
    original_text: str       # 原始文本
    extracted_time: Optional[datetime] = None  # 提取的时间
    status: TimeStatus = TimeStatus.MISSING
    confidence: float = 0.0  # 置信度
    details: Dict = None     # 详细信息

@dataclass
class ReminderTask:
    """提醒任务数据类"""
    task_id: str
    user_content: str        # 用户原始内容
    extracted_task: str      # 提取的任务内容
    time_info: TimeInfo
    device_id: str
    conversation_state: ConversationState = ConversationState.INITIAL
    attempts: int = 0        # 尝试次数
    max_attempts: int = 3    # 最大尝试次数
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class TimeExtractor:
    """时间信息提取器"""
    
    def __init__(self):
        # 时间模式定义
        self.time_patterns = {
            # 明确时间模式
            "clear_patterns": [
                r'(\d{4}年\d{1,2}月\d{1,2}日)',  # 2024年3月15日
                r'(\d{1,2}月\d{1,2}日)',          # 3月15日
                r'(明天|后天)(\d{1,2}点|\d{1,2}:\d{2})?',  # 明天下午3点
                r'(\d{1,2}点\d{1,2}分?)',         # 3点30分
                r'(\d{1,2}:\d{2})',               # 14:30
                r'(今天|明天|后天)(上午|下午|晚上)?(\d{1,2}点)?',
            ],
            # 模糊时间模式
            "vague_patterns": [
                r'(下周|下个月|下个星期)',
                r'(这周|这个月|这个星期)',
                r'(周\d|星期\d)(?!.*\d{1,2}点)',  # 周三但没有具体时间
                r'(早上|上午|下午|晚上)(?!.*\d{1,2}点)',  # 只有时段没有具体时间
                r'(过几天|几天后|一会儿|稍后)',
            ]
        }
        
    def extract_time_info(self, text: str) -> TimeInfo:
        """提取时间信息"""
        time_info = TimeInfo(original_text=text)
        
        # 检查明确时间模式
        for pattern in self.time_patterns["clear_patterns"]:
            if re.search(pattern, text):
                time_info.status = TimeStatus.CLEAR
                time_info.confidence = 0.8
                time_info.extracted_time = self._parse_specific_time(text)
                time_info.details = {"type": "clear", "pattern": pattern}
                return time_info
        
        # 检查模糊时间模式
        for pattern in self.time_patterns["vague_patterns"]:
            if re.search(pattern, text):
                time_info.status = TimeStatus.VAGUE
                time_info.confidence = 0.6
                time_info.details = {"type": "vague", "pattern": pattern}
                return time_info
        
        # 检查是否包含任务但缺少时间
        task_keywords = ["提醒", "记得", "别忘了", "到时候", "需要", "要做"]
        if any(keyword in text for keyword in task_keywords):
            time_info.status = TimeStatus.MISSING
            time_info.confidence = 0.4
            time_info.details = {"type": "missing", "has_task": True}
        
        return time_info
    
    def _parse_specific_time(self, text: str) -> Optional[datetime]:
        """解析具体时间"""
        try:
            now = datetime.now()
            
            # 明天
            if "明天" in text:
                target_date = now + timedelta(days=1)
                # 提取时间
                time_match = re.search(r'(\d{1,2})点', text)
                if time_match:
                    hour = int(time_match.group(1))
                    if "下午" in text and hour < 12:
                        hour += 12
                    return target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                return target_date.replace(hour=9, minute=0, second=0, microsecond=0)  # 默认9点
            
            # 后天
            if "后天" in text:
                target_date = now + timedelta(days=2)
                time_match = re.search(r'(\d{1,2})点', text)
                if time_match:
                    hour = int(time_match.group(1))
                    if "下午" in text and hour < 12:
                        hour += 12
                    return target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                return target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            
            # 今天
            if "今天" in text:
                time_match = re.search(r'(\d{1,2})点', text)
                if time_match:
                    hour = int(time_match.group(1))
                    if "下午" in text and hour < 12:
                        hour += 12
                    return now.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            # 具体时间格式 HH:MM
            time_match = re.search(r'(\d{1,2}):(\d{2})', text)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                # 如果是今天的时间已经过了，默认为明天
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target_time < now:
                    target_time += timedelta(days=1)
                return target_time
            
            return None
            
        except Exception as e:
            logger.error(f"时间解析失败: {e}")
            return None

class ConversationManager:
    """对话管理器"""
    
    def __init__(self):
        self.active_tasks: Dict[str, ReminderTask] = {}  # device_id -> task
        self.time_extractor = TimeExtractor()
        
        # 时间确认问题模板
        self.time_questions = [
            "请问您希望在什么时候提醒您呢？比如'明天下午3点'或'3月15日上午9点'",
            "能告诉我具体的提醒时间吗？比如'后天早上8点'",  
            "请提供一个准确的时间，这样我就能为您设置提醒了",
            "为了准确提醒您，请告诉我具体的日期和时间"
        ]
        
    def process_user_message(self, device_id: str, user_message: str) -> Dict[str, Any]:
        """处理用户消息"""
        try:
            # 检查是否有正在进行的时间确认对话
            if device_id in self.active_tasks:
                return self._handle_time_confirmation(device_id, user_message)
            else:
                return self._handle_new_message(device_id, user_message)
                
        except Exception as e:
            logger.error(f"处理用户消息失败: {e}")
            return {
                "success": False,
                "message": "处理消息时出现错误，请重试",
                "need_response": True
            }
    
    def _handle_new_message(self, device_id: str, user_message: str) -> Dict[str, Any]:
        """处理新消息"""
        # 提取时间信息
        time_info = self.time_extractor.extract_time_info(user_message)
        
        if time_info.status == TimeStatus.CLEAR:
            # 时间明确，直接保存策略
            task = ReminderTask(
                task_id=f"task_{uuid.uuid4().hex[:8]}",
                user_content=user_message,
                extracted_task=self._extract_task_content(user_message),
                time_info=time_info,
                device_id=device_id,
                conversation_state=ConversationState.CONFIRMED
            )
            
            # 保存到Java
            success = self._save_strategy_to_java(task)
            
            if success:
                time_str = time_info.extracted_time.strftime("%Y年%m月%d日 %H:%M") if time_info.extracted_time else "指定时间"
                return {
                    "success": True,
                    "message": f"好的，我会在{time_str}提醒您：{task.extracted_task}",
                    "need_response": True,
                    "task_id": task.task_id
                }
            else:
                return {
                    "success": False,
                    "message": "提醒设置失败，请稍后重试",
                    "need_response": True
                }
                
        elif time_info.status == TimeStatus.VAGUE or time_info.status == TimeStatus.MISSING:
            # 时间模糊或缺失，需要确认
            task = ReminderTask(
                task_id=f"task_{uuid.uuid4().hex[:8]}",
                user_content=user_message,
                extracted_task=self._extract_task_content(user_message),
                time_info=time_info,
                device_id=device_id,
                conversation_state=ConversationState.WAITING_TIME,
                attempts=1
            )
            
            # 保存到活跃任务中
            self.active_tasks[device_id] = task
            
            question = self.time_questions[0]
            return {
                "success": True,
                "message": f"我理解您想要设置提醒：{task.extracted_task}。{question}",
                "need_response": True,
                "waiting_for": "time_confirmation",
                "task_id": task.task_id
            }
        else:
            # 不是提醒相关的消息
            return {
                "success": True,
                "message": None,  # 不需要特殊回复
                "need_response": False
            }
    
    def _handle_time_confirmation(self, device_id: str, user_message: str) -> Dict[str, Any]:
        """处理时间确认对话"""
        task = self.active_tasks[device_id]
        
        # 检查用户是否想取消
        if any(word in user_message for word in ["取消", "算了", "不用了", "没事"]):
            del self.active_tasks[device_id]
            task.conversation_state = ConversationState.CANCELLED
            return {
                "success": True,
                "message": "好的，已取消设置提醒",
                "need_response": True,
                "cancelled": True
            }
        
        # 重新提取时间信息
        time_info = self.time_extractor.extract_time_info(user_message)
        
        if time_info.status == TimeStatus.CLEAR:
            # 获得了明确时间
            task.time_info = time_info
            task.conversation_state = ConversationState.CONFIRMED
            
            # 从活跃任务中移除
            del self.active_tasks[device_id]
            
            # 保存到Java
            success = self._save_strategy_to_java(task)
            
            if success:
                time_str = time_info.extracted_time.strftime("%Y年%m月%d日 %H:%M") if time_info.extracted_time else "指定时间"
                return {
                    "success": True,
                    "message": f"完美！我会在{time_str}提醒您：{task.extracted_task}。提醒已设置成功！",
                    "need_response": True,
                    "confirmed": True,
                    "task_id": task.task_id
                }
            else:
                return {
                    "success": False,
                    "message": "提醒设置失败，请稍后重试",
                    "need_response": True
                }
        else:
            # 时间仍然不明确
            task.attempts += 1
            
            if task.attempts >= task.max_attempts:
                # 超过最大尝试次数，放弃
                del self.active_tasks[device_id]
                task.conversation_state = ConversationState.CANCELLED
                return {
                    "success": True,
                    "message": "很抱歉，无法确定准确的时间。如果您想设置提醒，请直接告诉我具体的日期和时间，比如'明天下午3点'。",
                    "need_response": True,
                    "give_up": True
                }
            else:
                # 继续询问
                question_index = min(task.attempts - 1, len(self.time_questions) - 1)
                question = self.time_questions[question_index]
                return {
                    "success": True,
                    "message": f"时间还不够明确呢。{question}",
                    "need_response": True,
                    "attempt": task.attempts,
                    "task_id": task.task_id
                }
    
    def _extract_task_content(self, message: str) -> str:
        """提取任务内容"""
        # 简单的任务内容提取逻辑
        task_content = message
        
        # 移除时间相关词汇
        time_words = ["明天", "后天", "下周", "下个月", "上午", "下午", "晚上", "点", "时", "分"]
        for word in time_words:
            task_content = task_content.replace(word, "")
        
        # 移除提醒关键词
        remind_words = ["提醒我", "记得", "别忘了", "到时候"]
        for word in remind_words:
            task_content = task_content.replace(word, "")
        
        task_content = task_content.strip("，。！？")
        return task_content.strip()
    
    def _save_strategy_to_java(self, task: ReminderTask) -> bool:
        """保存策略到Java后端"""
        try:
            # 构建Java后端期望的数据格式
            strategy_data = {
                "device_id": task.device_id,
                "task_id": task.task_id,
                "task_content": task.extracted_task,
                "reminder_time": task.time_info.extracted_time.isoformat() if task.time_info.extracted_time else None,
                "original_message": task.user_content,
                "created_at": task.created_at.isoformat(),
                "status": "active",
                "type": "user_reminder"
            }
            
            # 发送到Java后端（这里需要替换为实际的Java API地址）
            java_api_url = "http://q83b6ed9.natappfree.cc/xiaozhi/strategy/reminder"  # 假设的接口
            
            response = requests.post(
                java_api_url,
                json=strategy_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"策略保存成功: {task.task_id}")
                return True
            else:
                logger.error(f"策略保存失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"保存策略到Java失败: {e}")
            return False
    
    def get_active_conversations(self) -> Dict[str, Dict]:
        """获取活跃对话状态"""
        return {
            device_id: {
                "task_id": task.task_id,
                "extracted_task": task.extracted_task,
                "attempts": task.attempts,
                "state": task.conversation_state.value,
                "created_at": task.created_at.isoformat()
            }
            for device_id, task in self.active_tasks.items()
        }

# 全局对话管理器实例
conversation_manager = ConversationManager()

def process_reminder_message(device_id: str, user_message: str) -> Dict[str, Any]:
    """处理提醒消息的主要接口"""
    return conversation_manager.process_user_message(device_id, user_message)

def get_conversation_status(device_id: str) -> Optional[Dict]:
    """获取对话状态"""
    if device_id in conversation_manager.active_tasks:
        task = conversation_manager.active_tasks[device_id]
        return {
            "task_id": task.task_id,
            "extracted_task": task.extracted_task,
            "attempts": task.attempts,
            "state": task.conversation_state.value,
            "max_attempts": task.max_attempts
        }
    return None

# 测试功能
def test_time_confirmation():
    """测试时间确认功能"""
    print("🧪 智能时间确认系统测试")
    print("="*40)
    
    test_cases = [
        ("user001", "下周提醒我记得给女儿买生日礼物"),
        ("user002", "明天下午3点提醒我开会"),
        ("user003", "过几天提醒我交水电费"),
        ("user004", "3月15日上午9点提醒我体检")
    ]
    
    for device_id, message in test_cases:
        print(f"\n👤 用户({device_id}): {message}")
        result = process_reminder_message(device_id, message)
        print(f"🤖 系统回复: {result.get('message', '无回复')}")
        
        # 如果需要时间确认，模拟用户回复
        if result.get('waiting_for') == 'time_confirmation':
            print("   (等待用户回复时间...)")
            # 模拟用户回复
            follow_up = input("   用户回复: ") or "下周三下午2点"
            follow_result = process_reminder_message(device_id, follow_up)
            print(f"🤖 系统确认: {follow_result.get('message', '无回复')}")
    
    # 显示活跃对话
    active = conversation_manager.get_active_conversations()
    if active:
        print("\n📋 当前活跃对话:")
        for device_id, info in active.items():
            print(f"  {device_id}: {info['extracted_task']} (尝试{info['attempts']}次)")

if __name__ == "__main__":
    test_time_confirmation()

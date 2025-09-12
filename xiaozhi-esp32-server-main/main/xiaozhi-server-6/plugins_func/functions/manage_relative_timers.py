#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相对时间定时器管理功能
支持查询、删除、修改相对时间定时器
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from plugins_func.register import register_function, Action, ActionResponse, ToolType
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

# 全局定时器信息存储（包含详细信息）
timer_registry: Dict[str, Dict[str, Any]] = {}

# 从schedule_relative_timer.py导入活跃定时器
try:
    from plugins_func.functions.schedule_relative_timer import active_timers
except ImportError:
    active_timers = {}

# 从save_user_strategy.py导入临时定时器
try:
    from plugins_func.functions.save_user_strategy import temp_active_timers
except ImportError:
    temp_active_timers = {}

def register_timer_info(timer_id: str, device_id: str, content: str, action_type: str, 
                       target_time: datetime, duration_description: str, timer_type: str = "relative"):
    """注册定时器信息到全局注册表"""
    timer_registry[timer_id] = {
        "device_id": device_id,
        "content": content,
        "action_type": action_type,
        "target_time": target_time,
        "duration_description": duration_description,
        "timer_type": timer_type,
        "created_time": datetime.now(),
        "status": "active"
    }
    logger.bind(tag=TAG).info(f"注册定时器信息: {timer_id} -> {content}")

def unregister_timer_info(timer_id: str):
    """从全局注册表移除定时器信息"""
    if timer_id in timer_registry:
        del timer_registry[timer_id]
        logger.bind(tag=TAG).info(f"移除定时器信息: {timer_id}")

def get_device_timers(device_id: str) -> List[Dict[str, Any]]:
    """获取指定设备的所有活跃定时器"""
    device_timers = []
    
    for timer_id, timer_info in timer_registry.items():
        if (timer_info["device_id"] == device_id and 
            timer_info["status"] == "active" and
            timer_info["target_time"] > datetime.now()):
            
            # 检查定时器任务是否还在运行
            is_active = (timer_id in active_timers or 
                        timer_id in temp_active_timers)
            
            if is_active:
                device_timers.append({
                    "timer_id": timer_id,
                    "content": timer_info["content"],
                    "action_type": timer_info["action_type"],
                    "target_time": timer_info["target_time"],
                    "duration_description": timer_info["duration_description"],
                    "remaining_time": timer_info["target_time"] - datetime.now()
                })
    
    # 按目标时间排序
    device_timers.sort(key=lambda x: x["target_time"])
    return device_timers

def format_timer_list(timers: List[Dict[str, Any]]) -> str:
    """格式化定时器列表为用户友好的文本"""
    if not timers:
        return "目前没有设置任何相对时间提醒。"
    
    formatted_list = []
    for i, timer in enumerate(timers, 1):
        target_time_str = timer["target_time"].strftime("%H:%M")
        remaining = timer["remaining_time"]
        
        if remaining.total_seconds() > 3600:
            remaining_str = f"{int(remaining.total_seconds() // 3600)}小时{int((remaining.total_seconds() % 3600) // 60)}分钟"
        else:
            remaining_str = f"{int(remaining.total_seconds() // 60)}分钟"
        
        formatted_list.append(
            f"{i}. {target_time_str} - {timer['action_type']}{timer['content']} "
            f"(还有{remaining_str})"
        )
    
    return "当前的相对时间提醒：\n" + "\n".join(formatted_list)

def cancel_timer_task_sync(timer_id: str) -> bool:
    """取消指定的定时器任务（同步版本）"""
    try:
        # 取消schedule_relative_timer创建的任务
        if timer_id in active_timers:
            task = active_timers[timer_id]
            task.cancel()
            del active_timers[timer_id]
            logger.bind(tag=TAG).info(f"取消活跃定时器: {timer_id}")
            return True
        
        # 取消save_user_strategy创建的临时任务
        if timer_id in temp_active_timers:
            task = temp_active_timers[timer_id]
            task.cancel()
            del temp_active_timers[timer_id]
            logger.bind(tag=TAG).info(f"取消临时定时器: {timer_id}")
            return True
        
        logger.bind(tag=TAG).warning(f"未找到定时器任务: {timer_id}")
        return False
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"取消定时器任务失败: {timer_id}, {e}")
        return False

# 函数描述定义
LIST_RELATIVE_TIMERS_DESC = {
    "name": "list_relative_timers",
    "description": "查询当前设备的所有相对时间定时提醒",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

CANCEL_RELATIVE_TIMER_DESC = {
    "name": "cancel_relative_timer",
    "description": "取消指定的相对时间定时提醒。支持多轮对话确认具体要取消的定时器",
    "parameters": {
        "type": "object",
        "properties": {
            "target_time": {
                "type": "string",
                "description": "要取消的定时器时间，如'12:30'、'1小时后'等，可选"
            },
            "content_keyword": {
                "type": "string", 
                "description": "要取消的定时器内容关键词，如'吃饭'、'开会'等，可选"
            },
            "confirm_action": {
                "type": "string",
                "description": "确认操作类型：'list'=先列出定时器，'cancel'=确认取消指定定时器"
            }
        },
        "required": ["confirm_action"]
    }
}

MODIFY_RELATIVE_TIMER_DESC = {
    "name": "modify_relative_timer", 
    "description": "修改指定的相对时间定时提醒时间。支持多轮对话确认具体要修改的定时器和新时间",
    "parameters": {
        "type": "object",
        "properties": {
            "target_time": {
                "type": "string",
                "description": "要修改的定时器当前时间，如'12:30'、'1小时后'等，可选"
            },
            "new_time": {
                "type": "string",
                "description": "新的定时时间，支持相对时间如'30分钟后'、'1小时后'等，可选"
            },
            "content_keyword": {
                "type": "string",
                "description": "要修改的定时器内容关键词，如'吃饭'、'开会'等，可选"
            },
            "confirm_action": {
                "type": "string", 
                "description": "确认操作类型：'list'=先列出定时器，'select'=选择要修改的定时器，'modify'=确认修改"
            }
        },
        "required": ["confirm_action"]
    }
}

@register_function("list_relative_timers", LIST_RELATIVE_TIMERS_DESC, ToolType.SYSTEM_CTL)
def list_relative_timers(conn):
    """
    查询当前设备的所有相对时间定时提醒
    """
    logger.bind(tag=TAG).info("查询相对时间定时器列表")
    
    try:
        device_id = getattr(conn, 'device_id', None)
        if not device_id:
            return ActionResponse(
                Action.RESPONSE,
                "抱歉，无法识别您的设备，无法查询定时提醒。",
                None
            )
        
        timers = get_device_timers(device_id)
        timer_list_text = format_timer_list(timers)
        
        logger.bind(tag=TAG).info(f"设备 {device_id} 的定时器数量: {len(timers)}")
        
        return ActionResponse(Action.REQLLM, 
            f"用户询问当前的相对时间定时提醒。{timer_list_text} 请用自然的语言告诉用户当前的定时提醒情况。", None)
    
    except Exception as e:
        logger.bind(tag=TAG).error(f"查询定时器列表失败: {e}")
        return ActionResponse(Action.RESPONSE, "查询定时提醒时遇到错误，请稍后再试。", None)

@register_function("cancel_relative_timer", CANCEL_RELATIVE_TIMER_DESC, ToolType.SYSTEM_CTL)
def cancel_relative_timer(conn, confirm_action: str, target_time: str = "", content_keyword: str = ""):
    """
    取消指定的相对时间定时提醒
    支持多轮对话确认
    """
    logger.bind(tag=TAG).info(f"取消定时器请求: action={confirm_action}, time={target_time}, keyword={content_keyword}")
    
    try:
        device_id = getattr(conn, 'device_id', None)
        if not device_id:
            return ActionResponse(Action.RESPONSE, "抱歉，无法识别您的设备。", None)
        
        timers = get_device_timers(device_id)
        
        if confirm_action == "list":
            # 先列出当前定时器
            if not timers:
                return ActionResponse(Action.REQLLM, 
                    "用户想要取消定时提醒，但目前没有设置任何相对时间提醒。请告诉用户目前没有可以取消的定时提醒。", None)
            
            timer_list_text = format_timer_list(timers)
            return ActionResponse(Action.REQLLM,
                f"用户想要取消定时提醒。{timer_list_text} 请询问用户想要取消哪个定时提醒，可以说时间或内容关键词。", None)
        
        elif confirm_action == "cancel":
            # 确认取消指定定时器
            if not timers:
                return ActionResponse(Action.REQLLM, "目前没有定时提醒可以取消。", None)
            
            # 查找匹配的定时器
            matched_timer = None
            
            for timer in timers:
                # 匹配时间
                timer_time_str = timer["target_time"].strftime("%H:%M")
                if target_time and (target_time in timer_time_str or timer_time_str in target_time):
                    matched_timer = timer
                    break
                
                # 匹配内容关键词
                if content_keyword and content_keyword in timer["content"]:
                    matched_timer = timer
                    break
            
            if not matched_timer:
                timer_list_text = format_timer_list(timers)
                return ActionResponse(Action.REQLLM,
                    f"没有找到匹配的定时提醒。{timer_list_text} 请用户重新指定要取消的定时提醒。", None)
            
            # 执行取消操作
            timer_id = matched_timer["timer_id"]
            success = False
            
            # 直接调用取消逻辑（同步方式）
            try:
                if timer_id in active_timers:
                    task = active_timers[timer_id]
                    task.cancel()
                    del active_timers[timer_id]
                    success = True
                    logger.bind(tag=TAG).info(f"取消活跃定时器: {timer_id}")
                elif timer_id in temp_active_timers:
                    task = temp_active_timers[timer_id]
                    task.cancel()
                    del temp_active_timers[timer_id]
                    success = True
                    logger.bind(tag=TAG).info(f"取消临时定时器: {timer_id}")
            except Exception as e:
                logger.bind(tag=TAG).error(f"取消定时器失败: {timer_id}, {e}")
            
            if timer_id in timer_registry:
                timer_registry[timer_id]["status"] = "cancelled"
            
            target_time_str = matched_timer["target_time"].strftime("%H:%M")
            return ActionResponse(Action.REQLLM,
                f"已成功取消{target_time_str}的{matched_timer['action_type']}{matched_timer['content']}提醒。请确认告诉用户定时提醒已取消。", None)
        
        else:
            return ActionResponse(Action.RESPONSE, "操作类型错误，请重新尝试。", None)
    
    except Exception as e:
        logger.bind(tag=TAG).error(f"取消定时器失败: {e}")
        return ActionResponse(Action.RESPONSE, "取消定时提醒时遇到错误，请稍后再试。", None)

@register_function("modify_relative_timer", MODIFY_RELATIVE_TIMER_DESC, ToolType.SYSTEM_CTL)  
def modify_relative_timer(conn, confirm_action: str, target_time: str = "", new_time: str = "", content_keyword: str = ""):
    """
    修改指定的相对时间定时提醒
    支持多轮对话确认
    """
    logger.bind(tag=TAG).info(f"修改定时器请求: action={confirm_action}, time={target_time}, new_time={new_time}, keyword={content_keyword}")
    
    try:
        device_id = getattr(conn, 'device_id', None)
        if not device_id:
            return ActionResponse(Action.RESPONSE, "抱歉，无法识别您的设备。", None)
        
        timers = get_device_timers(device_id)
        
        if confirm_action == "list":
            # 先列出当前定时器
            if not timers:
                return ActionResponse(Action.REQLLM,
                    "用户想要修改定时提醒，但目前没有设置任何相对时间提醒。请告诉用户目前没有可以修改的定时提醒。", None)
            
            timer_list_text = format_timer_list(timers)
            return ActionResponse(Action.REQLLM,
                f"用户想要修改定时提醒。{timer_list_text} 请询问用户想要修改哪个定时提醒，可以说时间或内容关键词。", None)
        
        elif confirm_action == "select":
            # 选择要修改的定时器
            if not timers:
                return ActionResponse(Action.REQLLM, "目前没有定时提醒可以修改。", None)
            
            # 查找匹配的定时器
            matched_timer = None
            
            for timer in timers:
                # 匹配时间
                timer_time_str = timer["target_time"].strftime("%H:%M")
                if target_time and (target_time in timer_time_str or timer_time_str in target_time):
                    matched_timer = timer
                    break
                
                # 匹配内容关键词
                if content_keyword and content_keyword in timer["content"]:
                    matched_timer = timer
                    break
            
            if not matched_timer:
                timer_list_text = format_timer_list(timers)
                return ActionResponse(Action.REQLLM,
                    f"没有找到匹配的定时提醒。{timer_list_text} 请用户重新指定要修改的定时提醒。", None)
            
            # 存储选中的定时器到会话状态（这里简化处理）
            target_time_str = matched_timer["target_time"].strftime("%H:%M")
            return ActionResponse(Action.REQLLM,
                f"找到了{target_time_str}的{matched_timer['action_type']}{matched_timer['content']}提醒。请询问用户希望改到什么时间，比如'30分钟后'或'1小时后'。", None)
        
        elif confirm_action == "modify":
            # 执行修改操作
            if not new_time:
                return ActionResponse(Action.REQLLM, "请告诉我新的提醒时间，比如'30分钟后'或'1小时后'。", None)
            
            # 查找要修改的定时器
            matched_timer = None
            for timer in timers:
                timer_time_str = timer["target_time"].strftime("%H:%M")
                if target_time and (target_time in timer_time_str or timer_time_str in target_time):
                    matched_timer = timer
                    break
                if content_keyword and content_keyword in timer["content"]:
                    matched_timer = timer
                    break
            
            if not matched_timer:
                return ActionResponse(Action.REQLLM, "没有找到要修改的定时提醒，请重新选择。", None)
            
            # 解析新的时间
            from plugins_func.functions.schedule_relative_timer import _parse_duration
            delay_seconds = _parse_duration(new_time)
            
            if delay_seconds is None:
                return ActionResponse(Action.REQLLM, f"无法理解新的时间'{new_time}'，请使用'30分钟后'或'1小时后'这样的格式。", None)
            
            # 取消原定时器
            old_timer_id = matched_timer["timer_id"]
            cancel_success = False
            
            # 直接取消原定时器（同步方式）
            try:
                if old_timer_id in active_timers:
                    task = active_timers[old_timer_id]
                    task.cancel()
                    del active_timers[old_timer_id]
                    cancel_success = True
                    logger.bind(tag=TAG).info(f"取消原定时器: {old_timer_id}")
                elif old_timer_id in temp_active_timers:
                    task = temp_active_timers[old_timer_id]
                    task.cancel()
                    del temp_active_timers[old_timer_id]
                    cancel_success = True
                    logger.bind(tag=TAG).info(f"取消原临时定时器: {old_timer_id}")
            except Exception as e:
                logger.bind(tag=TAG).error(f"取消原定时器失败: {old_timer_id}, {e}")
            
            # 创建新定时器
            from plugins_func.functions.schedule_relative_timer import _timer_task
            new_timer_id = f"{device_id}_{int(datetime.now().timestamp())}_modified"
            new_target_time = datetime.now() + timedelta(seconds=delay_seconds)
            
            timer_task = asyncio.create_task(
                _timer_task(device_id, delay_seconds, matched_timer["content"], 
                           matched_timer["action_type"], new_timer_id)
            )
            
            # 更新定时器注册表
            if old_timer_id in timer_registry:
                timer_registry[old_timer_id]["status"] = "modified"
            
            register_timer_info(new_timer_id, device_id, matched_timer["content"], 
                               matched_timer["action_type"], new_target_time, new_time)
            
            # 保存到活跃定时器
            active_timers[new_timer_id] = timer_task
            
            new_time_str = new_target_time.strftime("%H:%M")
            return ActionResponse(Action.REQLLM,
                f"已成功将{matched_timer['action_type']}{matched_timer['content']}的提醒时间修改为{new_time}后（预计{new_time_str}）。请确认告诉用户定时提醒已修改。", None)
        
        else:
            return ActionResponse(Action.RESPONSE, "操作类型错误，请重新尝试。", None)
    
    except Exception as e:
        logger.bind(tag=TAG).error(f"修改定时器失败: {e}")
        return ActionResponse(Action.RESPONSE, "修改定时提醒时遇到错误，请稍后再试。", None)

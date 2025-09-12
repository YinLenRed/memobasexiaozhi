import re
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from plugins_func.register import register_function, Action, ActionResponse, ToolType
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

# 时间单位映射（中文到秒数）
TIME_UNIT_MAPPING = {
    # 分钟
    "分钟": 60,
    "分": 60,
    "min": 60,
    "minute": 60,
    "minutes": 60,
    "m": 60,
    
    # 小时
    "小时": 3600,
    "时": 3600,
    "钟头": 3600,  # 口语表达
    "时间": 3600,  # "1小时间"
    "hour": 3600,
    "hours": 3600,
    "h": 3600,
    
    # 秒
    "秒钟": 1,
    "秒": 1,
    "sec": 1,
    "second": 1,
    "seconds": 1,
    "s": 1,
}

# 中文数字映射
CHINESE_NUMBERS = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "两": 2, "半": 0.5, "零": 0, "几": 3,  # "几"默认为3
    "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
    "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
    "三十": 30, "四十": 40, "五十": 50, "六十": 60,
    "一个": 1, "两个": 2, "三个": 3, "四个": 4, "五个": 5,
    "1个": 1, "2个": 2, "3个": 3, "4个": 4, "5个": 5,
}

# 全局定时器任务字典，用于管理正在运行的定时器
active_timers: Dict[str, asyncio.Task] = {}

SCHEDULE_RELATIVE_TIMER_FUNCTION_DESC = {
    "name": "schedule_relative_timer", 
    "description": "专门处理相对时间定时提醒，当用户说'X分钟后'、'X小时后'、'半小时后'等相对时间表达时使用此功能。例如：'两分钟后提醒我喝水'、'30分钟后叫我吃饭'、'1小时后提醒我开会'、'半小时后叫我起床'等。注意：只处理包含'后'字的相对时间表达。",
    "parameters": {
        "type": "object",
        "properties": {
            "duration_text": {
                "type": "string",
                "description": "相对时间表达，如'30分钟'、'1小时'、'半小时'等"
            },
            "reminder_content": {
                "type": "string", 
                "description": "提醒内容，如'吃饭'、'开会'、'休息'等"
            },
            "action_type": {
                "type": "string",
                "description": "提醒动作类型，如'叫我'、'提醒我'、'通知我'等，默认为'提醒您'"
            }
        },
        "required": ["duration_text", "reminder_content"]
    }
}


def _parse_chinese_number(text: str) -> float:
    """解析中文数字，返回对应的数值"""
    text = text.strip()
    
    # 直接匹配阿拉伯数字
    if text.isdigit():
        return float(text)
    
    # 处理小数（如"1.5"）
    try:
        return float(text)
    except ValueError:
        pass
    
    # 🎯 特殊处理"X个半"的表达（如"两个半" = 2.5）
    if "个半" in text:
        base_text = text.replace("个半", "")
        if base_text in CHINESE_NUMBERS:
            return CHINESE_NUMBERS[base_text] + 0.5
        else:
            logger.bind(tag=TAG).warning(f"无法解析'个半'表达中的基数: {base_text}")
            return 1.5  # 默认为1.5
    
    # 处理标准中文数字
    if text in CHINESE_NUMBERS:
        return CHINESE_NUMBERS[text]
    
    logger.bind(tag=TAG).warning(f"无法解析的中文数字: {text}")
    return 1.0  # 默认值


def _parse_duration(duration_text: str) -> Optional[int]:
    """
    解析相对时间表达，返回对应的秒数
    
    支持的格式:
    - "30分钟" -> 1800秒
    - "1小时" -> 3600秒  
    - "半小时" -> 1800秒
    - "一个半小时" -> 5400秒
    - "2.5小时" -> 9000秒
    - "30分钟后叫我起床" -> 1800秒 (从完整语句中提取)
    """
    duration_text = duration_text.strip().lower()
    
    # 🎯 扩展的相对时间提取模式 - 支持从完整语句中提取时间
    extraction_patterns = [
        # 标准相对时间表达
        r'([一二三四五六七八九十几半两\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))\s*(?:之?后|以后|过后)',
        r'过\s*([一二三四五六七八九十几半两\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))',
        r'([一二三四五六七八九十几半两\d.]+(?:个)?\s*[分时小时秒钟]+)\s*(?:后|之后)',
        
        # 拓展表达方式
        r'等\s*([一二三四五六七八九十几半两\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))\s*(?:再|就|后)?',
        r'([一二三四五六七八九十几半两\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))\s*(?:内|以内)',
        r'再\s*(?:过\s*)?([一二三四五六七八九十几半两\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))',
        r'([一二三四五六七八九十几半两\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))\s*(?:后面|以后|之后)',
        r'隔\s*([一二三四五六七八九十几半两\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))',
        
        # 常用口语表达
        r'([一二三四五六七八九十几两半\d.]+)\s*(?:个)?\s*(?:钟头|小时)\s*(?:之?后|以后|过后)',
        r'([一二三四五六七八九十几两\d.]+)\s*刻钟\s*(?:之?后|以后)',  # 刻钟 = 15分钟
        r'([一二三四五六七八九十几两\d.]+)\s*(?:个)?\s*(?:半小时|半钟头)\s*(?:之?后|以后)',
        
        # 数字 + 时间单位的各种组合
        r'([0-9]+(?:\.[0-9]+)?)\s*(?:个)?\s*(?:小时|钟头|时|h)\s*(?:之?后|以后|过后)',
        r'([0-9]+(?:\.[0-9]+)?)\s*(?:分钟?|分|min|m)\s*(?:之?后|以后|过后)',
    ]
    
    # 尝试从完整语句中提取时间表达
    extracted_time = None
    for pattern in extraction_patterns:
        match = re.search(pattern, duration_text)
        if match:
            time_expr = match.group(1)
            # 特殊处理刻钟
            if '刻钟' in duration_text:
                extracted_time = f"{time_expr}刻钟"
            # 特殊处理半小时/半钟头
            elif '半小时' in duration_text or '半钟头' in duration_text:
                extracted_time = f"{time_expr}半小时"
            else:
                extracted_time = time_expr
            logger.bind(tag=TAG).info(f"从语句'{duration_text}'中提取时间表达: '{extracted_time}'")
            break
    
    # 如果没有提取到，使用原文本
    if not extracted_time:
        extracted_time = duration_text
    
    # 正则模式匹配相对时间
    patterns = [
        # 处理刻钟（15分钟）
        r"([一二三四五六七八九十几两半零\d.]+(?:个)?)?\s*刻钟",
        # 处理半小时/半钟头
        r"([一二三四五六七八九十几两半零\d.]+(?:个)?)?\s*(?:半小时|半钟头)",
        # 数字 + 单位 (30分钟, 1小时)
        r"(\d+(?:\.\d+)?)\s*([a-z\u4e00-\u9fff]+)",
        # 中文数字 + 单位 - 优先匹配"个半"表达
        r"([一二三四五六七八九十几两零]+个半)\s*([a-z\u4e00-\u9fff]+)",  # 优先匹配"一个半"、"两个半"
        r"([一二三四五六七八九十几两半零]+)\s*([a-z\u4e00-\u9fff]+)",   # 标准匹配
    ]
    
    for pattern in patterns:
        match = re.search(pattern, extracted_time)
        if match:
            # 特殊处理刻钟（15分钟）
            if "刻钟" in extracted_time:
                number_text = match.group(1) if match.group(1) else "1"
                number = _parse_chinese_number(number_text) if not number_text.isdigit() else float(number_text)
                total_seconds = int(number * 15 * 60)  # 刻钟 = 15分钟
                logger.bind(tag=TAG).info(f"解析时间: '{duration_text}' -> {number}刻钟 -> {total_seconds}秒")
                return total_seconds
            
            # 特殊处理半小时/半钟头
            if "半小时" in extracted_time or "半钟头" in extracted_time:
                number_text = match.group(1) if match.group(1) else "1"
                number = _parse_chinese_number(number_text) if not number_text.isdigit() else float(number_text)
                total_seconds = int(number * 30 * 60)  # 半小时 = 30分钟
                logger.bind(tag=TAG).info(f"解析时间: '{duration_text}' -> {number}半小时 -> {total_seconds}秒")
                return total_seconds
            
            # 标准处理
            number_text, unit_text = match.groups()
            
            # 解析数字
            if number_text and (number_text.isdigit() or "." in number_text):
                try:
                    number = float(number_text)
                except ValueError:
                    continue
            elif number_text:
                number = _parse_chinese_number(number_text)
            else:
                number = 1.0  # 默认值
            
            # 解析单位
            unit_seconds = None
            for unit_key, seconds in TIME_UNIT_MAPPING.items():
                if unit_key in unit_text:
                    unit_seconds = seconds
                    break
            
            if unit_seconds is not None:
                total_seconds = int(number * unit_seconds)
                logger.bind(tag=TAG).info(f"解析时间: '{duration_text}' -> {number} {unit_text} -> {total_seconds}秒")
                return total_seconds
    
    logger.bind(tag=TAG).warning(f"无法解析的时间表达: {duration_text}")
    return None


def _extract_relative_time_info(user_request: str) -> Dict[str, str]:
    """从用户请求中提取相对时间信息"""
    
    # 常见的相对时间提醒模式
    patterns = [
        # "30分钟后叫我吃饭"
        r"([一二三四五六七八九十半零\d.]+(?:个半)?\s*[分时小时秒钟]+)\s*后\s*(叫我|提醒我|通知我)?\s*(.+)",
        # "1小时后提醒我开会"  
        r"([一二三四五六七八九十半零\d.]+(?:个半)?\s*[分时小时秒钟]+)\s*后\s*(.+)",
        # "过30分钟叫我"
        r"过\s*([一二三四五六七八九十半零\d.]+(?:个半)?\s*[分时小时秒钟]+)\s*(叫我|提醒我|通知我)?\s*(.+)?",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, user_request)
        if match:
            if len(match.groups()) == 3:
                duration, action, content = match.groups()
                # 如果没有明确的内容，使用action作为内容
                if not content and action:
                    content = action.replace("叫我", "").replace("提醒我", "").replace("通知我", "")
                elif not content:
                    content = "时间到了"
            else:
                duration, content = match.groups()
                action = "提醒您"
            
            return {
                "duration_text": duration.strip(),
                "reminder_content": (content or "时间到了").strip(),
                "action_type": action.strip() if action else "提醒您"
            }
    
    return {}


async def _send_reminder_to_device(device_id: str, reminder_content: str, action_type: str = "提醒您"):
    """发送提醒消息到设备"""
    try:
        # 🔧 从全局获取MQTT客户端并初始化统一事件服务
        from core.services.unified_event_service import get_unified_event_service
        from core.mqtt.mqtt_manager import get_global_mqtt_client
        
        mqtt_client = get_global_mqtt_client()
        unified_service = get_unified_event_service(mqtt_client)
        
        if not unified_service or not unified_service.message_queue:
            logger.bind(tag=TAG).error("无法获取消息队列服务")
            return False
        
        # 构建提醒消息 - 更自然的表达
        if action_type == "提醒我" or action_type == "提醒您":
            reminder_message = f"⏰ 时间到了！该{reminder_content}了"
        elif action_type == "叫我" or action_type == "叫您":
            reminder_message = f"⏰ 时间到了！该{reminder_content}了"
        else:
            # 其他情况保持原格式
            reminder_message = f"⏰ 时间到了！{action_type}{reminder_content}"
        
        # 通过消息队列发送提醒（高优先级）- 启用LLM智能处理
        message_id = unified_service.message_queue.add_message(
            device_id=device_id,
            content=reminder_message,
            category="relative_timer_reminder",
            priority=0,  # 最高优先级
            user_info={
                "type": "timer_reminder",  # 🔧 标记为需要LLM处理的定时提醒
                "timer_type": "relative", 
                "reminder_content": reminder_content,
                "action_type": action_type,
                "original_content": reminder_message  # 保留原始内容作为备用
            }
        )
        
        if message_id:
            logger.bind(tag=TAG).info(f"✅ 定时提醒已发送: {device_id}, 消息ID: {message_id}")
            return True
        else:
            logger.bind(tag=TAG).error(f"❌ 定时提醒发送失败: {device_id}")
            return False
            
    except Exception as e:
        logger.bind(tag=TAG).error(f"发送定时提醒异常: {e}")
        return False


async def _timer_task(device_id: str, delay_seconds: int, reminder_content: str, action_type: str, timer_id: str):
    """定时器任务"""
    try:
        logger.bind(tag=TAG).info(f"⏰ 定时器启动: {device_id}, {delay_seconds}秒后提醒'{reminder_content}'")
        
        # 等待指定时间
        await asyncio.sleep(delay_seconds)
        
        # 发送提醒
        success = await _send_reminder_to_device(device_id, reminder_content, action_type)
        
        if success:
            logger.bind(tag=TAG).info(f"🎉 定时提醒完成: {device_id}, {reminder_content}")
        else:
            logger.bind(tag=TAG).error(f"❌ 定时提醒失败: {device_id}, {reminder_content}")
            
    except asyncio.CancelledError:
        logger.bind(tag=TAG).info(f"⏹️ 定时器被取消: {timer_id}")
    except Exception as e:
        logger.bind(tag=TAG).error(f"定时器执行异常: {timer_id}, {e}")
    finally:
        # 清理完成的定时器
        if timer_id in active_timers:
            del active_timers[timer_id]


@register_function("schedule_relative_timer", SCHEDULE_RELATIVE_TIMER_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def schedule_relative_timer(conn, duration_text: str, reminder_content: str, action_type: str = "提醒您"):
    """
    创建相对时间定时提醒
    
    Args:
        conn: 连接对象，包含设备信息
        duration_text: 相对时间表达，如"30分钟"、"1小时"等
        reminder_content: 提醒内容，如"吃饭"、"开会"等  
        action_type: 提醒动作类型，如"叫我"、"提醒我"等
    
    Returns:
        ActionResponse: 包含操作结果和响应消息
    """
    logger.bind(tag=TAG).info(f"收到相对时间定时请求: {duration_text}后{action_type}{reminder_content}")
    
    try:
        # 获取设备ID
        device_id = getattr(conn, 'device_id', None)
        if not device_id:
            return ActionResponse(
                Action.RESPONSE,
                "抱歉，无法识别您的设备，无法设置定时提醒。",
                None
            )
        
        # 解析时间
        delay_seconds = _parse_duration(duration_text)
        if delay_seconds is None:
            return ActionResponse(
                Action.RESPONSE,
                f"抱歉，我无法理解'{duration_text}'这个时间表达，请使用'30分钟'或'1小时'这样的格式。",
                None
            )
        
        # 检查时间范围合理性（最短1分钟，最长24小时）
        if delay_seconds < 60:
            return ActionResponse(
                Action.RESPONSE,
                "定时提醒至少需要1分钟以上，请重新设置。",
                None
            )
        
        if delay_seconds > 86400:  # 24小时
            return ActionResponse(
                Action.RESPONSE,
                "定时提醒最长不能超过24小时，建议使用日程安排功能。",
                None
            )
        
        # 生成定时器ID
        timer_id = f"{device_id}_{int(datetime.now().timestamp())}_{len(active_timers)}"
        
        # 创建定时器任务
        timer_task = asyncio.create_task(
            _timer_task(device_id, delay_seconds, reminder_content, action_type, timer_id)
        )
        
        # 保存到活跃定时器列表
        active_timers[timer_id] = timer_task
        
        # 计算预计提醒时间
        target_time = datetime.now() + timedelta(seconds=delay_seconds)
        time_str = target_time.strftime("%H:%M")
        
        # 🎯 注册定时器信息到管理系统
        try:
            from plugins_func.functions.manage_relative_timers import register_timer_info
            time_desc = _format_duration_description(delay_seconds)
            register_timer_info(timer_id, device_id, reminder_content, action_type, 
                               target_time, time_desc, "relative")
        except ImportError:
            logger.bind(tag=TAG).debug("定时器管理系统未加载，跳过注册")
        except Exception as e:
            logger.bind(tag=TAG).warning(f"注册定时器信息失败: {e}")
        
        # 生成确认回复
        time_desc = _format_duration_description(delay_seconds)
        confirmation_prompt = (
            f"用户设置了相对时间定时提醒：'{duration_text}后{action_type}{reminder_content}'。"
            f"系统已成功创建定时器，将在{time_desc}后（预计{time_str}）提醒用户{reminder_content}。"
            f"请给用户一个友好的确认回复，告诉用户定时提醒已设置成功。"
        )
        
        logger.bind(tag=TAG).info(f"✅ 定时器创建成功: {timer_id}, {delay_seconds}秒后提醒")
        
        return ActionResponse(Action.REQLLM, confirmation_prompt, None)
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"创建相对时间定时器失败: {e}")
        return ActionResponse(
            Action.RESPONSE,
            "抱歉，设置定时提醒时遇到了系统错误，请稍后再试。",
            None
        )


def _format_duration_description(seconds: int) -> str:
    """格式化时间描述"""
    if seconds < 3600:  # 小于1小时
        minutes = seconds // 60
        return f"{minutes}分钟"
    else:  # 大于等于1小时
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes == 0:
            return f"{hours}小时"
        else:
            return f"{hours}小时{remaining_minutes}分钟"


def get_active_timers_status() -> Dict[str, Any]:
    """获取当前活跃定时器状态"""
    status = {
        "total_active": len(active_timers),
        "timers": []
    }
    
    for timer_id, task in active_timers.items():
        timer_info = {
            "timer_id": timer_id,
            "is_running": not task.done(),
            "is_cancelled": task.cancelled()
        }
        status["timers"].append(timer_info)
    
    return status


def cancel_timer(timer_id: str) -> bool:
    """取消指定的定时器"""
    if timer_id in active_timers:
        task = active_timers[timer_id]
        task.cancel()
        del active_timers[timer_id]
        logger.bind(tag=TAG).info(f"定时器已取消: {timer_id}")
        return True
    return False


def cancel_all_device_timers(device_id: str) -> int:
    """取消指定设备的所有定时器"""
    cancelled_count = 0
    timer_ids_to_remove = []
    
    for timer_id, task in active_timers.items():
        if timer_id.startswith(device_id):
            task.cancel()
            timer_ids_to_remove.append(timer_id)
            cancelled_count += 1
    
    for timer_id in timer_ids_to_remove:
        del active_timers[timer_id]
    
    if cancelled_count > 0:
        logger.bind(tag=TAG).info(f"已取消设备 {device_id} 的 {cancelled_count} 个定时器")
    
    return cancelled_count

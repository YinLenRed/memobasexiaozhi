from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.tools.java_backend_strategy import JavaBackendStrategyService
import asyncio
import re

TAG = __name__
logger = setup_logging()

SAVE_USER_STRATEGY_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "save_user_strategy",
        "description": (
            "保存用户策略或任务安排，适用于绝对时间和周期性定时任务。"
            "例如：'明天八点叫我起床'、'下午三点提醒我开会'、'每天晚上九点提醒我吃药'等。"
            "注意：不处理相对时间表达（如'X分钟后'、'X小时后'），这类请求请使用schedule_relative_timer功能。"
            "该功能会将用户的策略保存到系统中，以便后续执行相关操作。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "用户的完整策略或任务请求，例如：'明天八点叫我起床'",
                },
                "task_type": {
                    "type": "string",
                    "description": "任务类型，如：reminder（提醒）、alarm（闹钟）、notification（通知）、meeting（会议）等。可选参数",
                    "enum": ["reminder", "alarm", "notification", "meeting", "medicine", "birthday", "other"]
                }
            },
            "required": ["user_request"],
        },
    },
}


def _is_time_specific(text: str, conn=None) -> dict:
    """检查时间是否明确"""
    
    # 🚨 相对时间检测 - 这些应该由 schedule_relative_timer 处理
    relative_time_patterns = [
        # 标准相对时间表达
        r'([一二三四五六七八九十几半\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))\s*(?:之?后|以后|过后)',  # 一个小时后、30分钟后、半小时之后
        r'过\s*([一二三四五六七八九十几半\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))',     # 过一个小时、过30分钟
        r'([一二三四五六七八九十几半\d.]+(?:个)?\s*[分时小时秒钟]+)\s*(?:后|之后)',  # 兼容原有模式
        
        # 拓展表达方式
        r'等\s*([一二三四五六七八九十几半\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))\s*(?:再|就|后)?',  # 等30分钟再、等1小时就
        r'([一二三四五六七八九十几半\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))\s*(?:内|以内)',  # 30分钟内、1小时内
        r'再\s*(?:过\s*)?([一二三四五六七八九十几半\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))',  # 再过30分钟、再1小时
        r'([一二三四五六七八九十几半\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))\s*(?:后面|以后|之后)',  # 30分钟后面
        r'隔\s*([一二三四五六七八九十几半\d.]+(?:个)?\s*(?:小?时间?|分钟?|秒钟?|小时))',  # 隔30分钟、隔1小时
        
        # 常用口语表达
        r'([一二三四五六七八九十几两半\d.]+)\s*(?:个)?\s*(?:钟头|小时)\s*(?:之?后|以后|过后)',  # 1个钟头后、两小时后
        r'([一二三四五六七八九十几两\d.]+)\s*刻钟\s*(?:之?后|以后)',  # 1刻钟后、两刻钟后 (15分钟)
        r'([一二三四五六七八九十几两\d.]+)\s*(?:个)?\s*(?:半小时|半钟头)\s*(?:之?后|以后)',  # 1个半小时后
        
        # 数字 + 时间单位的各种组合
        r'([0-9]+(?:\.[0-9]+)?)\s*(?:个)?\s*(?:小时|钟头|时|h)\s*(?:之?后|以后|过后)',  # 1.5小时后、2h后
        r'([0-9]+(?:\.[0-9]+)?)\s*(?:分钟?|分|min|m)\s*(?:之?后|以后|过后)',  # 30分后、45min后
    ]
    
    for pattern in relative_time_patterns:
        match = re.search(pattern, text)
        if match:
            # 临时处理相对时间（直到服务重启加载新函数）
            logger.bind(tag=TAG).info(f"检测到相对时间表达: {text}")
            try:
                # 尝试直接处理相对时间
                return _handle_relative_timer_temporarily(conn, text)
            except Exception as e:
                logger.bind(tag=TAG).error(f"临时处理相对时间失败: {e}")
                return {
                    "is_specific": False, 
                    "reason": "这是相对时间表达，但处理失败",
                    "suggestion": "抱歉，相对时间功能暂时不可用，请使用'明天上午9点'这样的绝对时间。"
                }
    
    # 明确时间模式 - 只有这些才算明确时间
    specific_time_patterns = [
        r'\d{1,2}:\d{2}',                    # 14:30
        r'\d{1,2}点\d{1,2}分',               # 8点30分
        r'\d{1,2}点半',                      # 8点半  
        r'\d{1,2}点',                        # 8点
        r'(\d{1,2})[时]',                    # 8时
        r'[一二三四五六七八九十两]+点',       # 三点、八点、两点
        r'[一二三四五六七八九十两]+时',       # 三时、八时、两时
        r'(\d{4})年(\d{1,2})月(\d{1,2})日',  # 2024年3月15日
        r'(\d{1,2})月(\d{1,2})日',           # 3月15日
    ]
    
    # 模糊时间模式 - 这些需要进一步确认
    vague_time_patterns = [
        r'(早上|上午|中午|下午|晚上|夜里|凌晨)(?!.*[一二三四五六七八九十两\d]+[点时:])',  # 只有时段没有具体时间
        r'(明天|后天|大后天)(?!.*[一二三四五六七八九十两\d]+[点时:])',                  # 只有日期没有具体时间  
        r'(下周|下个月|下个星期)',                                    # 模糊未来时间
        r'(这周|这个月|本周|本月)',                                  # 模糊当前时间
        r'(周\d|星期\d)(?!.*[一二三四五六七八九十两\d]+[点时:])',                      # 只有星期没有具体时间
    ]
    
    # 检查是否有明确的时间点
    for pattern in specific_time_patterns:
        if re.search(pattern, text):
            return {"is_specific": True, "reason": "包含明确的时间点"}
    
    # 检查是否有模糊时间表达
    for pattern in vague_time_patterns:
        match = re.search(pattern, text)
        if match:
            vague_expression = match.group(1)
            
            # 生成针对性的询问建议
            if vague_expression in ["早上", "上午"]:
                suggestion = "请问您希望在早上几点呢？比如7点、8点还是9点？"
            elif vague_expression in ["下午"]:
                suggestion = "请问您希望在下午几点呢？比如1点、3点还是5点？"
            elif vague_expression in ["晚上"]:
                suggestion = "请问您希望在晚上几点呢？比如7点、8点还是9点？"
            elif vague_expression in ["明天", "后天"]:
                suggestion = "请问您希望在具体什么时间呢？比如'明天上午9点'？"
            elif vague_expression in ["下周", "下个月"]:
                suggestion = f"请问您希望在{vague_expression}的具体哪一天、什么时间呢？"
            else:
                suggestion = "请问您希望在具体什么时间呢？比如'明天下午3点'？"
                
            return {
                "is_specific": False, 
                "reason": f"时间表达模糊：'{vague_expression}'",
                "suggestion": suggestion
            }
    
    # 包含提醒关键词但没有明确时间信息
    task_keywords = ["提醒", "叫我", "记得", "别忘了", "通知我"]
    if any(keyword in text for keyword in task_keywords):
        return {
            "is_specific": False,
            "reason": "包含任务但缺少时间信息", 
            "suggestion": "请问您希望在什么时候提醒您呢？比如'明天下午2点'？"
        }
    
    return {"is_specific": True, "reason": "无明确时间信息但可能不需要定时"}


@register_function("save_user_strategy", SAVE_USER_STRATEGY_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def save_user_strategy(conn, user_request: str, task_type: str = "other"):
    """
    保存用户策略到Java后端系统
    
    Args:
        conn: 连接对象，包含设备信息
        user_request: 用户的完整策略请求
        task_type: 任务类型（可选）
    
    Returns:
        ActionResponse: 包含操作结果和响应消息
    """
    logger.bind(tag=TAG).info(f"收到用户策略保存请求: {user_request}, 任务类型: {task_type}")
    
    # 🎯 时间明确性检查
    time_check = _is_time_specific(user_request, conn)
    
    # 🚨 优先检查相对时间处理结果，避免重复提醒
    if "timer_info" in time_check and "已设置" in time_check.get("reason", ""):
        # 相对时间处理成功，生成确认回复，不保存到Java后端
        timer_info = time_check["timer_info"]
        confirmation_prompt = (
            f"用户设置了相对时间定时提醒：'{user_request}'。"
            f"系统已成功创建定时器，将在{timer_info['duration']}后（预计{timer_info['target_time']}）"
            f"{timer_info['action']}{timer_info['content']}。"
            f"请给用户一个友好的确认回复，告诉用户定时提醒已设置成功。"
        )
        logger.bind(tag=TAG).info(f"🎯 相对时间定时设置成功，跳过Java保存避免重复: {timer_info['duration']}后{timer_info['content']}")
        return ActionResponse(Action.REQLLM, confirmation_prompt, None)
    
    if not time_check["is_specific"]:
        logger.bind(tag=TAG).info(f"时间检查结果: {time_check['reason']}")
        # 其他情况，返回询问消息
        inquiry_prompt = f"用户说：'{user_request}'。时间不够明确（{time_check['reason']}）。请直接回复用户：{time_check['suggestion']}"
        logger.bind(tag=TAG).info(f"返回时间确认询问prompt: {inquiry_prompt}")
        return ActionResponse(Action.REQLLM, inquiry_prompt, None)
    
    try:
        # 检查是否配置了Java后端API
        if not conn.config.get("manager-api", {}).get("url"):
            logger.bind(tag=TAG).warning("未配置Java后端API，无法保存用户策略")
            return ActionResponse(
                Action.RESPONSE, 
                "抱歉，系统暂未配置策略保存功能，无法保存您的请求。", 
                None
            )
        
        # 创建Java后端策略服务
        strategy_service = JavaBackendStrategyService(conn.config)
        
        # 异步后台处理用户策略请求（不阻塞用户回复）
        def background_save_strategy():
            """后台异步保存策略，不影响用户体验"""
            try:
                future = asyncio.run_coroutine_threadsafe(
                    strategy_service.save_user_strategy(
                        getattr(conn, 'device_id', 'unknown'),
                        strategy_service._parse_user_input(user_request)["title"],
                        user_request
                    ),
                    conn.loop
                )
                result = future.result(timeout=15)
                if result["success"]:
                    logger.bind(tag=TAG).info(f"后台策略保存成功: {user_request[:30]}...")
                else:
                    logger.bind(tag=TAG).error(f"后台策略保存失败: {result['message']}")
            except Exception as e:
                logger.bind(tag=TAG).error(f"后台策略保存异常: {e}")
        
        # 启动后台保存任务
        import threading
        threading.Thread(target=background_save_strategy, daemon=True).start()
        logger.bind(tag=TAG).info(f"已启动后台策略保存任务: {user_request[:30]}...")
        
        # 立即返回让LLM生成确认回复，告诉LLM这个策略已经被接收和处理
        confirmation_prompt = f"用户说：'{user_request}'。我已经成功接收并保存了这个策略任务，系统会按照要求执行。请给用户一个友好、简洁的确认回复，表示已经记住了这个任务。"
        return ActionResponse(Action.REQLLM, confirmation_prompt, None)
    
    except Exception as e:
        logger.bind(tag=TAG).error(f"保存用户策略功能异常: {e}")
        return ActionResponse(
            Action.RESPONSE, 
            "抱歉，保存策略时遇到了系统错误，请稍后再试。", 
            None
        )


def _extract_task_info(user_request: str) -> dict:
    """
    从用户请求中提取任务信息
    这是一个辅助函数，用于更好地解析用户的策略请求
    """
    task_info = {
        "type": "other",
        "time": None,
        "content": user_request,
        "keywords": []
    }
    
    # 关键词匹配
    if any(keyword in user_request for keyword in ["提醒", "叫我", "通知我"]):
        task_info["type"] = "reminder"
        task_info["keywords"].append("提醒")
    
    if any(keyword in user_request for keyword in ["闹钟", "起床"]):
        task_info["type"] = "alarm"
        task_info["keywords"].append("闹钟")
    
    if any(keyword in user_request for keyword in ["会议", "开会"]):
        task_info["type"] = "meeting"
        task_info["keywords"].append("会议")
    
    if "吃药" in user_request:
        task_info["type"] = "medicine"
        task_info["keywords"].append("吃药")
    
    if "生日" in user_request:
        task_info["type"] = "birthday"
        task_info["keywords"].append("生日")
    
    # 时间提取（简单匹配）
    time_keywords = ["明天", "后天", "今天", "下午", "上午", "晚上", "点", "时"]
    for keyword in time_keywords:
        if keyword in user_request:
            task_info["keywords"].append(keyword)
    
    return task_info


# ========== 临时相对时间处理函数（直到服务重启加载新函数） ==========

import asyncio
from datetime import datetime, timedelta

# 时间单位映射（中文到秒数）
TEMP_TIME_UNIT_MAPPING = {
    # 分钟
    "分钟": 60, "分": 60, "min": 60, "minute": 60, "minutes": 60, "m": 60,
    # 小时  
    "小时": 3600, "时": 3600, "钟头": 3600, "时间": 3600, "hour": 3600, "hours": 3600, "h": 3600,
    # 秒
    "秒钟": 1, "秒": 1, "sec": 1, "second": 1, "seconds": 1, "s": 1,
}

# 中文数字映射  
TEMP_CHINESE_NUMBERS = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "两": 2, "半": 0.5, "零": 0, "几": 3,  # "几"默认为3
    "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
    "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
    "三十": 30, "四十": 40, "五十": 50, "六十": 60,
    "一个": 1, "两个": 2, "三个": 3, "四个": 4, "五个": 5,
    "1个": 1, "2个": 2, "3个": 3, "4个": 4, "5个": 5,
}

# 全局定时器字典
temp_active_timers = {}


def _temp_parse_chinese_number(text: str) -> float:
    """临时解析中文数字"""
    text = text.strip()
    if text.isdigit():
        return float(text)
    try:
        return float(text)
    except ValueError:
        pass
    if text in TEMP_CHINESE_NUMBERS:
        return TEMP_CHINESE_NUMBERS[text]
    if "个半" in text:
        base_text = text.replace("个半", "")
        if base_text in TEMP_CHINESE_NUMBERS:
            return TEMP_CHINESE_NUMBERS[base_text] + 0.5
    return 1.0


def _temp_parse_duration(duration_text: str) -> int:
    """临时解析相对时间表达"""
    duration_text = duration_text.strip().lower()
    
    # 🎯 特殊处理"半个X"的情况
    if "半个" in duration_text:
        # 半个小时 = 0.5小时 = 30分钟
        if "小时" in duration_text or "钟头" in duration_text:
            return 30 * 60
        elif "分钟" in duration_text or "分" in duration_text:
            return 30
    
    patterns = [
        # 数字模式
        r"(\d+(?:\.\d+)?)\s*([a-z\u4e00-\u9fff]+)",
        # 扩展的中文数字模式
        r"([一二三四五六七八九十几两半零]+(?:个半|个)?)\s*([a-z\u4e00-\u9fff]+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, duration_text)
        if match:
            number_text, unit_text = match.groups()
            
            if number_text.isdigit() or "." in number_text:
                try:
                    number = float(number_text)
                except ValueError:
                    continue
            else:
                number = _temp_parse_chinese_number(number_text)
            
            unit_seconds = None
            for unit_key, seconds in TEMP_TIME_UNIT_MAPPING.items():
                if unit_key in unit_text:
                    unit_seconds = seconds
                    break
            
            if unit_seconds is not None:
                total_seconds = int(number * unit_seconds)
                logger.bind(tag=TAG).info(f"临时解析时间: '{duration_text}' -> {total_seconds}秒")
                return total_seconds
    
    logger.bind(tag=TAG).warning(f"无法解析的时间表达: {duration_text}")
    return None


def _temp_extract_relative_time_info(user_request: str) -> dict:
    """临时提取相对时间信息"""
    logger.bind(tag=TAG).info(f"🔍 提取相对时间信息: {user_request}")
    
    # 🎯 修复的提取模式 - 针对"两分钟后提醒我喝水"格式优化
    extraction_patterns = [
        # 标准格式：数字+时间单位+后+动作+内容
        r'([一二三四五六七八九十几半两\d.]+(?:个)?)\s*(?:分钟|分)\s*后\s*(叫我|提醒我|通知我)?\s*(.+)',  # "两分钟后提醒我喝水"
        r'([一二三四五六七八九十几半两\d.]+(?:个)?)\s*(?:小时|钟头|时)\s*后\s*(叫我|提醒我|通知我)?\s*(.+)',  # "两小时后提醒我"
        r'([一二三四五六七八九十几半两\d.]+(?:个)?)\s*(?:秒钟|秒)\s*后\s*(叫我|提醒我|通知我)?\s*(.+)',  # "十秒后提醒我"
        
        # 带"之"的表达
        r'([一二三四五六七八九十几半两\d.]+(?:个)?)\s*(?:分钟|分)\s*之后\s*(叫我|提醒我|通知我)?\s*(.+)', 
        r'([一二三四五六七八九十几半两\d.]+(?:个)?)\s*(?:小时|钟头|时)\s*之后\s*(叫我|提醒我|通知我)?\s*(.+)',
        r'([一二三四五六七八九十几半两\d.]+(?:个)?)\s*(?:秒钟|秒)\s*之后\s*(叫我|提醒我|通知我)?\s*(.+)',
        
        # 数字格式
        r'([0-9]+(?:\.[0-9]+)?)\s*(?:分钟|分)\s*后\s*(叫我|提醒我|通知我)?\s*(.+)',  # "30分钟后提醒我"
        r'([0-9]+(?:\.[0-9]+)?)\s*(?:小时|时|h)\s*后\s*(叫我|提醒我|通知我)?\s*(.+)',  # "1.5小时后"
        r'([0-9]+(?:\.[0-9]+)?)\s*(?:秒钟|秒|s)\s*后\s*(叫我|提醒我|通知我)?\s*(.+)',  # "60秒后"
        
        # 其他表达方式
        r'等\s*([一二三四五六七八九十几半两\d.]+(?:个)?\s*(?:分钟|分|小时|时|秒))\s*(?:再|后)?\s*(叫我|提醒我|通知我)?\s*(.+)?',
        r'再\s*([一二三四五六七八九十几半两\d.]+(?:个)?\s*(?:分钟|分|小时|时|秒))\s*(?:后)?\s*(叫我|提醒我|通知我)?\s*(.+)?',
    ]
    
    for pattern in extraction_patterns:
        match = re.search(pattern, user_request)
        if match:
            logger.bind(tag=TAG).info(f"🎯 匹配成功: {match.groups()}")
            
            if len(match.groups()) == 3:
                duration, action, content = match.groups()
                
                # 处理动作词
                if action:
                    if "叫我" in action:
                        action_type = "叫您"
                    elif "提醒我" in action:
                        action_type = "提醒您"
                    elif "通知我" in action:
                        action_type = "通知您"
                    else:
                        action_type = "提醒您"
                else:
                    action_type = "提醒您"
                
                # 处理内容
                if not content:
                    content = "时间到了"
                
            else:
                duration, content = match.groups()
                action_type = "提醒您"
                if not content:
                    content = "时间到了"
            
            result = {
                "duration_text": duration.strip(),
                "reminder_content": (content or "时间到了").strip(),
                "action_type": action_type
            }
            
            logger.bind(tag=TAG).info(f"✅ 提取结果: {result}")
            return result
    
    return {}


async def _temp_send_reminder_to_device(device_id: str, reminder_content: str, action_type: str = "提醒您"):
    """临时发送提醒消息到设备"""
    try:
        from core.services.unified_event_service import get_unified_event_service
        unified_service = get_unified_event_service()
        
        if not unified_service or not unified_service.message_queue:
            logger.bind(tag=TAG).error("无法获取消息队列服务")
            return False
        
        reminder_message = f"⏰ 时间到了！{action_type}{reminder_content}"
        
        message_id = unified_service.message_queue.add_message(
            device_id=device_id,
            content=reminder_message,
            category="temp_relative_timer_reminder",
            priority=0,
            user_info={"timer_type": "temp_relative", "reminder_content": reminder_content}
        )
        
        if message_id:
            logger.bind(tag=TAG).info(f"✅ 临时定时提醒已发送: {device_id}, 消息ID: {message_id}")
            return True
        else:
            logger.bind(tag=TAG).error(f"❌ 临时定时提醒发送失败: {device_id}")
            return False
            
    except Exception as e:
        logger.bind(tag=TAG).error(f"发送临时定时提醒异常: {e}")
        return False


async def _temp_timer_task(device_id: str, delay_seconds: int, reminder_content: str, action_type: str, timer_id: str):
    """临时定时器任务"""
    try:
        logger.bind(tag=TAG).info(f"⏰ 临时定时器启动: {device_id}, {delay_seconds}秒后提醒'{reminder_content}'")
        
        await asyncio.sleep(delay_seconds)
        
        success = await _temp_send_reminder_to_device(device_id, reminder_content, action_type)
        
        if success:
            logger.bind(tag=TAG).info(f"🎉 临时定时提醒完成: {device_id}, {reminder_content}")
        else:
            logger.bind(tag=TAG).error(f"❌ 临时定时提醒失败: {device_id}, {reminder_content}")
            
    except asyncio.CancelledError:
        logger.bind(tag=TAG).info(f"⏹️ 临时定时器被取消: {timer_id}")
    except Exception as e:
        logger.bind(tag=TAG).error(f"临时定时器执行异常: {timer_id}, {e}")
    finally:
        if timer_id in temp_active_timers:
            del temp_active_timers[timer_id]


def _handle_relative_timer_temporarily(conn, user_request: str) -> dict:
    """临时处理相对时间定时请求"""
    logger.bind(tag=TAG).info(f"临时处理相对时间定时: {user_request}")
    
    # 提取相对时间信息
    time_info = _temp_extract_relative_time_info(user_request)
    if not time_info:
        return {
            "is_specific": False,
            "reason": "无法解析相对时间表达",
            "suggestion": "请使用'30分钟后'、'1小时后'这样的格式。"
        }
    
    # 解析时间
    delay_seconds = _temp_parse_duration(time_info['duration_text'])
    if delay_seconds is None:
        return {
            "is_specific": False,
            "reason": "无法解析时间长度",
            "suggestion": "请使用'30分钟后'、'1小时后'这样的格式。"
        }
    
    # 检查时间范围
    if delay_seconds < 60:
        return {
            "is_specific": False,
            "reason": "时间过短",
            "suggestion": "定时提醒至少需要1分钟以上。"
        }
    
    if delay_seconds > 86400:
        return {
            "is_specific": False,
            "reason": "时间过长",
            "suggestion": "定时提醒最长不能超过24小时。"
        }
    
    # 获取设备ID
    device_id = getattr(conn, 'device_id', None)
    if not device_id:
        return {
            "is_specific": False,
            "reason": "无法获取设备ID",
            "suggestion": "无法识别您的设备。"
        }
    
    # 创建定时器
    timer_id = f"temp_{device_id}_{int(datetime.now().timestamp())}"
    
    try:
        timer_task = asyncio.create_task(
            _temp_timer_task(
                device_id, 
                delay_seconds, 
                time_info['reminder_content'], 
                time_info['action_type'], 
                timer_id
            )
        )
        
        temp_active_timers[timer_id] = timer_task
        
        # 计算预计提醒时间
        target_time = datetime.now() + timedelta(seconds=delay_seconds)
        time_str = target_time.strftime("%H:%M")
        
        # 生成时间描述
        if delay_seconds < 3600:
            time_desc = f"{delay_seconds // 60}分钟"
        else:
            hours = delay_seconds // 3600
            remaining_minutes = (delay_seconds % 3600) // 60
            time_desc = f"{hours}小时{remaining_minutes}分钟" if remaining_minutes > 0 else f"{hours}小时"
        
        # 🎯 注册临时定时器信息到管理系统
        try:
            from plugins_func.functions.manage_relative_timers import register_timer_info
            register_timer_info(timer_id, device_id, time_info['reminder_content'], 
                               time_info['action_type'], target_time, time_desc, "temp_relative")
        except ImportError:
            logger.bind(tag=TAG).debug("定时器管理系统未加载，跳过注册")
        except Exception as e:
            logger.bind(tag=TAG).warning(f"注册临时定时器信息失败: {e}")
        
        logger.bind(tag=TAG).info(f"✅ 临时定时器创建成功: {timer_id}, {delay_seconds}秒后提醒")
        
        # 返回成功，让 save_user_strategy 生成确认回复
        return {
            "is_specific": True,
            "reason": f"已设置{time_desc}后的提醒",
            "timer_info": {
                "duration": time_desc,
                "target_time": time_str,
                "content": time_info['reminder_content'],
                "action": time_info['action_type']
            }
        }
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"创建临时定时器失败: {e}")
        return {
            "is_specific": False,
            "reason": "创建定时器失败",
            "suggestion": "系统错误，请稍后再试。"
        }

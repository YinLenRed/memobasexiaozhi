from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.tools.java_backend_strategy import JavaBackendStrategyService
import asyncio

TAG = __name__
logger = setup_logging()

QUERY_USER_STRATEGIES_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "query_user_strategies",
        "description": (
            "查询用户的定时策略或任务安排。当用户询问自己设置了哪些提醒、查看任务列表、"
            "查询定时安排等时使用此功能。例如：'我设置了什么提醒'、'查看我的任务列表'、"
            "'显示所有定时任务'、'我有哪些闹钟'等。可以按设备ID、任务名称、状态等条件进行筛选。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "设备ID，用于筛选特定设备的策略。可选参数，不填则查询所有设备",
                },
                "job_name": {
                    "type": "string", 
                    "description": "任务名称，用于模糊搜索特定名称的任务。可选参数",
                },
                "status": {
                    "type": "string",
                    "description": "任务状态筛选：0-正常运行，1-已暂停。可选参数",
                    "enum": ["0", "1"]
                },
                "page": {
                    "type": "integer",
                    "description": "页码，默认第1页",
                    "default": 1
                },
                "page_size": {
                    "type": "integer", 
                    "description": "每页条数，默认10条",
                    "default": 10
                }
            },
            "required": [],
        },
    },
}


@register_function("query_user_strategies", QUERY_USER_STRATEGIES_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def query_user_strategies(conn, device_id: str = None, job_name: str = None, 
                         status: str = None, page: int = 1, page_size: int = 10):
    """
    查询用户策略列表
    
    Args:
        conn: 连接对象，包含设备信息和配置
        device_id: 设备ID筛选条件
        job_name: 任务名称筛选条件 
        status: 任务状态筛选条件
        page: 页码
        page_size: 每页条数
    
    Returns:
        ActionResponse: 包含查询结果和响应消息
    """
    logger.bind(tag=TAG).info(f"收到用户策略查询请求: device_id={device_id}, job_name={job_name}, status={status}")
    
    try:
        # 检查是否配置了Java后端API
        if not conn.config.get("manager-api", {}).get("url"):
            logger.bind(tag=TAG).warning("未配置Java后端API，无法查询用户策略")
            return ActionResponse(
                Action.RESPONSE, 
                result=None, 
                response="抱歉，系统暂未配置策略查询功能，无法查询您的任务列表。"
            )
        
        # 如果没有指定device_id，使用当前连接的设备ID
        query_device_id = device_id if device_id else getattr(conn, 'device_id', None)
        
        # Java后端要求设备ID不能为空，如果没有设备ID则返回错误提示
        if not query_device_id:
            logger.bind(tag=TAG).warning("无法获取设备ID，无法查询策略")
            return ActionResponse(
                Action.RESPONSE, 
                result=None, 
                response="抱歉，无法识别您的设备，请确认设备连接正常后再试。"
            )
        
        # 创建Java后端策略服务
        strategy_service = JavaBackendStrategyService(conn.config)
        
        # 使用线程池执行异步查询，避免事件循环冲突
        import concurrent.futures
        import threading
        
        def run_async_query():
            """在新线程中运行异步查询"""
            try:
                # 在新线程中创建事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        strategy_service.query_user_strategies(
                            device_id=query_device_id,
                            job_name=job_name,
                            status=status,
                            current=page,
                            size=page_size
                        )
                    )
                    logger.bind(tag=TAG).info(f"查询策略完成: success={result.get('success', False)}")
                    return result
                finally:
                    loop.close()
            except Exception as e:
                logger.bind(tag=TAG).error(f"查询策略异常: {e}")
                return {
                    "success": False,
                    "message": f"查询异常: {str(e)}",
                    "data": [],
                    "total": 0
                }
        
        # 在线程池中执行查询
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_async_query)
                result = future.result(timeout=30)  # 30秒超时
        except concurrent.futures.TimeoutError:
            logger.bind(tag=TAG).error("查询策略超时（30秒）")
            result = {
                "success": False,
                "message": "查询超时，请稍后再试",
                "data": [],
                "total": 0
            }
        except Exception as e:
            logger.bind(tag=TAG).error(f"查询策略执行异常: {e}")
            result = {
                "success": False,
                "message": f"查询异常: {str(e)}",
                "data": [],
                "total": 0
            }
        
        if result["success"]:
            strategies = result["data"]
            total = result["total"]
            
            if not strategies or len(strategies) == 0:
                # 没有找到策略
                response_msg = "您目前没有设置任何定时任务。"
            else:
                # 构建完整的任务列表响应
                if total == 1:
                    response_msg = "为您查到1个定时任务：\n"
                else:
                    response_msg = f"为您查到{total}个定时任务：\n"
                
                # 遍历所有任务，提供详细信息
                for i, task in enumerate(strategies, 1):
                    task_name = task.get("jobName", "未知任务")
                    cron_expr = task.get("cronExpression", "")
                    status = task.get("status", 0)
                    status_desc = "运行中" if status == 0 else "已暂停"
                    time_desc = _parse_cron_to_readable(cron_expr)
                    
                    response_msg += f"第{i}个任务：{task_name}，时间是{time_desc}，状态{status_desc}。\n"
                
                # 移除最后的换行符
                response_msg = response_msg.rstrip('\n')
            
            logger.bind(tag=TAG).info(f"策略查询成功，返回{len(strategies)}条记录")
            
            # 🔍 调试日志：输出即将返回的语音内容
            logger.bind(tag=TAG).info(f"🎤 准备返回语音内容: {response_msg[:100]}...")
            logger.bind(tag=TAG).info(f"🎤 语音内容长度: {len(response_msg)}字符")
            
            action_response = ActionResponse(Action.RESPONSE, result=None, response=response_msg)
            logger.bind(tag=TAG).info(f"🎤 ActionResponse构造完成: action={action_response.action}")
            
            return action_response
            
        else:
            error_msg = result["message"]
            logger.bind(tag=TAG).error(f"策略查询失败: {error_msg}")
            return ActionResponse(
                Action.RESPONSE, 
                result=None, 
                response=f"查询任务列表时遇到问题：{error_msg}，请稍后再试。"
            )
    
    except Exception as e:
        logger.bind(tag=TAG).error(f"查询用户策略功能异常: {e}")
        return ActionResponse(
            Action.RESPONSE, 
            result=None, 
            response="抱歉，查询任务列表时遇到了系统错误，请稍后再试。"
        )


def _parse_cron_to_readable(cron_expr: str) -> str:
    """将cron表达式转换为用户可读的时间描述"""
    try:
        if not cron_expr or cron_expr.strip() == "":
            return "未设置时间"
        
        parts = cron_expr.strip().split()
        if len(parts) < 6:
            return f"表达式：{cron_expr}"
        
        second, minute, hour, day, month, weekday = parts[:6]
        
        # 解析小时和分钟
        hour_desc = f"{hour}点" if hour != "*" else "每小时"
        minute_desc = f"{minute}分" if minute != "0" else ""
        time_part = hour_desc + minute_desc
        
        # 解析频率
        if day == "*" and month == "*" and weekday == "?":
            return f"每天{time_part}"
        elif day == "?" and month == "*" and weekday != "*":
            weekdays = {"1": "周一", "2": "周二", "3": "周三", "4": "周四", 
                       "5": "周五", "6": "周六", "7": "周日"}
            weekday_desc = weekdays.get(weekday, f"星期{weekday}")
            return f"每{weekday_desc}{time_part}"
        elif day != "*" and month != "*":
            return f"{month}月{day}日{time_part}（一次性）"
        else:
            return f"表达式：{cron_expr}"
            
    except Exception:
        return f"表达式：{cron_expr}"

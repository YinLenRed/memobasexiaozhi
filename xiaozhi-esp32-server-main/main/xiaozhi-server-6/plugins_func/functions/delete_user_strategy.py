from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.tools.java_backend_strategy import JavaBackendStrategyService
import asyncio

TAG = __name__
logger = setup_logging()

DELETE_USER_STRATEGY_FUNCTION_DESC = {
    "type": "function", 
    "function": {
        "name": "delete_user_strategy",
        "description": (
            "删除用户的定时策略或任务安排。当用户要求删除、取消已有的提醒或任务时使用此功能。"
            "例如：'删除明天8点的闹钟'、'取消这个提醒'、'删除任务'等。需要指定任务ID。"
            "为了安全起见，建议先通过查询功能确认要删除的任务信息。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": "要删除的任务描述，如'明天8点的闹钟'、'下午3点的会议提醒'等。系统会自动匹配对应的任务。如果知道具体任务ID，也可以直接提供job_id",
                },
                "job_id": {
                    "type": "integer",
                    "description": "要删除的任务ID。可选参数，如果不知道具体ID，可以用task_description来描述任务，系统会自动匹配",
                },
                "job_name": {
                    "type": "string",
                    "description": "任务名称，用于确认删除的任务。可选参数，建议提供以增加安全性",
                },
                "device_id": {
                    "type": "string",
                    "description": "设备ID。可选参数，用于额外验证",
                },
                "confirm_delete": {
                    "type": "boolean",
                    "description": "确认删除标志。建议设为true以确认用户真的想要删除",
                    "default": True
                }
            },
            "required": [],  # 不再强制要求job_id
        },
    },
}


@register_function("delete_user_strategy", DELETE_USER_STRATEGY_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def delete_user_strategy(conn, task_description: str = None, job_id: int = None, job_name: str = None, 
                        device_id: str = None, cron_expression: str = None, 
                        confirm_delete: bool = True):
    """
    删除用户策略
    
    Args:
        conn: 连接对象，包含设备信息和配置
        job_id: 要删除的任务ID
        job_name: 任务名称（用于确认）
        device_id: 设备ID
        cron_expression: cron表达式（可选）
        confirm_delete: 确认删除标志
    
    Returns:
        ActionResponse: 包含删除结果和响应消息
    """
    logger.bind(tag=TAG).info(f"收到用户策略删除请求: task_description={task_description}, job_id={job_id}, job_name={job_name}, confirm={confirm_delete}")
    
    try:
        # 检查是否配置了Java后端API
        if not conn.config.get("manager-api", {}).get("url"):
            logger.bind(tag=TAG).warning("未配置Java后端API，无法删除用户策略")
            return ActionResponse(
                Action.RESPONSE, 
                "抱歉，系统暂未配置策略删除功能，无法删除您的任务。", 
                None
            )
        
        # 创建Java后端策略服务
        strategy_service = JavaBackendStrategyService(conn.config)
        
        # 使用当前设备ID（如果没有指定）
        delete_device_id = device_id if device_id else getattr(conn, 'device_id', None)
        
        # Java后端要求设备ID不能为空
        if not delete_device_id:
            logger.bind(tag=TAG).warning("无法获取设备ID，无法删除策略")
            return ActionResponse(
                Action.RESPONSE, 
                "抱歉，无法识别您的设备，请确认设备连接正常后再试。", 
                None
            )
        
        # Java后端要求cron表达式不能为空，如果没有提供，在异步调用中查询获取
        delete_cron_expression = cron_expression if cron_expression else "0 0 8 * * ?"

        
        # 🔍 智能任务匹配（支持多任务场景）
        actual_job_id = job_id
        if not actual_job_id and task_description:
            logger.bind(tag=TAG).info(f"🔍 开始智能匹配要删除的任务: {task_description}")
            try:
                # 简化的任务查询 - 避免复杂的异步调用
                def get_all_tasks():
                    try:
                        logger.bind(tag=TAG).info("开始查询任务列表...")
                        
                        # 使用现有的strategy_service，但采用更安全的调用方式
                        import asyncio
                        import concurrent.futures
                        
                        async def safe_query():
                            try:
                                return await strategy_service.query_user_strategies(device_id=delete_device_id, size=50)
                            except Exception as e:
                                logger.bind(tag=TAG).error(f"异步查询失败: {e}")
                                return None
                        
                        # 使用线程池执行异步任务，避免事件循环冲突
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, safe_query())
                            try:
                                result = future.result(timeout=8)  # 8秒超时
                                logger.bind(tag=TAG).info(f"查询任务完成，结果: {result is not None}")
                                return result
                            except concurrent.futures.TimeoutError:
                                logger.bind(tag=TAG).warning("查询任务超时")
                                return None
                            except Exception as e:
                                logger.bind(tag=TAG).error(f"查询任务异常: {e}")
                                return None
                                
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"查询任务失败: {e}")
                        return None
                
                query_result = get_all_tasks()
                logger.bind(tag=TAG).info(f"🔍 查询结果: {query_result}")
                
                # 兼容两种数据结构
                if not query_result:
                    logger.bind(tag=TAG).warning("查询结果为空")
                    return ActionResponse(
                        Action.RESPONSE,
                        "无法查询任务列表，请稍后再试。",
                        None
                    )
                
                # 检查是否成功 - 兼容 success 和 code 两种格式
                is_success = (query_result.get("success") == True) or (query_result.get("code") == 0)
                if not is_success:
                    logger.bind(tag=TAG).warning(f"查询失败，结果: {query_result}")
                    return ActionResponse(
                        Action.RESPONSE,
                        "无法查询任务列表，请稍后再试。",
                        None
                    )
                
                # 安全地获取records - 兼容两种数据结构
                data = query_result.get("data", [])
                logger.bind(tag=TAG).info(f"🔍 data字段类型: {type(data)}, 内容: {data}")
                
                if isinstance(data, list):
                    # 新格式：data直接是数组
                    records = data
                elif isinstance(data, dict):
                    # 旧格式：data是对象，包含records字段
                    records = data.get("records", [])
                else:
                    logger.bind(tag=TAG).warning(f"data字段格式不正确: {data}")
                    return ActionResponse(
                        Action.RESPONSE,
                        "查询结果格式异常，请稍后再试。",
                        None
                    )
                
                logger.bind(tag=TAG).info(f"📋 获取到 {len(records)} 条任务记录")
                
                if not records:
                    return ActionResponse(
                        Action.RESPONSE,
                        "没有找到任何任务可以删除。",
                        None
                    )
                
                # 打印任务详情用于调试
                try:
                    for i, record in enumerate(records):
                        # 兼容两种ID字段名称
                        task_id = record.get('jobId') or record.get('id')
                        logger.bind(tag=TAG).info(f"任务{i+1}: ID={task_id}, 名称='{record.get('jobName', '')}', Cron='{record.get('cronExpression', '')}'")
                    
                    # 如果只有一个任务且用户说"删除这个任务"等通用描述，直接删除
                    if len(records) == 1 and any(word in task_description.lower() for word in ["这个", "任务", "提醒", "定时"]):
                        # 兼容两种ID字段名称
                        actual_job_id = records[0].get("jobId") or records[0].get("id")
                        job_name = records[0].get("jobName", "")
                        cron_expression = records[0].get("cronExpression", "")  # 获取实际的cron表达式
                        logger.bind(tag=TAG).info(f"🎯 只有一个任务，直接匹配: 任务ID {actual_job_id} (任务名: '{job_name}', Cron: '{cron_expression}')")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"❌ 处理任务记录时出错: {e}")
                    return ActionResponse(
                        Action.RESPONSE,
                        "处理任务记录时出现问题，请稍后再试。",
                        None
                    )
                else:
                    # 简化的智能匹配 - 避免复杂逻辑导致卡死
                    logger.bind(tag=TAG).info(f"🔍 开始智能匹配，任务数量: {len(records)}")
                    matched_tasks = []
                    description_lower = task_description.lower()
                    
                    try:
                        import re
                        for i, record in enumerate(records):
                            logger.bind(tag=TAG).debug(f"正在匹配任务{i+1}...")
                            
                            task_name = record.get("jobName", "").lower()
                            task_content = record.get("promptContent", "").lower()
                            task_cron = record.get("cronExpression", "")
                            score = 0
                            
                            # 简化的匹配逻辑
                            # 1. 时间匹配（最重要）
                            if "19" in description_lower or "十九" in description_lower:
                                if "0 0 19 * * ?" in task_cron:
                                    score += 10
                                    logger.bind(tag=TAG).info(f"✅ 19点时间匹配成功")
                            
                            # 2. 关键词匹配
                            keywords = ["提醒", "任务", "定时", "闹钟"]
                            for keyword in keywords:
                                if keyword in description_lower:
                                    if keyword in task_name or keyword in task_content:
                                        score += 3
                            
                            # 3. 任务名称匹配
                            if task_name and any(word in task_name for word in description_lower.split()):
                                score += 5
                            
                            if score > 0:
                                matched_tasks.append((record, score))
                                logger.bind(tag=TAG).info(f"📊 任务匹配: {task_name} -> 分数: {score}")
                    
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"❌ 智能匹配过程出错: {e}")
                        # 如果匹配出错，直接选择第一个任务（如果只有一个）
                        if len(records) == 1:
                            actual_job_id = records[0]["jobId"]
                            task_name = records[0].get("jobName", "")
                            logger.bind(tag=TAG).info(f"🔄 匹配出错，使用唯一任务: 任务ID {actual_job_id}")
                        else:
                            return ActionResponse(
                                Action.RESPONSE,
                                "任务匹配过程出现问题，请稍后再试。",
                                None
                            )
                    
                    # 处理匹配结果
                    if matched_tasks:
                        matched_tasks.sort(key=lambda x: x[1], reverse=True)
                        best_match = matched_tasks[0][0]
                        best_score = matched_tasks[0][1]
                        
                        logger.bind(tag=TAG).info(f"🎯 智能匹配成功: 最高分={best_score}")
                        
                        # 如果最高分很低，可能匹配不准确
                        if best_score < 3:
                            task_list = [f"- {r.get('jobName', '无名任务')} (ID: {r.get('jobId') or r.get('id')})" for r in records]
                            return ActionResponse(
                                Action.RESPONSE,
                                f"没有找到明确匹配的任务，请具体说明要删除哪个：\n" + "\n".join(task_list),
                                None
                            )
                        
                        # 如果有多个高分匹配，要求用户确认
                        if len(matched_tasks) > 1 and matched_tasks[1][1] >= best_score * 0.8:
                            top_matches = [t[0] for t in matched_tasks[:3]]
                            task_list = [f"- {r.get('jobName', '无名任务')} (ID: {r.get('jobId') or r.get('id')})" for r in top_matches]
                            return ActionResponse(
                                Action.RESPONSE,
                                f"找到多个可能匹配的任务，请具体说明要删除哪个：\n" + "\n".join(task_list),
                                None
                            )
                        
                        actual_job_id = best_match.get("jobId") or best_match.get("id")
                        job_name = best_match.get("jobName", "")
                        cron_expression = best_match.get("cronExpression", "")  # 获取实际的cron表达式
                        logger.bind(tag=TAG).info(f"🎯 智能匹配成功: '{task_description}' -> 任务ID {actual_job_id} (任务名: '{job_name}', Cron: '{cron_expression}', 分数: {best_score})")
                    else:
                        # 没有匹配，列出所有任务让用户选择
                        task_list = [f"- {r.get('jobName', '无名任务')} (ID: {r.get('jobId') or r.get('id')})" for r in records]
                        return ActionResponse(
                            Action.RESPONSE,
                            f"没有找到与'{task_description}'匹配的任务。您的任务列表：\n" + "\n".join(task_list),
                            None
                        )
                        
            except Exception as e:
                import traceback
                logger.bind(tag=TAG).error(f"❌ 智能任务匹配失败: {e}")
                logger.bind(tag=TAG).error(f"❌ 详细错误信息: {traceback.format_exc()}")
                return ActionResponse(
                    Action.RESPONSE,
                    "任务匹配过程中出现问题，请直接提供任务ID或先查看任务列表。",
                    None
                )
        
        # 检查是否获得了有效的job_id
        if not actual_job_id:
            return ActionResponse(
                Action.RESPONSE,
                "请提供要删除的任务描述（如'明天8点的闹钟'）或任务ID。您也可以先说'查看我的任务列表'来查看所有任务。",
                None
            )
        
        # 安全确认：如果没有明确确认删除，给出提示
        if not confirm_delete:
            logger.bind(tag=TAG).info("用户未确认删除操作")
            return ActionResponse(
                Action.RESPONSE,
                f"您确定要删除任务ID为{actual_job_id}的任务吗？如果确定，请明确说'确认删除'。",
                None
            )
        
        # 安全的删除方法
        def safe_delete_strategy():
            """安全删除策略"""
            try:
                logger.bind(tag=TAG).info(f"开始删除任务: jobId={actual_job_id}")
                
                import asyncio
                import concurrent.futures
                
                async def safe_delete():
                    try:
                        # 确保任务名称不为空
                        final_job_name = job_name if job_name and job_name.strip() else "提醒任务"
                        logger.bind(tag=TAG).info(f"🔍 删除参数: job_id={actual_job_id}, job_name='{final_job_name}', cron='{cron_expression}', device_id={delete_device_id}")
                        
                        return await strategy_service.delete_user_strategy(
                            job_id=actual_job_id,
                            job_name=final_job_name,
                            cron_expression=cron_expression,  # 传递实际的cron表达式
                            device_id=delete_device_id,
                            prompt_content=""
                        )
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"异步删除失败: {e}")
                        return {"success": False, "message": f"删除失败: {str(e)}"}
                
                # 使用线程池执行异步任务
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, safe_delete())
                    try:
                        result = future.result(timeout=10)  # 10秒超时
                        logger.bind(tag=TAG).info(f"删除任务完成，结果: {result}")
                        return result
                    except concurrent.futures.TimeoutError:
                        logger.bind(tag=TAG).warning("删除任务超时")
                        return {"success": False, "message": "删除操作超时，请稍后再试"}
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"删除任务异常: {e}")
                        return {"success": False, "message": f"删除异常: {str(e)}"}
                        
            except Exception as e:
                logger.bind(tag=TAG).error(f"删除策略失败: {e}")
                return {"success": False, "message": f"删除失败: {str(e)}"}
        
        # 执行删除
        result = safe_delete_strategy()
        
        if result["success"]:
            logger.bind(tag=TAG).info(f"策略删除成功: job_id={actual_job_id}")
            
            # 构建成功消息
            if job_name:
                response_msg = f"好的，任务'{job_name}'已成功删除！"
            else:
                response_msg = f"好的，任务（ID:{actual_job_id}）已成功删除！"
            
            return ActionResponse(Action.RESPONSE, result=None, response=response_msg)
            
        else:
            error_msg = result["message"]
            logger.bind(tag=TAG).error(f"策略删除失败: {error_msg}")
            
            # 根据错误类型给出友好提示
            if "找不到" in error_msg or "不存在" in error_msg:
                response_msg = f"没有找到ID为{actual_job_id}的任务，可能该任务已经被删除或不存在。"
            elif "权限" in error_msg or "无法删除" in error_msg:
                response_msg = f"无法删除该任务，可能是权限问题：{error_msg}"
            else:
                response_msg = f"删除任务时遇到问题：{error_msg}，请稍后再试。"
            
            return ActionResponse(Action.RESPONSE, result=None, response=response_msg)
    
    except Exception as e:
        logger.bind(tag=TAG).error(f"删除用户策略功能异常: {e}")
        return ActionResponse(
            Action.RESPONSE, 
            "抱歉，删除任务时遇到了系统错误，请稍后再试。", 
            None
        )

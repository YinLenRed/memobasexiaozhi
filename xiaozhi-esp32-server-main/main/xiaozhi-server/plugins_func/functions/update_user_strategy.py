from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.tools.java_backend_strategy import JavaBackendStrategyService
import asyncio

TAG = __name__
logger = setup_logging()

UPDATE_USER_STRATEGY_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "update_user_strategy", 
        "description": (
            "修改用户的定时策略或任务安排。当用户要求修改已有的提醒、更改任务时间、"
            "修改任务内容等时使用此功能。例如：'把明天8点的闹钟改成9点'、'修改提醒内容'、"
            "'更改任务时间'等。需要指定任务ID以及要修改的内容。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": "要修改的任务描述，如'明天8点的闹钟'、'下午3点的会议提醒'等。系统会自动匹配对应的任务。如果知道具体任务ID，也可以直接提供job_id",
                },
                "job_id": {
                    "type": "integer",
                    "description": "要修改的任务ID。可选参数，如果不知道具体ID，可以用task_description来描述任务，系统会自动匹配",
                },
                "job_name": {
                    "type": "string",
                    "description": "新的任务名称。可选参数，不填则保持原名称",
                },
                "new_time_description": {
                    "type": "string", 
                    "description": "新的时间描述，如'每天8点'、'明天上午9点'等。系统会自动转换为cron表达式。可选参数",
                },
                "prompt_content": {
                    "type": "string",
                    "description": "新的提醒内容或任务描述。可选参数，不填则保持原内容",
                },
                "device_id": {
                    "type": "string",
                    "description": "设备ID。可选参数，通常不需要修改",
                }
            },
            "required": [],  # 不再强制要求job_id
        },
    },
}


@register_function("update_user_strategy", UPDATE_USER_STRATEGY_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def update_user_strategy(conn, task_description: str = None, job_id: int = None, job_name: str = None, 
                        new_time_description: str = None, prompt_content: str = None,
                        device_id: str = None):
    """
    修改用户策略
    
    Args:
        conn: 连接对象，包含设备信息和配置
        job_id: 要修改的任务ID
        job_name: 新的任务名称
        new_time_description: 新的时间描述
        prompt_content: 新的提醒内容
        device_id: 设备ID
    
    Returns:
        ActionResponse: 包含修改结果和响应消息
    """
    logger.bind(tag=TAG).info(f"收到用户策略修改请求: task_description={task_description}, job_id={job_id}, job_name={job_name}")
    
    try:
        # 检查是否配置了Java后端API
        if not conn.config.get("manager-api", {}).get("url"):
            logger.bind(tag=TAG).warning("未配置Java后端API，无法修改用户策略")
            return ActionResponse(
                Action.RESPONSE, 
                result=None,
                response="抱歉，系统暂未配置策略修改功能，无法修改您的任务。"
            )
        
        # 使用当前设备ID（如果没有指定）
        final_device_id = device_id if device_id else getattr(conn, 'device_id', None)
        
        # Java后端要求设备ID不能为空
        if not final_device_id:
            logger.bind(tag=TAG).warning("无法获取设备ID，无法修改策略")
            return ActionResponse(
                Action.RESPONSE, 
                result=None,
                response="抱歉，无法识别您的设备，请确认设备连接正常后再试。"
            )
        
        # 创建Java后端策略服务
        strategy_service = JavaBackendStrategyService(conn.config)
        
        # 🔍 智能任务匹配 + 快速ID提取
        actual_job_id = job_id
        original_job_id = job_id  # 保存原始提供的job_id
        found_task_record = None  # 存储找到的任务记录
        
        # 🚀 新增：从描述中提取任务ID（如"修改任务3"、"第2个任务"）
        if not actual_job_id and task_description:
            import re
            # 匹配 "任务X"、"第X个"、"ID:X" 等格式
            id_patterns = [
                r'任务(\d+)',
                r'第(\d+)个',
                r'ID[：:]\s*(\d+)',
                r'编号(\d+)',
                r'序号(\d+)'
            ]
            
            for pattern in id_patterns:
                match = re.search(pattern, task_description)
                if match:
                    try:
                        actual_job_id = int(match.group(1))
                        logger.bind(tag=TAG).info(f"🎯 从描述中提取到任务ID: {actual_job_id}")
                        break
                    except:
                        continue
        
        # 🎯 真实查询智能时间匹配 - 解决网络超时问题
        should_try_time_matching = (
            task_description and 
            ('点' in task_description or '时' in task_description) and
            (not actual_job_id or original_job_id == 1)  # 没有ID或ID=1(常见的无效ID)
        )
        
        if should_try_time_matching:
            logger.bind(tag=TAG).info(f"🔍 尝试查询时间匹配任务: {task_description}")
            try:
                # 🚀 参考删除策略的成功方法 - 使用ThreadPoolExecutor避免事件循环冲突
                def get_all_tasks():
                    try:
                        logger.bind(tag=TAG).info("开始查询任务列表...")
                        
                        # 使用现有的strategy_service，但采用更安全的调用方式
                        import concurrent.futures
                        
                        async def safe_query():
                            try:
                                return await strategy_service.query_user_strategies(device_id=final_device_id, size=50)
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
                
                # 🔧 参考删除策略的数据处理逻辑
                # 兼容两种数据结构
                if not query_result:
                    logger.bind(tag=TAG).warning("查询结果为空")
                else:
                    # 检查是否成功 - 兼容 success 和 code 两种格式
                    is_success = (query_result.get("success") == True) or (query_result.get("code") == 0)
                    if not is_success:
                        logger.bind(tag=TAG).warning(f"查询失败，结果: {query_result}")
                    else:
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
                            records = []
                        
                        logger.bind(tag=TAG).info(f"📋 获取到 {len(records)} 条任务记录")
                        
                        if records:
                            # 打印任务详情用于调试
                            try:
                                for i, record in enumerate(records):
                                    # 兼容两种ID字段名称
                                    task_id = record.get('jobId') or record.get('id')
                                    logger.bind(tag=TAG).info(f"任务{i+1}: ID={task_id}, 名称='{record.get('jobName', '')}', Cron='{record.get('cronExpression', '')}'")
                            except Exception as e:
                                logger.bind(tag=TAG).error(f"❌ 处理任务记录时出错: {e}")
                        
                        if len(records) > 0:
                            # 🔧 智能策略：如果只有一个任务，直接使用它（避免时间匹配失败）
                            if len(records) == 1:
                                record = records[0]
                                actual_job_id = record.get("jobId") or record.get("id")
                                found_task_record = record  # 🔧 保存找到的任务记录
                                current_cron = record.get("cronExpression", "")
                                current_name = record.get("jobName", "")
                                logger.bind(tag=TAG).info(f"✅ 只有一个任务，直接选择: ID={actual_job_id}, 名称='{current_name}', 当前时间={current_cron}")
                            else:
                                # 多个任务时才进行时间匹配
                                # 从task_description中提取时间
                                search_text = task_description
                                logger.bind(tag=TAG).info(f"🔍 时间提取搜索文本: {search_text}")
                                
                                time_patterns = [
                                    (r'十八点', 18),
                                    (r'十九点', 19), 
                                    (r'二十点', 20),
                                    (r'二十一点', 21),
                                    (r'(\d{1,2})点', None),
                                    (r'(\d{1,2})时', None),
                                ]
                                
                                target_hour = None
                                for pattern, hour_value in time_patterns:
                                    if hour_value is not None:
                                        # 中文数字模式
                                        clean_pattern = pattern.replace('\\', '')
                                        if clean_pattern in search_text:
                                            target_hour = hour_value
                                            logger.bind(tag=TAG).info(f"🎯 匹配中文时间: {clean_pattern} -> {target_hour}点")
                                            break
                                    else:
                                        # 数字模式
                                        import re
                                        match = re.search(pattern, search_text)
                                        if match:
                                            target_hour = int(match.group(1))
                                            logger.bind(tag=TAG).info(f"🎯 匹配数字时间: {match.group(1)} -> {target_hour}点")
                                            break
                                
                                if target_hour is not None:
                                    logger.bind(tag=TAG).info(f"🎯 提取目标时间: {target_hour}点")
                                    
                                    # 在查询到的任务列表中查找匹配的时间
                                    for record in records:
                                        cron_expr = record.get("cronExpression", "")
                                        record_id = record.get("jobId") or record.get("id")
                                        logger.bind(tag=TAG).debug(f"🔍 检查任务: ID={record_id}, cron={cron_expr}")
                                        
                                        # 解析cron表达式中的小时（格式：秒 分 时 日 月 周）
                                        if cron_expr:
                                            parts = cron_expr.split()
                                            if len(parts) >= 3:
                                                try:
                                                    cron_hour = int(parts[2])
                                                    if cron_hour == target_hour:
                                                        actual_job_id = record_id
                                                        found_task_record = record  # 🔧 保存找到的任务记录
                                                        logger.bind(tag=TAG).info(f"✅ 查询匹配到任务: ID={actual_job_id}, 时间={target_hour}点")
                                                        break
                                                except Exception as parse_e:
                                                    logger.bind(tag=TAG).debug(f"解析cron失败: {parse_e}")
                                                    continue
                                    
                                    if not actual_job_id:
                                        logger.bind(tag=TAG).warning(f"❌ 在{len(records)}条记录中未找到{target_hour}点的任务")
                                        # 🔧 备用策略：如果时间匹配失败，使用第一个任务
                                        if records:
                                            record = records[0]
                                            actual_job_id = record.get("jobId") or record.get("id")
                                            found_task_record = record  # 🔧 保存找到的任务记录
                                            logger.bind(tag=TAG).info(f"🔄 使用备用策略，选择第一个任务: ID={actual_job_id}")
                                else:
                                    logger.bind(tag=TAG).warning("❌ 未能从描述中提取时间信息")
                                    # 🔧 备用策略：没有提取到时间，使用第一个任务
                                    if records:
                                        record = records[0]
                                        actual_job_id = record.get("jobId") or record.get("id")
                                        found_task_record = record  # 🔧 保存找到的任务记录
                                        logger.bind(tag=TAG).info(f"🔄 未提取到时间，使用第一个任务: ID={actual_job_id}")
                                    else:
                                        logger.bind(tag=TAG).warning("❌ 查询到的任务列表为空")
                    
            except Exception as e:
                logger.bind(tag=TAG).error(f"❌ 查询时间匹配失败: {e}")
                import traceback
                logger.bind(tag=TAG).error(f"❌ 错误堆栈: {traceback.format_exc()}")
        
        # 🎯 如果智能匹配未找到ID，尝试使用默认策略或创建新任务的提示
        if not actual_job_id and task_description:
            logger.bind(tag=TAG).info(f"⚠️ 智能匹配未找到任务ID，但仍可继续处理: {task_description}")
            # 不再强制要求用户查看任务列表，而是给出更友好的提示
        
        # 🔧 移除智能推测，只使用实际查询结果
        if not actual_job_id:
            return ActionResponse(
                Action.RESPONSE,
                result=None,
                response="抱歉，没有找到匹配的任务。您可以说'查看我的任务列表'查看所有任务，或者尝试更具体的描述（比如'修改任务2的时间'）。"
            )
        
        # 🔧 重要：Java后端要求job_name不能为空，需要先查询原有任务信息
        original_job_name = job_name
        original_cron_expression = None
        original_prompt_content = prompt_content
        
        # 🔧 优化：如果已经找到了任务记录，直接使用，不再重复查询
        if found_task_record and (not job_name or not prompt_content):
            logger.bind(tag=TAG).info(f"✅ 使用已找到的任务记录信息: ID={actual_job_id}")
            
            if not job_name:
                original_job_name = found_task_record.get("jobName", f"任务{actual_job_id}")
                logger.bind(tag=TAG).info(f"✅ 从已找到任务获取名称: {original_job_name}")
            
            if not prompt_content:
                original_prompt_content = found_task_record.get("promptContent", "")
                logger.bind(tag=TAG).info(f"✅ 从已找到任务获取提示内容: {original_prompt_content[:50]}...")
        
        # 如果没有找到任务记录且缺少必需信息，设置默认值
        elif not job_name or not prompt_content:
            logger.bind(tag=TAG).info(f"🔍 设置默认任务信息: job_id={actual_job_id}")
            
            if not job_name:
                if task_description:
                    original_job_name = f"{task_description[:10]}..." if len(task_description) > 10 else task_description
                else:
                    original_job_name = f"定时任务{actual_job_id}"
                logger.bind(tag=TAG).info(f"📝 设置默认任务名称: {original_job_name}")
            
            if not prompt_content:
                if task_description:
                    original_prompt_content = task_description
                else:
                    original_prompt_content = f"定时提醒任务{actual_job_id}"
                logger.bind(tag=TAG).info(f"📝 设置默认提示内容: {original_prompt_content[:50]}...")
        
        # 处理cron表达式
        if new_time_description:
            cron_expression = strategy_service._generate_cron_expression(new_time_description)
            logger.bind(tag=TAG).info(f"生成新的cron表达式: '{new_time_description}' -> '{cron_expression}'")
        else:
            cron_expression = original_cron_expression or "0 0 8 * * ?"
            logger.bind(tag=TAG).info(f"使用原有或默认cron表达式: {cron_expression}")
        
        # 确保所有必需字段都有值
        final_job_name = original_job_name or f"定时任务{actual_job_id}"
        
        # 🔧 智能更新提示内容：如果修改了时间，也要更新提示文案
        if new_time_description and original_prompt_content:
            # 从新时间描述中提取关键时间信息来更新提示内容
            import re
            
            # 提取新的时间信息
            new_time_info = None
            time_patterns = [
                (r'一点', '一点'), (r'二点', '二点'), (r'三点', '三点'), (r'四点', '四点'), (r'五点', '五点'),
                (r'六点', '六点'), (r'七点', '七点'), (r'八点', '八点'), (r'九点', '九点'), (r'十点', '十点'),
                (r'十一点', '十一点'), (r'十二点', '十二点'), (r'十三点', '十三点'), (r'十四点', '十四点'),
                (r'十五点', '十五点'), (r'十六点', '十六点'), (r'十七点', '十七点'), (r'十八点', '十八点'),
                (r'十九点', '十九点'), (r'二十点', '二十点'), (r'二十一点', '二十一点'), (r'二十二点', '二十二点'), (r'二十三点', '二十三点'),
                (r'(\d{1,2})点', None),
            ]
            
            for pattern, time_text in time_patterns:
                if time_text is not None:
                    if time_text in new_time_description:
                        new_time_info = time_text
                        logger.bind(tag=TAG).info(f"🎯 提取到新时间信息: {time_text}")
                        break
                else:
                    match = re.search(pattern, new_time_description)
                    if match:
                        new_time_info = f"{match.group(1)}点"
                        logger.bind(tag=TAG).info(f"🎯 提取到新时间信息: {new_time_info}")
                        break
            
            if new_time_info:
                # 🔧 智能替换：找到原有提示内容中的时间并替换
                import re
                updated_content = original_prompt_content
                
                # 🚀 使用正则表达式进行更智能的时间替换
                # 匹配各种时间模式：十点、十八点、18点、22点等
                time_pattern = r'(十十点|二十二点|二十一点|二十点|十九点|十八点|十七点|十六点|十五点|十四点|十三点|十二点|十一点|十点|九点|八点|七点|六点|五点|四点|三点|二点|一点|\d{1,2}点)'
                
                def replace_time(match):
                    old_time = match.group(1)
                    logger.bind(tag=TAG).info(f"📝 找到需要替换的时间: '{old_time}'")
                    return new_time_info
                
                # 执行替换
                new_content = re.sub(time_pattern, replace_time, updated_content)
                
                if new_content != updated_content:
                    final_prompt_content = new_content
                    logger.bind(tag=TAG).info(f"✅ 智能正则替换后的提示内容: {final_prompt_content}")
                else:
                    # 如果正则没有匹配到，尝试简单字符串替换
                    all_time_patterns = [
                        '十十点', '二十二点', '二十一点', '二十点', '十九点', '十八点', '十七点', '十六点',
                        '十五点', '十四点', '十三点', '十二点', '十一点', '十点', '九点', '八点', '七点',
                        '六点', '五点', '四点', '三点', '二点', '一点'
                    ] + [f'{i}点' for i in range(1, 24)]
                    
                    replaced = False
                    for old_time in all_time_patterns:
                        if old_time in updated_content and old_time != new_time_info:
                            updated_content = updated_content.replace(old_time, new_time_info)
                            logger.bind(tag=TAG).info(f"📝 字符串替换: '{old_time}' -> '{new_time_info}'")
                            replaced = True
                            break
                    
                    if replaced:
                        final_prompt_content = updated_content
                        logger.bind(tag=TAG).info(f"✅ 字符串替换后的提示内容: {final_prompt_content}")
                    else:
                        final_prompt_content = original_prompt_content
                        logger.bind(tag=TAG).info(f"⚠️ 未找到可替换的时间模式，保持原内容: {final_prompt_content}")
            else:
                final_prompt_content = original_prompt_content
                logger.bind(tag=TAG).info(f"⚠️ 未能提取新时间信息，保持原内容: {final_prompt_content}")
        else:
            final_prompt_content = original_prompt_content or (task_description or f"定时提醒任务{actual_job_id}")
        
        logger.bind(tag=TAG).info(f"🔍 最终字段值: job_name='{final_job_name}', prompt_content='{final_prompt_content[:50]}...'")
        
        # 🔧 执行修改操作 - 使用ThreadPoolExecutor避免事件循环冲突
        def execute_update():
            try:
                logger.bind(tag=TAG).info(f"🚀 开始修改任务: job_id={actual_job_id}, job_name={final_job_name}, cron={cron_expression}")
                
                async def do_update():
                    return await strategy_service.update_user_strategy(
                        job_id=actual_job_id,
                        job_name=final_job_name,  # 使用确保非空的任务名称
                        cron_expression=cron_expression,
                        device_id=final_device_id,
                        prompt_content=final_prompt_content  # 使用处理后的提示内容
                    )
                
                # 🔧 使用ThreadPoolExecutor避免事件循环冲突（参考删除策略方法）
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, do_update())
                    return future.result(timeout=8)  # 8秒超时
                    
            except Exception as e:
                logger.bind(tag=TAG).error(f"修改策略异常: {e}")
                return {
                    "success": False,
                    "message": f"修改异常: {str(e)}"
                }
        
        result = execute_update()
        
        if result["success"]:
            logger.bind(tag=TAG).info(f"策略修改成功: job_id={actual_job_id}")
            
            # 构建成功消息
            changes = []
            if job_name and job_name != original_job_name:  # 只有当任务名称真的改变时才提及
                changes.append(f"任务名称改为'{final_job_name}'")
            if new_time_description:
                changes.append(f"时间改为'{new_time_description}'")
            if prompt_content and prompt_content != original_prompt_content:  # 只有当内容真的改变时才提及
                content_preview = prompt_content[:20] + "..." if len(prompt_content) > 20 else prompt_content
                changes.append(f"内容改为'{content_preview}'")
            
            if changes:
                change_desc = "、".join(changes)
                response_msg = f"好的，任务修改成功！已将{change_desc}。"
            else:
                response_msg = "任务修改成功！"
            
            return ActionResponse(Action.RESPONSE, result=None, response=response_msg)
            
        else:
            error_msg = result["message"]
            logger.bind(tag=TAG).error(f"策略修改失败: {error_msg}")
            
            # 根据错误类型给出友好提示
            if "找不到" in error_msg or "不存在" in error_msg:
                response_msg = f"没有找到ID为{job_id}的任务，请先查询任务列表确认任务ID。"
            else:
                response_msg = f"修改任务时遇到问题：{error_msg}，请稍后再试。"
            
            return ActionResponse(Action.RESPONSE, result=None, response=response_msg)
    
    except Exception as e:
        logger.bind(tag=TAG).error(f"修改用户策略功能异常: {e}")
        return ActionResponse(
            Action.RESPONSE, 
            result=None,
            response="抱歉，修改任务时遇到了系统错误，请稍后再试。"
        )

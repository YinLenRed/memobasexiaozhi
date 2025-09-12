import json
import time
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from config.logger import setup_logging
from core.utils.ssl_helper import create_secure_session

TAG = __name__


class JavaBackendStrategyService:
    """Java后端用户策略服务"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = setup_logging()
        self.config = config
        
        # Java后端API配置
        self.java_api_base = config.get("manager-api", {}).get("url", "")
        self.api_secret = config.get("manager-api", {}).get("secret", "")
        
        # MQTT配置
        self.mqtt_topic = "server/dev/report/userPolicy"
        
        # 超时配置
        self.request_timeout = 10
        self.query_timeout = 8  # 🚀 查询专用超时，适应公网环境
        
        self.logger.bind(tag=TAG).info(f"Java后端策略服务初始化: {self.java_api_base}")
        
    async def save_user_strategy(self, device_id: str, title: str, data: str) -> Dict[str, Any]:
        """保存用户策略到Java后端"""
        try:
            url = f"{self.java_api_base}/api/saveJob"
            headers = {
                "Content-Type": "application/json"
            }
            
            # 生成cron表达式
            cron_expression = self._generate_cron_expression(data)
            
            # 构建请求数据 (完全匹配Java后端API文档)
            request_data = {
                "jobId": 0,                     # 新任务，jobId设为0
                "jobName": title,               # Java期望: jobName  
                "cronExpression": cron_expression,  # Java期望: cronExpression
                "deviceId": device_id,          # Java期望: deviceId
                "promptContent": data           # Java期望: promptContent
            }
            
            self.logger.bind(tag=TAG).info(f"保存用户策略: 设备 {device_id}, 标题: {title}, 内容: {data[:50]}...")
            self.logger.bind(tag=TAG).info(f"发送到Java后端的数据: {request_data}")
            
            # 发送请求到Java后端
            result = await self._make_strategy_request(url, headers, request_data)
            
            if result and result.get("code") == 0:  # Java后端: code=0表示成功
                self.logger.bind(tag=TAG).info(f"用户策略保存成功: {device_id}")
                return {
                    "success": True,
                    "message": result.get("msg", "策略保存成功"),  # 使用Java后端返回的msg
                    "data": result.get("data")
                }
            else:
                error_msg = result.get("msg", "未知错误") if result else "请求失败"  # Java后端使用msg字段
                self.logger.bind(tag=TAG).error(f"用户策略保存失败: {error_msg}")
                return {
                    "success": False,
                    "message": f"策略保存失败: {error_msg}",
                    "data": None
                }
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"保存用户策略失败: {e}")
            return {
                "success": False,
                "message": f"保存失败: {str(e)}",
                "data": None
            }
    
    async def _make_strategy_request(self, url: str, headers: dict, request_data: dict) -> Optional[Dict[str, Any]]:
        """发起策略保存请求"""
        try:
            async with create_secure_session() as session:
                async with session.post(
                    url, 
                    headers=headers, 
                    json=request_data,
                    timeout=self.request_timeout
                ) as response:
                    if response.status == 200:
                        try:
                            result = await response.json()
                            # 🔧 修复：根据Java API的code字段判断成功与否
                            if isinstance(result, dict) and result.get("code") == 0:
                                result["success"] = True
                                self.logger.bind(tag=TAG).info(f"✅ Java API请求成功 (code=0): {response.status}")
                                return result
                            else:
                                # 即使状态码是200，如果code不为0，也认为是失败
                                error_msg = result.get("msg", "未知错误") if isinstance(result, dict) else "非JSON响应或解析失败"
                                self.logger.bind(tag=TAG).error(f"❌ Java API请求成功但操作失败 (code!=0): {response.status}, 消息: {error_msg}, 响应: {result}")
                                return {
                                    "success": False,
                                    "message": error_msg,
                                    "data": result
                                }
                        except Exception as json_error:
                            # 如果无法解析JSON，或者不是预期的JSON格式，视为失败
                            response_text = await response.text()
                            self.logger.bind(tag=TAG).error(f"❌ Java API响应非预期JSON格式或解析失败: {response.status}, 错误: {json_error}, 响应: {response_text}")
                            return {
                                "success": False,
                                "message": f"Java API响应格式错误或解析失败: {response_text}",
                                "data": response_text
                            }
                    else:
                        error_text = await response.text()
                        self.logger.bind(tag=TAG).error(f"Java API请求失败: {response.status}, {error_text}")
                        return {
                            "success": False,
                            "message": f"服务器错误 {response.status}: {error_text}"
                        }
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"发起策略请求异常: {e}")
            return {
                "success": False,
                "message": f"网络请求失败: {str(e)}"
            }
    
    def _parse_user_input(self, user_input: str) -> Dict[str, str]:
        """解析用户输入，提取任务名称和数据"""
        try:
            # 简单的关键词匹配来生成任务名称
            title = ""
            if "提醒" in user_input or "叫我" in user_input or "通知我" in user_input:
                title = "提醒任务"
            elif "闹钟" in user_input or "起床" in user_input:
                title = "闹钟提醒"
            elif "会议" in user_input or "开会" in user_input:
                title = "会议提醒"
            elif "吃药" in user_input:
                title = "吃药提醒"
            elif "生日" in user_input:
                title = "生日提醒"
            else:
                title = "任务名称"  # 默认标题
            
            return {
                "title": title,
                "data": user_input
            }
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"解析用户输入失败: {e}")
            return {
                "title": "用户任务",
                "data": user_input
            }
    
    def _get_smart_template_response(self, title: str, user_input: str) -> str:
        """智能模板回复（降级方案）"""
        if "闹钟" in title or "起床" in user_input or "叫我" in user_input:
            if "明天" in user_input:
                return "好嘞！明天早上准时叫您起床，记得早点睡觉哦~"
            else:
                return "好的！闹钟已经设置好了，我会按时提醒您的~"
        elif "吃药" in user_input:
            return "明白啦！按时吃药我来提醒，健康最重要嘛~"
        elif "会议" in user_input or "开会" in user_input:
            return "收到啦！开会时间我会及时提醒您的，不用担心忘记~"
        elif "生日" in user_input:
            return "好的！生日这么重要的日子怎么能忘记呢，我来帮您记住~"
        else:
            return f"好嘞！我已经记下了，会按时提醒您的，放心吧~"
    
    def _get_default_response(self, success: bool) -> str:
        """获取默认响应文本"""
        if success:
            return "好的，我已经帮您保存了这个策略，系统会按照您的要求执行。"
        else:
            return "抱歉，保存策略时遇到了问题，请稍后再试。"
    
    async def generate_llm_response(self, conn, title: str, data: str, user_input: str) -> str:
        """使用现有对话LLM生成个性化回复"""
        try:
            # 构建LLM提示词
            prompt = f"""你刚刚帮用户成功保存了一个策略/提醒请求，现在需要给用户一个确认回复。

用户的请求：{user_input}
策略类型：{title}

请生成一个温暖、贴心的确认回复，要求：
1. 语气亲切友好，像朋友一样
2. 确认已经保存成功，让用户安心
3. 根据具体任务给出相应的关怀
4. 长度控制在25字以内
5. 可以适当加入关怀词汇，如"记得早点睡"、"注意身体"等
6. 只使用中文字符，不要使用emoji表情符号

请直接返回纯文字回复内容。"""

            # 使用现有的LLM实例（conn.llm）
            if hasattr(conn, 'llm') and conn.llm:
                # 使用对话LLM生成回复（兼容现有格式）
                from core.utils.dialogue import Dialogue, Message
                
                # 创建临时对话对象
                temp_dialogue = Dialogue()
                temp_dialogue.put(Message(role="user", content=prompt))
                
                # 使用现有对话格式调用LLM
                response_generator = conn.llm.response("strategy_confirm", temp_dialogue.get_llm_dialogue())
                
                # 收集LLM响应
                response_text = ""
                for chunk in response_generator:
                    if chunk and isinstance(chunk, str):
                        response_text += chunk
                
                # 清理响应（移除emoji和特殊字符）
                response_text = response_text.strip()
                # 清理emoji和特殊符号，确保TTS能正常处理
                import re
                response_text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？、~]', '', response_text)
                
                if response_text and len(response_text) <= 40:
                    self.logger.bind(tag=TAG).info(f"对话LLM生成的个性化回复: {response_text}")
                    return response_text
                else:
                    self.logger.bind(tag=TAG).warning(f"LLM回复过长，使用模板: {response_text[:20]}...")
            
            # 如果没有LLM实例或生成失败，使用模板
            return self._get_smart_template_response(title, user_input)
            
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"对话LLM生成回复失败: {e}，使用模板")
            return self._get_smart_template_response(title, user_input)

    async def process_user_strategy_request(self, conn, user_input: str) -> Dict[str, Any]:
        """处理用户策略请求的完整流程"""
        try:
            # 获取设备ID
            device_id = getattr(conn, 'device_id', None)
            if not device_id:
                return {
                    "success": False,
                    "message": "无法获取设备ID",
                    "response": "抱歉，无法识别您的设备，请检查连接状态。"
                }
            
            # 解析用户输入
            parsed_input = self._parse_user_input(user_input)
            title = parsed_input["title"]
            data = parsed_input["data"]
            
            # 保存到Java后端
            result = await self.save_user_strategy(device_id, title, data)
            
            # 生成个性化响应文本
            if result["success"]:
                # 使用现有对话LLM生成个性化回复
                response_text = await self.generate_llm_response(conn, title, data, user_input)
            else:
                response_text = f"保存策略时遇到问题：{result['message']}，请稍后再试。"
            
            return {
                "success": result["success"],
                "message": result["message"],
                "response": response_text,
                "data": result["data"]
            }
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理用户策略请求失败: {e}")
            return {
                "success": False,
                "message": f"处理失败: {str(e)}",
                "response": "抱歉，处理您的请求时遇到了问题，请稍后再试。"
            }
    
    def _generate_cron_expression(self, user_input: str) -> str:
        """根据用户输入生成cron表达式"""
        try:
            # 基本时间解析
            now = datetime.now()
            hour = 8  # 默认8点
            minute = 0  # 默认0分
            
            # 中文数字转换
            chinese_numbers = {
                '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
                '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15, '十六': 16, '十七': 17, '十八': 18,
                '十九': 19, '二十': 20, '二十一': 21, '二十二': 22, '二十三': 23
            }
            
            def convert_chinese_time(text):
                """将中文数字时间转换为数字"""
                # 🔧 修复：按长度排序，先处理长的数字（如"十九"）再处理短的（如"十"）
                sorted_chinese = sorted(chinese_numbers.items(), key=lambda x: len(x[0]), reverse=True)
                for chinese, number in sorted_chinese:
                    text = text.replace(chinese + '点', str(number) + '点')
                    text = text.replace(chinese + '时', str(number) + '时')
                return text
            
            # 转换中文数字
            converted_input = convert_chinese_time(user_input)
            
            # 解析小时
            hour_patterns = [
                r'(\d{1,2})[点时]',  # 8点、18时
                r'(\d{1,2})[:：](\d{1,2})',  # 8:30、18：00
                r'(\d{1,2})点(\d{1,2})[分钟]?',  # 8点30分
                r'(\d{1,2})点半',  # 8点半
            ]
            
            for pattern in hour_patterns:
                match = re.search(pattern, converted_input)
                if match:
                    if '点半' in pattern:
                        hour = int(match.group(1))
                        minute = 30
                    elif len(match.groups()) == 2:
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                    else:
                        hour = int(match.group(1))
                        minute = 0
                    break
            
            # 🔧 修复时间段调整逻辑
            if '早上' in user_input or '早晨' in user_input:
                if hour > 12:
                    hour = hour - 12 if hour <= 18 else 8
                elif hour < 6:
                    hour = 8
            elif '上午' in user_input:
                if hour > 12:
                    hour = hour - 12 if hour <= 18 else 10
                elif hour < 6:
                    hour = 10
            elif '下午' in user_input:
                if hour < 12:
                    hour = hour + 12
                elif hour == 12:
                    hour = 14
            elif '晚上' in user_input:
                if hour < 12:
                    hour = hour + 12
                elif hour > 23:
                    hour = 20
            elif '凌晨' in user_input:
                if hour > 6:
                    hour = hour - 12 if hour > 12 else hour
                if hour < 0:
                    hour = hour + 12
                elif hour > 6:
                    hour = 2
            else:
                # 🎯 关键修复：如果是19点这样的24小时制，不要做调整
                # 对于>=13的小时数，认为是24小时制，保持原样
                if hour >= 13:
                    pass  # 保持19点就是19点，不做任何调整
                elif hour == 12:
                    pass  # 12点保持不变
                # 对于1-11点的时间，如果用户明确说了数字>12，说明是24小时制
                original_hour_str = re.search(r'(\d{1,2})', converted_input)
                if original_hour_str and int(original_hour_str.group(1)) >= 13:
                    hour = int(original_hour_str.group(1))
            
            # 确保小时在有效范围内
            hour = max(0, min(23, hour))
            minute = max(0, min(59, minute))
            
            # 🔍 调试日志：记录时间转换过程
            self.logger.bind(tag=TAG).info(f"🕐 时间转换详情: 原始输入='{user_input}' -> 转换后='{converted_input}' -> 最终时间={hour:02d}:{minute:02d}")
            
            # 频率判断
            if any(word in user_input for word in ['每天', '天天', '每日']):
                # 每天执行
                cron_expr = f"0 {minute} {hour} * * ?"
                self.logger.bind(tag=TAG).info(f"生成每天cron表达式: {cron_expr} (每天{hour:02d}:{minute:02d})")
                
            elif any(word in user_input for word in ['每周', '每星期']):
                # 每周执行，默认周一
                weekday = 1  # 周一
                # 可以扩展解析具体星期
                cron_expr = f"0 {minute} {hour} ? * {weekday}"
                self.logger.bind(tag=TAG).info(f"生成每周cron表达式: {cron_expr} (每周一{hour:02d}:{minute:02d})")
                
            elif '明天' in user_input:
                # 一次性执行 - 明天的具体时间
                tomorrow = now + timedelta(days=1)
                day = tomorrow.day
                month = tomorrow.month
                cron_expr = f"0 {minute} {hour} {day} {month} ?"
                self.logger.bind(tag=TAG).info(f"生成明天一次性cron表达式: {cron_expr} (明天{hour:02d}:{minute:02d})")
                
            elif '后天' in user_input:
                # 一次性执行 - 后天的具体时间
                day_after_tomorrow = now + timedelta(days=2)
                day = day_after_tomorrow.day
                month = day_after_tomorrow.month
                cron_expr = f"0 {minute} {hour} {day} {month} ?"
                self.logger.bind(tag=TAG).info(f"生成后天一次性cron表达式: {cron_expr} (后天{hour:02d}:{minute:02d})")
                
            elif '今天' in user_input:
                # 一次性执行 - 今天的具体时间
                today = now
                day = today.day
                month = today.month
                cron_expr = f"0 {minute} {hour} {day} {month} ?"
                self.logger.bind(tag=TAG).info(f"生成今天一次性cron表达式: {cron_expr} (今天{hour:02d}:{minute:02d})")
                
            else:
                # 默认：每天执行
                cron_expr = f"0 {minute} {hour} * * ?"
                self.logger.bind(tag=TAG).info(f"生成默认每天cron表达式: {cron_expr} (每天{hour:02d}:{minute:02d})")
            
            return cron_expr
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"生成cron表达式失败: {e}")
            # 默认每天早上8点
            return "0 0 8 * * ?"
    
    async def query_user_strategies(self, device_id: str = None, agent_id: str = None, 
                                   job_name: str = None, status: str = None,
                                   current: int = 1, size: int = 10) -> Dict[str, Any]:
        """查询用户策略列表
        
        Args:
            device_id: 设备ID
            agent_id: 智能体ID
            job_name: 任务名称
            status: 任务状态（0正常 1暂停）
            current: 页码，默认第1页
            size: 每页显示记录数，默认10条
            
        Returns:
            Dict: 包含查询结果的字典
        """
        try:
            url = f"{self.java_api_base}/api/userJobList"
            headers = {
                "Content-Type": "application/json"
            }
            
            # 🚀 优化：精简请求数据，减少传输量
            request_data = {
                "size": size,
                "current": current
            }
            
            # 只在有值时才添加筛选字段，避免传递空字符串
            if device_id:
                request_data["deviceId"] = device_id
            else:
                request_data["deviceId"] = ""
                
            if agent_id:
                request_data["agentId"] = agent_id  
            else:
                request_data["agentId"] = ""
                
            if job_name:
                request_data["jobName"] = job_name
            else:
                request_data["jobName"] = ""
                
            if status:
                request_data["status"] = status
            else:
                request_data["status"] = ""
                
            # 固定字段
            request_data["jobGroup"] = ""
            request_data["nowDate"] = ""
            request_data["cronExpression"] = ""
            
            self.logger.bind(tag=TAG).info(f"查询用户策略: 设备ID={device_id}, 第{current}页, 每页{size}条")
            self.logger.bind(tag=TAG).debug(f"查询请求数据: {request_data}")
            
            # 发送请求到Java后端
            result = await self._make_query_request(url, headers, request_data)
            
            if result and result.get("code") == 0:  # Java后端返回code=0表示成功
                self.logger.bind(tag=TAG).info(f"用户策略查询成功，返回{len(result.get('data', []))}条记录")
                return {
                    "success": True,
                    "message": result.get("msg", "查询成功"),
                    "data": result.get("data", []),
                    "total": len(result.get("data", []))  # 简单计算，实际应该从分页信息中获取
                }
            else:
                error_msg = result.get("msg", "未知错误") if result else "请求失败"
                self.logger.bind(tag=TAG).error(f"用户策略查询失败: {error_msg}")
                return {
                    "success": False,
                    "message": f"查询失败: {error_msg}",
                    "data": [],
                    "total": 0
                }
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"查询用户策略失败: {e}")
            return {
                "success": False,
                "message": f"查询失败: {str(e)}",
                "data": [],
                "total": 0
            }
    
    async def _make_query_request(self, url: str, headers: dict, request_data: dict) -> Optional[Dict[str, Any]]:
        """发起策略查询请求"""
        try:
            async with create_secure_session() as session:
                async with session.post(
                    url, 
                    headers=headers, 
                    json=request_data,
                    timeout=self.query_timeout  # 🚀 使用查询专用短超时
                ) as response:
                    if response.status == 200:
                        try:
                            result = await response.json()
                            self.logger.bind(tag=TAG).info(f"Java查询API请求成功: {response.status}")
                            return result
                        except Exception as json_error:
                            self.logger.bind(tag=TAG).error(f"解析查询响应JSON失败: {json_error}")
                            return None
                    else:
                        error_text = await response.text()
                        self.logger.bind(tag=TAG).error(f"Java查询API请求失败: {response.status}, {error_text}")
                        return {
                            "code": response.status,
                            "msg": f"服务器错误: {error_text}"
                        }
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"发起查询请求异常: {e}")
            return {
                "code": -1,
                "msg": f"网络请求失败: {str(e)}"
            }
    
    async def update_user_strategy(self, job_id: int, job_name: str = None, 
                                  cron_expression: str = None, device_id: str = None, 
                                  prompt_content: str = None) -> Dict[str, Any]:
        """修改用户策略
        
        Args:
            job_id: 任务ID（必须）
            job_name: 任务名称（可选）
            cron_expression: cron执行表达式（可选）
            device_id: 设备ID（可选）
            prompt_content: 提示内容（可选）
            
        Returns:
            Dict: 包含修改结果的字典
        """
        try:
            url = f"{self.java_api_base}/api/updateJob"
            headers = {
                "Content-Type": "application/json"
            }
            
            # 确保任务名称和cron表达式不为空
            final_job_name = job_name if job_name and job_name.strip() else "提醒任务"
            final_cron_expression = cron_expression if cron_expression and cron_expression.strip() else "0 0 8 * * ?"
            
            # 🔧 修复：按照删除API的成功经验，修改API也不使用sysJobDTO包装
            request_data = {
                "jobId": int(job_id),  # 确保是整数类型
                "jobName": final_job_name,
                "cronExpression": final_cron_expression,
                "deviceId": device_id if device_id else "",
                "promptContent": prompt_content if prompt_content else ""
            }
            
            self.logger.bind(tag=TAG).info(f"修改用户策略: jobId={job_id}, jobName='{final_job_name}', cron='{final_cron_expression}', 设备ID={device_id}")
            self.logger.bind(tag=TAG).info(f"🔍 详细修改请求数据: {request_data}")
            
            # 发送请求到Java后端
            result = await self._make_strategy_request(url, headers, request_data)
            
            if result and (result.get("code") == 0 or result.get("success")):  # 兼容不同的成功标识
                self.logger.bind(tag=TAG).info(f"用户策略修改成功: jobId={job_id}")
                return {
                    "success": True,
                    "message": result.get("msg", "修改成功"),
                    "data": result.get("data")
                }
            else:
                error_msg = result.get("msg", "未知错误") if result else "请求失败"
                self.logger.bind(tag=TAG).error(f"用户策略修改失败: {error_msg}")
                return {
                    "success": False,
                    "message": f"修改失败: {error_msg}",
                    "data": None
                }
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"修改用户策略失败: {e}")
            return {
                "success": False,
                "message": f"修改失败: {str(e)}",
                "data": None
            }
    
    async def delete_user_strategy(self, job_id: int, job_name: str = None,
                                  cron_expression: str = None, device_id: str = None,
                                  prompt_content: str = None) -> Dict[str, Any]:
        """删除用户策略
        
        Args:
            job_id: 任务ID（必须）
            job_name: 任务名称（可选）
            cron_expression: cron执行表达式（可选）  
            device_id: 设备ID（可选）
            prompt_content: 提示内容（可选）
            
        Returns:
            Dict: 包含删除结果的字典
        """
        try:
            url = f"{self.java_api_base}/api/deleteJob"
            headers = {
                "Content-Type": "application/json"
            }
            
            # 确保任务名称不为空
            final_job_name = job_name if job_name and job_name.strip() else "提醒任务"
            
            # 🔧 尝试按照Java文档的确切格式，不使用sysJobDTO包装
            request_data = {
                "jobId": int(job_id),  # 确保是整数类型
                "jobName": final_job_name,
                "cronExpression": cron_expression if cron_expression else "",
                "deviceId": device_id if device_id else "",
                "promptContent": prompt_content if prompt_content else ""
            }
            
            self.logger.bind(tag=TAG).info(f"删除用户策略: jobId={job_id}, jobName='{final_job_name}', 设备ID={device_id}")
            self.logger.bind(tag=TAG).info(f"🔍 删除请求数据: {request_data}")
            
            # 发送请求到Java后端
            result = await self._make_strategy_request(url, headers, request_data)
            
            if result and (result.get("code") == 0 or result.get("success")):  # 兼容不同的成功标识
                self.logger.bind(tag=TAG).info(f"用户策略删除成功: jobId={job_id}")
                return {
                    "success": True,
                    "message": result.get("msg", "删除成功"),
                    "data": result.get("data")
                }
            else:
                error_msg = result.get("msg", "未知错误") if result else "请求失败"
                self.logger.bind(tag=TAG).error(f"用户策略删除失败: {error_msg}")
                return {
                    "success": False,
                    "message": f"删除失败: {error_msg}",
                    "data": None
                }
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"删除用户策略失败: {e}")
            return {
                "success": False,
                "message": f"删除失败: {str(e)}",
                "data": None
            }
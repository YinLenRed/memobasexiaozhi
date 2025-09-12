from typing import List, Dict
from ..base import IntentProviderBase
from plugins_func.functions.play_music import initialize_music_handler
from config.logger import setup_logging
from core.utils.llm_pool import get_llm_pool
from ..smart_mcp_filter import should_enable_mcp_for_input, get_smart_filtered_mcp_tools
import re
import json
import hashlib
import time
import asyncio

TAG = __name__
logger = setup_logging()


class IntentProvider(IntentProviderBase):
    def __init__(self, config):
        super().__init__(config)
        self.llm = None
        self.promot = ""
        # 导入全局缓存管理器
        from core.utils.cache.manager import cache_manager, CacheType

        self.cache_manager = cache_manager
        self.CacheType = CacheType
        self.history_count = 4  # 默认使用最近4条对话记录

    def get_intent_system_prompt(self, functions_list: str) -> str:
        """
        根据配置的意图选项和可用函数动态生成系统提示词
        Args:
            functions: 可用的函数列表，JSON格式字符串
        Returns:
            格式化后的系统提示词
        """

        # 构建函数说明部分
        functions_desc = "可用的函数列表：\n"
        for func in functions_list:
            func_info = func.get("function", {})
            name = func_info.get("name", "")
            desc = func_info.get("description", "")
            params = func_info.get("parameters", {})

            functions_desc += f"\n函数名: {name}\n"
            functions_desc += f"描述: {desc}\n"

            if params:
                functions_desc += "参数:\n"
                for param_name, param_info in params.get("properties", {}).items():
                    param_desc = param_info.get("description", "")
                    param_type = param_info.get("type", "")
                    functions_desc += f"- {param_name} ({param_type}): {param_desc}\n"

            functions_desc += "---\n"

        prompt = (
            "你是一个意图识别助手。请分析用户的最后一句话，判断用户意图并调用相应的函数。\n\n"
            "- 如果用户使用疑问词（如'怎么'、'为什么'、'如何'）询问退出相关的问题（例如'怎么退出了？'），注意这不是让你退出，请返回 {'function_call': {'name': 'continue_chat'}\n"
            "- 仅当用户明确使用'退出系统'、'结束对话'、'我不想和你说话了'等指令时，才触发 handle_exit_intent\n"
            "- 相对时间定时：当用户说'30分钟后'、'1小时后'、'半小时后'等相对时间表达时，使用 schedule_relative_timer\n"
            "- 绝对时间定时：当用户说'明天早上8点'、'今天下午3点'等绝对时间表达时，使用 save_user_strategy\n"
            "- 查询任务列表：当用户说'查看我的任务列表'、'我有什么任务'、'显示所有任务'、'我设置了什么提醒'等时，使用 query_user_strategies\n"
            "- 查询临时定时器：当用户说'有哪些闹钟'、'查看定时提醒'、'现在设置了什么提醒'等时，使用 list_relative_timers\n"
            "- 修改任务：当用户说'修改任务'、'更改提醒时间'、'修改策略'等时，使用 update_user_strategy\n"
            "- 删除任务：当用户说'删除任务'、'取消提醒'、'删除策略'等时，使用 delete_user_strategy\n"
            "- 取消定时器：当用户说'取消闹钟'、'取消定时器'等时，使用 cancel_relative_timer\n"
            "- 修改定时器：当用户说'修改闹钟'、'修改定时器'等时，使用 modify_relative_timer\n"
            "- 搜索查询：当用户说'搜索'、'查询'、'帮我找'、'了解一下'、'讲个笑话'、'讲个故事'等需要获取信息时，使用 bailian_web_search 工具进行联网搜索，参数名为 query\n"
            "- 💡 智能工具选择：系统已根据用户输入智能筛选了合适的工具。如果没有看到某些工具（如MCP工具），说明当前输入不需要这些功能\n\n"
            f"{functions_desc}\n"
            "处理步骤:\n"
            "1. 分析用户输入，确定用户意图\n"
            "2. 从可用函数列表中选择最匹配的函数\n"
            "3. 如果找到匹配的函数，生成对应的function_call 格式\n"
            '4. 如果没有找到匹配的函数，返回{"function_call": {"name": "continue_chat"}}\n\n'
            "返回格式要求：\n"
            "1. 必须返回纯JSON格式\n"
            "2. 必须包含function_call字段\n"
            "3. function_call必须包含name字段\n"
            "4. 如果函数需要参数，必须包含arguments字段\n\n"
            "示例：\n"
            "```\n"
            "用户: 现在几点了？\n"
            '返回: {"function_call": {"name": "get_time"}}\n'
            "```\n"
            "```\n"
            "用户: 当前电池电量是多少？\n"
            '返回: {"function_call": {"name": "get_battery_level", "arguments": {"response_success": "当前电池电量为{value}%", "response_failure": "无法获取Battery的当前电量百分比"}}}\n'
            "```\n"
            "```\n"
            "用户: 当前屏幕亮度是多少？\n"
            '返回: {"function_call": {"name": "self_screen_get_brightness"}}\n'
            "```\n"
            "```\n"
            "用户: 设置屏幕亮度为50%\n"
            '返回: {"function_call": {"name": "self_screen_set_brightness", "arguments": {"brightness": 50}}}\n'
            "```\n"
            "```\n"
            "用户: 我想结束对话\n"
            '返回: {"function_call": {"name": "handle_exit_intent", "arguments": {"say_goodbye": "goodbye"}}}\n'
            "```\n"
            "```\n"
            "用户: 30分钟后叫我吃饭\n"
            '返回: {"function_call": {"name": "schedule_relative_timer", "arguments": {"duration_text": "30分钟", "reminder_content": "吃饭", "action_type": "叫我"}}}\n'
            "```\n"
            "```\n"
            "用户: 1小时后提醒我开会\n"
            '返回: {"function_call": {"name": "schedule_relative_timer", "arguments": {"duration_text": "1小时", "reminder_content": "开会", "action_type": "提醒我"}}}\n'
            "```\n"
            "```\n"
            "用户: 半小时后通知我休息\n"
            '返回: {"function_call": {"name": "schedule_relative_timer", "arguments": {"duration_text": "半小时", "reminder_content": "休息", "action_type": "通知我"}}}\n'
            "```\n"
            "```\n"
            "用户: 查看我的定时提醒\n"
            '返回: {"function_call": {"name": "list_relative_timers"}}\n'
            "```\n"
            "```\n"
            "用户: 有哪些闹钟\n"
            '返回: {"function_call": {"name": "list_relative_timers"}}\n'
            "```\n"
            "```\n"
            "用户: 取消闹钟\n"
            '返回: {"function_call": {"name": "cancel_relative_timer", "arguments": {"confirm_action": "list"}}}\n'
            "```\n"
            "```\n"
            "用户: 取消12点的提醒\n"
            '返回: {"function_call": {"name": "cancel_relative_timer", "arguments": {"confirm_action": "cancel", "target_time": "12点"}}}\n'
            "```\n"
            "```\n"
            "用户: 删除吃饭提醒\n"
            '返回: {"function_call": {"name": "cancel_relative_timer", "arguments": {"confirm_action": "cancel", "content_keyword": "吃饭"}}}\n'
            "```\n"
            "```\n"
            "用户: 修改闹钟\n"
            '返回: {"function_call": {"name": "modify_relative_timer", "arguments": {"confirm_action": "list"}}}\n'
            "```\n"
            "```\n"
            "用户: 修改12点的提醒\n"
            '返回: {"function_call": {"name": "modify_relative_timer", "arguments": {"confirm_action": "select", "target_time": "12点"}}}\n'
            "```\n"
            "```\n"
            "用户: 改成30分钟后\n"
            '返回: {"function_call": {"name": "modify_relative_timer", "arguments": {"confirm_action": "modify", "new_time": "30分钟后"}}}\n'
            "```\n"
            "```\n"
            "用户: 你好啊\n"
            '返回: {"function_call": {"name": "continue_chat"}}\n'
            "```\n\n"
            "注意：\n"
            "1. 只返回JSON格式，不要包含任何其他文字\n"
            '2. 如果没有找到匹配的函数，返回{"function_call": {"name": "continue_chat"}}\n'
            "3. 确保返回的JSON格式正确，包含所有必要的字段\n"
            "特殊说明：\n"
            "- 当用户单次输入包含多个指令时（如'打开灯并且调高音量'）\n"
            "- 请返回多个function_call组成的JSON数组\n"
            "- 示例：{'function_calls': [{name:'light_on'}, {name:'volume_up'}]}"
        )
        return prompt

    def replyResult(self, text: str, original_text: str):
        # 🔧 使用LLM连接池（暂时关闭并发限制）
        llm_pool = get_llm_pool(max_concurrent=999)
        
        # 由于这是同步方法，需要在事件循环中运行
        try:
            loop = asyncio.get_event_loop()
            future = asyncio.run_coroutine_threadsafe(
                llm_pool.call_llm(
                    self.llm,
                    "response_no_stream",
                    system_prompt=text,
                    user_prompt="请根据以上内容，像人类一样说话的口吻回复用户，要求简洁，请直接返回结果。用户现在说："
                    + original_text,
                ),
                loop
            )
            llm_result = future.result()
        except RuntimeError:
            # 如果没有事件循环，创建新的
            llm_result = asyncio.run(
                llm_pool.call_llm(
                    self.llm,
                    "response_no_stream",
                    system_prompt=text,
                    user_prompt="请根据以上内容，像人类一样说话的口吻回复用户，要求简洁，请直接返回结果。用户现在说："
                    + original_text,
                )
            )
        
        return llm_result

    async def detect_intent(self, conn, dialogue_history: List[Dict], text: str) -> str:
        if not self.llm:
            raise ValueError("LLM provider not set")
        if conn.func_handler is None:
            return '{"function_call": {"name": "continue_chat"}}'

        # 记录整体开始时间
        total_start_time = time.time()

        # 打印使用的模型信息
        model_info = getattr(self.llm, "model_name", str(self.llm.__class__.__name__))
        logger.bind(tag=TAG).debug(f"使用意图识别模型: {model_info}")

        # 计算缓存键
        cache_key = hashlib.md5((conn.device_id + text).encode()).hexdigest()

        # 检查缓存
        cached_intent = self.cache_manager.get(self.CacheType.INTENT, cache_key)
        if cached_intent is not None:
            cache_time = time.time() - total_start_time
            logger.bind(tag=TAG).debug(
                f"使用缓存的意图: {cache_key} -> {cached_intent}, 耗时: {cache_time:.4f}秒"
            )
            return cached_intent

        # 🔧 智能工具选择：根据用户输入动态决定可用工具
        functions = conn.func_handler.get_functions() if conn.func_handler else []
        
        # 如果工具处理器尚未初始化，强制等待初始化完成（带超时）
        if conn.func_handler and not conn.func_handler.finish_init:
            logger.bind(tag=TAG).info("意图识别等待工具处理器初始化完成...")
            try:
                # 🔧 添加5秒超时，防止初始化阻塞对话流程
                await asyncio.wait_for(conn.func_handler._initialize(), timeout=5.0)
                functions = conn.func_handler.get_functions()
                logger.bind(tag=TAG).info("工具处理器初始化完成，获取到函数列表")
            except asyncio.TimeoutError:
                logger.bind(tag=TAG).warning("⚠️ 工具处理器初始化超时(5秒)，使用空函数列表继续处理")
                functions = []
            except Exception as e:
                logger.bind(tag=TAG).error(f"❌ 工具处理器初始化失败: {str(e)}，使用空函数列表继续处理")
                functions = []
        
        # 🔧 智能MCP过滤：根据用户输入决定是否启用MCP工具
        mcp_tools = []
        if hasattr(conn, "mcp_client"):
            all_mcp_tools = conn.mcp_client.get_available_tools()
            if all_mcp_tools is not None and len(all_mcp_tools) > 0:
                # 智能判断是否需要MCP功能
                mcp_filter_result = should_enable_mcp_for_input(text)
                
                if mcp_filter_result["enabled"]:
                    # 获取过滤后的MCP工具
                    mcp_tools = get_smart_filtered_mcp_tools(text, all_mcp_tools)
                    logger.bind(tag=TAG).info(
                        f"🎯 智能启用MCP: {mcp_filter_result['reason']}, "
                        f"关键词: {mcp_filter_result['keywords_matched']}, "
                        f"工具数量: {len(mcp_tools)}/{len(all_mcp_tools)}"
                    )
                else:
                    logger.bind(tag=TAG).debug(
                        f"🚫 智能跳过MCP: {mcp_filter_result['reason']}, "
                        f"关键词: {mcp_filter_result['keywords_matched']}"
                    )
        
        # 合并系统函数和筛选后的MCP工具
        if mcp_tools:
            if functions is None:
                functions = []
            functions.extend(mcp_tools)

        # 每次都重新生成提示词（基于当前可用工具）
        current_prompt = self.get_intent_system_prompt(functions)

        music_config = initialize_music_handler(conn)
        music_file_names = music_config["music_file_names"]
        prompt_music = f"{current_prompt}\n<musicNames>{music_file_names}\n</musicNames>"

        home_assistant_cfg = conn.config["plugins"].get("home_assistant")
        if home_assistant_cfg:
            devices = home_assistant_cfg.get("devices", [])
        else:
            devices = []
        if len(devices) > 0:
            hass_prompt = "\n下面是我家智能设备列表（位置，设备名，entity_id），可以通过homeassistant控制\n"
            for device in devices:
                hass_prompt += device + "\n"
            prompt_music += hass_prompt

        logger.bind(tag=TAG).debug(f"User prompt: {prompt_music}")

        # 构建用户对话历史的提示
        msgStr = ""

        # 获取最近的对话历史
        start_idx = max(0, len(dialogue_history) - self.history_count)
        for i in range(start_idx, len(dialogue_history)):
            dialogue_item = dialogue_history[i]
            # 🔧 兼容字典和对象两种格式
            if isinstance(dialogue_item, dict):
                role = dialogue_item.get("role", "user")
                content = dialogue_item.get("content", "")
            else:
                role = getattr(dialogue_item, "role", "user")
                content = getattr(dialogue_item, "content", "")
            msgStr += f"{role}: {content}\n"

        msgStr += f"User: {text}\n"
        user_prompt = f"current dialogue:\n{msgStr}"

        # 记录预处理完成时间
        preprocess_time = time.time() - total_start_time
        logger.bind(tag=TAG).debug(f"意图识别预处理耗时: {preprocess_time:.4f}秒")

        # 使用LLM进行意图识别
        llm_start_time = time.time()
        logger.bind(tag=TAG).debug(f"开始LLM意图识别调用, 模型: {model_info}")

        # 🔧 使用LLM连接池（暂时关闭并发限制）
        llm_pool = get_llm_pool(max_concurrent=999)
        intent = await llm_pool.call_llm(
            self.llm,
            "response_no_stream",
            system_prompt=prompt_music, 
            user_prompt=user_prompt
        )

        # 记录LLM调用完成时间
        llm_time = time.time() - llm_start_time
        logger.bind(tag=TAG).debug(
            f"LLM意图识别完成, 模型: {model_info}, 调用耗时: {llm_time:.4f}秒"
        )

        # 记录后处理开始时间
        postprocess_start_time = time.time()

        # 清理和解析响应
        intent = intent.strip()
        # 使用更智能的JSON提取方法
        # 找到第一个{，然后匹配平衡的括号
        start_pos = intent.find('{')
        if start_pos != -1:
            brace_count = 0
            end_pos = start_pos
            for i, char in enumerate(intent[start_pos:], start_pos):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break
            
            if brace_count == 0:  # 找到了完整的JSON
                intent = intent[start_pos:end_pos]

        # 记录总处理时间
        total_time = time.time() - total_start_time
        logger.bind(tag=TAG).debug(
            f"【意图识别性能】模型: {model_info}, 总耗时: {total_time:.4f}秒, LLM调用: {llm_time:.4f}秒, 查询: '{text[:20]}...'"
        )

        # 尝试解析为JSON
        try:
            intent_data = json.loads(intent)
            # 如果包含function_call，则格式化为适合处理的格式
            if "function_call" in intent_data:
                function_data = intent_data["function_call"]
                function_name = function_data.get("name")
                function_args = function_data.get("arguments", {})

                # 记录识别到的function call
                logger.bind(tag=TAG).info(
                    f"llm 识别到意图: {function_name}, 参数: {function_args}"
                )

                # 如果是继续聊天，清理工具调用相关的历史消息
                if function_name == "continue_chat":
                    # 保留非工具相关的消息
                    clean_history = [
                        msg
                        for msg in conn.dialogue.dialogue
                        if msg.role not in ["tool", "function"]
                    ]
                    conn.dialogue.dialogue = clean_history

                # 添加到缓存
                self.cache_manager.set(self.CacheType.INTENT, cache_key, intent)

                # 后处理时间
                postprocess_time = time.time() - postprocess_start_time
                logger.bind(tag=TAG).debug(f"意图后处理耗时: {postprocess_time:.4f}秒")

                # 确保返回完全序列化的JSON字符串
                return intent
            else:
                # 添加到缓存
                self.cache_manager.set(self.CacheType.INTENT, cache_key, intent)

                # 后处理时间
                postprocess_time = time.time() - postprocess_start_time
                logger.bind(tag=TAG).debug(f"意图后处理耗时: {postprocess_time:.4f}秒")

                # 返回普通意图
                return intent
        except json.JSONDecodeError:
            # 后处理时间
            postprocess_time = time.time() - postprocess_start_time
            logger.bind(tag=TAG).error(
                f"无法解析意图JSON: {intent}, 后处理耗时: {postprocess_time:.4f}秒"
            )
            # 如果解析失败，默认返回继续聊天意图
            return '{"intent": "继续聊天"}'

import json
import uuid
import time
import asyncio
import threading
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from core.mqtt.mqtt_client import MQTTClient
from core.utils import llm as llm_utils
from core.utils import tts as tts_utils
from core.providers.tts.base import TTSProviderBase
from core.tools.weather_tool import WeatherTool, get_weather_info, WEATHER_FUNCTION_DEFINITION
from core.tools.memobase_client import MemobaseClient, get_user_memory_text, MEMORY_FUNCTION_DEFINITION
from core.tools.news_tool import NewsTool, get_news_info, NEWS_FUNCTION_DEFINITION, execute_news_function
from core.tools.music_tool import MusicTool, get_music_info, MUSIC_FUNCTION_DEFINITION, execute_music_function
from config.logger import setup_logging
from config.manage_api_client import forward_log_to_java
from core.utils.encoding_helper import safe_encode_string, safe_encode_dict

TAG = __name__


class ProactiveGreetingService:
    """主动问候服务"""
    
    def __init__(self, config: Dict[str, Any], mqtt_client: MQTTClient, llm_instance=None, tts_instance=None):
        self.config = config
        self.mqtt_client = mqtt_client
        self.logger = setup_logging()
        
        # 使用传入的实例或稍后初始化
        self.llm = llm_instance
        self.tts = tts_instance
        
        # 标记是否使用外部实例
        self.use_external_llm = llm_instance is not None
        self.use_external_tts = tts_instance is not None
        
        # 记忆和用户信息
        self.memory = None
        self.user_profiles: Dict[str, Dict] = {}
        
        # 工具集成
        self.weather_tool = WeatherTool(config)
        self.memobase_client = MemobaseClient(config)
        self.news_tool = NewsTool(config)
        self.music_tool = MusicTool(config)
        
        # 问候内容生成配置
        self.greeting_prompts = {
            "system_reminder": "你是一个贴心的AI助手，需要根据系统提醒为用户生成温馨的问候语。请用亲切自然的语气，结合用户的基本信息。",
            "schedule": "你是一个贴心的AI助手，需要根据用户日程安排生成提醒式的问候语。请用关怀的语气提醒用户重要事项。",
            "weather": "你是一个贴心的AI助手，需要根据天气信息为用户生成实用的问候语。请结合天气情况给出合适的建议。",
            "entertainment": "你是一个贴心的AI助手，需要根据娱乐内容为用户生成有趣的问候语。请用轻松愉快的语气分享内容。",
            "music": "你是一个贴心的AI助手，需要根据音乐推荐为用户生成温馨的问候语。请用温和愉悦的语气介绍音乐，帮助用户放松心情。",
            "news": "你是一个贴心的AI助手，需要根据新闻内容为用户生成信息性的问候语。请用客观友善的语气传递信息。"
        }
        
        # 运行状态
        self.running = False
        self.greeting_tasks: Dict[str, asyncio.Task] = {}
        
        # 注册MQTT消息处理器
        self.mqtt_client.register_message_handler("greeting", self._handle_device_event)
        
    async def start(self):
        """启动主动问候服务"""
        if self.running:
            return
            
        self.running = True
        
        # 初始化LLM（如果没有外部实例）
        if not self.use_external_llm:
            await self._initialize_llm()
        else:
            self.logger.bind(tag=TAG).info("使用外部LLM实例")
        
        # 初始化TTS（如果没有外部实例）
        if not self.use_external_tts:
            await self._initialize_tts()
        else:
            self.logger.bind(tag=TAG).info("使用外部TTS实例")
        
        # 记录最终状态
        llm_status = "✅ 可用" if self.llm is not None else "❌ 不可用"
        tts_status = "✅ 可用" if self.tts is not None else "❌ 不可用"
        self.logger.bind(tag=TAG).info(f"主动问候服务启动成功 - LLM: {llm_status}, TTS: {tts_status}")
    
    async def stop(self):
        """停止主动问候服务"""
        if not self.running:
            return
            
        self.running = False
        
        # 取消所有问候任务
        for task in self.greeting_tasks.values():
            if not task.done():
                task.cancel()
        
        self.greeting_tasks.clear()
        
        self.logger.bind(tag=TAG).info("主动问候服务已停止")
    
    async def _initialize_llm(self):
        """初始化LLM"""
        try:
            # 获取LLM配置
            llm_config = self.config.get("LLM", {})
            selected_llm = self.config.get("selected_module", {}).get("LLM", "ChatGLMLLM")
            
            # 检查配置是否存在
            if not llm_config:
                self.logger.bind(tag=TAG).warning("未找到LLM配置段，将使用简化模式（无LLM内容生成）")
                return
            
            if not selected_llm:
                self.logger.bind(tag=TAG).warning("未指定选中的LLM模块")
                return
            
            if selected_llm not in llm_config:
                self.logger.bind(tag=TAG).warning(f"未找到指定的LLM配置: {selected_llm}，可用配置: {list(llm_config.keys())}")
                # 尝试使用第一个可用的配置
                if llm_config:
                    available_llm = list(llm_config.keys())[0]
                    self.logger.bind(tag=TAG).info(f"尝试使用第一个可用的LLM配置: {available_llm}")
                    selected_llm = available_llm
                else:
                    return
            
            llm_type = llm_config[selected_llm].get("type", selected_llm)
            self.llm = llm_utils.create_instance(llm_type, llm_config[selected_llm])
            self.logger.bind(tag=TAG).info(f"LLM初始化成功: {selected_llm} (类型: {llm_type})")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM初始化失败: {e}")
            self.logger.bind(tag=TAG).warning("将在无LLM模式下运行")
    
    async def _initialize_tts(self):
        """初始化TTS"""
        try:
            # 获取TTS配置
            tts_config = self.config.get("TTS", {})
            selected_tts = self.config.get("selected_module", {}).get("TTS", "EdgeTTS")
            
            # 检查配置是否存在
            if not tts_config:
                self.logger.bind(tag=TAG).warning("未找到TTS配置段，将使用简化模式（无TTS音频生成）")
                return
            
            if not selected_tts:
                self.logger.bind(tag=TAG).warning("未指定选中的TTS模块")
                return
            
            if selected_tts not in tts_config:
                self.logger.bind(tag=TAG).warning(f"未找到指定的TTS配置: {selected_tts}，可用配置: {list(tts_config.keys())}")
                # 尝试使用第一个可用的配置
                if tts_config:
                    available_tts = list(tts_config.keys())[0]
                    self.logger.bind(tag=TAG).info(f"尝试使用第一个可用的TTS配置: {available_tts}")
                    selected_tts = available_tts
                else:
                    return
            
            tts_type = tts_config[selected_tts].get("type", selected_tts)
            self.tts = tts_utils.create_instance(tts_type, tts_config[selected_tts])
            self.logger.bind(tag=TAG).info(f"TTS初始化成功: {selected_tts} (类型: {tts_type})")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"TTS初始化失败: {e}")
            self.logger.bind(tag=TAG).warning("将在无TTS模式下运行")
    
    async def generate_greeting_content(
        self, 
        initial_content: str, 
        category: str, 
        user_info: Dict[str, Any], 
        memory_info: str = None,
        device_id: str = None
    ) -> str:
        """生成主动问候内容"""
        try:
            # 获取对应类别的prompt
            system_prompt = self.greeting_prompts.get(category, self.greeting_prompts["system_reminder"])
            
            # 构建用户上下文
            user_context = await self._build_user_context(user_info, memory_info, device_id)
            
            # 特殊处理：天气类别时获取实时天气信息
            enhanced_content = initial_content
            if category == "weather" and device_id:
                try:
                    weather_info = await self.weather_tool.get_weather_by_device(device_id)
                    weather_text = self.weather_tool.format_weather_for_greeting(weather_info)
                    enhanced_content = f"{initial_content}。{weather_text}"
                    self.logger.bind(tag=TAG).info(f"已获取设备 {device_id} 的天气信息")
                except Exception as e:
                    self.logger.bind(tag=TAG).warning(f"获取天气信息失败，使用原始内容: {e}")
            
            # 特殊处理：新闻类别时获取最新新闻信息
            if category == "news":
                try:
                    news_list = await self.news_tool.get_elderly_news(user_info)
                    news_text = self.news_tool.format_news_for_greeting(news_list)
                    enhanced_content = f"{initial_content}。{news_text}"
                    self.logger.bind(tag=TAG).info(f"已获取老年人新闻信息，共{len(news_list)}条")
                except Exception as e:
                    self.logger.bind(tag=TAG).warning(f"获取新闻信息失败，使用原始内容: {e}")
            
            # 特殊处理：音乐类别时获取音乐推荐信息
            if category == "music" or category == "entertainment":
                try:
                    music_list = await self.music_tool.get_elderly_music(user_info)
                    music_text = self.music_tool.format_music_for_greeting(music_list)
                    enhanced_content = f"{initial_content}。{music_text}"
                    self.logger.bind(tag=TAG).info(f"已获取老年人音乐推荐，共{len(music_list)}首")
                except Exception as e:
                    self.logger.bind(tag=TAG).warning(f"获取音乐推荐失败，使用原始内容: {e}")
            
            # 构建完整prompt
            user_prompt = f"""
            请根据以下信息生成一段温馨的问候语：

            初始内容：{enhanced_content}
            类别：{category}
            用户信息：{user_context}

            要求：
            1. 语言亲切自然，符合老年人交流习惯
            2. 内容简洁明了，控制在50字以内
            3. 结合用户信息个性化问候
            4. 根据内容类别调整语气和重点
            """
            
            # 调用LLM生成内容
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            if self.llm:
                # 支持Function Calling的LLM调用
                response = await self._call_llm_with_tools(messages, category, device_id)
                
                # 清理和验证生成的内容
                greeting_text = self._clean_generated_text(response)
                
                # 如果LLM生成的内容为空或无效，使用原始内容作为fallback
                if not greeting_text or greeting_text == "您好！有什么可以帮助您的吗？":
                    self.logger.bind(tag=TAG).warning("LLM生成内容无效，使用原始内容作为fallback")
                    return self._generate_template_greeting(initial_content, user_info)
                
                self.logger.bind(tag=TAG).info(f"生成问候内容成功: {greeting_text[:30]}...")
                return greeting_text
            else:
                # 如果LLM不可用，返回简单的模板问候
                return self._generate_template_greeting(enhanced_content, user_info)
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"生成问候内容失败: {e}")
            return self._generate_template_greeting(initial_content, user_info)
    
    async def _call_llm_with_tools(self, messages: List[Dict], category: str, device_id: str = None) -> str:
        """调用LLM接口，支持Function Calling"""
        try:
            loop = asyncio.get_event_loop()
            
            def call_llm_sync():
                # 根据类别决定是否使用tools
                if hasattr(self.llm, 'response_with_functions') and (
                    (category == "weather" and device_id) or category == "news" or category == "music" or category == "entertainment"
                ):
                    # 使用Function Calling
                    functions = []
                    if category == "weather" and device_id:
                        functions.append(WEATHER_FUNCTION_DEFINITION)
                    if category == "news":
                        functions.append(NEWS_FUNCTION_DEFINITION)
                    if category == "music" or category == "entertainment":
                        functions.append(MUSIC_FUNCTION_DEFINITION)
                    
                    responses = self.llm.response_with_functions("greeting_session", messages, functions=functions)
                    
                    result = ""
                    for response in responses:
                        if isinstance(response, tuple) and len(response) == 2:
                            content, tools_call = response
                            if content:
                                result += content
                            # 处理工具调用
                            if tools_call and len(tools_call) > 0:
                                for tool_call in tools_call:
                                    if tool_call.function.name == "get_weather_info":
                                        # 天气工具调用处理
                                        pass
                                    elif tool_call.function.name == "get_latest_news":
                                        # 新闻工具调用处理
                                        pass
                                    elif tool_call.function.name == "get_music_recommendation":
                                        # 音乐工具调用处理
                                        pass
                        elif isinstance(response, str):
                            result += response
                        elif isinstance(response, dict) and "content" in response:
                            result += response["content"]
                    return result
                else:
                    # 普通LLM调用
                    return self._call_llm_simple(messages)
            
            result = await loop.run_in_executor(None, call_llm_sync)
            return result
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"调用LLM失败: {e}")
            return "抱歉，暂时无法生成问候内容。"
    
    def _call_llm_simple(self, messages: List[Dict]) -> str:
        """简单的LLM调用，使用安全编码处理"""
        try:
            # 使用编码辅助函数确保消息安全
            safe_messages = []
            for msg in messages:
                safe_msg = safe_encode_dict(msg)
                safe_messages.append(safe_msg)
            
            self.logger.bind(tag=TAG).info(f"调用LLM，消息数: {len(safe_messages)}")
            
            # 假设LLM有response方法，需要根据实际接口调整
            if hasattr(self.llm, 'response'):
                responses = self.llm.response("greeting_session", safe_messages)
                result = ""
                for response in responses:
                    if isinstance(response, str):
                        # 使用安全编码函数处理响应
                        result += safe_encode_string(response)
                    elif isinstance(response, dict) and "content" in response:
                        content = response["content"]
                        if isinstance(content, str):
                            result += safe_encode_string(content)
                        else:
                            result += safe_encode_string(str(content))
                return result
            else:
                return "抱歉，暂时无法生成问候内容。"
        except Exception as e:
            # 使用安全编码处理异常信息
            safe_error = safe_encode_string(str(e), "LLM调用异常")
            self.logger.bind(tag=TAG).error(f"简单LLM调用失败: {safe_error}")
            return "抱歉，暂时无法生成问候内容。"
    
    async def _call_llm(self, messages: List[Dict]) -> str:
        """调用LLM接口（向后兼容）"""
        return self._call_llm_simple(messages)
    
    async def _build_user_context(self, user_info: Dict[str, Any], memory_info: str = None, device_id: str = None) -> str:
        """构建用户上下文信息"""
        context_parts = []
        
        # 基本信息
        if "name" in user_info:
            context_parts.append(f"姓名：{user_info['name']}")
        if "age" in user_info:
            context_parts.append(f"年龄：{user_info['age']}")
        if "location" in user_info:
            context_parts.append(f"地址：{user_info['location']}")
        
        # 从memobase获取记忆信息
        if self.memobase_client.enabled and user_info.get("id") and device_id:
            try:
                memobase_memories = await get_user_memory_text(self.config, user_info["id"], device_id)
                if memobase_memories:
                    context_parts.append(f"历史记忆：{memobase_memories}")
                    self.logger.bind(tag=TAG).info(f"已获取用户 {user_info['id']} 的记忆信息")
            except Exception as e:
                self.logger.bind(tag=TAG).warning(f"获取memobase记忆失败: {e}")
        
        # 个性化记忆信息（向后兼容）
        if memory_info:
            context_parts.append(f"个人记忆：{memory_info}")
        
        # 时间信息
        current_time = datetime.now()
        time_info = f"当前时间：{current_time.strftime('%Y年%m月%d日 %H:%M')}"
        context_parts.append(time_info)
        
        return "，".join(context_parts)
    
    def _clean_generated_text(self, text: str) -> str:
        """清理生成的文本"""
        if not text:
            return "您好！有什么可以帮助您的吗？"
        
        # 移除多余的标点和空白
        text = text.strip()
        
        # 确保以合适的标点结尾
        if not text.endswith(("。", "！", "？", "~")):
            text += "。"
        
        # 限制长度
        if len(text) > 100:
            text = text[:97] + "..."
        
        return text
    
    def _generate_template_greeting(self, initial_content: str, user_info: Dict[str, Any]) -> str:
        """生成模板问候语（备用方案）"""
        user_name = user_info.get("name", "")
        if user_name:
            return f"{user_name}，{initial_content}"
        else:
            return f"您好！{initial_content}"
    
    async def synthesize_speech(self, text: str) -> str:
        """合成语音，返回音频文件路径"""
        try:
            if not self.tts:
                self.logger.bind(tag=TAG).warning("TTS未初始化，跳过语音合成")
                return ""
            
            # 确保输出目录存在
            output_dir = getattr(self.tts, 'output_file', 'tmp/')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                
            # 生成完整的临时文件路径
            filename = os.path.join(output_dir, f"greeting_{uuid.uuid4().hex[:8]}.wav")
            self.logger.bind(tag=TAG).info(f"生成TTS文件路径: {filename}")
            
            # 调用TTS合成
            audio_data = await self._call_tts(text, filename)
            
            if audio_data and len(audio_data) > 0:
                # 检查文件是否存在，如果不存在则重新写入
                if not os.path.exists(filename):
                    self.logger.bind(tag=TAG).warning(f"TTS文件被删除，重新写入: {filename}")
                    with open(filename, 'wb') as f:
                        f.write(audio_data)
                
                # 为了防止TTS自动删除，创建一个专用的副本
                # 修复：使用标准音频扩展名，确保TTS队列和ffmpeg能正确识别
                persistent_filename = os.path.join(output_dir, f"persistent_greeting_{uuid.uuid4().hex[:8]}.wav")
                import shutil
                
                if os.path.exists(filename):
                    shutil.copy2(filename, persistent_filename)
                    self.logger.bind(tag=TAG).info(f"创建持久音频文件: {persistent_filename}")
                    return persistent_filename
                else:
                    # 如果原文件不存在，直接写入到持久文件
                    with open(persistent_filename, 'wb') as f:
                        f.write(audio_data)
                    self.logger.bind(tag=TAG).info(f"直接创建持久音频文件: {persistent_filename}")
                    return persistent_filename
            else:
                self.logger.bind(tag=TAG).warning("语音合成失败: 生成的音频数据为空")
                return ""
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"语音合成失败: {e}")
            return ""
    
    async def _call_tts(self, text: str, filename: str) -> bytes:
        """调用TTS接口 - 使用to_tts方法确保正确的音频格式转换"""
        try:
            # 重要修复：使用to_tts方法，而不是text_to_speak
            # to_tts会自动进行音频格式转换(audio_bytes_to_data)，确保生成Opus格式
            loop = asyncio.get_event_loop()
            
            def call_tts_sync():
                if hasattr(self.tts, 'to_tts'):
                    # 使用to_tts方法，它会自动进行格式转换
                    self.logger.bind(tag=TAG).info("使用to_tts方法进行音频合成（与普通对话一致）")
                    opus_frames = self.tts.to_tts(text)
                    
                    if opus_frames and len(opus_frames) > 0:
                        # 将Opus帧转换为字节数据用于文件保存
                        from core.utils.util import opus_datas_to_wav_bytes
                        try:
                            # 转换为WAV字节数据保存到文件
                            wav_bytes = opus_datas_to_wav_bytes(opus_frames, sample_rate=16000)
                            if filename:
                                with open(filename, 'wb') as f:
                                    f.write(wav_bytes)
                                self.logger.bind(tag=TAG).info(f"音频文件保存成功: {filename}")
                            return wav_bytes
                        except Exception as convert_error:
                            self.logger.bind(tag=TAG).error(f"Opus转WAV失败: {convert_error}")
                            # 降级：直接返回第一个Opus帧作为示例
                            return opus_frames[0] if opus_frames else b""
                    else:
                        self.logger.bind(tag=TAG).warning("to_tts返回空音频数据")
                        return b""
                else:
                    # 降级到text_to_speak（保持兼容性）
                    self.logger.bind(tag=TAG).warning("TTS对象没有to_tts方法，降级使用text_to_speak")
                    if hasattr(self.tts, 'text_to_speak'):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result = loop.run_until_complete(self.tts.text_to_speak(text, filename))
                            if filename and os.path.exists(filename):
                                with open(filename, 'rb') as f:
                                    audio_data = f.read()
                                if self.tts.delete_audio_file:
                                    os.remove(filename)
                                return audio_data
                            return result or b""
                        finally:
                            loop.close()
                    else:
                        self.logger.bind(tag=TAG).error("TTS对象既没有to_tts也没有text_to_speak方法")
                        return b""
            
            result = await loop.run_in_executor(None, call_tts_sync)
            return result if result else b""
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"调用TTS失败: {e}")
            return b""
    
    async def send_proactive_greeting(
        self, 
        device_id: str, 
        initial_content: str, 
        category: str, 
        user_info: Dict[str, Any] = None,
        memory_info: str = None
    ) -> str:
        """发送主动问候"""
        try:
            self.logger.bind(tag=TAG).info(f"开始主动问候: {device_id} - {category}")
            
            # 生成问候内容（传入device_id用于天气查询）
            greeting_text = await self.generate_greeting_content(
                initial_content, category, user_info or {}, memory_info, device_id
            )
            
            # 合成语音
            audio_file_path = await self.synthesize_speech(greeting_text)
            
            # 检查音频生成是否成功
            if not audio_file_path:
                self.logger.bind(tag=TAG).error("语音合成失败，无法发送主动问候")
                raise Exception("语音合成失败")
            
            # 生成track_id
            track_id = f"WX{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"
            
            # 注册ACK处理器
            self.mqtt_client.register_ack_handler(
                track_id, 
                lambda device_id, data: self._handle_device_ack(device_id, data, audio_file_path, greeting_text)
            )
            
            # 发送MQTT命令
            await self.mqtt_client.send_speak_command(device_id, greeting_text, track_id)
            
            # 保存交互记忆到memobase
            if user_info and user_info.get("id"):
                try:
                    await self.memobase_client.save_interaction_memory(
                        user_id=user_info["id"],
                        device_id=device_id,
                        greeting_content=greeting_text,
                        interaction_type="proactive_greeting"
                    )
                    self.logger.bind(tag=TAG).info(f"交互记忆已保存到memobase: {user_info['id']}")
                except Exception as e:
                    self.logger.bind(tag=TAG).warning(f"保存交互记忆失败: {e}")
            
            self.logger.bind(tag=TAG).info(f"主动问候发送成功: {track_id}")
            return track_id
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"发送主动问候失败: {e}")
            raise
    
    def _handle_device_ack(self, device_id: str, ack_data: Dict, audio_file_path: str, greeting_text: str):
        """处理设备ACK，发送音频数据"""
        try:
            self.logger.bind(tag=TAG).info(f"收到设备ACK: {device_id}")
            
            # 这里应该通过某种方式将音频数据发送给设备
            # 具体实现取决于音频传输方式（HTTP、WebSocket等）
            # 使用事件循环安全的方式调度协程
            if self.mqtt_client and hasattr(self.mqtt_client, '_main_loop') and self.mqtt_client._main_loop:
                if not self.mqtt_client._main_loop.is_closed():
                    # 从ACK数据中获取track_id
                    track_id = ack_data.get("track_id", "UNKNOWN")
                    asyncio.run_coroutine_threadsafe(
                        self._send_audio_to_device(device_id, audio_file_path, track_id, greeting_text),
                        self.mqtt_client._main_loop
                    )
                else:
                    self.logger.bind(tag=TAG).warning("主事件循环不可用，跳过音频发送")
            else:
                self.logger.bind(tag=TAG).warning("MQTT客户端事件循环不可用，跳过音频发送")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理设备ACK失败: {e}")
    
    async def _send_audio_to_device(self, device_id: str, audio_file_path: str, track_id: str, greeting_text: str):
        """发送音频数据到设备 - 使用文件路径，参考普通对话实现"""
        try:
            self.logger.bind(tag=TAG).info(f"发送音频文件到设备: {device_id}, 文件: {audio_file_path}, track_id: {track_id}")
            
            # 通过WebSocket服务器发送音频数据
            if hasattr(self.mqtt_client, 'websocket_server') and self.mqtt_client.websocket_server:
                # 重要修复：使用相同的track_id，确保MQTT命令和WebSocket音频能被硬件正确关联
                # 直接使用传入的track_id参数
                audio_track_id = track_id  # 使用从ACK中获取的track_id
                
                success = await self.mqtt_client.websocket_server.send_audio_to_device(
                    device_id, audio_file_path, audio_track_id, greeting_text
                )
                
                if success:
                    self.logger.bind(tag=TAG).info(f"WebSocket音频发送成功: {device_id}")
                else:
                    self.logger.bind(tag=TAG).warning(f"WebSocket音频发送失败，可能设备未连接: {device_id}")
            else:
                self.logger.bind(tag=TAG).error("WebSocket服务器不可用，无法发送音频")
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"发送音频数据失败: {e}")
    
    def _handle_device_event(self, device_id: str, event_type: str, event_data: Dict):
        """处理设备事件"""
        try:
            if event_type == "EVT_SPEAK_DONE":
                track_id = event_data.get("track_id")
                timestamp = event_data.get("timestamp")
                
                self.logger.bind(tag=TAG).info(f"设备播放完成: {device_id} - {track_id}")
                
                # 转发日志到Java后端
                # 使用事件循环安全的方式调度协程
                if self.mqtt_client and hasattr(self.mqtt_client, '_main_loop') and self.mqtt_client._main_loop:
                    if not self.mqtt_client._main_loop.is_closed():
                        asyncio.run_coroutine_threadsafe(
                            self._forward_log_to_java(device_id, event_data),
                            self.mqtt_client._main_loop
                        )
                    else:
                        self.logger.bind(tag=TAG).warning("主事件循环不可用，跳过日志转发")
                else:
                    self.logger.bind(tag=TAG).warning("MQTT客户端事件循环不可用，跳过日志转发")
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理设备事件失败: {e}")
    
    async def _forward_log_to_java(self, device_id: str, event_data: Dict):
        """转发日志到Java后端"""
        try:
            # 检查是否启用日志转发
            enable_log_forward = self.config.get("manager-api", {}).get("enable_log_forward", True)
            if not enable_log_forward:
                self.logger.bind(tag=TAG).debug(f"日志转发已禁用: {device_id}")
                return
            
            log_data = {
                "device_id": device_id,
                "event_type": "proactive_greeting_complete",
                "event_data": event_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # 修复：使用异步方式调用同步函数
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: forward_log_to_java(self.config, log_data))
            
            if result:
                self.logger.bind(tag=TAG).info(f"日志转发成功: {device_id}")
            else:
                self.logger.bind(tag=TAG).warning(f"日志转发返回空结果: {device_id}")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"转发日志失败: {e}")
            # 日志转发失败不应该影响主要功能，只记录错误即可
    
    def update_user_profile(self, device_id: str, user_info: Dict[str, Any]):
        """更新用户档案"""
        self.user_profiles[device_id] = user_info
        self.logger.bind(tag=TAG).info(f"更新用户档案: {device_id}")
    
    def get_user_profile(self, device_id: str) -> Dict[str, Any]:
        """获取用户档案"""
        return self.user_profiles.get(device_id, {})

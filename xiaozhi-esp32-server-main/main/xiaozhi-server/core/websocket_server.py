import asyncio
import websockets
import json
import time
import os
import uuid
from config.logger import setup_logging
from core.connection import ConnectionHandler
from config.config_loader import get_config_from_api
from core.utils.modules_initialize import initialize_modules
from core.utils.util import check_vad_update, check_asr_update
from core.handle.sendAudioHandle import send_tts_message, sendAudio, sendAudioMessage
from core.providers.tts.dto.dto import SentenceType
# 🚀 WebSocket预缓冲优化导入
from core.utils.websocket_performance_monitor import get_performance_monitor, log_optimization_result

TAG = __name__


class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.config_lock = asyncio.Lock()
        modules = initialize_modules(
            self.logger,
            self.config,
            "VAD" in self.config["selected_module"],
            "ASR" in self.config["selected_module"],
            "LLM" in self.config["selected_module"],
            False,
            "Memory" in self.config["selected_module"],  # 重新启用Memory模块
            "Intent" in self.config["selected_module"],
        )
        self._vad = modules["vad"] if "vad" in modules else None
        self._asr = modules["asr"] if "asr" in modules else None
        self._llm = modules["llm"] if "llm" in modules else None
        self._intent = modules["intent"] if "intent" in modules else None
        self._memory = modules["memory"] if "memory" in modules else None

        self.active_connections = set()

    async def start(self):
        server_config = self.config["server"]
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("port", 8000))

        async with websockets.serve(
            self._handle_connection, host, port, process_request=self._http_response
        ):
            await asyncio.Future()

    async def _handle_connection(self, websocket):
        """处理新连接，每次创建独立的ConnectionHandler"""
        # 创建ConnectionHandler时传入当前server实例
        handler = ConnectionHandler(
            self.config,
            self._vad,
            self._asr,
            self._llm,
            self._memory,
            self._intent,
            self,  # 传入server实例
        )
        self.active_connections.add(handler)
        try:
            await handler.handle_connection(websocket)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理连接时出错: {e}")
        finally:
            # 确保从活动连接集合中移除
            self.active_connections.discard(handler)
            # 强制关闭连接（如果还没有关闭的话）
            try:
                # 安全地检查WebSocket状态并关闭
                if hasattr(websocket, "closed") and not websocket.closed:
                    await websocket.close()
                elif hasattr(websocket, "state") and websocket.state.name != "CLOSED":
                    await websocket.close()
                else:
                    # 如果没有closed属性，直接尝试关闭
                    await websocket.close()
            except Exception as close_error:
                self.logger.bind(tag=TAG).error(
                    f"服务器端强制关闭连接时出错: {close_error}"
                )

    async def _http_response(self, websocket, request_headers):
        # 检查是否为 WebSocket 升级请求
        if request_headers.headers.get("connection", "").lower() == "upgrade":
            # 如果是 WebSocket 请求，返回 None 允许握手继续
            return None
        else:
            # 如果是普通 HTTP 请求，返回 "server is running"
            return websocket.respond(200, "Server is running\n")

    def find_device_connection(self, device_id: str):
        """根据设备ID查找对应的WebSocket连接"""
        for connection in self.active_connections:
            if hasattr(connection, 'device_id') and connection.device_id == device_id:
                return connection
        return None
    
    async def send_audio_to_device(self, device_id: str, audio_file_path: str, track_id: str, greeting_text: str = None) -> bool:
        """发送音频数据到指定设备 - 完全参考普通对话实现"""
        try:
            # 导入必需模块
            import uuid
            from core.providers.tts.dto.dto import TTSMessageDTO, ContentType
            
            # 🔧 优化连接等待机制，减少卡顿（基于硬件反馈优化）
            connection = None
            max_retries = 3  # 减少重试次数从6次到3次
            retry_delay = 0.5  # 减少等待时间从1秒到0.5秒
            
            for retry in range(max_retries):
                connection = self.find_device_connection(device_id)
                if connection and connection.websocket:
                    self.logger.bind(tag=TAG).info(f"找到设备连接: {device_id} (重试 {retry+1}/{max_retries})")
                    break
                    
                if retry < max_retries - 1:  # 不是最后一次重试
                    self.logger.bind(tag=TAG).info(f"设备连接未就绪，快速重试: {device_id} (重试 {retry+1}/{max_retries})")
                    await asyncio.sleep(retry_delay)  # 减少等待时间
                    
            if connection and connection.websocket:
                # 导入音频处理工具
                from core.handle.sendAudioHandle import send_tts_message
                
                # 完全参考普通对话：直接使用TTS基类的音频处理方法
                try:
                    # 读取音频文件内容
                    with open(audio_file_path, 'rb') as f:
                        audio_bytes = f.read()
                    
                    # 自动检测音频格式（基于文件内容，不依赖扩展名）
                    if audio_bytes.startswith(b'RIFF'):
                        audio_format = "wav"
                    elif (audio_bytes.startswith(b'ID3') or 
                          (len(audio_bytes) >= 2 and audio_bytes[0] == 0xff and (audio_bytes[1] & 0xe0) == 0xe0)):
                        audio_format = "mp3"
                    else:
                        # 默认尝试mp3格式（Edge TTS通常生成mp3）
                        audio_format = "mp3"
                    
                    # 使用普通对话相同的音频处理函数
                    from core.utils.util import audio_bytes_to_data
                    opus_frames, duration = audio_bytes_to_data(audio_bytes, audio_format, is_opus=True)
                        
                except Exception as audio_error:
                    self.logger.bind(tag=TAG).error(f"音频格式处理失败: {audio_error}")
                    return False
                
                self.logger.bind(tag=TAG).info(f"音频转换成功: {len(opus_frames)} 帧, 时长 {duration:.2f}s, 格式: {audio_format}")
                
                # 完全模拟普通对话的sendAudioMessage机制（包含stop消息！）
                # 重要修复：使用实际的问候文本内容，而不是模板字符串
                text_content = greeting_text if greeting_text else f"主动问候播放 - {track_id}"
                
                # 🎯 关键修复：调整状态设置时机，避免音频提前终止
                # 不要立即设置llm_finish_task=True，让音频播放完成后再设置
                connection.client_is_speaking = True  # 设置正在播放状态
                connection.client_abort = False  # 确保不被打断
                
                # 🎯 关键修复：使用硬件当前的session_id，而不是生成新的
                if hasattr(connection, 'session_id') and connection.session_id:
                    self.logger.bind(tag=TAG).info(f"使用硬件当前session_id: {connection.session_id}")
                else:
                    # 如果确实没有session_id，才生成新的（但这种情况不应该发生在正常连接中）
                    connection.session_id = str(uuid.uuid4())
                    self.logger.bind(tag=TAG).warning(f"硬件缺少session_id，生成新的: {connection.session_id}")
                
                # 设置句子ID（普通对话中会设置）
                if not hasattr(connection, 'sentence_id') or not connection.sentence_id:
                    connection.sentence_id = str(uuid.uuid4().hex)
                    self.logger.bind(tag=TAG).info(f"生成主动问候句子ID: {connection.sentence_id}")
                
                # 确保连接对象有clearSpeakStatus方法（send_tts_message中会调用）
                if not hasattr(connection, 'clearSpeakStatus'):
                    def clearSpeakStatus():
                        connection.client_is_speaking = False
                        self.logger.bind(tag=TAG).info("主动问候：清除讲话状态")
                    connection.clearSpeakStatus = clearSpeakStatus
                    self.logger.bind(tag=TAG).info("添加clearSpeakStatus方法")
                
                # 初始化TTS第一句话状态（关键！预缓冲的触发条件）
                if connection.tts is not None:
                    connection.tts.tts_audio_first_sentence = True
                    self.logger.bind(tag=TAG).info(f"设置TTS第一句话标志: {connection.tts.tts_audio_first_sentence}")
                else:
                    self.logger.bind(tag=TAG).warning("连接对象没有TTS实例，可能影响预缓冲机制")
                
                # 🎯 **最终修复：使用TTS队列系统，完全模拟普通对话流程**
                # 不再直接调用sendAudioMessage，而是使用_audio_play_priority_thread
                
                # 设置TTS文本内容（用于报告和统计）
                connection.tts_MessageText = text_content
                
                # 🚀 WebSocket + 预缓冲优化：使用完整的TTS序列
                # 🎯 WebSocket + 预缓冲优化: 启动性能监控
                monitor = get_performance_monitor()
                metrics = monitor.start_transmission(
                    device_id=device_id,
                    track_id=track_id, 
                    total_frames=len(opus_frames),
                    audio_duration=duration
                )
                audio_send_start = time.perf_counter()
                
                if connection.tts and hasattr(connection.tts, 'tts_audio_queue'):
                    # 🎯 发送TTS start消息（普通对话的关键步骤！）
                    from core.handle.sendAudioHandle import send_tts_message
                    await send_tts_message(connection, "start")
                    self.logger.bind(tag=TAG).info("🚀 主动问候：发送TTS start消息（启用预缓冲优化）")
                    
                    # 1. 发送FIRST类型消息初始化TTS会话（包含文本）  
                    connection.tts.tts_audio_queue.put((SentenceType.FIRST, [], text_content))
                    self.logger.bind(tag=TAG).info(f"📝 主动问候：发送TTS FIRST消息，文本: {text_content[:30]}...")
                    
                    # 🚀 预缓冲优化: 记录预期的预缓冲帧数
                    expected_prebuffer = min(5 if len(opus_frames) <= 10 else 4 if len(opus_frames) <= 30 else 3, len(opus_frames))
                    monitor.update_prebuffer(track_id, expected_prebuffer, 0)  # 预缓冲时间稍后更新
                    
                    # 2. 🎯 优化音频数据发送：启用智能预缓冲
                    connection.tts.tts_audio_queue.put((SentenceType.LAST, opus_frames, text_content))
                    self.logger.bind(tag=TAG).info(
                        f"🚀 主动问候音频已放入TTS队列: {len(opus_frames)}帧, "
                        f"预计播放时长: {duration:.2f}s, 文本: {text_content[:50]}..."
                    )
                    
                    # 3. 🔧 关键修复：确保TTS stop消息正确发送
                    connection.llm_finish_task = True
                    # 🎯 立即设置TTS完成处理回调，确保音频播放完成后发送stop
                    connection.tts_completion_callback = lambda: asyncio.create_task(
                        self._ensure_tts_stop_message(connection, track_id, text_content)
                    )
                    self.logger.bind(tag=TAG).info("✅ 主动问候：设置任务完成标志并注册stop消息确保机制")
                else:
                    # 降级方案：如果没有TTS队列，直接发送
                    from core.handle.sendAudioHandle import sendAudioMessage
                    connection.llm_finish_task = True  # 直接发送时需要设置
                    await sendAudioMessage(connection, SentenceType.LAST, opus_frames, text_content)
                    self.logger.bind(tag=TAG).warning(f"TTS队列不可用，直接发送音频: {len(opus_frames)}帧")
                
                # 清理临时音频文件
                try:
                    if os.path.exists(audio_file_path) and "persistent_greeting_" in audio_file_path:
                        os.remove(audio_file_path)
                        self.logger.bind(tag=TAG).info(f"已清理临时音频文件: {audio_file_path}")
                except Exception as e:
                    self.logger.bind(tag=TAG).warning(f"清理音频文件失败: {e}")
                
                # 🚀 WebSocket + 预缓冲优化: 完成性能监控和统计
                final_metrics = monitor.finish_transmission(track_id)
                if final_metrics:
                    # 记录优化结果到日志
                    log_optimization_result(self.logger.bind(tag=TAG), final_metrics)
                    
                    # 详细性能报告
                    self.logger.bind(tag=TAG).info(
                        f"🎵 主动问候音频发送完成: 设备={device_id}, "
                        f"帧数={len(opus_frames)}, 时长={duration:.2f}s, "
                        f"发送用时={final_metrics.transmission_time:.1f}ms, "
                        f"预缓冲={final_metrics.prebuffer_frames}帧, "
                        f"优化比例={final_metrics.optimization_ratio:.3f}x, "
                        f"提升倍数={final_metrics.speed_improvement:.2f}x"
                    )
                    
                    # 如果优化效果显著，记录成功案例
                    if final_metrics.optimization_ratio < 0.5:  # 传输时间小于播放时间的50%
                        self.logger.bind(tag=TAG).info(
                            f"🏆 优秀优化案例: 设备{device_id} 达到{final_metrics.optimization_ratio:.3f}x优化比例!"
                        )
                else:
                    self.logger.bind(tag=TAG).warning(f"⚠️ 性能监控数据缺失: {track_id}")
                    
                return True
            else:
                self.logger.bind(tag=TAG).error(f"设备连接检查失败，无法发送音频: {device_id} (已重试{max_retries}次)")
                return False
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"发送音频数据失败: {e}")
            return False

    async def _ensure_tts_stop_message(self, connection, track_id: str, text_content: str):
        """🔧 确保TTS stop消息被正确发送 - 修复硬件反馈的stop消息缺失问题"""
        try:
            # 等待音频播放完成的合理时间
            import time
            from core.handle.sendAudioHandle import send_tts_message
            
            # 🎯 基于文本长度计算等待时间（防止过早发送stop）
            text_length = len(text_content) if text_content else 0
            # 每个字符约0.15秒播放时间 + 2秒缓冲
            estimated_duration = max(2.0, text_length * 0.15 + 2.0)
            
            self.logger.bind(tag=TAG).info(f"⏰ 主动问候音频播放预估时长: {estimated_duration:.1f}秒 (文本{text_length}字符)")
            await asyncio.sleep(estimated_duration)
            
            # 🚫 检查连接状态
            if not connection or not connection.websocket:
                self.logger.bind(tag=TAG).warning(f"连接已断开，跳过stop消息发送: {track_id}")
                return
                
            # 🚫 检查abort状态
            if hasattr(connection, 'client_abort') and connection.client_abort:
                self.logger.bind(tag=TAG).info(f"检测到abort状态，跳过stop消息发送: {track_id}")
                return
            
            # 🔧 强制发送TTS stop消息（修复硬件反馈的关键问题）
            await send_tts_message(connection, "stop", text_content)
            self.logger.bind(tag=TAG).info(f"🎯 主动问候强制发送TTS stop消息完成: {track_id}")
            
            # 🔄 清理状态
            connection.client_is_speaking = False
            connection.llm_finish_task = False
            if hasattr(connection, 'tts_completion_callback'):
                delattr(connection, 'tts_completion_callback')
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"确保TTS stop消息发送失败: {e}")
            # 🚨 紧急修复：即使出错也要尝试发送基本stop消息
            try:
                if connection and connection.websocket:
                    import json
                    stop_message = {
                        "type": "tts",
                        "state": "stop", 
                        "session_id": getattr(connection, 'session_id', ''),
                        "track_id": track_id
                    }
                    await connection.websocket.send(json.dumps(stop_message))
                    self.logger.bind(tag=TAG).info(f"🚨 紧急修复：发送基本TTS stop消息: {track_id}")
            except Exception as emergency_error:
                self.logger.bind(tag=TAG).error(f"紧急修复发送stop消息也失败: {emergency_error}")

    async def update_config(self) -> bool:
        """更新服务器配置并重新初始化组件

        Returns:
            bool: 更新是否成功
        """
        try:
            async with self.config_lock:
                # 重新获取配置
                new_config = get_config_from_api(self.config)
                if new_config is None:
                    self.logger.bind(tag=TAG).error("获取新配置失败")
                    return False
                self.logger.bind(tag=TAG).info(f"获取新配置成功")
                # 检查 VAD 和 ASR 类型是否需要更新
                update_vad = check_vad_update(self.config, new_config)
                update_asr = check_asr_update(self.config, new_config)
                self.logger.bind(tag=TAG).info(
                    f"检查VAD和ASR类型是否需要更新: {update_vad} {update_asr}"
                )
                # 更新配置
                self.config = new_config
                # 重新初始化组件
                modules = initialize_modules(
                    self.logger,
                    new_config,
                    update_vad,
                    update_asr,
                    "LLM" in new_config["selected_module"],
                    False,
                    "Memory" in new_config["selected_module"],  # 重新启用Memory模块
                    "Intent" in new_config["selected_module"],
                )

                # 更新组件实例
                if "vad" in modules:
                    self._vad = modules["vad"]
                if "asr" in modules:
                    self._asr = modules["asr"]
                if "llm" in modules:
                    self._llm = modules["llm"]
                if "intent" in modules:
                    self._intent = modules["intent"]
                if "memory" in modules:
                    self._memory = modules["memory"]
                self.logger.bind(tag=TAG).info(f"更新配置任务执行完毕")
                return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"更新服务器配置失败: {str(e)}")
            return False

import os
import uuid
import json
import queue
import asyncio
import traceback
import websockets
from core.utils.tts import MarkdownCleaner
from config.logger import setup_logging
from core.utils import opus_encoder_utils
from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType
from asyncio import Task


TAG = __name__
logger = setup_logging()

PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

# Message Type:
FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_RESPONSE = 0b1011
FULL_SERVER_RESPONSE = 0b1001
ERROR_INFORMATION = 0b1111

# Message Type Specific Flags
MsgTypeFlagNoSeq = 0b0000  # Non-terminal packet with no sequence
MsgTypeFlagPositiveSeq = 0b1  # Non-terminal packet with sequence > 0
MsgTypeFlagLastNoSeq = 0b10  # last packet with no sequence
MsgTypeFlagNegativeSeq = 0b11  # Payload contains event number (int32)
MsgTypeFlagWithEvent = 0b100
# Message Serialization
NO_SERIALIZATION = 0b0000
JSON = 0b0001
# Message Compression
COMPRESSION_NO = 0b0000
COMPRESSION_GZIP = 0b0001

EVENT_NONE = 0
EVENT_Start_Connection = 1

EVENT_FinishConnection = 2

EVENT_ConnectionStarted = 50  # 成功建连

EVENT_ConnectionFailed = 51  # 建连失败（可能是无法通过权限认证）

EVENT_ConnectionFinished = 52  # 连接结束

# 上行Session事件
EVENT_StartSession = 100
EVENT_CancelSession = 101
EVENT_FinishSession = 102
# 下行Session事件
EVENT_SessionStarted = 150
EVENT_SessionCanceled = 151
EVENT_SessionFinished = 152

EVENT_SessionFailed = 153

# 上行通用事件
EVENT_TaskRequest = 200

# 下行TTS事件
EVENT_TTSSentenceStart = 350

EVENT_TTSSentenceEnd = 351

EVENT_TTSResponse = 352


class Header:
    def __init__(
        self,
        protocol_version=PROTOCOL_VERSION,
        header_size=DEFAULT_HEADER_SIZE,
        message_type: int = 0,
        message_type_specific_flags: int = 0,
        serial_method: int = NO_SERIALIZATION,
        compression_type: int = COMPRESSION_NO,
        reserved_data=0,
    ):
        self.header_size = header_size
        self.protocol_version = protocol_version
        self.message_type = message_type
        self.message_type_specific_flags = message_type_specific_flags
        self.serial_method = serial_method
        self.compression_type = compression_type
        self.reserved_data = reserved_data

    def as_bytes(self) -> bytes:
        return bytes(
            [
                (self.protocol_version << 4) | self.header_size,
                (self.message_type << 4) | self.message_type_specific_flags,
                (self.serial_method << 4) | self.compression_type,
                self.reserved_data,
            ]
        )


class Optional:
    def __init__(
        self, event: int = EVENT_NONE, sessionId: str = None, sequence: int = None
    ):
        self.event = event
        self.sessionId = sessionId
        self.errorCode: int = 0
        self.connectionId: str | None = None
        self.response_meta_json: str | None = None
        self.sequence = sequence

    # 转成 byte 序列
    def as_bytes(self) -> bytes:
        option_bytes = bytearray()
        if self.event != EVENT_NONE:
            option_bytes.extend(self.event.to_bytes(4, "big", signed=True))
        if self.sessionId is not None:
            session_id_bytes = str.encode(self.sessionId)
            size = len(session_id_bytes).to_bytes(4, "big", signed=True)
            option_bytes.extend(size)
            option_bytes.extend(session_id_bytes)
        if self.sequence is not None:
            option_bytes.extend(self.sequence.to_bytes(4, "big", signed=True))
        return option_bytes


class Response:
    def __init__(self, header: Header, optional: Optional):
        self.optional = optional
        self.header = header
        self.payload: bytes | None = None

    def __str__(self):
        return super().__str__()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.ws = None
        self.interface_type = InterfaceType.DUAL_STREAM
        self._monitor_task = None  # 监听任务引用
        # 🔧 修复第一句话音频数据为空的问题
        self.waiting_for_first_audio = False
        self.first_sentence_text = ""
        
        # 🛠️ 会话管理：记录当前会话ID用于复用判断
        self.current_session_id = None
        
        self.appId = config.get("appid")
        self.access_token = config.get("access_token")
        self.cluster = config.get("cluster")
        self.resource_id = config.get("resource_id")
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("speaker")
        self.ws_url = config.get("ws_url")
        self.authorization = config.get("authorization")
        self.header = {"Authorization": f"{self.authorization}{self.access_token}"}
        self.enable_two_way = True
        self.tts_text = ""
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=16000, channels=1, frame_size_ms=60
        )
        model_key_msg = check_model_key("TTS", self.access_token)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

    async def open_audio_channels(self, conn):
        try:
            await super().open_audio_channels(conn)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to open audio channels: {str(e)}")
            self.ws = None
            raise

    async def _ensure_connection(self):
        """建立新的WebSocket连接"""
        try:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            # 🔧 强制重新建立连接，排除连接复用问题
            if self.ws:
                logger.bind(tag=TAG).info(f"检测到已有连接，先关闭...")
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
                logger.bind(tag=TAG).info(f"已关闭旧连接，准备建立新连接")
            logger.bind(tag=TAG).info("开始建立新连接...")
            ws_header = {
                "X-Api-App-Key": self.appId,
                "X-Api-Access-Key": self.access_token,
                "X-Api-Resource-Id": self.resource_id,
                "X-Api-Connect-Id": uuid.uuid4(),
            }
            self.ws = await websockets.connect(
                self.ws_url, additional_headers=ws_header, max_size=1000000000, ssl=ssl_context
            )
            logger.bind(tag=TAG).info("WebSocket连接建立成功")
            return self.ws
        except Exception as e:
            logger.bind(tag=TAG).error(f"建立连接失败: {str(e)}")
            self.ws = None
            raise

    def tts_text_priority_thread(self):
        """火山引擎双流式TTS的文本处理线程"""
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                logger.bind(tag=TAG).debug(
                    f"收到TTS任务｜{message.sentence_type.name} ｜ {message.content_type.name} | 会话ID: {self.conn.sentence_id}"
                )

                # 🚫 关键修复：先检查abort状态，避免被FIRST消息重置
                if self.conn.client_abort:
                    try:
                        logger.bind(tag=TAG).info("收到打断信息，终止TTS文本处理线程")
                        asyncio.run_coroutine_threadsafe(
                            self.cancel_session(self.conn.sentence_id),
                            loop=self.conn.loop,
                        )
                        continue
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"取消TTS会话失败: {str(e)}")
                        continue

                # 🔧 只有在非abort状态下才重置abort标志（防止打断被意外重置）
                if message.sentence_type == SentenceType.FIRST:
                    # 不自动重置client_abort，由textHandle.py在适当时机重置
                    pass

                if message.sentence_type == SentenceType.FIRST:
                    # 初始化参数
                    try:
                        if not getattr(self.conn, "sentence_id", None): 
                            self.conn.sentence_id = uuid.uuid4().hex
                            logger.bind(tag=TAG).info(f"自动生成新的 会话ID: {self.conn.sentence_id}")

                        logger.bind(tag=TAG).info("开始启动TTS会话...")
                        future = asyncio.run_coroutine_threadsafe(
                            self.start_session(self.conn.sentence_id),
                            loop=self.conn.loop,
                        )
                        try:
                            future.result(timeout=5)  # 🔧 缩短为5秒超时，加快响应速度
                            self.before_stop_play_files.clear()
                            logger.bind(tag=TAG).info("TTS会话启动成功")
                        except asyncio.TimeoutError:
                            logger.bind(tag=TAG).error("TTS会话启动超时(5秒)，跳过此次处理")
                            continue
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"启动TTS会话失败: {str(e)}")
                        continue

                elif ContentType.TEXT == message.content_type:
                    if message.content_detail:
                        # 🔧 增强错误处理：检查文本内容
                        if not message.content_detail.strip():
                            logger.bind(tag=TAG).warning(f"⚠️ 跳过空白文本段: '{message.content_detail}'")
                            continue
                            
                        # 🔧 重试机制：最多尝试2次
                        max_retries = 2
                        for attempt in range(max_retries):
                            try:
                                logger.bind(tag=TAG).debug(
                                    f"发送TTS文本 (尝试{attempt+1}/{max_retries}): '{message.content_detail}'"
                                )
                                future = asyncio.run_coroutine_threadsafe(
                                    self.text_to_speak(message.content_detail, None),
                                    loop=self.conn.loop,
                                )
                                future.result(timeout=8)  # 🔧 增加超时时间到8秒
                                logger.bind(tag=TAG).debug(f"TTS文本发送成功: '{message.content_detail}'")
                                break  # 成功后跳出重试循环
                            except asyncio.TimeoutError:
                                logger.bind(tag=TAG).error(f"❌ TTS文本发送超时 (尝试{attempt+1}/{max_retries}): '{message.content_detail}'")
                                if attempt == max_retries - 1:
                                    logger.bind(tag=TAG).error(f"❌ TTS文本发送最终失败，跳过此文本段: '{message.content_detail}'")
                            except Exception as e:
                                logger.bind(tag=TAG).error(f"❌ TTS文本发送异常 (尝试{attempt+1}/{max_retries}): {str(e)}, 文本: '{message.content_detail}'")
                                if attempt == max_retries - 1:
                                    logger.bind(tag=TAG).error(f"❌ TTS文本发送最终失败，跳过此文本段: '{message.content_detail}'")
                                    break
                                else:
                                    # 🔧 重试前短暂等待
                                    import time
                                    time.sleep(0.5)

                elif ContentType.FILE == message.content_type:
                    logger.bind(tag=TAG).info(
                        f"添加音频文件到待播放列表: {message.content_file}"
                    )
                    if message.content_file and os.path.exists(message.content_file):
                        # 先处理文件音频数据
                        file_audio = self._process_audio_file(message.content_file)
                        self.before_stop_play_files.append(
                            (file_audio, message.content_detail)
                        )

                if message.sentence_type == SentenceType.LAST:
                    try:
                        # 🔧 修复时序问题：延迟会话结束，确保音频数据完全接收
                        logger.bind(tag=TAG).info("准备结束TTS会话，等待音频数据完成...")
                        
                        # 延迟一小段时间，让音频数据处理完成（使用time.sleep而不是await）
                        import time
                        time.sleep(0.5)
                        
                        logger.bind(tag=TAG).info("开始结束TTS会话...")
                        future = asyncio.run_coroutine_threadsafe(
                            self.finish_session(self.conn.sentence_id),
                            loop=self.conn.loop,
                        )
                        future.result()
                        logger.bind(tag=TAG).info("TTS会话结束成功")
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"结束TTS会话失败: {str(e)}")
                        continue

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"处理TTS文本失败: {str(e)}, 类型: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )
                continue

    async def text_to_speak(self, text, _):
        """发送文本到TTS服务"""
        try:
            # 建立新连接
            if self.ws is None:
                logger.bind(tag=TAG).error(f"❌ WebSocket连接不存在，无法发送文本: '{text}'")
                raise Exception("WebSocket连接不存在")

            #  过滤Markdown
            filtered_text = MarkdownCleaner.clean_markdown(text)
            logger.bind(tag=TAG).debug(f"Markdown过滤后文本: '{filtered_text}'")
            
            # 🔧 检查过滤后的文本
            if not filtered_text or not filtered_text.strip():
                logger.bind(tag=TAG).warning(f"⚠️ 过滤后文本为空，跳过发送: 原文本='{text}'")
                return

            # 发送文本
            logger.bind(tag=TAG).debug(f"发送到TTS服务: '{filtered_text}'")
            await self.send_text(self.voice, filtered_text, self.conn.sentence_id)
            logger.bind(tag=TAG).debug(f"文本已发送到TTS服务: '{filtered_text}'")
            return
        except Exception as e:
            logger.bind(tag=TAG).error(f"❌ text_to_speak发送失败: {str(e)}, 文本: '{text}'")
            if self.ws:
                try:
                    await self.ws.close()
                    logger.bind(tag=TAG).info("🔧 已关闭异常的WebSocket连接")
                except:
                    pass
            raise  # 重新抛出异常，让上层重试机制处理

    async def start_session(self, session_id):
        logger.bind(tag=TAG).info(f"开始会话～～{session_id}")
        try:
            # 🛠️ 关键修复：检查是否已有相同会话ID的活跃会话
            if hasattr(self, 'current_session_id') and self.current_session_id == session_id:
                # 相同会话ID，检查连接是否正常
                if (self.ws is not None and 
                    self._monitor_task is not None and 
                    isinstance(self._monitor_task, Task) and 
                    not self._monitor_task.done()):
                    logger.bind(tag=TAG).info(f"🔄 复用现有TTS会话: {session_id}")
                    return  # 复用现有会话，不需要重新创建
            
            # 不同会话ID或连接异常，需要重新创建
            if (
                self._monitor_task is not None
                and isinstance(self._monitor_task, Task)
                and not self._monitor_task.done()
            ):
                logger.bind(tag=TAG).info("检测到未完成的上个会话，关闭监听任务和连接...")
                await self.close()

            # 建立新连接
            await self._ensure_connection()

            # 启动监听任务
            self._monitor_task = asyncio.create_task(self._start_monitor_tts_response())
            logger.bind(tag=TAG).info(f"🔍 音频监听任务已启动: {id(self._monitor_task)}")

            header = Header(
                message_type=FULL_CLIENT_REQUEST,
                message_type_specific_flags=MsgTypeFlagWithEvent,
                serial_method=JSON,
            ).as_bytes()
            optional = Optional(
                event=EVENT_StartSession, sessionId=session_id
            ).as_bytes()
            payload = self.get_payload_bytes(
                event=EVENT_StartSession, speaker=self.voice
            )
            await self.send_event(self.ws, header, optional, payload)
            logger.bind(tag=TAG).info("会话启动请求已发送")
            logger.bind(tag=TAG).info("TTS会话启动成功")
            
            # 🛠️ 记录当前会话ID，用于会话复用判断
            self.current_session_id = session_id
        except Exception as e:
            logger.bind(tag=TAG).error(f"启动会话失败: {str(e)}")
            # 确保清理资源
            await self.close()
            raise

    async def finish_session(self, session_id):
        logger.bind(tag=TAG).info(f"关闭会话～～{session_id}")
        try:
            if self.ws:
                header = Header(
                    message_type=FULL_CLIENT_REQUEST,
                    message_type_specific_flags=MsgTypeFlagWithEvent,
                    serial_method=JSON,
                ).as_bytes()
                optional = Optional(
                    event=EVENT_FinishSession, sessionId=session_id
                ).as_bytes()
                payload = str.encode("{}")
                await self.send_event(self.ws, header, optional, payload)
                logger.bind(tag=TAG).info("会话结束请求已发送")

                # 等待监听任务完成
                if self._monitor_task:
                    try:
                        await self._monitor_task
                    except Exception as e:
                        logger.bind(tag=TAG).error(
                            f"等待监听任务完成时发生错误: {str(e)}"
                        )
                    finally:
                        self._monitor_task = None

        except Exception as e:
            logger.bind(tag=TAG).error(f"关闭会话失败: {str(e)}")
            # 确保清理资源
            await self.close()
            raise

    async def cancel_session(self,session_id):
        logger.bind(tag=TAG).info(f"取消会话，释放服务端资源～～{session_id}")
        try:
            if self.ws:
                header = Header(
                    message_type=FULL_CLIENT_REQUEST,
                    message_type_specific_flags=MsgTypeFlagWithEvent,
                    serial_method=JSON,
                ).as_bytes()
                optional = Optional(
                    event=EVENT_CancelSession, sessionId=session_id
                ).as_bytes()
                payload = str.encode("{}")
                await self.send_event(self.ws, header, optional, payload)
                logger.bind(tag=TAG).info("会话取消请求已发送")
        except Exception as e:
            logger.bind(tag=TAG).error(f"取消会话失败: {str(e)}")
            # 确保清理资源
            await self.close()
            raise

    async def close(self):
        """资源清理方法"""
        # 取消监听任务
        if self._monitor_task:
            try:
                self._monitor_task.cancel()
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.bind(tag=TAG).warning(f"关闭时取消监听任务错误: {e}")
            self._monitor_task = None

        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            self.ws = None
            
        # 🛠️ 清理会话ID，确保下次可以创建新会话
        if hasattr(self, 'current_session_id'):
            self.current_session_id = None

    async def _start_monitor_tts_response(self):
        """监听TTS响应"""
        logger.bind(tag=TAG).info("🎧 开始监听TTS音频响应...")
        opus_datas_cache = []
        is_first_sentence = True
        first_sentence_segment_count = 0  # 添加计数器
        try:
            session_finished = False  # 标记会话是否正常结束
            while not self.conn.stop_event.is_set():
                # 🚫 关键修复：在循环开始检查abort状态
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info("🚫 监听循环检测到abort，停止TTS音频生成")
                    break
                    
                logger.bind(tag=TAG).debug("🔍 等待WebSocket消息...")
                try:
                    # 确保 `recv()` 运行在同一个 event loop
                    msg = await self.ws.recv()
                    logger.bind(tag=TAG).debug(f"收到WebSocket消息，长度: {len(msg) if msg else 0}")
                    res = self.parser_response(msg)
                    logger.bind(tag=TAG).debug(f"解析消息事件: {res.optional.event}")
                    # self.print_response(res, "send_text res:")

                    # 🔧 简化事件处理日志
                    if res.optional.event == 350:  # EVENT_TTSSentenceStart
                        logger.bind(tag=TAG).debug(f"句子开始: {res.optional.event}")
                    elif res.optional.event == 352:  # EVENT_TTSResponse
                        logger.bind(tag=TAG).debug(f"音频响应: {res.optional.event}")
                    elif res.optional.event == 351:  # EVENT_TTSSentenceEnd
                        logger.bind(tag=TAG).debug(f"句子结束: {res.optional.event}")
                    elif res.optional.event == 150:  # EVENT_SessionStarted
                        logger.bind(tag=TAG).debug(f"会话已启动: {res.optional.event}")
                    elif res.optional.event == 152:  # EVENT_SessionFinished
                        logger.bind(tag=TAG).info(f"🎯 匹配到EVENT_SessionFinished(152)")
                    else:
                        logger.bind(tag=TAG).info(f"🤔 未知事件: {res.optional.event}")

                    if res.optional.event == EVENT_SessionCanceled:
                        logger.bind(tag=TAG).debug(f"释放服务端资源成功～～")
                        session_finished = True
                        break
                    elif res.optional.event == EVENT_TTSSentenceStart:
                        json_data = json.loads(res.payload.decode("utf-8"))
                        self.tts_text = json_data.get("text", "")
                        logger.bind(tag=TAG).info(f"🎵 句子语音生成开始: {self.tts_text}")
                        # 🔧 修复：不要立即放入空音频数据，标记等待第一个音频数据
                        self.waiting_for_first_audio = True
                        self.first_sentence_text = self.tts_text
                        logger.bind(tag=TAG).info(f"🔍 等待第一句话音频数据: text='{self.tts_text}'")
                        opus_datas_cache = []
                        first_sentence_segment_count = 0  # 重置计数器
                    elif (
                        res.optional.event == EVENT_TTSResponse
                        and res.header.message_type == AUDIO_ONLY_RESPONSE
                    ):
                        # 🚫 在处理音频前检查abort状态
                        if self.conn.client_abort:
                            logger.bind(tag=TAG).info("🚫 音频处理中检测到abort，跳过音频数据")
                            continue
                            
                        logger.bind(tag=TAG).debug(f"收到音频数据，处理中...")
                        opus_datas = self.wav_to_opus_data_audio_raw(res.payload)
                        logger.bind(tag=TAG).debug(
                            f"处理音频数据完成: {len(opus_datas)}帧"
                        )
                        
                        # 🔧 修复：如果这是等待中的第一个音频数据，立即发送FIRST消息
                        if hasattr(self, 'waiting_for_first_audio') and self.waiting_for_first_audio:
                            logger.bind(tag=TAG).info(f"🎵 收到第一句话的首个音频数据，立即发送FIRST消息")
                            self.tts_audio_queue.put(
                                (SentenceType.FIRST, opus_datas, self.first_sentence_text)
                            )
                            self.waiting_for_first_audio = False
                            first_sentence_segment_count = 1  # 已经处理了第一段
                        elif is_first_sentence:
                            first_sentence_segment_count += 1
                            logger.bind(tag=TAG).info(f"🔍 第一句话处理: 片段{first_sentence_segment_count}, 音频帧数{len(opus_datas)}")
                            if first_sentence_segment_count <= 6:
                                logger.bind(tag=TAG).info(f"📤 直接入队: 片段{first_sentence_segment_count}, {len(opus_datas)}帧")
                                self.tts_audio_queue.put(
                                    (SentenceType.MIDDLE, opus_datas, None)
                                )
                            else:
                                logger.bind(tag=TAG).info(f"📦 缓存音频: 片段{first_sentence_segment_count}, {len(opus_datas)}帧")
                                opus_datas_cache.extend(opus_datas)
                        else:
                            # 后续句子缓存
                            logger.bind(tag=TAG).info(f"📦 后续句子缓存: {len(opus_datas)}帧")
                            opus_datas_cache.extend(opus_datas)
                    elif res.optional.event == EVENT_TTSSentenceEnd:
                        logger.bind(tag=TAG).info(f"句子语音生成成功：{self.tts_text}")
                        
                        # 🛠️ 关键修复：句子结束时必须发送所有缓存的音频数据
                        if len(opus_datas_cache) > 0:
                            logger.bind(tag=TAG).info(f"📤 发送缓存音频数据：{len(opus_datas_cache)}帧")
                            self.tts_audio_queue.put(
                                (SentenceType.MIDDLE, opus_datas_cache, None)
                            )
                            logger.bind(tag=TAG).info(f"✅ 缓存音频数据已放入队列")
                            opus_datas_cache = []  # 清空缓存
                        else:
                            logger.bind(tag=TAG).debug(f"📭 句子结束，无缓存音频需要发送")
                        
                        # 第一句话结束后，将标志设置为False
                        is_first_sentence = False
                    elif res.optional.event == EVENT_SessionFinished:
                        logger.bind(tag=TAG).debug(f"会话结束～～")
                        self._process_before_stop_play_files()
                        session_finished = True
                        break
                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).warning("WebSocket连接已关闭")
                    break
                except Exception as e:
                    logger.bind(tag=TAG).error(
                        f"❌ WebSocket监听异常: {e}, WebSocket状态: {self.ws.closed if self.ws else 'None'}"
                    )
                    traceback.print_exc()
                    break
            # 仅在连接异常时才关闭
            if not session_finished and self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
        # 监听任务退出时清理引用
        finally:
            self._monitor_task = None

    async def send_event(
        self,
        ws: websockets.WebSocketClientProtocol,
        header: bytes,
        optional: bytes | None = None,
        payload: bytes = None,
    ):
        try:
            full_client_request = bytearray(header)
            if optional is not None:
                full_client_request.extend(optional)
            if payload is not None:
                payload_size = len(payload).to_bytes(4, "big", signed=True)
                full_client_request.extend(payload_size)
                full_client_request.extend(payload)
            await ws.send(full_client_request)
        except websockets.ConnectionClosed:
            logger.bind(tag=TAG).error(f"ConnectionClosed")
            raise

    async def send_text(self, speaker: str, text: str, session_id):
        header = Header(
            message_type=FULL_CLIENT_REQUEST,
            message_type_specific_flags=MsgTypeFlagWithEvent,
            serial_method=JSON,
        ).as_bytes()
        optional = Optional(event=EVENT_TaskRequest, sessionId=session_id).as_bytes()
        payload = self.get_payload_bytes(
            event=EVENT_TaskRequest, text=text, speaker=speaker
        )
        return await self.send_event(self.ws, header, optional, payload)

    # 读取 res 数组某段 字符串内容
    def read_res_content(self, res: bytes, offset: int):
        content_size = int.from_bytes(res[offset : offset + 4], "big", signed=True)
        offset += 4
        content = str(res[offset : offset + content_size])
        offset += content_size
        return content, offset

    # 读取 payload
    def read_res_payload(self, res: bytes, offset: int):
        payload_size = int.from_bytes(res[offset : offset + 4], "big", signed=True)
        offset += 4
        payload = res[offset : offset + payload_size]
        offset += payload_size
        return payload, offset

    def parser_response(self, res) -> Response:
        if isinstance(res, str):
            raise RuntimeError(res)
        response = Response(Header(), Optional())
        # 解析结果
        # header
        header = response.header
        num = 0b00001111
        header.protocol_version = res[0] >> 4 & num
        header.header_size = res[0] & 0x0F
        header.message_type = (res[1] >> 4) & num
        header.message_type_specific_flags = res[1] & 0x0F
        header.serialization_method = res[2] >> num
        header.message_compression = res[2] & 0x0F
        header.reserved = res[3]
        #
        offset = 4
        optional = response.optional
        if header.message_type == FULL_SERVER_RESPONSE or AUDIO_ONLY_RESPONSE:
            # read event
            if header.message_type_specific_flags == MsgTypeFlagWithEvent:
                optional.event = int.from_bytes(res[offset:8], "big", signed=True)
                offset += 4
                if optional.event == EVENT_NONE:
                    return response
                # read connectionId
                elif optional.event == EVENT_ConnectionStarted:
                    optional.connectionId, offset = self.read_res_content(res, offset)
                elif optional.event == EVENT_ConnectionFailed:
                    optional.response_meta_json, offset = self.read_res_content(
                        res, offset
                    )
                elif (
                    optional.event == EVENT_SessionStarted
                    or optional.event == EVENT_SessionFailed
                    or optional.event == EVENT_SessionFinished
                ):
                    optional.sessionId, offset = self.read_res_content(res, offset)
                    optional.response_meta_json, offset = self.read_res_content(
                        res, offset
                    )
                else:
                    optional.sessionId, offset = self.read_res_content(res, offset)
                    response.payload, offset = self.read_res_payload(res, offset)

        elif header.message_type == ERROR_INFORMATION:
            optional.errorCode = int.from_bytes(
                res[offset : offset + 4], "big", signed=True
            )
            offset += 4
            response.payload, offset = self.read_res_payload(res, offset)
        return response

    async def start_connection(self):
        header = Header(
            message_type=FULL_CLIENT_REQUEST,
            message_type_specific_flags=MsgTypeFlagWithEvent,
        ).as_bytes()
        optional = Optional(event=EVENT_Start_Connection).as_bytes()
        payload = str.encode("{}")
        return await self.send_event(self.ws, header, optional, payload)

    def print_response(self, res, tag_msg: str):
        logger.bind(tag=TAG).debug(f"===>{tag_msg} header:{res.header.__dict__}")
        logger.bind(tag=TAG).debug(f"===>{tag_msg} optional:{res.optional.__dict__}")

    def get_payload_bytes(
        self,
        uid="1234",
        event=EVENT_NONE,
        text="",
        speaker="",
        audio_format="pcm",
        audio_sample_rate=16000,
    ):
        return str.encode(
            json.dumps(
                {
                    "user": {"uid": uid},
                    "event": event,
                    "namespace": "BidirectionalTTS",
                    "req_params": {
                        "text": text,
                        "speaker": speaker,
                        "audio_params": {
                            "format": audio_format,
                            "sample_rate": audio_sample_rate,
                        },
                    },
                }
            )
        )

    def wav_to_opus_data_audio_raw(self, raw_data_var, is_end=False):
        opus_datas = self.opus_encoder.encode_pcm_to_opus(raw_data_var, is_end)
        return opus_datas

    def to_tts(self, text: str) -> list:
        """非流式生成音频数据，用于生成音频及测试场景

        Args:
            text: 要转换的文本

        Returns:
            list: 音频数据列表
        """
        try:
            # 创建事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 生成会话ID
            session_id = uuid.uuid4().__str__().replace("-", "")

            # 存储音频数据
            audio_data = []

            async def _generate_audio():
                # 创建新的WebSocket连接
                ws_header = {
                    "X-Api-App-Key": self.appId,
                    "X-Api-Access-Key": self.access_token,
                    "X-Api-Resource-Id": self.resource_id,
                    "X-Api-Connect-Id": uuid.uuid4(),
                }
                ws = await websockets.connect(
                    self.ws_url, additional_headers=ws_header, max_size=1000000000
                )

                try:
                    # 启动会话
                    header = Header(
                        message_type=FULL_CLIENT_REQUEST,
                        message_type_specific_flags=MsgTypeFlagWithEvent,
                        serial_method=JSON,
                    ).as_bytes()
                    optional = Optional(
                        event=EVENT_StartSession, sessionId=session_id
                    ).as_bytes()
                    payload = self.get_payload_bytes(
                        event=EVENT_StartSession, speaker=self.voice
                    )
                    await self.send_event(ws, header, optional, payload)

                    # 发送文本
                    header = Header(
                        message_type=FULL_CLIENT_REQUEST,
                        message_type_specific_flags=MsgTypeFlagWithEvent,
                        serial_method=JSON,
                    ).as_bytes()
                    optional = Optional(
                        event=EVENT_TaskRequest, sessionId=session_id
                    ).as_bytes()
                    payload = self.get_payload_bytes(
                        event=EVENT_TaskRequest, text=text, speaker=self.voice
                    )
                    await self.send_event(ws, header, optional, payload)

                    # 发送结束会话请求
                    header = Header(
                        message_type=FULL_CLIENT_REQUEST,
                        message_type_specific_flags=MsgTypeFlagWithEvent,
                        serial_method=JSON,
                    ).as_bytes()
                    optional = Optional(
                        event=EVENT_FinishSession, sessionId=session_id
                    ).as_bytes()
                    payload = str.encode("{}")
                    await self.send_event(ws, header, optional, payload)

                    # 接收音频数据
                    while True:
                        msg = await ws.recv()
                        res = self.parser_response(msg)

                        if (
                            res.optional.event == EVENT_TTSResponse
                            and res.header.message_type == AUDIO_ONLY_RESPONSE
                        ):
                            opus_datas = self.wav_to_opus_data_audio_raw(res.payload)
                            audio_data.extend(opus_datas)
                        elif res.optional.event == EVENT_SessionFinished:
                            break

                finally:
                    # 清理资源
                    try:
                        await ws.close()
                    except:
                        pass

            # 运行异步任务
            loop.run_until_complete(_generate_audio())
            loop.close()

            return audio_data

        except Exception as e:
            logger.bind(tag=TAG).error(f"生成音频数据失败: {str(e)}")
            return []

import json
import time
import uuid
import hmac
import base64
import hashlib
import asyncio
import requests
import websockets
import opuslib_next
import random
from typing import Optional, Tuple, List
from urllib import parse
from datetime import datetime
from config.logger import setup_logging
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType
from core.utils.audio_buffer_manager import get_or_create_audio_manager

TAG = __name__
logger = setup_logging()


class AccessToken:
    @staticmethod
    def _encode_text(text):
        encoded_text = parse.quote_plus(text)
        return encoded_text.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    @staticmethod
    def _encode_dict(dic):
        keys = dic.keys()
        dic_sorted = [(key, dic[key]) for key in sorted(keys)]
        encoded_text = parse.urlencode(dic_sorted)
        return encoded_text.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    @staticmethod
    def create_token(access_key_id, access_key_secret):
        parameters = {
            "AccessKeyId": access_key_id,
            "Action": "CreateToken",
            "Format": "JSON",
            "RegionId": "cn-shanghai",
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid.uuid1()),
            "SignatureVersion": "1.0",
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "Version": "2019-02-28",
        }
        query_string = AccessToken._encode_dict(parameters)
        string_to_sign = (
            "GET" + "&" + AccessToken._encode_text("/") + "&" + AccessToken._encode_text(query_string)
        )
        secreted_string = hmac.new(
            bytes(access_key_secret + "&", encoding="utf-8"),
            bytes(string_to_sign, encoding="utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(secreted_string)
        signature = AccessToken._encode_text(signature)
        full_url = "http://nls-meta.cn-shanghai.aliyuncs.com/?Signature=%s&%s" % (signature, query_string)
        response = requests.get(full_url)
        if response.ok:
            root_obj = response.json()
            if "Token" in root_obj:
                return root_obj["Token"]["Id"], root_obj["Token"]["ExpireTime"]
        return None, None


class ASRProvider(ASRProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.config = config
        self.text = ""
        self.decoder = opuslib_next.Decoder(16000, 1)
        self.asr_ws = None
        self.forward_task = None
        self.is_processing = False
        self.server_ready = False  # 服务器准备状态

        # 基础配置
        self.access_key_id = config.get("access_key_id")
        self.access_key_secret = config.get("access_key_secret")
        self.appkey = config.get("appkey")
        self.token = config.get("token")
        self.host = config.get("host", "nls-gateway-cn-shanghai.aliyuncs.com")
        # 如果配置的是内网地址（包含-internal.aliyuncs.com），则使用ws协议，默认是wss协议
        if "-internal." in self.host:
            self.ws_url = f"ws://{self.host}/ws/v1"
        else:
            # 默认使用wss协议
            self.ws_url = f"wss://{self.host}/ws/v1"

        self.max_sentence_silence = config.get("max_sentence_silence")
        self.output_dir = config.get("output_dir", "./audio_output")
        self.delete_audio_file = delete_audio_file
        self.expire_time = None

        # Token管理
        if self.access_key_id and self.access_key_secret:
            self._refresh_token()
        elif not self.token:
            raise ValueError("必须提供access_key_id+access_key_secret或者直接提供token")

    def _refresh_token(self):
        """刷新Token"""
        self.token, expire_time_str = AccessToken.create_token(self.access_key_id, self.access_key_secret)
        if not self.token:
            raise ValueError("无法获取有效的访问Token")
        
        try:
            expire_str = str(expire_time_str).strip()
            if expire_str.isdigit():
                expire_time = datetime.fromtimestamp(int(expire_str))
            else:
                expire_time = datetime.strptime(expire_str, "%Y-%m-%dT%H:%M:%SZ")
            self.expire_time = expire_time.timestamp() - 60
        except:
            self.expire_time = None

    def _is_token_expired(self):
        """检查Token是否过期"""
        return self.expire_time and time.time() > self.expire_time

    async def open_audio_channels(self, conn):
        await super().open_audio_channels(conn)

    async def receive_audio(self, conn, audio, audio_have_voice):
        # 🔧 修复：使用音频缓冲区管理器防止内存泄漏
        audio_manager = get_or_create_audio_manager(conn)
        
        # 存储音频数据
        if audio:
            audio_manager.add_audio(audio)
            audio_manager.add_voiceprint_audio(audio)

        # 只在有声音且没有连接时建立连接
        if audio_have_voice and not self.is_processing:
            try:
                await self._start_recognition(conn)
            except Exception as e:
                logger.bind(tag=TAG).error(f"开始识别失败: {str(e)}")
                await self._cleanup(conn)
                return

        if self.asr_ws and self.is_processing and self.server_ready:
            try:
                pcm_frame = self.decoder.decode(audio, 960)
                await self.asr_ws.send(pcm_frame)
            except Exception as e:
                logger.bind(tag=TAG).warning(f"发送音频失败: {str(e)}")
                await self._cleanup(conn)

    async def _start_recognition(self, conn):
        """开始识别会话"""
        if self._is_token_expired():
            self._refresh_token()
        
        # 建立连接
        headers = {"X-NLS-Token": self.token}
        self.asr_ws = await websockets.connect(
            self.ws_url,
            additional_headers=headers,
            max_size=1000000000,
            ping_interval=None,
            ping_timeout=None,
            close_timeout=5,
        )
        
        self.is_processing = True
        self.server_ready = False  # 重置服务器准备状态
        self.forward_task = asyncio.create_task(self._forward_results(conn))
        
        # 发送开始请求
        start_request = {
            "header": {
                "namespace": "SpeechTranscriber",
                "name": "StartTranscription",
                "status": 20000000,
                "message_id": ''.join(random.choices('0123456789abcdef', k=32)),
                "task_id": ''.join(random.choices('0123456789abcdef', k=32)),
                "status_text": "Gateway:SUCCESS:Success.",
                "appkey": self.appkey
            },
            "payload": {
                "format": "pcm",
                "sample_rate": 16000,
                "enable_intermediate_result": True,
                "enable_punctuation_prediction": True,
                "enable_inverse_text_normalization": True,
                "max_sentence_silence": self.max_sentence_silence,
                "enable_voice_detection": False,
            }
        }
        await self.asr_ws.send(json.dumps(start_request, ensure_ascii=False))
        logger.bind(tag=TAG).info("已发送开始请求，等待服务器准备...")

    async def _forward_results(self, conn):
        """转发识别结果"""
        try:
            while self.asr_ws and not conn.stop_event.is_set():
                try:
                    response = await asyncio.wait_for(self.asr_ws.recv(), timeout=1.0)
                    result = json.loads(response)
                    
                    header = result.get("header", {})
                    payload = result.get("payload", {})
                    message_name = header.get("name", "")
                    status = header.get("status", 0)
                    
                    if status != 20000000:
                        if status in [40000004, 40010004]:  # 连接超时或客户端断开
                            logger.bind(tag=TAG).warning(f"连接问题，状态码: {status}")
                            break
                        elif status in [40270002, 40270003]:  # 音频问题
                            logger.bind(tag=TAG).warning(f"音频处理问题，状态码: {status}")
                            continue
                        else:
                            logger.bind(tag=TAG).error(f"识别错误，状态码: {status}, 消息: {header.get('status_text', '')}")
                            continue
                    
                    # 收到TranscriptionStarted表示服务器准备好接收音频数据
                    if message_name == "TranscriptionStarted":
                        self.server_ready = True
                        logger.bind(tag=TAG).info("服务器已准备，开始发送缓存音频...")
                        
                        # 发送缓存音频
                        if conn.asr_audio:
                            for cached_audio in conn.asr_audio[-10:]:
                                try:
                                    pcm_frame = self.decoder.decode(cached_audio, 960)
                                    await self.asr_ws.send(pcm_frame)
                                except Exception as e:
                                    logger.bind(tag=TAG).warning(f"发送缓存音频失败: {e}")
                                    break
                        continue
                    
                    if message_name == "TranscriptionResultChanged":
                        # 中间结果
                        text = payload.get("result", "")
                        if text:
                            self.text = text
                    elif message_name == "SentenceEnd":
                        # 最终结果
                        text = payload.get("result", "")
                        if text:
                            self.text = text
                            conn.reset_vad_states()
                            # 传递缓存的音频数据
                            audio_data = getattr(conn, 'asr_audio_for_voiceprint', [])
                            await self.handle_voice_stop(conn, audio_data)
                            # 清空缓存
                            conn.asr_audio_for_voiceprint = []
                            break
                    elif message_name == "TranscriptionCompleted":
                        # 识别完成
                        self.is_processing = False
                        break
                        
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception as e:
                    logger.bind(tag=TAG).error(f"处理结果失败: {str(e)}")
                    break
                    
        except Exception as e:
            logger.bind(tag=TAG).error(f"结果转发失败: {str(e)}")
        finally:
            await self._cleanup(conn)

    async def _cleanup(self, conn):
        """清理资源"""
        logger.bind(tag=TAG).info(f"开始ASR会话清理 | 当前状态: processing={self.is_processing}, server_ready={self.server_ready}")
        
        # 清理连接的音频缓存
        if conn and hasattr(conn, 'asr_audio_for_voiceprint'):
            conn.asr_audio_for_voiceprint = []
        
        # 判断是否需要发送终止请求
        should_stop = self.is_processing or self.server_ready
        
        # 发送停止识别请求
        if self.asr_ws and should_stop:
            try:
                stop_msg = {
                    "header": {
                        "namespace": "SpeechTranscriber",
                        "name": "StopTranscription",
                        "status": 20000000,
                        "message_id": ''.join(random.choices('0123456789abcdef', k=32)),
                        "status_text": "Client:Stop",
                        "appkey": self.appkey
                    }
                }
                logger.bind(tag=TAG).info("正在发送ASR终止请求")
                await self.asr_ws.send(json.dumps(stop_msg, ensure_ascii=False))
                await asyncio.sleep(0.1)
                logger.bind(tag=TAG).info("ASR终止请求已发送")
            except Exception as e:
                logger.bind(tag=TAG).error(f"ASR终止请求发送失败: {e}")
        
        # 状态重置（在终止请求发送后）
        self.is_processing = False
        self.server_ready = False
        logger.bind(tag=TAG).info("ASR状态已重置")

        # 清理任务
        if self.forward_task and not self.forward_task.done():
            self.forward_task.cancel()
            try:
                await asyncio.wait_for(self.forward_task, timeout=1.0)
            except Exception as e:
                logger.bind(tag=TAG).debug(f"forward_task取消异常: {e}")
            finally:
                self.forward_task = None
        
        # 关闭连接
        if self.asr_ws:
            try:
                logger.bind(tag=TAG).debug("正在关闭WebSocket连接")
                await asyncio.wait_for(self.asr_ws.close(), timeout=2.0)
                logger.bind(tag=TAG).debug("WebSocket连接已关闭")
            except Exception as e:
                logger.bind(tag=TAG).error(f"关闭WebSocket连接失败: {e}")
            finally:
                self.asr_ws = None
        
        logger.bind(tag=TAG).info("ASR会话清理完成")

    async def speech_to_text(self, opus_data, session_id, audio_format):
        """获取识别结果"""
        result = self.text
        self.text = ""
        return result, None

    async def close(self):
        """关闭资源"""
        await self._cleanup()

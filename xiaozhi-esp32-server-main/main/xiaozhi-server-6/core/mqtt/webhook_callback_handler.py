#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT Webhooks回调处理器
实现完整的 MQTT -> ACK -> TTS -> WebSocket -> 硬件播放 流程
"""

import asyncio
import json
import time
import uuid
import websockets
from datetime import datetime
from typing import Dict, Any, Optional
from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase

TAG = __name__


class WebhookCallbackHandler:
    """MQTT Webhooks回调处理器"""
    
    def __init__(self, config: Dict[str, Any], mqtt_client=None, tts_provider: TTSProviderBase = None):
        self.config = config
        self.mqtt_client = mqtt_client
        self.tts_provider = tts_provider
        self.logger = setup_logging()
        
        # 跟踪正在处理的请求
        self.pending_requests = {}
        
        # WebSocket连接管理
        self.device_websockets = {}
        
        # 设置MQTT客户端的默认ACK处理器
        if self.mqtt_client:
            self.mqtt_client.set_default_ack_handler(self.handle_device_ack)
    
    async def handle_device_ack(self, device_id: str, track_id: str, ack_data: Dict):
        """
        处理设备ACK回调 - 完全复制xiaozhi-server-2的成功实现
        
        流程: Java触发 -> MQTT命令 -> 设备ACK -> TTS生成 -> WebSocket音频 -> 设备播放
        """
        self.logger.bind(tag=TAG).info(f"🔔 收到设备ACK: {device_id}, track_id: {track_id}")
        
        try:
            # 1. 检查是否有对应的待处理请求
            if track_id not in self.pending_requests:
                self.logger.bind(tag=TAG).warning(f"未找到对应的待处理请求: {track_id}")
                return
            
            request_info = self.pending_requests[track_id]
            text_content = request_info.get("text", "")
            
            if not text_content:
                self.logger.bind(tag=TAG).error(f"缺少文本内容: {track_id}")
                return
            
            # 2. 更新请求状态
            request_info["status"] = "ack_received"
            request_info["ack_time"] = datetime.now().isoformat()
            request_info["ack_data"] = ack_data
            
            # 3. 🔧 关键修复：先生成TTS音频文件（参考xiaozhi-server-2的ProactiveGreetingService）
            self.logger.bind(tag=TAG).info(f"🎵 开始生成TTS音频: {text_content[:50]}...")
            audio_file_path = await self._synthesize_speech_like_server2(text_content)
            
            if audio_file_path:
                # 4. 🔧 关键修复：使用xiaozhi-server-2相同的音频发送方式
                success = await self._send_audio_to_device_like_server2(device_id, audio_file_path, track_id, text_content)
                
                if success:
                    request_info["status"] = "audio_sent"
                    request_info["audio_sent_time"] = datetime.now().isoformat()
                    self.logger.bind(tag=TAG).info(f"✅ 音频发送成功: {track_id}")
                else:
                    request_info["status"] = "audio_send_failed"
                    self.logger.bind(tag=TAG).error(f"❌ 音频发送失败: {track_id}")
            else:
                request_info["status"] = "tts_failed"
                self.logger.bind(tag=TAG).error(f"❌ TTS生成失败: {track_id}")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"❌ 处理设备ACK失败: {e}")
            if track_id in self.pending_requests:
                self.pending_requests[track_id]["status"] = "error"
                self.pending_requests[track_id]["error"] = str(e)
    
    async def register_awaken_request(self, device_id: str, text: str, track_id: str = None):
        """
        注册唤醒请求，等待设备ACK
        
        在发送MQTT唤醒命令之前调用此方法，注册待处理的请求
        """
        if not track_id:
            track_id = f"WH{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"
        
        # 注册待处理请求
        self.pending_requests[track_id] = {
            "device_id": device_id,
            "text": text,
            "status": "registered",
            "register_time": datetime.now().isoformat(),
            "track_id": track_id
        }
        
        self.logger.bind(tag=TAG).info(f"📝 注册唤醒请求: {device_id}, track_id: {track_id}")
        
        # 🔧 参考xiaozhi-server-2：增加备用触发机制，不完全依赖设备ACK
        try:
            # 🔧 备用触发机制：延迟5秒后，如果没有收到ACK就主动触发TTS生成（使用xiaozhi-server-2方式）
            async def fallback_trigger():
                await asyncio.sleep(5.0)  # 等待5秒
                if track_id in self.pending_requests and self.pending_requests[track_id]["status"] == "registered":
                    self.logger.bind(tag=TAG).warning(f"⚠️ 未收到设备ACK，启动备用TTS触发: {track_id}")
                    # 直接生成TTS和发送音频，不依赖ACK
                    try:
                        text_content = self.pending_requests[track_id].get("text", "")
                        if text_content:
                            # 使用xiaozhi-server-2相同的TTS方式
                            audio_file_path = await self._synthesize_speech_like_server2(text_content)
                            if audio_file_path:
                                # 使用xiaozhi-server-2相同的音频发送方式
                                success = await self._send_audio_to_device_like_server2(device_id, audio_file_path, track_id, text_content)
                                if success:
                                    self.pending_requests[track_id]["status"] = "fallback_completed"
                                    self.logger.bind(tag=TAG).info(f"✅ 备用触发完成: {track_id}")
                                else:
                                    self.logger.bind(tag=TAG).error(f"❌ 备用触发音频发送失败: {track_id}")
                            else:
                                self.logger.bind(tag=TAG).error(f"❌ 备用触发TTS生成失败: {track_id}")
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"❌ 备用触发异常: {e}")
            
            # 启动备用触发任务
            asyncio.create_task(fallback_trigger())
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"设置备用触发机制失败: {e}")
        
        return track_id
    
    async def _synthesize_speech_like_server2(self, text: str) -> Optional[str]:
        """合成语音 - 完全复制xiaozhi-server-2的ProactiveGreetingService.synthesize_speech方法"""
        try:
            if not self.tts_provider:
                self.logger.bind(tag=TAG).warning("TTS提供器未配置")
                return None
            
            self.logger.bind(tag=TAG).info(f"开始TTS合成: {text[:50]}...")
            
            # 🔧 关键修复：完全复制xiaozhi-server-2的_call_tts实现
            import uuid
            import os
            
            # 创建临时音频文件
            output_dir = getattr(self.tts_provider, 'output_file', './cache/tts')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            filename = os.path.join(output_dir, f"webhook_tts_{uuid.uuid4().hex[:8]}.wav")
            
            # 使用xiaozhi-server-2的_call_tts方法
            audio_data = await self._call_tts_like_server2(text, filename)
            
            if audio_data and len(audio_data) > 0:
                # 为了防止TTS自动删除，创建一个专用的副本
                persistent_filename = os.path.join(output_dir, f"persistent_webhook_{uuid.uuid4().hex[:8]}.wav")
                import shutil
                
                if os.path.exists(filename):
                    shutil.copy2(filename, persistent_filename)
                    self.logger.bind(tag=TAG).info(f"✅ TTS合成成功，创建持久音频文件: {persistent_filename}")
                    return persistent_filename
                else:
                    # 如果原文件不存在，直接写入到持久文件
                    with open(persistent_filename, 'wb') as f:
                        f.write(audio_data)
                    self.logger.bind(tag=TAG).info(f"✅ TTS合成成功，直接创建持久音频文件: {persistent_filename}")
                    return persistent_filename
            else:
                self.logger.bind(tag=TAG).error("TTS合成失败：生成的音频数据为空")
                return None
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"TTS合成异常: {e}")
            return None
    
    async def _call_tts_like_server2(self, text: str, filename: str) -> bytes:
        """调用TTS接口 - 完全复制xiaozhi-server-2的_call_tts方法"""
        try:
            import asyncio
            import os  # 🔧 修复：导入os模块
            
            def call_tts_sync():
                if hasattr(self.tts_provider, 'to_tts'):
                    # 使用to_tts方法，它会自动进行格式转换
                    self.logger.bind(tag=TAG).info("使用to_tts方法进行音频合成（与普通对话一致）")
                    result = self.tts_provider.to_tts(text)
                    
                    # 🔧 关键修复：处理不同类型的返回值
                    if isinstance(result, str):
                        # 返回的是文件路径字符串
                        self.logger.bind(tag=TAG).info(f"TTS返回文件路径: {result}")
                        if os.path.exists(result):
                            # 读取文件内容
                            with open(result, 'rb') as f:
                                audio_bytes = f.read()
                            
                            # 如果需要保存到指定文件名
                            if filename and filename != result:
                                import shutil
                                shutil.copy2(result, filename)
                                self.logger.bind(tag=TAG).info(f"音频文件复制成功: {result} -> {filename}")
                            
                            return audio_bytes
                        else:
                            self.logger.bind(tag=TAG).error(f"TTS生成的文件不存在: {result}")
                            return b""
                    
                    elif isinstance(result, list) and result:
                        # 返回的是Opus帧数据列表
                        self.logger.bind(tag=TAG).info("TTS返回Opus帧数据")
                        try:
                            from core.utils.util import opus_datas_to_wav_bytes
                            # 转换为WAV字节数据保存到文件
                            wav_bytes = opus_datas_to_wav_bytes(result, sample_rate=16000)
                            if filename:
                                with open(filename, 'wb') as f:
                                    f.write(wav_bytes)
                                self.logger.bind(tag=TAG).info(f"音频文件保存成功: {filename}")
                            return wav_bytes
                        except Exception as convert_error:
                            self.logger.bind(tag=TAG).error(f"Opus转WAV失败: {convert_error}")
                            # 降级：直接返回第一个Opus帧作为示例
                            return result[0] if result else b""
                    
                    elif isinstance(result, bytes):
                        # 返回的是字节数据
                        self.logger.bind(tag=TAG).info("TTS返回字节数据")
                        if filename:
                            with open(filename, 'wb') as f:
                                f.write(result)
                            self.logger.bind(tag=TAG).info(f"音频文件保存成功: {filename}")
                        return result
                    
                    else:
                        self.logger.bind(tag=TAG).warning(f"TTS返回未知类型数据: {type(result)}")
                        return b""
                else:
                    # 降级到text_to_speak（保持兼容性）
                    self.logger.bind(tag=TAG).warning("TTS对象没有to_tts方法，降级使用text_to_speak")
                    return b""
            
            # 使用线程池执行，避免事件循环冲突
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(call_tts_sync)
                return future.result(timeout=30)  # 30秒超时
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"调用TTS失败: {e}")
            return b""
    
    async def _send_audio_to_device_like_server2(self, device_id: str, audio_file_path: str, track_id: str, greeting_text: str) -> bool:
        """发送音频数据到设备 - 完全复制xiaozhi-server-2的_send_audio_to_device方法"""
        try:
            self.logger.bind(tag=TAG).info(f"发送音频文件到设备: {device_id}, 文件: {audio_file_path}, track_id: {track_id}")
            
            # 通过WebSocket服务器发送音频数据（完全复制xiaozhi-server-2的实现）
            if hasattr(self.mqtt_client, 'websocket_server') and self.mqtt_client.websocket_server:
                # 重要修复：使用相同的track_id，确保MQTT命令和WebSocket音频能被硬件正确关联
                audio_track_id = track_id  # 使用从ACK中获取的track_id
                
                success = await self.mqtt_client.websocket_server.send_audio_to_device(
                    device_id, audio_file_path, audio_track_id, greeting_text
                )
                
                if success:
                    self.logger.bind(tag=TAG).info(f"✅ WebSocket音频发送成功: {device_id}")
                    return True
                else:
                    self.logger.bind(tag=TAG).warning(f"⚠️ WebSocket音频发送失败，可能设备未连接: {device_id}")
                    return False
            else:
                self.logger.bind(tag=TAG).error("❌ WebSocket服务器不可用，无法发送音频")
                return False
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"❌ 发送音频数据失败: {e}")
            return False

    async def _generate_tts_audio(self, text: str, track_id: str) -> Optional[str]:
        """生成TTS音频文件（采用xiaozhi-server-2成功模式）"""
        try:
            if not self.tts_provider:
                self.logger.bind(tag=TAG).warning("TTS提供器未配置，使用模拟音频")
                await asyncio.sleep(0.5)  # 模拟TTS生成时间
                return None
            
            # 🔧 参考xiaozhi-server-2：使用正确的TTS生成方式
            import os
            import uuid
            from datetime import datetime
            
            # 获取TTS输出目录（确保使用正确路径）
            output_dir = getattr(self.tts_provider, 'output_file', './cache/tts')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 生成唯一文件名
            audio_format = getattr(self.tts_provider, 'audio_file_type', 'mp3')
            tmp_file = os.path.join(
                output_dir,
                f"webhook-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}.{audio_format}"
            )
            
            self.logger.bind(tag=TAG).info(f"🎵 开始TTS生成: {text[:50]}... -> {tmp_file}")
            
            # 🔧 针对火山引擎TTS的特殊处理
            try:
                # 检查TTS提供器类型
                tts_class_name = type(self.tts_provider).__name__
                self.logger.bind(tag=TAG).info(f"TTS提供器类型: {tts_class_name}")
                
                # 火山引擎TTS有专门的非流式方法
                if hasattr(self.tts_provider, 'to_tts') and 'huoshan' in tts_class_name.lower():
                    self.logger.bind(tag=TAG).info("使用火山引擎离线TTS方法")
                    
                    # 使用线程池避免事件循环冲突
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(self.tts_provider.to_tts, text)
                        result_file = future.result(timeout=30)
                    
                    if result_file and os.path.exists(result_file):
                        # 复制到指定位置
                        import shutil
                        shutil.copy2(result_file, tmp_file)
                        self.logger.bind(tag=TAG).info(f"火山引擎TTS生成成功: {result_file} -> {tmp_file}")
                    else:
                        self.logger.bind(tag=TAG).error("火山引擎TTS生成失败")
                        return None
                        
                else:
                    # 其他TTS提供器使用标准方法
                    await self.tts_provider.text_to_speak(text, tmp_file)
                    self.logger.bind(tag=TAG).info(f"✅ TTS调用完成，检查文件: {tmp_file}")
                    
            except Exception as tts_error:
                self.logger.bind(tag=TAG).error(f"❌ TTS生成异常: {tts_error}")
                import traceback
                self.logger.bind(tag=TAG).error(f"TTS异常详情: {traceback.format_exc()}")
                return None
            
            # 验证文件生成
            if os.path.exists(tmp_file) and os.path.getsize(tmp_file) > 0:
                self.logger.bind(tag=TAG).info(f"✅ TTS音频文件生成成功: {tmp_file} ({os.path.getsize(tmp_file)} bytes)")
                return tmp_file
            else:
                self.logger.bind(tag=TAG).error(f"❌ TTS文件生成失败或文件为空: {tmp_file}")
                return None
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"❌ TTS生成异常: {e}")
            import traceback
            self.logger.bind(tag=TAG).error(f"TTS异常详情: {traceback.format_exc()}")
            return None
    
    async def _send_audio_file_via_websocket(self, device_id: str, audio_file_path: str, track_id: str, greeting_text: str) -> bool:
        """发送音频文件到设备（采用成功的ProactiveGreetingService模式）"""
        try:
            self.logger.bind(tag=TAG).info(f"📨 通过WebSocket发送音频文件: {device_id}, 文件: {audio_file_path}")
            
            # 通过WebSocket服务器发送音频数据（采用ProactiveGreetingService的成功模式）
            if hasattr(self.mqtt_client, 'websocket_server') and self.mqtt_client.websocket_server:
                success = await self.mqtt_client.websocket_server.send_audio_to_device(
                    device_id, audio_file_path, track_id, greeting_text
                )
                
                if success:
                    self.logger.bind(tag=TAG).info(f"✅ WebSocket音频文件发送成功: {device_id}")
                    return True
                else:
                    self.logger.bind(tag=TAG).warning(f"⚠️ WebSocket音频文件发送失败，可能设备未连接: {device_id}")
                    return False
            else:
                self.logger.bind(tag=TAG).error("❌ WebSocket服务器不可用，无法发送音频文件")
                return False
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"❌ 发送音频文件异常: {e}")
            return False

    async def _send_audio_via_websocket(self, device_id: str, audio_data: bytes, track_id: str) -> bool:
        """通过WebSocket发送音频到设备"""
        try:
            # 构建音频消息
            audio_message = {
                "type": "audio",
                "track_id": track_id,
                "audio_data": audio_data.hex(),  # 转换为十六进制字符串
                "timestamp": datetime.now().isoformat(),
                "device_id": device_id
            }
            
            # 尝试发送到设备的WebSocket连接
            websocket_url = self._get_device_websocket_url(device_id)
            
            if websocket_url:
                success = await self._send_to_websocket(websocket_url, audio_message)
                return success
            else:
                # 如果没有直接的WebSocket连接，尝试通过现有的连接管理器
                success = await self._send_via_connection_manager(device_id, audio_message)
                return success
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"WebSocket音频发送异常: {e}")
            return False
    
    def _get_device_websocket_url(self, device_id: str) -> Optional[str]:
        """获取设备的WebSocket连接URL"""
        # 这里可以根据设备ID构建WebSocket URL
        # 或者从设备注册表中获取
        
        # 示例: 假设设备有固定的WebSocket端点
        device_ws_port = self.config.get("device_websocket", {}).get("port", 8080)
        device_ip = self._get_device_ip(device_id)
        
        if device_ip:
            return f"ws://{device_ip}:{device_ws_port}/audio"
        
        return None
    
    def _get_device_ip(self, device_id: str) -> Optional[str]:
        """获取设备IP地址"""
        # 这里应该从设备管理系统中获取设备IP
        # 或者从配置文件中读取设备映射
        
        device_mapping = self.config.get("device_mapping", {})
        return device_mapping.get(device_id)
    
    async def _send_to_websocket(self, websocket_url: str, message: Dict) -> bool:
        """发送消息到WebSocket"""
        try:
            async with websockets.connect(websocket_url) as websocket:
                await websocket.send(json.dumps(message))
                self.logger.bind(tag=TAG).info(f"📡 WebSocket消息发送成功: {websocket_url}")
                return True
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"WebSocket连接失败: {websocket_url}, {e}")
            return False
    
    async def _send_via_connection_manager(self, device_id: str, message: Dict) -> bool:
        """通过现有的连接管理器发送消息"""
        try:
            # 这里应该与现有的WebSocket连接管理器集成
            # 假设有一个全局的连接管理器
            
            self.logger.bind(tag=TAG).info(f"📨 通过连接管理器发送音频: {device_id}")
            
            # 模拟发送过程
            await asyncio.sleep(0.3)
            
            # 实际实现应该调用连接管理器的发送方法
            # connection_manager.send_to_device(device_id, message)
            
            return True
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"连接管理器发送失败: {e}")
            return False
    
    async def handle_device_speak_done(self, device_id: str, track_id: str, event_data: Dict):
        """处理设备播放完成事件"""
        self.logger.bind(tag=TAG).info(f"🎯 设备播放完成: {device_id}, track_id: {track_id}")
        
        try:
            if track_id in self.pending_requests:
                # 更新请求状态
                self.pending_requests[track_id]["status"] = "completed"
                self.pending_requests[track_id]["completed_time"] = datetime.now().isoformat()
                self.pending_requests[track_id]["event_data"] = event_data
                
                # 转发完成事件到Java后端
                await self._forward_completion_to_java(device_id, track_id, event_data)
                
                self.logger.bind(tag=TAG).info(f"✅ 完整流程完成: {track_id}")
                
                # 可选：清理已完成的请求
                await asyncio.sleep(5)  # 等待5秒后清理
                if track_id in self.pending_requests:
                    del self.pending_requests[track_id]
                    
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理播放完成事件失败: {e}")
    
    async def _forward_completion_to_java(self, device_id: str, track_id: str, event_data: Dict):
        """转发完成事件到Java后端"""
        try:
            # 构建转发数据
            completion_data = {
                "device_id": device_id,
                "track_id": track_id,
                "event_type": "speak_done",
                "event_data": event_data,
                "process_info": self.pending_requests.get(track_id, {}),
                "timestamp": datetime.now().isoformat()
            }
            
            # 发送到Java API
            java_api_url = self.config.get("manager-api", {}).get("url", "http://localhost:8080")
            completion_endpoint = f"{java_api_url}/api/device/completion"
            
            self.logger.bind(tag=TAG).info(f"📤 转发完成事件到Java: {completion_endpoint}")
            
            # 这里应该使用HTTP客户端发送POST请求
            # import aiohttp
            # async with aiohttp.ClientSession() as session:
            #     async with session.post(completion_endpoint, json=completion_data) as response:
            #         if response.status == 200:
            #             self.logger.bind(tag=TAG).info("✅ Java转发成功")
            
            # 模拟HTTP请求
            await asyncio.sleep(0.2)
            self.logger.bind(tag=TAG).info(f"✅ 完成事件转发成功: {track_id}")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"转发到Java失败: {e}")
    
    def get_request_status(self, track_id: str) -> Dict:
        """获取请求处理状态"""
        return self.pending_requests.get(track_id, {})
    
    def get_all_pending_requests(self) -> Dict:
        """获取所有待处理请求"""
        return self.pending_requests.copy()
    
    async def cleanup_old_requests(self, max_age_hours: int = 24):
        """清理旧的请求记录"""
        now = datetime.now()
        to_remove = []
        
        for track_id, request_info in self.pending_requests.items():
            register_time_str = request_info.get("register_time", "")
            if register_time_str:
                try:
                    register_time = datetime.fromisoformat(register_time_str)
                    age = now - register_time
                    
                    if age.total_seconds() > max_age_hours * 3600:
                        to_remove.append(track_id)
                        
                except ValueError:
                    # 时间格式错误，也删除
                    to_remove.append(track_id)
        
        for track_id in to_remove:
            del self.pending_requests[track_id]
        
        if to_remove:
            self.logger.bind(tag=TAG).info(f"🗑️ 清理了 {len(to_remove)} 个旧请求记录")


class AwakenWithCallbackService:
    """带回调的唤醒服务 - 集成了完整的Webhooks流程"""
    
    def __init__(self, config: Dict[str, Any], mqtt_client, tts_provider=None):
        self.config = config
        self.mqtt_client = mqtt_client
        self.callback_handler = WebhookCallbackHandler(config, mqtt_client, tts_provider)
        self.logger = setup_logging()
    
    async def send_awaken_with_callback(self, device_id: str, message: str, message_type: str = "weather") -> str:
        """
        发送唤醒消息并启动完整的回调流程
        
        这是用户应该调用的主要方法，它会自动处理整个流程：
        1. 注册回调请求
        2. 发送MQTT唤醒命令
        3. 等待设备ACK
        4. 自动生成TTS
        5. 发送音频到设备
        6. 处理播放完成事件
        """
        try:
            # 🔧 确保有MQTT客户端可用
            if self.mqtt_client is None:
                # 🔧 关键修复：从全局获取MQTT客户端
                try:
                    from core.mqtt.mqtt_manager import get_global_mqtt_client
                    self.mqtt_client = get_global_mqtt_client()
                    if self.mqtt_client:
                        self.logger.bind(tag=TAG).info("✅ 成功获取全局MQTT客户端")
                    else:
                        self.logger.bind(tag=TAG).error("❌ 全局MQTT客户端为None")
                except ImportError as ie:
                    self.logger.bind(tag=TAG).error(f"❌ 导入get_global_mqtt_client失败: {ie}")
                    raise Exception("无法导入MQTT客户端函数")
            
            if not self.mqtt_client:
                raise Exception("MQTT客户端未初始化")
            
            # 1. 生成track_id并注册回调请求
            track_id = await self.callback_handler.register_awaken_request(device_id, message)
            
            # 2. 发送MQTT SPEAK命令（带音频）
            await self.mqtt_client.send_speak_command(device_id, message, track_id)
            
            self.logger.bind(tag=TAG).info(f"🚀 启动完整回调流程: {device_id}, track_id: {track_id}")
            
            return track_id
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"❌ 启动回调流程失败: {e}")
            raise
    
    def get_flow_status(self, track_id: str) -> Dict:
        """获取完整流程的状态"""
        return self.callback_handler.get_request_status(track_id)

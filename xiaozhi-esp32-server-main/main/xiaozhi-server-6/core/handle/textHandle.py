import json
import time
import asyncio
from core.handle.abortHandle import handleAbortMessage
from core.handle.helloHandle import handleHelloMessage
from core.providers.tools.device_mcp import handle_mcp_message
from core.utils.util import remove_punctuation_and_length, filter_sensitive_info
from core.handle.receiveAudioHandle import startToChat, handleAudioMessage
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.providers.tools.device_iot import handleIotDescriptors, handleIotStatus
from core.handle.reportHandle import enqueue_asr_report
import asyncio

TAG = __name__


async def handleTextMessage(conn, message):
    """处理文本消息"""
    try:
        msg_json = json.loads(message)
        if isinstance(msg_json, int):
            conn.logger.bind(tag=TAG).info(f"收到文本消息：{message}")
            await conn.websocket.send(message)
            return
        if msg_json["type"] == "hello":
            conn.logger.bind(tag=TAG).info(f"收到hello消息：{message}")
            await handleHelloMessage(conn, msg_json)
        elif msg_json["type"] == "abort":
            conn.logger.bind(tag=TAG).info(f"收到abort消息：{message}")
            
            # 🎯 智能abort处理：延迟处理，检查是否紧跟listen消息
            # 保存abort时间，如果100ms内收到listen start则跳过abort处理
            conn.last_abort_time = time.time()
            
            # 设置延迟处理任务
            async def delayed_abort_handler():
                await asyncio.sleep(0.1)  # 等待100ms
                
                # 检查是否在延迟期间收到了listen start
                if (hasattr(conn, 'last_listen_start_time') and 
                    conn.last_listen_start_time > conn.last_abort_time):
                    conn.logger.bind(tag=TAG).info(f"🛡️ 检测到按钮操作序列，跳过abort处理")
                    return
                
                # 否则正常处理abort
                conn.logger.bind(tag=TAG).info(f"🔄 延迟后执行abort处理")
                await handleAbortMessage(conn)
            
            # 启动延迟任务
            asyncio.create_task(delayed_abort_handler())
        elif msg_json["type"] == "listen":
            conn.logger.bind(tag=TAG).info(f"收到listen消息：{message}")
            if "mode" in msg_json:
                conn.client_listen_mode = msg_json["mode"]
                conn.logger.bind(tag=TAG).debug(
                    f"客户端拾音模式：{conn.client_listen_mode}"
                )
            if msg_json["state"] == "start":
                # 🎯 记录listen start时间，用于智能abort处理
                conn.last_listen_start_time = time.time()
                
                # 🎯 智能按钮逻辑：区分打断和聆听
                # 🔧 更精确的状态判断：只有在真正播放TTS时才算speaking
                is_actually_speaking = (conn.client_is_speaking and 
                                       hasattr(conn, 'tts_actually_started') and 
                                       conn.tts_actually_started)
                
                if is_actually_speaking:
                    # 📱 场景1：播放期间按下 → 打断当前播放
                    conn.logger.bind(tag=TAG).info(f"🔴 播放期间按下按钮 → 打断当前TTS播放")
                    await handleAbortMessage(conn)
                    # 短暂延迟确保abort处理完成
                    await asyncio.sleep(0.1)
                    
                    # 🧹 清除所有对话相关状态，确保全新开始
                    conn.client_abort = False
                    
                    # 🆔 生成新的会话ID，确保完全隔离
                    import uuid
                    conn.session_id = str(uuid.uuid4())
                    conn.logger.bind(tag=TAG).info(f"🆔 打断后生成新会话ID: {conn.session_id}")
                    
                    if hasattr(conn, 'tts') and conn.tts:
                        if hasattr(conn.tts, 'waiting_for_first_audio'):
                            conn.tts.waiting_for_first_audio = False
                    
                    # 🧹 清除之前的对话内容和状态，确保全新开始
                    if hasattr(conn, 'last_tts_complete_time'):
                        delattr(conn, 'last_tts_complete_time')
                    if hasattr(conn, 'just_sent_speaking_status'):
                        conn.just_sent_speaking_status = False
                    
                    if hasattr(conn, 'dialogue') and conn.dialogue:
                        try:
                            # 🔧 检查dialogue对象是否有messages属性
                            if hasattr(conn.dialogue, 'messages'):
                                system_messages = []
                                for msg in conn.dialogue.messages:
                                    if hasattr(msg, 'role') and msg.role == 'system':
                                        system_messages.append(msg)
                                conn.dialogue.messages = system_messages
                                conn.logger.bind(tag=TAG).info(f"🗑️ 清除对话历史，保留{len(system_messages)}条系统消息")
                            else:
                                # 🔧 重新初始化dialogue对象而不是设置为None
                                from core.utils.dialogue import Dialogue
                                conn.dialogue = Dialogue()
                                conn.logger.bind(tag=TAG).info(f"🔄 重新初始化dialogue对象")
                        except Exception as e:
                            conn.logger.bind(tag=TAG).warning(f"清除对话历史时出错: {e}")
                            # 🔧 出错时重新初始化dialogue
                            try:
                                from core.utils.dialogue import Dialogue
                                conn.dialogue = Dialogue()
                                conn.logger.bind(tag=TAG).info(f"🔄 出错后重新初始化dialogue对象")
                            except Exception as init_e:
                                conn.logger.bind(tag=TAG).error(f"重新初始化dialogue失败: {init_e}")
                    
                    # 🔄 强制重置LLM完成标志，确保不会处理之前的响应
                    conn.llm_finish_task = False
                    
                    # 🧹 清除所有TTS相关的显示内容
                    if hasattr(conn, 'current_tts_text'):
                        conn.current_tts_text = ""
                    if hasattr(conn, 'tts_MessageText'):
                        conn.tts_MessageText = ""
                    if hasattr(conn, 'last_system_response'):
                        conn.last_system_response = ""
                    
                    conn.logger.bind(tag=TAG).info(f"🧹 清除所有TTS显示内容，确保不显示旧对话")
                    
                    # 🚫 不在这里重置abort状态，让它在新的语音识别开始时重置
                    conn.logger.bind(tag=TAG).info("🚫 保持abort状态，等待新对话开始时重置")
                    
                    # 📱 进入聆听状态
                    conn.client_have_voice = True
                    conn.client_voice_stop = False
                    # 🔧 新增：专门用于按钮状态跟踪的标志
                    conn.button_is_pressed = True
                    conn.button_press_time = time.time()
                    
                    # 🕐 短暂延迟确保abort处理完全完成
                    await asyncio.sleep(0.15)
                    
                    # 🔄 只发送listen start消息，不发送status消息（避免冲突）
                    listen_start_message = {
                        "type": "listen",
                        "state": "start", 
                        "mode": "manual",
                        "session_id": conn.session_id,
                        "timestamp": int(time.time() * 1000)
                    }
                    await conn.websocket.send(json.dumps(listen_start_message))
                    conn.logger.bind(tag=TAG).info(f"📱 发送listen start消息进入聆听状态 - WebSocket发送: {json.dumps(listen_start_message)}")
                    
                    # 🔄 双重发送确保接收
                    await asyncio.sleep(0.05)
                    await conn.websocket.send(json.dumps(listen_start_message))
                    conn.logger.bind(tag=TAG).info(f"📱 重复发送listen start消息确保硬件接收")
                    
                else:
                    # 📱 场景2：空闲期间按下 → 直接进入聆听状态
                    conn.logger.bind(tag=TAG).info(f"🎤 空闲期间按下按钮 → 直接进入聆听状态")
                    
                    # 🆔 生成新的会话ID，确保新对话完全隔离
                    import uuid
                    conn.session_id = str(uuid.uuid4())
                    conn.logger.bind(tag=TAG).info(f"🆔 新对话生成新会话ID: {conn.session_id}")
                    
                    # 🔄 重置abort状态，确保新对话正常开始
                    conn.client_abort = False
                    
                    # 📱 进入聆听状态
                    conn.client_have_voice = True
                    conn.client_voice_stop = False
                    # 🔧 新增：专门用于按钮状态跟踪的标志
                    conn.button_is_pressed = True
                    conn.button_press_time = time.time()
                    
                    listening_message = {
                        "type": "status", 
                        "state": "listening", 
                        "session_id": conn.session_id,
                        "timestamp": int(time.time() * 1000)
                    }
                    await conn.websocket.send(json.dumps(listening_message))
                    conn.logger.bind(tag=TAG).info(f"📱 空闲状态进入聆听: listening")
                    
                    # 🔄 强制双重发送确保硬件接收状态（防止消息丢失）
                    await asyncio.sleep(0.05)
                    await conn.websocket.send(json.dumps(listening_message))
                    conn.logger.bind(tag=TAG).info(f"📱 强制重发聆听状态确保硬件接收")
                
                # 🎯 按钮控制模式：按下按钮开始聆听，不启动超时机制
                # await _start_listening_timeout(conn)  # 注释掉自动超时
            elif msg_json["state"] == "stop":
                conn.client_have_voice = True
                conn.client_voice_stop = True
                
                # 🔘 按钮松手，聆听状态保持（已删除超时机制）
                conn.logger.bind(tag=TAG).info(f"🔘 按钮松手，聆听状态保持")
                
                if len(conn.asr_audio) > 0:
                    await handleAudioMessage(conn, b"")
                    
                # 🔧 立即更新按钮状态，但设置保护标志
                conn.button_is_pressed = False
                conn.button_just_released = True  # 设置刚松开按钮的标志
                conn.button_release_time = time.time()
                conn.logger.bind(tag=TAG).info(f"🔧 按钮松开: button_is_pressed = False, 设置保护标志")
                
                # 🛡️ 延迟清除保护标志
                async def clear_button_protection():
                    await asyncio.sleep(0.5)  # 500ms保护期
                    conn.button_just_released = False
                    conn.logger.bind(tag=TAG).info(f"🛡️ 清除按钮松开保护标志")
                
                asyncio.create_task(clear_button_protection())
            elif msg_json["state"] == "detect":
                # 🎯 智能detect处理：按钮聆听期间保护状态不被重置
                if (hasattr(conn, 'client_listen_mode') and 
                    conn.client_listen_mode == "manual" and
                    hasattr(conn, 'client_have_voice') and
                    conn.client_have_voice and 
                    not conn.client_voice_stop):
                    conn.logger.bind(tag=TAG).info(f"🛡️ 按钮聆听中，忽略detect状态重置，保护聆听状态")
                else:
                    conn.client_have_voice = False
                    
                conn.asr_audio.clear()
                if "text" in msg_json:
                    conn.last_activity_time = time.time() * 1000
                    # 🎯 用户开始说话（已删除超时机制）
                    original_text = msg_json["text"]  # 保留原始文本
                    filtered_len, filtered_text = remove_punctuation_and_length(
                        original_text
                    )

                    # 识别是否是唤醒词
                    is_wakeup_words = filtered_text in conn.config.get("wakeup_words")
                    # 是否开启唤醒词回复
                    enable_greeting = conn.config.get("enable_greeting", True)

                    if is_wakeup_words and not enable_greeting:
                        # 如果是唤醒词，且关闭了唤醒词回复，就不用回答
                        await send_stt_message(conn, original_text)
                        await send_tts_message(conn, "stop", None)
                        conn.client_is_speaking = False
                        
                        # 📱 唤醒词无回复：明确发送屏幕状态更新回到待机状态
                        idle_message = {
                            "type": "status", 
                            "state": "idle", 
                            "session_id": conn.session_id,
                            "timestamp": int(time.time() * 1000)
                        }
                        await conn.websocket.send(json.dumps(idle_message))
                        conn.logger.bind(tag=TAG).info(f"📱 唤醒词无回复，明确发送屏幕状态更新: idle")
                    elif is_wakeup_words:
                        conn.just_woken_up = True
                        # 🔄 重置abort状态，确保唤醒词对话可以正常处理
                        conn.client_abort = False
                        conn.logger.bind(tag=TAG).info("🔄 唤醒词对话开始，重置abort状态")
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                        enqueue_asr_report(conn, "嘿，你好呀", [])
                        await startToChat(conn, "嘿，你好呀")
                    else:
                        # 保存用户输入用于智能对话结束检测
                        conn.last_user_input = original_text
                        
                        # 🔄 重置abort状态，确保新对话可以正常处理
                        conn.client_abort = False
                        conn.logger.bind(tag=TAG).info("🔄 新对话开始，重置abort状态")
                        
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                        enqueue_asr_report(conn, original_text, [])
                        # 否则需要LLM对文字内容进行答复
                        await startToChat(conn, original_text)
        elif msg_json["type"] == "iot":
            conn.logger.bind(tag=TAG).info(f"收到iot消息：{message}")
            if "descriptors" in msg_json:
                asyncio.create_task(handleIotDescriptors(conn, msg_json["descriptors"]))
            if "states" in msg_json:
                asyncio.create_task(handleIotStatus(conn, msg_json["states"]))
        elif msg_json["type"] == "mcp":
            conn.logger.bind(tag=TAG).info(f"收到mcp消息：{message[:100]}")
            if "payload" in msg_json:
                asyncio.create_task(
                    handle_mcp_message(conn, conn.mcp_client, msg_json["payload"])
                )
        elif msg_json["type"] == "server":
            # 记录日志时过滤敏感信息
            conn.logger.bind(tag=TAG).info(
                f"收到服务器消息：{filter_sensitive_info(msg_json)}"
            )
            # 如果配置是从API读取的，则需要验证secret
            if not conn.read_config_from_api:
                return
            # 获取post请求的secret
            post_secret = msg_json.get("content", {}).get("secret", "")
            secret = conn.config["manager-api"].get("secret", "")
            # 如果secret不匹配，则返回
            if post_secret != secret:
                await conn.websocket.send(
                    json.dumps(
                        {
                            "type": "server",
                            "status": "error",
                            "message": "服务器密钥验证失败",
                        }
                    )
                )
                return
            # 动态更新配置
            if msg_json["action"] == "update_config":
                try:
                    # 更新WebSocketServer的配置
                    if not conn.server:
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "无法获取服务器实例",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    if not await conn.server.update_config():
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "更新服务器配置失败",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    # 发送成功响应
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "success",
                                "message": "配置更新成功",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"更新配置失败: {str(e)}")
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "error",
                                "message": f"更新配置失败: {str(e)}",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
            # 重启服务器
            elif msg_json["action"] == "restart":
                await conn.handle_restart(msg_json)
        else:
            conn.logger.bind(tag=TAG).error(f"收到未知类型消息：{message}")
    except json.JSONDecodeError:
        await conn.websocket.send(message)


# ================================================================
# 🚫 聆听超时机制已删除 - 用户手动控制聆听状态
# ================================================================

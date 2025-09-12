from core.handle.sendAudioHandle import send_stt_message
from core.handle.intentHandler import handle_user_intent
from core.utils.output_counter import check_device_output_limit
from core.handle.abortHandle import handleAbortMessage
import time
import asyncio
import json
from core.handle.sendAudioHandle import SentenceType
from core.utils.util import audio_to_data

TAG = __name__


async def handleAudioMessage(conn, audio):
    # 当前片段是否有人说话
    have_voice = conn.vad.is_vad(conn, audio)
    # 如果设备刚刚被唤醒，短暂忽略VAD检测
    if have_voice and hasattr(conn, "just_woken_up") and conn.just_woken_up:
        have_voice = False
        # 设置一个短暂延迟后恢复VAD检测
        conn.asr_audio.clear()
        if not hasattr(conn, "vad_resume_task") or conn.vad_resume_task.done():
            conn.vad_resume_task = asyncio.create_task(resume_vad_detection(conn))
        return

    if have_voice:
        # 🎯 用户开始说话（已删除超时机制）
        
        # 🎯 智能TTS打断处理 (已禁用)
        # if conn.client_is_speaking:
        #     # 如果不是按钮聆听状态，启用语音打断检测
        #     if not (conn.client_have_voice and not conn.client_voice_stop):
        #         # 🎯 TTS播放期间的语音打断：启用关键词检测模式
        #         await _handle_tts_voice_interruption(conn)
        #     # 如果是按钮聆听状态，不做任何处理，保护TTS
        pass
        
    # 设备长时间空闲检测，用于say goodbye
    await no_voice_close_connect(conn, have_voice)
    # 接收音频
    await conn.asr.receive_audio(conn, audio, have_voice)


async def resume_vad_detection(conn):
    # 等待2秒后恢复VAD检测
    await asyncio.sleep(1)
    conn.just_woken_up = False


# async def _handle_tts_voice_interruption(conn):
#     """处理TTS播放期间的语音打断检测 (已禁用)"""
#     try:
#         # 🔧 TTS语音打断功能默认启用（不依赖配置文件）
#         # 检查是否已经在进行关键词检测
#         if hasattr(conn, 'tts_keyword_detecting') and conn.tts_keyword_detecting:
#             return
#         
#         # 启动关键词检测模式
#         conn.tts_keyword_detecting = True
#         conn.tts_keyword_start_time = time.time()
#         
#         conn.logger.bind(tag=TAG).info("🎙️ TTS播放期间检测到语音，启动关键词检测模式")
#         
#         # 设置3秒超时的关键词检测
#         asyncio.create_task(_tts_keyword_detection_timeout(conn))
#         
#     except Exception as e:
#         conn.logger.bind(tag=TAG).error(f"启动TTS语音打断检测失败: {e}")


# async def _tts_keyword_detection_timeout(conn):
#     """TTS关键词检测超时处理 (已禁用)"""
#     try:
#         # 等待3秒检测关键词
#         await asyncio.sleep(3.0)
#         
#         # 检查是否仍在检测状态
#         if hasattr(conn, 'tts_keyword_detecting') and conn.tts_keyword_detecting:
#             # 超时未检测到关键词，恢复TTS播放状态
#             conn.tts_keyword_detecting = False
#             conn.logger.bind(tag=TAG).info("🔄 关键词检测超时，TTS继续播放")
#             
#             # 清空可能累积的音频数据
#             if hasattr(conn, 'asr_audio'):
#                 conn.asr_audio.clear()
#                 
#     except Exception as e:
#         conn.logger.bind(tag=TAG).error(f"关键词检测超时处理失败: {e}")


# def _check_stop_keywords(text: str) -> bool:
#     """检查是否包含停止关键词 (已禁用)"""
#     if not text:
#         return False
#     
#     # 🔧 硬编码停止关键词列表（不依赖配置文件）
#     stop_keywords = [
#         "停下", "停止", "闭嘴", "别说了", "不要说", "够了", 
#         "停", "别说", "安静", "暂停", "结束", "不用说了",
#         "打住", "行了", "算了", "不说了", "别讲了", "休息"
#     ]
#     
#     # 去除标点符号
#     from core.utils.util import remove_punctuation_and_length
#     _, filtered_text = remove_punctuation_and_length(text)
#     
#     # 检查是否包含任何停止关键词
#     for keyword in stop_keywords:
#         if keyword in filtered_text:
#             return True
#     
#     return False


async def startToChat(conn, text):
    # 🎯 TTS期间关键词检测：优先处理停止指令 (已禁用)
    # if (hasattr(conn, 'tts_keyword_detecting') and conn.tts_keyword_detecting and 
    #     hasattr(conn, 'client_is_speaking') and conn.client_is_speaking):
    #     
    #     # 提取文本内容用于关键词检测
    #     check_text = text
    #     try:
    #         if text.strip().startswith('{') and text.strip().endswith('}'):
    #             data = json.loads(text)
    #             if 'content' in data:
    #                 check_text = data['content']
    #     except (json.JSONDecodeError, KeyError):
    #         pass
    #     
    #     # 检查是否包含停止关键词
    #     if _check_stop_keywords(check_text):
    #         conn.logger.bind(tag=TAG).info(f"🛑 检测到停止关键词: '{check_text}', 立即停止TTS播放")
    #         
    #         # 停止TTS播放并进入静默状态
    #         conn.tts_keyword_detecting = False
    #         await handleAbortMessage(conn)
    #         
    #         # 记录停止事件（不播放声音，保持静默）
    #         conn.logger.bind(tag=TAG).info("🤐 已响应用户停止指令，进入静默状态")
    #         return
    #     else:
    #         conn.logger.bind(tag=TAG).info(f"🔍 TTS期间识别到语音但非停止指令: '{check_text}', 继续播放")
    #         # 非停止关键词，清除检测状态，继续播放TTS
    #         conn.tts_keyword_detecting = False
    #         return
    
    # 检查输入是否是JSON格式（包含说话人信息）
    speaker_name = None
    actual_text = text
    
    try:
        # 尝试解析JSON格式的输入
        if text.strip().startswith('{') and text.strip().endswith('}'):
            data = json.loads(text)
            if 'speaker' in data and 'content' in data:
                speaker_name = data['speaker']
                actual_text = data['content']
                conn.logger.bind(tag=TAG).info(f"解析到说话人信息: {speaker_name}")
                
                # 直接使用JSON格式的文本，不解析
                actual_text = text
    except (json.JSONDecodeError, KeyError):
        # 如果解析失败，继续使用原始文本
        pass
    
    # 保存说话人信息到连接对象
    if speaker_name:
        conn.current_speaker = speaker_name
    else:
        conn.current_speaker = None
    
    # 保存用户输入用于智能对话结束检测
    # 只保存非系统生成的文本（排除结束提示语等）
    if not text.startswith("请你以```时间过得真快```"):
        conn.last_user_input = actual_text

    if conn.need_bind:
        await check_bind_device(conn)
        return

    # 如果当日的输出字数大于限定的字数
    if conn.max_output_size > 0:
        if check_device_output_limit(
            conn.headers.get("device-id"), conn.max_output_size
        ):
            await max_out_size(conn)
            return
    # 🎯 修复按钮聆听被打断的问题：只有在不是主动聆听状态时才打断
    if conn.client_is_speaking and not (conn.client_have_voice and not conn.client_voice_stop):
        await handleAbortMessage(conn)

    # 首先进行意图分析，使用实际文本内容
    intent_handled = await handle_user_intent(conn, actual_text)

    if intent_handled:
        # 如果意图已被处理，不再进行聊天
        return

    # 意图未被处理，继续常规聊天流程，使用实际文本内容
    await send_stt_message(conn, actual_text)
    
    # 🔄 关键修复：重置abort状态，开始新的对话
    if conn.client_abort:
        conn.logger.bind(tag=TAG).info("🔄 检测到abort状态，重置后开始新的LLM对话")
        conn.client_abort = False  # 重置abort状态，允许新对话开始
        
    conn.executor.submit(conn.chat, actual_text)


async def no_voice_close_connect(conn, have_voice):
    if have_voice:
        conn.last_activity_time = time.time() * 1000
        return
    # 只有在已经初始化过时间戳的情况下才进行超时检查
    if conn.last_activity_time > 0.0:
        no_voice_time = time.time() * 1000 - conn.last_activity_time
        # 🎯 临时覆盖：因为配置从Java后端拉取，本地config.yaml不生效
        # 如需永久修改，请联系Java后端修改配置
        close_connection_no_voice_time = 300  # 临时改为5分钟，原为120秒
        # close_connection_no_voice_time = int(
        #     conn.config.get("close_connection_no_voice_time", 120)
        # )
        if (
            not conn.close_after_chat
            and no_voice_time > 1000 * close_connection_no_voice_time
        ):
            conn.close_after_chat = True
            conn.client_abort = False
            # 🎯 临时禁用告别语：直接关闭连接，不播放告别语音
            conn.logger.bind(tag=TAG).info("🔇 临时禁用告别语，直接关闭连接")
            await conn.close()
            return
            
            # 原有的告别语逻辑（已禁用）
            # end_prompt = conn.config.get("end_prompt", {})
            # if end_prompt and end_prompt.get("enable", True) is False:
            #     conn.logger.bind(tag=TAG).info("结束对话，无需发送结束提示语")
            #     await conn.close()
            #     return
            prompt = end_prompt.get("prompt")
            if not prompt:
                prompt = "请你以```时间过得真快```未来头，用富有感情、依依不舍的话来结束这场对话吧。！"
            await startToChat(conn, prompt)


async def max_out_size(conn):
    text = "不好意思，我现在有点事情要忙，明天这个时候我们再聊，约好了哦！明天不见不散，拜拜！"
    await send_stt_message(conn, text)
    
    # 安全检查：确保TTS已经初始化
    if conn.tts is not None:
        try:
            file_path = "config/assets/max_output_size.wav"
            opus_packets, _ = audio_to_data(file_path)
            conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"TTS音频播放失败: {e}")
    else:
        conn.logger.bind(tag=TAG).warning("TTS服务尚未初始化，跳过配额限制音频播放")
    
    conn.close_after_chat = True


async def check_bind_device(conn):
    # 安全检查：确保TTS已经初始化
    if conn.tts is None:
        conn.logger.bind(tag=TAG).warning("TTS服务尚未初始化，跳过绑定设备音频播放")
        
        if conn.bind_code:
            text = f"请登录控制面板，输入{conn.bind_code}，绑定设备。"
            await send_stt_message(conn, text)
        else:
            text = f"没有找到该设备的版本信息，请正确配置 OTA地址，然后重新编译固件。"
            await send_stt_message(conn, text)
        return

    if conn.bind_code:
        # 确保bind_code是6位数字
        if len(conn.bind_code) != 6:
            conn.logger.bind(tag=TAG).error(f"无效的绑定码格式: {conn.bind_code}")
            text = "绑定码格式错误，请检查配置。"
            await send_stt_message(conn, text)
            return

        text = f"请登录控制面板，输入{conn.bind_code}，绑定设备。"
        await send_stt_message(conn, text)

        # 播放提示音
        try:
            music_path = "config/assets/bind_code.wav"
            opus_packets, _ = audio_to_data(music_path)
            conn.tts.tts_audio_queue.put((SentenceType.FIRST, opus_packets, text))

            # 逐个播放数字
            for i in range(6):  # 确保只播放6位数字
                try:
                    digit = conn.bind_code[i]
                    num_path = f"config/assets/bind_code/{digit}.wav"
                    num_packets, _ = audio_to_data(num_path)
                    conn.tts.tts_audio_queue.put((SentenceType.MIDDLE, num_packets, None))
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"播放数字音频失败: {e}")
                    continue
            conn.tts.tts_audio_queue.put((SentenceType.LAST, [], None))
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"TTS音频播放失败: {e}")
    else:
        text = f"没有找到该设备的版本信息，请正确配置 OTA地址，然后重新编译固件。"
        await send_stt_message(conn, text)
        try:
            music_path = "config/assets/bind_not_found.wav"
            opus_packets, _ = audio_to_data(music_path)
            conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"TTS音频播放失败: {e}")


# ================================================================
# 🚫 聆听超时机制已删除
# ================================================================

import json
import asyncio
import time
import uuid
from core.providers.tts.dto.dto import SentenceType
from core.utils import textUtils
# 🚀 WebSocket预缓冲优化导入
from core.utils.websocket_performance_monitor import get_performance_monitor

TAG = __name__


async def sendAudioMessage(conn, sentenceType, audios, text):
    # 🔧 修复：使用会话级别标志修正句子类型
    # 初始化会话级别的第一段标志
    if not hasattr(conn, '_session_first_audio_sent'):
        conn._session_first_audio_sent = False

    # 🔧 移除预缓冲逻辑，简化音频发送流程
    
    # 判断是否是真正的第一段音频
    if conn.tts is not None and conn.tts.tts_audio_first_sentence and not conn._session_first_audio_sent:
        # 真正的第一段
        corrected_type = SentenceType.FIRST
        conn.logger.bind(tag=TAG).info(f"📝 确认真正的第一段: {sentenceType} → {corrected_type}")
        conn.logger.bind(tag=TAG).info(f"发送第一段语音: {text}")
        conn.tts.tts_audio_first_sentence = False
        conn._session_first_audio_sent = True
    elif sentenceType == SentenceType.FIRST and conn._session_first_audio_sent:
        # 后续段错误标记为FIRST，修正为MIDDLE
        corrected_type = SentenceType.MIDDLE
        conn.logger.bind(tag=TAG).info(f"📝 修正后续段: {sentenceType} → {corrected_type}")
    else:
        # 保持原始类型
        corrected_type = sentenceType
    
    # 发送句子开始消息
    conn.logger.bind(tag=TAG).info(f"发送音频消息: {corrected_type}, {text}")
    # 🔧 调试：检查音频数据
    if audios is None:
        conn.logger.bind(tag=TAG).error(f"❌ 音频数据为None: {corrected_type}")
    elif len(audios) == 0:
        conn.logger.bind(tag=TAG).error(f"❌ 音频数据为空数组: {corrected_type}")
    else:
        conn.logger.bind(tag=TAG).info(f"✅ 音频数据正常: {corrected_type}, {len(audios)}帧")

    await send_tts_message(conn, "sentence_start", text)
    
    # 🔧 关键修复：在真正开始发送音频时设置tts_actually_started
    if not hasattr(conn, 'tts_actually_started') or not conn.tts_actually_started:
        conn.tts_actually_started = True
        conn.logger.bind(tag=TAG).info(f"🎯 真正开始发送TTS音频，设置 tts_actually_started = True")

    await sendAudio(conn, audios)  # 🔧 移除pre_buffer参数

    await send_tts_message(conn, "sentence_end", text)



    # 发送结束消息（如果是最后一个文本）
    if conn.llm_finish_task and corrected_type == SentenceType.LAST:
        # 🎯 保存TTS文本用于智能检测和延迟计算
        # 优先使用完整的tts_MessageText，否则使用当前text
        full_tts_text = getattr(conn, 'tts_MessageText', '') or text or ''
        conn.current_tts_text = full_tts_text
        conn.logger.bind(tag=TAG).info(f"💾 保存TTS文本用于智能检测: '{full_tts_text[:50]}{'...' if len(full_tts_text) > 50 else ''}'")
        
        # 🎯 智能选择TTS完成处理方案
        use_event_method = False
        if hasattr(conn, 'config') and conn.config:
            use_event_method = conn.config.get("use_speak_done_event", False)
        
        if use_event_method:
            # 方案一：等待硬件播放完成事件（无延迟，基于实际播放状态）
            task = asyncio.create_task(_handle_tts_completion_with_event(conn, full_tts_text))
        else:
            # 方案二：延迟等待方案（稳定可靠）
            task = asyncio.create_task(_handle_tts_completion_with_delay(conn, full_tts_text))
        
        # 🔧 关键修复：跟踪TTS完成任务，以便abort时取消
        if not hasattr(conn, '_tts_completion_tasks'):
            conn._tts_completion_tasks = set()
        conn._tts_completion_tasks.add(task)
        conn.logger.bind(tag=TAG).info(f"🔧 添加TTS完成任务到跟踪列表: {id(task)}")
        
        # 自动清理完成的任务
        def cleanup_tts_task(task):
            if hasattr(conn, '_tts_completion_tasks') and task in conn._tts_completion_tasks:
                conn._tts_completion_tasks.discard(task)
                conn.logger.bind(tag=TAG).debug(f"🔧 TTS完成任务自动清理: {id(task)}")
        
        task.add_done_callback(lambda t: cleanup_tts_task(t))


# 🎵 优化版音频发送 - 智能缓冲与自适应间隔
async def sendAudio(conn, audios):  # 🔧 移除pre_buffer参数
    if audios is None or len(audios) == 0:
        conn.logger.bind(tag=TAG).warning(f"⚠️ sendAudio跳过：音频数据为空 (audios={audios})")
        return
    
    conn.logger.bind(tag=TAG).info(f"🎵 开始发送音频: {len(audios)}帧")
    sent_frames = 0
    failed_frames = 0
    
    # 🎛️ 自适应参数
    base_interval = 0.055  # 基础55ms间隔
    current_interval = base_interval
    max_interval = 0.070   # 最大70ms间隔
    min_interval = 0.045   # 最小45ms间隔
    
    # 🔧 取消预缓冲策略：避免开头播放过快导致听起来奇怪
    prebuffer_frames = 0  # 禁用预缓冲，保持全程恒定播放速度
    
    # 📊 性能监控
    start_time = time.time()
    last_success_time = start_time
    
    for i, opus_packet in enumerate(audios):
        if conn.client_abort:
            conn.logger.bind(tag=TAG).info(f"⏹️ 音频发送被中止，已发送{sent_frames}帧")
            break

        # 重置活动时间
        conn.last_activity_time = time.time() * 1000

        # 📡 发送尝试（带智能重试机制）
        max_retries = 2
        retry_count = 0
        frame_sent = False
        
        # 🔍 简化的WebSocket连接检查
        if not conn.websocket:
            conn.logger.bind(tag=TAG).error(f"❌ WebSocket连接为空，停止音频发送")
            break
        
        while retry_count <= max_retries and not frame_sent:
            try:
                # 🕒 检查连接是否保持活跃
                current_time = time.time() * 1000
                if hasattr(conn, 'last_keepalive_time'):
                    if current_time - getattr(conn, 'last_keepalive_time', 0) > 30000:  # 30秒无keepalive
                        conn.logger.bind(tag=TAG).warning(f"⚠️ 长时间无keepalive消息，可能存在连接问题")
                
                await conn.websocket.send(opus_packet)
                sent_frames += 1
                frame_sent = True
                last_success_time = time.time()
                
                # 📈 成功发送，逐渐优化间隔
                if current_interval > min_interval:
                    current_interval = max(min_interval, current_interval - 0.002)
                    
            except asyncio.TimeoutError:
                retry_count += 1
                failed_frames += 1
                conn.logger.bind(tag=TAG).warning(f"⏰ 帧{i+1}发送超时，重试{retry_count}/{max_retries}")
                current_interval = min(max_interval, current_interval + 0.010)
                await asyncio.sleep(0.020 * retry_count)
                
            except (ConnectionError, ConnectionResetError, BrokenPipeError) as conn_error:
                retry_count += 1
                failed_frames += 1
                conn.logger.bind(tag=TAG).error(f"🔌 帧{i+1}连接错误，重试{retry_count}/{max_retries}: {conn_error}")
                current_interval = min(max_interval, current_interval + 0.015)
                await asyncio.sleep(0.050 * retry_count)  # 连接错误需要更长延迟
                
            except Exception as ws_error:
                retry_count += 1
                failed_frames += 1
                
                if retry_count <= max_retries:
                    conn.logger.bind(tag=TAG).warning(f"⚠️ 帧{i+1}发送失败，重试{retry_count}/{max_retries}: {ws_error}")
                    # 📉 发送失败，增加间隔和重试延迟
                    current_interval = min(max_interval, current_interval + 0.005)
                    await asyncio.sleep(0.010 * retry_count)  # 递增重试延迟
                else:
                    conn.logger.bind(tag=TAG).error(f"❌ 帧{i+1}发送彻底失败: {ws_error}")
                    break
        
        # 如果帧发送失败，跳过该帧继续
        if not frame_sent:
            conn.logger.bind(tag=TAG).warning(f"⚠️ 跳过第{i+1}帧，继续发送后续帧")
            continue
            
        # 📊 定期进度报告
        if sent_frames % 10 == 0:
            elapsed = time.time() - start_time
            avg_rate = sent_frames / elapsed if elapsed > 0 else 0
            conn.logger.bind(tag=TAG).info(f"📊 音频发送进度: {sent_frames}/{len(audios)}帧, 速率:{avg_rate:.1f}帧/秒, 间隔:{current_interval*1000:.1f}ms")
        
        # 🎛️ 恒定间隔控制 - 修复语音播放速度问题
        # 🔧 关键修复：全程使用固定间隔，避免播放速度变化导致听感异常
        await asyncio.sleep(base_interval)  # 固定55ms间隔，确保播放速度始终稳定
    
    # 📈 最终统计和网络质量评估
    total_time = time.time() - start_time
    success_rate = (sent_frames / len(audios)) * 100 if len(audios) > 0 else 0
    avg_rate = sent_frames / total_time if total_time > 0 else 0
    
    # 🎯 网络质量评级
    if success_rate >= 98 and avg_rate >= 16:
        quality_rating = "🟢 优秀"
    elif success_rate >= 95 and avg_rate >= 14:
        quality_rating = "🟡 良好"  
    elif success_rate >= 90 and avg_rate >= 12:
        quality_rating = "🟠 一般"
    else:
        quality_rating = "🔴 需优化"
    
    # 📊 性能建议
    performance_tips = []
    if success_rate < 95:
        performance_tips.append("建议检查网络连接稳定性")
    if avg_rate < 14:
        performance_tips.append("传输速度偏慢，可能影响音频连续性")
    if failed_frames > len(audios) * 0.05:
        performance_tips.append("失败帧数过多，建议检查WebSocket配置")
    
    conn.logger.bind(tag=TAG).info(
        f"🎵 音频发送完成: {sent_frames}/{len(audios)}帧 "
        f"(成功率:{success_rate:.1f}%, 失败:{failed_frames}帧, "
        f"耗时:{total_time:.2f}s, 平均速率:{avg_rate:.1f}帧/秒, "
        f"网络质量:{quality_rating})"
    )
    
    # 🔧 性能建议日志
    if performance_tips:
        conn.logger.bind(tag=TAG).warning(f"💡 性能建议: {'; '.join(performance_tips)}")
    
    # 📊 保存性能指标用于后续分析
    if not hasattr(conn, '_audio_performance_history'):
        conn._audio_performance_history = []
    
    conn._audio_performance_history.append({
        'timestamp': time.time(),
        'total_frames': len(audios),
        'sent_frames': sent_frames,
        'failed_frames': failed_frames,
        'success_rate': success_rate,
        'avg_rate': avg_rate,
        'total_time': total_time,
        'final_interval': current_interval
    })
    
    # 🗑️ 保留最近10次记录
    if len(conn._audio_performance_history) > 10:
        conn._audio_performance_history = conn._audio_performance_history[-10:]


async def send_tts_message(conn, state, text=None):
    """发送 TTS 状态消息"""
    message = {"type": "tts", "state": state, "session_id": conn.session_id}
    if text is not None:
        message["text"] = textUtils.check_emoji(text)

    # 🔧 状态同步修复：确保屏幕状态与实际TTS状态一致
    if state == "start":
        # 🔇 TTS开始播放（已删除超时机制）
        conn.logger.bind(tag=TAG).info(f"🔇 TTS开始播放")
        
        # TTS开始播放 - 设置说话状态
        conn.client_is_speaking = True
        # 🔧 关键修复：区分TTS消息开始和真正的音频播放开始
        # 只有在发送实际音频时才设置tts_actually_started
        # 这里只是TTS消息的开始，不代表音频已经开始播放
        conn.tts_message_started = True  # 新标志：TTS消息已开始
        conn.logger.bind(tag=TAG).info(f"🎯 TTS消息开始，设置状态: client_is_speaking = True, tts_message_started = True")
        
        # 🛠️ 检查是否需要发送屏幕状态（避免重复发送）
        # 如果刚刚在send_stt_message中已经发送了speaking状态，就不重复发送
        # 💡 硬件端反馈：不支持"type": "listen"消息类型，暂时注释掉状态消息
        # if not (hasattr(conn, 'just_sent_speaking_status') and conn.just_sent_speaking_status):
        #     # 📱 发送屏幕状态更新：进入说话状态
        #     screen_message = {
        #         "type": "listen", 
        #         "state": "stop", 
        #         "mode": "speaking",
        #         "session_id": conn.session_id,
        #         "timestamp": int(time.time() * 1000)
        #     }
        #     await conn.websocket.send(json.dumps(screen_message))
        #     conn.logger.bind(tag=TAG).info(f"📱 TTS start发送屏幕状态更新: speaking - 会话ID: {conn.session_id}")
        #     conn.logger.bind(tag=TAG).info(f"🔍 发送的完整speaking消息: {json.dumps(screen_message)}")
        # else:
        #     conn.logger.bind(tag=TAG).info(f"📱 跳过重复的speaking状态发送（已在STT中发送）")
        #     # 清除标志
        #     conn.just_sent_speaking_status = False
        
        # 💡 由于注释掉了状态消息发送，这里统一清除标志
        if hasattr(conn, 'just_sent_speaking_status'):
            conn.just_sent_speaking_status = False
        
    elif state == "stop":
        # TTS播放结束 - 清除说话状态
        conn.client_is_speaking = False
        conn.tts_actually_started = False  # 🔧 清除TTS播放标志
        conn.tts_message_started = False   # 🔧 清除TTS消息标志
        conn.logger.bind(tag=TAG).info(f"🎯 TTS播放结束，清除说话状态: client_is_speaking = False, tts_actually_started = False, tts_message_started = False")
        
        # 🛠️ 关键修复：TTS stop不主动发送屏幕状态，让后续逻辑决定
        # 只有在特定情况下才发送idle状态（如唤醒词无回复、对话结束等）
        conn.logger.bind(tag=TAG).info(f"🔧 TTS stop完成，屏幕状态由后续逻辑决定")
        
        # 🔧 记录TTS完成时间，用于检测短暂待机期间的按钮竞态
        conn.last_tts_complete_time = time.time()
        
        # 播放提示音
        tts_notify = conn.config.get("enable_stop_tts_notify", False)
        if tts_notify and conn.tts is not None:
            try:
                stop_tts_notify_voice = conn.config.get(
                    "stop_tts_notify_voice", "config/assets/tts_notify.mp3"
                )
                audios, _ = conn.tts.audio_to_opus_data(stop_tts_notify_voice)
                await sendAudio(conn, audios)
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"播放停止TTS提示音失败: {e}")
        
        # 清除服务端讲话状态
        conn.clearSpeakStatus()

    # 发送TTS消息到客户端
    await conn.websocket.send(json.dumps(message))


async def send_stt_message(conn, text):
    end_prompt_str = conn.config.get("end_prompt", {}).get("prompt")
    if end_prompt_str and end_prompt_str == text:
        await send_tts_message(conn, "start")
        return

    """发送 STT 状态消息"""
    
    # 🛠️ 关键修复：按钮聆听状态转换问题 - 确保直接从聆听转到说话状态
    is_button_listening = False
    
    # 🔧 检测按钮模式的多种方式
    is_manual_mode = (hasattr(conn, 'client_listen_mode') and 
                     conn.client_listen_mode == "manual")
    has_button_voice = (hasattr(conn, 'client_have_voice') and conn.client_have_voice)
    just_released_button = (hasattr(conn, 'button_just_released') and conn.button_just_released)
    
    # 🎯 如果是按钮模式或刚松开按钮，都认为是按钮聆听
    if is_manual_mode or has_button_voice or just_released_button:
        is_button_listening = True
        if has_button_voice:
            conn.client_have_voice = False
            conn.client_voice_stop = False
        conn.logger.bind(tag=TAG).info(f"🔄 检测到按钮模式聆听 (manual_mode={is_manual_mode}, has_voice={has_button_voice}, just_released={just_released_button})，直接进入说话状态")
    
    # 解析JSON格式，提取实际的用户说话内容
    display_text = text
    try:
        # 尝试解析JSON格式
        if text.strip().startswith('{') and text.strip().endswith('}'):
            parsed_data = json.loads(text)
            if isinstance(parsed_data, dict) and "content" in parsed_data:
                # 如果是包含说话人信息的JSON格式，只显示content部分
                display_text = parsed_data["content"]
                # 保存说话人信息到conn对象
                if "speaker" in parsed_data:
                    conn.current_speaker = parsed_data["speaker"]
    except (json.JSONDecodeError, TypeError):
        # 如果不是JSON格式，直接使用原始文本
        display_text = text
    stt_text = textUtils.get_string_no_punctuation_or_emoji(display_text)
    await conn.websocket.send(
        json.dumps({"type": "stt", "text": stt_text, "session_id": conn.session_id})
    )
    
    # 🛠️ 关键修复：按钮聆听后，立即进入说话状态，跳过processing和idle
    if is_button_listening:
        # 🔧 按钮聆听，立即发送说话状态
        conn.client_is_speaking = True
        # 🔄 使用listen消息类型保持一致性
        # 💡 硬件端反馈：不支持"type": "listen"消息类型，暂时注释掉状态消息
        # speaking_message = {
        #     "type": "listen", 
        #     "state": "stop", 
        #     "mode": "manual",
        #     "session_id": conn.session_id,
        #     "timestamp": int(time.time() * 1000)
        # }
        # await conn.websocket.send(json.dumps(speaking_message))
        conn.logger.bind(tag=TAG).info(f"🎯 按钮聆听完成，跳过状态消息发送（硬件端不支持listen类型）")
        
        # 🔧 设置标志，避免TTS start时重复发送speaking状态
        conn.just_sent_speaking_status = True
    else:
        # 📱 正常流程：发送处理状态
        # 💡 硬件端反馈：不支持"type": "listen"消息类型，暂时注释掉状态消息
        # processing_message = {
        #     "type": "listen", 
        #     "state": "stop", 
        #     "mode": "processing",
        #     "session_id": conn.session_id,
        #     "timestamp": int(time.time() * 1000)
        # }
        # await conn.websocket.send(json.dumps(processing_message))
        conn.logger.bind(tag=TAG).info(f"📱 跳过处理状态消息发送（硬件端不支持listen类型）")
        
        # 🔧 正常流程也需要设置说话状态
    conn.client_is_speaking = True
    conn.logger.bind(tag=TAG).info(f"🎯 设置说话状态: client_is_speaking = True")
    await send_tts_message(conn, "start")


# ================================================================
# 🎯 硬件播放完成事件处理机制（方案一：无延迟，基于实际播放状态）
# ================================================================

async def _handle_tts_completion_with_event(conn, text):
    """处理TTS播放完成 - 基于硬件播放完成事件（无固定延迟）"""
    try:
        # 保存当前TTS文本用于智能检测
        conn.current_tts_text = text
        
        # 生成唯一的音频track_id用于事件追踪
        track_id = f"TTS_{uuid.uuid4().hex[:8]}_{int(time.time() * 1000)}"
        
        # 设置连接状态，等待硬件播放完成事件
        conn.waiting_for_speak_done = True
        conn.speak_done_track_id = track_id
        conn.speak_done_timestamp = time.time()
        
        conn.logger.bind(tag=TAG).info(f"🎵 等待硬件播放完成事件: track_id={track_id}")
        conn.logger.bind(tag=TAG).info(f"📝 播放文本: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # 在发送的音频消息中包含track_id，供硬件端使用
        await _send_tts_with_track_id(conn, track_id)
        
        # 启动超时保护机制（防止硬件无响应）
        timeout_seconds = 15.0  # 默认15秒超时
        if hasattr(conn, 'config') and conn.config:
            timeout_seconds = conn.config.get("speak_done_timeout", 15.0)
        asyncio.create_task(_speak_done_timeout_handler(conn, track_id, timeout_seconds))
        
        conn.logger.bind(tag=TAG).info(f"⏰ 播放完成超时保护: {timeout_seconds}秒")
        
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"设置播放完成事件监听失败: {e}")
        # 降级处理：发送普通stop消息并立即完成
        try:
            await send_tts_message(conn, "stop", None)
            conn.logger.bind(tag=TAG).info(f"🔄 降级处理：已发送普通TTS stop消息")
        except Exception as stop_error:
            conn.logger.bind(tag=TAG).error(f"发送降级stop消息失败: {stop_error}")
        
        await _complete_tts_and_start_vad(conn)


async def _handle_tts_completion_with_delay(conn, text):
    """处理TTS播放完成 - 基于延迟等待（稳定方案）"""
    try:
        # 保存当前TTS文本用于智能检测
        conn.current_tts_text = text
        
        # 🎯 动态计算延迟时间（基于文本长度和配置）
        base_delay = 3.0  # 默认基础延迟
        dynamic_enabled = True  # 默认启用动态延迟
        min_delay = 4.0  # 默认最小延迟4秒
        max_delay = 10.0  # 默认最大延迟10秒
        
        if hasattr(conn, 'config') and conn.config:
            base_delay = conn.config.get("tts_completion_delay", 3.0)
            dynamic_enabled = conn.config.get("dynamic_tts_delay", True)
            min_delay = conn.config.get("min_tts_delay", 4.0)
            max_delay = conn.config.get("max_tts_delay", 10.0)
            
            # 🚨 临时修复：确保足够的延迟时间避免语音中断
            if min_delay < 1.0:
                original_min = min_delay
                min_delay = 1.0  # 临时设置最小1秒
                conn.logger.bind(tag=TAG).info(f"🔧 临时修复：最小延迟从 {original_min}秒 增加到 {min_delay}秒")
        
        if dynamic_enabled:
            # 根据文本长度动态调整延迟（使用完整TTS文本）
            full_text = getattr(conn, 'current_tts_text', '') or text or ''
            text_length = len(full_text)
            
            # 🔍 调试：显示文本获取情况
            conn.logger.bind(tag=TAG).debug(f"🔍 延迟计算文本来源: current_tts_text='{getattr(conn, 'current_tts_text', 'None')}', text='{text}', full_text='{full_text}'")
            
            # 智能延迟算法：基础延迟 + 文本长度延迟，但有最小最大限制
            # 每25个字符增加0.5秒
            text_delay = (text_length // 25) * 0.5
            calculated_delay = base_delay + text_delay
            
            # 应用最小最大限制
            delay_seconds = max(min_delay, min(calculated_delay, max_delay))
            
            conn.logger.bind(tag=TAG).info(f"📏 动态延迟计算: {text_length}字符 → 基础{base_delay}s + 文本{text_delay:.1f}s = {calculated_delay:.1f}s")
            conn.logger.bind(tag=TAG).info(f"⏰ 应用限制: min={min_delay}s, max={max_delay}s → 最终{delay_seconds:.1f}秒")
        else:
            delay_seconds = max(base_delay, min_delay)  # 至少使用最小延迟
            conn.logger.bind(tag=TAG).info(f"⏰ 固定延迟模式: {delay_seconds}秒")
        
        if delay_seconds > 0:
            conn.logger.bind(tag=TAG).info(f"⏱️ 延迟等待TTS播放完成: {delay_seconds}秒")
            await asyncio.sleep(delay_seconds)
        
        # 🚫 关键修复：延迟等待后检查abort状态
        if conn.client_abort:
            conn.logger.bind(tag=TAG).info(f"🚫 延迟等待后检测到abort，停止TTS完成处理")
            return
        
        await send_tts_message(conn, "stop", None)
        conn.logger.bind(tag=TAG).info(f"🎯 TTS stop消息已发送（修复硬件反馈问题）")
        
        # 🎯 额外保障：检查是否有completion回调需要执行（主要用于主动问候）
        if hasattr(conn, 'tts_completion_callback') and callable(conn.tts_completion_callback):
            try:
                conn.tts_completion_callback()
                conn.logger.bind(tag=TAG).info("🔄 执行TTS完成回调")
            except Exception as callback_error:
                conn.logger.bind(tag=TAG).error(f"TTS完成回调执行失败: {callback_error}")
        
        # 🎯 智能结束检测：检查是否需要停止聆听
        conn.logger.bind(tag=TAG).info(f"🔍 开始智能对话结束检测（延迟方案）")
        should_stop_listening = _should_stop_listening_after_response(conn, text)
        conn.logger.bind(tag=TAG).info(f"🔍 智能检测结果: {should_stop_listening}")
        
        # 🚫 关键修复：在检查智能结束前先检查abort状态
        if conn.client_abort:
            conn.logger.bind(tag=TAG).info(f"🚫 延迟TTS完成检测到abort状态，完全跳过智能结束处理")
            return
            
        if should_stop_listening:
            # 对话自然结束，不启动VAD聆听
            conn.client_is_speaking = False
            conn.logger.bind(tag=TAG).info(f"💤 检测到对话结束，停止聆听模式（延迟方案）")
            
            # 🛡️ 按钮聆听保护：如果用户正在按住按钮，不要发送idle状态
            is_button_listening = (hasattr(conn, 'button_is_pressed') and conn.button_is_pressed)
            
            if is_button_listening:
                conn.logger.bind(tag=TAG).info(f"🛡️ 检测到用户正在按住按钮聆听，保持listening状态不发送idle")
                # 发送listening状态确保硬件显示正确
                # 💡 硬件端反馈：不支持"type": "listen"消息类型，暂时注释掉状态消息

                # listening_message = {

                #                 "type": "listen", 

                #                 "state": "start", 

                #                 "mode": "auto",

                #                 "session_id": conn.session_id,

                #                 "timestamp": int(time.time() * 1000)

                #                 }

                # await conn.websocket.send(json.dumps(listening_message))
                conn.logger.bind(tag=TAG).info(f"📱 对话结束但用户仍在聆听，跳过状态消息发送（硬件端不支持listen类型）屏幕状态更新: listening")
            else:
                # 📱 发送屏幕状态更新：回到待机状态
                # 💡 硬件端反馈：不支持"type": "listen"消息类型，暂时注释掉状态消息

                # idle_message = {

                #                 "type": "listen", 

                #                 "state": "stop", 

                #                 "mode": "idle",

                #                 "session_id": conn.session_id,

                #                 "timestamp": int(time.time() * 1000)

                #                 }

                # await conn.websocket.send(json.dumps(idle_message))
                conn.logger.bind(tag=TAG).info(f"📱 对话结束，跳过状态消息发送（硬件端不支持listen类型）屏幕状态更新: idle")
            
            # 发送停止聆听信号给硬件
            await _send_stop_listening_message(conn)
        else:
            # 🎤 正常启动VAD聆听（新逻辑：按钮按下会直接停止TTS，无需保护）
            conn.client_is_speaking = False
            conn.logger.bind(tag=TAG).info(f"🎤 延迟等待完成，启动VAD聆听模式")
            
            # 📱 发送屏幕状态更新：进入聆听状态
            # 💡 硬件端反馈：不支持"type": "listen"消息类型，暂时注释掉状态消息

            # listening_message = {

            #                 "type": "listen", 

            #                 "state": "start", 

            #                 "mode": "auto",

            #                 "session_id": conn.session_id,

            #                 "timestamp": int(time.time() * 1000)

            #             }

            # await conn.websocket.send(json.dumps(listening_message))
            conn.logger.bind(tag=TAG).info(f"📱 跳过状态消息发送（硬件端不支持listen类型）屏幕状态更新: listening")
        
        if conn.close_after_chat:
            await conn.close()
            
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"延迟处理TTS完成失败: {e}")
        # 降级到立即完成
        try:
            await send_tts_message(conn, "stop", None)
            conn.logger.bind(tag=TAG).info(f"🎯 异常处理中TTS stop消息已发送（修复硬件反馈问题）")
            conn.client_is_speaking = False
            
            # 🛡️ 按钮聆听保护：如果用户正在按住按钮，不要发送idle状态
            is_button_listening = (hasattr(conn, 'button_is_pressed') and conn.button_is_pressed)
            
            if is_button_listening:
                conn.logger.bind(tag=TAG).info(f"🛡️ 检测到用户正在按住按钮聆听，保持listening状态不发送idle")
                # 发送listening状态确保硬件显示正确
                # 💡 硬件端反馈：不支持"type": "listen"消息类型，暂时注释掉状态消息

                # listening_message = {

                #                 "type": "listen", 

                #                 "state": "start", 

                #                 "mode": "auto",

                #                 "session_id": conn.session_id,

                #                 "timestamp": int(time.time() * 1000)

                #                 }

                # await conn.websocket.send(json.dumps(listening_message))
                conn.logger.bind(tag=TAG).info(f"📱 强制停止但用户仍在聆听，跳过状态消息发送（硬件端不支持listen类型）屏幕状态更新: listening")
            else:
                # 📱 发送屏幕状态更新：强制回到待机状态
                # 💡 硬件端反馈：不支持"type": "listen"消息类型，暂时注释掉状态消息

                # idle_message = {

                #                 "type": "listen", 

                #                 "state": "stop", 

                #                 "mode": "idle",

                #                 "session_id": conn.session_id,

                #                 "timestamp": int(time.time() * 1000)

                #                 }

                # await conn.websocket.send(json.dumps(idle_message))
                conn.logger.bind(tag=TAG).info(f"📱 强制停止后，跳过状态消息发送（硬件端不支持listen类型）屏幕状态更新: idle")
        except:
            pass


async def _send_tts_with_track_id(conn, track_id: str):
    """发送带有track_id的TTS完成消息"""
    try:
        # 发送包含track_id的stop消息，供硬件端识别
        message = {
            "type": "tts", 
            "state": "stop", 
            "session_id": conn.session_id,
            "track_id": track_id,  # 🔑 关键：硬件需要用此ID上报完成事件
            "timestamp": int(time.time() * 1000)
        }
        
        await conn.websocket.send(json.dumps(message))
        conn.logger.bind(tag=TAG).info(f"📤 发送TTS stop消息 (track_id: {track_id})")
        
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"发送TTS stop消息失败: {e}")


async def _speak_done_timeout_handler(conn, track_id: str, timeout_seconds: float):
    """播放完成超时处理"""
    try:
        await asyncio.sleep(timeout_seconds)
        
        # 检查是否还在等待该track_id的完成事件
        if (hasattr(conn, 'waiting_for_speak_done') and conn.waiting_for_speak_done and
            hasattr(conn, 'speak_done_track_id') and conn.speak_done_track_id == track_id):
            
            conn.logger.bind(tag=TAG).warning(f"⏰ 播放完成事件超时: track_id={track_id}")
            conn.logger.bind(tag=TAG).warning(f"💡 硬件可能未发送EVT_SPEAK_DONE事件，降级处理")
            
            # 超时后自动完成
            await _complete_tts_and_start_vad(conn)
            
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"超时处理失败: {e}")


async def handle_speak_done_event(conn, track_id: str, status: str = "completed"):
    """处理硬件发送的播放完成事件"""
    try:
        # 检查是否正在等待此track_id的完成事件
        if (hasattr(conn, 'waiting_for_speak_done') and conn.waiting_for_speak_done and
            hasattr(conn, 'speak_done_track_id') and conn.speak_done_track_id == track_id):
            
            elapsed_time = time.time() - getattr(conn, 'speak_done_timestamp', time.time())
            conn.logger.bind(tag=TAG).info(f"✅ 收到硬件播放完成事件: track_id={track_id}")
            conn.logger.bind(tag=TAG).info(f"⏱️ 实际播放时长: {elapsed_time:.2f}秒")
            
            if status == "completed":
                conn.logger.bind(tag=TAG).info(f"🎉 播放成功完成，启动VAD聆听")
                await _complete_tts_and_start_vad(conn)
            else:
                conn.logger.bind(tag=TAG).warning(f"⚠️ 播放异常: {status}，仍启动VAD")
                await _complete_tts_and_start_vad(conn)
                
        else:
            conn.logger.bind(tag=TAG).debug(f"🔍 收到播放完成事件但不匹配当前等待: track_id={track_id}")
            
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"处理播放完成事件失败: {e}")


async def _complete_tts_and_start_vad(conn):
    """完成TTS播放并启动VAD聆听"""
    try:
        # 清理等待状态
        if hasattr(conn, 'waiting_for_speak_done'):
            conn.waiting_for_speak_done = False
        if hasattr(conn, 'speak_done_track_id'):
            conn.speak_done_track_id = None
        if hasattr(conn, 'speak_done_timestamp'):
            conn.speak_done_timestamp = None
        
        # 🎯 智能结束检测：检查是否需要停止聆听
        # 获取当前TTS文本（从事件方案中我们没有直接的text参数，需要从连接对象获取）
        current_text = getattr(conn, 'current_tts_text', '')
        should_stop_listening = _should_stop_listening_after_response(conn, current_text)
        
        # 🚫 关键修复：在检查智能结束前先检查abort状态
        if conn.client_abort:
            conn.logger.bind(tag=TAG).info(f"🚫 事件TTS完成检测到abort状态，完全跳过智能结束处理")
            return
        
        if should_stop_listening:
            # 对话自然结束，不启动VAD聆听
            conn.client_is_speaking = False
            conn.logger.bind(tag=TAG).info(f"💤 检测到对话结束，停止聆听模式")
            
            # 🛡️ 按钮聆听保护：如果用户正在按住按钮，不要发送idle状态
            is_button_listening = (hasattr(conn, 'button_is_pressed') and conn.button_is_pressed)
            
            if is_button_listening:
                conn.logger.bind(tag=TAG).info(f"🛡️ 检测到用户正在按住按钮聆听，保持listening状态不发送idle")
                # 发送listening状态确保硬件显示正确
                # 💡 硬件端反馈：不支持"type": "listen"消息类型，暂时注释掉状态消息

                # listening_message = {

                #                 "type": "listen", 

                #                 "state": "start", 

                #                 "mode": "auto",

                #                 "session_id": conn.session_id,

                #                 "timestamp": int(time.time() * 1000)

                #                 }

                # await conn.websocket.send(json.dumps(listening_message))
                conn.logger.bind(tag=TAG).info(f"📱 对话结束但用户仍在聆听，跳过状态消息发送（硬件端不支持listen类型）屏幕状态更新: listening")
            else:
                # 📱 发送屏幕状态更新：回到待机状态
                # 💡 硬件端反馈：不支持"type": "listen"消息类型，暂时注释掉状态消息

                # idle_message = {

                #                 "type": "listen", 

                #                 "state": "stop", 

                #                 "mode": "idle",

                #                 "session_id": conn.session_id,

                #                 "timestamp": int(time.time() * 1000)

                #                 }

                # await conn.websocket.send(json.dumps(idle_message))
                conn.logger.bind(tag=TAG).info(f"📱 对话结束，跳过状态消息发送（硬件端不支持listen类型）屏幕状态更新: idle")
            
            # 发送停止聆听信号给硬件
            await _send_stop_listening_message(conn)
        else:
            # 🎤 TTS播放完成后的状态处理
            conn.client_is_speaking = False  
            conn.logger.bind(tag=TAG).info(f"🎤 TTS播放完成，检查是否需要启动VAD聆听")
            
            # 🛡️ 检查用户是否在按住按钮（优先保持聆听状态）
            is_button_listening = (hasattr(conn, 'button_is_pressed') and conn.button_is_pressed)
            
            if is_button_listening:
                conn.logger.bind(tag=TAG).info(f"🛡️ TTS完成但用户仍在按住按钮，保持listening状态")
                # 发送listening状态确保硬件显示正确
                # 💡 硬件端反馈：不支持"type": "listen"消息类型，暂时注释掉状态消息

                # listening_message = {

                #                 "type": "listen", 

                #                 "state": "start", 

                #                 "mode": "auto",

                #                 "session_id": conn.session_id,

                #                 "timestamp": int(time.time() * 1000)

                #                 }

                # await conn.websocket.send(json.dumps(listening_message))
                conn.logger.bind(tag=TAG).info(f"📱 TTS完成保持聆听状态: listening")
            else:
                # 🚫 关键修复：在发送idle前检查abort状态
                if conn.client_abort:
                    conn.logger.bind(tag=TAG).info(f"🚫 TTS完成检测到abort状态，跳过发送idle状态")
                    return
                
                # 🔧 检查是否为按钮模式（manual mode）
                is_manual_mode = (hasattr(conn, 'client_listen_mode') and 
                                conn.client_listen_mode == "manual")
                
                if is_manual_mode:
                    # 🎯 按钮模式：TTS完成后保持当前状态，不主动发送idle
                    conn.logger.bind(tag=TAG).info(f"🎯 按钮模式TTS完成，保持当前状态不发送idle")
                else:
                    # 🚨 自动模式：TTS播放完成后延迟1秒进入idle状态
                    conn.logger.bind(tag=TAG).info(f"💤 自动模式TTS完成，1秒后进入待机状态")
                    
                    # 🔧 添加1秒延迟再发送idle状态
                    await asyncio.sleep(1.0)
                    
                    # 🚫 延迟后再次检查abort状态
                    if conn.client_abort:
                        conn.logger.bind(tag=TAG).info(f"🚫 延迟1秒后检测到abort状态，跳过发送idle状态")
                        return
                    
                    # 💡 硬件端反馈：不支持"type": "listen"消息类型，暂时注释掉状态消息

                    
                    # idle_message = {

                    
                    #                 "type": "listen", 

                    
                    #                 "state": "stop", 

                    
                    #                 "mode": "idle",

                    
                    #                 "session_id": conn.session_id,

                    
                    #                 "timestamp": int(time.time() * 1000)

                    
                    #                     }

                    
                    # await conn.websocket.send(json.dumps(idle_message))
                    conn.logger.bind(tag=TAG).info(f"📱 TTS完成延迟1秒后跳过状态消息发送（硬件端不支持listen类型）屏幕状态更新: idle")
        
        if conn.close_after_chat:
            await conn.close()
            
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"完成TTS和启动VAD失败: {e}")


# ================================================================
# 🎯 智能对话结束检测系统
# ================================================================

def _should_stop_listening_after_response(conn, current_text: str = None) -> bool:
    """检测是否应该在响应后停止聆听"""
    try:
        # 获取配置
        smart_ending_enabled = True  # 默认启用
        if hasattr(conn, 'config') and conn.config:
            smart_ending_enabled = conn.config.get("smart_conversation_ending", True)
            
            # 🚨 临时修复：禁用智能检测避免影响TTS播放
            if smart_ending_enabled:
                smart_ending_enabled = False
                conn.logger.bind(tag=TAG).info("🔧 临时修复：禁用智能对话结束检测，避免影响TTS播放")
        
        if not smart_ending_enabled:
            return False
        
        # 获取用户最后的输入和系统回复
        user_input = getattr(conn, 'last_user_input', '')
        # 🎯 优先使用当前文本，避免使用可能已清空的tts_MessageText
        system_response = current_text or getattr(conn, 'tts_MessageText', '') or getattr(conn, 'last_system_response', '')
        
        conn.logger.bind(tag=TAG).info(f"🔍 用户输入: '{user_input}'")
        conn.logger.bind(tag=TAG).info(f"🔍 当前TTS文本: '{current_text}'")
        conn.logger.bind(tag=TAG).info(f"🔍 连接TTS文本: '{getattr(conn, 'tts_MessageText', 'None')}'")
        conn.logger.bind(tag=TAG).info(f"🔍 最后回复: '{getattr(conn, 'last_system_response', 'None')}'")
        conn.logger.bind(tag=TAG).info(f"🔍 最终系统回复: '{system_response}'")
        
        # 检测用户的结束性话语
        user_ending_result = _is_ending_user_input(user_input)
        conn.logger.bind(tag=TAG).debug(f"🔍 用户结束性检测: '{user_input}' → {user_ending_result}")
        if user_ending_result:
            conn.logger.bind(tag=TAG).info(f"📝 用户结束性话语: '{user_input[:20]}...'")
            return True
        
        # 🔍 最高优先级：如果是询问语句，绝不停止聆听
        question_result = _is_question_response(system_response)
        conn.logger.bind(tag=TAG).debug(f"🔍 询问语句检测: '{system_response[:30]}...' → {question_result}")
        if question_result:
            conn.logger.bind(tag=TAG).info(f"❓ 系统询问语句，继续聆听: '{system_response[:30]}...'")
            return False
        
        # 检测系统的结束性回复
        system_ending_result = _is_ending_system_response(system_response)
        conn.logger.bind(tag=TAG).debug(f"🔍 系统结束性检测: '{system_response[:30]}...' → {system_ending_result}")
        if system_ending_result:
            conn.logger.bind(tag=TAG).info(f"🤖 系统结束性回复: '{system_response[:20]}...'")
            return True
        
        # 检测任务确认类回复
        if _is_task_confirmation_response(system_response):
            conn.logger.bind(tag=TAG).info(f"✅ 任务确认回复: '{system_response[:20]}...'")
            return True
            
        return False
        
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"检测对话结束失败: {e}")
        return False


def _is_ending_user_input(text: str) -> bool:
    """检测用户输入是否为结束性话语"""
    if not text or len(text.strip()) == 0:
        return False
    
    text = text.strip().lower()
    
    # 结束性用户话语模式
    ending_patterns = [
        # 感谢类
        r'^(谢谢|感谢|多谢|thank|thanks)(?:你|您)?[！。!.]*$',
        # 确认类  
        r'^(好的|好|行|可以|没问题|ok|okay)(?:了|的|啦)?[！。!.]*$',
        # 组合确认感谢类 - 🎯 新增：支持"好的谢谢"等组合
        r'^(好的|好|行|可以)[\s,，]*(?:谢谢|感谢|多谢)(?:你|您)?[！。!.]*$',
        r'^(谢谢|感谢|多谢)[\s,，]*(?:好的|好|行|可以)(?:了|的|啦)?[！。!.]*$',
        # 告别类
        r'^(再见|拜拜|bye|goodbye|晚安|回头见)(?:了|啦)?[！。!.]*$',
        # 短确认
        r'^(嗯|哦|嗯嗯|哦哦|嗯哦|好吧)(?:了|的|啦)?[！。!.]*$',
        # 知道了类
        r'^(知道了|明白了|懂了|了解了|收到了)(?:啦)?[！。!.]*$',
        # 没事了类 - 🎯 扩展拒绝/不需要模式
        r'^(没事了|算了|不用了|不要了|取消)(?:吧|啦)?[！。!.]*$',
        r'^(不需要|不用|不要|没有)(?:不需要|不用|不要|了|啦)?[！。!.]*$',  # "不需要"、"不需要不需要"
        r'^不+[！。!.]*$',  # 连续的"不"
    ]
    
    import re
    for pattern in ending_patterns:
        if re.search(pattern, text):
            return True
    
    return False


def _is_ending_system_response(text: str) -> bool:
    """检测系统回复是否为结束性话语"""
    if not text or len(text.strip()) == 0:
        return False
    
    text = text.strip()
    
    # 系统结束性回复模式
    ending_patterns = [
        # 告别类 - 🎯 扩展告别模式
        r'(再见|拜拜|晚安|回头聊|有需要再叫我|明天见|下次见|回头见|待会见)',
        r'(咱们.*?见|时间.*?快|该.*?再见)',  # "咱们明天见"、"时间过得真快"
        # 服务完成类
        r'(帮您设置好了|已经为您|操作完成|设置完成|任务完成)',
        # 结束性服务提供 - 🎯 添加"有需要随时"等模式
        r'(有需要.*?随时|随时.*?告诉我|随时.*?联系|有什么.*?随时|若.*?有需要)',
        # 无需回复类
        r'(不用回复|不用谢|别客气|应该的)',
        # 祝福类 - 🎯 精确化模式，避免误匹配
        r'(祝您|希望您|愿您|好好休息|注意身体)',  # 明确的祝福语
        r'(记得.*?防暑.*?[！。!.~哦]|记得.*?多喝水.*?[！。!.~哦]).*?$',  # 祝福性的提醒
    ]
    
    import re
    for i, pattern in enumerate(ending_patterns):
        match = re.search(pattern, text)
        if match:
            # 获取logger用于调试
            try:
                from config.logger import setup_logging
                logger = setup_logging()
                logger.bind(tag=TAG).info(f"✅ 系统结束性匹配: 模式{i+1} '{pattern}' 匹配内容: '{match.group()}'")
            except:
                pass
            return True
    
    return False


def _is_question_response(text: str) -> bool:
    """检测系统询问类回复（需要继续聆听）"""
    if not text or len(text.strip()) == 0:
        return False
    
    text = text.strip()
    
    # 询问语句特征 - 🎯 扩展询问检测
    question_patterns = [
        r'[？?]',  # 包含问号
        r'(您想|你想|您希望|你希望|您觉得|你觉得)',  # 询问意见
        r'(怎么样|如何|什么时候|哪种|选择)',  # 询问选择
        r'(还是|或者).*?呀',  # 选择性问句："用闹铃还是唱歌叫您呀？"
        r'(您说|你说|您看|你看).*?[？?呀]',  # 征求意见
        r'(想聊.*?啥|聊点.*?啥|说点.*?啥|讲点.*?啥)',  # "想聊点啥"类询问
        r'(您.*?会.*?想.*?[？?呀]|你.*?会.*?想.*?[？?呀])',  # "您这会儿想"类询问
    ]
    
    import re
    for i, pattern in enumerate(question_patterns):
        match = re.search(pattern, text)
        if match:
            # 获取logger用于调试
            try:
                from config.logger import setup_logging
                logger = setup_logging()
                logger.bind(tag=TAG).info(f"✅ 询问语句匹配: 模式{i+1} '{pattern}' 匹配内容: '{match.group()}'")
            except:
                pass
            return True
    
    return False


def _is_task_confirmation_response(text: str) -> bool:
    """检测任务确认类回复（比如定时提醒确认）"""
    # 获取logger（从TAG创建）
    from config.logger import setup_logging
    logger = setup_logging()
    
    if not text or len(text.strip()) == 0:
        logger.bind(tag=TAG).debug(f"🔍 任务确认检测: 文本为空")
        return False
    
    text = text.strip()
    logger.bind(tag=TAG).info(f"🔍 任务确认检测文本: '{text}'")
    
    # 任务确认回复模式
    confirmation_patterns = [
        # 提醒确认 - 明确的确认语句
        r'(已记住|已设置|会提醒|会通知|记住了).*?(提醒|通知|叫您|告诉您)',
        # 保存确认 - 明确的保存成功语句
        r'(好的，已记住|已经保存|已经记录|设置成功|安排好了)',
        # 时间确认 - 但排除询问语句
        r'(?!.*[？?]).*?(已安排|已设定|到时候|定时).*?(提醒|叫您|通知您)',
    ]
    
    import re
    for i, pattern in enumerate(confirmation_patterns):
        match = re.search(pattern, text)
        logger.bind(tag=TAG).debug(f"🔍 模式{i+1} '{pattern}' 匹配结果: {bool(match)}")
        if match:
            logger.bind(tag=TAG).info(f"✅ 任务确认匹配成功: 模式{i+1}")
            return True
    
    logger.bind(tag=TAG).debug(f"❌ 任务确认检测: 无匹配")
    return False


async def _send_stop_listening_message(conn):
    """发送停止聆听信号给硬件"""
    try:
        message = {
            "type": "listening",
            "state": "stop", 
            "reason": "conversation_ended",
            "session_id": conn.session_id,
            "timestamp": int(time.time() * 1000)
        }
        
        await conn.websocket.send(json.dumps(message))
        conn.logger.bind(tag=TAG).info(f"📤 发送停止聆听信号给硬件")
        
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"发送停止聆听信号失败: {e}")

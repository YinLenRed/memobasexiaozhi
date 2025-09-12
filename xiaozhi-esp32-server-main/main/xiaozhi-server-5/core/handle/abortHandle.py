import json

TAG = __name__


async def handleAbortMessage(conn):
    conn.logger.bind(tag=TAG).info("Abort message received")
    # 设置成打断状态，会自动打断llm、tts任务
    conn.client_abort = True
    
    # 🚫 强制中断所有音频发送任务（立即生效）
    if hasattr(conn, '_audio_send_tasks'):
        for task in conn._audio_send_tasks:
            if not task.done():
                task.cancel()
                conn.logger.bind(tag=TAG).info("🚫 强制取消音频发送任务")
        conn._audio_send_tasks.clear()
    
    # 🚫 关键修复：强制取消所有TTS完成任务（防止后续发送idle状态）
    if hasattr(conn, '_tts_completion_tasks'):
        for task in conn._tts_completion_tasks:
            if not task.done():
                task.cancel()
                conn.logger.bind(tag=TAG).info(f"🚫 强制取消TTS完成任务: {id(task)}")
        conn._tts_completion_tasks.clear()
        conn.logger.bind(tag=TAG).info("🚫 所有TTS完成任务已取消，防止发送idle状态")
    
    conn.clear_queues()
    
    # 🔄 关键修复：强制重置LLM完成标志，防止处理旧的响应
    conn.llm_finish_task = False
    if hasattr(conn, 'current_tts_text'):
        conn.current_tts_text = ""
    
    # 🔧 清除TTS播放标志
    conn.tts_actually_started = False
    # 🔧 清除TTS消息标志
    if hasattr(conn, 'tts_message_started'):
        conn.tts_message_started = False
    
    # 🔧 关键修复：强制重置TTS状态，确保后续音频正常
    if hasattr(conn, 'tts') and conn.tts:
        try:
            # 强制关闭当前TTS会话
            await _force_reset_tts_state(conn)
            conn.logger.bind(tag=TAG).info("🔄 强制重置TTS状态完成")
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"重置TTS状态失败: {e}")
    
    # 🛠️ 关键修复：检查是否为按钮打断，设置标志避免发送idle状态
    if hasattr(conn, 'client_have_voice') and conn.client_have_voice:
        conn.logger.bind(tag=TAG).info("🔘 按钮打断TTS，设置标志避免发送idle状态")
        # 不清除client_have_voice，让TTS stop知道这是按钮打断
    
    # 打断客户端说话状态
    await conn.websocket.send(
        json.dumps({"type": "tts", "state": "stop", "session_id": conn.session_id})
    )
    
    # 🛠️ 关键修复：重置所有可能影响后续语音的状态标志
    conn.client_is_speaking = False
    if hasattr(conn, 'waiting_for_speak_done'):
        conn.waiting_for_speak_done = False
    if hasattr(conn, 'speak_done_track_id'):
        conn.speak_done_track_id = None
    
    conn.clearSpeakStatus()
    conn.logger.bind(tag=TAG).info("🔄 Abort完成，重置所有说话相关状态")
    conn.logger.bind(tag=TAG).info("Abort message received-end")


async def _force_reset_tts_state(conn):
    """强制重置TTS状态，确保后续音频流正常"""
    try:
        # 1. 🔧 强制关闭当前TTS会话（如果存在）
        if hasattr(conn.tts, 'cancel_session'):
            try:
                if hasattr(conn, 'sentence_id') and conn.sentence_id:
                    await conn.tts.cancel_session(conn.sentence_id)
                    conn.logger.bind(tag=TAG).debug(f"取消TTS会话: {conn.sentence_id}")
            except Exception as e:
                conn.logger.bind(tag=TAG).debug(f"取消TTS会话异常（忽略）: {e}")
        
        # 🚫 关键修复：立即取消TTS监听任务（防止继续生成音频）
        if hasattr(conn.tts, '_monitor_task') and conn.tts._monitor_task:
            try:
                if not conn.tts._monitor_task.done():
                    conn.tts._monitor_task.cancel()
                    conn.logger.bind(tag=TAG).info("🚫 强制取消TTS监听任务，停止音频生成")
            except Exception as e:
                conn.logger.bind(tag=TAG).debug(f"取消TTS监听任务异常（忽略）: {e}")
        
        # 🚫 强制关闭TTS WebSocket连接（立即生效）
        if hasattr(conn.tts, 'ws') and conn.tts.ws:
            try:
                await conn.tts.ws.close()
                conn.tts.ws = None
                conn.logger.bind(tag=TAG).info("🚫 强制关闭TTS WebSocket连接")
            except Exception as e:
                conn.logger.bind(tag=TAG).debug(f"关闭TTS连接异常（忽略）: {e}")
        
        # 2. 🔧 重置TTS相关标志位
        if hasattr(conn.tts, 'waiting_for_first_audio'):
            conn.tts.waiting_for_first_audio = False
        if hasattr(conn.tts, 'first_sentence_text'):
            conn.tts.first_sentence_text = ""
        
        # 3. 🔧 清空所有TTS队列（关键修复）
        if hasattr(conn.tts, 'audio_play_queue'):
            try:
                while not conn.tts.audio_play_queue.empty():
                    conn.tts.audio_play_queue.get_nowait()
                conn.logger.bind(tag=TAG).debug("清空TTS音频播放队列")
            except:
                pass
        
        # 🚫 清空TTS文本队列（防止继续处理旧请求）
        if hasattr(conn.tts, 'tts_text_queue'):
            try:
                while not conn.tts.tts_text_queue.empty():
                    conn.tts.tts_text_queue.get_nowait()
                conn.logger.bind(tag=TAG).info("🚫 清空TTS文本队列，防止处理旧内容")
            except:
                pass
        
        # 🚫 清空TTS音频队列（防止播放旧音频）
        if hasattr(conn.tts, 'tts_audio_queue'):
            try:
                while not conn.tts.tts_audio_queue.empty():
                    conn.tts.tts_audio_queue.get_nowait()
                conn.logger.bind(tag=TAG).info("🚫 清空TTS音频队列，防止播放旧音频")
            except:
                pass
        
        # 🚫 强制清空所有TTS相关缓存（关键修复）
        if hasattr(conn.tts, 'audio_cache_buffer'):
            try:
                conn.tts.audio_cache_buffer.clear()
                conn.logger.bind(tag=TAG).debug("清空TTS音频缓存")
            except:
                pass
        
        # 4. 🔧 重新生成会话ID，确保新会话独立
        import uuid
        conn.sentence_id = uuid.uuid4().hex
        conn.logger.bind(tag=TAG).debug(f"生成新的TTS会话ID: {conn.sentence_id}")
        
        # 5. 🔧 强制重置WebSocket连接状态（如果是流式TTS）
        if hasattr(conn.tts, 'ws') and conn.tts.ws:
            try:
                # 对于双流TTS，强制关闭连接以确保干净状态
                if hasattr(conn.tts, '_ensure_connection'):
                    await conn.tts.ws.close()
                    conn.tts.ws = None
                    conn.logger.bind(tag=TAG).info("🔥 强制关闭TTS WebSocket连接，清除所有音频缓存")
            except Exception as e:
                conn.logger.bind(tag=TAG).debug(f"关闭TTS WebSocket异常（忽略）: {e}")
        
        # 6. 🚫 强制清空TTS监听任务（关键修复）
        if hasattr(conn.tts, '_monitor_task') and conn.tts._monitor_task:
            try:
                conn.tts._monitor_task.cancel()
                conn.logger.bind(tag=TAG).info("🛑 强制取消TTS监听任务")
            except Exception as e:
                conn.logger.bind(tag=TAG).debug(f"取消TTS监听任务异常（忽略）: {e}")
        
        conn.logger.bind(tag=TAG).info("🛠️ TTS状态强制重置完成，确保后续音频正常")
        
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"强制重置TTS状态异常: {e}")
        # 即使重置失败，也要确保基本状态正确
        import uuid
        conn.sentence_id = uuid.uuid4().hex

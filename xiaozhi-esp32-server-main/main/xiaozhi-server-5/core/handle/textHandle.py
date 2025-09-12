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
        
        # 🔍 如果启用了消息监控，记录收到的消息
        if hasattr(conn, 'monitor_websocket_messages') and conn.monitor_websocket_messages:
            conn.logger.bind(tag=TAG).info(f"🔍 [监控] 收到硬件消息: {message}")
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
                
                # 🔍 详细状态日志 - 帮助诊断问题
                conn.logger.bind(tag=TAG).info(f"🔍 [状态诊断] 收到listen start，当前状态:")
                conn.logger.bind(tag=TAG).info(f"🔍 [状态诊断] client_is_speaking: {getattr(conn, 'client_is_speaking', None)}")
                conn.logger.bind(tag=TAG).info(f"🔍 [状态诊断] tts_message_started: {getattr(conn, 'tts_message_started', None)}")
                conn.logger.bind(tag=TAG).info(f"🔍 [状态诊断] tts_actually_started: {getattr(conn, 'tts_actually_started', None)}")
                conn.logger.bind(tag=TAG).info(f"🔍 [状态诊断] client_abort: {getattr(conn, 'client_abort', None)}")
                conn.logger.bind(tag=TAG).info(f"🔍 [状态诊断] button_is_pressed: {getattr(conn, 'button_is_pressed', None)}")
                conn.logger.bind(tag=TAG).info(f"🔍 [状态诊断] current_tts_text: '{getattr(conn, 'current_tts_text', '')}'")
                conn.logger.bind(tag=TAG).info(f"🔍 [状态诊断] tts_MessageText: '{getattr(conn, 'tts_MessageText', '')}'")
                conn.logger.bind(tag=TAG).info(f"🔍 [状态诊断] last_system_response: '{getattr(conn, 'last_system_response', '')}'")
                
                # 🚨 关键诊断：检查是否是第二次按钮
                button_press_count = getattr(conn, 'button_press_count', 0) + 1
                conn.button_press_count = button_press_count
                conn.logger.bind(tag=TAG).info(f"🔍 [关键诊断] 这是第 {button_press_count} 次按钮 - 会话ID: {conn.session_id}")
                
                # 🎯 智能按钮逻辑：区分打断和聆听
                # 🔧 更精确的状态判断：只有在真正播放TTS时才算speaking
                is_actually_speaking = (conn.client_is_speaking and 
                                       hasattr(conn, 'tts_actually_started') and 
                                       conn.tts_actually_started)
                
                # 🔧 检测是否处于处理状态（TTS消息已开始但音频还未真正播放）
                is_processing = (conn.client_is_speaking and 
                               hasattr(conn, 'tts_message_started') and conn.tts_message_started and
                               not (hasattr(conn, 'tts_actually_started') and conn.tts_actually_started))
                
                conn.logger.bind(tag=TAG).info(f"🔍 [状态诊断] is_actually_speaking: {is_actually_speaking}")
                conn.logger.bind(tag=TAG).info(f"🔍 [状态诊断] is_processing: {is_processing}")
                
                if is_actually_speaking:
                    # 📱 场景1：TTS播放期间按下 → 打断当前播放
                    conn.logger.bind(tag=TAG).info(f"🔴 TTS播放期间按下按钮 → 打断当前TTS播放")
                    
                    # 🚀 快速打断优化：先同步会话ID，再发送聆听状态
                    hardware_session_id = msg_json.get("session_id")
                    if hardware_session_id:
                        conn.session_id = hardware_session_id
                        conn.logger.bind(tag=TAG).info(f"🚀 快速打断：立即同步会话ID到 {conn.session_id}")
                    
                    quick_listen_message = {
                        "type": "listen",
                        "state": "start", 
                        "mode": "manual",
                        "session_id": conn.session_id,
                        "timestamp": int(time.time() * 1000),
                        "priority": "high"  # 高优先级消息
                    }
                    await conn.websocket.send(json.dumps(quick_listen_message))
                    conn.logger.bind(tag=TAG).info(f"🚀 快速打断：立即发送聆听状态 - {json.dumps(quick_listen_message)}")
                    
                    await handleAbortMessage(conn)
                    # 减少延迟，提升响应速度
                    await asyncio.sleep(0.05)
                    
                    # 🚫 保持abort状态，等待新对话开始时重置
                    # conn.client_abort = False  # 不在这里重置，等startToChat时重置
                    conn.logger.bind(tag=TAG).info(f"🚫 保持abort状态，等待新对话开始时重置")
                elif is_processing:
                    # 📱 场景1.5：处理状态期间按下 → 打断LLM处理，直接进入聆听
                    conn.logger.bind(tag=TAG).info(f"🟡 处理状态期间按下按钮 → 打断LLM处理，直接进入聆听")
                    
                    # 🚀 快速打断优化：先同步会话ID，再发送聆听状态
                    hardware_session_id = msg_json.get("session_id")
                    if hardware_session_id:
                        conn.session_id = hardware_session_id
                        conn.logger.bind(tag=TAG).info(f"🚀 处理状态快速打断：立即同步会话ID到 {conn.session_id}")
                    
                    quick_listen_message = {
                        "type": "listen",
                        "state": "start", 
                        "mode": "manual",
                        "session_id": conn.session_id,
                        "timestamp": int(time.time() * 1000),
                        "priority": "high"  # 高优先级消息
                    }
                    await conn.websocket.send(json.dumps(quick_listen_message))
                    conn.logger.bind(tag=TAG).info(f"🚀 处理状态快速打断：立即发送聆听状态 - {json.dumps(quick_listen_message)}")
                    
                    # 🔧 处理状态打断：直接清理，不调用abort（避免设置client_abort=True）
                    # await handleAbortMessage(conn)  # 不调用abort，避免阻止新对话
                    # 直接清理TTS和队列
                    conn.clear_queues()
                    conn.llm_finish_task = False
                    if hasattr(conn, 'current_tts_text'):
                        conn.current_tts_text = ""
                    if hasattr(conn, 'tts_actually_started'):
                        conn.tts_actually_started = False
                    if hasattr(conn, 'tts_message_started'):
                        conn.tts_message_started = False
                    conn.logger.bind(tag=TAG).info(f"🧹 处理状态打断：直接清理状态，不设置abort标志")
                    
                    # 🔄 处理状态打断：不设置abort，让新对话正常开始
                    conn.client_abort = False  # 确保新对话可以正常开始
                    conn.logger.bind(tag=TAG).info(f"🔄 处理状态打断：重置abort状态，允许新对话开始")
                    
                    # 🚀 快速打断：强制同步到硬件的会话ID
                    hardware_session_id = msg_json.get("session_id")
                    old_session_id = conn.session_id

                    if hardware_session_id:
                        conn.session_id = hardware_session_id
                        conn.logger.bind(tag=TAG).info(f"🚀 处理状态快速打断：强制同步到硬件会话ID: {old_session_id} → {conn.session_id}")
                    else:
                        # 备用方案：生成新ID
                        import uuid
                        conn.session_id = str(uuid.uuid4())
                        conn.logger.bind(tag=TAG).info(f"🆔 处理状态备用方案：生成新会话ID: {old_session_id} → {conn.session_id}")
                    
                    # 重新初始化对话状态，但保留当前用户输入
                    try:
                        from core.utils.dialogue import Dialogue, Message
                        
                        # 获取当前的用户输入（从ASR识别的文本）
                        current_user_input = None
                        if hasattr(conn, 'last_user_input'):
                            current_user_input = conn.last_user_input
                            
                        conn.dialogue = Dialogue()
                        
                        # 如果有当前用户输入，重新添加到dialogue中
                        if current_user_input:
                            conn.dialogue.put(Message(role="user", content=current_user_input))
                            conn.logger.bind(tag=TAG).info(f"🔄 处理状态打断：重新初始化dialogue并保留用户输入: '{current_user_input}'")
                        else:
                            conn.logger.bind(tag=TAG).info(f"🔄 处理状态打断：重新初始化dialogue对象（无用户输入）")
                    except Exception as e:
                        conn.logger.bind(tag=TAG).error(f"重新初始化dialogue失败: {e}")
                    
                    # 清除TTS显示内容
                    if hasattr(conn, 'current_tts_text'):
                        conn.current_tts_text = ""
                    if hasattr(conn, 'tts_MessageText'):
                        conn.tts_MessageText = ""
                    if hasattr(conn, 'last_system_response'):
                        conn.last_system_response = ""
                    conn.logger.bind(tag=TAG).info(f"🧹 处理状态打断：清除所有TTS显示内容，确保不显示旧对话")
                    
                    # 📱 发送确认聆听状态的消息
                    listen_start_message = {
                        "type": "listen",
                        "state": "start",
                        "mode": "manual", 
                        "session_id": conn.session_id,
                        "timestamp": int(time.time() * 1000)
                    }
                    await conn.websocket.send(json.dumps(listen_start_message))
                    conn.logger.bind(tag=TAG).info(f"📱 处理状态打断：发送listen start消息进入聆听状态 - WebSocket发送: {json.dumps(listen_start_message)}")
                    
                    # 🚀 快速打断优化：减少重复发送次数，提升响应速度
                    for i in range(2):  # 从3次减少到2次
                        await asyncio.sleep(0.01)  # 从20ms减少到10ms
                        await conn.websocket.send(json.dumps(listen_start_message))
                        conn.logger.bind(tag=TAG).info(f"📱 处理状态打断：快速同步会话ID第{i+2}次: {conn.session_id}")
                    
                    # 🔍 发送最终确认消息，确保硬件状态
                    final_confirm_message = {
                        "type": "listen",
                        "state": "start",
                        "mode": "manual",
                        "session_id": conn.session_id,
                        "timestamp": int(time.time() * 1000),
                        "force": True,  # 强制状态
                        "priority": "critical"  # 关键优先级
                    }
                    await conn.websocket.send(json.dumps(final_confirm_message))
                    conn.logger.bind(tag=TAG).info(f"🔍 处理状态打断：发送最终确认listen消息确保硬件聆听状态: {json.dumps(final_confirm_message)}")
                    
                    # 🔧 设置按钮状态
                    conn.client_have_voice = True
                    conn.client_voice_stop = False
                    conn.button_is_pressed = True
                    conn.button_press_time = time.time()
                    conn.logger.bind(tag=TAG).info(f"🔧 处理状态打断：设置按钮聆听状态")
                    
                    # 🚀 快速打断场景：强制使用硬件的会话ID，确保一致性
                    if hardware_session_id:
                        conn.session_id = hardware_session_id
                        conn.logger.bind(tag=TAG).info(f"🚀 快速打断：强制同步到硬件会话ID: {old_session_id} → {conn.session_id}")
                    else:
                        # 备用方案：生成新ID
                        import uuid
                        conn.session_id = str(uuid.uuid4())
                        conn.logger.bind(tag=TAG).info(f"🆔 备用方案：生成新会话ID: {old_session_id} → {conn.session_id}")
                    
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
                                # 🔧 重新初始化dialogue对象而不是设置为None，并保留当前用户输入
                                from core.utils.dialogue import Dialogue, Message
                                
                                # 获取当前的用户输入
                                current_user_input = getattr(conn, 'last_user_input', None)
                                conn.dialogue = Dialogue()
                                
                                # 如果有当前用户输入，重新添加到dialogue中
                                if current_user_input:
                                    conn.dialogue.put(Message(role="user", content=current_user_input))
                                    conn.logger.bind(tag=TAG).info(f"🔄 重新初始化dialogue并保留用户输入: '{current_user_input}'")
                                else:
                                    conn.logger.bind(tag=TAG).info(f"🔄 重新初始化dialogue对象（无用户输入）")
                        except Exception as e:
                            conn.logger.bind(tag=TAG).warning(f"清除对话历史时出错: {e}")
                            # 🔧 出错时重新初始化dialogue
                            try:
                                from core.utils.dialogue import Dialogue, Message
                                
                                # 获取当前的用户输入
                                current_user_input = getattr(conn, 'last_user_input', None)
                                conn.dialogue = Dialogue()
                                
                                # 如果有当前用户输入，重新添加到dialogue中
                                if current_user_input:
                                    conn.dialogue.put(Message(role="user", content=current_user_input))
                                    conn.logger.bind(tag=TAG).info(f"🔄 出错后重新初始化dialogue并保留用户输入: '{current_user_input}'")
                                else:
                                    conn.logger.bind(tag=TAG).info(f"🔄 出错后重新初始化dialogue对象（无用户输入）")
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
                    
                    # 🚀 快速打断优化：减少重复发送次数，提升响应速度
                    for i in range(2):  # 从3次减少到2次
                        await asyncio.sleep(0.01)  # 从20ms减少到10ms
                        await conn.websocket.send(json.dumps(listen_start_message))
                        conn.logger.bind(tag=TAG).info(f"📱 快速同步会话ID第{i+2}次: {conn.session_id}")
                    
                    # 🔍 减少等待时间，提升响应速度
                    await asyncio.sleep(0.05)  # 从100ms减少到50ms
                    conn.logger.bind(tag=TAG).info(f"🔍 快速会话ID同步完成，等待硬件响应")
                    
                    # 🔍 发送最终确认消息，确保硬件状态 - 统一使用listen类型
                    final_confirm_message = {
                        "type": "listen",
                        "state": "start",
                        "mode": "manual",
                        "session_id": conn.session_id,
                        "timestamp": int(time.time() * 1000),
                        "force": True,  # 强制状态
                        "priority": "critical"  # 关键优先级
                    }
                    await conn.websocket.send(json.dumps(final_confirm_message))
                    conn.logger.bind(tag=TAG).info(f"🔍 发送最终确认listen消息确保硬件聆听状态: {json.dumps(final_confirm_message)}")
                    
                    # 🔍 启动消息监控，追踪后续可能的状态消息
                    conn.monitor_websocket_messages = True
                    conn.logger.bind(tag=TAG).info(f"🔍 启动WebSocket消息监控，追踪可能影响硬件状态的消息")
                    
                    # 🔍 拦截WebSocket发送函数，监控所有发送给硬件的消息
                    if not hasattr(conn, '_original_websocket_send'):
                        conn._original_websocket_send = conn.websocket.send
                        
                        async def monitored_send(data):
                            # 记录发送的消息
                            if isinstance(data, str):
                                try:
                                    msg_data = json.loads(data)
                                    if msg_data.get('type') in ['status', 'listen', 'tts']:
                                        conn.logger.bind(tag=TAG).info(f"🔍 [监控] 发送给硬件: {data}")
                                except:
                                    conn.logger.bind(tag=TAG).info(f"🔍 [监控] 发送给硬件(非JSON): {data[:100]}...")
                            
                            # 调用原始发送函数
                            return await conn._original_websocket_send(data)
                        
                        # 替换发送函数
                        conn.websocket.send = monitored_send
                        conn.logger.bind(tag=TAG).info(f"🔍 WebSocket发送拦截器已启动")
                    
                    # 🔍 启动状态监控任务，持续追踪硬件状态变化
                    async def monitor_hardware_state():
                        """监控硬件状态变化，帮助诊断问题"""
                        start_time = time.time()
                        conn.logger.bind(tag=TAG).info(f"🔍 开始监控硬件状态变化 (会话ID: {conn.session_id})")
                        
                        # 监控10秒钟
                        while time.time() - start_time < 10:
                            await asyncio.sleep(0.5)
                            
                            # 检查连接状态
                            if not hasattr(conn, 'websocket') or not conn.websocket:
                                conn.logger.bind(tag=TAG).info(f"🔍 WebSocket连接已关闭，停止监控")
                                break
                                
                            # 记录当前状态
                            current_state = {
                                "client_abort": getattr(conn, 'client_abort', None),
                                "client_is_speaking": getattr(conn, 'client_is_speaking', None),
                                "tts_actually_started": getattr(conn, 'tts_actually_started', None),
                                "button_is_pressed": getattr(conn, 'button_is_pressed', None),
                                "session_id": getattr(conn, 'session_id', None)
                            }
                            conn.logger.bind(tag=TAG).debug(f"🔍 当前状态快照: {current_state}")
                        
                        conn.logger.bind(tag=TAG).info(f"🔍 硬件状态监控结束")
                    
                    # 启动监控任务（不等待）
                    asyncio.create_task(monitor_hardware_state())
                    
                    # 🔍 启动TTS播放打断专用监控
                    async def monitor_tts_interrupt_state():
                        """监控TTS播放打断后的状态变化，专门诊断第二次按钮问题"""
                        start_time = time.time()
                        conn.logger.bind(tag=TAG).info(f"🔍 [TTS打断监控] 开始监控TTS播放打断后的状态变化")
                        
                        for i in range(20):  # 监控10秒钟
                            await asyncio.sleep(0.5)
                            
                            # 检查连接状态
                            if not hasattr(conn, 'websocket') or not conn.websocket:
                                conn.logger.bind(tag=TAG).info(f"🔍 [TTS打断监控] WebSocket连接已关闭")
                                break
                                
                            # 记录关键状态 - 专注于按钮和聆听状态
                            current_state = {
                                "client_abort": getattr(conn, 'client_abort', None),
                                "client_is_speaking": getattr(conn, 'client_is_speaking', None),
                                "tts_actually_started": getattr(conn, 'tts_actually_started', None),
                                "button_is_pressed": getattr(conn, 'button_is_pressed', None),
                                "client_have_voice": getattr(conn, 'client_have_voice', None),
                                "client_voice_stop": getattr(conn, 'client_voice_stop', None),
                                "session_id": getattr(conn, 'session_id', None)
                            }
                            conn.logger.bind(tag=TAG).info(f"🔍 [TTS打断监控][{i+1}]: {current_state}")
                        
                        conn.logger.bind(tag=TAG).info(f"🔍 [TTS打断监控] 监控结束")
                    
                    # 启动TTS打断专用监控任务（不等待）
                    asyncio.create_task(monitor_tts_interrupt_state())
                    
                else:
                    # 📱 场景2：空闲期间按下 → 直接进入聆听状态
                    conn.logger.bind(tag=TAG).info(f"🎤 空闲期间按下按钮 → 直接进入聆听状态")
                    
                    # 🔧 同步硬件会话ID，确保一致性
                    hardware_session_id = msg_json.get("session_id")
                    old_session_id = conn.session_id
                    
                    if hardware_session_id:
                        # 🎯 强制使用硬件会话ID，确保一致性
                        conn.session_id = hardware_session_id
                        conn.logger.bind(tag=TAG).info(f"🎯 强制同步到硬件会话ID: {old_session_id} → {conn.session_id}")
                    else:
                        # 🆔 备用方案：生成新ID并同步给硬件
                        import uuid
                        conn.session_id = str(uuid.uuid4())
                        conn.logger.bind(tag=TAG).info(f"🆔 生成新会话ID并同步给硬件: {conn.session_id}")
                        
                        # 发送会话同步消息给硬件
                        sync_message = {
                            "type": "status",
                            "state": "session_sync",
                            "session_id": conn.session_id,
                            "timestamp": int(time.time() * 1000)
                        }
                        await conn.websocket.send(json.dumps(sync_message))
                        conn.logger.bind(tag=TAG).info(f"📤 发送会话同步消息给硬件")
                    
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
                        # 🔧 关键修复：检查是否处于abort状态，如果是则跳过处理
                        if hasattr(conn, 'client_abort') and conn.client_abort:
                            conn.logger.bind(tag=TAG).info(f"🚫 检测到abort状态，跳过文本处理: '{original_text}'")
                            return
                        
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

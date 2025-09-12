#!/usr/bin/env python3
"""
直接测试TTS功能的脚本
用于验证TTS组件是否能正常工作，绕过意图识别等复杂流程
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.providers.tts.huoshan_double_stream import TTSProvider
from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType
from config.logger import setup_logging
import queue
import threading
import time

logger = setup_logging()

class MockConnection:
    def __init__(self):
        self.stop_event = threading.Event()
        self.sentence_id = None
        self.client_abort = False
        self.loop = asyncio.new_event_loop()
        self.logger = logger
        
    def stop(self):
        self.stop_event.set()

async def test_tts_direct():
    """直接测试TTS功能"""
    print("🧪 开始直接测试TTS功能...")
    
    # 模拟TTS配置（需要根据实际配置调整）
    config = {
        "type": "huoshan_double_stream",
        "appid": "1864245147",
        "ws_url": "wss://openspeech.bytedance.com/api/v3/tts/bidirection",
        "speaker": "zh_female_linjianvhai_moon_bigtts",
        "resource_id": "volc.service_type.10029",
        "access_token": "your_access_token_here",  # 需要实际的token
        "private_voice": "ICL_zh_female_chengshujiejie_tob"
    }
    
    try:
        # 创建TTS提供器
        tts_provider = TTSProvider(config, delete_audio_file=True)
        
        # 创建模拟连接
        mock_conn = MockConnection()
        
        # 初始化TTS
        await tts_provider.open_audio_channels(mock_conn)
        
        print("✅ TTS提供器初始化成功")
        
        # 测试简单文本
        test_text = "你好，这是TTS测试"
        print(f"🎵 测试文本: {test_text}")
        
        # 发送FIRST消息
        tts_provider.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id="test_001",
                sentence_type=SentenceType.FIRST,
                content_type=ContentType.TEXT,
                content_detail=""
            )
        )
        
        # 发送文本消息
        tts_provider.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id="test_001",
                sentence_type=SentenceType.MIDDLE,
                content_type=ContentType.TEXT,
                content_detail=test_text
            )
        )
        
        # 发送LAST消息
        tts_provider.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id="test_001",
                sentence_type=SentenceType.LAST,
                content_type=ContentType.TEXT,
                content_detail=""
            )
        )
        
        print("📤 TTS消息已发送到队列")
        
        # 等待处理
        print("⏳ 等待TTS处理...")
        await asyncio.sleep(10)
        
        # 检查音频队列
        audio_queue_size = tts_provider.tts_audio_queue.qsize()
        print(f"🔍 音频队列大小: {audio_queue_size}")
        
        if audio_queue_size > 0:
            print("✅ 音频队列有数据，TTS功能正常")
            # 取出一个音频数据检查
            try:
                sentence_type, audio_data, text = tts_provider.tts_audio_queue.get_nowait()
                print(f"🎵 音频数据: type={sentence_type}, data_len={len(audio_data) if audio_data else 0}, text={text}")
            except queue.Empty:
                print("⚠️ 音频队列为空")
        else:
            print("❌ 音频队列为空，TTS功能异常")
        
    except Exception as e:
        print(f"❌ TTS测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理
        if 'mock_conn' in locals():
            mock_conn.stop()

if __name__ == "__main__":
    print("🚀 启动TTS直接测试...")
    asyncio.run(test_tts_direct())

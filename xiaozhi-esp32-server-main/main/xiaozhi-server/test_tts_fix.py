#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试TTS修复效果
"""

import asyncio
import sys
import os
sys.path.append('.')

from config.config_loader import load_config
from core.utils.modules_initialize import initialize_modules
from core.mqtt.webhook_callback_handler import WebhookCallbackHandler
from config.logger import setup_logging

async def test_tts_fix():
    """测试TTS修复效果"""
    logger = setup_logging()
    
    print("🧪 开始测试TTS修复效果...")
    
    # 加载配置
    config = load_config()
    
    # 初始化TTS模块
    modules = initialize_modules(
        logger,
        config,
        init_vad=False,
        init_asr=False,
        init_llm=False,
        init_tts=True,  # 只初始化TTS
        init_memory=False,
        init_intent=False,
    )
    
    tts_provider = modules.get("tts")
    if not tts_provider:
        print("❌ TTS提供器初始化失败")
        return
    
    print(f"✅ TTS提供器初始化成功: {type(tts_provider).__name__}")
    
    # 创建webhook处理器
    handler = WebhookCallbackHandler(config, None, tts_provider)
    
    # 测试TTS生成
    test_text = "这是TTS修复测试，应该能正常生成音频文件"
    track_id = "TEST_TTS_FIX"
    
    print(f"🎵 开始测试TTS生成: {test_text}")
    
    try:
        audio_file = await handler._generate_tts_audio(test_text, track_id)
        
        if audio_file and os.path.exists(audio_file):
            file_size = os.path.getsize(audio_file)
            print(f"✅ TTS生成成功！")
            print(f"   文件路径: {audio_file}")
            print(f"   文件大小: {file_size} bytes")
            
            # 清理测试文件
            os.remove(audio_file)
            print(f"🗑️ 清理测试文件: {audio_file}")
            
            return True
        else:
            print("❌ TTS生成失败：没有生成音频文件")
            return False
            
    except Exception as e:
        print(f"❌ TTS测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_tts_fix())
    if success:
        print("\n🎉 TTS修复测试成功！")
        sys.exit(0)
    else:
        print("\n💥 TTS修复测试失败！")
        sys.exit(1)

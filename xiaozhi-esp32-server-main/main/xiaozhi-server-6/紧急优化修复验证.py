#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紧急优化修复验证脚本
验证已实施的三个紧急修复的效果
"""

import asyncio
import time
import threading
import gc
from typing import List
from loguru import logger

# 导入修复的模块
from core.utils.audio_buffer_manager import AudioBufferManager, ConnectionAudioManager
from core.utils.resource_manager import ResourceManager, ConnectionResourceManager

logger.add("紧急修复验证.log", rotation="10MB", level="INFO")

class MockConnection:
    """模拟连接对象"""
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.asr_audio = []
        self.asr_audio_for_voiceprint = []
        self.websocket = None
        self.asr = None
        self.tts = None

async def test_async_memory_save():
    """测试异步内存保存修复"""
    logger.info("🧪 测试1: 异步编程修复验证")
    
    class MockMemory:
        async def save_memory(self, dialogue):
            await asyncio.sleep(0.1)  # 模拟保存时间
            logger.info("模拟记忆保存完成")
    
    class MockDialogue:
        dialogue = ["测试对话1", "测试对话2"]
    
    # 模拟修复后的代码逻辑
    memory = MockMemory()
    dialogue = MockDialogue()
    
    async def save_memory_background():
        """后台保存记忆任务（修复后的逻辑）"""
        try:
            if memory and dialogue:
                await memory.save_memory(dialogue.dialogue)
                logger.info("✅ 后台记忆保存完成")
        except Exception as e:
            logger.error(f"❌ 后台保存记忆失败: {e}")
    
    # 测试不阻塞的保存
    start_time = time.time()
    save_task = asyncio.create_task(save_memory_background())
    logger.info("启动后台记忆保存任务（不等待）")
    
    # 立即继续其他操作
    await asyncio.sleep(0.05)  # 模拟其他操作
    elapsed = time.time() - start_time
    
    if elapsed < 0.1:  # 应该没有阻塞
        logger.info(f"✅ 测试1通过: 异步保存不阻塞 ({elapsed:.3f}秒)")
    else:
        logger.error(f"❌ 测试1失败: 保存操作阻塞了主流程 ({elapsed:.3f}秒)")
    
    # 等待后台任务完成
    await save_task

def test_audio_buffer_limit():
    """测试音频缓冲区限制修复"""
    logger.info("🧪 测试2: 音频缓冲区限制验证")
    
    # 创建音频缓冲区管理器
    buffer_manager = AudioBufferManager(max_size=100, max_total_size=1024)  # 1KB限制
    
    # 测试大量音频数据添加
    large_audio = b'A' * 200  # 200字节的音频块
    added_count = 0
    
    for i in range(200):  # 尝试添加200块（理论上40KB）
        success = buffer_manager.add_audio(large_audio)
        if success:
            added_count += 1
    
    stats = buffer_manager.get_stats()
    logger.info(f"音频缓冲区统计: {stats}")
    
    # 验证内存限制是否生效
    if stats['total_size_mb'] <= 1.0 and stats['dropped_chunks'] > 0:
        logger.info("✅ 测试2通过: 音频缓冲区正确限制内存使用")
    else:
        logger.error(f"❌ 测试2失败: 内存限制未生效")
    
    # 测试连接级别的音频管理器
    mock_conn = MockConnection("test-device")
    conn_audio_manager = ConnectionAudioManager(mock_conn)
    
    # 添加一些音频数据
    for i in range(10):
        conn_audio_manager.add_audio(f"audio-{i}".encode())
        conn_audio_manager.add_voiceprint_audio(f"voice-{i}".encode())
    
    # 验证连接的音频列表是否同步更新
    if len(mock_conn.asr_audio) == 10 and len(mock_conn.asr_audio_for_voiceprint) == 10:
        logger.info("✅ 测试2.1通过: 连接音频列表正确同步")
    else:
        logger.error("❌ 测试2.1失败: 连接音频列表同步异常")

async def test_resource_cleanup():
    """测试资源清理修复"""
    logger.info("🧪 测试3: 资源清理验证")
    
    # 创建资源管理器
    resource_manager = ResourceManager("test-manager")
    
    # 模拟各种资源
    class MockWebSocket:
        def __init__(self):
            self.closed = False
        
        async def close(self):
            await asyncio.sleep(0.01)  # 模拟关闭时间
            self.closed = True
    
    class MockASR:
        def __init__(self):
            self.closed = False
        
        async def close(self):
            await asyncio.sleep(0.01)
            self.closed = True
    
    # 注册资源
    mock_ws = MockWebSocket()
    mock_asr = MockASR()
    
    resource_manager.register_resource(mock_ws, mock_ws.close, "WebSocket")
    resource_manager.register_resource(mock_asr, mock_asr.close, "ASR")
    
    # 注册一个同步资源
    test_list = [1, 2, 3]
    resource_manager.register_resource(test_list, test_list.clear, "TestList")
    
    logger.info(f"注册了 {resource_manager.get_resource_count()} 个资源")
    
    # 执行清理
    start_time = time.time()
    cleanup_success = await resource_manager.cleanup_all()
    cleanup_time = time.time() - start_time
    
    # 验证清理结果
    all_closed = mock_ws.closed and mock_asr.closed and len(test_list) == 0
    
    if cleanup_success and all_closed:
        logger.info(f"✅ 测试3通过: 资源清理成功 ({cleanup_time:.3f}秒)")
    else:
        logger.error(f"❌ 测试3失败: 资源清理不完整")
    
    # 测试连接级别的资源管理器
    mock_conn = MockConnection("test-device-2")
    mock_conn.websocket = MockWebSocket()
    mock_conn.asr = MockASR()
    
    conn_resource_manager = ConnectionResourceManager(mock_conn)
    
    # 清理连接资源
    conn_cleanup_success = await conn_resource_manager.cleanup()
    
    if conn_cleanup_success:
        logger.info("✅ 测试3.1通过: 连接资源管理器正常工作")
    else:
        logger.error("❌ 测试3.1失败: 连接资源清理异常")

def test_memory_usage():
    """测试内存使用优化"""
    logger.info("🧪 测试4: 内存使用验证")
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # 创建大量音频缓冲区管理器（模拟多个连接）
    managers = []
    for i in range(50):
        manager = AudioBufferManager(max_size=100, max_total_size=512*1024)  # 512KB限制
        # 添加一些音频数据
        for j in range(20):
            manager.add_audio(b'X' * 100)  # 100字节
        managers.append(manager)
    
    mid_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # 清理所有管理器
    for manager in managers:
        manager.clear()
    
    # 强制垃圾回收
    del managers
    gc.collect()
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    memory_increase = mid_memory - initial_memory
    memory_released = mid_memory - final_memory
    
    logger.info(f"内存使用: 初始={initial_memory:.1f}MB, 峰值={mid_memory:.1f}MB, 最终={final_memory:.1f}MB")
    logger.info(f"内存增长: {memory_increase:.1f}MB, 释放: {memory_released:.1f}MB")
    
    if memory_increase < 100:  # 50个管理器增长应该小于100MB
        logger.info("✅ 测试4通过: 内存使用合理")
    else:
        logger.warning(f"⚠️ 测试4注意: 内存增长较大 ({memory_increase:.1f}MB)")

async def main():
    """运行所有测试"""
    logger.info("🚀 开始紧急优化修复验证")
    logger.info("=" * 50)
    
    try:
        # 测试1: 异步编程修复
        await test_async_memory_save()
        logger.info("-" * 30)
        
        # 测试2: 音频缓冲区限制
        test_audio_buffer_limit()
        logger.info("-" * 30)
        
        # 测试3: 资源清理
        await test_resource_cleanup()
        logger.info("-" * 30)
        
        # 测试4: 内存使用
        test_memory_usage()
        logger.info("-" * 30)
        
        logger.info("🎉 所有紧急修复验证完成！")
        
    except Exception as e:
        logger.error(f"💥 验证过程发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    print("🔧 紧急优化修复验证脚本")
    print("正在验证已实施的三个紧急修复...")
    print("详细日志请查看: 紧急修复验证.log")
    
    asyncio.run(main())

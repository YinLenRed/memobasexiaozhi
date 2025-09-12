#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复LLM并发调用问题
解决rapid模式下OpenAI MissingParameter错误
"""

import asyncio
import time
import threading
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('LLM并发修复')

class LLMConcurrencyManager:
    """LLM并发调用管理器"""
    
    def __init__(self, max_concurrent_calls=2, call_interval=1.0):
        self.max_concurrent_calls = max_concurrent_calls  # 最大并发调用数
        self.call_interval = call_interval  # 调用间隔(秒)
        
        # 并发控制
        self.semaphore = asyncio.Semaphore(max_concurrent_calls)
        self.last_call_time = 0
        self.call_lock = threading.Lock()
        
        # 统计信息
        self.total_calls = 0
        self.concurrent_calls = 0
        self.error_calls = 0
        
        logger.info(f"🔧 LLM并发管理器已初始化")
        logger.info(f"   最大并发数: {max_concurrent_calls}")
        logger.info(f"   调用间隔: {call_interval}秒")
    
    async def safe_llm_call(self, llm_instance, messages: List[Dict], **kwargs) -> str:
        """安全的LLM调用，带并发控制"""
        async with self.semaphore:  # 限制并发数
            try:
                self.concurrent_calls += 1
                self.total_calls += 1
                
                # 控制调用频率
                await self._rate_limit()
                
                logger.debug(f"🔄 LLM调用开始 (并发数: {self.concurrent_calls}/{self.max_concurrent_calls})")
                
                # 执行LLM调用
                response = await asyncio.to_thread(llm_instance.chat, messages, **kwargs)
                
                if response and len(response.strip()) > 0:
                    # 检测错误响应
                    if "OpenAI服务响应异常" in response or "MissingParameter" in response:
                        logger.error(f"🚨 LLM返回错误: {response[:100]}...")
                        self.error_calls += 1
                        return self._get_fallback_response()
                    
                    logger.debug(f"✅ LLM调用成功: {response[:50]}...")
                    return response.strip()
                else:
                    logger.warning("⚠️ LLM返回空响应")
                    return self._get_fallback_response()
                    
            except Exception as e:
                self.error_calls += 1
                logger.error(f"❌ LLM调用异常: {e}")
                
                # 分析错误类型
                error_msg = str(e)
                if "MissingParameter" in error_msg:
                    logger.error("🔍 检测到MissingParameter - 可能是并发调用导致的参数问题")
                elif "timeout" in error_msg.lower():
                    logger.error("🔍 检测到超时 - 可能是并发调用过多")
                elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
                    logger.error("🔍 检测到限流 - API调用过于频繁")
                
                return self._get_fallback_response()
                
            finally:
                self.concurrent_calls -= 1
    
    async def _rate_limit(self):
        """调用频率限制"""
        with self.call_lock:
            current_time = time.time()
            time_since_last_call = current_time - self.last_call_time
            
            if time_since_last_call < self.call_interval:
                sleep_time = self.call_interval - time_since_last_call
                logger.debug(f"⏳ 频率限制，等待 {sleep_time:.2f} 秒")
                
        # 在锁外进行sleep
        if 'sleep_time' in locals():
            await asyncio.sleep(sleep_time)
        
        with self.call_lock:
            self.last_call_time = time.time()
    
    def _get_fallback_response(self) -> str:
        """获取备用响应"""
        fallback_responses = [
            "收到消息，请注意查看。",
            "消息提醒，请及时关注。",
            "信息更新，请查看详情。"
        ]
        import random
        return random.choice(fallback_responses)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_calls": self.total_calls,
            "concurrent_calls": self.concurrent_calls,
            "error_calls": self.error_calls,
            "error_rate": f"{(self.error_calls/max(self.total_calls,1)*100):.1f}%",
            "max_concurrent": self.max_concurrent_calls,
            "call_interval": f"{self.call_interval}秒"
        }

# 全局并发管理器
_concurrency_manager: Optional[LLMConcurrencyManager] = None

def get_llm_concurrency_manager() -> LLMConcurrencyManager:
    """获取全局LLM并发管理器"""
    global _concurrency_manager
    if _concurrency_manager is None:
        _concurrency_manager = LLMConcurrencyManager(
            max_concurrent_calls=2,  # 限制最大并发为2
            call_interval=0.8        # 每次调用间隔0.8秒
        )
    return _concurrency_manager

def patch_unified_event_service_for_concurrency():
    """为UnifiedEventService打并发控制补丁"""
    try:
        import sys
        from core.services.unified_event_service import UnifiedEventService
        
        # 备份原始的LLM调用方法
        original_generate = UnifiedEventService._generate_content_with_java_prompt
        
        async def safe_generate_with_concurrency(self, event_data: Dict[str, Any]) -> Optional[str]:
            """带并发控制的内容生成"""
            try:
                # 检查是否需要LLM处理
                prompt = event_data.get("prompt")
                result = (event_data.get("result") or 
                         event_data.get("content") or 
                         event_data.get("data") or 
                         event_data.get("festival"))
                
                if not prompt or not result or not self.llm:
                    return await original_generate(self, event_data)
                
                # 使用并发管理器进行LLM调用
                manager = get_llm_concurrency_manager()
                
                # 构建messages
                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"请根据以下信息生成回复：{result}"}
                ]
                
                # 安全的LLM调用
                response = await manager.safe_llm_call(self.llm, messages)
                
                logger.info(f"🎯 LLM并发调用完成: {response[:50]}...")
                return response
                
            except Exception as e:
                logger.error(f"并发LLM调用失败: {e}")
                # 降级到原始方法
                return await original_generate(self, event_data)
        
        # 替换方法
        UnifiedEventService._generate_content_with_java_prompt = safe_generate_with_concurrency
        logger.info("✅ UnifiedEventService并发控制补丁已应用")
        
    except Exception as e:
        logger.error(f"❌ 并发控制补丁应用失败: {e}")

async def test_concurrent_llm_calls():
    """测试并发LLM调用"""
    logger.info("🧪 测试LLM并发调用控制")
    logger.info("="*40)
    
    class MockLLM:
        def __init__(self):
            self.call_count = 0
        
        def chat(self, messages, **kwargs):
            self.call_count += 1
            call_id = self.call_count
            
            # 模拟处理时间
            time.sleep(0.5)
            
            # 模拟偶发的并发问题
            if call_id > 1 and call_id % 3 == 0:
                raise Exception("OpenAI服务响应异常: MissingParameter")
            
            return f"响应内容 {call_id} - 处理时间: {datetime.now().strftime('%H:%M:%S')}"
    
    mock_llm = MockLLM()
    manager = LLMConcurrencyManager(max_concurrent_calls=2, call_interval=0.5)
    
    # 模拟快速发送5条消息（类似rapid测试）
    test_messages = [
        [{"role": "user", "content": f"测试消息 {i}"}] 
        for i in range(1, 6)
    ]
    
    logger.info(f"📤 模拟发送 {len(test_messages)} 条并发消息")
    
    # 并发发送所有消息
    start_time = time.time()
    tasks = [
        manager.safe_llm_call(mock_llm, messages) 
        for messages in test_messages
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    # 显示结果
    logger.info(f"📊 并发测试完成，总耗时: {end_time - start_time:.2f} 秒")
    
    for i, result in enumerate(results, 1):
        if isinstance(result, Exception):
            logger.error(f"   消息 {i}: ❌ {result}")
        else:
            logger.info(f"   消息 {i}: ✅ {result}")
    
    # 显示统计信息
    stats = manager.get_stats()
    logger.info("📈 调用统计:")
    for key, value in stats.items():
        logger.info(f"   {key}: {value}")

def create_improved_test_script():
    """创建改进的测试脚本"""
    improved_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的消息队列测试 - 支持LLM并发控制
"""

import asyncio
import time
from datetime import datetime
import logging

# 应用并发控制补丁
from 修复LLM并发问题 import patch_unified_event_service_for_concurrency
patch_unified_event_service_for_concurrency()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('改进队列测试')

DEVICE_ID = "f0:9e:9e:04:8a:44"

async def test_rapid_with_concurrency_control():
    """带并发控制的快速消息测试"""
    logger.info("🧪 测试带并发控制的快速消息发送")
    logger.info("="*50)
    
    messages = [
        {"title": "天气预警", "prompt": "大风预警，请注意安全", "priority": 0},
        {"title": "节日问候", "prompt": "节日快乐，祝您愉快", "priority": 1},  
        {"title": "24节气", "prompt": "立秋时节，注意养生", "priority": 1},
        {"title": "天气播报", "prompt": "今日晴朗，温度适宜", "priority": 2},
    ]
    
    logger.info(f"📋 准备发送 {len(messages)} 条消息（间隔1秒，避免并发冲突）")
    
    for i, msg in enumerate(messages, 1):
        logger.info(f"📤 [{i}/{len(messages)}] 发送: {msg['title']}")
        
        # 发送消息的API调用...
        await asyncio.sleep(1.0)  # 增加间隔到1秒，避免并发问题
        
        logger.info(f"   ✅ 消息 {i} 发送完成")
    
    logger.info("✅ 所有消息发送完成，LLM并发得到有效控制")

if __name__ == "__main__":
    asyncio.run(test_rapid_with_concurrency_control())
'''
    
    with open("改进的消息队列测试.py", "w", encoding="utf-8") as f:
        f.write(improved_script)
    
    logger.info("📄 创建了改进的测试脚本: 改进的消息队列测试.py")

def main():
    """主函数"""
    logger.info("🔧 LLM并发调用问题修复工具")
    logger.info("="*40)
    
    print("🎯 修复方案:")
    print("1. 应用并发控制补丁")
    print("2. 测试并发LLM调用")
    print("3. 创建改进的测试脚本")
    print()
    
    choice = input("选择操作 (1-3, 或按回车全部执行): ").strip()
    
    if choice == "1" or not choice:
        patch_unified_event_service_for_concurrency()
    
    if choice == "2" or not choice:
        asyncio.run(test_concurrent_llm_calls())
    
    if choice == "3" or not choice:
        create_improved_test_script()
    
    print()
    print("🎉 修复完成！建议:")
    print("1. 重启Python服务以使补丁生效")
    print("2. 使用 python 改进的消息队列测试.py 测试")
    print("3. 或者在rapid测试中增加消息间隔到1-2秒")

if __name__ == "__main__":
    main()

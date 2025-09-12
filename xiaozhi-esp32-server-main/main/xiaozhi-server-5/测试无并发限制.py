#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试LLM并发控制是否已关闭
"""

import asyncio
import time
from core.utils.llm_pool import get_llm_pool

class MockLLM:
    """模拟LLM服务"""
    def __init__(self):
        self.call_count = 0
    
    def response(self, session_id, messages, **kwargs):
        self.call_count += 1
        time.sleep(0.1)  # 模拟处理时间
        return [f"响应 {self.call_count}"]

async def test_unlimited_concurrency():
    """测试无限制并发"""
    print("🧪 测试并发控制是否已关闭...")
    
    # 创建LLM池（应该是999并发）
    llm_pool = get_llm_pool(max_concurrent=999)
    mock_llm = MockLLM()
    
    # 同时发送10个请求
    print("📤 发送10个并发请求...")
    
    start_time = time.time()
    
    async def single_call(i):
        result = await llm_pool.call_llm(
            mock_llm, "response", f"session_{i}", [{"role": "user", "content": f"测试{i}"}]
        )
        return i, result
    
    # 并发执行
    tasks = [single_call(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"📊 测试结果:")
    print(f"   总请求数: {len(results)}")
    print(f"   总耗时: {total_time:.2f} 秒")
    print(f"   平均耗时: {total_time/len(results):.2f} 秒")
    
    # 获取连接池统计
    stats = llm_pool.get_stats()
    print(f"   最大并发数: {llm_pool.max_concurrent}")
    print(f"   成功率: {stats['success_rate']}")
    
    # 判断是否关闭了并发限制
    if total_time < 0.5:  # 如果总耗时很短，说明是并发执行的
        print("✅ 并发控制已成功关闭：所有请求几乎同时执行")
    else:
        print("⚠️ 并发控制可能仍在工作：请求是串行执行的")

if __name__ == "__main__":
    asyncio.run(test_unlimited_concurrency())

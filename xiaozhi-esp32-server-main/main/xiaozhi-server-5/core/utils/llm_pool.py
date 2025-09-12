#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM连接池管理器
解决LLM并发调用限制、API限额超出、调用失败等问题
"""

import asyncio
import time
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from loguru import logger

TAG = "LLMPool"

class LLMRateLimiter:
    """LLM调用频率限制器"""
    
    def __init__(self, max_calls_per_minute: int = 60, max_calls_per_second: int = 3):
        self.max_calls_per_minute = max_calls_per_minute
        self.max_calls_per_second = max_calls_per_second
        
        # 使用滑动窗口记录调用时间
        self.call_times = deque(maxlen=max_calls_per_minute)
        self.recent_calls = deque(maxlen=max_calls_per_second)
        
        self._lock = threading.Lock()
    
    async def acquire(self) -> bool:
        """获取调用许可"""
        with self._lock:
            now = time.time()
            
            # 清理过期的调用记录
            cutoff_minute = now - 60  # 1分钟前
            cutoff_second = now - 1   # 1秒前
            
            # 清理分钟级别的记录
            while self.call_times and self.call_times[0] < cutoff_minute:
                self.call_times.popleft()
            
            # 清理秒级别的记录
            while self.recent_calls and self.recent_calls[0] < cutoff_second:
                self.recent_calls.popleft()
            
            # 检查是否超过限制
            if len(self.call_times) >= self.max_calls_per_minute:
                wait_time = self.call_times[0] + 60 - now
                logger.bind(tag=TAG).warning(f"分钟限额达到，需等待 {wait_time:.1f} 秒")
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    return await self.acquire()  # 递归重试
            
            if len(self.recent_calls) >= self.max_calls_per_second:
                wait_time = self.recent_calls[0] + 1 - now
                logger.bind(tag=TAG).debug(f"秒限额达到，需等待 {wait_time:.3f} 秒")
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    return await self.acquire()  # 递归重试
            
            # 记录调用时间
            self.call_times.append(now)
            self.recent_calls.append(now)
            return True
    
    def get_stats(self) -> dict:
        """获取频率限制统计"""
        now = time.time()
        recent_minute = sum(1 for t in self.call_times if t > now - 60)
        recent_second = sum(1 for t in self.recent_calls if t > now - 1)
        
        return {
            "calls_last_minute": recent_minute,
            "calls_last_second": recent_second,
            "minute_limit": self.max_calls_per_minute,
            "second_limit": self.max_calls_per_second,
            "minute_utilization": f"{recent_minute/self.max_calls_per_minute*100:.1f}%",
            "second_utilization": f"{recent_second/self.max_calls_per_second*100:.1f}%"
        }

class LLMConnectionPool:
    """LLM连接池管理器"""
    
    def __init__(self, max_concurrent: int = 3, enable_retry: bool = True):
        self.max_concurrent = max_concurrent
        self.enable_retry = enable_retry
        
        # 并发控制
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = LLMRateLimiter(max_calls_per_minute=99999, max_calls_per_second=99999)  # 关闭频率限制
        
        # 统计信息
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'retried_calls': 0,
            'concurrent_calls': 0,
            'avg_response_time': 0.0,
            'last_call_time': 0
        }
        
        # 响应时间记录（最近100次）
        self.response_times = deque(maxlen=100)
        
        # 错误统计
        self.error_stats = defaultdict(int)
        
        logger.bind(tag=TAG).info(f"LLM连接池初始化: 最大并发{max_concurrent}, 重试{'启用' if enable_retry else '禁用'}")
    
    async def call_llm(self, llm_instance, method_name: str, *args, **kwargs) -> Any:
        """
        安全的LLM调用
        
        Args:
            llm_instance: LLM实例
            method_name: 调用的方法名（如'response', 'response_no_stream'等）
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            LLM调用结果
        """
        async with self.semaphore:
            await self.rate_limiter.acquire()
            
            self.stats['concurrent_calls'] += 1
            self.stats['total_calls'] += 1
            self.stats['last_call_time'] = time.time()
            
            start_time = time.time()
            
            try:
                # 获取LLM方法
                if not hasattr(llm_instance, method_name):
                    raise AttributeError(f"LLM实例没有方法: {method_name}")
                
                method = getattr(llm_instance, method_name)
                
                logger.bind(tag=TAG).debug(f"调用LLM方法: {method_name}, 并发数: {self.stats['concurrent_calls']}")
                
                # 执行LLM调用
                if asyncio.iscoroutinefunction(method):
                    result = await method(*args, **kwargs)
                else:
                    # 对于同步方法，使用线程池执行
                    result = await asyncio.to_thread(method, *args, **kwargs)
                
                # 记录成功
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                self.stats['successful_calls'] += 1
                
                logger.bind(tag=TAG).debug(f"LLM调用成功: {method_name}, 耗时: {response_time:.3f}秒")
                
                return result
                
            except Exception as e:
                # 记录错误
                error_type = type(e).__name__
                self.error_stats[error_type] += 1
                self.stats['failed_calls'] += 1
                
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                
                logger.bind(tag=TAG).error(f"LLM调用失败: {method_name}, 错误: {error_type}: {str(e)[:100]}")
                
                # 根据错误类型决定是否重试
                if self.enable_retry and self._should_retry(e):
                    return await self._retry_call(llm_instance, method_name, e, *args, **kwargs)
                
                # 不重试或重试失败，抛出原始异常
                raise
                
            finally:
                self.stats['concurrent_calls'] -= 1
                
                # 更新平均响应时间
                if self.response_times:
                    self.stats['avg_response_time'] = sum(self.response_times) / len(self.response_times)
    
    def _should_retry(self, error: Exception) -> bool:
        """判断是否应该重试"""
        error_msg = str(error).lower()
        
        # 可重试的错误类型
        retryable_errors = [
            'timeout',
            'connection',
            'rate limit',
            'service unavailable',
            'internal server error',
            'bad gateway',
            'temporary',
            'busy'
        ]
        
        return any(keyword in error_msg for keyword in retryable_errors)
    
    async def _retry_call(self, llm_instance, method_name: str, original_error: Exception, *args, **kwargs) -> Any:
        """重试LLM调用"""
        max_retries = 2
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                self.stats['retried_calls'] += 1
                
                # 指数退避延迟
                delay = base_delay * (2 ** attempt)
                logger.bind(tag=TAG).info(f"重试LLM调用 ({attempt + 1}/{max_retries}), 延迟: {delay}秒")
                
                await asyncio.sleep(delay)
                
                # 重新获取信号量和频率限制
                async with self.semaphore:
                    await self.rate_limiter.acquire()
                    
                    method = getattr(llm_instance, method_name)
                    
                    if asyncio.iscoroutinefunction(method):
                        result = await method(*args, **kwargs)
                    else:
                        result = await asyncio.to_thread(method, *args, **kwargs)
                    
                    logger.bind(tag=TAG).info(f"LLM重试成功: {method_name}")
                    return result
                    
            except Exception as retry_error:
                logger.bind(tag=TAG).warning(f"LLM重试 {attempt + 1} 失败: {retry_error}")
                
                if attempt == max_retries - 1:
                    # 最后一次重试失败，抛出原始错误
                    logger.bind(tag=TAG).error(f"LLM重试全部失败，抛出原始错误: {original_error}")
                    raise original_error
    
    def get_stats(self) -> dict:
        """获取连接池统计信息"""
        rate_stats = self.rate_limiter.get_stats()
        
        return {
            **self.stats,
            'success_rate': f"{self.stats['successful_calls'] / max(self.stats['total_calls'], 1) * 100:.1f}%",
            'error_breakdown': dict(self.error_stats),
            'rate_limiter': rate_stats,
            'pool_utilization': f"{self.stats['concurrent_calls'] / self.max_concurrent * 100:.1f}%"
        }
    
    def get_health_status(self) -> dict:
        """获取连接池健康状态"""
        success_rate = self.stats['successful_calls'] / max(self.stats['total_calls'], 1)
        avg_response_time = self.stats['avg_response_time']
        
        # 健康状态判断
        if success_rate >= 0.95 and avg_response_time < 5.0:
            status = "healthy"
        elif success_rate >= 0.8 and avg_response_time < 10.0:
            status = "warning"
        else:
            status = "unhealthy"
        
        return {
            'status': status,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'concurrent_calls': self.stats['concurrent_calls'],
            'total_errors': self.stats['failed_calls']
        }

# 全局LLM连接池实例
_global_llm_pool: Optional[LLMConnectionPool] = None

def get_llm_pool(max_concurrent: int = 3, enable_retry: bool = True) -> LLMConnectionPool:
    """获取全局LLM连接池实例"""
    global _global_llm_pool
    
    if _global_llm_pool is None:
        _global_llm_pool = LLMConnectionPool(max_concurrent, enable_retry)
    
    return _global_llm_pool

def reset_llm_pool():
    """重置LLM连接池（主要用于测试）"""
    global _global_llm_pool
    _global_llm_pool = None

# 便捷装饰器
def llm_pool_call(method_name: str):
    """LLM连接池调用装饰器"""
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            pool = get_llm_pool()
            return await pool.call_llm(self.llm, method_name, *args, **kwargs)
        return wrapper
    return decorator

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT消息限流器
防止消息洪水攻击导致服务崩溃
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """限流配置"""
    max_messages_per_second: int = 10  # 每秒最大消息数
    max_messages_per_minute: int = 300  # 每分钟最大消息数
    max_queue_size: int = 1000  # 最大队列大小
    burst_limit: int = 20  # 突发限制
    cooldown_seconds: int = 60  # 冷却时间

class MessageRateLimiter:
    """MQTT消息限流器"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._message_counts: Dict[str, deque] = defaultdict(deque)  # device_id -> timestamps
        self._burst_counts: Dict[str, int] = defaultdict(int)  # device_id -> burst_count
        self._last_reset: Dict[str, float] = defaultdict(float)  # device_id -> last_reset_time
        self._blocked_until: Dict[str, float] = defaultdict(float)  # device_id -> blocked_until_time
        self._lock = Lock()
        
        # 统计信息
        self.total_messages = 0
        self.blocked_messages = 0
        self.last_cleanup = time.time()
        
        logger.info(f"🛡️ MQTT消息限流器已初始化: {self.config}")
    
    def is_allowed(self, device_id: str, message_type: str = "default") -> bool:
        """
        检查消息是否被允许
        
        Args:
            device_id: 设备ID
            message_type: 消息类型
            
        Returns:
            bool: 是否允许处理该消息
        """
        current_time = time.time()
        
        with self._lock:
            # 清理过期数据
            self._cleanup_old_records(current_time)
            
            # 检查是否在冷却期
            if current_time < self._blocked_until[device_id]:
                self.blocked_messages += 1
                logger.warning(f"🚫 设备 {device_id} 在冷却期，拒绝消息 (还需等待 {self._blocked_until[device_id] - current_time:.1f}秒)")
                return False
            
            # 获取该设备的消息时间戳队列
            timestamps = self._message_counts[device_id]
            
            # 移除超过1分钟的旧时间戳
            while timestamps and current_time - timestamps[0] > 60:
                timestamps.popleft()
            
            # 检查每分钟限制
            if len(timestamps) >= self.config.max_messages_per_minute:
                self._trigger_cooldown(device_id, current_time, "每分钟消息数超限")
                return False
            
            # 检查每秒限制
            recent_messages = sum(1 for ts in timestamps if current_time - ts <= 1.0)
            if recent_messages >= self.config.max_messages_per_second:
                logger.warning(f"⚠️ 设备 {device_id} 每秒消息数超限 ({recent_messages}/{self.config.max_messages_per_second})")
                # 不立即阻断，但记录警告
                if recent_messages > self.config.max_messages_per_second * 2:
                    self._trigger_cooldown(device_id, current_time, "每秒消息数严重超限")
                    return False
            
            # 检查突发限制
            burst_count = self._burst_counts[device_id]
            if burst_count >= self.config.burst_limit:
                self._trigger_cooldown(device_id, current_time, "突发消息数超限")
                return False
            
            # 记录此消息
            timestamps.append(current_time)
            self._burst_counts[device_id] += 1
            self.total_messages += 1
            
            # 重置突发计数器（每5秒重置一次）
            if current_time - self._last_reset[device_id] > 5:
                self._burst_counts[device_id] = 0
                self._last_reset[device_id] = current_time
            
            return True
    
    def _trigger_cooldown(self, device_id: str, current_time: float, reason: str):
        """触发冷却期"""
        self._blocked_until[device_id] = current_time + self.config.cooldown_seconds
        self.blocked_messages += 1
        
        logger.error(f"🚨 设备 {device_id} 触发限流冷却: {reason}")
        logger.info(f"   冷却时间: {self.config.cooldown_seconds}秒")
        logger.info(f"   解除时间: {time.strftime('%H:%M:%S', time.localtime(self._blocked_until[device_id]))}")
    
    def _cleanup_old_records(self, current_time: float):
        """清理过期记录"""
        # 每分钟清理一次
        if current_time - self.last_cleanup < 60:
            return
        
        self.last_cleanup = current_time
        cleanup_count = 0
        
        # 清理消息计数
        for device_id, timestamps in list(self._message_counts.items()):
            # 移除超过5分钟的记录
            while timestamps and current_time - timestamps[0] > 300:
                timestamps.popleft()
                cleanup_count += 1
            
            # 如果队列为空，删除该设备记录
            if not timestamps:
                del self._message_counts[device_id]
                if device_id in self._burst_counts:
                    del self._burst_counts[device_id]
                if device_id in self._last_reset:
                    del self._last_reset[device_id]
        
        # 清理过期的阻断记录
        for device_id in list(self._blocked_until.keys()):
            if current_time > self._blocked_until[device_id]:
                del self._blocked_until[device_id]
                logger.info(f"🔓 设备 {device_id} 冷却期结束，恢复正常")
        
        if cleanup_count > 0:
            logger.debug(f"🧹 清理了 {cleanup_count} 条过期消息记录")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            current_time = time.time()
            
            return {
                "总消息数": self.total_messages,
                "被阻断消息数": self.blocked_messages,
                "阻断率": f"{(self.blocked_messages/max(self.total_messages, 1)*100):.1f}%",
                "活跃设备数": len(self._message_counts),
                "被冷却设备数": len([d for d, t in self._blocked_until.items() if current_time < t]),
                "限流配置": {
                    "每秒最大": self.config.max_messages_per_second,
                    "每分钟最大": self.config.max_messages_per_minute,
                    "突发限制": self.config.burst_limit,
                    "冷却时间": f"{self.config.cooldown_seconds}秒"
                }
            }
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """获取设备限流状态"""
        with self._lock:
            current_time = time.time()
            timestamps = self._message_counts.get(device_id, deque())
            
            # 计算最近消息数
            recent_1min = len(timestamps)
            recent_1sec = sum(1 for ts in timestamps if current_time - ts <= 1.0)
            
            is_blocked = current_time < self._blocked_until.get(device_id, 0)
            time_until_unblock = max(0, self._blocked_until.get(device_id, 0) - current_time)
            
            return {
                "设备ID": device_id,
                "最近1分钟消息数": recent_1min,
                "最近1秒消息数": recent_1sec,
                "突发计数": self._burst_counts.get(device_id, 0),
                "是否被阻断": is_blocked,
                "解除阻断倒计时": f"{time_until_unblock:.1f}秒" if is_blocked else "正常",
                "状态": "🚫冷却中" if is_blocked else "✅正常"
            }
    
    def reset_device_limits(self, device_id: str):
        """重置设备限流状态"""
        with self._lock:
            if device_id in self._message_counts:
                del self._message_counts[device_id]
            if device_id in self._burst_counts:
                del self._burst_counts[device_id]
            if device_id in self._last_reset:
                del self._last_reset[device_id]
            if device_id in self._blocked_until:
                del self._blocked_until[device_id]
            
            logger.info(f"🔄 已重置设备 {device_id} 的限流状态")
    
    def update_config(self, new_config: RateLimitConfig):
        """更新限流配置"""
        with self._lock:
            old_config = self.config
            self.config = new_config
            
            logger.info(f"🔧 限流配置已更新:")
            logger.info(f"   每秒最大: {old_config.max_messages_per_second} → {new_config.max_messages_per_second}")
            logger.info(f"   每分钟最大: {old_config.max_messages_per_minute} → {new_config.max_messages_per_minute}")
            logger.info(f"   突发限制: {old_config.burst_limit} → {new_config.burst_limit}")


class AdaptiveRateLimiter(MessageRateLimiter):
    """自适应限流器 - 根据系统负载动态调整限制"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        super().__init__(config)
        self.system_load = 0.0
        self.last_load_check = time.time()
        self.base_config = self.config
    
    def update_system_load(self, load: float):
        """更新系统负载 (0.0-1.0)"""
        self.system_load = load
        self.last_load_check = time.time()
        
        # 根据负载调整限制
        if load > 0.8:  # 高负载
            scale = 0.3
        elif load > 0.6:  # 中负载
            scale = 0.6
        elif load > 0.4:  # 轻负载
            scale = 0.8
        else:  # 低负载
            scale = 1.0
        
        # 动态调整配置
        self.config.max_messages_per_second = int(self.base_config.max_messages_per_second * scale)
        self.config.max_messages_per_minute = int(self.base_config.max_messages_per_minute * scale)
        
        logger.debug(f"📊 系统负载: {load:.1f}, 限流比例: {scale:.1f}")


# 全局限流器实例
_rate_limiter: Optional[MessageRateLimiter] = None

def get_rate_limiter() -> MessageRateLimiter:
    """获取全局限流器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = MessageRateLimiter()
    return _rate_limiter

def init_rate_limiter(config: Optional[RateLimitConfig] = None, adaptive: bool = False) -> MessageRateLimiter:
    """初始化全局限流器"""
    global _rate_limiter
    if adaptive:
        _rate_limiter = AdaptiveRateLimiter(config)
    else:
        _rate_limiter = MessageRateLimiter(config)
    return _rate_limiter

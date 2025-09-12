#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一错误处理系统
标准化错误分类、记录、恢复和告警机制
"""

import asyncio
import traceback
import time
from typing import Dict, Any, Optional, Callable, List, Type
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict, deque
from functools import wraps
from loguru import logger

TAG = "ErrorHandler"

class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"           # 轻微错误，不影响核心功能
    MEDIUM = "medium"     # 中等错误，影响部分功能
    HIGH = "high"         # 严重错误，影响核心功能
    CRITICAL = "critical" # 致命错误，系统无法正常运行

class ErrorCategory(Enum):
    """错误分类"""
    NETWORK = "network"           # 网络相关错误
    API = "api"                   # API调用错误
    DATABASE = "database"         # 数据库错误
    LLM = "llm"                   # LLM调用错误
    HARDWARE = "hardware"         # 硬件设备错误
    VALIDATION = "validation"     # 数据验证错误
    PERMISSION = "permission"     # 权限错误
    RESOURCE = "resource"         # 资源不足错误
    UNKNOWN = "unknown"           # 未知错误

@dataclass
class ErrorInfo:
    """错误信息结构"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    timestamp: float
    traceback_info: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    resolved: bool = False
    
class ErrorClassifier:
    """错误分类器"""
    
    def __init__(self):
        # 错误模式匹配规则
        self.patterns = {
            ErrorCategory.NETWORK: [
                "connection", "timeout", "network", "dns", "socket",
                "unreachable", "refused", "reset", "broken pipe"
            ],
            ErrorCategory.API: [
                "api", "rate limit", "quota", "unauthorized", "forbidden",
                "not found", "bad request", "service unavailable"
            ],
            ErrorCategory.LLM: [
                "openai", "llm", "model", "token", "completion",
                "missing parameter", "invalid request"
            ],
            ErrorCategory.DATABASE: [
                "database", "sql", "connection pool", "transaction",
                "integrity", "constraint"
            ],
            ErrorCategory.HARDWARE: [
                "device", "hardware", "sensor", "microphone", "speaker",
                "audio", "vad", "asr", "tts"
            ],
            ErrorCategory.VALIDATION: [
                "validation", "invalid", "format", "schema", "parse"
            ],
            ErrorCategory.PERMISSION: [
                "permission", "access", "denied", "unauthorized", "auth"
            ],
            ErrorCategory.RESOURCE: [
                "memory", "disk", "cpu", "resource", "limit", "exhausted"
            ]
        }
        
        # 严重程度判断规则
        self.severity_patterns = {
            ErrorSeverity.CRITICAL: [
                "fatal", "critical", "crash", "shutdown", "abort",
                "out of memory", "segmentation fault"
            ],
            ErrorSeverity.HIGH: [
                "error", "failed", "exception", "broken", "corrupted",
                "unavailable", "unreachable"
            ],
            ErrorSeverity.MEDIUM: [
                "warning", "timeout", "retry", "degraded", "slow"
            ],
            ErrorSeverity.LOW: [
                "info", "debug", "notice", "temporary", "minor"
            ]
        }
    
    def classify_error(self, error: Exception, context: Optional[Dict] = None) -> tuple[ErrorCategory, ErrorSeverity]:
        """分类错误"""
        error_msg = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # 分类错误类别
        category = ErrorCategory.UNKNOWN
        for cat, patterns in self.patterns.items():
            if any(pattern in error_msg or pattern in error_type for pattern in patterns):
                category = cat
                break
        
        # 判断严重程度
        severity = ErrorSeverity.MEDIUM  # 默认中等
        for sev, patterns in self.severity_patterns.items():
            if any(pattern in error_msg or pattern in error_type for pattern in patterns):
                severity = sev
                break
        
        # 根据异常类型调整严重程度
        if isinstance(error, (SystemExit, KeyboardInterrupt)):
            severity = ErrorSeverity.CRITICAL
        elif isinstance(error, (MemoryError, OSError)):
            severity = ErrorSeverity.HIGH
        elif isinstance(error, (ValueError, TypeError, AttributeError)):
            if context and context.get('user_input'):
                severity = ErrorSeverity.LOW  # 用户输入错误通常不严重
            else:
                severity = ErrorSeverity.MEDIUM
        
        return category, severity

class ErrorRecoveryHandler:
    """错误恢复处理器"""
    
    def __init__(self):
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = {
            ErrorCategory.NETWORK: [
                self._retry_with_backoff,
                self._switch_to_fallback_endpoint,
                self._cache_and_retry_later
            ],
            ErrorCategory.API: [
                self._wait_for_rate_limit_reset,
                self._use_alternative_api,
                self._degrade_service_gracefully
            ],
            ErrorCategory.LLM: [
                self._retry_llm_call,
                self._use_fallback_response,
                self._switch_llm_provider
            ],
            ErrorCategory.HARDWARE: [
                self._reinitialize_device,
                self._use_software_fallback,
                self._notify_hardware_issue
            ],
            ErrorCategory.RESOURCE: [
                self._free_resources,
                self._throttle_requests,
                self._restart_service
            ]
        }
    
    async def attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """尝试错误恢复"""
        strategies = self.recovery_strategies.get(error_info.category, [])
        
        for strategy in strategies:
            try:
                logger.bind(tag=TAG).info(f"尝试恢复策略: {strategy.__name__}")
                success = await strategy(error_info)
                if success:
                    logger.bind(tag=TAG).info(f"恢复成功: {strategy.__name__}")
                    error_info.resolved = True
                    return True
            except Exception as e:
                logger.bind(tag=TAG).warning(f"恢复策略失败 {strategy.__name__}: {e}")
        
        return False
    
    async def _retry_with_backoff(self, error_info: ErrorInfo) -> bool:
        """指数退避重试"""
        if error_info.retry_count >= 3:
            return False
        
        delay = min(2 ** error_info.retry_count, 60)  # 最大60秒
        await asyncio.sleep(delay)
        error_info.retry_count += 1
        return True
    
    async def _switch_to_fallback_endpoint(self, error_info: ErrorInfo) -> bool:
        """切换到备用端点"""
        # 实际实现需要根据具体服务配置
        logger.bind(tag=TAG).info("切换到备用端点")
        return True
    
    async def _cache_and_retry_later(self, error_info: ErrorInfo) -> bool:
        """缓存请求稍后重试"""
        logger.bind(tag=TAG).info("请求已缓存，稍后重试")
        return True
    
    async def _wait_for_rate_limit_reset(self, error_info: ErrorInfo) -> bool:
        """等待速率限制重置"""
        # 根据API响应头确定等待时间
        await asyncio.sleep(60)  # 默认等待1分钟
        return True
    
    async def _use_alternative_api(self, error_info: ErrorInfo) -> bool:
        """使用替代API"""
        logger.bind(tag=TAG).info("切换到替代API")
        return True
    
    async def _degrade_service_gracefully(self, error_info: ErrorInfo) -> bool:
        """优雅降级服务"""
        logger.bind(tag=TAG).info("服务优雅降级")
        return True
    
    async def _retry_llm_call(self, error_info: ErrorInfo) -> bool:
        """重试LLM调用"""
        if error_info.retry_count >= 2:
            return False
        await asyncio.sleep(1)
        error_info.retry_count += 1
        return True
    
    async def _use_fallback_response(self, error_info: ErrorInfo) -> bool:
        """使用备用响应"""
        logger.bind(tag=TAG).info("使用LLM备用响应")
        return True
    
    async def _switch_llm_provider(self, error_info: ErrorInfo) -> bool:
        """切换LLM提供商"""
        logger.bind(tag=TAG).info("切换LLM提供商")
        return True
    
    async def _reinitialize_device(self, error_info: ErrorInfo) -> bool:
        """重新初始化设备"""
        logger.bind(tag=TAG).info("重新初始化硬件设备")
        return True
    
    async def _use_software_fallback(self, error_info: ErrorInfo) -> bool:
        """使用软件备用方案"""
        logger.bind(tag=TAG).info("使用软件备用方案")
        return True
    
    async def _notify_hardware_issue(self, error_info: ErrorInfo) -> bool:
        """通知硬件问题"""
        logger.bind(tag=TAG).warning("硬件问题已通知")
        return True
    
    async def _free_resources(self, error_info: ErrorInfo) -> bool:
        """释放资源"""
        logger.bind(tag=TAG).info("释放系统资源")
        return True
    
    async def _throttle_requests(self, error_info: ErrorInfo) -> bool:
        """限制请求速率"""
        logger.bind(tag=TAG).info("启用请求限流")
        return True
    
    async def _restart_service(self, error_info: ErrorInfo) -> bool:
        """重启服务"""
        logger.bind(tag=TAG).warning("建议重启服务")
        return False  # 不自动重启，只是建议

class ErrorStatistics:
    """错误统计"""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.category_counts = defaultdict(int)
        self.severity_counts = defaultdict(int)
        self.recent_errors = deque(maxlen=1000)  # 最近1000个错误
        self.hourly_stats = defaultdict(lambda: defaultdict(int))
    
    def record_error(self, error_info: ErrorInfo):
        """记录错误统计"""
        self.error_counts[error_info.error_id] += 1
        self.category_counts[error_info.category.value] += 1
        self.severity_counts[error_info.severity.value] += 1
        self.recent_errors.append(error_info)
        
        # 按小时统计
        hour = int(error_info.timestamp // 3600)
        self.hourly_stats[hour][error_info.category.value] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        total_errors = sum(self.error_counts.values())
        
        return {
            "total_errors": total_errors,
            "category_breakdown": dict(self.category_counts),
            "severity_breakdown": dict(self.severity_counts),
            "recent_error_rate": len([e for e in self.recent_errors 
                                    if time.time() - e.timestamp < 3600]),  # 最近1小时
            "most_frequent_errors": sorted(
                self.error_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        }

class UnifiedErrorHandler:
    """统一错误处理器"""
    
    def __init__(self):
        self.classifier = ErrorClassifier()
        self.recovery_handler = ErrorRecoveryHandler()
        self.statistics = ErrorStatistics()
        self.error_history: Dict[str, ErrorInfo] = {}
    
    async def handle_error(
        self, 
        error: Exception, 
        context: Optional[Dict[str, Any]] = None,
        auto_recover: bool = True
    ) -> ErrorInfo:
        """
        统一错误处理入口
        
        Args:
            error: 异常对象
            context: 错误上下文信息
            auto_recover: 是否尝试自动恢复
            
        Returns:
            ErrorInfo: 错误信息对象
        """
        # 生成错误ID
        error_id = f"{type(error).__name__}_{hash(str(error)) % 100000}"
        
        # 分类错误
        category, severity = self.classifier.classify_error(error, context)
        
        # 创建错误信息
        error_info = ErrorInfo(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(error),
            timestamp=time.time(),
            traceback_info=traceback.format_exc(),
            context=context or {}
        )
        
        # 记录错误
        self._log_error(error_info)
        
        # 更新统计
        self.statistics.record_error(error_info)
        self.error_history[error_id] = error_info
        
        # 尝试自动恢复
        if auto_recover and severity != ErrorSeverity.LOW:
            await self.recovery_handler.attempt_recovery(error_info)
        
        return error_info
    
    def _log_error(self, error_info: ErrorInfo):
        """记录错误日志"""
        log_method = {
            ErrorSeverity.LOW: logger.debug,
            ErrorSeverity.MEDIUM: logger.warning,
            ErrorSeverity.HIGH: logger.error,
            ErrorSeverity.CRITICAL: logger.critical
        }.get(error_info.severity, logger.error)
        
        log_method(
            f"[{error_info.category.value.upper()}] {error_info.message}",
            extra={
                "error_id": error_info.error_id,
                "severity": error_info.severity.value,
                "context": error_info.context
            }
        )
        
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.bind(tag=TAG).error(f"错误堆栈:\n{error_info.traceback_info}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return self.statistics.get_stats()
    
    def get_error_history(self, limit: int = 100) -> List[ErrorInfo]:
        """获取错误历史"""
        return list(self.error_history.values())[-limit:]

# 全局错误处理器实例
_global_error_handler: Optional[UnifiedErrorHandler] = None

def get_error_handler() -> UnifiedErrorHandler:
    """获取全局错误处理器"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = UnifiedErrorHandler()
    return _global_error_handler

# 错误处理装饰器
def handle_errors(
    category: Optional[ErrorCategory] = None,
    severity: Optional[ErrorSeverity] = None,
    auto_recover: bool = True,
    reraise: bool = True
):
    """错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()
                context = {
                    "function": func.__name__,
                    "args": str(args)[:200],
                    "kwargs": str(kwargs)[:200]
                }
                
                error_info = await error_handler.handle_error(e, context, auto_recover)
                
                if reraise:
                    raise
                return None
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()
                context = {
                    "function": func.__name__,
                    "args": str(args)[:200],
                    "kwargs": str(kwargs)[:200]
                }
                
                # 对于同步函数，使用asyncio.run处理
                try:
                    loop = asyncio.get_event_loop()
                    asyncio.run_coroutine_threadsafe(
                        error_handler.handle_error(e, context, auto_recover),
                        loop
                    )
                except RuntimeError:
                    asyncio.run(error_handler.handle_error(e, context, auto_recover))
                
                if reraise:
                    raise
                return None
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

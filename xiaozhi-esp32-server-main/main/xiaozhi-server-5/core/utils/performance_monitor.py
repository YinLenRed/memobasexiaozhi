#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控系统
实时收集系统性能指标、分析瓶颈、生成报告
"""

import asyncio
import time
import threading
import psutil
import gc
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timedelta
from loguru import logger

TAG = "PerformanceMonitor"

@dataclass
class PerformanceMetric:
    """性能指标数据结构"""
    name: str
    value: float
    timestamp: float
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class SystemStats:
    """系统统计信息"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    thread_count: int
    open_files: int

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.system_stats_history = deque(maxlen=max_history)
        self._lock = threading.Lock()
    
    def record_metric(self, metric: PerformanceMetric):
        """记录性能指标"""
        with self._lock:
            self.metrics[metric.name].append(metric)
    
    def record_system_stats(self, stats: SystemStats):
        """记录系统统计信息"""
        with self._lock:
            self.system_stats_history.append((time.time(), stats))
    
    def get_metric_stats(self, metric_name: str, duration_seconds: int = 3600) -> Dict[str, Any]:
        """获取指标统计信息"""
        with self._lock:
            metrics = self.metrics.get(metric_name, deque())
            if not metrics:
                return {}
            
            # 筛选时间范围内的指标
            cutoff_time = time.time() - duration_seconds
            recent_metrics = [m for m in metrics if m.timestamp > cutoff_time]
            
            if not recent_metrics:
                return {}
            
            values = [m.value for m in recent_metrics]
            return {
                "count": len(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "p50": sorted(values)[len(values)//2],
                "p95": sorted(values)[int(len(values)*0.95)],
                "p99": sorted(values)[int(len(values)*0.99)],
                "latest": values[-1],
                "unit": recent_metrics[-1].unit
            }
    
    def get_all_metrics_summary(self) -> Dict[str, Any]:
        """获取所有指标汇总"""
        summary = {}
        with self._lock:
            for metric_name in self.metrics.keys():
                summary[metric_name] = self.get_metric_stats(metric_name)
        return summary

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.network_counters_baseline = psutil.net_io_counters()
    
    def collect_system_stats(self) -> SystemStats:
        """收集系统统计信息"""
        try:
            # CPU和内存信息
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            
            # 网络统计
            net_io = psutil.net_io_counters()
            
            # 进程信息
            process_count = len(psutil.pids())
            
            # 当前进程信息
            thread_count = self.process.num_threads()
            try:
                open_files = self.process.num_fds()  # Linux/Mac
            except AttributeError:
                open_files = len(self.process.open_files())  # Windows
            
            return SystemStats(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / 1024 / 1024,
                memory_available_mb=memory.available / 1024 / 1024,
                disk_usage_percent=disk.percent,
                network_bytes_sent=net_io.bytes_sent - self.network_counters_baseline.bytes_sent,
                network_bytes_recv=net_io.bytes_recv - self.network_counters_baseline.bytes_recv,
                process_count=process_count,
                thread_count=thread_count,
                open_files=open_files
            )
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"收集系统统计信息失败: {e}")
            return SystemStats(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

class PerformanceTimer:
    """性能计时器"""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.active_timers: Dict[str, float] = {}
    
    @contextmanager
    def measure(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        """测量操作耗时的上下文管理器"""
        start_time = time.time()
        timer_id = f"{operation_name}_{id(threading.current_thread())}"
        self.active_timers[timer_id] = start_time
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            
            metric = PerformanceMetric(
                name=f"{operation_name}_duration",
                value=duration,
                timestamp=time.time(),
                unit="seconds",
                tags=tags or {}
            )
            
            self.collector.record_metric(metric)
            
            if timer_id in self.active_timers:
                del self.active_timers[timer_id]
    
    async def measure_async(self, operation_name: str, coro, tags: Optional[Dict[str, str]] = None):
        """测量异步操作耗时"""
        start_time = time.time()
        
        try:
            result = await coro
            return result
        finally:
            duration = time.time() - start_time
            
            metric = PerformanceMetric(
                name=f"{operation_name}_duration",
                value=duration,
                timestamp=time.time(),
                unit="seconds",
                tags=tags or {}
            )
            
            self.collector.record_metric(metric)

class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
    
    def analyze_bottlenecks(self) -> List[Dict[str, Any]]:
        """分析性能瓶颈"""
        bottlenecks = []
        
        # 分析响应时间
        duration_metrics = {
            name: stats for name, stats in self.collector.get_all_metrics_summary().items()
            if name.endswith('_duration') and stats
        }
        
        for metric_name, stats in duration_metrics.items():
            # 识别慢操作
            if stats['p95'] > 5.0:  # P95超过5秒
                bottlenecks.append({
                    "type": "slow_operation",
                    "metric": metric_name,
                    "p95": stats['p95'],
                    "avg": stats['avg'],
                    "severity": "high" if stats['p95'] > 10.0 else "medium"
                })
            
            # 识别响应时间不稳定的操作
            if stats['max'] > stats['avg'] * 5:  # 最大值是平均值的5倍以上
                bottlenecks.append({
                    "type": "unstable_performance",
                    "metric": metric_name,
                    "max": stats['max'],
                    "avg": stats['avg'],
                    "severity": "medium"
                })
        
        return bottlenecks
    
    def get_performance_score(self) -> float:
        """计算性能得分 (0-100)"""
        scores = []
        
        # 响应时间得分
        duration_metrics = {
            name: stats for name, stats in self.collector.get_all_metrics_summary().items()
            if name.endswith('_duration') and stats
        }
        
        for stats in duration_metrics.values():
            if stats['p95'] < 1.0:
                scores.append(95)
            elif stats['p95'] < 3.0:
                scores.append(80)
            elif stats['p95'] < 5.0:
                scores.append(60)
            else:
                scores.append(30)
        
        # 系统资源得分
        if self.collector.system_stats_history:
            latest_stats = self.collector.system_stats_history[-1][1]
            
            # CPU得分
            if latest_stats.cpu_percent < 50:
                cpu_score = 95
            elif latest_stats.cpu_percent < 80:
                cpu_score = 70
            else:
                cpu_score = 30
            scores.append(cpu_score)
            
            # 内存得分
            if latest_stats.memory_percent < 60:
                memory_score = 95
            elif latest_stats.memory_percent < 85:
                memory_score = 70
            else:
                memory_score = 30
            scores.append(memory_score)
        
        return sum(scores) / len(scores) if scores else 50.0

class PerformanceReporter:
    """性能报告生成器"""
    
    def __init__(self, collector: MetricsCollector, analyzer: PerformanceAnalyzer):
        self.collector = collector
        self.analyzer = analyzer
    
    def generate_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        bottlenecks = self.analyzer.analyze_bottlenecks()
        performance_score = self.analyzer.get_performance_score()
        
        # 系统资源统计
        system_summary = {}
        if self.collector.system_stats_history:
            recent_stats = [stats for _, stats in self.collector.system_stats_history[-60:]]  # 最近60个数据点
            if recent_stats:
                system_summary = {
                    "avg_cpu_percent": sum(s.cpu_percent for s in recent_stats) / len(recent_stats),
                    "avg_memory_percent": sum(s.memory_percent for s in recent_stats) / len(recent_stats),
                    "avg_memory_used_mb": sum(s.memory_used_mb for s in recent_stats) / len(recent_stats),
                    "thread_count": recent_stats[-1].thread_count,
                    "open_files": recent_stats[-1].open_files
                }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "performance_score": round(performance_score, 1),
            "bottlenecks": bottlenecks,
            "system_resources": system_summary,
            "metrics_summary": self.collector.get_all_metrics_summary(),
            "recommendations": self._generate_recommendations(bottlenecks, performance_score)
        }
    
    def _generate_recommendations(self, bottlenecks: List[Dict], performance_score: float) -> List[str]:
        """生成性能优化建议"""
        recommendations = []
        
        if performance_score < 60:
            recommendations.append("整体性能较差，建议进行全面优化")
        
        for bottleneck in bottlenecks:
            if bottleneck["type"] == "slow_operation":
                recommendations.append(f"优化 {bottleneck['metric']} 操作，当前P95响应时间: {bottleneck['p95']:.2f}秒")
            
            elif bottleneck["type"] == "unstable_performance":
                recommendations.append(f"稳定 {bottleneck['metric']} 性能，响应时间波动较大")
        
        if len(recommendations) == 0:
            recommendations.append("系统性能良好，继续保持")
        
        return recommendations

class PerformanceMonitor:
    """主性能监控器"""
    
    def __init__(self, collection_interval: float = 10.0):
        self.collection_interval = collection_interval
        self.collector = MetricsCollector()
        self.system_monitor = SystemMonitor()
        self.timer = PerformanceTimer(self.collector)
        self.analyzer = PerformanceAnalyzer(self.collector)
        self.reporter = PerformanceReporter(self.collector, self.analyzer)
        
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        logger.bind(tag=TAG).info(f"性能监控器初始化完成，采集间隔: {collection_interval}秒")
    
    def start_monitoring(self):
        """开始监控"""
        if self._monitoring:
            return
        
        self._monitoring = True
        
        # 🔧 修复：在线程池中启动监控，避免事件循环冲突
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._monitor_task = loop.create_task(self._monitoring_loop())
                logger.bind(tag=TAG).info("性能监控已启动（事件循环中）")
            else:
                logger.bind(tag=TAG).warning("事件循环未运行，跳过性能监控启动")
                self._monitoring = False
        except RuntimeError:
            # 如果没有事件循环，使用线程方式启动
            logger.bind(tag=TAG).info("没有事件循环，使用线程方式启动性能监控")
            import threading
            monitor_thread = threading.Thread(target=self._start_monitoring_in_thread, daemon=True)
            monitor_thread.start()
            logger.bind(tag=TAG).info("性能监控已启动（线程模式）")
    
    def _start_monitoring_in_thread(self):
        """在独立线程中启动监控（同步版本）"""
        import time
        
        while self._monitoring:
            try:
                # 收集系统统计信息
                stats = self.system_monitor.collect_system_stats()
                self.collector.record_system_stats(stats)
                
                # 记录垃圾回收统计
                import gc
                gc_stats = gc.get_stats()
                if gc_stats:
                    self.record_metric("gc_collections", sum(stat['collections'] for stat in gc_stats))
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                logger.bind(tag=TAG).error(f"线程监控循环错误: {e}")
                time.sleep(1)
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
        
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        
        logger.bind(tag=TAG).info("性能监控已停止")
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self._monitoring:
            try:
                # 收集系统统计信息
                stats = self.system_monitor.collect_system_stats()
                self.collector.record_system_stats(stats)
                
                # 记录垃圾回收统计
                gc_stats = gc.get_stats()
                if gc_stats:
                    self.record_metric("gc_collections", sum(stat['collections'] for stat in gc_stats))
                
                await asyncio.sleep(self.collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.bind(tag=TAG).error(f"监控循环错误: {e}")
                await asyncio.sleep(1)
    
    def record_metric(self, name: str, value: float, unit: str = "", tags: Optional[Dict[str, str]] = None):
        """记录自定义指标"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=time.time(),
            unit=unit,
            tags=tags or {}
        )
        self.collector.record_metric(metric)
    
    def measure_operation(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        """测量操作耗时的装饰器/上下文管理器"""
        return self.timer.measure(operation_name, tags)
    
    async def measure_async_operation(self, operation_name: str, coro, tags: Optional[Dict[str, str]] = None):
        """测量异步操作耗时"""
        return await self.timer.measure_async(operation_name, coro, tags)
    
    def get_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return self.reporter.generate_report()
    
    def get_health_status(self) -> str:
        """获取健康状态"""
        score = self.analyzer.get_performance_score()
        
        if score >= 80:
            return "healthy"
        elif score >= 60:
            return "warning"
        else:
            return "unhealthy"

# 全局性能监控器实例
_global_performance_monitor: Optional[PerformanceMonitor] = None

def get_performance_monitor(auto_start: bool = False) -> PerformanceMonitor:
    """获取全局性能监控器"""
    global _global_performance_monitor
    
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor()
        
        # 🔧 修复：只在明确要求时自动启动监控
        if auto_start:
            _global_performance_monitor.start_monitoring()
        else:
            logger.bind(tag=TAG).info("性能监控器已创建，未自动启动（使用 auto_start=True 启动）")
    
    return _global_performance_monitor

# 便捷装饰器
def monitor_performance(operation_name: str, tags: Optional[Dict[str, str]] = None):
    """性能监控装饰器"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                monitor = get_performance_monitor()
                return await monitor.measure_async_operation(
                    operation_name, 
                    func(*args, **kwargs), 
                    tags
                )
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                monitor = get_performance_monitor()
                with monitor.measure_operation(operation_name, tags):
                    return func(*args, **kwargs)
            return sync_wrapper
    
    return decorator

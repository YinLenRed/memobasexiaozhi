#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket音频传输性能监控器
监控预缓冲优化效果和传输性能指标
"""

import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import deque
import json


@dataclass
class AudioTransmissionMetrics:
    """音频传输性能指标"""
    device_id: str
    track_id: str
    total_frames: int
    audio_duration: float  # 音频时长(秒)
    
    # 时间指标
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    transmission_time: Optional[float] = None
    
    # 预缓冲指标
    prebuffer_frames: int = 0
    prebuffer_time: Optional[float] = None
    
    # 传输指标
    sent_frames: int = 0
    failed_frames: int = 0
    avg_frame_rate: Optional[float] = None
    
    # 优化效果
    optimization_ratio: Optional[float] = None  # 传输时间/播放时间
    speed_improvement: Optional[float] = None  # 相比标准传输的提升
    
    def finish_transmission(self):
        """完成传输，计算最终指标"""
        self.end_time = time.perf_counter()
        self.transmission_time = (self.end_time - self.start_time) * 1000  # ms
        
        if self.transmission_time > 0:
            self.avg_frame_rate = self.sent_frames / (self.transmission_time / 1000)
            
        if self.audio_duration > 0:
            theoretical_time = self.audio_duration * 1000  # ms
            self.optimization_ratio = self.transmission_time / theoretical_time
            
            # 计算相比60ms标准间隔的提升
            standard_transmission_time = self.total_frames * 60  # ms
            if standard_transmission_time > 0:
                self.speed_improvement = standard_transmission_time / self.transmission_time


class WebSocketPerformanceMonitor:
    """WebSocket音频传输性能监控器"""
    
    def __init__(self, max_history=100):
        self.max_history = max_history
        self.current_transmissions: Dict[str, AudioTransmissionMetrics] = {}
        self.completed_transmissions = deque(maxlen=max_history)
        self._lock = threading.Lock()
        
    def start_transmission(self, device_id: str, track_id: str, total_frames: int, 
                          audio_duration: float) -> AudioTransmissionMetrics:
        """开始传输监控"""
        with self._lock:
            metrics = AudioTransmissionMetrics(
                device_id=device_id,
                track_id=track_id,
                total_frames=total_frames,
                audio_duration=audio_duration
            )
            self.current_transmissions[track_id] = metrics
            return metrics
    
    def update_prebuffer(self, track_id: str, prebuffer_frames: int, prebuffer_time: float):
        """更新预缓冲指标"""
        with self._lock:
            if track_id in self.current_transmissions:
                metrics = self.current_transmissions[track_id]
                metrics.prebuffer_frames = prebuffer_frames
                metrics.prebuffer_time = prebuffer_time
    
    def update_progress(self, track_id: str, sent_frames: int, failed_frames: int = 0):
        """更新传输进度"""
        with self._lock:
            if track_id in self.current_transmissions:
                metrics = self.current_transmissions[track_id]
                metrics.sent_frames = sent_frames
                metrics.failed_frames = failed_frames
    
    def finish_transmission(self, track_id: str) -> Optional[AudioTransmissionMetrics]:
        """完成传输监控"""
        with self._lock:
            if track_id in self.current_transmissions:
                metrics = self.current_transmissions.pop(track_id)
                metrics.finish_transmission()
                self.completed_transmissions.append(metrics)
                return metrics
        return None
    
    def get_current_stats(self) -> Dict:
        """获取当前传输统计"""
        with self._lock:
            return {
                'active_transmissions': len(self.current_transmissions),
                'completed_count': len(self.completed_transmissions),
                'current_devices': list({m.device_id for m in self.current_transmissions.values()})
            }
    
    def get_performance_summary(self, last_n: int = 10) -> Dict:
        """获取性能摘要"""
        with self._lock:
            if not self.completed_transmissions:
                return {'status': 'no_data', 'message': '暂无传输数据'}
            
            recent = list(self.completed_transmissions)[-last_n:]
            
            # 计算平均性能指标
            avg_transmission_time = sum(m.transmission_time for m in recent if m.transmission_time) / len(recent)
            avg_frame_rate = sum(m.avg_frame_rate for m in recent if m.avg_frame_rate) / len(recent)
            avg_optimization_ratio = sum(m.optimization_ratio for m in recent if m.optimization_ratio) / len(recent)
            avg_speed_improvement = sum(m.speed_improvement for m in recent if m.speed_improvement) / len(recent)
            
            # 成功率统计
            total_frames = sum(m.total_frames for m in recent)
            sent_frames = sum(m.sent_frames for m in recent)
            success_rate = (sent_frames / total_frames * 100) if total_frames > 0 else 0
            
            return {
                'status': 'success',
                'sample_size': len(recent),
                'avg_transmission_time_ms': round(avg_transmission_time, 2),
                'avg_frame_rate': round(avg_frame_rate, 2),
                'avg_optimization_ratio': round(avg_optimization_ratio, 3),
                'avg_speed_improvement': round(avg_speed_improvement, 2),
                'success_rate_percent': round(success_rate, 2),
                'best_optimization': min(m.optimization_ratio for m in recent if m.optimization_ratio),
                'worst_optimization': max(m.optimization_ratio for m in recent if m.optimization_ratio)
            }
    
    def get_detailed_report(self, device_id: str = None) -> List[Dict]:
        """获取详细报告"""
        with self._lock:
            transmissions = self.completed_transmissions
            if device_id:
                transmissions = [m for m in transmissions if m.device_id == device_id]
            
            return [{
                'device_id': m.device_id,
                'track_id': m.track_id,
                'total_frames': m.total_frames,
                'audio_duration': m.audio_duration,
                'transmission_time_ms': m.transmission_time,
                'prebuffer_frames': m.prebuffer_frames,
                'prebuffer_time_ms': m.prebuffer_time,
                'sent_frames': m.sent_frames,
                'failed_frames': m.failed_frames,
                'success_rate': (m.sent_frames / m.total_frames * 100) if m.total_frames > 0 else 0,
                'avg_frame_rate': m.avg_frame_rate,
                'optimization_ratio': m.optimization_ratio,
                'speed_improvement': m.speed_improvement,
                'timestamp': m.start_time
            } for m in transmissions]


# 全局性能监控器实例
_global_monitor = None


def get_performance_monitor() -> WebSocketPerformanceMonitor:
    """获取全局性能监控器"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = WebSocketPerformanceMonitor()
    return _global_monitor


def log_optimization_result(logger, metrics: AudioTransmissionMetrics):
    """记录优化结果日志"""
    if not metrics or not metrics.transmission_time:
        return
        
    status = "🚀 优秀" if metrics.optimization_ratio < 0.3 else \
             "✅ 良好" if metrics.optimization_ratio < 0.6 else \
             "⚠️ 一般" if metrics.optimization_ratio < 1.0 else \
             "❌ 需优化"
    
    logger.info(
        f"{status} WebSocket预缓冲优化结果: "
        f"设备={metrics.device_id}, "
        f"传输={metrics.transmission_time:.1f}ms, "
        f"帧率={metrics.avg_frame_rate:.1f}帧/s, "
        f"优化比例={metrics.optimization_ratio:.3f}x, "
        f"提升={metrics.speed_improvement:.2f}x, "
        f"成功率={(metrics.sent_frames/metrics.total_frames*100):.1f}%"
    )

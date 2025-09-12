#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频缓冲区管理器
防止音频数据无限累积导致内存泄漏
"""

import time
from collections import deque
from typing import List, Optional
from loguru import logger

TAG = "AudioBufferManager"

class AudioBufferManager:
    """音频缓冲区管理器 - 防止内存泄漏"""
    
    def __init__(self, max_size: int = 1000, max_total_size: int = 10 * 1024 * 1024):
        """
        初始化音频缓冲区管理器
        
        Args:
            max_size: 最大音频块数量
            max_total_size: 最大总字节数 (默认10MB)
        """
        self.max_size = max_size
        self.max_total_size = max_total_size
        
        # 使用deque实现高效的FIFO队列
        self.buffer = deque(maxlen=max_size)
        self.voiceprint_buffer = deque(maxlen=max_size // 2)  # 声纹缓冲区较小
        
        # 统计信息
        self.total_size = 0
        self.voiceprint_size = 0
        self.dropped_chunks = 0
        self.last_cleanup_time = time.time()
        
        logger.bind(tag=TAG).info(f"音频缓冲区管理器初始化: 最大{max_size}块, {max_total_size//1024//1024}MB")
    
    def add_audio(self, audio_data: bytes) -> bool:
        """
        添加音频数据到主缓冲区
        
        Args:
            audio_data: 音频字节数据
            
        Returns:
            bool: 是否成功添加
        """
        if not audio_data:
            return False
        
        data_size = len(audio_data)
        
        # 检查是否需要清理
        if self.total_size + data_size > self.max_total_size:
            self._cleanup_old_audio()
        
        # 如果缓冲区满了，旧数据会自动被移除
        if len(self.buffer) >= self.max_size:
            old_audio = self.buffer[0] if self.buffer else None
            if old_audio:
                self.total_size -= len(old_audio)
                self.dropped_chunks += 1
        
        self.buffer.append(audio_data)
        self.total_size += data_size
        
        return True
    
    def add_voiceprint_audio(self, audio_data: bytes) -> bool:
        """
        添加音频数据到声纹缓冲区
        
        Args:
            audio_data: 音频字节数据
            
        Returns:
            bool: 是否成功添加
        """
        if not audio_data:
            return False
        
        data_size = len(audio_data)
        
        # 声纹缓冲区大小控制
        if self.voiceprint_size + data_size > self.max_total_size // 4:  # 声纹最多使用1/4内存
            self._cleanup_voiceprint_audio()
        
        # 如果缓冲区满了，旧数据会自动被移除
        if len(self.voiceprint_buffer) >= self.voiceprint_buffer.maxlen:
            old_audio = self.voiceprint_buffer[0] if self.voiceprint_buffer else None
            if old_audio:
                self.voiceprint_size -= len(old_audio)
        
        self.voiceprint_buffer.append(audio_data)
        self.voiceprint_size += data_size
        
        return True
    
    def get_audio_list(self) -> List[bytes]:
        """获取主音频缓冲区的列表形式（兼容现有接口）"""
        return list(self.buffer)
    
    def get_voiceprint_list(self) -> List[bytes]:
        """获取声纹音频缓冲区的列表形式（兼容现有接口）"""
        return list(self.voiceprint_buffer)
    
    def clear(self):
        """清空所有缓冲区"""
        self.buffer.clear()
        self.voiceprint_buffer.clear()
        self.total_size = 0
        self.voiceprint_size = 0
        logger.bind(tag=TAG).debug("音频缓冲区已清空")
    
    def _cleanup_old_audio(self):
        """清理旧的音频数据"""
        target_size = int(self.max_total_size * 0.7)  # 清理到70%
        
        while self.buffer and self.total_size > target_size:
            old_audio = self.buffer.popleft()
            self.total_size -= len(old_audio)
            self.dropped_chunks += 1
        
        self.last_cleanup_time = time.time()
        logger.bind(tag=TAG).debug(f"清理音频缓冲区: 剩余{len(self.buffer)}块, {self.total_size//1024}KB")
    
    def _cleanup_voiceprint_audio(self):
        """清理声纹音频数据"""
        target_size = int(self.max_total_size // 4 * 0.7)  # 清理到70%
        
        while self.voiceprint_buffer and self.voiceprint_size > target_size:
            old_audio = self.voiceprint_buffer.popleft()
            self.voiceprint_size -= len(old_audio)
        
        logger.bind(tag=TAG).debug(f"清理声纹缓冲区: 剩余{len(self.voiceprint_buffer)}块")
    
    def get_stats(self) -> dict:
        """获取缓冲区统计信息"""
        return {
            "audio_chunks": len(self.buffer),
            "voiceprint_chunks": len(self.voiceprint_buffer),
            "total_size_mb": round(self.total_size / 1024 / 1024, 2),
            "voiceprint_size_mb": round(self.voiceprint_size / 1024 / 1024, 2),
            "dropped_chunks": self.dropped_chunks,
            "max_size": self.max_size,
            "max_total_size_mb": round(self.max_total_size / 1024 / 1024, 2),
            "memory_usage_percent": round((self.total_size / self.max_total_size) * 100, 1)
        }

class ConnectionAudioManager:
    """连接级别的音频管理器 - 为每个连接提供独立的音频缓冲区"""
    
    def __init__(self, conn):
        self.conn = conn
        self.buffer_manager = AudioBufferManager()
        
        # 初始化连接的音频属性
        if not hasattr(conn, 'asr_audio'):
            conn.asr_audio = []
        if not hasattr(conn, 'asr_audio_for_voiceprint'):
            conn.asr_audio_for_voiceprint = []
    
    def add_audio(self, audio_data: bytes):
        """添加音频数据"""
        success = self.buffer_manager.add_audio(audio_data)
        if success:
            # 同步更新连接的音频列表（向后兼容）
            self.conn.asr_audio = self.buffer_manager.get_audio_list()
    
    def add_voiceprint_audio(self, audio_data: bytes):
        """添加声纹音频数据"""
        success = self.buffer_manager.add_voiceprint_audio(audio_data)
        if success:
            # 同步更新连接的声纹音频列表（向后兼容）
            self.conn.asr_audio_for_voiceprint = self.buffer_manager.get_voiceprint_list()
    
    def clear(self):
        """清空音频缓冲区"""
        self.buffer_manager.clear()
        self.conn.asr_audio = []
        self.conn.asr_audio_for_voiceprint = []
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.buffer_manager.get_stats()


def get_or_create_audio_manager(conn) -> ConnectionAudioManager:
    """获取或创建连接的音频管理器"""
    if not hasattr(conn, '_audio_manager'):
        conn._audio_manager = ConnectionAudioManager(conn)
    return conn._audio_manager

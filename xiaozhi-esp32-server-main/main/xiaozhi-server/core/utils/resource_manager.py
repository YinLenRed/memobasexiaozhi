#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一资源管理器
确保所有资源都能正确清理，防止内存泄漏和连接泄漏
"""

import asyncio
import time
import weakref
from typing import Dict, List, Callable, Any, Optional
from loguru import logger

TAG = "ResourceManager"

class ResourceManager:
    """统一资源管理器 - 确保所有资源正确清理"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._resources: List[tuple] = []  # (resource, cleanup_func, resource_type)
        self._cleanup_callbacks: List[Callable] = []
        self._closed = False
        self._cleanup_timeout = 10.0  # 清理超时时间
        
        logger.bind(tag=TAG).debug(f"资源管理器初始化: {name}")
    
    def register_resource(self, resource: Any, cleanup_func: Callable, resource_type: str = "unknown"):
        """
        注册需要清理的资源
        
        Args:
            resource: 资源对象
            cleanup_func: 清理函数（可以是同步或异步）
            resource_type: 资源类型（用于日志）
        """
        if self._closed:
            logger.bind(tag=TAG).warning(f"资源管理器已关闭，无法注册新资源: {resource_type}")
            return
        
        self._resources.append((resource, cleanup_func, resource_type))
        logger.bind(tag=TAG).debug(f"注册资源: {resource_type} (总计{len(self._resources)}个)")
    
    def register_callback(self, callback: Callable):
        """注册清理回调函数"""
        if self._closed:
            return
        self._cleanup_callbacks.append(callback)
    
    async def cleanup_all(self) -> bool:
        """
        清理所有资源
        
        Returns:
            bool: 是否所有资源都成功清理
        """
        if self._closed:
            logger.bind(tag=TAG).debug(f"资源管理器 {self.name} 已经清理过")
            return True
        
        self._closed = True
        logger.bind(tag=TAG).info(f"开始清理资源管理器 {self.name}: {len(self._resources)}个资源")
        
        success_count = 0
        total_count = len(self._resources)
        
        # 并行清理所有资源
        cleanup_tasks = []
        for resource, cleanup_func, resource_type in self._resources:
            task = self._safe_cleanup_resource(resource, cleanup_func, resource_type)
            cleanup_tasks.append(task)
        
        if cleanup_tasks:
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*cleanup_tasks, return_exceptions=True),
                    timeout=self._cleanup_timeout
                )
                success_count = sum(1 for result in results if result is True)
            except asyncio.TimeoutError:
                logger.bind(tag=TAG).error(f"资源清理超时: {self._cleanup_timeout}秒")
        
        # 执行清理回调
        for callback in self._cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.bind(tag=TAG).error(f"清理回调执行失败: {e}")
        
        logger.bind(tag=TAG).info(f"资源清理完成: {success_count}/{total_count}")
        return success_count == total_count
    
    async def _safe_cleanup_resource(self, resource: Any, cleanup_func: Callable, resource_type: str) -> bool:
        """安全清理单个资源"""
        try:
            if resource is None:
                return True
            
            # 检查资源是否还有效
            if hasattr(resource, 'closed') and resource.closed:
                logger.bind(tag=TAG).debug(f"{resource_type} 已经关闭")
                return True
            
            # 执行清理函数
            if asyncio.iscoroutinefunction(cleanup_func):
                await cleanup_func()
            else:
                cleanup_func()
            
            logger.bind(tag=TAG).debug(f"✅ {resource_type} 清理成功")
            return True
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"❌ {resource_type} 清理失败: {e}")
            return False
    
    def is_closed(self) -> bool:
        """检查资源管理器是否已关闭"""
        return self._closed
    
    def get_resource_count(self) -> int:
        """获取注册的资源数量"""
        return len(self._resources)


class ConnectionResourceManager:
    """连接级别的资源管理器"""
    
    def __init__(self, conn):
        self.conn = conn
        self.resource_manager = ResourceManager(f"Connection-{getattr(conn, 'device_id', 'unknown')}")
        self._setup_standard_resources()
    
    def _setup_standard_resources(self):
        """设置标准的连接资源"""
        conn = self.conn
        
        # WebSocket连接
        if hasattr(conn, 'websocket') and conn.websocket:
            self.resource_manager.register_resource(
                conn.websocket,
                lambda: self._close_websocket(conn.websocket),
                "WebSocket"
            )
        
        # ASR连接
        if hasattr(conn, 'asr') and conn.asr:
            self.resource_manager.register_resource(
                conn.asr,
                conn.asr.close,
                "ASR"
            )
        
        # TTS连接
        if hasattr(conn, 'tts') and conn.tts:
            self.resource_manager.register_resource(
                conn.tts,
                conn.tts.close,
                "TTS"
            )
        
        # 定时器任务
        if hasattr(conn, 'timeout_task') and conn.timeout_task:
            self.resource_manager.register_resource(
                conn.timeout_task,
                lambda: self._cancel_task(conn.timeout_task),
                "TimeoutTask"
            )
        
        # 音频缓冲区
        if hasattr(conn, '_audio_manager'):
            self.resource_manager.register_resource(
                conn._audio_manager,
                conn._audio_manager.clear,
                "AudioManager"
            )
        
        # 工具处理器
        if hasattr(conn, 'func_handler') and conn.func_handler:
            self.resource_manager.register_resource(
                conn.func_handler,
                conn.func_handler.cleanup,
                "FuncHandler"
            )
    
    async def _close_websocket(self, ws):
        """安全关闭WebSocket"""
        if ws and hasattr(ws, 'close'):
            try:
                if not (hasattr(ws, 'closed') and ws.closed):
                    await asyncio.wait_for(ws.close(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.bind(tag=TAG).warning("WebSocket关闭超时")
            except Exception as e:
                logger.bind(tag=TAG).debug(f"WebSocket关闭异常（忽略）: {e}")
    
    async def _cancel_task(self, task):
        """安全取消异步任务"""
        if task and not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.bind(tag=TAG).debug(f"任务取消异常（忽略）: {e}")
    
    async def cleanup(self) -> bool:
        """清理连接的所有资源"""
        return await self.resource_manager.cleanup_all()
    
    def register_resource(self, resource: Any, cleanup_func: Callable, resource_type: str = "custom"):
        """注册额外资源"""
        self.resource_manager.register_resource(resource, cleanup_func, resource_type)


def get_or_create_resource_manager(conn) -> ConnectionResourceManager:
    """获取或创建连接的资源管理器"""
    if not hasattr(conn, '_resource_manager'):
        conn._resource_manager = ConnectionResourceManager(conn)
    return conn._resource_manager


class GlobalResourceTracker:
    """全局资源跟踪器 - 跟踪所有活跃资源"""
    
    def __init__(self):
        self._active_managers: Dict[str, weakref.ref] = {}
        self._stats = {
            'created': 0,
            'cleaned': 0,
            'leaked': 0,
            'last_cleanup': 0
        }
    
    def register_manager(self, manager: ResourceManager):
        """注册资源管理器"""
        manager_id = f"{manager.name}-{id(manager)}"
        self._active_managers[manager_id] = weakref.ref(manager, self._on_manager_deleted)
        self._stats['created'] += 1
    
    def _on_manager_deleted(self, ref):
        """资源管理器被垃圾回收时的回调"""
        # 从活跃列表中移除
        to_remove = []
        for manager_id, manager_ref in self._active_managers.items():
            if manager_ref is ref:
                to_remove.append(manager_id)
        
        for manager_id in to_remove:
            del self._active_managers[manager_id]
    
    def get_active_count(self) -> int:
        """获取活跃的资源管理器数量"""
        # 清理已经被垃圾回收的引用
        self._cleanup_dead_refs()
        return len(self._active_managers)
    
    def _cleanup_dead_refs(self):
        """清理死亡的弱引用"""
        to_remove = []
        for manager_id, manager_ref in self._active_managers.items():
            if manager_ref() is None:
                to_remove.append(manager_id)
        
        for manager_id in to_remove:
            del self._active_managers[manager_id]
    
    async def cleanup_all_active(self):
        """清理所有活跃的资源管理器"""
        self._cleanup_dead_refs()
        
        cleanup_tasks = []
        for manager_ref in self._active_managers.values():
            manager = manager_ref()
            if manager and not manager.is_closed():
                cleanup_tasks.append(manager.cleanup_all())
        
        if cleanup_tasks:
            results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            self._stats['cleaned'] += sum(1 for r in results if r is True)
            self._stats['leaked'] += sum(1 for r in results if r is not True)
        
        self._stats['last_cleanup'] = time.time()
    
    def get_stats(self) -> dict:
        """获取资源统计信息"""
        return {
            **self._stats,
            'active': self.get_active_count()
        }

# 全局资源跟踪器实例
global_resource_tracker = GlobalResourceTracker()

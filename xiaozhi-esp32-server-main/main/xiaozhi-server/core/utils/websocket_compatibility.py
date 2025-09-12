#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket服务器兼容性补丁
解决硬件客户端HTTP协议兼容性问题
"""

import asyncio
import websockets
from websockets import server
from websockets.http11 import Request
import logging

logger = logging.getLogger(__name__)

class CompatibleWebSocketServer:
    """兼容硬件客户端的WebSocket服务器"""
    
    def __init__(self, host="0.0.0.0", port=8000):
        self.host = host
        self.port = port
        self.server = None
        
    async def handle_connection(self, websocket, path):
        """处理WebSocket连接"""
        try:
            logger.info(f"WebSocket连接: {websocket.remote_address} -> {path}")
            
            # 这里可以添加音频数据发送逻辑
            await websocket.send("音频数据流")
            
            # 保持连接
            async for message in websocket:
                logger.info(f"收到消息: {message}")
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket连接关闭")
        except Exception as e:
            logger.error(f"WebSocket处理异常: {e}")
    
    async def custom_process_request(self, path, request_headers):
        """自定义请求处理，增强兼容性"""
        logger.info(f"WebSocket请求: {path}")
        logger.info(f"请求头: {dict(request_headers)}")
        
        # 允许所有来源
        return None
    
    async def start_server(self):
        """启动兼容性WebSocket服务器"""
        try:
            # 创建服务器，增加兼容性选项
            self.server = await websockets.serve(
                self.handle_connection,
                self.host,
                self.port,
                process_request=self.custom_process_request,
                # 增强兼容性选项
                compression=None,  # 禁用压缩
                max_size=2**20,    # 1MB最大消息大小
                max_queue=32,      # 消息队列大小
                read_limit=2**16,  # 读取缓冲区
                write_limit=2**16, # 写入缓冲区
                ping_interval=None,  # 禁用ping
                ping_timeout=None,   # 禁用ping超时
                close_timeout=10,    # 关闭超时
            )
            
            logger.info(f"兼容性WebSocket服务器启动: {self.host}:{self.port}")
            return self.server
            
        except Exception as e:
            logger.error(f"WebSocket服务器启动失败: {e}")
            raise
    
    async def stop_server(self):
        """停止WebSocket服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket服务器已停止")

# 自定义HTTP请求解析器（更宽松的解析）
class CompatibleHTTPParser:
    """兼容的HTTP请求解析器"""
    
    @staticmethod
    def parse_request_line(line):
        """解析HTTP请求行，支持HTTP/1.0和非标准格式"""
        try:
            # 标准解析
            method, path, version = line.split(' ', 2)
            return method, path, version
        except ValueError:
            # 兼容性解析
            parts = line.split()
            if len(parts) >= 2:
                method = parts[0]
                path = parts[1] 
                version = parts[2] if len(parts) > 2 else "HTTP/1.0"
                return method, path, version
            else:
                raise ValueError(f"Invalid request line: {line}")

async def create_compatible_websocket_server(host="0.0.0.0", port=8000):
    """创建兼容性WebSocket服务器的便捷函数"""
    server = CompatibleWebSocketServer(host, port)
    return await server.start_server()

if __name__ == "__main__":
    # 测试兼容性WebSocket服务器
    async def main():
        logging.basicConfig(level=logging.INFO)
        server = await create_compatible_websocket_server("0.0.0.0", 8888)
        
        print("兼容性WebSocket服务器运行在 ws://0.0.0.0:8888")
        print("按Ctrl+C停止...")
        
        try:
            await server.wait_closed()
        except KeyboardInterrupt:
            print("停止服务器...")
            server.close()
            await server.wait_closed()
    
    asyncio.run(main())

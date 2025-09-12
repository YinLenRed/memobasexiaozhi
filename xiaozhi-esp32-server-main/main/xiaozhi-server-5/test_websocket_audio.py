#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket音频传输专项测试脚本
测试小智系统的WebSocket音频流传输功能
"""

import asyncio
import json
import logging
import time
import websockets
import wave
import io
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid
import sys
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('WebSocket_Audio_Test')

class WebSocketAudioTestConfig:
    """WebSocket音频测试配置"""
    
    # WebSocket配置
    WEBSOCKET_URL = "ws://47.98.51.180:8000/xiaozhi/v1/"
    
    # 设备配置
    TEST_DEVICE_ID = "f0:9e:9e:04:8a:44"
    CLIENT_ID = f"ws-audio-tester-{uuid.uuid4().hex[:8]}"
    
    # 超时配置
    CONNECTION_TIMEOUT = 10
    AUDIO_RECEIVE_TIMEOUT = 30
    HANDSHAKE_TIMEOUT = 5
    
    # 测试配置
    TEST_AUDIO_DURATION = 5  # 测试音频时长(秒)
    CONCURRENT_CONNECTIONS = 3
    SIMULATE_AUDIO_PLAYBACK = True

class AudioTestResult:
    """音频测试结果"""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = time.time()
        self.end_time = None
        self.success = False
        self.error_message = None
        self.metrics = {}
        
    def finish(self, success: bool, error_message: str = None, **metrics):
        self.end_time = time.time()
        self.success = success
        self.error_message = error_message
        self.metrics.update(metrics)
        
    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

class WebSocketAudioTester:
    """WebSocket音频传输测试器"""
    
    def __init__(self, config: WebSocketAudioTestConfig = None):
        self.config = config or WebSocketAudioTestConfig()
        
        # 连接管理
        self.active_connections = {}  # connection_id -> websocket
        self.connection_info = {}     # connection_id -> info
        
        # 音频数据跟踪
        self.received_audio_data = {}  # connection_id -> audio_chunks
        self.audio_statistics = {}     # connection_id -> stats
        
        # 测试结果
        self.test_results: List[AudioTestResult] = []
        
        # 创建测试音频数据目录
        self.test_data_dir = "test_audio_data"
        os.makedirs(self.test_data_dir, exist_ok=True)
    
    def create_test_headers(self, device_id: str = None, track_id: str = None) -> Dict[str, str]:
        """创建WebSocket连接头"""
        headers = {
            "Device-ID": device_id or self.config.TEST_DEVICE_ID,
            "Client-ID": self.config.CLIENT_ID,
            "User-Agent": "WebSocket-Audio-Tester/1.0"
        }
        
        if track_id:
            headers["Track-ID"] = track_id
            
        return headers
    
    async def test_basic_websocket_connection(self) -> AudioTestResult:
        """基础WebSocket连接测试"""
        result = AudioTestResult("基础WebSocket连接测试")
        
        try:
            logger.info("🧪 开始基础WebSocket连接测试...")
            
            headers = self.create_test_headers()
            
            async with websockets.connect(
                self.config.WEBSOCKET_URL,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                
                logger.info("✅ WebSocket连接建立成功")
                
                # 发送hello消息
                hello_message = {
                    "type": "hello",
                    "device_id": self.config.TEST_DEVICE_ID,
                    "client_id": self.config.CLIENT_ID,
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(hello_message))
                logger.info("📤 发送hello消息")
                
                # 等待响应
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=self.config.HANDSHAKE_TIMEOUT
                    )
                    
                    logger.info(f"📥 收到响应: {response}")
                    
                    result.finish(
                        success=True,
                        connection_url=self.config.WEBSOCKET_URL,
                        hello_sent=True,
                        response_received=True,
                        response_content=response[:100] if len(response) > 100 else response
                    )
                    
                except asyncio.TimeoutError:
                    logger.warning("⚠️  握手响应超时，但连接成功")
                    result.finish(
                        success=True,
                        connection_url=self.config.WEBSOCKET_URL,
                        hello_sent=True,
                        response_received=False,
                        timeout=True
                    )
                    
        except Exception as e:
            logger.error(f"❌ WebSocket连接测试失败: {e}")
            result.finish(success=False, error_message=str(e))
        
        self.test_results.append(result)
        return result
    
    async def test_audio_data_reception(self) -> AudioTestResult:
        """音频数据接收测试"""
        result = AudioTestResult("音频数据接收测试")
        
        try:
            logger.info("🧪 开始音频数据接收测试...")
            
            connection_id = f"audio_test_{int(time.time())}"
            headers = self.create_test_headers(track_id=connection_id)
            
            audio_chunks = []
            total_audio_size = 0
            text_messages = []
            connection_start_time = time.time()
            
            async with websockets.connect(
                self.config.WEBSOCKET_URL,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                
                logger.info("✅ WebSocket连接建立成功")
                
                # 发送hello消息并准备接收音频
                hello_message = {
                    "type": "hello",
                    "device_id": self.config.TEST_DEVICE_ID,
                    "ready_for_audio": True,
                    "supported_formats": ["PCM", "Opus", "MP3"],
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(hello_message))
                logger.info("📤 发送hello消息，准备接收音频")
                
                # 模拟等待音频数据
                receive_timeout = self.config.AUDIO_RECEIVE_TIMEOUT
                first_audio_time = None
                last_activity_time = time.time()
                
                try:
                    while time.time() - connection_start_time < receive_timeout:
                        try:
                            # 等待消息，设置短超时以便检查整体超时
                            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            last_activity_time = time.time()
                            
                            if isinstance(message, bytes):
                                # 二进制音频数据
                                if first_audio_time is None:
                                    first_audio_time = time.time()
                                
                                audio_chunks.append(message)
                                total_audio_size += len(message)
                                
                                logger.info(f"🎵 接收音频数据块 #{len(audio_chunks)}, 大小: {len(message)} 字节")
                                
                            else:
                                # 文本消息
                                try:
                                    text_msg = json.loads(message)
                                    text_messages.append(text_msg)
                                    logger.info(f"📥 接收文本消息: {text_msg}")
                                except json.JSONDecodeError:
                                    logger.info(f"📥 接收文本: {message[:100]}...")
                        
                        except asyncio.TimeoutError:
                            # 短超时，检查是否有音频数据或者总超时
                            if audio_chunks and time.time() - last_activity_time > 5:
                                # 有音频数据且5秒无新数据，认为传输完成
                                logger.info("🎵 音频传输完成（无新数据5秒）")
                                break
                            continue
                
                except websockets.exceptions.ConnectionClosed:
                    logger.info("🔌 WebSocket连接已关闭")
                
                # 保存接收到的音频数据
                if audio_chunks:
                    audio_file_path = os.path.join(
                        self.test_data_dir,
                        f"received_audio_{connection_id}.raw"
                    )
                    with open(audio_file_path, 'wb') as f:
                        for chunk in audio_chunks:
                            f.write(chunk)
                    
                    logger.info(f"💾 音频数据已保存到: {audio_file_path}")
                
                # 计算统计信息
                audio_duration = (last_activity_time - first_audio_time) if first_audio_time else 0
                avg_chunk_size = total_audio_size / len(audio_chunks) if audio_chunks else 0
                
                result.finish(
                    success=len(audio_chunks) > 0,
                    error_message="未接收到音频数据" if len(audio_chunks) == 0 else None,
                    connection_id=connection_id,
                    audio_chunks_received=len(audio_chunks),
                    total_audio_size_bytes=total_audio_size,
                    text_messages_received=len(text_messages),
                    audio_duration_seconds=audio_duration,
                    avg_chunk_size_bytes=avg_chunk_size,
                    connection_duration=time.time() - connection_start_time
                )
                
                if len(audio_chunks) > 0:
                    logger.info(f"✅ 音频接收测试成功，共接收{len(audio_chunks)}个音频块，总大小{total_audio_size}字节")
                else:
                    logger.warning("⚠️  未接收到音频数据")
                    
        except Exception as e:
            logger.error(f"❌ 音频数据接收测试异常: {e}")
            result.finish(success=False, error_message=str(e))
        
        self.test_results.append(result)
        return result
    
    async def test_concurrent_audio_streams(self) -> AudioTestResult:
        """并发音频流测试"""
        result = AudioTestResult("并发音频流测试")
        
        try:
            logger.info(f"🧪 开始并发音频流测试（{self.config.CONCURRENT_CONNECTIONS}个连接）...")
            
            # 创建多个并发连接
            connection_tasks = []
            for i in range(self.config.CONCURRENT_CONNECTIONS):
                task = asyncio.create_task(
                    self._single_audio_connection_test(f"concurrent_{i}")
                )
                connection_tasks.append(task)
            
            # 等待所有连接测试完成
            connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # 统计结果
            successful_connections = 0
            total_audio_received = 0
            errors = []
            
            for i, conn_result in enumerate(connection_results):
                if isinstance(conn_result, Exception):
                    errors.append(f"连接{i}: {str(conn_result)}")
                elif conn_result and conn_result.get('success', False):
                    successful_connections += 1
                    total_audio_received += conn_result.get('audio_chunks_received', 0)
                else:
                    errors.append(f"连接{i}: 音频接收失败")
            
            success_rate = successful_connections / self.config.CONCURRENT_CONNECTIONS * 100
            
            result.finish(
                success=success_rate >= 80,  # 80%成功率算通过
                concurrent_connections=self.config.CONCURRENT_CONNECTIONS,
                successful_connections=successful_connections,
                success_rate=success_rate,
                total_audio_chunks_received=total_audio_received,
                errors=errors
            )
            
            logger.info(f"✅ 并发测试完成，成功率: {success_rate:.1f}%")
            
        except Exception as e:
            logger.error(f"❌ 并发音频流测试异常: {e}")
            result.finish(success=False, error_message=str(e))
        
        self.test_results.append(result)
        return result
    
    async def _single_audio_connection_test(self, connection_id: str) -> Dict:
        """单个音频连接测试"""
        try:
            headers = self.create_test_headers(track_id=connection_id)
            
            audio_chunks = []
            start_time = time.time()
            
            async with websockets.connect(
                self.config.WEBSOCKET_URL,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                
                # 发送hello消息
                hello_message = {
                    "type": "hello",
                    "device_id": self.config.TEST_DEVICE_ID,
                    "connection_id": connection_id,
                    "ready_for_audio": True,
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send(json.dumps(hello_message))
                
                # 接收音频数据（简化版）
                timeout_time = start_time + 15  # 15秒超时
                
                while time.time() < timeout_time:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        
                        if isinstance(message, bytes):
                            audio_chunks.append(message)
                        
                        # 如果收到足够的数据就退出
                        if len(audio_chunks) >= 5:
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        break
            
            return {
                'success': len(audio_chunks) > 0,
                'connection_id': connection_id,
                'audio_chunks_received': len(audio_chunks),
                'total_size': sum(len(chunk) for chunk in audio_chunks),
                'duration': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"单个连接测试异常 {connection_id}: {e}")
            return {
                'success': False,
                'connection_id': connection_id,
                'error': str(e)
            }
    
    async def test_websocket_reconnection(self) -> AudioTestResult:
        """WebSocket重连测试"""
        result = AudioTestResult("WebSocket重连测试")
        
        try:
            logger.info("🧪 开始WebSocket重连测试...")
            
            reconnect_attempts = 3
            successful_reconnects = 0
            
            for attempt in range(reconnect_attempts):
                try:
                    headers = self.create_test_headers(track_id=f"reconnect_test_{attempt}")
                    
                    async with websockets.connect(
                        self.config.WEBSOCKET_URL,
                        extra_headers=headers,
                        ping_interval=20,
                        ping_timeout=10
                    ) as websocket:
                        
                        logger.info(f"✅ 重连尝试 {attempt + 1} 成功")
                        
                        # 发送测试消息
                        test_message = {
                            "type": "reconnect_test",
                            "attempt": attempt + 1,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        await websocket.send(json.dumps(test_message))
                        
                        # 短暂等待
                        await asyncio.sleep(1)
                        
                        successful_reconnects += 1
                
                except Exception as e:
                    logger.error(f"❌ 重连尝试 {attempt + 1} 失败: {e}")
                
                # 间隔2秒再次尝试
                if attempt < reconnect_attempts - 1:
                    await asyncio.sleep(2)
            
            success_rate = successful_reconnects / reconnect_attempts * 100
            
            result.finish(
                success=success_rate >= 80,
                reconnect_attempts=reconnect_attempts,
                successful_reconnects=successful_reconnects,
                success_rate=success_rate
            )
            
            logger.info(f"✅ 重连测试完成，成功率: {success_rate:.1f}%")
            
        except Exception as e:
            logger.error(f"❌ WebSocket重连测试异常: {e}")
            result.finish(success=False, error_message=str(e))
        
        self.test_results.append(result)
        return result
    
    async def test_audio_format_compatibility(self) -> AudioTestResult:
        """音频格式兼容性测试"""
        result = AudioTestResult("音频格式兼容性测试")
        
        try:
            logger.info("🧪 开始音频格式兼容性测试...")
            
            # 测试不同音频格式的支持
            supported_formats = []
            format_tests = [
                {"format": "PCM", "sample_rate": 16000, "channels": 1},
                {"format": "Opus", "bitrate": 64000},
                {"format": "MP3", "bitrate": 128000},
                {"format": "WAV", "sample_rate": 44100, "channels": 2}
            ]
            
            for fmt_test in format_tests:
                try:
                    headers = self.create_test_headers(
                        track_id=f"format_test_{fmt_test['format']}"
                    )
                    
                    async with websockets.connect(
                        self.config.WEBSOCKET_URL,
                        extra_headers=headers
                    ) as websocket:
                        
                        # 发送格式支持询问
                        format_inquiry = {
                            "type": "format_support_inquiry",
                            "requested_format": fmt_test,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        await websocket.send(json.dumps(format_inquiry))
                        
                        # 等待响应
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5)
                            if response:
                                supported_formats.append(fmt_test['format'])
                                logger.info(f"✅ 支持格式: {fmt_test['format']}")
                        except asyncio.TimeoutError:
                            logger.info(f"⚠️  格式测试超时: {fmt_test['format']}")
                            
                except Exception as e:
                    logger.error(f"❌ 格式测试失败 {fmt_test['format']}: {e}")
            
            result.finish(
                success=len(supported_formats) > 0,
                tested_formats=[fmt['format'] for fmt in format_tests],
                supported_formats=supported_formats,
                support_count=len(supported_formats)
            )
            
            logger.info(f"✅ 音频格式兼容性测试完成，支持{len(supported_formats)}种格式")
            
        except Exception as e:
            logger.error(f"❌ 音频格式兼容性测试异常: {e}")
            result.finish(success=False, error_message=str(e))
        
        self.test_results.append(result)
        return result
    
    async def run_all_tests(self):
        """运行所有WebSocket音频测试"""
        logger.info("🚀 开始WebSocket音频传输全面测试")
        
        try:
            # 1. 基础连接测试
            await self.test_basic_websocket_connection()
            
            # 2. 音频数据接收测试
            await self.test_audio_data_reception()
            
            # 3. 并发音频流测试
            await self.test_concurrent_audio_streams()
            
            # 4. 重连测试
            await self.test_websocket_reconnection()
            
            # 5. 音频格式兼容性测试
            await self.test_audio_format_compatibility()
            
        except Exception as e:
            logger.error(f"❌ 测试执行异常: {e}")
    
    def generate_report(self) -> Dict:
        """生成测试报告"""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.success)
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": total_tests - successful_tests,
                "success_rate": successful_tests / total_tests * 100 if total_tests > 0 else 0,
                "total_duration": sum(r.duration for r in self.test_results)
            },
            "websocket_configuration": {
                "websocket_url": self.config.WEBSOCKET_URL,
                "test_device_id": self.config.TEST_DEVICE_ID,
                "client_id": self.config.CLIENT_ID,
                "connection_timeout": self.config.CONNECTION_TIMEOUT,
                "audio_receive_timeout": self.config.AUDIO_RECEIVE_TIMEOUT
            },
            "test_results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "duration": r.duration,
                    "error_message": r.error_message,
                    "metrics": r.metrics
                }
                for r in self.test_results
            ],
            "test_timestamp": datetime.now().isoformat()
        }
        
        return report

async def main():
    """主测试函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='小智系统WebSocket音频传输测试')
    parser.add_argument('--device-id', default='f0:9e:9e:04:8a:44', help='测试设备ID')
    parser.add_argument('--websocket-url', default='ws://47.98.51.180:8000/xiaozhi/v1/', help='WebSocket服务器URL')
    parser.add_argument('--concurrent', type=int, default=3, help='并发连接数')
    parser.add_argument('--audio-timeout', type=int, default=30, help='音频接收超时时间(秒)')
    parser.add_argument('--report', default='websocket_audio_test_report.json', help='测试报告文件名')
    
    args = parser.parse_args()
    
    # 创建配置
    config = WebSocketAudioTestConfig()
    config.TEST_DEVICE_ID = args.device_id
    config.WEBSOCKET_URL = args.websocket_url
    config.CONCURRENT_CONNECTIONS = args.concurrent
    config.AUDIO_RECEIVE_TIMEOUT = args.audio_timeout
    
    # 创建测试器
    tester = WebSocketAudioTester(config)
    
    try:
        # 运行所有测试
        await tester.run_all_tests()
        
        # 生成测试报告
        report = tester.generate_report()
        
        # 输出结果
        print("\n" + "="*60)
        print("🎵 WebSocket音频传输测试报告")
        print("="*60)
        
        summary = report["test_summary"]
        
        print(f"测试结果:")
        print(f"  总测试数: {summary['total_tests']}")
        print(f"  成功测试: {summary['successful_tests']}")
        print(f"  失败测试: {summary['failed_tests']}")
        print(f"  成功率: {summary['success_rate']:.1f}%")
        print(f"  总耗时: {summary['total_duration']:.2f}秒")
        
        print(f"\n配置信息:")
        ws_config = report["websocket_configuration"]
        print(f"  WebSocket URL: {ws_config['websocket_url']}")
        print(f"  测试设备ID: {ws_config['test_device_id']}")
        print(f"  客户端ID: {ws_config['client_id']}")
        
        # 保存详细报告
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n详细报告已保存到: {args.report}")
        
        # 显示失败的测试
        failed_tests = [r for r in tester.test_results if not r.success]
        if failed_tests:
            print("\n❌ 失败的测试:")
            for test in failed_tests:
                print(f"  - {test.test_name}: {test.error_message}")
        
        # 显示重要指标
        for test_result in tester.test_results:
            if test_result.test_name == "音频数据接收测试" and test_result.success:
                metrics = test_result.metrics
                print(f"\n🎵 音频接收统计:")
                print(f"  音频块数: {metrics.get('audio_chunks_received', 0)}")
                print(f"  总音频大小: {metrics.get('total_audio_size_bytes', 0)} 字节")
                print(f"  平均块大小: {metrics.get('avg_chunk_size_bytes', 0):.1f} 字节")
                break
        
        return summary['success_rate'] >= 80
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 测试执行异常: {e}")
        return False

if __name__ == "__main__":
    print("🎵 小智系统WebSocket音频传输专项测试 v1.0.0")
    print("=" * 60)
    
    success = asyncio.run(main())
    
    if success:
        print("\n🎉 WebSocket音频传输测试通过!")
        sys.exit(0)
    else:
        print("\n❌ WebSocket音频传输测试失败!")
        sys.exit(1)

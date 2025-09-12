#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS音频生成专项检查工具
检查主动问候中TTS音频生成和传输的问题
"""

import asyncio
import json
import logging
import time
import requests
import os
from datetime import datetime
from typing import Dict, List, Any
import uuid
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('TTS检查')

class TTSAudioChecker:
    """TTS音频生成检查器"""
    
    def __init__(self):
        self.python_api = "http://47.98.51.180:8003"
        self.device_id = "f0:9e:9e:04:8a:44"
        
    async def check_python_service_health(self):
        """检查Python服务健康状态"""
        logger.info("🔍 检查Python服务状态...")
        
        try:
            # 检查健康接口
            response = requests.get(f"{self.python_api}/health", timeout=5)
            logger.info(f"健康检查: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("✅ Python API服务正常")
                return True
            else:
                logger.warning(f"⚠️  Python API返回异常状态: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error("❌ 无法连接Python API服务")
            return False
        except Exception as e:
            logger.error(f"❌ Python API检查异常: {e}")
            return False
    
    async def test_tts_generation(self):
        """测试TTS音频生成"""
        logger.info("🎵 测试TTS音频生成...")
        
        # 测试TTS接口（如果存在）
        test_texts = [
            "你好，这是TTS测试",
            "主动问候音频生成测试",
            "硬件音频播放检查"
        ]
        
        tts_results = []
        
        for i, text in enumerate(test_texts):
            logger.info(f"🧪 测试文本 {i+1}: {text}")
            
            try:
                # 尝试直接调用TTS接口（根据你的实际TTS接口调整）
                tts_payload = {
                    "text": text,
                    "voice": "default",
                    "format": "wav"
                }
                
                # 检查是否有TTS接口
                tts_endpoints = [
                    f"{self.python_api}/tts/generate",
                    f"{self.python_api}/api/tts",
                    f"{self.python_api}/speech/synthesize"
                ]
                
                tts_success = False
                for endpoint in tts_endpoints:
                    try:
                        response = requests.post(endpoint, json=tts_payload, timeout=10)
                        if response.status_code == 200:
                            logger.info(f"✅ TTS接口工作正常: {endpoint}")
                            tts_success = True
                            break
                        else:
                            logger.info(f"⚠️  TTS接口 {endpoint}: {response.status_code}")
                    except:
                        continue
                
                if not tts_success:
                    logger.warning("⚠️  未找到可用的TTS接口")
                
                tts_results.append(tts_success)
                
            except Exception as e:
                logger.error(f"❌ TTS测试失败: {e}")
                tts_results.append(False)
        
        return any(tts_results)
    
    async def check_audio_storage(self):
        """检查音频文件存储"""
        logger.info("📁 检查音频文件存储...")
        
        # 常见的音频存储路径
        audio_paths = [
            "audio",
            "tts_audio", 
            "generated_audio",
            "static/audio",
            "files/audio",
            "../audio"
        ]
        
        found_audio_dir = False
        for path in audio_paths:
            if os.path.exists(path):
                logger.info(f"📂 找到音频目录: {path}")
                
                # 列出最近的音频文件
                try:
                    files = os.listdir(path)
                    audio_files = [f for f in files if f.endswith(('.wav', '.mp3', '.ogg'))]
                    
                    if audio_files:
                        logger.info(f"🎵 音频文件数量: {len(audio_files)}")
                        
                        # 显示最近的几个文件
                        recent_files = sorted(audio_files, key=lambda x: os.path.getmtime(os.path.join(path, x)), reverse=True)[:3]
                        for file in recent_files:
                            file_path = os.path.join(path, file)
                            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                            size = os.path.getsize(file_path)
                            logger.info(f"   📄 {file} ({size}字节, {mtime.strftime('%H:%M:%S')})")
                    else:
                        logger.warning(f"⚠️  {path} 目录为空")
                    
                    found_audio_dir = True
                except Exception as e:
                    logger.error(f"❌ 无法读取 {path}: {e}")
        
        if not found_audio_dir:
            logger.warning("⚠️  未找到音频存储目录")
        
        return found_audio_dir
    
    async def trace_proactive_greeting_flow(self):
        """跟踪主动问候完整流程"""
        logger.info("🔍 跟踪主动问候生成流程...")
        
        test_payload = {
            "device_id": self.device_id,
            "initial_content": f"TTS流程跟踪测试 {datetime.now().strftime('%H:%M:%S')}",
            "category": "system_reminder"
        }
        
        logger.info(f"🚀 发送主动问候请求...")
        logger.info(f"   设备ID: {self.device_id}")
        logger.info(f"   内容: {test_payload['initial_content']}")
        
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.python_api}/xiaozhi/greeting/send",
                json=test_payload,
                timeout=15  # 增加超时时间，观察TTS生成过程
            )
            
            response_time = time.time() - start_time
            
            logger.info(f"📤 API响应时间: {response_time:.2f}秒")
            logger.info(f"📤 API响应状态: {response.status_code}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                track_id = result.get('track_id')
                logger.info(f"✅ 请求成功!")
                logger.info(f"   Track ID: {track_id}")
                logger.info(f"   响应内容: {result}")
                
                # 分析响应时间
                if response_time > 5:
                    logger.warning(f"⚠️  响应时间较长({response_time:.2f}s)，可能TTS生成缓慢")
                elif response_time < 1:
                    logger.warning(f"⚠️  响应时间过快({response_time:.2f}s)，可能TTS生成跳过")
                else:
                    logger.info(f"✅ 响应时间正常({response_time:.2f}s)")
                
                return True, track_id
                
            else:
                logger.error(f"❌ 请求失败: {response.status_code}")
                logger.error(f"   响应内容: {response.text}")
                return False, None
                
        except requests.exceptions.Timeout:
            logger.error("❌ 请求超时，可能TTS生成过程卡住")
            return False, None
        except Exception as e:
            logger.error(f"❌ 请求异常: {e}")
            return False, None
    
    async def check_websocket_service(self):
        """检查WebSocket音频服务"""
        logger.info("🌐 检查WebSocket音频服务...")
        
        websocket_url = f"ws://47.98.51.180:8000/xiaozhi/v1/{self.device_id}"
        
        try:
            import websockets
            
            logger.info(f"🔗 连接WebSocket: {websocket_url}")
            
            async with websockets.connect(websocket_url) as websocket:
                logger.info("✅ WebSocket连接成功")
                
                # 发送测试消息
                test_message = json.dumps({
                    "type": "test",
                    "device_id": self.device_id,
                    "timestamp": time.time()
                })
                
                await websocket.send(test_message)
                logger.info("📤 发送测试消息")
                
                # 等待响应
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    logger.info(f"📨 收到响应: {response[:100]}...")
                    return True
                except asyncio.TimeoutError:
                    logger.warning("⚠️  WebSocket无响应")
                    return True  # 连接成功但无响应也算正常
                    
        except Exception as e:
            logger.error(f"❌ WebSocket连接失败: {e}")
            return False
    
    async def run_comprehensive_check(self):
        """运行综合检查"""
        logger.info("🔍 TTS音频生成综合检查")
        logger.info("="*60)
        
        results = {}
        
        # 1. Python服务健康检查
        results['python_service'] = await self.check_python_service_health()
        await asyncio.sleep(1)
        
        # 2. TTS生成检查
        results['tts_generation'] = await self.test_tts_generation()
        await asyncio.sleep(1)
        
        # 3. 音频存储检查
        results['audio_storage'] = await self.check_audio_storage()
        await asyncio.sleep(1)
        
        # 4. WebSocket服务检查
        results['websocket_service'] = await self.check_websocket_service()
        await asyncio.sleep(1)
        
        # 5. 完整流程跟踪
        flow_success, track_id = await self.trace_proactive_greeting_flow()
        results['proactive_flow'] = flow_success
        
        # 分析结果
        logger.info("\n" + "="*60)
        logger.info("📊 TTS音频问题诊断报告")
        logger.info("="*60)
        
        total_checks = len(results)
        passed_checks = sum(1 for r in results.values() if r)
        
        logger.info(f"🔍 检查项目: {total_checks}")
        logger.info(f"✅ 通过检查: {passed_checks}")
        logger.info(f"❌ 失败检查: {total_checks - passed_checks}")
        logger.info(f"🎯 健康度: {passed_checks/total_checks*100:.1f}%")
        
        logger.info(f"\n📋 详细结果:")
        logger.info(f"   Python服务: {'✅' if results['python_service'] else '❌'}")
        logger.info(f"   TTS生成: {'✅' if results['tts_generation'] else '❌'}")
        logger.info(f"   音频存储: {'✅' if results['audio_storage'] else '❌'}")
        logger.info(f"   WebSocket服务: {'✅' if results['websocket_service'] else '❌'}")
        logger.info(f"   主动问候流程: {'✅' if results['proactive_flow'] else '❌'}")
        
        # 问题诊断
        logger.info(f"\n🔍 问题分析:")
        
        if not results['python_service']:
            logger.error("❌ Python API服务异常，无法处理主动问候请求")
            
        if not results['tts_generation']:
            logger.error("❌ TTS音频生成服务异常")
            logger.error("   可能原因:")
            logger.error("   1. TTS引擎未启动或配置错误")
            logger.error("   2. TTS接口路径不正确")
            logger.error("   3. TTS服务依赖缺失")
            
        if not results['audio_storage']:
            logger.error("❌ 音频文件存储异常")
            logger.error("   可能原因:")
            logger.error("   1. 音频存储目录不存在")
            logger.error("   2. 音频文件生成失败")
            logger.error("   3. 文件权限问题")
            
        if not results['websocket_service']:
            logger.error("❌ WebSocket音频传输服务异常")
            logger.error("   可能原因:")
            logger.error("   1. WebSocket服务未启动")
            logger.error("   2. 端口被占用或防火墙阻拦")
            logger.error("   3. 音频流推送逻辑错误")
            
        if results['python_service'] and results['proactive_flow']:
            if not results['tts_generation']:
                logger.warning("⚠️  主动问候API工作，但TTS生成有问题")
                logger.warning("   这解释了为什么硬件收到命令但没有音频！")
        
        # 修复建议
        logger.info(f"\n💡 修复建议:")
        
        if not results['tts_generation']:
            logger.info("🔧 TTS问题修复:")
            logger.info("   1. 检查Python服务的TTS配置文件")
            logger.info("   2. 确认TTS引擎（如edge-tts, espnet等）已安装")
            logger.info("   3. 查看Python服务日志中的TTS相关错误")
            logger.info("   4. 测试TTS引擎是否能独立工作")
            
        if not results['audio_storage']:
            logger.info("🔧 音频存储问题修复:")
            logger.info("   1. 创建音频存储目录")
            logger.info("   2. 检查文件系统权限")
            logger.info("   3. 确认磁盘空间充足")
            
        if not results['websocket_service']:
            logger.info("🔧 WebSocket问题修复:")
            logger.info("   1. 检查WebSocket服务是否启动")
            logger.info("   2. 确认端口8000未被占用")
            logger.info("   3. 检查防火墙和网络配置")
        
        return passed_checks >= total_checks * 0.8  # 80%以上算正常

async def main():
    """主检查函数"""
    logger.info("🎵 TTS音频生成专项检查工具")
    logger.info("="*50)
    logger.info("🎯 检查目标:")
    logger.info("   主动问候中TTS音频生成和传输问题")
    logger.info("="*50)
    
    checker = TTSAudioChecker()
    
    try:
        result = await checker.run_comprehensive_check()
        
        if result:
            logger.info("\n✅ TTS音频系统基本正常")
        else:
            logger.info("\n❌ TTS音频系统存在问题")
        
        return result
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  检查被中断")
        return False
    except Exception as e:
        logger.error(f"\n❌ 检查异常: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    
    if success:
        print("\n✅ TTS音频检查完成")
    else:
        print("\n❌ 发现TTS音频问题")
    
    sys.exit(0 if success else 1)

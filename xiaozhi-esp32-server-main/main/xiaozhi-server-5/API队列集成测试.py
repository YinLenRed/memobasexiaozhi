#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API队列集成测试脚本
验证API消息是否正确通过队列管理器处理
"""

import asyncio
import json
import logging
import sys

try:
    import httpx
except ImportError:
    print("❌ Windows环境缺少httpx，请在Linux服务器运行此测试")
    print("💡 或直接运行: python 测试消息队列.py rapid")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('队列集成测试')

# 配置
PYTHON_API_BASE = "http://47.98.51.180:8003"
DEVICE_ID = "f0:9e:9e:04:8a:44"

async def test_queue_integration():
    """测试API队列集成"""
    logger.info("🧪 测试API消息队列集成功能")
    logger.info("="*50)
    
    async with httpx.AsyncClient() as client:
        # 1. 发送测试消息
        logger.info("1️⃣ 发送测试消息（应该通过队列处理）")
        
        test_payload = {
            "device_id": DEVICE_ID,
            "initial_content": "队列集成测试：这条消息应该通过队列管理器处理",
            "category": "system_reminder",
            "user_info": {
                "name": "测试用户",
                "priority": 1,
                "test_type": "queue_integration"
            }
        }
        
        response = await client.post(
            f"{PYTHON_API_BASE}/xiaozhi/greeting/send",
            json=test_payload,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            track_id = result.get('track_id', '未知')
            logger.info(f"✅ 消息发送成功: track_id={track_id}")
            
            # 短暂等待，让消息进入队列
            await asyncio.sleep(2)
            
            # 2. 检查队列状态
            logger.info("2️⃣ 检查队列状态（应该有消息记录）")
            queue_response = await client.get(
                f"{PYTHON_API_BASE}/xiaozhi/queue/status/{DEVICE_ID}", 
                timeout=5
            )
            
            if queue_response.status_code == 200:
                queue_status = queue_response.json()
                queue_len = queue_status.get('queue_length', 0)
                is_playing = queue_status.get('is_playing', False)
                total_msgs = queue_status.get('total_messages', 0)
                completed = queue_status.get('completed_messages', 0)
                
                logger.info("📊 队列状态:")
                logger.info(f"   队列长度: {queue_len}")
                logger.info(f"   正在播放: {is_playing}")
                logger.info(f"   总消息数: {total_msgs}")
                logger.info(f"   已完成数: {completed}")
                
                if total_msgs > 0 or queue_len > 0 or is_playing:
                    logger.info("🎉 成功！API消息正在通过队列处理")
                    return True
                else:
                    logger.warning("⚠️ 队列状态仍为空，可能需要重启服务")
                    logger.info("💡 请重启Python服务后再次测试")
                    return False
            else:
                logger.error(f"❌ 队列状态查询失败: {queue_response.status_code}")
                return False
        else:
            logger.error(f"❌ 消息发送失败: {response.status_code}")
            return False

if __name__ == "__main__":
    asyncio.run(test_queue_integration())

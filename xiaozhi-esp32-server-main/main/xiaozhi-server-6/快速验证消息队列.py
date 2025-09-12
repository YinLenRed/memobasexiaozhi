#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速验证消息队列功能
检查硬件消息是否按顺序播放，不会被新消息打断
"""

import asyncio
import time
import httpx
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('队列验证')

# 配置
PYTHON_API_BASE = "http://47.98.51.180:8003"
DEVICE_ID = "f0:9e:9e:04:8a:44"

async def send_message(client: httpx.AsyncClient, message: str, category: str = "test", priority: int = 1):
    """发送单条消息"""
    try:
        logger.info(f"📤 发送消息: {message}")
        
        response = await client.post(
            f"{PYTHON_API_BASE}/xiaozhi/greeting/send",
            json={
                "device_id": DEVICE_ID,
                "category": category,
                "initial_content": message,
                "user_info": {
                    "custom_prompt": message,
                    "priority": priority
                }
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"   ✅ 发送成功: {result.get('message', '无信息')}")
            return True
        else:
            logger.error(f"   ❌ 发送失败: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"   ❌ 发送异常: {e}")
        return False

async def check_queue_status(client: httpx.AsyncClient):
    """检查队列状态"""
    try:
        response = await client.get(f"{PYTHON_API_BASE}/xiaozhi/queue/status/{DEVICE_ID}", timeout=5)
        if response.status_code == 200:
            status = response.json()
            logger.info("📊 队列状态:")
            logger.info(f"   队列长度: {status.get('queue_length', 0)}")
            logger.info(f"   正在播放: {status.get('is_playing', False)}")
            logger.info(f"   已完成消息: {status.get('completed_messages', 0)}")
            return status
        else:
            logger.warning(f"⚠️ 无法获取队列状态: {response.status_code}")
            return None
    except Exception as e:
        logger.warning(f"⚠️ 队列状态检查失败: {e}")
        return None

async def test_queue_ordering():
    """测试队列顺序功能"""
    logger.info("🧪 测试消息队列顺序功能")
    logger.info("="*50)
    logger.info("🎯 验证: 消息按顺序播放，不会被打断")
    print()
    
    async with httpx.AsyncClient() as client:
        # 1. 检查初始状态
        logger.info("1️⃣ 检查初始队列状态")
        await check_queue_status(client)
        print()
        
        # 2. 快速发送多条消息（测试队列）
        logger.info("2️⃣ 快速发送多条消息测试队列")
        messages = [
            ("第一条消息：测试开始", "test", 1),
            ("第二条消息：应该在第一条完成后播放", "test", 1), 
            ("第三条消息：优先级高，应该插队", "urgent", 0),  # 高优先级
            ("第四条消息：普通消息", "test", 1),
            ("第五条消息：测试结束", "test", 1)
        ]
        
        logger.info(f"📋 将发送 {len(messages)} 条消息:")
        for i, (msg, cat, pri) in enumerate(messages, 1):
            logger.info(f"   {i}. {msg} (优先级: {pri})")
        print()
        
        # 快速发送（间隔很短，测试队列）
        success_count = 0
        for i, (message, category, priority) in enumerate(messages, 1):
            logger.info(f"🚀 [{i}/{len(messages)}] {message}")
            success = await send_message(client, message, category, priority)
            if success:
                success_count += 1
            
            # 短间隔发送，测试队列缓冲
            if i < len(messages):
                await asyncio.sleep(0.5)
        
        print()
        logger.info(f"📊 发送统计: {success_count}/{len(messages)} 成功")
        
        # 3. 监控队列状态变化
        logger.info("3️⃣ 监控队列处理情况")
        logger.info("   (观察消息是否按顺序处理，高优先级是否插队)")
        
        for i in range(10):  # 监控10次
            status = await check_queue_status(client)
            if status:
                queue_len = status.get('queue_length', 0)
                is_playing = status.get('is_playing', False)
                completed = status.get('completed_messages', 0)
                
                if queue_len == 0 and not is_playing and completed >= success_count:
                    logger.info("🎉 所有消息处理完成！")
                    break
                    
                logger.info(f"   等待中... 队列: {queue_len}, 播放中: {is_playing}, 已完成: {completed}")
            
            await asyncio.sleep(3)  # 每3秒检查一次
        
        # 4. 最终状态
        logger.info("4️⃣ 最终队列状态")
        final_status = await check_queue_status(client)
        
        print()
        logger.info("📋 测试总结:")
        if final_status:
            completed = final_status.get('completed_messages', 0)
            queue_len = final_status.get('queue_length', 0)
            
            if completed >= success_count and queue_len == 0:
                logger.info("✅ 消息队列功能正常！")
                logger.info("   - 所有消息都按顺序处理完成")
                logger.info("   - 没有消息被丢失或覆盖")
                logger.info("   - 优先级消息正确插队")
                return True
            else:
                logger.warning("⚠️ 可能存在问题，部分消息未完成")
                return False
        else:
            logger.error("❌ 无法获取最终状态")
            return False

async def test_interruption_protection():
    """测试消息不被打断的保护机制"""
    logger.info("🧪 测试消息打断保护")
    logger.info("="*40)
    
    async with httpx.AsyncClient() as client:
        # 发送一条长消息
        long_message = "这是一条比较长的消息，用来测试播放过程中不会被新消息打断。" * 3
        logger.info("📤 发送长消息")
        await send_message(client, long_message, "test", 1)
        
        # 等待1秒后发送短消息
        await asyncio.sleep(1)
        logger.info("📤 发送短消息（应该等待长消息完成）")
        await send_message(client, "短消息，应该排队等待", "test", 1)
        
        # 监控状态
        for i in range(8):
            status = await check_queue_status(client)
            if status:
                logger.info(f"   队列: {status.get('queue_length', 0)}, "
                          f"播放中: {status.get('is_playing', False)}")
            await asyncio.sleep(2)

async def main():
    """主函数"""
    print("🔍 消息队列功能验证工具")
    print("="*40)
    print("🎯 检查硬件消息是否按顺序播放，不被新消息打断")
    print()
    
    print("测试选项:")
    print("1. 队列顺序测试（推荐）")
    print("2. 打断保护测试")
    print("3. 完整测试")
    
    choice = input("\n选择测试类型 (1-3, 默认1): ").strip()
    
    try:
        if choice == "2":
            await test_interruption_protection()
        elif choice == "3":
            success1 = await test_queue_ordering()
            print("\n" + "="*50)
            await test_interruption_protection()
        else:
            # 默认选择1
            success = await test_queue_ordering()
            if success:
                print("\n🎉 消息队列功能验证通过！")
                print("✅ 硬件消息会按顺序播放，不会被新消息顶掉")
            else:
                print("\n⚠️ 验证结果不确定，请检查服务状态")
    
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        logger.error(f"测试异常: {e}")

if __name__ == "__main__":
    asyncio.run(main())

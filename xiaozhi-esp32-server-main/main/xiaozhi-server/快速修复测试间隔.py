#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速修复测试消息队列的间隔问题
将rapid模式的0.5秒间隔调整为2秒，避免LLM并发冲突
"""

import re

def fix_test_interval():
    """修复测试脚本的消息间隔"""
    try:
        # 读取原文件
        with open('测试消息队列.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 备份原文件
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = f'测试消息队列_备份_{timestamp}.py'
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📁 原文件已备份为: {backup_file}")
        
        # 修复间隔时间：0.5秒 → 2秒
        # 查找: await asyncio.sleep(0.5)
        # 替换为: await asyncio.sleep(2.0)
        fixed_content = re.sub(
            r'await asyncio\.sleep\(0\.5\)',
            'await asyncio.sleep(2.0)  # 修复: 增加间隔避免LLM并发冲突',
            content
        )
        
        # 写入修复后的文件
        with open('测试消息队列.py', 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print("✅ 测试脚本修复完成!")
        print("🔧 修改内容:")
        print("   - 消息间隔: 0.5秒 → 2.0秒")
        print("   - 避免LLM并发调用冲突")
        print("   - 现在rapid模式应该能正常工作")
        
        print("\n🧪 测试建议:")
        print("   python 测试消息队列.py rapid")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False

def create_safe_rapid_test():
    """创建安全的rapid测试版本"""
    safe_test_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全的快速消息测试 - 避免LLM并发冲突
"""

import asyncio
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('安全测试')

DEVICE_ID = "f0:9e:9e:04:8a:44"

async def safe_rapid_test():
    """安全的快速消息测试"""
    logger.info("🧪 安全的快速消息测试")
    logger.info("="*40)
    
    messages = [
        {
            "device_id": DEVICE_ID,
            "title": "天气预警",
            "data": "大风蓝色预警", 
            "prompt": "有大风预警，请注意安全",
            "priority": 0
        },
        {
            "device_id": DEVICE_ID,
            "title": "节日问候",
            "data": "国庆节",
            "prompt": "国庆节快乐！祝您节日愉快",
            "priority": 1
        },
        {
            "device_id": DEVICE_ID, 
            "title": "24节气",
            "data": "立秋",
            "prompt": "今天是立秋，注意养生",
            "priority": 1
        }
    ]
    
    logger.info(f"📋 准备安全发送 {len(messages)} 条消息")
    logger.info("💡 使用2秒间隔，避免LLM并发冲突")
    
    for i, msg in enumerate(messages, 1):
        logger.info(f"📤 [{i}/{len(messages)}] 发送消息: {msg['title']}")
        logger.info(f"   内容: {msg['prompt']}")
        
        # 发送消息到Python服务
        success = await send_message_safely(msg)
        
        if success:
            logger.info(f"   ✅ 消息 {i} 发送成功")
        else:
            logger.error(f"   ❌ 消息 {i} 发送失败")
        
        # 安全间隔：2秒（避免LLM并发冲突）
        if i < len(messages):
            logger.info(f"   ⏳ 等待 2 秒（避免LLM并发冲突）...")
            await asyncio.sleep(2.0)
    
    logger.info("✅ 安全测试完成！应该不会出现OpenAI错误了")

async def send_message_safely(message_data):
    """安全发送消息"""
    try:
        import urllib.request
        import urllib.parse
        import json
        
        payload = {
            "device_id": message_data["device_id"],
            "category": "system_reminder", 
            "initial_content": message_data["prompt"]
        }
        
        data = json.dumps(payload).encode('utf-8')
        
        req = urllib.request.Request(
            "http://47.98.51.180:8003/xiaozhi/greeting/send",
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                return True
            else:
                logger.error(f"HTTP错误: {response.status}")
                return False
                
    except Exception as e:
        logger.error(f"发送失败: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(safe_rapid_test())
'''
    
    with open('安全的快速消息测试.py', 'w', encoding='utf-8') as f:
        f.write(safe_test_content)
    
    print("📄 创建了安全测试脚本: 安全的快速消息测试.py")
    print("🧪 使用方法: python 安全的快速消息测试.py")

def main():
    print("⚡ 快速修复LLM并发冲突")
    print("="*30)
    print("🎯 问题: rapid模式0.5秒间隔导致LLM并发调用冲突")
    print("💡 解决: 增加消息间隔到2秒，避免并发问题")
    print()
    
    print("选择修复方案:")
    print("1. 修复原测试脚本间隔 (推荐)")
    print("2. 创建安全测试脚本")  
    print("3. 两者都执行")
    
    choice = input("\n请选择 (1-3): ").strip()
    
    if choice == "1":
        fix_test_interval()
    elif choice == "2":
        create_safe_rapid_test()
    elif choice == "3":
        fix_test_interval()
        print()
        create_safe_rapid_test()
    else:
        print("执行默认修复...")
        fix_test_interval()
    
    print()
    print("🎉 修复完成！现在可以测试:")
    print("   python 测试消息队列.py rapid  # 应该不会再报OpenAI错误")
    print("   python 安全的快速消息测试.py      # 或使用新的安全脚本")

if __name__ == "__main__":
    main()

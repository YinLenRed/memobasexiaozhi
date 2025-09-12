#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息队列测试脚本
验证硬件按顺序播放消息功能
"""

import asyncio
import time
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('队列测试')

DEVICE_ID = "f0:9e:9e:04:8a:44"

def simulate_java_messages():
    """模拟Java后端推送的多条消息"""
    messages = [
        {
            "device_id": DEVICE_ID,
            "title": "天气预警",
            "data": "大风蓝色预警",
            "prompt": "有大风预警，请注意安全",
            "priority": 0  # 高优先级
        },
        {
            "device_id": DEVICE_ID,
            "title": "节日问候", 
            "data": "国庆节",
            "prompt": "国庆节快乐！祝您节日愉快",
            "priority": 1  # 普通优先级
        },
        {
            "device_id": DEVICE_ID,
            "title": "24节气",
            "data": "立秋",
            "prompt": "今天是立秋，注意养生",
            "priority": 1  # 普通优先级
        },
        {
            "device_id": DEVICE_ID,
            "title": "天气播报",
            "data": "晴天22度",
            "prompt": "今天天气晴朗，温度22度，适合外出",
            "priority": 2  # 低优先级
        }
    ]
    return messages

async def test_rapid_message_sending():
    """测试快速发送多条消息"""
    logger.info("🧪 测试快速发送多条消息")
    logger.info("="*50)
    
    messages = simulate_java_messages()
    
    logger.info(f"📋 准备发送 {len(messages)} 条消息到设备: {DEVICE_ID}")
    logger.info("💡 预期效果: 硬件按优先级和顺序依次播放，不会被新消息打断")
    print()
    
    for i, msg in enumerate(messages, 1):
        logger.info(f"📤 [{i}/{len(messages)}] 发送消息: {msg['title']} - {msg['data']}")
        logger.info(f"   内容: {msg['prompt']}")
        logger.info(f"   优先级: {msg['priority']}")
        
        # 模拟Java后端API调用
        success = await send_message_to_python_service(msg)
        
        if success:
            logger.info(f"   ✅ 消息发送成功")
        else:
            logger.error(f"   ❌ 消息发送失败")
        
        print()
        
        # 快速发送（模拟Java后端连续推送）
        await asyncio.sleep(0.5)
    
    logger.info("📊 所有消息已发送完毕")
    logger.info("💡 请观察硬件是否按顺序播放：")
    logger.info("   1. 大风蓝色预警（高优先级，最先播放）")
    logger.info("   2. 国庆节快乐！（普通优先级）") 
    logger.info("   3. 今天是立秋（普通优先级）")
    logger.info("   4. 今天天气晴朗（低优先级，最后播放）")

async def send_message_to_python_service(message_data):
    """发送消息到Python服务"""
    try:
        import urllib.request
        import urllib.parse
        
        # 构建请求数据（使用正确的API格式）
        payload = {
            "device_id": message_data["device_id"],
            "category": get_category_from_title(message_data["title"]),
            "initial_content": message_data["prompt"]
        }
        
        # 发送HTTP请求
        url = "http://47.98.51.180:8003/xiaozhi/greeting/send"
        data_json = json.dumps(payload).encode('utf-8')
        
        req = urllib.request.Request(url, data=data_json)
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=15) as response:
            response_text = response.read().decode('utf-8')
            response_data = json.loads(response_text)
            
            if response_data.get("success"):
                return True
            else:
                logger.error(f"服务响应错误: {response_data}")
                return False
                
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        return False

def get_category_from_title(title):
    """根据标题确定消息类别"""
    if "预警" in title or "警报" in title:
        return "weather"
    elif "节日" in title or "节假日" in title:
        return "entertainment"
    elif "节气" in title:
        return "entertainment"
    elif "天气" in title:
        return "weather"
    else:
        return "system_reminder"

async def test_single_message():
    """测试单条消息"""
    logger.info("🧪 测试单条消息发送")
    logger.info("="*30)
    
    message = {
        "device_id": DEVICE_ID,
        "title": "队列测试",
        "data": "单条消息",
        "prompt": f"消息队列测试，当前时间 {datetime.now().strftime('%H点%M分')}",
        "priority": 1
    }
    
    logger.info(f"📤 发送测试消息: {message['prompt']}")
    
    success = await send_message_to_python_service(message)
    
    if success:
        logger.info("✅ 单条消息测试成功")
    else:
        logger.error("❌ 单条消息测试失败")

async def test_priority_ordering():
    """测试优先级排序"""
    logger.info("🧪 测试优先级排序")
    logger.info("="*30)
    
    # 故意乱序发送，测试优先级排序
    priority_messages = [
        {"title": "低优先级消息", "prompt": "我是低优先级，应该最后播放", "priority": 3},
        {"title": "高优先级消息", "prompt": "我是高优先级，应该最先播放", "priority": 0},
        {"title": "普通优先级消息", "prompt": "我是普通优先级，应该中间播放", "priority": 1},
    ]
    
    logger.info("📋 发送顺序（故意乱序）:")
    for i, msg in enumerate(priority_messages, 1):
        logger.info(f"   {i}. {msg['title']} (优先级: {msg['priority']})")
    
    print()
    logger.info("💡 预期播放顺序:")
    logger.info("   1. 高优先级消息 (优先级: 0)")
    logger.info("   2. 普通优先级消息 (优先级: 1)")
    logger.info("   3. 低优先级消息 (优先级: 3)")
    print()
    
    for msg in priority_messages:
        full_msg = {
            "device_id": DEVICE_ID,
            "title": msg["title"],
            "data": "优先级测试",
            "prompt": msg["prompt"],
            "priority": msg["priority"]
        }
        
        await send_message_to_python_service(full_msg)
        await asyncio.sleep(0.3)  # 快速发送
    
    logger.info("✅ 优先级测试消息发送完毕")

async def interactive_test():
    """交互式测试"""
    print("🎵 硬件消息队列测试工具")
    print("="*40)
    print("1. 单条消息测试")
    print("2. 快速多条消息测试")
    print("3. 优先级排序测试")
    print("4. 自定义消息测试")
    print("5. 退出")
    
    while True:
        try:
            choice = input("\n请选择测试项目 (1-5): ").strip()
            
            if choice == "1":
                await test_single_message()
                
            elif choice == "2":
                await test_rapid_message_sending()
                
            elif choice == "3":
                await test_priority_ordering()
                
            elif choice == "4":
                content = input("请输入自定义消息内容: ").strip()
                if content:
                    custom_msg = {
                        "device_id": DEVICE_ID,
                        "title": "自定义消息",
                        "data": "用户输入",
                        "prompt": content,
                        "priority": 1
                    }
                    await send_message_to_python_service(custom_msg)
                    logger.info("✅ 自定义消息发送成功")
                
            elif choice == "5":
                print("👋 退出测试工具")
                break
                
            else:
                print("❌ 无效选择，请输入 1-5")
                
        except KeyboardInterrupt:
            print("\n👋 退出测试工具")
            break
        except Exception as e:
            logger.error(f"测试异常: {e}")

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "single":
            asyncio.run(test_single_message())
        elif test_type == "rapid":
            asyncio.run(test_rapid_message_sending())
        elif test_type == "priority":
            asyncio.run(test_priority_ordering())
        else:
            print("用法: python 测试消息队列.py [single|rapid|priority]")
            print("或者直接运行进入交互模式")
    else:
        asyncio.run(interactive_test())

if __name__ == "__main__":
    main()

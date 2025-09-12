#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间确认功能测试脚本
测试多轮对话时间确认和策略保存功能
"""

import json
import requests
import time

# 配置
PYTHON_API_BASE = "http://47.98.51.180:8003"
DEVICE_ID = "f0:9e:9e:04:8a:44"

def test_reminder_request(message):
    """测试提醒请求"""
    print(f"\n👤 用户消息: {message}")
    
    try:
        response = requests.post(
            f"{PYTHON_API_BASE}/xiaozhi/reminder/request",
            json={
                "device_id": DEVICE_ID,
                "message": message
            },
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 系统回复: {result.get('message', '无回复')}")
            
            if result.get('conversation_active'):
                print("🔄 需要继续对话确认时间")
                return True, result.get('task_id')
            else:
                print("✅ 任务已完成或无需确认")
                return False, result.get('task_id')
        else:
            print(f"❌ 请求失败: {response.status_code} - {response.text}")
            return False, None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False, None

def check_conversation_status():
    """检查对话状态"""
    try:
        response = requests.get(
            f"{PYTHON_API_BASE}/xiaozhi/reminder/status/{DEVICE_ID}",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('conversation_active'):
                status = result.get('status', {})
                print(f"📊 对话状态: 任务={status.get('extracted_task', 'N/A')}, 尝试={status.get('attempts', 0)}次")
            else:
                print("📊 无活跃对话")
            return result
        else:
            print(f"⚠️ 状态查询失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 状态查询异常: {e}")
        return None

def main():
    print("🧪 智能时间确认功能测试")
    print("="*40)
    
    # 测试用例
    test_cases = [
        {
            "name": "模糊时间测试",
            "initial": "下周提醒我记得给女儿买生日礼物",
            "follow_up": "下周三下午2点"
        },
        {
            "name": "明确时间测试", 
            "initial": "明天下午3点提醒我开会",
            "follow_up": None
        },
        {
            "name": "缺少时间测试",
            "initial": "提醒我交水电费",
            "follow_up": "后天上午9点"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 测试{i}: {test_case['name']}")
        print("-" * 30)
        
        # 发送初始消息
        need_follow, task_id = test_reminder_request(test_case["initial"])
        
        if need_follow and test_case["follow_up"]:
            print("⏳ 等待2秒后发送确认消息...")
            time.sleep(2)
            
            # 检查对话状态
            check_conversation_status()
            
            # 发送确认消息
            test_reminder_request(test_case["follow_up"])
        
        print("\n" + "="*40)
        time.sleep(1)
    
    print("\n📋 最终对话状态检查:")
    check_conversation_status()

if __name__ == "__main__":
    main()

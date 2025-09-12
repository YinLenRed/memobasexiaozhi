#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能时间确认系统功能演示
展示多轮对话时间确认的完整流程
"""

import sys
import os

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from 智能时间确认系统 import conversation_manager, TimeExtractor

def demo_time_extraction():
    """演示时间信息提取功能"""
    print("🕒 时间信息提取功能演示")
    print("="*40)
    
    extractor = TimeExtractor()
    
    test_messages = [
        "明天下午3点提醒我开会",                    # 明确时间
        "下周提醒我记得给女儿买生日礼物",              # 模糊时间  
        "3月15日上午9点提醒我体检",                  # 明确时间
        "过几天提醒我交水电费",                      # 模糊时间
        "提醒我买菜",                              # 缺少时间
        "周三下午提醒我接孩子",                      # 部分模糊
    ]
    
    for message in test_messages:
        time_info = extractor.extract_time_info(message)
        status_icon = {
            "clear": "✅",
            "vague": "⚠️", 
            "missing": "❌",
            "invalid": "🚫"
        }
        
        print(f"\n📝 消息: {message}")
        print(f"   状态: {status_icon[time_info.status.value]} {time_info.status.value.upper()}")
        if time_info.extracted_time:
            print(f"   时间: {time_info.extracted_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"   置信度: {time_info.confidence:.1f}")

def demo_conversation_flow():
    """演示多轮对话流程"""
    print("\n\n🔄 多轮对话流程演示")
    print("="*40)
    
    # 模拟用户对话
    conversations = [
        {
            "device_id": "demo_user_001",
            "scenario": "模糊时间确认",
            "messages": [
                "下周提醒我记得给女儿买生日礼物",
                "下周三下午2点"
            ]
        },
        {
            "device_id": "demo_user_002", 
            "scenario": "缺少时间询问",
            "messages": [
                "提醒我交水电费",
                "明天上午9点"
            ]
        },
        {
            "device_id": "demo_user_003",
            "scenario": "明确时间直接保存",
            "messages": [
                "明天下午3点提醒我开会"
            ]
        },
        {
            "device_id": "demo_user_004",
            "scenario": "用户取消提醒",
            "messages": [
                "下个月提醒我续费",
                "算了，不用了"
            ]
        }
    ]
    
    for conv in conversations:
        print(f"\n🎭 场景: {conv['scenario']}")
        print(f"👤 用户ID: {conv['device_id']}")
        print("-" * 30)
        
        for i, message in enumerate(conv["messages"]):
            if i == 0:
                print(f"👤 用户: {message}")
            else:
                print(f"👤 用户回复: {message}")
            
            # 处理消息
            result = conversation_manager.process_user_message(conv["device_id"], message)
            
            if result.get('message'):
                print(f"🤖 系统: {result['message']}")
            
            # 显示处理结果
            if result.get('success'):
                if result.get('waiting_for'):
                    print("   🔄 等待用户回复时间信息")
                elif result.get('confirmed'):
                    print("   ✅ 提醒设置成功")
                elif result.get('cancelled'):
                    print("   🚫 用户取消设置")
            else:
                print("   ❌ 处理失败")
            
            print()

def demo_api_usage():
    """演示API使用方法"""
    print("\n🌐 API使用方法演示")
    print("="*40)
    
    print("1️⃣ 发送提醒请求:")
    print("""
curl -X POST http://47.98.51.180:8003/xiaozhi/reminder/request \\
  -H "Content-Type: application/json" \\
  -d '{
    "device_id": "f0:9e:9e:04:8a:44",
    "message": "下周提醒我记得给女儿买生日礼物"
  }'
""")
    
    print("📤 预期响应 (需要确认时间):")
    print("""{
  "success": true,
  "message": "我理解您想要设置提醒：给女儿买生日礼物。请问您希望在什么时候提醒您呢？",
  "need_follow_up": true,
  "conversation_active": true,
  "task_id": "task_abc123"
}""")
    
    print("\n2️⃣ 继续对话确认时间:")
    print("""
curl -X POST http://47.98.51.180:8003/xiaozhi/reminder/request \\
  -H "Content-Type: application/json" \\
  -d '{
    "device_id": "f0:9e:9e:04:8a:44", 
    "message": "下周三下午2点"
  }'
""")
    
    print("📤 预期响应 (确认成功):")
    print("""{
  "success": true,
  "message": "完美！我会在2024年3月13日 14:00提醒您：给女儿买生日礼物。提醒已设置成功！",
  "need_follow_up": false,
  "conversation_active": false,
  "task_id": "task_abc123"
}""")
    
    print("\n3️⃣ 查询对话状态:")
    print("""
curl http://47.98.51.180:8003/xiaozhi/reminder/status/f0:9e:9e:04:8a:44
""")

def demo_java_integration():
    """演示Java集成说明"""
    print("\n🔗 Java后端集成说明")
    print("="*40)
    
    print("📋 Java后端需要提供策略保存接口:")
    print("""
接口地址: POST http://q83b6ed9.natappfree.cc/xiaozhi/strategy/reminder

请求格式:
{
  "device_id": "f0:9e:9e:04:8a:44",
  "task_id": "task_abc123", 
  "task_content": "给女儿买生日礼物",
  "reminder_time": "2024-03-13T14:00:00",
  "original_message": "下周提醒我记得给女儿买生日礼物",
  "created_at": "2024-03-08T10:30:00",
  "status": "active",
  "type": "user_reminder"
}

成功响应: HTTP 200
{
  "success": true,
  "strategy_id": "strategy_123",
  "message": "提醒策略保存成功"
}
""")
    
    print("🎯 集成要点:")
    print("1. Java后端接收并保存用户提醒策略")
    print("2. 根据reminder_time字段安排定时任务") 
    print("3. 到时间后通过MQTT推送提醒消息给Python")
    print("4. Python通过消息队列播放提醒内容给用户")

def main():
    """主演示函数"""
    print("🎭 智能时间确认系统功能演示")
    print("="*50)
    print("🎯 展示多轮对话时间确认的完整功能")
    print()
    
    print("演示内容:")
    print("1. 时间信息提取功能")
    print("2. 多轮对话流程")
    print("3. API使用方法") 
    print("4. Java集成说明")
    print()
    
    input("按回车开始演示...")
    
    # 执行各种演示
    demo_time_extraction()
    
    input("\n按回车继续下一个演示...")
    demo_conversation_flow()
    
    input("\n按回车查看API使用方法...")
    demo_api_usage()
    
    input("\n按回车查看Java集成说明...")
    demo_java_integration()
    
    print("\n🎉 演示完成！")
    print("📋 关键功能:")
    print("   ✅ 智能识别时间信息的明确性")
    print("   ✅ 多轮对话确认模糊时间") 
    print("   ✅ 自动保存策略到Java后端")
    print("   ✅ 通过消息队列回复用户")
    print("   ✅ 完整的API接口支持")
    
    print("\n🚀 现在您可以:")
    print("   1. 重启Python服务加载新功能")
    print("   2. 配置Java后端策略保存接口")
    print("   3. 运行测试验证功能")
    print("   4. 用户可以通过自然语言设置智能提醒！")

if __name__ == "__main__":
    main()

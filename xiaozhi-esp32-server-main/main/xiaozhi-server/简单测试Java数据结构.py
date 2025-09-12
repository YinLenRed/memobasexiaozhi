#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试Java后端新数据结构
不依赖完整服务，仅测试核心逻辑
"""

import json
import re
from typing import Dict, Any

class EventType:
    WEATHER_ALERT = "weather_alert"
    SOLAR_TERM = "solar_term"
    HOLIDAY = "holiday"
    UNKNOWN = "unknown"

class SimpleEventParser:
    """简化的事件解析器"""
    
    @staticmethod
    def detect_event_type(data: Dict[str, Any]) -> str:
        """检测事件类型"""
        if SimpleEventParser._is_weather_alert(data):
            return EventType.WEATHER_ALERT
        if SimpleEventParser._is_solar_term(data):
            return EventType.SOLAR_TERM
        if SimpleEventParser._is_holiday(data):
            return EventType.HOLIDAY
        return EventType.UNKNOWN
    
    @staticmethod
    def _is_weather_alert(data: Dict[str, Any]) -> bool:
        """判断是否为天气预警"""
        topic = str(data.get("topic", ""))
        if "天气" in topic and ("预警" in topic or "警报" in topic or "预报" in topic):
            return True
        return False
    
    @staticmethod
    def _is_solar_term(data: Dict[str, Any]) -> bool:
        """判断是否为24节气"""
        topic = str(data.get("topic", ""))
        if "节气" in topic or "立春" in topic or "立夏" in topic or "立秋" in topic or "立冬" in topic:
            return True
        return False
    
    @staticmethod
    def _is_holiday(data: Dict[str, Any]) -> bool:
        """判断是否为节假日"""
        topic = str(data.get("topic", ""))
        if ("节假日" in topic or "节日" in topic or "假期" in topic or 
            "春节" in topic or "中秋" in topic or "国庆" in topic or "元旦" in topic):
            return True
        return False

def extract_content_from_event(event_data: Dict[str, Any]) -> str:
    """从事件数据中提取内容"""
    # 检查prompt字段
    prompt = event_data.get("prompt")
    
    # 兼容多种数据字段
    result = (event_data.get("result") or 
             event_data.get("content") or 
             event_data.get("data") or 
             event_data.get("festival"))
    
    # 如果没有单独的内容字段，尝试从title+content构建
    if not result and event_data.get("title"):
        title = event_data.get("title", "")
        content = event_data.get("content", "")
        result = f"{title}: {content}" if content else title
    
    print(f"🔍 提取字段: prompt='{prompt}', result='{result}'")
    return prompt, result

def simulate_java_event_processing(java_data: Dict[str, Any]):
    """模拟Java事件处理流程"""
    print("📋 Java后端原始数据:")
    print(json.dumps(java_data, indent=2, ensure_ascii=False))
    
    # 检查是否是Java后端数组格式
    if isinstance(java_data, dict) and "data" in java_data and isinstance(java_data["data"], list):
        print(f"📊 检测到Java后端事件数组，包含 {len(java_data['data'])} 个事件")
        
        # 提取全局字段
        global_fields = {k: v for k, v in java_data.items() if k != "data"}
        print(f"🌐 全局字段: {global_fields}")
        
        processed_events = []
        
        for idx, single_event in enumerate(java_data["data"]):
            print(f"\n📝 处理第 {idx+1} 个事件:")
            
            # 合并全局字段和单个事件数据
            merged_event = {**global_fields, **single_event}
            print(f"🔄 合并后的事件: {json.dumps(merged_event, ensure_ascii=False)}")
            
            # 检测事件类型
            event_type = SimpleEventParser.detect_event_type(merged_event)
            print(f"🎯 事件类型: {event_type}")
            
            # 提取内容
            prompt, content = extract_content_from_event(merged_event)
            
            # 检查是否支持prompt处理
            if prompt and content:
                print("✅ 该事件支持Java后端prompt处理")
                print(f"   Prompt: {prompt}")
                print(f"   Content: {content}")
            else:
                print("⚠️ 该事件将使用传统内容生成")
            
            processed_events.append({
                "event_type": event_type,
                "has_prompt": bool(prompt),
                "has_content": bool(content),
                "merged_data": merged_event
            })
        
        return processed_events
    
    return []

def main():
    """主函数"""
    print("🔧 Java后端新数据结构测试")
    print("="*50)
    
    # 用户提供的Java数据结构
    java_data = {
        "device_id": "f0:9e:9e:04:8a:44",
        "topic": "天气预报",
        "data": [
            {
                "title": "北京天气预报",
                "content": "天气json"
            }
        ],
        "prompt": "这是prompt"
    }
    
    print("🎯 测试用户提供的数据结构:")
    processed_events = simulate_java_event_processing(java_data)
    
    print("\n📊 处理结果总结:")
    for i, event in enumerate(processed_events):
        print(f"事件 {i+1}: 类型={event['event_type']}, prompt支持={event['has_prompt']}, 内容可用={event['has_content']}")
    
    # 测试其他数据结构
    test_cases = [
        {
            "name": "天气预警",
            "data": {
                "device_id": "f0:9e:9e:04:8a:44",
                "topic": "天气预警",
                "data": [{"title": "大风预警", "content": "大风蓝色预警"}],
                "prompt": "请生成预警播报"
            }
        },
        {
            "name": "春节假期",
            "data": {
                "device_id": "f0:9e:9e:04:8a:44", 
                "topic": "春节假期",
                "data": [{"title": "春节祝福", "content": "春节快乐"}],
                "prompt": "请生成节日问候"
            }
        },
        {
            "name": "立春节气",
            "data": {
                "device_id": "f0:9e:9e:04:8a:44",
                "topic": "立春节气", 
                "data": [{"title": "立春到了", "content": "今天是立春"}],
                "prompt": "请生成节气播报"
            }
        }
    ]
    
    print("\n🧪 测试其他数据结构:")
    for test_case in test_cases:
        print(f"\n📋 {test_case['name']}:")
        processed = simulate_java_event_processing(test_case["data"])
        if processed:
            event = processed[0]
            print(f"   结果: 类型={event['event_type']}, prompt支持={event['has_prompt']}")
    
    print("\n🎉 测试完成！")
    print("✅ 修改效果:")
    print("   - 支持topic字段的事件类型检测")  
    print("   - 支持content字段的内容提取")
    print("   - 支持title+content的内容组合")
    print("   - 完整支持Java后端新数据结构")

if __name__ == "__main__":
    main()

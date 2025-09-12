#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP等待提示功能测试脚本
验证在MCP查询前是否正确播放等待提示
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.providers.tools.mcp_waiting_assistant import mcp_waiting_assistant

def test_waiting_messages():
    """测试等待提示消息生成"""
    
    print("🎭 MCP等待提示功能测试")
    print("=" * 50)
    
    # 测试不同类型的查询
    test_cases = [
        {
            "tool_name": "bailian_web_search",
            "arguments": {"query": "今天有什么新闻"},
            "user_query": "今天社区有什么新闻",
            "expected_type": "news"
        },
        {
            "tool_name": "bailian_web_search", 
            "arguments": {"query": "北京天气"},
            "user_query": "今天天气怎么样",
            "expected_type": "weather"
        },
        {
            "tool_name": "bailian_web_search",
            "arguments": {"query": "苹果股价"},
            "user_query": "苹果股票价格",
            "expected_type": "stock"
        },
        {
            "tool_name": "bailian_web_search",
            "arguments": {"query": "人工智能发展"},
            "user_query": "人工智能的发展趋势",
            "expected_type": "search"
        },
        {
            "tool_name": "unknown_tool",
            "arguments": {"param": "test"},
            "user_query": "测试查询",
            "expected_type": "general"
        }
    ]
    
    print("📋 测试等待提示消息生成:")
    for i, case in enumerate(test_cases, 1):
        print(f"\n  {i}. 工具: {case['tool_name']}")
        print(f"     查询: '{case['user_query']}'")
        
        # 生成等待提示
        waiting_msg = mcp_waiting_assistant.generate_waiting_message(
            case["tool_name"], 
            case["arguments"], 
            case["user_query"]
        )
        
        print(f"     提示: '{waiting_msg}'")
        
        # 测试是否需要显示等待提示
        should_show = mcp_waiting_assistant.should_show_waiting_message(case["tool_name"])
        print(f"     显示: {'✅ 是' if should_show else '❌ 否'}")
    
    print(f"\n📋 测试工具类型检测:")
    
    # 测试各种工具名称
    tool_names = [
        "bailian_web_search",
        "search_tool", 
        "web_search",
        "news_tool",
        "weather_api",
        "stock_query",
        "unknown_tool"
    ]
    
    for tool_name in tool_names:
        should_show = mcp_waiting_assistant.should_show_waiting_message(tool_name)
        status = "✅ 显示等待提示" if should_show else "❌ 不显示"
        print(f"    {tool_name}: {status}")
    
    print(f"\n📋 测试查询类型检测:")
    
    # 测试查询类型检测
    query_tests = [
        ("今天有什么新闻", "news"),
        ("北京天气怎么样", "weather"), 
        ("苹果股价多少", "stock"),
        ("搜索人工智能", "search"),
        ("随机查询", "general")
    ]
    
    for query, expected in query_tests:
        detected = mcp_waiting_assistant._detect_query_type("bailian_web_search", {}, query)
        status = "✅" if detected == expected else "❌"
        print(f"    '{query}' → {detected} {status}")
    
    print("\n" + "=" * 50)
    print("✅ MCP等待提示功能测试完成！")
    
    print(f"\n💡 功能说明:")
    print(f"  1. 当调用MCP工具时，会先播放等待提示")
    print(f"  2. 根据查询内容智能选择合适的提示语")
    print(f"  3. 提示语随机选择，避免重复")
    print(f"  4. 只对慢速工具（如搜索）显示等待提示")
    
    print(f"\n🎯 使用效果:")
    print(f"  用户: '今天有什么新闻'")
    print(f"  系统: '让我帮您搜索一下最新新闻...' (立即播放)")
    print(f"  系统: (等待MCP搜索完成)")
    print(f"  系统: '根据搜索结果，今天的主要新闻有...' (播放搜索结果)")

if __name__ == "__main__":
    test_waiting_messages()

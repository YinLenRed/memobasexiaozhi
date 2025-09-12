#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻功能测试脚本
验证LLM是否能正确调用新闻函数
"""

import yaml
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from plugins_func.register import all_function_registry
from core.providers.tools.server_plugins.plugin_executor import ServerPluginExecutor

def test_news_functions():
    """测试新闻函数是否正确注册和可用"""
    
    print("🔍 新闻功能测试")
    print("=" * 50)
    
    # 1. 检查函数是否在注册表中
    news_functions = [
        "get_news_from_chinanews", 
        "get_news_from_newsnow"
    ]
    
    print("📋 检查函数注册状态:")
    for func_name in news_functions:
        if func_name in all_function_registry:
            func_item = all_function_registry[func_name]
            print(f"  ✅ {func_name}: 已注册")
            print(f"     描述: {func_item.description['function']['description'][:80]}...")
        else:
            print(f"  ❌ {func_name}: 未注册")
    
    # 2. 检查配置文件
    print("\n📋 检查配置文件:")
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        function_call_functions = config.get('Intent', {}).get('function_call', {}).get('functions', [])
        intent_llm_functions = config.get('Intent', {}).get('intent_llm', {}).get('functions', [])
        
        print(f"  function_call.functions: {len(function_call_functions)} 个函数")
        for func_name in news_functions:
            if func_name in function_call_functions:
                print(f"    ✅ {func_name}")
            else:
                print(f"    ❌ {func_name}")
                
        print(f"  intent_llm.functions: {len(intent_llm_functions)} 个函数")
        for func_name in news_functions:
            if func_name in intent_llm_functions:
                print(f"    ✅ {func_name}")
            else:
                print(f"    ❌ {func_name}")
                
    except Exception as e:
        print(f"  ❌ 配置文件读取失败: {e}")
    
    # 3. 模拟工具执行器测试
    print("\n📋 模拟工具执行器测试:")
    try:
        # 创建一个模拟的连接对象
        class MockConn:
            def __init__(self):
                with open('config.yaml', 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                    
        mock_conn = MockConn()
        executor = ServerPluginExecutor(mock_conn)
        tools = executor.get_tools()
        
        print(f"  总工具数: {len(tools)}")
        for func_name in news_functions:
            if func_name in tools:
                print(f"    ✅ {func_name}: 可用")
            else:
                print(f"    ❌ {func_name}: 不可用")
                
    except Exception as e:
        print(f"  ❌ 工具执行器测试失败: {e}")
    
    # 4. 生成函数描述列表
    print("\n📋 生成函数描述 (LLM可见的函数):")
    try:
        descriptions = []
        for func_name in news_functions:
            if func_name in all_function_registry:
                func_item = all_function_registry[func_name]
                descriptions.append(func_item.description)
        
        print(f"  新闻函数描述数: {len(descriptions)}")
        for i, desc in enumerate(descriptions, 1):
            func_info = desc['function']
            print(f"    {i}. {func_info['name']}")
            print(f"       描述: {func_info['description'][:80]}...")
            
    except Exception as e:
        print(f"  ❌ 函数描述生成失败: {e}")
    
    print("\n" + "=" * 50)
    print("✅ 测试完成！")
    print("\n💡 如果所有项目都显示 ✅，说明新闻功能配置正确")
    print("💡 如果有 ❌，请检查对应的配置或注册问题")

if __name__ == "__main__":
    test_news_functions()

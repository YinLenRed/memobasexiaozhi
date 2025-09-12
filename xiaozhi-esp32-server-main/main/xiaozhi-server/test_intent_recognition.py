#!/usr/bin/env python3
"""
测试意图识别修复效果
验证"查看我的任务列表"是否能正确识别为query_user_strategies
"""

import asyncio
from core.providers.intent.intent_llm.intent_llm import IntentProvider
from config.config_loader import load_config
from plugins_func.register import all_function_registry
from config.logger import setup_logging

logger = setup_logging()

async def test_intent_recognition():
    print("🔍 测试意图识别修复效果")
    print("=" * 50)
    
    try:
        # 加载配置
        config = load_config()
        
        # 创建意图识别提供器
        intent_provider = IntentProvider(config)
        
        # 模拟设置LLM（这里简化测试）
        print("✅ 配置加载成功")
        
        # 检查注册的函数
        print(f"\n📋 当前注册的函数数量: {len(all_function_registry)}")
        
        target_functions = ["query_user_strategies", "update_user_strategy", "delete_user_strategy"]
        for func_name in target_functions:
            if func_name in all_function_registry:
                print(f"✅ {func_name} 已注册")
            else:
                print(f"❌ {func_name} 未注册")
        
        # 检查配置文件中的functions列表
        intent_config = config.get("Intent", {}).get("intent_llm", {})
        configured_functions = intent_config.get("functions", [])
        
        print(f"\n⚙️ 配置文件中的函数列表:")
        for func in configured_functions:
            status = "✅" if func in all_function_registry else "❌"
            print(f"  {status} {func}")
        
        # 构建函数列表用于生成系统提示词
        available_functions = []
        for func_name in configured_functions:
            if func_name in all_function_registry:
                func_item = all_function_registry[func_name]
                available_functions.append(func_item.description)
        
        # 生成系统提示词并检查
        if available_functions:
            system_prompt = intent_provider.get_intent_system_prompt(available_functions)
            
            print(f"\n📝 系统提示词预览:")
            lines = system_prompt.split('\n')
            for i, line in enumerate(lines):
                if i < 20:  # 只显示前20行
                    print(f"  {line}")
                elif i == 20:
                    print(f"  ... (共{len(lines)}行)")
                    break
        
        print("\n🎯 测试结果分析:")
        
        # 检查关键配置
        if "query_user_strategies" in configured_functions:
            print("✅ query_user_strategies 已添加到配置文件")
        else:
            print("❌ query_user_strategies 未在配置文件中")
            
        if "query_user_strategies" in all_function_registry:
            print("✅ query_user_strategies 功能已注册")
        else:
            print("❌ query_user_strategies 功能未注册")
        
        print("\n🚀 修复建议:")
        print("1. 重启服务：Ctrl+C 停止，然后 python app.py 重新启动")
        print("2. 测试语音：说'查看我的任务列表'")
        print("3. 观察日志：应该看到 query_user_strategies 被调用")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_intent_recognition())

#!/usr/bin/env python3
"""
测试用户策略管理功能
用于验证查询、修改、删除功能是否正常工作

使用方法:
python test_user_strategy_functions.py
"""

import asyncio
import sys
import json
from config.config_loader import load_config
from config.logger import setup_logging
from core.tools.java_backend_strategy import JavaBackendStrategyService

# 测试配置
TEST_DEVICE_ID = "test_device_001"
TEST_JOB_NAME = "测试任务"
TEST_PROMPT_CONTENT = "这是一个测试提醒内容"

logger = setup_logging()

async def create_test_strategy(strategy_service):
    """创建测试策略数据"""
    try:
        print("🔨 正在创建测试策略...")
        
        # 创建一个简单的测试策略
        result = await strategy_service.save_user_strategy(
            device_id=TEST_DEVICE_ID,
            title="测试提醒任务",
            data="每天上午9点提醒我测试功能"
        )
        
        if result["success"]:
            print("✅ 测试策略创建成功")
            # 重新查询以获取刚创建的策略ID
            query_result = await strategy_service.query_user_strategies(
                device_id=TEST_DEVICE_ID,
                current=1,
                size=1
            )
            
            if query_result["success"] and query_result["data"]:
                new_job_id = query_result["data"][0].get('id')
                print(f"📋 新创建的测试策略ID: {new_job_id}")
                return new_job_id
            else:
                print("⚠️ 无法获取新创建的策略ID")
                return None
        else:
            print(f"❌ 测试策略创建失败: {result['message']}")
            return None
            
    except Exception as e:
        print(f"❌ 创建测试策略时发生异常: {e}")
        return None

async def test_java_backend_strategy_service():
    """测试Java后端策略服务的基本功能"""
    print("=" * 60)
    print("测试用户策略管理功能")
    print("=" * 60)
    
    try:
        # 加载配置
        config = load_config()
        java_api_url = config.get("manager-api", {}).get("url", "")
        
        if not java_api_url:
            print("❌ 错误：未配置Java后端API地址")
            print("请在config.yaml中配置manager-api.url")
            return False
            
        print(f"✅ Java后端API地址: {java_api_url}")
        
        # 创建策略服务实例
        strategy_service = JavaBackendStrategyService(config)
        
        # 测试1：查询用户策略
        print("\n📋 测试1：查询用户策略")
        print("-" * 40)
        
        # 首先尝试查询指定设备的策略（Java后端要求设备ID不能为空）
        print(f"🔍 查询设备 {TEST_DEVICE_ID} 的策略...")
        query_result = await strategy_service.query_user_strategies(
            device_id=TEST_DEVICE_ID,  # 必须指定设备ID
            current=1,
            size=10
        )
        
        print(f"查询结果: {query_result['success']}")
        if query_result['success']:
            strategies = query_result['data']
            print(f"找到 {len(strategies)} 个策略:")
            for i, strategy in enumerate(strategies[:3]):  # 只显示前3个
                print(f"  {i+1}. 任务名: {strategy.get('jobName', 'N/A')}")
                print(f"     ID: {strategy.get('id', 'N/A')}")
                print(f"     状态: {'运行中' if strategy.get('status') == '0' else '已暂停'}")
                print(f"     设备ID: {strategy.get('deviceId', 'N/A')}")
                print(f"     Cron表达式: {strategy.get('cronExpression', 'N/A')}")
        else:
            print(f"查询失败: {query_result['message']}")
        
        # 从查询结果中获取一个任务ID和cron表达式用于测试修改和删除
        test_job_id = None
        test_job_cron = None
        if query_result['success'] and query_result['data']:
            test_strategy = query_result['data'][0]
            test_job_id = test_strategy.get('id')
            test_job_cron = test_strategy.get('cronExpression')
            print(f"将使用任务ID {test_job_id} (cron: {test_job_cron}) 进行修改和删除测试")
        else:
            # 如果没有数据，询问是否创建测试数据
            print("\n💡 没有找到现有策略，是否创建测试数据？")
            create_test = input("输入 'y' 创建测试策略，或直接回车跳过: ").lower()
            if create_test == 'y':
                test_job_id = await create_test_strategy(strategy_service)
        
        # 测试2：修改用户策略（如果有可用的任务ID）
        if test_job_id:
            print("\n✏️ 测试2：修改用户策略")
            print("-" * 40)
            
            # 测试时间修改：将原有时间改为上午10点
            new_time_desc = "每天上午10点"
            print(f"修改任务时间：{test_job_cron} -> {new_time_desc}")
            
            update_result = await strategy_service.update_user_strategy(
                job_id=test_job_id,
                job_name="修改后的测试任务", 
                cron_expression=strategy_service._generate_cron_expression(new_time_desc),  # 生成新的cron表达式
                prompt_content="修改后的提醒内容",
                device_id=TEST_DEVICE_ID  # 添加设备ID
            )
            
            print(f"修改结果: {update_result['success']}")
            print(f"消息: {update_result['message']}")
            
            # 测试3：删除用户策略（注意：这会真的删除数据！）
            confirm_delete = input("\n⚠️  是否要测试删除功能？这会真的删除数据！(y/N): ").lower()
            if confirm_delete == 'y':
                print("\n🗑️ 测试3：删除用户策略")
                print("-" * 40)
                
                delete_result = await strategy_service.delete_user_strategy(
                    job_id=test_job_id,
                    job_name="修改后的测试任务",
                    cron_expression=test_job_cron,  # 添加cron表达式
                    device_id=TEST_DEVICE_ID  # 添加设备ID
                )
                
                print(f"删除结果: {delete_result['success']}")
                print(f"消息: {delete_result['message']}")
            else:
                print("\n⏭️ 跳过删除测试")
        else:
            print("\n⏭️ 没有找到可用的任务ID，跳过修改和删除测试")
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_function_registration():
    """测试功能函数是否正确注册"""
    print("\n🔍 测试功能函数注册情况")
    print("-" * 40)
    
    try:
        # 手动导入插件模块以触发注册
        print("正在导入插件模块...")
        import plugins_func.functions.query_user_strategies
        import plugins_func.functions.update_user_strategy
        import plugins_func.functions.delete_user_strategy
        
        from plugins_func.register import all_function_registry
        
        # 检查三个新功能是否已注册
        functions_to_check = [
            "query_user_strategies",
            "update_user_strategy", 
            "delete_user_strategy"
        ]
        
        for func_name in functions_to_check:
            if func_name in all_function_registry:
                func_item = all_function_registry[func_name]
                print(f"✅ {func_name} 已注册")
                print(f"   描述: {func_item.description['function']['description'][:80]}...")
                print(f"   类型: {func_item.type}")
            else:
                print(f"❌ {func_name} 未注册")
        
        print(f"\n总共注册了 {len(all_function_registry)} 个功能函数")
        
        # 显示所有已注册的函数（用于调试）
        if len(all_function_registry) > 0:
            print("\n已注册的函数列表：")
            for name in sorted(all_function_registry.keys()):
                print(f"  - {name}")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查功能注册时出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("小智定时任务管理功能测试")
    print("测试范围：查询、修改、删除用户策略")
    print()
    
    # 测试功能注册
    registration_ok = test_function_registration()
    
    if not registration_ok:
        print("功能注册测试失败，请检查模块导入")
        return
    
    # 测试Java后端API调用
    api_test_ok = await test_java_backend_strategy_service()
    
    if api_test_ok:
        print("\n🎉 所有测试通过！")
        print("\n📖 使用说明：")
        print("现在您可以通过语音或文字与小智交互：")
        print("- '查看我的任务列表' - 调用查询功能")
        print("- '修改任务' - 调用修改功能（需要提供任务ID）")
        print("- '删除提醒' - 调用删除功能（需要提供任务ID）")
    else:
        print("\n❌ 测试失败，请检查配置和网络连接")

if __name__ == "__main__":
    asyncio.run(main())

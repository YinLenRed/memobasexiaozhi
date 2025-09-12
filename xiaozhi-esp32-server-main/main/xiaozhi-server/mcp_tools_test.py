#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP工具测试脚本
验证阿里云百炼联网搜索是否正常工作
"""

import asyncio
import sys
import os
import json

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config_loader import load_config
from core.providers.tools.server_mcp.mcp_manager import ServerMCPManager

class MockConn:
    def __init__(self):
        self.config = load_config()
        self.device_id = 'test-device'
        self.func_handler = None

async def test_mcp_tools():
    """测试MCP工具是否正常工作"""
    
    print("🔍 MCP工具测试")
    print("=" * 50)
    
    # 1. 检查MCP配置文件
    config_path = "data/.mcp_server_settings.json"
    print(f"📋 检查MCP配置文件: {config_path}")
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        servers = config.get('mcpServers', {})
        print(f"  ✅ 配置文件存在，共 {len(servers)} 个MCP服务:")
        
        for name, srv_config in servers.items():
            print(f"    - {name}: {srv_config.get('description', 'No description')[:80]}...")
            print(f"      URL: {srv_config.get('url', 'No URL')}")
            print(f"      API Token: {'已配置' if srv_config.get('API_ACCESS_TOKEN') else '未配置'}")
    else:
        print(f"  ❌ 配置文件不存在: {config_path}")
        return
    
    # 2. 初始化MCP管理器
    print(f"\n📋 初始化MCP管理器:")
    try:
        conn = MockConn()
        mcp_manager = ServerMCPManager(conn)
        
        print("  🔄 正在初始化MCP服务...")
        await mcp_manager.initialize_servers()
        
        print(f"  ✅ MCP管理器初始化完成")
        print(f"  📊 已连接的MCP客户端: {len(mcp_manager.clients)}")
        
        for name, client in mcp_manager.clients.items():
            print(f"    - {name}: 连接状态未知")
            
    except Exception as e:
        print(f"  ❌ MCP管理器初始化失败: {e}")
        return
    
    # 3. 获取所有可用工具
    print(f"\n📋 获取MCP工具列表:")
    try:
        all_tools = mcp_manager.get_all_tools()
        print(f"  ✅ 共获取到 {len(all_tools)} 个MCP工具:")
        
        for i, tool in enumerate(all_tools, 1):
            func_info = tool.get('function', {})
            name = func_info.get('name', 'Unknown')
            desc = func_info.get('description', 'No description')
            
            print(f"    {i}. {name}")
            print(f"       描述: {desc[:100]}...")
            
            # 检查是否是搜索相关工具
            if any(keyword in name.lower() or keyword in desc.lower() 
                   for keyword in ['search', 'web', 'bailian', 'news']):
                print(f"       🎯 这个工具可用于新闻搜索！")
                
    except Exception as e:
        print(f"  ❌ 获取工具列表失败: {e}")
        return
    
    # 4. 测试智能过滤器
    print(f"\n📋 测试智能MCP过滤器:")
    try:
        from core.providers.intent.smart_mcp_filter import smart_mcp_filter
        
        # 模拟新闻查询
        test_text = "今天社区有什么新闻"
        filter_result = smart_mcp_filter.should_enable_mcp(test_text)
        
        print(f"  查询文本: '{test_text}'")
        print(f"  过滤结果: {filter_result}")
        
        if filter_result.get('enabled', filter_result.get('enable_mcp', False)):
            filtered_tools = smart_mcp_filter.get_filtered_mcp_tools(all_tools, filter_result)
            print(f"  🎯 过滤后可用工具数: {len(filtered_tools)}")
            
            for tool in filtered_tools:
                func_info = tool.get('function', {})
                print(f"    - {func_info.get('name', 'Unknown')}")
        else:
            print(f"  ❌ 智能过滤器认为不需要启用MCP")
            
    except Exception as e:
        print(f"  ❌ 智能过滤器测试失败: {e}")
    
    # 5. 尝试调用搜索工具（如果有的话）
    print(f"\n📋 尝试调用搜索工具:")
    try:
        if all_tools:
            # 找到第一个搜索相关工具
            search_tool = None
            for tool in all_tools:
                func_info = tool.get('function', {})
                name = func_info.get('name', '')
                desc = func_info.get('description', '')
                
                if any(keyword in name.lower() or keyword in desc.lower() 
                       for keyword in ['search', 'web', 'bailian']):
                    search_tool = tool
                    break
            
            if search_tool:
                tool_name = search_tool['function']['name']
                print(f"  🔍 找到搜索工具: {tool_name}")
                
                # 尝试调用工具
                test_query = "今天有什么新闻"
                print(f"  🔄 测试查询: '{test_query}'")
                
                # 尝试不同的参数格式
                try:
                    result = await mcp_manager.execute_tool(tool_name, {"query": test_query})
                except Exception as e1:
                    print(f"    ⚠️  参数格式1失败: {e1}")
                    try:
                        result = await mcp_manager.execute_tool(tool_name, {"search_query": test_query})
                    except Exception as e2:
                        print(f"    ⚠️  参数格式2失败: {e2}")
                        try:
                            result = await mcp_manager.execute_tool(tool_name, {"text": test_query})
                        except Exception as e3:
                            print(f"    ⚠️  参数格式3失败: {e3}")
                            result = None
                
                if hasattr(result, 'response') and result.response:
                    print(f"  ✅ 搜索成功，结果长度: {len(result.response)} 字符")
                    print(f"  📄 结果预览: {result.response[:200]}...")
                else:
                    print(f"  ❌ 搜索失败或无结果")
                    
            else:
                print(f"  ❌ 未找到可用的搜索工具")
                
    except Exception as e:
        print(f"  ❌ 工具调用失败: {e}")
    
    print("\n" + "=" * 50)
    print("✅ MCP工具测试完成！")
    
    if all_tools:
        print(f"\n💡 建议:")
        print(f"  1. 如果有搜索工具，说明MCP配置正确")
        print(f"  2. 如果LLM仍返回 query_news，可能需要检查工具名称匹配")
        print(f"  3. 重启服务后测试: '今天社区有什么新闻'")
    else:
        print(f"\n⚠️  警告:")
        print(f"  没有获取到任何MCP工具，请检查:")
        print(f"  1. 阿里云API Token是否有效")
        print(f"  2. 网络连接是否正常")
        print(f"  3. MCP服务是否正常运行")

if __name__ == "__main__":
    asyncio.run(test_mcp_tools())

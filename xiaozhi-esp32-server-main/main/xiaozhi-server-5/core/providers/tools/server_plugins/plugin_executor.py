"""服务端插件工具执行器"""

from typing import Dict, Any
from ..base import ToolType, ToolDefinition, ToolExecutor
from plugins_func.register import all_function_registry, Action, ActionResponse


class ServerPluginExecutor(ToolExecutor):
    """服务端插件工具执行器"""

    def __init__(self, conn):
        self.conn = conn
        self.config = conn.config

    async def execute(
        self, conn, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """执行服务端插件工具"""
        func_item = all_function_registry.get(tool_name)
        if not func_item:
            return ActionResponse(
                action=Action.NOTFOUND, response=f"插件函数 {tool_name} 不存在"
            )

        try:
            # 根据工具类型决定如何调用
            if hasattr(func_item, "type"):
                func_type = func_item.type
                if func_type.code in [4, 5]:  # SYSTEM_CTL, IOT_CTL (需要conn参数)
                    result = func_item.func(conn, **arguments)
                elif func_type.code == 2:  # WAIT
                    result = func_item.func(**arguments)
                elif func_type.code == 3:  # CHANGE_SYS_PROMPT
                    result = func_item.func(conn, **arguments)
                else:
                    result = func_item.func(**arguments)
            else:
                # 默认不传conn参数
                result = func_item.func(**arguments)

            # 🔍 调试日志：追踪ServerPluginExecutor返回值
            if hasattr(result, 'action') and hasattr(result, 'response'):
                response_len = len(result.response) if result.response else 0
                self.conn.logger.info(f"🎤 ServerPluginExecutor返回: action={result.action}, response长度={response_len}")
                if result.response:
                    self.conn.logger.info(f"🎤 ServerPluginExecutor返回内容: {result.response[:50]}...")
            
            return result

        except Exception as e:
            return ActionResponse(
                action=Action.ERROR,
                response=str(e),
            )

    def get_tools(self) -> Dict[str, ToolDefinition]:
        """获取所有注册的服务端插件工具"""
        tools = {}

        # 获取必要的函数
        necessary_functions = ["handle_exit_intent", "get_lunar", "save_user_strategy"]

        # 🚨 临时补充函数：Java后端配置可能尚未包含的新函数
        # 这些函数在Python端已实现，但Java配置可能需要手动更新
        supplement_functions = [
            "schedule_relative_timer",
            "list_relative_timers", 
            "cancel_relative_timer",
            "modify_relative_timer",
            "query_user_strategies",    # 用户策略查询功能
            "update_user_strategy",     # 用户策略修改功能
            "delete_user_strategy"      # 用户策略删除功能
        ]

        # 获取配置中的函数
        config_functions = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ].get("functions", [])

        # 转换为列表
        if not isinstance(config_functions, list):
            try:
                config_functions = list(config_functions)
            except TypeError:
                config_functions = []

        # 合并所有需要的函数：必要函数 + 配置函数 + 补充函数
        all_required_functions = list(set(necessary_functions + config_functions + supplement_functions))

        for func_name in all_required_functions:
            func_item = all_function_registry.get(func_name)
            if func_item:
                tools[func_name] = ToolDefinition(
                    name=func_name,
                    description=func_item.description,
                    tool_type=ToolType.SERVER_PLUGIN,
                )

        return tools

    def has_tool(self, tool_name: str) -> bool:
        """检查是否有指定的服务端插件工具"""
        return tool_name in all_function_registry

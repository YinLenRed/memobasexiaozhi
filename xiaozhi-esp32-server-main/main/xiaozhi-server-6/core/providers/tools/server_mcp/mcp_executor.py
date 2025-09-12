"""服务端MCP工具执行器"""

from typing import Dict, Any, Optional
from ..base import ToolType, ToolDefinition, ToolExecutor
from plugins_func.register import Action, ActionResponse
from .mcp_manager import ServerMCPManager


class ServerMCPExecutor(ToolExecutor):
    """服务端MCP工具执行器"""

    def __init__(self, conn):
        self.conn = conn
        self.mcp_manager: Optional[ServerMCPManager] = None
        self._initialized = False

    async def initialize(self):
        """初始化MCP管理器"""
        if not self._initialized:
            self.mcp_manager = ServerMCPManager(self.conn)
            await self.mcp_manager.initialize_servers()
            self._initialized = True

    async def execute(
        self, conn, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """执行服务端MCP工具"""
        if not self._initialized or not self.mcp_manager:
            return ActionResponse(
                action=Action.ERROR,
                response="MCP管理器未初始化",
            )

        try:
            # 移除mcp_前缀（如果有）
            actual_tool_name = tool_name
            if tool_name.startswith("mcp_"):
                actual_tool_name = tool_name[4:]

            result = await self.mcp_manager.execute_tool(actual_tool_name, arguments)

            # 如果是搜索工具，过滤结果中的技术信息
            if actual_tool_name in ["bocha_web_search", "bocha_ai_search"]:
                filtered_result = self._filter_search_result(str(result))
                return ActionResponse(action=Action.REQLLM, result=filtered_result)
            
            return ActionResponse(action=Action.REQLLM, result=str(result))

        except ValueError as e:
            return ActionResponse(
                action=Action.NOTFOUND,
                response=str(e),
            )
        except Exception as e:
            return ActionResponse(
                action=Action.ERROR,
                response=str(e),
            )

    def get_tools(self) -> Dict[str, ToolDefinition]:
        """获取所有服务端MCP工具"""
        if not self._initialized or not self.mcp_manager:
            return {}

        tools = {}
        mcp_tools = self.mcp_manager.get_all_tools()

        for tool in mcp_tools:
            func_def = tool.get("function", {})
            tool_name = func_def.get("name", "")
            if tool_name == "":
                continue
            tools[tool_name] = ToolDefinition(
                name=tool_name, description=tool, tool_type=ToolType.SERVER_MCP
            )

        return tools

    def has_tool(self, tool_name: str) -> bool:
        """检查是否有指定的服务端MCP工具"""
        if not self._initialized or not self.mcp_manager:
            return False

        # 移除mcp_前缀（如果有）
        actual_tool_name = tool_name
        if tool_name.startswith("mcp_"):
            actual_tool_name = tool_name[4:]

        return self.mcp_manager.is_mcp_tool(actual_tool_name)

    def _filter_search_result(self, result: str) -> str:
        """过滤搜索结果中的技术信息，只保留用户关心的内容"""
        import re
        
        # 移除URL链接
        result = re.sub(r'URL：[^\s\n]+', '', result)
        result = re.sub(r'https?://[^\s\n]+', '', result)
        
        # 移除发布日期信息
        result = re.sub(r'发布日期：[^\n]+', '', result)
        result = re.sub(r'时间：[^\n]+', '', result)
        
        # 移除来源信息（但保留标题后的来源）
        result = re.sub(r'来源：([^\n]+)(?=\n|$)', r'', result)
        
        # 清理多余的空行和空格
        result = re.sub(r'\n\s*\n', '\n', result)
        result = re.sub(r'^\s+|\s+$', '', result, flags=re.MULTILINE)
        
        # 如果结果为空或过短，返回友好提示
        if len(result.strip()) < 10:
            return "搜索到了相关信息，但内容比较简单，建议您换个关键词再试试。"
        
        return result.strip()

    async def cleanup(self):
        """清理MCP连接"""
        if self.mcp_manager:
            await self.mcp_manager.cleanup_all()

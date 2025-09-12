"""
MCP等待提示助手
在MCP查询期间生成并播放等待提示，提升用户体验
"""

import asyncio
import random
from typing import Dict, Any, Optional
from config.logger import setup_logging
from core.providers.tts.dto.dto import ContentType

TAG = __name__
logger = setup_logging()


class MCPWaitingAssistant:
    """MCP等待提示助手"""
    
    def __init__(self):
        # 不同查询类型的等待提示模板
        self.waiting_messages = {
            "news": [
                "让我帮您搜索一下最新新闻...",
                "正在为您查找新闻资讯，请稍等...",
                "我来看看有什么新闻...",
                "稍等一下，我去搜索最新消息...",
                "让我查查最近发生了什么...",
            ],
            "weather": [
                "让我查一下天气情况...",
                "正在获取天气信息，请稍等...",
                "我来看看天气预报...",
                "稍等，我查查天气...",
            ],
            "search": [
                "让我帮您搜索一下...",
                "正在搜索相关信息，请稍等...",
                "我来查找相关资料...",
                "稍等一下，我去搜索...",
                "让我找找相关信息...",
            ],
            "stock": [
                "让我查一下股市行情...",
                "正在获取股票信息，请稍等...",
                "我来看看市场情况...",
                "稍等，我查查股价...",
            ],
            "general": [
                "让我帮您查询一下...",
                "正在处理您的请求，请稍等...",
                "我来查找相关信息...",
                "稍等一下，正在搜索...",
                "让我为您查询...",
            ]
        }
    
    def _detect_query_type(self, tool_name: str, arguments: Dict[str, Any], user_query: str = "") -> str:
        """检测查询类型"""
        tool_name_lower = tool_name.lower()
        user_query_lower = user_query.lower()
        
        # 根据工具名称判断
        if "news" in tool_name_lower or "新闻" in user_query_lower:
            return "news"
        elif "weather" in tool_name_lower or any(word in user_query_lower for word in ["天气", "温度", "下雨", "晴天"]):
            return "weather"
        elif "stock" in tool_name_lower or any(word in user_query_lower for word in ["股票", "股价", "股市"]):
            return "stock"
        elif any(word in tool_name_lower for word in ["search", "web", "bailian"]):
            # 进一步细分搜索类型
            if any(word in user_query_lower for word in ["新闻", "消息", "资讯"]):
                return "news"
            elif any(word in user_query_lower for word in ["天气", "温度"]):
                return "weather"
            elif any(word in user_query_lower for word in ["股票", "股价"]):
                return "stock"
            else:
                return "search"
        else:
            return "general"
    
    def generate_waiting_message(self, tool_name: str, arguments: Dict[str, Any], user_query: str = "") -> str:
        """生成等待提示消息"""
        query_type = self._detect_query_type(tool_name, arguments, user_query)
        messages = self.waiting_messages.get(query_type, self.waiting_messages["general"])
        
        # 随机选择一个提示消息
        waiting_msg = random.choice(messages)
        
        logger.bind(tag=TAG).info(f"🎭 生成MCP等待提示: 类型={query_type}, 消息='{waiting_msg}'")
        return waiting_msg
    
    async def play_waiting_message(self, conn, tool_name: str, arguments: Dict[str, Any], user_query: str = "") -> bool:
        """播放等待提示消息"""
        try:
            if not hasattr(conn, 'tts') or conn.tts is None:
                logger.bind(tag=TAG).warning("TTS不可用，跳过等待提示")
                return False
            
            waiting_msg = self.generate_waiting_message(tool_name, arguments, user_query)
            
            # 播放等待提示
            logger.bind(tag=TAG).info(f"🎵 播放MCP等待提示: '{waiting_msg}'")
            
            # 使用TTS播放等待消息
            conn.tts.tts_one_sentence(
                conn, 
                ContentType.TEXT, 
                content_detail=waiting_msg
            )
            
            # 等待一小段时间确保消息开始播放
            await asyncio.sleep(0.5)
            
            return True
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"播放MCP等待提示失败: {e}")
            return False
    
    def should_show_waiting_message(self, tool_name: str) -> bool:
        """判断是否需要显示等待提示"""
        # 对于MCP工具（通常比较慢），显示等待提示
        mcp_keywords = ["search", "web", "bailian", "news", "weather", "stock"]
        tool_name_lower = tool_name.lower()
        
        return any(keyword in tool_name_lower for keyword in mcp_keywords)


# 全局实例
mcp_waiting_assistant = MCPWaitingAssistant()

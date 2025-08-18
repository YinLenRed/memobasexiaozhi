"""
工具模块 - 集成外部服务和工具
"""

# 天气工具
from .weather_tool import WeatherTool, get_weather_info, WEATHER_FUNCTION_DEFINITION

# 记忆数据库工具  
from .memobase_client import MemobaseClient, get_user_memory_text, MEMORY_FUNCTION_DEFINITION

# 新闻工具
from .news_tool import NewsTool, get_news_info, NEWS_FUNCTION_DEFINITION, execute_news_function

__all__ = [
    # 天气工具
    "WeatherTool",
    "get_weather_info", 
    "WEATHER_FUNCTION_DEFINITION",
    
    # 记忆数据库工具
    "MemobaseClient",
    "get_user_memory_text",
    "MEMORY_FUNCTION_DEFINITION",
    
    # 新闻工具
    "NewsTool",
    "get_news_info",
    "NEWS_FUNCTION_DEFINITION",
    "execute_news_function"
]

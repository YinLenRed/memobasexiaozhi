# MQTT模块初始化文件

from .mqtt_client import MQTTClient
from .mqtt_manager import MQTTManager
from .proactive_greeting_service import ProactiveGreetingService

# 工具导入
from ..tools.weather_tool import WeatherTool, get_weather_info, WEATHER_FUNCTION_DEFINITION
from ..tools.memobase_client import MemobaseClient, get_user_memory_text, MEMORY_FUNCTION_DEFINITION
from ..tools.news_tool import NewsTool, get_news_info, NEWS_FUNCTION_DEFINITION, execute_news_function
from ..tools.music_tool import MusicTool, get_music_info, MUSIC_FUNCTION_DEFINITION, execute_music_function

__all__ = [
    "MQTTClient",
    "MQTTManager", 
    "ProactiveGreetingService",
    # Weather tools
    "WeatherTool",
    "get_weather_info",
    "WEATHER_FUNCTION_DEFINITION",
    # Memory tools
    "MemobaseClient",
    "get_user_memory_text", 
    "MEMORY_FUNCTION_DEFINITION",
    # News tools
    "NewsTool",
    "get_news_info",
    "NEWS_FUNCTION_DEFINITION",
    "execute_news_function",
    # Music tools
    "MusicTool",
    "get_music_info",
    "MUSIC_FUNCTION_DEFINITION", 
    "execute_music_function"
]

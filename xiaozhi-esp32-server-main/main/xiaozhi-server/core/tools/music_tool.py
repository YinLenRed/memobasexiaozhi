"""
音乐播放工具 - 集成Java后端音乐API
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from config.logger import setup_logging

TAG = __name__


class MusicTool:
    """音乐播放工具，调用Java后端API获取音乐推荐和播放信息"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()
        
        # Java后端API配置
        self.java_api_base = config.get("manager-api", {}).get("url", "")
        self.api_secret = config.get("manager-api", {}).get("secret", "")
        
    async def get_music_recommendation(self, device_id: str, music_type: str = "relaxing", user_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """根据设备ID和音乐类型获取音乐推荐（通过Java后端API）"""
        try:
            if not self.java_api_base or not self.api_secret:
                self.logger.bind(tag=TAG).warning("Java API配置不完整，使用默认音乐推荐")
                return self._get_default_music(music_type)
            
            # 调用Java后端音乐推荐API
            url = f"{self.java_api_base}/api/music/recommend"
            headers = {
                "Authorization": f"Bearer {self.api_secret}",
                "Content-Type": "application/json"
            }
            
            data = {
                "device_id": device_id,
                "music_type": music_type,
                "user_info": user_info or {},
                "limit": 5
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=10) as response:
                    if response.status == 200:
                        music_data = await response.json()
                        self.logger.bind(tag=TAG).info(f"获取设备 {device_id} 的{music_type}音乐推荐成功")
                        return self._format_music_data(music_data.get('music_list', []))
                    else:
                        self.logger.bind(tag=TAG).error(f"Java API返回错误: {response.status}")
                        return self._get_default_music(music_type)
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"调用Java音乐API失败: {e}")
            return self._get_default_music(music_type)
    
    async def get_elderly_music(self, user_info: Dict[str, Any] = None, mood: str = "peaceful") -> List[Dict[str, Any]]:
        """获取适合老年人的音乐内容"""
        try:
            if not self.java_api_base or not self.api_secret:
                self.logger.bind(tag=TAG).warning("Java API配置不完整，使用默认老年人音乐")
                return self._get_default_elderly_music()
            
            # 调用Java后端老年人音乐API
            url = f"{self.java_api_base}/api/music/elderly"
            headers = {
                "Authorization": f"Bearer {self.api_secret}",
                "Content-Type": "application/json"
            }
            
            # 传递用户信息和心情用于个性化音乐推荐
            data = {
                "user_info": user_info or {},
                "mood": mood,
                "limit": 3
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=10) as response:
                    if response.status == 200:
                        music_data = await response.json()
                        self.logger.bind(tag=TAG).info(f"获取老年人音乐成功，共{len(music_data.get('music_list', []))}首")
                        return self._format_music_data(music_data.get('music_list', []))
                    else:
                        self.logger.bind(tag=TAG).error(f"Java API返回错误: {response.status}")
                        return self._get_default_elderly_music()
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"调用Java老年人音乐API失败: {e}")
            return self._get_default_elderly_music()
    
    async def play_music(self, device_id: str, music_id: str) -> Dict[str, Any]:
        """通过Java后端API播放指定音乐"""
        try:
            if not self.java_api_base or not self.api_secret:
                self.logger.bind(tag=TAG).warning("Java API配置不完整，无法播放音乐")
                return {"success": False, "message": "API配置不完整"}
            
            # 调用Java后端音乐播放API
            url = f"{self.java_api_base}/api/music/play"
            headers = {
                "Authorization": f"Bearer {self.api_secret}",
                "Content-Type": "application/json"
            }
            
            data = {
                "device_id": device_id,
                "music_id": music_id
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.logger.bind(tag=TAG).info(f"设备 {device_id} 开始播放音乐 {music_id}")
                        return {"success": True, "message": "音乐播放成功", "data": result}
                    else:
                        self.logger.bind(tag=TAG).error(f"Java API返回错误: {response.status}")
                        return {"success": False, "message": f"API错误: {response.status}"}
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"调用Java音乐播放API失败: {e}")
            return {"success": False, "message": f"播放失败: {e}"}
    
    def _format_music_data(self, raw_music: List[Dict]) -> List[Dict[str, Any]]:
        """格式化Java API返回的音乐数据"""
        try:
            formatted_music = []
            
            for music_item in raw_music:
                formatted = {
                    "music_id": music_item.get("music_id", ""),
                    "title": music_item.get("title", ""),
                    "artist": music_item.get("artist", ""),
                    "album": music_item.get("album", ""),
                    "genre": music_item.get("genre", ""),
                    "duration": music_item.get("duration", 0),  # 秒
                    "url": music_item.get("url", ""),
                    "description": music_item.get("description", ""),
                    "mood": music_item.get("mood", ""),  # peaceful, happy, nostalgic, etc.
                    "era": music_item.get("era", ""),  # 60s, 70s, 80s, 90s, etc.
                    "language": music_item.get("language", "中文"),
                    "popularity": music_item.get("popularity", 0),  # 0-100
                    "suitable_for_elderly": music_item.get("suitable_for_elderly", True)
                }
                
                # 只添加有效的音乐
                if formatted["title"] and formatted["artist"]:
                    formatted_music.append(formatted)
            
            return formatted_music[:5]  # 最多返回5首音乐
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化音乐数据失败: {e}")
            return self._get_default_music("relaxing")
    
    def _get_default_music(self, music_type: str = "relaxing") -> List[Dict[str, Any]]:
        """返回默认音乐推荐（API不可用时的备用方案）"""
        default_music = {
            "relaxing": [
                {
                    "music_id": "default_001",
                    "title": "春江花月夜",
                    "artist": "民族音乐",
                    "album": "中国古典名曲",
                    "genre": "古典",
                    "duration": 240,
                    "url": "",
                    "description": "优美的古典音乐，适合放松心情",
                    "mood": "peaceful",
                    "era": "古典",
                    "language": "纯音乐",
                    "popularity": 85,
                    "suitable_for_elderly": True
                },
                {
                    "music_id": "default_002",
                    "title": "月光曲",
                    "artist": "贝多芬",
                    "album": "贝多芬钢琴名曲",
                    "genre": "古典",
                    "duration": 300,
                    "url": "",
                    "description": "宁静优美的钢琴曲",
                    "mood": "peaceful",
                    "era": "古典",
                    "language": "纯音乐",
                    "popularity": 90,
                    "suitable_for_elderly": True
                }
            ],
            "nostalgic": [
                {
                    "music_id": "default_003",
                    "title": "甜蜜蜜",
                    "artist": "邓丽君",
                    "album": "邓丽君经典",
                    "genre": "流行",
                    "duration": 210,
                    "url": "",
                    "description": "经典老歌，勾起美好回忆",
                    "mood": "nostalgic",
                    "era": "70s",
                    "language": "中文",
                    "popularity": 95,
                    "suitable_for_elderly": True
                },
                {
                    "music_id": "default_004",
                    "title": "茉莉花",
                    "artist": "民歌",
                    "album": "中国民歌精选",
                    "genre": "民歌",
                    "duration": 180,
                    "url": "",
                    "description": "优美的传统民歌",
                    "mood": "nostalgic",
                    "era": "传统",
                    "language": "中文",
                    "popularity": 80,
                    "suitable_for_elderly": True
                }
            ]
        }
        
        return default_music.get(music_type, default_music["relaxing"])
    
    def _get_default_elderly_music(self) -> List[Dict[str, Any]]:
        """返回默认的老年人音乐"""
        elderly_music = [
            {
                "music_id": "elderly_001",
                "title": "夕阳红",
                "artist": "经典老歌",
                "album": "怀旧金曲",
                "genre": "流行",
                "duration": 240,
                "url": "",
                "description": "温暖的旋律，适合老年朋友聆听",
                "mood": "peaceful",
                "era": "80s",
                "language": "中文",
                "popularity": 88,
                "suitable_for_elderly": True
            },
            {
                "music_id": "elderly_002",
                "title": "高山流水",
                "artist": "古筝演奏",
                "album": "古筝名曲",
                "genre": "民族",
                "duration": 300,
                "url": "",
                "description": "清雅的古筝曲，心灵的净化",
                "mood": "peaceful",
                "era": "古典",
                "language": "纯音乐",
                "popularity": 82,
                "suitable_for_elderly": True
            },
            {
                "music_id": "elderly_003",
                "title": "在那桃花盛开的地方",
                "artist": "经典民歌",
                "album": "红色经典",
                "genre": "民歌",
                "duration": 220,
                "url": "",
                "description": "充满回忆的经典歌曲",
                "mood": "nostalgic",
                "era": "70s",
                "language": "中文",
                "popularity": 90,
                "suitable_for_elderly": True
            }
        ]
        
        return elderly_music
    
    def format_music_for_greeting(self, music_list: List[Dict[str, Any]], max_items: int = 2) -> str:
        """将音乐数据格式化为适合问候的文本"""
        try:
            if not music_list:
                return "今天为您准备了一些轻松的音乐，希望您喜欢！"
            
            music_texts = []
            
            for i, music in enumerate(music_list[:max_items]):
                title = music.get("title", "")
                artist = music.get("artist", "")
                description = music.get("description", "")
                mood = music.get("mood", "")
                
                if title and artist:
                    # 构建音乐推荐文本
                    music_text = f"《{title}》"
                    if artist != "未知艺术家":
                        music_text += f" - {artist}"
                    
                    if description:
                        music_text += f"，{description}"
                    elif mood == "peaceful":
                        music_text += "，让您心情平静"
                    elif mood == "nostalgic":
                        music_text += "，勾起美好回忆"
                    elif mood == "happy":
                        music_text += "，带来愉悦心情"
                    
                    music_texts.append(music_text)
            
            if music_texts:
                if len(music_texts) == 1:
                    return f"为您推荐音乐：{music_texts[0]}。"
                else:
                    return f"为您推荐音乐：{music_texts[0]}。另外还有{music_texts[1]}。"
            else:
                return "今天为您准备了一些轻松的音乐，希望您喜欢！"
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化音乐推荐失败: {e}")
            return "今天为您准备了一些轻松的音乐，希望您喜欢！"
    
    def format_music_summary(self, music_list: List[Dict[str, Any]]) -> str:
        """格式化音乐摘要（用于LLM上下文）"""
        try:
            if not music_list:
                return "暂无音乐推荐"
            
            summaries = []
            for music in music_list[:3]:  # 最多3首
                title = music.get("title", "")
                artist = music.get("artist", "")
                mood = music.get("mood", "")
                
                if title:
                    mood_desc = {"peaceful": "宁静", "nostalgic": "怀旧", "happy": "欢快"}.get(mood, "")
                    summary = f"{mood_desc}：《{title}》"
                    if artist:
                        summary += f"({artist})"
                    summaries.append(summary)
            
            return "；".join(summaries)
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化音乐摘要失败: {e}")
            return "暂无音乐推荐"


# 便捷函数
async def get_music_info(config: Dict[str, Any], music_type: str = "elderly", user_info: Dict[str, Any] = None, device_id: str = "") -> List[Dict[str, Any]]:
    """
    获取音乐信息的便捷函数
    
    Args:
        config: 应用配置
        music_type: 音乐类型
        user_info: 用户信息
        device_id: 设备ID
        
    Returns:
        List[Dict]: 音乐列表
    """
    tool = MusicTool(config)
    
    if music_type == "elderly":
        return await tool.get_elderly_music(user_info)
    else:
        return await tool.get_music_recommendation(device_id, music_type, user_info)


# Function Calling定义
MUSIC_FUNCTION_DEFINITION = {
    "name": "get_music_recommendation",
    "description": "获取音乐推荐，特别适合老年用户的音乐内容，可以根据心情和喜好推荐合适的音乐",
    "parameters": {
        "type": "object",
        "properties": {
            "music_type": {
                "type": "string",
                "description": "音乐类型或心情",
                "enum": ["elderly", "relaxing", "nostalgic", "peaceful", "classical", "folk"],
                "default": "elderly"
            },
            "mood": {
                "type": "string", 
                "description": "当前心情",
                "enum": ["peaceful", "happy", "nostalgic", "calm", "energetic"],
                "default": "peaceful"
            },
            "max_items": {
                "type": "integer",
                "description": "最大推荐数量",
                "default": 2,
                "minimum": 1,
                "maximum": 3
            }
        },
        "required": ["music_type"]
    }
}


# Function Calling执行函数
async def execute_music_function(function_args: Dict[str, Any], config: Dict[str, Any], user_info: Dict[str, Any] = None, device_id: str = "") -> str:
    """
    执行音乐Function Calling
    
    Args:
        function_args: 函数参数
        config: 应用配置
        user_info: 用户信息
        device_id: 设备ID
        
    Returns:
        str: 音乐推荐文本
    """
    try:
        music_type = function_args.get("music_type", "elderly")
        mood = function_args.get("mood", "peaceful")
        max_items = function_args.get("max_items", 2)
        
        music_tool = MusicTool(config)
        
        if music_type == "elderly":
            music_list = await music_tool.get_elderly_music(user_info, mood)
        else:
            music_list = await music_tool.get_music_recommendation(device_id, music_type, user_info)
        
        return music_tool.format_music_for_greeting(music_list, max_items)
        
    except Exception as e:
        return "抱歉，暂时无法获取音乐推荐，请稍后再试。"

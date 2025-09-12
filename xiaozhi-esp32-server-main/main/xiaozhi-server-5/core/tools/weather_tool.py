"""
天气查询工具 - 集成Java后端天气API
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional
from config.logger import setup_logging

TAG = __name__


class WeatherTool:
    """天气查询工具，支持Java后端API和第三方天气API"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()
        
        # Java后端API配置
        self.java_api_base = config.get("manager-api", {}).get("url", "")
        self.api_secret = config.get("manager-api", {}).get("secret", "")
        
        # 第三方天气API配置
        self.third_party_api = config.get("proactive_greeting", {}).get("weather", {}).get("third_party_api", {})
        self.third_party_enabled = self.third_party_api.get("enabled", False)
        self.third_party_url = self.third_party_api.get("url", "")
        self.third_party_key = self.third_party_api.get("api_key", "")
        
        # 设备城市映射（当Java API不可用时的备用方案）
        self.device_city_mapping = config.get("proactive_greeting", {}).get("weather", {}).get("device_city_mapping", {})
        
    async def get_weather_by_device(self, device_id: str) -> Dict[str, Any]:
        """根据设备ID获取天气信息（优先使用Java后端API，失败时使用第三方API）"""
        try:
            # 优先使用Java后端API
            if self.java_api_base and self.api_secret:
                try:
                    # 调用Java后端天气API
                    url = f"{self.java_api_base}/api/weather/device/{device_id}"
                    headers = {
                        "Authorization": f"Bearer {self.api_secret}",
                        "Content-Type": "application/json"
                    }
                    
                    # 使用SSL辅助工具创建安全会话
                    from core.utils.ssl_helper import create_secure_session
                    
                    async with create_secure_session() as session:
                        async with session.get(url, headers=headers, timeout=10) as response:
                            if response.status == 200:
                                weather_data = await response.json()
                                self.logger.bind(tag=TAG).info(f"Java API获取设备 {device_id} 天气信息成功")
                                return self._format_weather_data(weather_data)
                except Exception as e:
                    self.logger.bind(tag=TAG).warning(f"Java API调用失败: {e}，尝试第三方API")
            
            # 回退到第三方API
            if self.third_party_enabled and self.third_party_url and self.third_party_key:
                # 根据设备ID获取城市名
                city = self.device_city_mapping.get(device_id, "Beijing")  # 默认北京
                return await self._get_third_party_weather(city)
            
            # 最后使用默认天气
            self.logger.bind(tag=TAG).warning("所有API都不可用，使用默认天气信息")
            return self._get_default_weather()
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取天气信息失败: {e}")
            return self._get_default_weather()
    
    async def get_weather_by_city(self, city: str) -> Dict[str, Any]:
        """根据城市名获取天气信息"""
        try:
            # 优先使用Java后端API（如果支持按城市查询）
            if self.java_api_base and self.api_secret:
                try:
                    url = f"{self.java_api_base}/api/weather/city/{city}"
                    headers = {
                        "Authorization": f"Bearer {self.api_secret}",
                        "Content-Type": "application/json"
                    }
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=headers, timeout=10) as response:
                            if response.status == 200:
                                weather_data = await response.json()
                                self.logger.bind(tag=TAG).info(f"Java API获取 {city} 天气信息成功")
                                return self._format_weather_data(weather_data)
                except Exception as e:
                    self.logger.bind(tag=TAG).warning(f"Java API调用失败: {e}，尝试第三方API")
            
            # 回退到第三方API
            if self.third_party_enabled and self.third_party_url and self.third_party_key:
                return await self._get_third_party_weather(city)
            
            # 最后使用默认天气
            self.logger.bind(tag=TAG).warning("所有API都不可用，使用默认天气信息")
            return self._get_default_weather()
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取城市 {city} 天气信息失败: {e}")
            return self._get_default_weather()
    
    async def _get_third_party_weather(self, city: str) -> Dict[str, Any]:
        """调用第三方天气API获取天气信息"""
        try:
            if not self.third_party_url or not self.third_party_key:
                self.logger.bind(tag=TAG).error("第三方天气API配置不完整")
                return self._get_default_weather()
            
            # 调用第三方API
            params = {
                "key": self.third_party_key,
                "city": city
            }
            
            # 使用SSL辅助工具创建安全会话
            from core.utils.ssl_helper import create_secure_session
            
            async with create_secure_session() as session:
                async with session.get(self.third_party_url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == 1 and data.get("data"):
                            weather_data = data["data"]
                            self.logger.bind(tag=TAG).info(f"第三方API获取 {city} 天气信息成功")
                            return self._format_third_party_weather(weather_data)
                        else:
                            self.logger.bind(tag=TAG).error(f"第三方API返回数据格式错误: {data}")
                            return self._get_default_weather()
                    else:
                        self.logger.bind(tag=TAG).error(f"第三方API返回状态码: {response.status}")
                        return self._get_default_weather()
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"调用第三方天气API失败: {e}")
            return self._get_default_weather()
    
    def _format_third_party_weather(self, raw_data: Dict) -> Dict[str, Any]:
        """格式化第三方API返回的天气数据"""
        try:
            # 第三方API数据格式处理
            city = raw_data.get("city", "未知城市")
            temp_c = raw_data.get("temp_C", "")
            weather_desc = ""
            
            # 获取天气描述
            if raw_data.get("weatherDesc") and len(raw_data["weatherDesc"]) > 0:
                weather_desc = raw_data["weatherDesc"][0].get("value", "")
                
                # 英文转中文
                weather_translations = {
                    "Sunny": "晴天",
                    "Partly cloudy": "多云",
                    "Cloudy": "阴天", 
                    "Overcast": "阴",
                    "Mist": "薄雾",
                    "Light rain": "小雨",
                    "Moderate rain": "中雨",
                    "Heavy rain": "大雨",
                    "Light snow": "小雪",
                    "Moderate snow": "中雪",
                    "Heavy snow": "大雪"
                }
                weather_desc = weather_translations.get(weather_desc, weather_desc)
            
            # 体感温度
            feels_like = raw_data.get("FeelsLikeC", "")
            
            # 湿度
            humidity = raw_data.get("humidity", "")
            
            # 风速和风向
            wind_speed = raw_data.get("windspeedKmph", "")
            wind_dir = raw_data.get("winddir16Point", "")
            wind_info = ""
            if wind_speed and wind_dir:
                wind_info = f"{wind_dir}风{wind_speed}公里/小时"
            
            # 气压
            pressure = raw_data.get("pressure", "")
            
            # 能见度
            visibility = raw_data.get("visibility", "")
            
            # 降水量
            precip_mm = raw_data.get("precipMM", "")
            
            # 观测时间
            obs_time = raw_data.get("observation_time", "")
            local_time = raw_data.get("localObsDateTime", "")
            
            formatted = {
                "city": city,
                "temperature": temp_c,
                "weather": weather_desc,
                "temperature_high": "",  # 第三方API没有提供，可以用体感温度代替
                "temperature_low": "",
                "wind": wind_info,
                "humidity": humidity + "%" if humidity else "",
                "pressure": pressure + "毫帕" if pressure else "",
                "visibility": visibility + "公里" if visibility else "",
                "feels_like": feels_like + "℃" if feels_like else "",
                "precipitation": precip_mm + "毫米" if precip_mm else "0毫米",
                "suggestion": self._generate_weather_suggestion(temp_c, weather_desc, humidity),
                "update_time": local_time or obs_time,
                "source": "第三方天气API"
            }
            
            return formatted
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化第三方天气数据失败: {e}")
            return self._get_default_weather()
    
    def _generate_weather_suggestion(self, temperature: str, weather: str, humidity: str) -> str:
        """根据天气数据生成建议"""
        try:
            suggestions = []
            
            # 温度建议
            if temperature:
                temp = float(temperature)
                if temp >= 35:
                    suggestions.append("天气炎热，请注意防暑降温，多喝水")
                elif temp >= 30:
                    suggestions.append("天气较热，建议穿轻薄衣物")
                elif temp <= 0:
                    suggestions.append("天气寒冷，请注意保暖")
                elif temp <= 10:
                    suggestions.append("天气较冷，建议添加衣物")
            
            # 天气建议
            if weather:
                if "雨" in weather:
                    suggestions.append("有降雨，出门请带雨具")
                elif "雪" in weather:
                    suggestions.append("有降雪，请注意路面安全")
                elif "雾" in weather or "霾" in weather:
                    suggestions.append("能见度较低，出行请注意安全")
            
            # 湿度建议
            if humidity:
                hum = float(humidity)
                if hum >= 80:
                    suggestions.append("湿度较高，注意通风")
                elif hum <= 30:
                    suggestions.append("空气干燥，注意补水")
            
            if suggestions:
                return "，".join(suggestions[:2])  # 最多显示2条建议
            else:
                return "天气不错，适合外出活动"
                
        except Exception:
            return "请根据天气情况适当调整活动安排"
    
    def _format_weather_data(self, raw_data: Dict) -> Dict[str, Any]:
        """格式化Java API返回的天气数据"""
        try:
            # 根据Java API的实际返回格式进行调整
            formatted = {
                "city": raw_data.get("city", "未知城市"),
                "temperature": raw_data.get("temperature", "未知"),
                "weather": raw_data.get("weather", "未知"),
                "temperature_high": raw_data.get("high", ""),
                "temperature_low": raw_data.get("low", ""),
                "wind": raw_data.get("wind", ""),
                "humidity": raw_data.get("humidity", ""),
                "suggestion": raw_data.get("suggestion", ""),
                "update_time": raw_data.get("updateTime", "")
            }
            return formatted
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化天气数据失败: {e}")
            return self._get_default_weather()
    
    def _get_default_weather(self) -> Dict[str, Any]:
        """返回默认天气信息（API不可用时的备用方案）"""
        return {
            "city": "当前城市",
            "temperature": "适宜",
            "weather": "天气良好",
            "temperature_high": "",
            "temperature_low": "", 
            "wind": "",
            "humidity": "",
            "suggestion": "请关注天气变化",
            "update_time": ""
        }
    
    def format_weather_for_greeting(self, weather_data: Dict[str, Any]) -> str:
        """将天气数据格式化为适合问候的文本"""
        try:
            city = weather_data.get("city", "")
            temp = weather_data.get("temperature", "")
            weather = weather_data.get("weather", "")
            high = weather_data.get("temperature_high", "")
            low = weather_data.get("temperature_low", "")
            feels_like = weather_data.get("feels_like", "")
            humidity = weather_data.get("humidity", "")
            wind = weather_data.get("wind", "")
            
            # 构建天气描述文本
            weather_text = f"{city}今天{weather}"
            
            if temp:
                weather_text += f"，当前温度{temp}℃"
            
            # 如果有高低温，优先显示；否则显示体感温度
            if high and low:
                weather_text += f"，最高{high}℃，最低{low}℃"
            elif high:
                weather_text += f"，最高{high}℃"
            elif feels_like and feels_like != temp + "℃":
                weather_text += f"，体感温度{feels_like}"
            
            # 添加湿度信息（如果较高或较低）
            if humidity:
                try:
                    hum_val = float(humidity.replace("%", ""))
                    if hum_val >= 80:
                        weather_text += "，湿度较高"
                    elif hum_val <= 30:
                        weather_text += "，空气干燥"
                except:
                    pass
            
            # 添加风力信息（如果较强）
            if wind and "风" in wind:
                try:
                    # 提取风速数字
                    import re
                    speed_match = re.search(r'(\d+)', wind)
                    if speed_match:
                        speed = int(speed_match.group(1))
                        if speed >= 20:  # 风速较大时提醒
                            weather_text += f"，{wind}"
                except:
                    pass
                
            suggestion = weather_data.get("suggestion", "")
            if suggestion:
                weather_text += f"。{suggestion}"
            
            return weather_text
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化天气问候文本失败: {e}")
            return "今天天气不错，请注意适当添减衣物"


# 为LLM Function Calling提供的工具函数
async def get_weather_info(device_id: str, config: Dict[str, Any]) -> str:
    """
    LLM Function Calling使用的天气查询函数（按设备ID）
    
    Args:
        device_id: 设备ID
        config: 应用配置
        
    Returns:
        str: 格式化的天气信息文本
    """
    weather_tool = WeatherTool(config)
    weather_data = await weather_tool.get_weather_by_device(device_id)
    return weather_tool.format_weather_for_greeting(weather_data)


async def get_weather_by_city_info(city: str, config: Dict[str, Any]) -> str:
    """
    LLM Function Calling使用的天气查询函数（按城市名）
    
    Args:
        city: 城市名
        config: 应用配置
        
    Returns:
        str: 格式化的天气信息文本
    """
    weather_tool = WeatherTool(config)
    weather_data = await weather_tool.get_weather_by_city(city)
    return weather_tool.format_weather_for_greeting(weather_data)


# Function Calling的函数定义
WEATHER_FUNCTION_DEFINITION = {
    "name": "get_weather_info",
    "description": "获取指定设备所在城市的天气信息，用于生成天气相关的问候内容",
    "parameters": {
        "type": "object",
        "properties": {
            "device_id": {
                "type": "string",
                "description": "设备ID，用于查询该设备绑定城市的天气信息"
            }
        },
        "required": ["device_id"]
    }
}

# 按城市查询天气的Function Calling定义
WEATHER_CITY_FUNCTION_DEFINITION = {
    "name": "get_weather_by_city",
    "description": "根据城市名获取天气信息，支持中英文城市名",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名，如'北京'、'Beijing'、'武汉'、'Wuhan'等"
            }
        },
        "required": ["city"]
    }
}

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Java后端天气API集成
支持实时天气和未来天气预报数据格式
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from config.logger import setup_logging

TAG = __name__


class JavaBackendWeatherService:
    """Java后端天气服务"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()
        
        # Java后端API配置
        self.java_api_base = config.get("manager-api", {}).get("url", "")
        self.api_secret = config.get("manager-api", {}).get("secret", "")
        
        # 超时配置
        self.timeout = config.get("weather", {}).get("timeout", 10)
        
        # 设备城市映射
        self.device_city_mapping = config.get("proactive_greeting", {}).get("weather", {}).get("device_city_mapping", {
            "ESP32_001": "广州",
            "ESP32_002": "北京"
        })
        
    async def get_current_weather(self, device_id: str) -> Dict[str, Any]:
        """获取设备当前天气（实时天气）"""
        try:
            url = f"{self.java_api_base}/api/getWeather"
            headers = {
                "Content-Type": "application/json"
            }
            
            # 优先尝试设备ID查询
            request_data = {
                "deviceId": device_id
            }
            
            weather_data = await self._make_weather_request(url, headers, request_data)
            
            # 如果设备ID查询失败（500错误），尝试使用设备对应的城市查询
            if not weather_data or weather_data.get("code") == 500:
                self.logger.bind(tag=TAG).info(f"设备ID查询失败，尝试使用城市查询")
                city = self._get_device_city(device_id)
                return await self.get_weather_by_city(city)
            
            return self._format_java_api_weather(weather_data, device_id)
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取实时天气失败: {e}")
            # 备用方案：使用城市查询
            try:
                city = self._get_device_city(device_id)
                self.logger.bind(tag=TAG).info(f"使用备用城市查询: {city}")
                return await self.get_weather_by_city(city)
            except:
                return self._get_default_weather()
    
    async def _make_weather_request(self, url: str, headers: dict, request_data: dict) -> Dict[str, Any]:
        """发送天气请求的通用方法"""
        try:
            self.logger.bind(tag=TAG).info(f"请求Java API: {url}, 参数: {request_data}")
            
            # 使用SSL辅助工具创建安全会话
            from core.utils.ssl_helper import create_secure_session
            
            async with create_secure_session() as session:
                async with session.post(url, headers=headers, json=request_data, timeout=self.timeout) as response:
                    if response.status == 200:
                        try:
                            weather_data = await response.json()
                            self.logger.bind(tag=TAG).info(f"Java API响应: {weather_data}")
                            return weather_data
                        except Exception as json_error:
                            self.logger.bind(tag=TAG).error(f"JSON解析失败: {json_error}")
                            return None
                    else:
                        error_text = await response.text()
                        self.logger.bind(tag=TAG).error(f"HTTP错误状态码: {response.status}, 响应: {error_text}")
                        return None
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"请求失败: {e}")
            return None
    
    async def get_weather_by_date(self, device_id: str, date: str, city: str = None) -> Dict[str, Any]:
        """获取设备指定日期的天气"""
        try:
            url = f"{self.java_api_base}/api/getWeather"
            headers = {
                "Content-Type": "application/json"
            }
            
            # 构建请求数据
            request_data = {
                "deviceId": device_id,
                "date": date
            }
            
            # 如果指定了城市，也传递city参数
            if city:
                request_data["city"] = city
            
            self.logger.bind(tag=TAG).info(f"请求Java API指定日期天气: {url}, deviceId: {device_id}, date: {date}, city: {city}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=request_data, timeout=self.timeout) as response:
                    if response.status == 200:
                        weather_data = await response.json()
                        self.logger.bind(tag=TAG).info(f"获取设备 {device_id} 日期 {date} 天气成功")
                        return self._format_java_api_weather(weather_data, device_id, date)
                    else:
                        error_text = await response.text()
                        self.logger.bind(tag=TAG).error(f"Java API返回错误状态码: {response.status}, 响应: {error_text}")
                        return self._get_default_weather()
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取日期 {date} 天气失败: {e}")
            return self._get_default_weather()
    
    async def get_weather_by_city(self, city: str, date: str = None) -> Dict[str, Any]:
        """根据城市名获取天气信息 - 基于测试发现这是最可靠的方法"""
        try:
            url = f"{self.java_api_base}/api/getWeather"
            headers = {
                "Content-Type": "application/json"
            }
            
            # 基于测试结果，只传city是最可靠的方式
            request_data = {"city": city}
            
            # 如果有日期，添加日期参数
            if date:
                request_data["date"] = date
            
            self.logger.bind(tag=TAG).info(f"使用城市查询天气: city={city}, date={date}")
            
            weather_data = await self._make_weather_request(url, headers, request_data)
            
            if weather_data:
                api_code = weather_data.get("code")
                if api_code == 0:
                    self.logger.bind(tag=TAG).info(f"城市天气查询成功: {city}")
                    return self._format_java_api_weather(weather_data, city, date)
                else:
                    self.logger.bind(tag=TAG).warning(f"城市天气查询失败: code={api_code}, msg={weather_data.get('msg')}")
            
            return self._get_default_weather()
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取城市 {city} 天气失败: {e}")
            return self._get_default_weather()
    
    async def get_future_weather(self, device_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """获取设备未来天气预报（通过日期范围实现）"""
        try:
            from datetime import datetime, timedelta
            
            weather_list = []
            today = datetime.now()
            
            # 获取未来几天的天气
            for i in range(1, min(days + 1, 8)):  # 最多7天
                future_date = today + timedelta(days=i)
                date_str = future_date.strftime("%Y-%m-%d")
                
                try:
                    weather_data = await self.get_weather_by_date(device_id, date_str)
                    if weather_data and weather_data.get("temperature"):
                        weather_list.append(weather_data)
                    await asyncio.sleep(0.5)  # 避免频繁请求
                except Exception as e:
                    self.logger.bind(tag=TAG).warning(f"获取 {date_str} 天气失败: {e}")
                    continue
            
            self.logger.bind(tag=TAG).info(f"获取设备 {device_id} 未来{len(weather_list)}天预报成功")
            return weather_list
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取未来天气失败: {e}")
            return []
    
    async def get_weather_summary(self, device_id: str) -> Dict[str, Any]:
        """获取天气概要信息（主要是实时天气）"""
        try:
            # 获取实时天气
            current_weather = await self.get_current_weather(device_id)
            
            return {
                "current": current_weather,
                "forecast": [],  # 暂时不获取预报，因为Java API可能还没有提供
                "city": current_weather.get("city", "未知城市"),
                "update_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取天气概要失败: {e}")
            return {
                "current": self._get_default_weather(),
                "forecast": [],
                "city": "未知城市",
                "update_time": datetime.now().isoformat()
            }
    
    def _format_current_weather(self, raw_data: Dict) -> Dict[str, Any]:
        """
        格式化实时天气数据
        输入格式示例：
        {"obsTime":"2025-08-19T13:16+08:00","temp":"37","feelsLike":"40","icon":"101",
         "text":"多云","wind360":"270","windDir":"西风","windScale":"1","windSpeed":"3",
         "humidity":"40","precip":"0.0","pressure":"1004","vis":"28","cloud":"10","dew":"24"}
        """
        try:
            return {
                "observation_time": raw_data.get("obsTime", ""),
                "temperature": raw_data.get("temp", ""),
                "feels_like": raw_data.get("feelsLike", ""),
                "weather_icon": raw_data.get("icon", ""),
                "weather_text": raw_data.get("text", ""),
                "wind_direction_degree": raw_data.get("wind360", ""),
                "wind_direction": raw_data.get("windDir", ""),
                "wind_scale": raw_data.get("windScale", ""),
                "wind_speed": raw_data.get("windSpeed", ""),
                "humidity": raw_data.get("humidity", ""),
                "precipitation": raw_data.get("precip", ""),
                "pressure": raw_data.get("pressure", ""),
                "visibility": raw_data.get("vis", ""),
                "cloud_coverage": raw_data.get("cloud", ""),
                "dew_point": raw_data.get("dew", ""),
                # 标准化字段
                "city": raw_data.get("city", "当前城市"),
                "weather": raw_data.get("text", ""),
                "wind": self._format_wind(raw_data.get("windDir", ""), raw_data.get("windScale", "")),
                "suggestion": self._generate_weather_suggestion(raw_data)
            }
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化实时天气数据失败: {e}")
            return self._get_default_weather()
    
    def _format_forecast_weather(self, raw_data: List[Dict]) -> List[Dict[str, Any]]:
        """
        格式化未来天气预报数据
        输入格式示例：
        {"fxDate":"2025-08-20","sunrise":"05:30","sunset":"18:37","moonrise":"01:58",
         "moonset":"16:54","moonPhase":"残月","moonPhaseIcon":"807","tempMax":"39",
         "tempMin":"28","iconDay":"305","textDay":"小雨","iconNight":"305",
         "textNight":"小雨","wind360Day":"270","windDirDay":"西风","windScaleDay":"1-3",
         "windSpeedDay":"3","wind360Night":"225","windDirNight":"西南风","windScaleNight":"1-3",
         "windSpeedNight":"3","humidity":"66","precip":"0.5","pressure":"1005",
         "vis":"25","cloud":"55","uvIndex":"10"}
        """
        formatted_list = []
        
        try:
            for day_data in raw_data:
                formatted = {
                    "date": day_data.get("fxDate", ""),
                    "sunrise": day_data.get("sunrise", ""),
                    "sunset": day_data.get("sunset", ""),
                    "moon_rise": day_data.get("moonrise", ""),
                    "moon_set": day_data.get("moonset", ""),
                    "moon_phase": day_data.get("moonPhase", ""),
                    "temp_max": day_data.get("tempMax", ""),
                    "temp_min": day_data.get("tempMin", ""),
                    "day_icon": day_data.get("iconDay", ""),
                    "day_weather": day_data.get("textDay", ""),
                    "night_icon": day_data.get("iconNight", ""),
                    "night_weather": day_data.get("textNight", ""),
                    "day_wind_direction": day_data.get("windDirDay", ""),
                    "day_wind_scale": day_data.get("windScaleDay", ""),
                    "night_wind_direction": day_data.get("windDirNight", ""),
                    "night_wind_scale": day_data.get("windScaleNight", ""),
                    "humidity": day_data.get("humidity", ""),
                    "precipitation": day_data.get("precip", ""),
                    "pressure": day_data.get("pressure", ""),
                    "visibility": day_data.get("vis", ""),
                    "cloud_coverage": day_data.get("cloud", ""),
                    "uv_index": day_data.get("uvIndex", ""),
                    # 标准化字段
                    "weather": day_data.get("textDay", ""),
                    "high": day_data.get("tempMax", ""),
                    "low": day_data.get("tempMin", ""),
                    "wind": self._format_wind(day_data.get("windDirDay", ""), day_data.get("windScaleDay", "")),
                    "formatted_date": self._format_date(day_data.get("fxDate", ""))
                }
                formatted_list.append(formatted)
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化预报天气数据失败: {e}")
        
        return formatted_list
    
    def _format_wind(self, direction: str, scale: str) -> str:
        """格式化风力信息"""
        if direction and scale:
            return f"{direction}{scale}级"
        elif direction:
            return direction
        elif scale:
            return f"{scale}级风"
        return ""
    
    def _format_date(self, date_str: str) -> str:
        """格式化日期显示"""
        try:
            if not date_str:
                return ""
            
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            today = datetime.now().date()
            
            if date_obj.date() == today:
                return "今天"
            elif date_obj.date() == today + timedelta(days=1):
                return "明天"
            elif date_obj.date() == today + timedelta(days=2):
                return "后天"
            else:
                return date_obj.strftime("%m月%d日")
                
        except Exception:
            return date_str
    
    def _get_device_city(self, device_id: str) -> str:
        """获取设备对应的城市"""
        city = self.device_city_mapping.get(device_id, "广州")  # 默认广州
        self.logger.bind(tag=TAG).debug(f"设备 {device_id} 对应城市: {city}")
        return city
    
    def _format_java_api_weather(self, weather_data: Dict, device_or_city: str, date: str = None) -> Dict[str, Any]:
        """格式化Java API返回的天气数据"""
        try:
            self.logger.bind(tag=TAG).debug(f"原始天气数据: {weather_data}")
            
            # 检查输入数据是否有效
            if not weather_data or not isinstance(weather_data, dict):
                self.logger.bind(tag=TAG).warning(f"Java API返回数据无效: {weather_data}")
                return self._get_default_weather()
            
            # 检查是否是业务错误响应
            if isinstance(weather_data, dict):
                api_code = weather_data.get("code")
                api_msg = weather_data.get("msg", "")
                
                # Java API使用 code=0 表示成功，code=200 也可能表示成功
                if api_code is not None and api_code not in [0, 200]:
                    self.logger.bind(tag=TAG).warning(f"Java API业务错误: code={api_code}, msg={api_msg}")
                    return self._get_default_weather()
                elif api_code == 0:
                    self.logger.bind(tag=TAG).info(f"Java API成功响应: code=0, msg={api_msg}")
            
            # 处理Java API可能的响应格式
            # 如果返回的是包装格式，提取实际数据
            actual_data = weather_data
            if isinstance(weather_data, dict) and "data" in weather_data:
                data_value = weather_data["data"]
                if data_value is not None:  # 检查data不是null
                    actual_data = data_value
                else:
                    # 对于成功响应但data为null的情况，可能数据在顶层
                    api_code = weather_data.get("code")
                    if api_code in [0, 200]:
                        self.logger.bind(tag=TAG).info(f"成功响应但data为null，尝试使用顶层数据")
                        # 移除控制字段，使用剩余字段作为天气数据
                        actual_data = {k: v for k, v in weather_data.items() if k not in ['code', 'msg', 'data']}
                        if not actual_data:
                            self.logger.bind(tag=TAG).warning(f"成功响应但没有有效的天气数据")
                            return self._get_default_weather()
                    else:
                        self.logger.bind(tag=TAG).warning(f"API返回data为null，可能是业务错误")
                        return self._get_default_weather()
            elif isinstance(weather_data, dict) and "result" in weather_data:
                result_value = weather_data["result"]
                if result_value is not None:  # 检查result不是null
                    actual_data = result_value
                else:
                    self.logger.bind(tag=TAG).warning(f"API返回result为null，可能是业务错误")
                    return self._get_default_weather()
            
            # 再次检查提取的数据是否有效
            if not actual_data or not isinstance(actual_data, dict):
                self.logger.bind(tag=TAG).warning(f"提取的实际数据无效: {actual_data}")
                return self._get_default_weather()
            
            # 检查是否有实时天气数据
            current_weather = actual_data
            if isinstance(actual_data, dict) and "current" in actual_data:
                current_weather = actual_data["current"]
            elif isinstance(actual_data, dict) and "now" in actual_data:
                current_weather = actual_data["now"]
            
            # 最终检查天气数据是否有效
            if not current_weather or not isinstance(current_weather, dict):
                self.logger.bind(tag=TAG).warning(f"当前天气数据无效: {current_weather}")
                return self._get_default_weather()
            
            # 尝试从返回数据中获取城市信息，如果没有则使用传入的参数
            city_name = current_weather.get("city", "")
            if not city_name:
                # 如果是设备ID格式，尝试从映射中获取城市
                if device_or_city in self.device_city_mapping:
                    city_name = self.device_city_mapping[device_or_city]
                else:
                    city_name = device_or_city
            
            # 格式化为标准格式
            formatted = {
                "city": city_name,
                "temperature": str(current_weather.get("temp", current_weather.get("temperature", ""))),
                "weather": current_weather.get("text", current_weather.get("weather", "")),
                "feels_like": str(current_weather.get("feelsLike", current_weather.get("feels_like", ""))),
                "humidity": str(current_weather.get("humidity", "")),
                "wind_direction": current_weather.get("windDir", current_weather.get("wind_direction", "")),
                "wind_scale": current_weather.get("windScale", current_weather.get("wind_scale", "")),
                "wind_speed": str(current_weather.get("windSpeed", current_weather.get("wind_speed", ""))),
                "pressure": str(current_weather.get("pressure", "")),
                "visibility": str(current_weather.get("vis", current_weather.get("visibility", ""))),
                "cloud_coverage": str(current_weather.get("cloud", current_weather.get("cloud_coverage", ""))),
                "observation_time": current_weather.get("obsTime", current_weather.get("observation_time", "")),
                "weather_icon": current_weather.get("icon", current_weather.get("weather_icon", "")),
                "wind": self._format_wind(
                    current_weather.get("windDir", current_weather.get("wind_direction", "")), 
                    current_weather.get("windScale", current_weather.get("wind_scale", ""))
                ),
                "suggestion": self._generate_weather_suggestion(current_weather),
                "query_date": date if date else "实时"  # 记录查询的日期
            }
            
            date_desc = f"日期={date}" if date else "实时"
            self.logger.bind(tag=TAG).info(f"格式化后天气数据: 城市={city_name}, 温度={formatted['temperature']}℃, 天气={formatted['weather']}, {date_desc}")
            
            return formatted
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化Java API天气数据失败: {e}")
            return self._get_default_weather()
    
    def _generate_weather_suggestion(self, weather_data: Dict) -> str:
        """根据天气数据生成建议"""
        try:
            # 检查输入数据是否有效
            if not weather_data or not isinstance(weather_data, dict):
                return "今天天气不错，注意适当添减衣物"
            
            suggestions = []
            
            # 温度建议
            temp = weather_data.get("temp", "")
            if temp:
                temp_val = float(temp)
                if temp_val >= 35:
                    suggestions.append("天气炎热，请注意防暑降温，多喝水")
                elif temp_val >= 30:
                    suggestions.append("天气较热，建议穿轻薄衣物")
                elif temp_val <= 0:
                    suggestions.append("天气寒冷，请注意保暖")
                elif temp_val <= 10:
                    suggestions.append("天气较冷，建议添加衣物")
            
            # 天气建议
            weather_text = weather_data.get("text", "")
            if weather_text:
                if "雨" in weather_text:
                    suggestions.append("有降雨，出门请带雨具")
                elif "雪" in weather_text:
                    suggestions.append("有降雪，请注意路面安全")
                elif "雾" in weather_text or "霾" in weather_text:
                    suggestions.append("能见度较低，出行请注意安全")
            
            # 湿度建议
            humidity = weather_data.get("humidity", "")
            if humidity:
                hum_val = float(humidity)
                if hum_val >= 80:
                    suggestions.append("湿度较高，注意通风")
                elif hum_val <= 30:
                    suggestions.append("空气干燥，注意补水")
            
            # 风力建议
            wind_scale = weather_data.get("windScale", "")
            if wind_scale:
                try:
                    scale_val = int(wind_scale)
                    if scale_val >= 6:
                        suggestions.append("风力较大，户外活动请注意安全")
                except ValueError:
                    pass
            
            if suggestions:
                return "，".join(suggestions[:2])  # 最多显示2条建议
            else:
                return "天气不错，适合外出活动"
                
        except Exception:
            return "请根据天气情况适当调整活动安排"
    
    def _get_default_weather(self) -> Dict[str, Any]:
        """返回默认天气信息"""
        return {
            "city": "当前城市",
            "temperature": "适宜",
            "weather": "天气良好",
            "feels_like": "",
            "humidity": "",
            "wind": "",
            "pressure": "",
            "visibility": "",
            "suggestion": "请关注天气变化",
            "observation_time": datetime.now().isoformat()
        }
    
    def format_weather_for_greeting(self, weather_summary: Dict[str, Any]) -> str:
        """将天气数据格式化为适合问候的文本"""
        try:
            current = weather_summary.get("current", {})
            forecast = weather_summary.get("forecast", [])
            city = weather_summary.get("city", "")
            
            # 构建天气描述文本
            weather_text = f"{city}现在{current.get('weather', '')}"
            
            temp = current.get("temperature", "")
            if temp:
                weather_text += f"，当前温度{temp}℃"
            
            feels_like = current.get("feels_like", "")
            if feels_like and feels_like != temp:
                weather_text += f"，体感温度{feels_like}℃"
            
            # 添加湿度信息（如果较高或较低）
            humidity = current.get("humidity", "")
            if humidity:
                try:
                    hum_val = float(humidity)
                    if hum_val >= 80:
                        weather_text += "，湿度较高"
                    elif hum_val <= 30:
                        weather_text += "，空气干燥"
                except ValueError:
                    pass
            
            # 添加风力信息
            wind = current.get("wind", "")
            if wind:
                weather_text += f"，{wind}"
            
            # 添加今天预报（如果有）
            if forecast and len(forecast) > 0:
                today_forecast = forecast[0]
                high = today_forecast.get("temp_max", "")
                low = today_forecast.get("temp_min", "")
                if high and low:
                    weather_text += f"。今天最高{high}℃，最低{low}℃"
            
            # 添加建议
            suggestion = current.get("suggestion", "")
            if suggestion:
                weather_text += f"。{suggestion}"
            
            return weather_text
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化天气问候文本失败: {e}")
            return "今天天气不错，请注意适当添减衣物"


class ProactiveWeatherGreetingService:
    """主动天气问候服务"""
    
    def __init__(self, config: Dict[str, Any], weather_service: JavaBackendWeatherService):
        self.config = config
        self.weather_service = weather_service
        self.logger = setup_logging()
    
    async def generate_weather_greeting(self, device_id: str, greeting_type: str = "morning") -> str:
        """生成天气问候内容"""
        try:
            # 获取天气概要
            weather_summary = await self.weather_service.get_weather_summary(device_id)
            
            # 基础问候语
            base_greetings = {
                "morning": ["早上好", "早安", "美好的早晨"],
                "afternoon": ["下午好", "午安"],
                "evening": ["晚上好", "晚安"],
                "general": ["你好", "您好"]
            }
            
            import random
            base_greeting = random.choice(base_greetings.get(greeting_type, base_greetings["general"]))
            
            # 格式化天气信息
            weather_text = self.weather_service.format_weather_for_greeting(weather_summary)
            
            # 生成特定时间的建议
            time_suggestion = self._get_time_specific_suggestion(greeting_type, weather_summary)
            
            # 组合最终问候语
            full_greeting = f"{base_greeting}！{weather_text}"
            if time_suggestion:
                full_greeting += f" {time_suggestion}"
            
            return full_greeting
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"生成天气问候失败: {e}")
            return "您好！今天是美好的一天，请注意适当添减衣物。"
    
    def _get_time_specific_suggestion(self, greeting_type: str, weather_summary: Dict) -> str:
        """根据时间和天气生成特定建议"""
        try:
            current = weather_summary.get("current", {})
            temp = current.get("temperature", "")
            weather = current.get("weather", "")
            
            suggestions = {
                "morning": [
                    "适合晨练" if temp and float(temp) > 15 and "雨" not in weather else "室内活动更安全",
                    "记得吃早餐",
                    "新的一天开始了"
                ],
                "afternoon": [
                    "午休时间到了",
                    "下午精神要集中",
                    "适当补充水分"
                ],
                "evening": [
                    "晚上散步很不错" if temp and float(temp) > 10 and "雨" not in weather else "室内休息更舒适",
                    "注意休息",
                    "晚餐记得要营养均衡"
                ]
            }
            
            import random
            time_suggestions = suggestions.get(greeting_type, [])
            
            if time_suggestions:
                return random.choice(time_suggestions)
            
            return ""
            
        except Exception:
            return ""


# 为Function Calling提供的工具函数
async def get_java_weather_info(device_id: str, config: Dict[str, Any]) -> str:
    """
    LLM Function Calling使用的Java后端天气查询函数
    
    Args:
        device_id: 设备ID
        config: 应用配置
        
    Returns:
        str: 格式化的天气信息文本
    """
    weather_service = JavaBackendWeatherService(config)
    weather_summary = await weather_service.get_weather_summary(device_id)
    return weather_service.format_weather_for_greeting(weather_summary)


async def generate_weather_greeting(device_id: str, greeting_type: str, config: Dict[str, Any]) -> str:
    """
    生成天气问候内容
    
    Args:
        device_id: 设备ID
        greeting_type: 问候类型 (morning/afternoon/evening/general)
        config: 应用配置
        
    Returns:
        str: 格式化的问候文本
    """
    weather_service = JavaBackendWeatherService(config)
    greeting_service = ProactiveWeatherGreetingService(config, weather_service)
    return await greeting_service.generate_weather_greeting(device_id, greeting_type)


# Function Calling的函数定义
JAVA_WEATHER_FUNCTION_DEFINITION = {
    "name": "get_java_weather_info",
    "description": "从Java后端获取指定设备所在城市的实时天气信息",
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

WEATHER_GREETING_FUNCTION_DEFINITION = {
    "name": "generate_weather_greeting",
    "description": "生成包含天气信息的主动问候内容",
    "parameters": {
        "type": "object",
        "properties": {
            "device_id": {
                "type": "string",
                "description": "设备ID"
            },
            "greeting_type": {
                "type": "string",
                "description": "问候类型：morning(早上)、afternoon(下午)、evening(晚上)、general(通用)",
                "enum": ["morning", "afternoon", "evening", "general"]
            }
        },
        "required": ["device_id", "greeting_type"]
    }
}

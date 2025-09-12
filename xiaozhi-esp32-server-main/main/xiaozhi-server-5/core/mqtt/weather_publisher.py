#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT天气信息发布服务
为硬件人员提供天气信息订阅功能
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from config.logger import setup_logging
from core.tools.java_backend_weather import JavaBackendWeatherService

TAG = __name__


class MQTTWeatherPublisher:
    """MQTT天气信息发布器"""
    
    def __init__(self, config: Dict[str, Any], mqtt_client=None):
        self.config = config
        self.mqtt_client = mqtt_client
        self.logger = setup_logging()
        
        # 天气服务
        self.weather_service = JavaBackendWeatherService(config)
        
        # 发布配置
        self.publisher_config = config.get("weather_publisher", {})
        self.enabled = self.publisher_config.get("enabled", True)
        
        # 主题配置
        self.topics = {
            # 全局天气主题
            "global_weather": self.publisher_config.get("topics", {}).get("global_weather", "weather/global"),
            # 设备专用天气主题
            "device_weather": self.publisher_config.get("topics", {}).get("device_weather", "weather/device/{device_id}"),
            # 城市天气主题
            "city_weather": self.publisher_config.get("topics", {}).get("city_weather", "weather/city/{city_name}"),
            # 天气预警主题
            "weather_alert": self.publisher_config.get("topics", {}).get("weather_alert", "weather/alert")
        }
        
        # 发布频率（分钟）
        self.publish_interval = self.publisher_config.get("publish_interval", 30)
        
        # 目标设备和城市
        self.target_devices = self.publisher_config.get("devices", ["ESP32_001", "ESP32_002"])
        self.target_cities = self.publisher_config.get("cities", ["广州", "北京", "上海"])
        
        # 发布状态跟踪
        self.last_publish_time = {}
        self.publish_counter = 0
        
    async def start_weather_publisher(self):
        """启动天气信息发布服务"""
        if not self.enabled:
            self.logger.bind(tag=TAG).info("📡 天气发布服务已禁用")
            return
            
        self.logger.bind(tag=TAG).info("📡 启动MQTT天气信息发布服务")
        
        # 启动定时发布任务
        asyncio.create_task(self._schedule_weather_publishing())
        
        self.logger.bind(tag=TAG).info("✅ MQTT天气发布服务启动成功")
    
    async def _schedule_weather_publishing(self):
        """定时发布天气信息"""
        while self.enabled:
            try:
                current_time = datetime.now()
                
                # 检查是否需要发布
                if self._should_publish(current_time):
                    await self._publish_all_weather_info()
                
                # 每分钟检查一次
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"定时发布天气信息失败: {e}")
                await asyncio.sleep(60)
    
    def _should_publish(self, current_time: datetime) -> bool:
        """检查是否应该发布天气信息"""
        last_publish = self.last_publish_time.get("global")
        
        if not last_publish:
            return True
            
        time_diff = (current_time - last_publish).total_seconds() / 60  # 转换为分钟
        return time_diff >= self.publish_interval
    
    async def _publish_all_weather_info(self):
        """发布所有天气信息"""
        try:
            self.logger.bind(tag=TAG).info("📤 开始发布天气信息")
            
            # 发布设备天气信息
            for device_id in self.target_devices:
                await self.publish_device_weather(device_id)
                await asyncio.sleep(1)  # 避免并发过多
            
            # 发布城市天气信息
            for city in self.target_cities:
                await self.publish_city_weather(city)
                await asyncio.sleep(1)
            
            # 发布全局天气概览
            await self.publish_global_weather()
            
            # 更新发布时间
            self.last_publish_time["global"] = datetime.now()
            self.publish_counter += 1
            
            self.logger.bind(tag=TAG).info(f"✅ 天气信息发布完成，第 {self.publish_counter} 次")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"发布天气信息失败: {e}")
    
    async def publish_device_weather(self, device_id: str) -> bool:
        """发布单个设备的天气信息"""
        try:
            # 获取设备天气信息
            weather_summary = await self.weather_service.get_weather_summary(device_id)
            
            # 构建发布消息
            weather_message = {
                "message_id": f"weather_{device_id}_{uuid.uuid4().hex[:8]}",
                "device_id": device_id,
                "timestamp": datetime.now().isoformat(),
                "weather_data": weather_summary,
                "formatted_text": self.weather_service.format_weather_for_greeting(weather_summary),
                "source": "java_backend_api",
                "publish_type": "device_weather"
            }
            
            # 发布到设备专用主题
            topic = self.topics["device_weather"].format(device_id=device_id)
            success = await self._publish_message(topic, weather_message)
            
            if success:
                self.logger.bind(tag=TAG).info(f"📡 设备 {device_id} 天气信息发布成功")
            
            return success
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"发布设备 {device_id} 天气信息失败: {e}")
            return False
    
    async def publish_city_weather(self, city_name: str) -> bool:
        """发布城市天气信息"""
        try:
            # 获取城市天气信息
            weather_data = await self.weather_service.get_weather_by_city(city_name)
            
            # 构建发布消息
            weather_message = {
                "message_id": f"weather_{city_name}_{uuid.uuid4().hex[:8]}",
                "city": city_name,
                "timestamp": datetime.now().isoformat(),
                "weather_data": weather_data,
                "formatted_text": self.weather_service.format_weather_for_greeting({"current": weather_data, "city": city_name}),
                "source": "java_backend_api",
                "publish_type": "city_weather"
            }
            
            # 发布到城市主题
            topic = self.topics["city_weather"].format(city_name=city_name)
            success = await self._publish_message(topic, weather_message)
            
            if success:
                self.logger.bind(tag=TAG).info(f"📡 城市 {city_name} 天气信息发布成功")
            
            return success
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"发布城市 {city_name} 天气信息失败: {e}")
            return False
    
    async def publish_global_weather(self) -> bool:
        """发布全局天气概览"""
        try:
            # 收集所有设备和城市的天气信息
            all_weather_data = {
                "devices": {},
                "cities": {}
            }
            
            # 收集设备天气
            for device_id in self.target_devices:
                try:
                    weather_summary = await self.weather_service.get_weather_summary(device_id)
                    all_weather_data["devices"][device_id] = weather_summary
                except Exception as e:
                    self.logger.bind(tag=TAG).warning(f"获取设备 {device_id} 天气失败: {e}")
            
            # 收集城市天气
            for city in self.target_cities:
                try:
                    weather_data = await self.weather_service.get_weather_by_city(city)
                    all_weather_data["cities"][city] = weather_data
                except Exception as e:
                    self.logger.bind(tag=TAG).warning(f"获取城市 {city} 天气失败: {e}")
            
            # 构建全局天气消息
            global_message = {
                "message_id": f"weather_global_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now().isoformat(),
                "weather_data": all_weather_data,
                "summary": {
                    "total_devices": len(self.target_devices),
                    "success_devices": len(all_weather_data["devices"]),
                    "total_cities": len(self.target_cities),
                    "success_cities": len(all_weather_data["cities"])
                },
                "source": "java_backend_api",
                "publish_type": "global_weather",
                "publish_count": self.publish_counter + 1
            }
            
            # 发布到全局主题
            success = await self._publish_message(self.topics["global_weather"], global_message)
            
            if success:
                self.logger.bind(tag=TAG).info("📡 全局天气概览发布成功")
            
            return success
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"发布全局天气概览失败: {e}")
            return False
    
    async def publish_weather_alert(self, alert_type: str, message: str, affected_areas: List[str] = None) -> bool:
        """发布天气预警信息"""
        try:
            alert_message = {
                "message_id": f"alert_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now().isoformat(),
                "alert_type": alert_type,  # "high_temperature", "rain", "wind", etc.
                "message": message,
                "affected_areas": affected_areas or [],
                "severity": "warning",  # "info", "warning", "severe"
                "publish_type": "weather_alert"
            }
            
            success = await self._publish_message(self.topics["weather_alert"], alert_message)
            
            if success:
                self.logger.bind(tag=TAG).info(f"⚠️ 天气预警发布成功: {alert_type}")
            
            return success
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"发布天气预警失败: {e}")
            return False
    
    async def _publish_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """发布消息到MQTT主题"""
        try:
            if not self.mqtt_client:
                self.logger.bind(tag=TAG).error("MQTT客户端未初始化")
                return False
            
            if not hasattr(self.mqtt_client, 'connected') or not self.mqtt_client.connected:
                self.logger.bind(tag=TAG).error("MQTT客户端未连接")
                return False
            
            # 发布消息
            result = self.mqtt_client.client.publish(topic, json.dumps(message, ensure_ascii=False))
            
            if result.rc == 0:
                self.logger.bind(tag=TAG).debug(f"📤 消息发布成功: {topic}")
                return True
            else:
                self.logger.bind(tag=TAG).error(f"📤 消息发布失败: {topic}, 返回码: {result.rc}")
                return False
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"发布消息异常: {e}")
            return False
    
    async def manual_publish_all(self) -> Dict[str, Any]:
        """手动发布所有天气信息"""
        self.logger.bind(tag=TAG).info("🔄 手动触发天气信息发布")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "devices": {},
            "cities": {},
            "global": False,
            "success_count": 0,
            "total_count": 0
        }
        
        try:
            # 发布设备天气
            for device_id in self.target_devices:
                success = await self.publish_device_weather(device_id)
                results["devices"][device_id] = success
                results["total_count"] += 1
                if success:
                    results["success_count"] += 1
            
            # 发布城市天气
            for city in self.target_cities:
                success = await self.publish_city_weather(city)
                results["cities"][city] = success
                results["total_count"] += 1
                if success:
                    results["success_count"] += 1
            
            # 发布全局天气
            global_success = await self.publish_global_weather()
            results["global"] = global_success
            results["total_count"] += 1
            if global_success:
                results["success_count"] += 1
            
            # 更新计数器
            self.publish_counter += 1
            self.last_publish_time["manual"] = datetime.now()
            
            self.logger.bind(tag=TAG).info(f"✅ 手动发布完成: {results['success_count']}/{results['total_count']} 成功")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"手动发布失败: {e}")
            results["error"] = str(e)
        
        return results
    
    def get_publisher_status(self) -> Dict[str, Any]:
        """获取发布器状态"""
        return {
            "enabled": self.enabled,
            "mqtt_connected": bool(self.mqtt_client and hasattr(self.mqtt_client, 'connected') and self.mqtt_client.connected),
            "topics": self.topics,
            "target_devices": self.target_devices,
            "target_cities": self.target_cities,
            "publish_interval": self.publish_interval,
            "publish_counter": self.publish_counter,
            "last_publish_times": self.last_publish_time,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_subscription_guide(self) -> Dict[str, Any]:
        """获取硬件人员订阅指南"""
        return {
            "mqtt_server": {
                "host": self.config.get("mqtt", {}).get("host", "47.97.185.142"),
                "port": self.config.get("mqtt", {}).get("port", 1883),
                "username": self.config.get("mqtt", {}).get("username", "admin"),
                "password": self.config.get("mqtt", {}).get("password", "Jyxd@2025")
            },
            "subscription_topics": {
                "全局天气信息": self.topics["global_weather"],
                "所有设备天气": "weather/device/+",
                "特定设备天气": "weather/device/{device_id}",
                "所有城市天气": "weather/city/+", 
                "特定城市天气": "weather/city/{city_name}",
                "天气预警": self.topics["weather_alert"]
            },
            "example_subscriptions": [
                {
                    "description": "订阅ESP32_001设备天气",
                    "topic": "weather/device/ESP32_001",
                    "command": "mosquitto_sub -h 47.97.185.142 -p 1883 -u admin -P Jyxd@2025 -t weather/device/ESP32_001"
                },
                {
                    "description": "订阅所有设备天气",
                    "topic": "weather/device/+",
                    "command": "mosquitto_sub -h 47.97.185.142 -p 1883 -u admin -P Jyxd@2025 -t 'weather/device/+'"
                },
                {
                    "description": "订阅全局天气概览",
                    "topic": "weather/global",
                    "command": "mosquitto_sub -h 47.97.185.142 -p 1883 -u admin -P Jyxd@2025 -t weather/global"
                },
                {
                    "description": "订阅广州天气",
                    "topic": "weather/city/广州",
                    "command": "mosquitto_sub -h 47.97.185.142 -p 1883 -u admin -P Jyxd@2025 -t 'weather/city/广州'"
                }
            ],
            "message_format": {
                "device_weather": {
                    "message_id": "weather_ESP32_001_a1b2c3d4",
                    "device_id": "ESP32_001",
                    "timestamp": "2025-08-19T15:30:00",
                    "weather_data": "天气数据对象",
                    "formatted_text": "广州现在多云，当前温度37℃...",
                    "source": "java_backend_api",
                    "publish_type": "device_weather"
                }
            },
            "update_frequency": f"每 {self.publish_interval} 分钟自动更新",
            "manual_trigger": "可通过API手动触发发布"
        }


# 便捷函数
async def create_weather_publisher(config: Dict[str, Any], mqtt_client=None) -> MQTTWeatherPublisher:
    """创建天气发布器实例"""
    return MQTTWeatherPublisher(config, mqtt_client)


async def start_weather_publishing_service(config: Dict[str, Any], mqtt_client=None):
    """启动天气发布服务"""
    publisher = MQTTWeatherPublisher(config, mqtt_client)
    await publisher.start_weather_publisher()
    return publisher

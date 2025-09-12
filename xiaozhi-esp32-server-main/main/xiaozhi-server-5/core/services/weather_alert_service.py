#!/usr/bin/env python3
"""
气象预警服务
处理Java后端推送的预警信息，根据设备ID唤醒对应设备并播报预警内容
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

from core.mqtt.mqtt_client import MQTTClient
from core.mqtt.webhook_callback_handler import AwakenWithCallbackService
from config.config_loader import load_config


TAG = "WeatherAlertService"


class WeatherAlertService:
    """气象预警服务类"""
    
    def __init__(self, mqtt_client: MQTTClient = None):
        self.config = load_config()
        self.mqtt_client = mqtt_client
        self.awaken_service = AwakenWithCallbackService(self.config, mqtt_client)
        self.alert_topics = self._get_alert_topics()
        self.device_location_mapping = self._get_device_location_mapping()
        self.is_running = False
        
    def _get_alert_topics(self) -> List[str]:
        """获取预警订阅主题列表"""
        return self.config.get("weather_alert", {}).get("topics", [
            "weather/alert/broadcast",      # 广播预警
            "weather/alert/regional",       # 区域预警
            "weather/alert/device/+",       # 设备特定预警 (通配符)
        ])
    
    def _get_device_location_mapping(self) -> Dict[str, str]:
        """获取设备与地区的映射关系"""
        return self.config.get("weather_alert", {}).get("device_location_mapping", {
            # 示例映射，实际需要根据部署情况配置
            "device_001": "西平县",
            "device_002": "驻马店市",
            "test_device": "西平县",
            "00:0c:29:fc:b7:b9": "西平县",  # MAC地址设备
        })
    
    async def start(self):
        """启动预警服务"""
        if self.is_running:
            logger.bind(tag=TAG).warning("预警服务已在运行中")
            return
            
        try:
            if not self.mqtt_client:
                logger.bind(tag=TAG).error("MQTT客户端未初始化")
                return
                
            # 订阅所有预警主题
            for topic in self.alert_topics:
                await self._subscribe_alert_topic(topic)
                
            self.is_running = True
            logger.bind(tag=TAG).info(f"预警服务启动成功，订阅主题: {self.alert_topics}")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"启动预警服务失败: {e}")
            raise
    
    async def stop(self):
        """停止预警服务"""
        if not self.is_running:
            return
            
        try:
            # 取消订阅所有预警主题
            for topic in self.alert_topics:
                if hasattr(self.mqtt_client, 'unsubscribe'):
                    await self.mqtt_client.unsubscribe(topic)
                    
            self.is_running = False
            logger.bind(tag=TAG).info("预警服务已停止")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"停止预警服务失败: {e}")
    
    async def _subscribe_alert_topic(self, topic: str):
        """订阅预警主题"""
        try:
            # 设置消息回调
            if hasattr(self.mqtt_client, 'set_message_callback'):
                self.mqtt_client.set_message_callback(self._handle_alert_message)
            
            # 订阅主题
            if hasattr(self.mqtt_client, 'subscribe'):
                await self.mqtt_client.subscribe(topic, qos=1)  # QoS=1保证消息送达
                logger.bind(tag=TAG).info(f"订阅预警主题成功: {topic}")
            else:
                logger.bind(tag=TAG).warning(f"MQTT客户端不支持subscribe方法")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"订阅预警主题失败 {topic}: {e}")
    
    async def _handle_alert_message(self, client, userdata, message):
        """处理预警消息"""
        try:
            # 解析消息
            topic = message.topic
            payload = message.payload.decode('utf-8')
            alert_data = json.loads(payload)
            
            logger.bind(tag=TAG).info(f"收到预警消息: topic={topic}")
            logger.bind(tag=TAG).debug(f"预警内容类型: {type(alert_data)}")
            
            # 处理不同格式的预警数据
            if isinstance(alert_data, list):
                # 数组格式：处理多个预警
                logger.bind(tag=TAG).info(f"处理预警数组，包含 {len(alert_data)} 条预警")
                for idx, single_alert in enumerate(alert_data):
                    try:
                        await self._process_weather_alert(single_alert, topic, idx)
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"处理第{idx+1}条预警失败: {e}")
            elif isinstance(alert_data, dict):
                # 单个对象格式
                logger.bind(tag=TAG).info("处理单个预警对象")
                await self._process_weather_alert(alert_data, topic)
            else:
                logger.bind(tag=TAG).warning(f"未知的预警数据格式: {type(alert_data)}")
            
        except json.JSONDecodeError as e:
            logger.bind(tag=TAG).error(f"预警消息JSON解析失败: {e}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理预警消息失败: {e}")
    
    async def _process_weather_alert(self, alert_data: Dict[str, Any], topic: str, alert_index: int = 0):
        """处理气象预警"""
        try:
            # 验证预警数据格式
            if not self._validate_alert_data(alert_data):
                logger.bind(tag=TAG).warning("预警数据格式验证失败")
                return
            
            # 提取预警信息
            alert_info = self._extract_alert_info(alert_data)
            
            # 根据主题类型确定目标设备
            target_devices = await self._determine_target_devices(alert_data, topic)
            
            if not target_devices:
                logger.bind(tag=TAG).warning("未找到目标设备，跳过预警播报")
                return
            
            # 生成预警播报内容
            alert_content = self._generate_alert_content(alert_info)
            
            # 向目标设备发送预警
            for device_id in target_devices:
                await self._send_alert_to_device(device_id, alert_content, alert_info)
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理预警失败: {e}")
    
    def _validate_alert_data(self, alert_data: Dict[str, Any]) -> bool:
        """验证预警数据格式"""
        required_fields = ["id", "title", "level", "text", "startTime", "endTime"]
        
        for field in required_fields:
            if field not in alert_data:
                logger.bind(tag=TAG).warning(f"预警数据缺少必要字段: {field}")
                return False
                
        return True
    
    def _extract_alert_info(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取预警关键信息"""
        return {
            "id": alert_data.get("id", ""),
            "sender": alert_data.get("sender", "气象台"),
            "title": alert_data.get("title", ""),
            "level": alert_data.get("level", ""),
            "severity": alert_data.get("severity", ""),
            "severity_color": alert_data.get("severityColor", ""),
            "type_name": alert_data.get("typeName", ""),
            "text": alert_data.get("text", ""),
            "start_time": alert_data.get("startTime", ""),
            "end_time": alert_data.get("endTime", ""),
            "pub_time": alert_data.get("pubTime", ""),
            "status": alert_data.get("status", "active")
        }
    
    async def _determine_target_devices(self, alert_data: Dict[str, Any], topic: str) -> List[str]:
        """确定目标设备列表"""
        target_devices = []
        
        try:
            # 1. 处理Java后端的预警主题格式: server/dev/report/earlyWarning/设备id
            if "earlyWarning/" in topic:
                device_id = topic.split("earlyWarning/")[-1]
                if device_id and device_id != "+":
                    target_devices.append(device_id)
                    logger.bind(tag=TAG).info(f"从Java后端主题提取设备ID: {device_id}")
                    return target_devices
            
            # 2. 如果topic包含设备ID，直接使用（兼容旧格式）
            if "/device/" in topic:
                device_id = topic.split("/device/")[-1]
                if device_id and device_id != "+":
                    target_devices.append(device_id)
                    logger.bind(tag=TAG).info(f"从topic提取设备ID: {device_id}")
                    return target_devices
            
            # 2. 如果预警数据中包含设备列表
            if "deviceIds" in alert_data:
                device_ids = alert_data["deviceIds"]
                if isinstance(device_ids, list):
                    target_devices.extend(device_ids)
                elif isinstance(device_ids, str):
                    target_devices.append(device_ids)
                logger.bind(tag=TAG).info(f"从预警数据提取设备ID: {target_devices}")
                return target_devices
            
            # 3. 根据预警发布机构匹配设备
            sender = alert_data.get("sender", "")
            for device_id, location in self.device_location_mapping.items():
                if location in sender or sender in location:
                    target_devices.append(device_id)
                    
            if target_devices:
                logger.bind(tag=TAG).info(f"根据发布机构匹配设备: {target_devices}")
                return target_devices
            
            # 4. 广播模式：所有设备
            if "broadcast" in topic or not target_devices:
                target_devices = list(self.device_location_mapping.keys())
                logger.bind(tag=TAG).info(f"广播模式，目标所有设备: {len(target_devices)}个")
            
            return target_devices
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"确定目标设备失败: {e}")
            return []
    
    def _generate_alert_content(self, alert_info: Dict[str, Any]) -> str:
        """生成预警播报内容"""
        try:
            # 获取配置
            alert_config = self.config.get("weather_alert", {}).get("alert_processing", {})
            max_length = alert_config.get("max_content_length", 300)
            priority_levels = alert_config.get("priority_levels", {})
            type_mapping = alert_config.get("type_mapping", {})
            
            # 提取关键信息
            sender = alert_info.get("sender", "气象台")
            title = alert_info.get("title", "")
            level = alert_info.get("level", "")
            type_name = alert_info.get("type_name", "")
            alert_type = alert_info.get("type", "")
            text = alert_info.get("text", "")
            
            # 转换预警级别为中文
            level_text = priority_levels.get(level, level)
            
            # 转换预警类型为中文
            type_text = type_mapping.get(alert_type, type_name or "天气预警")
            
            # 生成播报内容
            if level in ["Red", "Orange"]:  # 高优先级预警
                alert_content = f"""
紧急{type_text}预警！

{sender}发布{level_text}级预警

{text}

请立即采取防护措施，确保人身安全！
                """.strip()
            else:  # 普通预警
                alert_content = f"""
{type_text}预警通知

{sender}发布{level_text}级预警

{text}

请注意防范，做好相应准备。
                """.strip()
            
            # 限制长度，避免播报时间过长
            if len(alert_content) > max_length:
                # 保留重要部分，截取内容
                important_part = f"{type_text}{level_text}级预警通知。{text}"
                if len(important_part) > max_length - 20:
                    alert_content = important_part[:max_length-23] + "...请注意防范！"
                else:
                    alert_content = important_part + "请注意防范！"
                
            logger.bind(tag=TAG).debug(f"生成预警播报内容: {len(alert_content)}字符")
            
            return alert_content
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"生成预警内容失败: {e}")
            return "收到紧急预警通知，请注意安全！"
    
    async def _send_alert_to_device(self, device_id: str, alert_content: str, alert_info: Dict[str, Any]):
        """向指定设备发送预警"""
        try:
            logger.bind(tag=TAG).info(f"开始向设备 {device_id} 发送预警")
            
            # 构建预警消息
            alert_message = {
                "type": "weather_alert",
                "device_id": device_id,
                "alert_id": alert_info.get("id", ""),
                "content": alert_content,
                "urgency": "high",  # 预警都是高优先级
                "timestamp": datetime.now().isoformat()
            }
            
            # 使用现有的唤醒服务发送预警
            if hasattr(self.awaken_service, 'send_awaken_with_tts'):
                success = await self.awaken_service.send_awaken_with_tts(
                    device_id=device_id,
                    tts_text=alert_content,
                    callback_data=alert_message
                )
                
                if success:
                    logger.bind(tag=TAG).info(f"预警发送成功: {device_id}")
                else:
                    logger.bind(tag=TAG).error(f"预警发送失败: {device_id}")
            else:
                logger.bind(tag=TAG).warning("唤醒服务不可用，无法发送预警")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"向设备 {device_id} 发送预警失败: {e}")
    
    async def publish_test_alert(self, device_id: str = None):
        """发布测试预警（用于调试）"""
        try:
            test_alert = {
                "id": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "sender": "测试气象台",
                "pubTime": datetime.now().isoformat(),
                "title": "测试预警信号",
                "startTime": datetime.now().isoformat(),
                "endTime": (datetime.now().replace(hour=23, minute=59)).isoformat(),
                "status": "active",
                "level": "Yellow",
                "severity": "Moderate",
                "severityColor": "Yellow",
                "type": "test",
                "typeName": "Test Alert",
                "text": "这是一条测试预警信息，用于验证预警系统功能。请忽略此消息。",
                "deviceIds": [device_id] if device_id else []
            }
            
            # 选择发布主题
            topic = f"weather/alert/device/{device_id}" if device_id else "weather/alert/broadcast"
            
            # 发布测试预警
            if hasattr(self.mqtt_client, 'publish'):
                await self.mqtt_client.publish(
                    topic, 
                    json.dumps(test_alert, ensure_ascii=False),
                    qos=1
                )
                logger.bind(tag=TAG).info(f"发布测试预警成功: {topic}")
            else:
                logger.bind(tag=TAG).warning("MQTT客户端不支持publish方法")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"发布测试预警失败: {e}")


# 单例模式
_weather_alert_service = None

def get_weather_alert_service(mqtt_client: MQTTClient = None) -> WeatherAlertService:
    """获取预警服务单例"""
    global _weather_alert_service
    if _weather_alert_service is None:
        _weather_alert_service = WeatherAlertService(mqtt_client)
    return _weather_alert_service

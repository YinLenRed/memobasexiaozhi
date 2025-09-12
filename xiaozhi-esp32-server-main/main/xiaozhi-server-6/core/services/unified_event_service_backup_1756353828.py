#!/usr/bin/env python3
"""
统一事件服务
处理Java后端推送的各种事件：天气预警、24节气、节假日等
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from loguru import logger

from core.mqtt.mqtt_client import MQTTClient
from core.mqtt.webhook_callback_handler import AwakenWithCallbackService
from config.config_loader import load_config
from core.utils import llm as llm_utils
from core.utils.modules_initialize import initialize_tts
from core.queue.message_queue_manager import MessageQueueManager
from core.mqtt.message_rate_limiter import get_rate_limiter, RateLimitConfig

TAG = "UnifiedEventService"

class EventType:
    """事件类型常量"""
    WEATHER_ALERT = "weather_alert"
    SOLAR_TERM = "solar_term" 
    HOLIDAY = "holiday"
    UNKNOWN = "unknown"

class EventParser:
    """事件解析器"""
    
    @staticmethod
    def detect_event_type(event_data: Dict[str, Any]) -> str:
        """检测事件类型"""
        try:
            # 检查是否是天气预警
            if EventParser._is_weather_alert(event_data):
                return EventType.WEATHER_ALERT
            
            # 检查是否是24节气
            if EventParser._is_solar_term(event_data):
                return EventType.SOLAR_TERM
                
            # 检查是否是节假日
            if EventParser._is_holiday(event_data):
                return EventType.HOLIDAY
                
            return EventType.UNKNOWN
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"事件类型检测失败: {e}")
            return EventType.UNKNOWN
    
    @staticmethod
    def _is_weather_alert(data: Dict[str, Any]) -> bool:
        """判断是否为天气预警"""
        # Java后端标准格式检测
        if "weather_alert" in str(data.get("event_type", "")).lower():
            return True
        
        # 新增：支持topic字段检测
        topic = str(data.get("topic", ""))
        if "天气" in topic and ("预警" in topic or "警报" in topic or "预报" in topic):
            return True
            
        # 传统格式检测
        weather_fields = ["level", "severity", "type", "typeName", "sender"]
        return any(field in data for field in weather_fields) and \
               ("气象" in str(data.get("sender", "")) or 
                "预警" in str(data.get("title", "")) or
                "天气" in str(data.get("title", "")))
    
    @staticmethod
    def _is_solar_term(data: Dict[str, Any]) -> bool:
        """判断是否为24节气"""
        # Java后端标准格式检测
        if "solar_term" in str(data.get("event_type", "")).lower():
            return True
        
        # 新增：支持topic字段检测
        topic = str(data.get("topic", ""))
        if "节气" in topic or "立春" in topic or "立夏" in topic or "立秋" in topic or "立冬" in topic:
            return True
            
        # 传统格式检测
        return "solar_term" in data or "节气" in str(data.get("title", "")) or \
               "festival" in data
    
    @staticmethod
    def _is_holiday(data: Dict[str, Any]) -> bool:
        """判断是否为节假日"""
        # Java后端标准格式检测
        if "holiday" in str(data.get("event_type", "")).lower():
            return True
        
        # 新增：支持topic字段检测
        topic = str(data.get("topic", ""))
        if ("节假日" in topic or "节日" in topic or "假期" in topic or 
            "春节" in topic or "中秋" in topic or "国庆" in topic or "元旦" in topic):
            return True
            
        # 传统格式检测
        return "holiday" in data or \
               "节假日" in str(data.get("title", "")) or \
               "节日" in str(data.get("title", ""))

class UnifiedEventService:
    """统一事件服务类"""
    
    def __init__(self, mqtt_client: MQTTClient = None):
        self.config = load_config()
        self.mqtt_client = mqtt_client

        self.event_topics = self._get_event_topics()
        self.device_location_mapping = self._get_device_location_mapping()
        self.is_running = False
        self.event_parser = EventParser()
        
        # 初始化LLM用于Java后端prompt处理
        self.llm = None
        self._initialize_llm()
        
        # 初始化TTS提供器 - 修复Java事件TTS问题
        try:
            self.tts_provider = initialize_tts(self.config)
            logger.bind(tag=TAG).info("✅ UnifiedEventService TTS提供器初始化成功")
        except Exception as e:
            logger.bind(tag=TAG).error(f"❌ UnifiedEventService TTS提供器初始化失败: {e}")
            self.tts_provider = None
        
        # 现在使用初始化的TTS提供器创建AwakenWithCallbackService
        self.awaken_service = AwakenWithCallbackService(self.config, mqtt_client, self.tts_provider)
        
        # 初始化消息队列管理器
        self.message_queue = MessageQueueManager(unified_event_service=self)
        logger.bind(tag=TAG).info("✅ 消息队列管理器初始化成功")
        
        # 初始化MQTT消息限流器
        self._init_rate_limiter()
        
    def _get_event_topics(self) -> List[str]:
        """获取事件订阅主题列表"""
        return self.config.get("event_system", {}).get("topics", [
            "server/dev/report/event"
        ])
    
    def _get_device_location_mapping(self) -> Dict[str, str]:
        """获取设备与地区的映射关系"""
        return self.config.get("event_system", {}).get("device_location_mapping", {})
    
    async def start(self):
        """启动事件服务"""
        if self.is_running:
            logger.bind(tag=TAG).warning("事件服务已在运行中")
            return
            
        try:
            if not self.mqtt_client:
                logger.bind(tag=TAG).error("MQTT客户端未初始化")
                return
                
            # 订阅所有事件主题
            for topic in self.event_topics:
                await self._subscribe_event_topic(topic)
            
            # 注册设备事件处理器（用于处理EVT_SPEAK_DONE等事件）
            if hasattr(self.mqtt_client, 'register_message_handler'):
                self.mqtt_client.register_message_handler(
                    "device/+/event", 
                    self._handle_device_event
                )
                logger.bind(tag=TAG).info("✅ 注册设备事件处理器成功")
                
            self.is_running = True
            logger.bind(tag=TAG).info(f"统一事件服务启动成功，订阅主题: {self.event_topics}")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"启动事件服务失败: {e}")
            raise
    
    async def stop(self):
        """停止事件服务"""
        if not self.is_running:
            return
            
        try:
            # 取消订阅所有事件主题
            for topic in self.event_topics:
                if hasattr(self.mqtt_client, 'unsubscribe'):
                    await self.mqtt_client.unsubscribe(topic)
                    
            self.is_running = False
            logger.bind(tag=TAG).info("统一事件服务已停止")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"停止事件服务失败: {e}")
    
    async def _subscribe_event_topic(self, topic: str):
        """订阅事件主题"""
        try:
            # 设置消息回调
            if hasattr(self.mqtt_client, 'set_message_callback'):
                self.mqtt_client.set_message_callback(self._handle_event_message)
            
            # 订阅主题
            if hasattr(self.mqtt_client, 'subscribe'):
                await self.mqtt_client.subscribe(topic, qos=1)
                logger.bind(tag=TAG).info(f"订阅事件主题成功: {topic}")
            else:
                logger.bind(tag=TAG).warning(f"MQTT客户端不支持subscribe方法")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"订阅事件主题失败 {topic}: {e}")
    
    async def _handle_event_message(self, client, userdata, message):
        """处理事件消息"""
        try:
            # 解析消息
            topic = message.topic
            payload = message.payload.decode('utf-8')
            event_data = json.loads(payload)
            
            # 从topic中提取device_id (如: device/f0:9e:9e:04:8a:44/event -> f0:9e:9e:04:8a:44)
            device_id = self._extract_device_id_from_topic(topic)
            
            # 检查是否为设备事件（EVT_SPEAK_DONE等）
            if self._is_device_event(event_data):
                logger.bind(tag=TAG).info(f"🎯 识别为设备事件，转发给消息队列管理器: topic={topic}")
                await self._handle_device_event(event_data, device_id, topic)
                return
            
            # 应用MQTT消息限流器
            if self.rate_limiter and device_id:
                if not self.rate_limiter.is_allowed(device_id, "business_event"):
                    logger.bind(tag=TAG).warning(f"🚫 消息被限流器阻断: {device_id}")
                    return
            
            logger.bind(tag=TAG).info(f"收到事件消息: topic={topic}")
            logger.bind(tag=TAG).info(f"📋 事件数据: {event_data}")
            logger.bind(tag=TAG).debug(f"事件内容类型: {type(event_data)}")
            
            # 处理不同格式的事件数据
            if isinstance(event_data, dict) and "data" in event_data and isinstance(event_data["data"], list):
                # Java后端格式：包含data数组的对象格式
                logger.bind(tag=TAG).info(f"处理Java后端事件数组，包含 {len(event_data['data'])} 个事件")
                
                # 提取全局字段
                global_fields = {k: v for k, v in event_data.items() if k != "data"}
                
                for idx, single_event in enumerate(event_data["data"]):
                    try:
                        # 合并全局字段和单个事件数据
                        merged_event = {**global_fields, **single_event}
                        await self._process_single_event(merged_event, topic, idx)
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"处理第{idx+1}个事件失败: {e}")
                        
            elif isinstance(event_data, list):
                # 旧格式：直接的数组格式（向后兼容）
                logger.bind(tag=TAG).info(f"处理事件数组，包含 {len(event_data)} 个事件")
                for idx, single_event in enumerate(event_data):
                    try:
                        await self._process_single_event(single_event, topic, idx)
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"处理第{idx+1}个事件失败: {e}")
            elif isinstance(event_data, dict):
                # 单个对象格式
                logger.bind(tag=TAG).info("处理单个事件对象")
                await self._process_single_event(event_data, topic)
            else:
                logger.bind(tag=TAG).warning(f"未知的事件数据格式: {type(event_data)}")
            
        except json.JSONDecodeError as e:
            logger.bind(tag=TAG).error(f"事件消息JSON解析失败: {e}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理事件消息失败: {e}")
    
    async def _process_single_event(self, event_data: Dict[str, Any], topic: str, event_index: int = 0):
        """处理单个事件"""
        try:
            # 检测事件类型
            event_type = self.event_parser.detect_event_type(event_data)
            logger.bind(tag=TAG).info(f"检测到事件类型: {event_type}")
            
            # 获取目标设备
            target_devices = await self._determine_target_devices(event_data, topic)
            logger.bind(tag=TAG).info(f"🎯 目标设备: {target_devices}")
            
            if not target_devices:
                logger.bind(tag=TAG).warning("未找到目标设备，跳过事件处理")
                return
            
            # 根据事件类型处理
            if event_type == EventType.WEATHER_ALERT:
                await self._process_weather_alert(event_data, target_devices)
            elif event_type == EventType.SOLAR_TERM:
                await self._process_solar_term(event_data, target_devices)
            elif event_type == EventType.HOLIDAY:
                await self._process_holiday(event_data, target_devices)
            else:
                logger.bind(tag=TAG).warning(f"未知事件类型: {event_type}")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理事件失败: {e}")
    
    async def _determine_target_devices(self, event_data: Dict[str, Any], topic: str) -> List[str]:
        """确定目标设备列表"""
        target_devices = []
        
        try:
            logger.bind(tag=TAG).info(f"🔍 开始确定目标设备，主题: {topic}")
            logger.bind(tag=TAG).info(f"🔍 事件数据包含字段: {list(event_data.keys())}")
            
            # 1. 优先从消息体中的device_id字段提取设备ID（Java后端新方案）
            if "device_id" in event_data:
                device_id = event_data["device_id"]
                logger.bind(tag=TAG).info(f"✅ 找到device_id字段: {device_id}")
                if device_id:
                    target_devices.append(device_id)
                    logger.bind(tag=TAG).info(f"从消息体提取设备ID: {device_id}")
                    return target_devices
                else:
                    logger.bind(tag=TAG).warning("device_id字段为空")
            else:
                logger.bind(tag=TAG).info("❌ 未找到device_id字段")
            
            # 2. 如果事件数据中包含设备列表（兼容性）
            if "deviceIds" in event_data:
                device_ids = event_data["deviceIds"]
                if isinstance(device_ids, list):
                    target_devices.extend(device_ids)
                elif isinstance(device_ids, str):
                    target_devices.append(device_ids)
                logger.bind(tag=TAG).info(f"从事件数据提取设备ID: {target_devices}")
                return target_devices
            
            # 3. 从主题路径提取设备ID（向后兼容）
            if "/event/" in topic:
                device_id = topic.split("/event/")[-1]
                if device_id and device_id != "+" and device_id.strip():
                    target_devices.append(device_id)
                    logger.bind(tag=TAG).info(f"从主题提取设备ID: {device_id}")
                    return target_devices
            
            # 3. 根据发布机构匹配设备（针对天气预警）
            sender = event_data.get("sender", "")
            if sender:
                for device_id, location in self.device_location_mapping.items():
                    if location in sender or sender in location:
                        target_devices.append(device_id)
                        
                if target_devices:
                    logger.bind(tag=TAG).info(f"根据发布机构匹配设备: {target_devices}")
                    return target_devices
            
            # 4. 广播模式：所有设备
            if not target_devices:
                target_devices = list(self.device_location_mapping.keys())
                logger.bind(tag=TAG).info(f"广播模式，目标所有设备: {len(target_devices)}个")
            
            return target_devices
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"确定目标设备失败: {e}")
            return []
    
    async def _process_weather_alert(self, alert_data: Dict[str, Any], target_devices: List[str]):
        """处理天气预警事件"""
        try:
            logger.bind(tag=TAG).info("处理天气预警事件")
            
            # 1. 优先尝试使用Java后端prompt生成内容
            alert_content = await self._generate_content_with_java_prompt(alert_data)
            
            # 2. 如果没有prompt或生成失败，使用传统方式
            if not alert_content:
                # 验证预警数据
                if not self._validate_weather_alert(alert_data):
                    logger.bind(tag=TAG).warning("天气预警数据验证失败")
                    return
                
                # 使用硬编码逻辑生成内容
                alert_content = self._generate_weather_alert_content(alert_data)
                logger.bind(tag=TAG).info("使用传统硬编码方式生成天气预警内容")
            else:
                logger.bind(tag=TAG).info("✅ 使用Java后端prompt生成天气预警内容")
            
            # 向目标设备发送预警
            for device_id in target_devices:
                await self._send_event_to_device(device_id, alert_content, alert_data, "weather_alert")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理天气预警失败: {e}")
    
    async def _process_solar_term(self, term_data: Dict[str, Any], target_devices: List[str]):
        """处理24节气事件"""
        try:
            logger.bind(tag=TAG).info("处理24节气事件")
            
            # 1. 优先尝试使用Java后端prompt生成内容
            logger.bind(tag=TAG).info(f"🔍 尝试使用Java后端prompt生成24节气内容")
            logger.bind(tag=TAG).info(f"📋 可用字段: {list(term_data.keys())}")
            logger.bind(tag=TAG).info(f"📄 prompt字段: {term_data.get('prompt')}")
            logger.bind(tag=TAG).info(f"📄 data字段: {term_data.get('data')}")
            logger.bind(tag=TAG).info(f"📄 result字段: {term_data.get('result')}")
            
            term_content = await self._generate_content_with_java_prompt(term_data)
            
            # 2. 如果没有prompt或生成失败，使用传统方式
            if not term_content:
                # 使用硬编码逻辑生成内容
                term_content = self._generate_solar_term_content(term_data)
                logger.bind(tag=TAG).info("使用传统硬编码方式生成24节气内容")
            else:
                logger.bind(tag=TAG).info("✅ 使用Java后端prompt生成24节气内容")
            
            # 向目标设备发送提醒
            for device_id in target_devices:
                await self._send_event_to_device(device_id, term_content, term_data, "solar_term")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理24节气失败: {e}")
    
    async def _process_holiday(self, holiday_data: Dict[str, Any], target_devices: List[str]):
        """处理节假日事件"""
        try:
            logger.bind(tag=TAG).info("处理节假日事件")
            
            # 1. 优先尝试使用Java后端prompt生成内容
            holiday_content = await self._generate_content_with_java_prompt(holiday_data)
            
            # 2. 如果没有prompt或生成失败，使用传统方式
            if not holiday_content:
                # 使用硬编码逻辑生成内容
                holiday_content = self._generate_holiday_content(holiday_data)
                logger.bind(tag=TAG).info("使用传统硬编码方式生成节假日内容")
            else:
                logger.bind(tag=TAG).info("✅ 使用Java后端prompt生成节假日内容")
            
            # 向目标设备发送祝福
            for device_id in target_devices:
                await self._send_event_to_device(device_id, holiday_content, holiday_data, "holiday")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理节假日失败: {e}")
    
    def _validate_weather_alert(self, alert_data: Dict[str, Any]) -> bool:
        """验证天气预警数据"""
        required_fields = ["id", "title", "level", "text"]
        for field in required_fields:
            if field not in alert_data:
                logger.bind(tag=TAG).warning(f"预警数据缺少必要字段: {field}")
                return False
        return True
    
    def _generate_weather_alert_content(self, alert_data: Dict[str, Any]) -> str:
        """生成天气预警播报内容"""
        try:
            # 获取配置
            alert_config = self.config.get("event_system", {}).get("weather_alert", {})
            max_length = alert_config.get("max_content_length", 300)
            priority_levels = alert_config.get("priority_levels", {})
            type_mapping = alert_config.get("type_mapping", {})
            
            # 提取关键信息
            sender = alert_data.get("sender", "气象台")
            level = alert_data.get("level", "")
            type_name = alert_data.get("typeName", "")
            alert_type = alert_data.get("type", "")
            text = alert_data.get("text", "")
            
            # 转换预警级别和类型
            level_text = priority_levels.get(level, level)
            type_text = type_mapping.get(alert_type, type_name or "天气预警")
            
            # 生成播报内容
            if level in ["Red", "Orange"]:
                alert_content = f"紧急{type_text}预警！{sender}发布{level_text}级预警。{text[:100]}...请立即采取防护措施，确保人身安全！"
            else:
                alert_content = f"{type_text}预警通知。{sender}发布{level_text}级预警。{text[:100]}...请注意防范，做好相应准备。"
            
            # 限制长度
            if len(alert_content) > max_length:
                alert_content = alert_content[:max_length-3] + "..."
                
            return alert_content
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"生成天气预警内容失败: {e}")
            return "收到天气预警通知，请注意安全！"
    
    def _generate_solar_term_content(self, term_data: Dict[str, Any]) -> str:
        """生成24节气播报内容"""
        try:
            # 获取配置
            solar_config = self.config.get("event_system", {}).get("solar_terms", {})
            template = solar_config.get("content_template", "今天是{solar_term}，{description}，{tips}")
            terms_info = solar_config.get("solar_terms_info", {})
            
            # 提取节气信息
            solar_term = term_data.get("solar_term", term_data.get("title", ""))
            
            # 获取节气详细信息
            term_info = terms_info.get(solar_term, {})
            description = term_info.get("description", "二十四节气之一")
            tips = term_info.get("tips", "注意身体健康")
            
            # 生成内容
            content = template.format(
                solar_term=solar_term,
                description=description,
                tips=tips
            )
            
            return content
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"生成24节气内容失败: {e}")
            return "今天是二十四节气，注意身体健康！"
    
    def _generate_holiday_content(self, holiday_data: Dict[str, Any]) -> str:
        """生成节假日播报内容"""
        try:
            # 获取配置
            holiday_config = self.config.get("event_system", {}).get("holidays", {})
            template = holiday_config.get("content_template", "今天是{holiday}，{description}，{greeting}")
            holiday_greetings = holiday_config.get("holiday_greetings", {})
            
            # 提取节假日信息
            holiday = holiday_data.get("festival", holiday_data.get("holiday", holiday_data.get("title", "")))
            
            # 获取节假日详细信息
            holiday_info = holiday_greetings.get(holiday, {})
            description = holiday_info.get("description", "重要节日")
            greeting = holiday_info.get("greeting", "祝您节日快乐！")
            
            # 生成内容
            content = template.format(
                holiday=holiday,
                description=description,
                greeting=greeting
            )
            
            return content
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"生成节假日内容失败: {e}")
            return "祝您节日快乐！"
    
    async def _send_event_to_device(self, device_id: str, content: str, event_data: Dict[str, Any], event_type: str):
        """向指定设备发送事件（使用消息队列）"""
        try:
            logger.bind(tag=TAG).info(f"🎵 添加{event_type}事件到设备队列: {device_id}")
            
            # 设置优先级（预警消息优先级最高）
            priority = 0 if event_type == "weather_alert" else 1
            
            # 构建用户信息
            user_info = {
                "type": event_type,
                "event_id": event_data.get("id", f"{event_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                "urgency": "high" if event_type == "weather_alert" else "normal",
                "timestamp": datetime.now().isoformat(),
                "original_data": event_data
            }
            
            # 添加消息到队列（队列会自动按顺序播放）
            message_id = self.message_queue.add_message(
                device_id=device_id,
                content=content,
                category=event_type,
                priority=priority,
                user_info=user_info
            )
            
            if message_id:
                logger.bind(tag=TAG).info(f"✅ {event_type}事件已入队: {device_id}, 消息ID: {message_id}")
                logger.bind(tag=TAG).info(f"📋 队列状态: {self.message_queue.get_device_queue_status(device_id)}")
            else:
                logger.bind(tag=TAG).error(f"❌ {event_type}事件入队失败: {device_id}")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"向设备 {device_id} 发送{event_type}事件失败: {e}")
    
    def _handle_device_event(self, device_id: str, event_type: str, event_data: Dict):
        """处理设备事件（消息队列集成）"""
        try:
            if event_type == "EVT_SPEAK_DONE":
                track_id = event_data.get("track_id")
                logger.bind(tag=TAG).info(f"🎯 设备播放完成: {device_id}, track_id: {track_id}")
                
                # 通知消息队列当前消息播放完成
                if track_id and self.message_queue:
                    self.message_queue.on_message_completed(device_id, track_id)
                
            elif event_type == "EVT_SPEAK_ERROR":
                track_id = event_data.get("track_id")
                error = event_data.get("error", "未知错误")
                logger.bind(tag=TAG).error(f"❌ 设备播放失败: {device_id}, track_id: {track_id}, 错误: {error}")
                
                # 通知消息队列当前消息播放失败
                if track_id and self.message_queue:
                    self.message_queue.on_message_failed(device_id, track_id, error)
            
            else:
                logger.bind(tag=TAG).debug(f"其他设备事件: {device_id}, {event_type}")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理设备事件失败: {e}")
    
    def _initialize_llm(self):
        """初始化LLM用于Java后端prompt处理"""
        try:
            # 获取LLM配置
            llm_config = self.config.get("LLM", {})
            selected_llm = self.config.get("selected_module", {}).get("LLM", "ChatGLMLLM")
            
            if not llm_config or selected_llm not in llm_config:
                logger.bind(tag=TAG).warning("未找到LLM配置，Java后端prompt功能将不可用")
                return
            
            llm_type = llm_config[selected_llm].get("type", selected_llm)
            self.llm = llm_utils.create_instance(llm_type, llm_config[selected_llm])
            logger.bind(tag=TAG).info(f"LLM初始化成功，支持Java后端prompt处理: {selected_llm}")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"LLM初始化失败: {e}")
            logger.bind(tag=TAG).warning("将使用硬编码内容生成逻辑")
    
    def _init_rate_limiter(self):
        """初始化MQTT消息限流器"""
        try:
            # 从配置中获取限流参数
            rate_limit_config = self.config.get("event_system", {}).get("rate_limit", {})
            
            config = RateLimitConfig(
                max_messages_per_second=rate_limit_config.get("max_messages_per_second", 5),  # 降低默认限制
                max_messages_per_minute=rate_limit_config.get("max_messages_per_minute", 100),
                max_queue_size=rate_limit_config.get("max_queue_size", 500),
                burst_limit=rate_limit_config.get("burst_limit", 10),
                cooldown_seconds=rate_limit_config.get("cooldown_seconds", 30)
            )
            
            self.rate_limiter = get_rate_limiter()
            self.rate_limiter.update_config(config)
            
            logger.bind(tag=TAG).info(f"🛡️ MQTT消息限流器已初始化")
            logger.bind(tag=TAG).info(f"   每秒最大: {config.max_messages_per_second}")
            logger.bind(tag=TAG).info(f"   每分钟最大: {config.max_messages_per_minute}")
            logger.bind(tag=TAG).info(f"   冷却时间: {config.cooldown_seconds}秒")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"❌ 限流器初始化失败: {e}")
            self.rate_limiter = None
    
    def _extract_device_id_from_topic(self, topic: str) -> Optional[str]:
        """从MQTT topic中提取device_id"""
        try:
            # 常见格式: device/f0:9e:9e:04:8a:44/event -> f0:9e:9e:04:8a:44
            # 或: xiaozhi/java-to-python/device-status/f0:9e:9e:04:8a:44 -> f0:9e:9e:04:8a:44
            
            if "device/" in topic and "/event" in topic:
                # device/f0:9e:9e:04:8a:44/event
                parts = topic.split("/")
                if len(parts) >= 3 and parts[0] == "device":
                    device_id = parts[1]
                    logger.bind(tag=TAG).debug(f"从topic提取device_id: {topic} -> {device_id}")
                    return device_id
            
            elif "device-status/" in topic:
                # xiaozhi/java-to-python/device-status/f0:9e:9e:04:8a:44
                parts = topic.split("/")
                for i, part in enumerate(parts):
                    if part == "device-status" and i + 1 < len(parts):
                        device_id = parts[i + 1]
                        logger.bind(tag=TAG).debug(f"从topic提取device_id: {topic} -> {device_id}")
                        return device_id
            
            logger.bind(tag=TAG).debug(f"无法从topic提取device_id: {topic}")
            return None
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"从topic提取device_id失败: {e}")
            return None
    
    def _is_device_event(self, event_data: Dict[str, Any]) -> bool:
        """判断是否为设备事件（而非业务事件）"""
        try:
            # 检查是否包含设备事件标识字段
            event_type = event_data.get("evt") or event_data.get("event_type")
            
            if event_type:
                # 设备事件类型列表
                device_event_types = [
                    "EVT_SPEAK_DONE",    # 播放完成
                    "EVT_SPEAK_ERROR",   # 播放错误
                    "EVT_AWAKEN",        # 唤醒事件
                    "EVT_ASR_START",     # ASR开始
                    "EVT_ASR_END",       # ASR结束
                    "EVT_DEVICE_ONLINE", # 设备上线
                    "EVT_DEVICE_OFFLINE",# 设备下线
                    "EVT_HEARTBEAT"      # 心跳
                ]
                
                if str(event_type) in device_event_types:
                    return True
            
            # 检查是否包含设备特有字段组合
            device_fields = ["track_id", "timestamp"]
            has_device_fields = all(field in event_data for field in device_fields)
            
            # 检查是否缺少业务事件字段
            business_fields = ["title", "prompt", "data", "content", "result", "festival"]
            has_business_fields = any(field in event_data for field in business_fields)
            
            # 如果有设备字段但没有业务字段，认为是设备事件
            if has_device_fields and not has_business_fields:
                return True
            
            return False
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"判断设备事件类型失败: {e}")
            return False
    
    async def _handle_device_event(self, event_data: Dict[str, Any], device_id: str, topic: str):
        """处理设备事件（异步版本）"""
        try:
            event_type = event_data.get("evt") or event_data.get("event_type")
            
            if event_type == "EVT_SPEAK_DONE":
                track_id = event_data.get("track_id")
                logger.bind(tag=TAG).info(f"🎯 设备播放完成: {device_id}, track_id: {track_id}")
                
                # 通知消息队列当前消息播放完成
                if track_id and self.message_queue and device_id:
                    self.message_queue.on_message_completed(device_id, track_id)
                else:
                    logger.bind(tag=TAG).warning(f"⚠️ 播放完成事件缺少必要信息: device_id={device_id}, track_id={track_id}")
                
            elif event_type == "EVT_SPEAK_ERROR":
                track_id = event_data.get("track_id")
                error = event_data.get("error", "未知错误")
                logger.bind(tag=TAG).error(f"❌ 设备播放失败: {device_id}, track_id: {track_id}, 错误: {error}")
                
                # 通知消息队列当前消息播放失败
                if track_id and self.message_queue and device_id:
                    self.message_queue.on_message_failed(device_id, track_id, error)
                    
            else:
                logger.bind(tag=TAG).info(f"🔄 其他设备事件: {event_type}, device: {device_id}")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理设备事件失败: {e}")
    
    async def _generate_content_with_java_prompt(self, event_data: Dict[str, Any]) -> Optional[str]:
        """使用Java后端prompt和result生成内容"""
        try:
            logger.bind(tag=TAG).info(f"🔄 开始Java后端prompt处理")
            
            # 检查是否包含Java后端prompt字段
            prompt = event_data.get("prompt")
            # 兼容Java后端的多种数据字段
            result = (event_data.get("result") or 
                     event_data.get("content") or      # 新增：支持content字段
                     event_data.get("data") or 
                     event_data.get("festival"))
            
            # 如果没有单独的内容字段，尝试从title+content构建
            if not result and event_data.get("title"):
                title = event_data.get("title", "")
                content = event_data.get("content", "")
                result = f"{title}: {content}" if content else title
            
            logger.bind(tag=TAG).info(f"🔍 检查字段: prompt='{prompt}', result='{result}'")
            
            if not prompt or not result:
                logger.bind(tag=TAG).info("❌ 事件数据不包含prompt或result/data/festival字段，使用传统处理方式")
                logger.bind(tag=TAG).info(f"   prompt是否为空: {not prompt}, result/data/festival是否为空: {not result}")
                return None
                
            if not self.llm:
                logger.bind(tag=TAG).warning("❌ LLM未初始化，无法处理Java后端prompt")
                logger.bind(tag=TAG).info(f"   LLM对象: {self.llm}")
                return None
            
            logger.bind(tag=TAG).info(f"🎯 使用Java后端prompt生成内容")
            logger.bind(tag=TAG).info(f"📋 Prompt: {prompt}")
            logger.bind(tag=TAG).info(f"📄 Result: {result}")
            
            # 构建LLM输入消息
            system_prompt = "你是一个智能语音助手，需要根据提供的信息和提示词生成合适的播报内容。"
            user_message = f"""
根据以下信息生成播报内容：

信息内容：{result}

处理提示：{prompt}

请生成一段适合语音播报的内容，要求：
1. 语言自然流畅
2. 重点突出
3. 长度适中（100-200字）
4. 语气符合事件性质
"""

            # 调用LLM生成内容 - 修复方法名
            generated_content = self.llm.response_no_stream(system_prompt, user_message)
            generated_content = generated_content.strip()
            
            logger.bind(tag=TAG).info(f"✅ Java后端prompt生成内容: {generated_content}")
            return generated_content
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Java后端prompt内容生成失败: {e}")
            return None

# 单例模式
_unified_event_service = None

def get_unified_event_service(mqtt_client: MQTTClient = None) -> UnifiedEventService:
    """获取统一事件服务单例"""
    global _unified_event_service
    if _unified_event_service is None:
        _unified_event_service = UnifiedEventService(mqtt_client)
    return _unified_event_service

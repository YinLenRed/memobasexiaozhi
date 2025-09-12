import json
import asyncio
from aiohttp import web
from typing import Dict, Any
from config.logger import setup_logging

TAG = __name__


class GreetingHandler:
    """主动问候API处理器"""
    
    def __init__(self, config: dict, mqtt_manager=None):
        self.config = config
        self.mqtt_manager = mqtt_manager
        self.logger = setup_logging()
    
    def set_mqtt_manager(self, mqtt_manager):
        """设置MQTT管理器"""
        self.mqtt_manager = mqtt_manager
    
    def _is_device_online(self, device_id: str) -> bool:
        """判断设备是否在线（优先使用Java报告的状态）"""
        if not self.mqtt_manager:
            return False
        
        # 优先使用Java报告的设备状态
        return self.mqtt_manager.is_device_online(device_id)
    
    async def handle_webhook_trigger(self, request: web.Request) -> web.Response:
        """处理Java后端webhook触发请求"""
        try:
            # 检查MQTT管理器是否可用
            if not self.mqtt_manager:
                return web.json_response(
                    {"error": "MQTT服务未启用", "code": "MQTT_NOT_AVAILABLE"},
                    status=503
                )
            
            # 解析webhook数据
            try:
                webhook_data = await request.json()
            except Exception as e:
                return web.json_response(
                    {"error": f"JSON解析失败: {e}", "code": "INVALID_JSON"},
                    status=400
                )
            
            # 提取必要参数
            device_id = webhook_data.get("device_id")
            message_content = webhook_data.get("message", webhook_data.get("content", ""))
            message_type = webhook_data.get("type", "java_trigger")
            
            if not device_id or not message_content:
                return web.json_response(
                    {"error": "缺少必要参数: device_id, message", "code": "MISSING_PARAMS"},
                    status=400
                )
            
            self.logger.bind(tag=TAG).info(f"🔔 收到Java webhook触发: {device_id}, 消息: {message_content[:50]}...")
            
            # 🔧 关键修复：直接使用WebhookCallbackHandler处理
            if hasattr(self.mqtt_manager, 'webhook_handler'):
                # 注册webhook请求
                track_id = await self.mqtt_manager.webhook_handler.register_awaken_request(
                    device_id, message_content
                )
                
                # 发送MQTT唤醒命令（触发设备ACK流程）
                mqtt_success = await self._send_mqtt_awaken_command(device_id, message_content, track_id)
                
                return web.json_response({
                    "success": True,
                    "track_id": track_id,
                    "message": "Webhook触发成功",
                    "mqtt_sent": mqtt_success,
                    "device_id": device_id
                })
            else:
                # 备用方案：使用问候服务
                return await self._fallback_greeting_trigger(device_id, message_content, webhook_data)
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"❌ Webhook处理失败: {e}")
            return web.json_response(
                {"error": f"处理失败: {e}", "code": "WEBHOOK_ERROR"},
                status=500
            )
    
    async def _send_mqtt_awaken_command(self, device_id: str, message: str, track_id: str) -> bool:
        """发送MQTT唤醒命令"""
        try:
            if not self.mqtt_manager or not self.mqtt_manager.mqtt_client:
                return False
            
            # 构建MQTT消息
            mqtt_message = {
                "type": "awaken",
                "track_id": track_id,
                "message": message,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # 发送到设备主题
            topic = f"server/{device_id}/awaken"
            success = await self.mqtt_manager.mqtt_client.publish(topic, mqtt_message)
            
            if success:
                self.logger.bind(tag=TAG).info(f"✅ MQTT唤醒命令发送成功: {device_id}, track_id: {track_id}")
            else:
                self.logger.bind(tag=TAG).warning(f"⚠️ MQTT唤醒命令发送失败: {device_id}")
                
            return success
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"❌ MQTT唤醒命令发送异常: {e}")
            return False
    
    async def _fallback_greeting_trigger(self, device_id: str, message: str, webhook_data: Dict) -> web.Response:
        """备用问候触发方案"""
        try:
            # 使用现有的问候服务
            if hasattr(self.mqtt_manager, 'greeting_service'):
                track_id = await self.mqtt_manager.greeting_service.send_proactive_greeting(
                    device_id=device_id,
                    initial_content=message,
                    category=webhook_data.get("category", "java_trigger"),
                    user_info=webhook_data.get("user_info")
                )
                
                return web.json_response({
                    "success": True,
                    "track_id": track_id,
                    "message": "备用问候触发成功",
                    "device_id": device_id
                })
            else:
                return web.json_response(
                    {"error": "问候服务不可用", "code": "GREETING_SERVICE_NOT_AVAILABLE"},
                    status=503
                )
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"备用问候触发失败: {e}")
            return web.json_response(
                {"error": f"备用触发失败: {e}", "code": "FALLBACK_ERROR"},
                status=500
            )

    async def handle_post(self, request: web.Request) -> web.Response:
        """处理主动问候POST请求"""
        try:
            # 检查MQTT管理器是否可用
            if not self.mqtt_manager:
                return web.json_response(
                    {"error": "MQTT服务未启用", "code": "MQTT_NOT_AVAILABLE"},
                    status=503
                )
            
            if not self.mqtt_manager.is_connected():
                return web.json_response(
                    {"error": "MQTT未连接", "code": "MQTT_NOT_CONNECTED"},
                    status=503
                )
            
            # 解析请求数据
            try:
                data = await request.json()
            except Exception as e:
                return web.json_response(
                    {"error": f"无效的JSON格式: {str(e)}", "code": "INVALID_JSON"},
                    status=400
                )
            
            # 验证必需字段
            required_fields = ["device_id", "initial_content", "category"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return web.json_response(
                    {
                        "error": f"缺少必需字段: {', '.join(missing_fields)}",
                        "code": "MISSING_FIELDS"
                    },
                    status=400
                )
            
            # 提取请求参数
            device_id = data["device_id"]
            initial_content = data["initial_content"]
            category = data["category"]
            user_info = data.get("user_info", {})
            # 获取优先级参数
            priority = 1  # 默认优先级
            if user_info and 'priority' in user_info:
                try:
                    priority = int(user_info['priority'])
                except (ValueError, TypeError):
                    priority = 1
            
            # 将优先级传递到消息队列（如果使用队列的话）
            memory_info = data.get("memory_info")
            
            # 验证类别
            valid_categories = ["system_reminder", "schedule", "weather", "entertainment", "news"]
            if category not in valid_categories:
                return web.json_response(
                    {
                        "error": f"无效的类别，支持的类别: {', '.join(valid_categories)}",
                        "code": "INVALID_CATEGORY"
                    },
                    status=400
                )
            
            self.logger.bind(tag=TAG).info(
                f"收到主动问候请求: device_id={device_id}, category={category}, content={initial_content[:30]}..."
            )
            
            # 发送主动问候
            try:
                track_id = await self.mqtt_manager.send_proactive_greeting(
                    device_id=device_id,
                    initial_content=initial_content,
                    category=category,
                    user_info=user_info,
                    memory_info=memory_info
                )
                
                response_data = {
                    "success": True,
                    "message": "主动问候发送成功",
                    "track_id": track_id,
                    "device_id": device_id,
                    "timestamp": asyncio.get_event_loop().time()
                }
                
                self.logger.bind(tag=TAG).info(f"主动问候发送成功: track_id={track_id}")
                return web.json_response(response_data, status=200)
                
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"发送主动问候失败: {e}")
                return web.json_response(
                    {
                        "error": f"发送主动问候失败: {str(e)}",
                        "code": "SEND_FAILED"
                    },
                    status=500
                )
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理主动问候请求失败: {e}")
            return web.json_response(
                {
                    "error": f"服务器内部错误: {str(e)}",
                    "code": "INTERNAL_ERROR"
                },
                status=500
            )
    
    async def handle_get(self, request: web.Request) -> web.Response:
        """处理主动问候GET请求（获取状态）"""
        try:
            # 获取查询参数
            device_id = request.query.get("device_id")
            track_id = request.query.get("track_id")
            
            if not device_id:
                return web.json_response(
                    {"error": "缺少device_id参数", "code": "MISSING_DEVICE_ID"},
                    status=400
                )
            
            # 检查MQTT管理器是否可用
            if not self.mqtt_manager:
                return web.json_response(
                    {"error": "MQTT服务未启用", "code": "MQTT_NOT_AVAILABLE"},
                    status=503
                )
            
            # 获取设备状态
            device_state = self.mqtt_manager.get_device_state(device_id, track_id)
            
            # 判断设备是否在线（使用Java报告的状态）
            device_online = self._is_device_online(device_id)
            
            response_data = {
                "device_id": device_id,
                "connected": device_online,
                "mqtt_server_connected": self.mqtt_manager.is_connected(),
                "state": device_state
            }
            
            if track_id:
                response_data["track_id"] = track_id
            
            # 检查是否请求简化响应
            simple = request.query.get("simple", "").lower() == "true"
            if simple:
                return web.json_response({
                    "device_id": device_id,
                    "online": device_online
                }, status=200)
            
            return web.json_response(response_data, status=200)
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取设备状态失败: {e}")
            return web.json_response(
                {
                    "error": f"服务器内部错误: {str(e)}",
                    "code": "INTERNAL_ERROR"
                },
                status=500
            )
    
    async def handle_options(self, request: web.Request) -> web.Response:
        """处理CORS预检请求"""
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "3600"
        }
        return web.Response(headers=headers, status=204)
    
    async def handle_user_profile(self, request: web.Request) -> web.Response:
        """处理用户档案更新请求"""
        try:
            if request.method == "POST":
                # 更新用户档案
                try:
                    data = await request.json()
                except Exception as e:
                    return web.json_response(
                        {"error": f"无效的JSON格式: {str(e)}", "code": "INVALID_JSON"},
                        status=400
                    )
                
                device_id = data.get("device_id")
                user_info = data.get("user_info", {})
            # 获取优先级参数
            priority = 1  # 默认优先级
            if user_info and 'priority' in user_info:
                try:
                    priority = int(user_info['priority'])
                except (ValueError, TypeError):
                    priority = 1
            
            # 将优先级传递到消息队列（如果使用队列的话）
                
                if not device_id:
                    return web.json_response(
                        {"error": "缺少device_id字段", "code": "MISSING_DEVICE_ID"},
                        status=400
                    )
                
                if self.mqtt_manager:
                    self.mqtt_manager.update_user_profile(device_id, user_info)
                
                return web.json_response(
                    {
                        "success": True,
                        "message": "用户档案更新成功",
                        "device_id": device_id
                    },
                    status=200
                )
            
            elif request.method == "GET":
                # 获取用户档案
                device_id = request.query.get("device_id")
                
                if not device_id:
                    return web.json_response(
                        {"error": "缺少device_id参数", "code": "MISSING_DEVICE_ID"},
                        status=400
                    )
                
                user_profile = {}
                if self.mqtt_manager:
                    user_profile = self.mqtt_manager.greeting_service.get_user_profile(device_id)
                
                return web.json_response(
                    {
                        "device_id": device_id,
                        "user_profile": user_profile
                    },
                    status=200
                )
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理用户档案请求失败: {e}")
            return web.json_response(
                {
                    "error": f"服务器内部错误: {str(e)}",
                    "code": "INTERNAL_ERROR"
                },
                status=500
            )
    async def handle_queue_status(self, request: web.Request) -> web.Response:
        """处理队列状态查询请求"""
        try:
            # 获取设备ID
            device_id = request.match_info.get('device_id')
            if not device_id:
                return web.json_response(
                    {"error": "缺少设备ID", "code": "MISSING_DEVICE_ID"},
                    status=400
                )
            
            # 获取队列状态
            if hasattr(self.mqtt_manager, 'unified_event_service') and self.mqtt_manager.unified_event_service:
                if hasattr(self.mqtt_manager.unified_event_service, 'message_queue'):
                    queue_status = self.mqtt_manager.unified_event_service.message_queue.get_device_queue_status(device_id)
                    if queue_status:
                        return web.json_response(queue_status, status=200)
                    else:
                        # 设备没有队列记录，返回空状态
                        return web.json_response({
                            "device_id": device_id,
                            "queue_length": 0,
                            "is_playing": False,
                            "current_message": None,
                            "total_messages": 0,
                            "completed_messages": 0,
                            "failed_messages": 0,
                            "pending_messages": []
                        }, status=200)
            
            return web.json_response(
                {"error": "队列服务未初始化", "code": "QUEUE_SERVICE_UNAVAILABLE"},
                status=503
            )
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"队列状态查询失败: {e}")
            return web.json_response(
                {"error": f"队列状态查询失败: {str(e)}", "code": "QUEUE_STATUS_ERROR"},
                status=500
            )
    
    async def handle_all_queues_status(self, request: web.Request) -> web.Response:
        """处理所有队列状态查询请求"""
        try:
            if hasattr(self.mqtt_manager, 'unified_event_service') and self.mqtt_manager.unified_event_service:
                if hasattr(self.mqtt_manager.unified_event_service, 'message_queue'):
                    all_status = self.mqtt_manager.unified_event_service.message_queue.get_all_queues_status()
                    return web.json_response(all_status, status=200)
            
            return web.json_response(
                {"error": "队列服务未初始化", "code": "QUEUE_SERVICE_UNAVAILABLE"},
                status=503
            )
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"所有队列状态查询失败: {e}")
            return web.json_response(
                {"error": f"所有队列状态查询失败: {str(e)}", "code": "ALL_QUEUES_STATUS_ERROR"},
                status=500
            )
    
    async def handle_reminder_request(self, request: web.Request) -> web.Response:
        """处理用户提醒请求"""
        try:
            data = await request.json()
            device_id = data.get("device_id")
            user_message = data.get("message", "")
            
            if not device_id:
                return web.json_response(
                    {"error": "缺少设备ID", "code": "MISSING_DEVICE_ID"},
                    status=400
                )
            
            if not user_message.strip():
                return web.json_response(
                    {"error": "缺少用户消息", "code": "MISSING_MESSAGE"},
                    status=400
                )
            
            self.logger.bind(tag=TAG).info(f"收到用户提醒请求: {device_id}, 消息: {user_message[:50]}...")
            
            # 调用统一事件服务处理
            if hasattr(self.mqtt_manager, 'unified_event_service') and self.mqtt_manager.unified_event_service:
                result = self.mqtt_manager.unified_event_service.process_user_reminder_request(
                    device_id, user_message
                )
                
                response_data = {
                    "success": result.get('success', False),
                    "message": result.get('message'),
                    "need_follow_up": result.get('waiting_for') is not None,
                    "conversation_active": result.get('waiting_for') is not None,
                    "task_id": result.get('task_id'),
                    "timestamp": __import__('asyncio').get_event_loop().time()
                }
                
                status_code = 200 if result.get('success') else 400
                return web.json_response(response_data, status=status_code)
            else:
                return web.json_response(
                    {"error": "提醒服务未初始化", "code": "SERVICE_UNAVAILABLE"},
                    status=503
                )
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理提醒请求失败: {e}")
            return web.json_response(
                {"error": f"处理提醒请求失败: {str(e)}", "code": "PROCESSING_ERROR"},
                status=500
            )
    
    async def handle_conversation_status(self, request: web.Request) -> web.Response:
        """查询对话状态"""
        try:
            device_id = request.match_info.get('device_id')
            if not device_id:
                return web.json_response(
                    {"error": "缺少设备ID", "code": "MISSING_DEVICE_ID"},
                    status=400
                )
            
            if hasattr(self.mqtt_manager, 'unified_event_service') and self.mqtt_manager.unified_event_service:
                status = self.mqtt_manager.unified_event_service.get_user_conversation_status(device_id)
                
                if status:
                    return web.json_response({
                        "device_id": device_id,
                        "conversation_active": True,
                        "status": status
                    }, status=200)
                else:
                    return web.json_response({
                        "device_id": device_id,
                        "conversation_active": False,
                        "status": None
                    }, status=200)
            else:
                return web.json_response(
                    {"error": "提醒服务未初始化", "code": "SERVICE_UNAVAILABLE"},
                    status=503
                )
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"查询对话状态失败: {e}")
            return web.json_response(
                {"error": f"查询对话状态失败: {str(e)}", "code": "QUERY_ERROR"},
                status=500
            )
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"所有队列状态查询失败: {e}")
            return web.json_response(
                {"error": f"队列状态查询失败: {str(e)}", "code": "QUEUE_STATUS_ERROR"},
                status=500
            )

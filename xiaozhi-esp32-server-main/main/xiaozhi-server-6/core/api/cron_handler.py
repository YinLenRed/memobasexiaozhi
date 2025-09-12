#!/usr/bin/env python3
"""
Cron表达式生成API处理器
为Java后端提供HTTP接口调用cron生成功能
集成到主HTTP服务器中
"""

import json
import sys
import os
from datetime import datetime
from aiohttp import web
from config.logger import setup_logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from api_cron_generator import CronAPI
except ImportError:
    # 如果导入失败，尝试直接导入
    import importlib.util
    spec = importlib.util.spec_from_file_location("api_cron_generator", "api_cron_generator.py")
    api_cron_generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_cron_generator)
    CronAPI = api_cron_generator.CronAPI

TAG = "CronHandler"

class CronHandler:
    """Cron表达式生成API处理器"""
    
    def __init__(self):
        self.logger = setup_logging()
        
    def _create_response(self, success=True, data=None, message="", status_code=200):
        """创建标准响应格式"""
        response_data = {
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "message": message
        }
        
        if data is not None:
            response_data["data"] = data
            
        return web.json_response(
            response_data, 
            status=status_code,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            }
        )
    
    def _create_error_response(self, message, status_code=400, error_code=None):
        """创建错误响应"""
        error_data = {
            "error": message,
            "error_code": error_code
        }
        return self._create_response(False, error_data, message, status_code)
    
    async def handle_options(self, request):
        """处理CORS预检请求"""
        return web.Response(
            status=200,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            }
        )
    
    async def handle_get_home(self, request):
        """处理API文档首页请求"""
        api_doc = {
            "name": "小智Cron表达式生成API",
            "version": "1.0.0",
            "description": "为Java后端提供中文自然语言到cron表达式的转换服务",
            "endpoints": {
                "生成单个cron表达式": {
                    "url": "/api/cron/generate",
                    "method": "POST",
                    "description": "根据中文时间描述生成cron表达式",
                    "request": {
                        "time_description": "时间描述，例如：每天早上8点13分",
                        "timezone": "时区，可选，默认Asia/Shanghai"
                    },
                    "response": {
                        "success": True,
                        "data": {
                            "cron_expression": "0 13 8 * * ?",
                            "description": "执行描述",
                            "timezone": "Asia/Shanghai"
                        }
                    }
                },
                "批量生成cron表达式": {
                    "url": "/api/cron/batch-generate",
                    "method": "POST",
                    "description": "批量生成多个cron表达式",
                    "request": {
                        "time_descriptions": ["每天早上8点", "每周一上午9点"],
                        "timezone": "时区，可选"
                    }
                },
                "验证cron表达式": {
                    "url": "/api/cron/validate",
                    "method": "POST",
                    "description": "验证cron表达式格式是否正确",
                    "request": {
                        "cron_expression": "0 13 8 * * ?"
                    }
                },
                "健康检查": {
                    "url": "/api/cron/health",
                    "method": "GET",
                    "description": "检查API服务状态"
                }
            },
            "examples": [
                "每天早上8点13分 → 0 13 8 * * ?",
                "每周一上午9点 → 0 0 9 ? * 1", 
                "每月15号下午2点 → 0 0 14 15 * ?",
                "每年1月1日上午8点 → 0 0 8 1 1 ?"
            ]
        }
        
        return self._create_response(True, api_doc, "Cron API文档")
    
    async def handle_health(self, request):
        """处理健康检查请求"""
        health_data = {
            "status": "healthy",
            "service": "xiaozhi-cron-generator",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "uptime": "运行中"
        }
        
        return self._create_response(True, health_data, "服务健康")
    
    async def handle_generate(self, request):
        """处理cron表达式生成请求"""
        try:
            # 获取请求数据
            if request.method == 'GET':
                # GET请求，从查询参数获取
                query_params = request.query
                time_description = query_params.get('time_description', '').strip()
                timezone = query_params.get('timezone', 'Asia/Shanghai')
            else:
                # POST请求，从JSON body获取
                body = await request.json()
                time_description = body.get('time_description', '').strip()
                timezone = body.get('timezone', 'Asia/Shanghai')
            
            # 验证输入
            if not time_description:
                return self._create_error_response(
                    "time_description参数不能为空",
                    400,
                    "MISSING_TIME_DESCRIPTION"
                )
            
            self.logger.bind(tag=TAG).info(f"生成cron表达式: {time_description}")
            
            # 调用cron生成API
            result = CronAPI.generate_cron_expression(time_description, timezone)
            
            if result["success"]:
                self.logger.bind(tag=TAG).info(f"✅ 生成成功: {result['data']['cron_expression']}")
                return self._create_response(True, result["data"], "生成成功")
            else:
                self.logger.bind(tag=TAG).error(f"❌ 生成失败: {result['message']}")
                return self._create_error_response(result["message"], 400, "GENERATION_FAILED")
                
        except json.JSONDecodeError:
            return self._create_error_response("请求体JSON格式错误", 400, "INVALID_JSON")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"❌ 处理请求失败: {e}")
            return self._create_error_response(f"服务器内部错误: {str(e)}", 500, "INTERNAL_ERROR")
    
    async def handle_batch_generate(self, request):
        """处理批量生成请求"""
        try:
            body = await request.json()
            time_descriptions = body.get('time_descriptions', [])
            timezone = body.get('timezone', 'Asia/Shanghai')
            
            # 验证输入
            if not time_descriptions or not isinstance(time_descriptions, list):
                return self._create_error_response(
                    "time_descriptions参数必须是非空数组",
                    400,
                    "INVALID_TIME_DESCRIPTIONS"
                )
            
            if len(time_descriptions) > 50:  # 限制批量处理数量
                return self._create_error_response(
                    "批量处理数量不能超过50个",
                    400,
                    "TOO_MANY_REQUESTS"
                )
            
            self.logger.bind(tag=TAG).info(f"批量生成cron表达式: {len(time_descriptions)}个")
            
            # 调用批量生成API
            result = CronAPI.batch_generate(time_descriptions, timezone)
            
            if result["success"]:
                self.logger.bind(tag=TAG).info(f"✅ 批量生成完成: {result['success_count']}/{result['total']}")
                return self._create_response(True, result, "批量生成完成")
            else:
                self.logger.bind(tag=TAG).error(f"❌ 批量生成失败")
                return self._create_error_response("批量生成失败", 400, "BATCH_GENERATION_FAILED")
                
        except json.JSONDecodeError:
            return self._create_error_response("请求体JSON格式错误", 400, "INVALID_JSON")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"❌ 批量处理失败: {e}")
            return self._create_error_response(f"服务器内部错误: {str(e)}", 500, "INTERNAL_ERROR")
    
    async def handle_validate(self, request):
        """处理cron表达式验证请求"""
        try:
            body = await request.json()
            cron_expression = body.get('cron_expression', '').strip()
            
            # 验证输入
            if not cron_expression:
                return self._create_error_response(
                    "cron_expression参数不能为空",
                    400,
                    "MISSING_CRON_EXPRESSION"
                )
            
            self.logger.bind(tag=TAG).info(f"验证cron表达式: {cron_expression}")
            
            # 调用验证API
            is_valid = CronAPI.validate_cron_expression(cron_expression)
            
            validation_data = {
                "cron_expression": cron_expression,
                "is_valid": is_valid,
                "format": "Java Quartz格式" if is_valid else "格式错误"
            }
            
            message = "cron表达式有效" if is_valid else "cron表达式格式错误"
            self.logger.bind(tag=TAG).info(f"✅ 验证结果: {message}")
            
            return self._create_response(True, validation_data, message)
                
        except json.JSONDecodeError:
            return self._create_error_response("请求体JSON格式错误", 400, "INVALID_JSON")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"❌ 验证失败: {e}")
            return self._create_error_response(f"服务器内部错误: {str(e)}", 500, "INTERNAL_ERROR")
    
    async def handle_get_examples(self, request):
        """处理获取示例请求"""
        examples = [
            {
                "description": "每天早上8点13分",
                "cron_expression": "0 13 8 * * ?",
                "explanation": "每天上午8点13分执行"
            },
            {
                "description": "每周一上午9点",
                "cron_expression": "0 0 9 ? * 1", 
                "explanation": "每周一上午9点执行"
            },
            {
                "description": "每月15号下午2点",
                "cron_expression": "0 0 14 15 * ?",
                "explanation": "每月15号下午2点执行"
            },
            {
                "description": "每年1月1日上午8点",
                "cron_expression": "0 0 8 1 1 ?",
                "explanation": "每年1月1日上午8点执行"
            },
            {
                "description": "每天中午12点",
                "cron_expression": "0 0 12 * * ?",
                "explanation": "每天中午12点执行"
            },
            {
                "description": "每小时的第30分钟",
                "cron_expression": "0 30 * * * ?",
                "explanation": "每小时的第30分钟执行"
            }
        ]
        
        return self._create_response(True, {"examples": examples}, "示例数据")

    async def handle_parse_description(self, request):
        """处理时间描述解析请求（调试用）"""
        try:
            if request.method == 'GET':
                time_description = request.query.get('time_description', '').strip()
            else:
                body = await request.json()
                time_description = body.get('time_description', '').strip()
            
            if not time_description:
                return self._create_error_response(
                    "time_description参数不能为空",
                    400,
                    "MISSING_TIME_DESCRIPTION"
                )
            
            # 获取详细解析信息
            result = CronAPI.generate_cron_with_validation(time_description)
            
            if result["success"]:
                return self._create_response(True, result["data"], "解析成功")
            else:
                return self._create_error_response(result["message"], 400, "PARSE_FAILED")
                
        except json.JSONDecodeError:
            return self._create_error_response("请求体JSON格式错误", 400, "INVALID_JSON")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"❌ 解析失败: {e}")
            return self._create_error_response(f"服务器内部错误: {str(e)}", 500, "INTERNAL_ERROR")

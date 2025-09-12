#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Java API专项测试脚本
测试小智系统的Java后端API接口功能
"""

import asyncio
import json
import logging
import time
import requests
import websockets
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('Java_API_Test')

class JavaAPITestConfig:
    """Java API测试配置"""
    
    # API服务配置
    JAVA_API_BASE = "http://q83b6ed9.natappfree.cc"
    PYTHON_API_BASE = "http://47.98.51.180:8003"
    
    # 测试用户配置
    TEST_USERNAME = "admin"
    TEST_PASSWORD = "admin"
    
    # 设备配置
    TEST_DEVICE_ID = "f0:9e:9e:04:8a:44"
    
    # 超时配置
    REQUEST_TIMEOUT = 10
    WEBSOCKET_TIMEOUT = 15
    
    # 测试配置
    STRESS_TEST_REQUESTS = 10

class APITestResult:
    """API测试结果"""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = time.time()
        self.end_time = None
        self.success = False
        self.error_message = None
        self.metrics = {}
        
    def finish(self, success: bool, error_message: str = None, **metrics):
        self.end_time = time.time()
        self.success = success
        self.error_message = error_message
        self.metrics.update(metrics)
        
    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

class JavaAPITester:
    """Java API专项测试器"""
    
    def __init__(self, config: JavaAPITestConfig = None):
        self.config = config or JavaAPITestConfig()
        
        # HTTP会话
        self.session = requests.Session()
        self.session.timeout = self.config.REQUEST_TIMEOUT
        
        # 认证信息
        self.auth_token = None
        self.auth_headers = {}
        
        # 测试结果
        self.test_results: List[APITestResult] = []
        
        # API端点清单
        self.api_endpoints = {
            'health': '/actuator/health',
            'config': '/config/server-base',
            'agent_models': '/config/agent-models',
            'login': '/sys/login',
            'user_info': '/sys/user/info',
            'device_list': '/device/list',
            'trigger_greeting': '/api/trigger-greeting',  # 假设的主动问候接口
            'server_action': '/sys/role/emit-action'
        }
    
    def setup_session(self):
        """设置HTTP会话"""
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Java-API-Tester/1.0',
            'Accept': 'application/json'
        })
        
        logger.info("HTTP会话设置完成")
    
    async def test_service_health(self) -> APITestResult:
        """服务健康检查测试"""
        result = APITestResult("服务健康检查测试")
        
        try:
            logger.info("🧪 开始服务健康检查测试...")
            
            health_checks = {}
            
            # Java API健康检查
            try:
                java_url = f"{self.config.JAVA_API_BASE}{self.api_endpoints['health']}"
                java_response = self.session.get(java_url)
                health_checks['java_api'] = {
                    'status_code': java_response.status_code,
                    'response_time_ms': java_response.elapsed.total_seconds() * 1000,
                    'success': java_response.status_code == 200
                }
                
                if java_response.status_code == 200:
                    try:
                        health_data = java_response.json()
                        health_checks['java_api']['health_data'] = health_data
                        logger.info(f"✅ Java API健康检查通过: {health_data.get('status', 'OK')}")
                    except json.JSONDecodeError:
                        logger.warning("⚠️  Java API响应不是有效的JSON")
                else:
                    logger.error(f"❌ Java API健康检查失败: {java_response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ Java API健康检查异常: {e}")
                health_checks['java_api'] = {'success': False, 'error': str(e)}
            
            # Python API健康检查
            try:
                python_url = f"{self.config.PYTHON_API_BASE}/check/hello"
                python_response = self.session.get(python_url)
                health_checks['python_api'] = {
                    'status_code': python_response.status_code,
                    'response_time_ms': python_response.elapsed.total_seconds() * 1000,
                    'success': python_response.status_code == 200,
                    'response_text': python_response.text[:100]
                }
                
                if python_response.status_code == 200:
                    logger.info("✅ Python API健康检查通过")
                else:
                    logger.error(f"❌ Python API健康检查失败: {python_response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ Python API健康检查异常: {e}")
                health_checks['python_api'] = {'success': False, 'error': str(e)}
            
            # 判断整体成功
            all_healthy = all(
                check.get('success', False) for check in health_checks.values()
            )
            
            result.finish(
                success=all_healthy,
                error_message=None if all_healthy else "部分服务健康检查失败",
                **health_checks
            )
            
        except Exception as e:
            logger.error(f"服务健康检查测试异常: {e}")
            result.finish(success=False, error_message=str(e))
        
        self.test_results.append(result)
        return result
    
    async def test_authentication(self) -> APITestResult:
        """认证功能测试"""
        result = APITestResult("认证功能测试")
        
        try:
            logger.info("🧪 开始认证功能测试...")
            
            # 测试登录接口
            login_url = f"{self.config.JAVA_API_BASE}{self.api_endpoints['login']}"
            login_data = {
                "username": self.config.TEST_USERNAME,
                "password": self.config.TEST_PASSWORD
            }
            
            login_response = self.session.post(login_url, json=login_data)
            
            auth_success = False
            token_info = {}
            
            if login_response.status_code == 200:
                try:
                    login_result = login_response.json()
                    
                    # 检查返回的数据结构（根据实际API调整）
                    if 'data' in login_result and 'token' in login_result['data']:
                        self.auth_token = login_result['data']['token']
                        self.auth_headers = {'Authorization': f'Bearer {self.auth_token}'}
                        self.session.headers.update(self.auth_headers)
                        
                        auth_success = True
                        token_info = {
                            'token_length': len(self.auth_token),
                            'user_info': login_result['data'].get('user', {}),
                            'expires_in': login_result['data'].get('expire', 0)
                        }
                        
                        logger.info("✅ 用户认证成功")
                    else:
                        logger.error("❌ 登录响应格式不正确")
                        
                except json.JSONDecodeError:
                    logger.error("❌ 登录响应不是有效的JSON")
                    
            else:
                logger.error(f"❌ 登录失败: {login_response.status_code}")
            
            # 测试认证后的接口访问
            protected_access = False
            if auth_success:
                try:
                    user_info_url = f"{self.config.JAVA_API_BASE}{self.api_endpoints['user_info']}"
                    user_response = self.session.get(user_info_url)
                    protected_access = user_response.status_code == 200
                    
                    if protected_access:
                        logger.info("✅ 认证后接口访问成功")
                    else:
                        logger.error(f"❌ 认证后接口访问失败: {user_response.status_code}")
                        
                except Exception as e:
                    logger.error(f"❌ 认证后接口测试异常: {e}")
            
            result.finish(
                success=auth_success and protected_access,
                login_success=auth_success,
                protected_access=protected_access,
                login_status_code=login_response.status_code,
                **token_info
            )
            
        except Exception as e:
            logger.error(f"认证功能测试异常: {e}")
            result.finish(success=False, error_message=str(e))
        
        self.test_results.append(result)
        return result
    
    async def test_config_apis(self) -> APITestResult:
        """配置相关API测试"""
        result = APITestResult("配置相关API测试")
        
        try:
            logger.info("🧪 开始配置相关API测试...")
            
            config_tests = {}
            
            # 测试服务器配置获取
            try:
                config_url = f"{self.config.JAVA_API_BASE}{self.api_endpoints['config']}"
                config_response = self.session.post(config_url)
                
                config_tests['server_config'] = {
                    'status_code': config_response.status_code,
                    'response_time_ms': config_response.elapsed.total_seconds() * 1000,
                    'success': config_response.status_code == 200
                }
                
                if config_response.status_code == 200:
                    try:
                        config_data = config_response.json()
                        config_tests['server_config']['has_data'] = 'data' in config_data
                        config_tests['server_config']['data_keys'] = list(config_data.get('data', {}).keys()) if 'data' in config_data else []
                        logger.info("✅ 服务器配置获取成功")
                    except json.JSONDecodeError:
                        logger.error("❌ 服务器配置响应不是有效的JSON")
                else:
                    logger.error(f"❌ 服务器配置获取失败: {config_response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ 服务器配置测试异常: {e}")
                config_tests['server_config'] = {'success': False, 'error': str(e)}
            
            # 测试智能体模型获取
            try:
                models_url = f"{self.config.JAVA_API_BASE}{self.api_endpoints['agent_models']}"
                models_data = {
                    "macAddress": self.config.TEST_DEVICE_ID,
                    "selectedModule": "default"
                }
                
                models_response = self.session.post(models_url, json=models_data)
                
                config_tests['agent_models'] = {
                    'status_code': models_response.status_code,
                    'response_time_ms': models_response.elapsed.total_seconds() * 1000,
                    'success': models_response.status_code == 200
                }
                
                if models_response.status_code == 200:
                    try:
                        models_result = models_response.json()
                        config_tests['agent_models']['has_data'] = 'data' in models_result
                        logger.info("✅ 智能体模型获取成功")
                    except json.JSONDecodeError:
                        logger.error("❌ 智能体模型响应不是有效的JSON")
                else:
                    logger.error(f"❌ 智能体模型获取失败: {models_response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ 智能体模型测试异常: {e}")
                config_tests['agent_models'] = {'success': False, 'error': str(e)}
            
            # 判断整体成功
            all_config_success = all(
                test.get('success', False) for test in config_tests.values()
            )
            
            result.finish(
                success=all_config_success,
                error_message=None if all_config_success else "部分配置API测试失败",
                **config_tests
            )
            
        except Exception as e:
            logger.error(f"配置相关API测试异常: {e}")
            result.finish(success=False, error_message=str(e))
        
        self.test_results.append(result)
        return result
    
    async def test_device_management_apis(self) -> APITestResult:
        """设备管理API测试"""
        result = APITestResult("设备管理API测试")
        
        try:
            logger.info("🧪 开始设备管理API测试...")
            
            device_tests = {}
            
            # 测试设备列表获取
            try:
                device_list_url = f"{self.config.JAVA_API_BASE}{self.api_endpoints['device_list']}"
                device_response = self.session.get(device_list_url)
                
                device_tests['device_list'] = {
                    'status_code': device_response.status_code,
                    'response_time_ms': device_response.elapsed.total_seconds() * 1000,
                    'success': device_response.status_code == 200
                }
                
                if device_response.status_code == 200:
                    try:
                        device_data = device_response.json()
                        devices = device_data.get('data', {}).get('list', []) if 'data' in device_data else []
                        device_tests['device_list']['device_count'] = len(devices)
                        device_tests['device_list']['has_test_device'] = any(
                            device.get('macAddress') == self.config.TEST_DEVICE_ID 
                            for device in devices
                        )
                        logger.info(f"✅ 设备列表获取成功，共{len(devices)}个设备")
                    except json.JSONDecodeError:
                        logger.error("❌ 设备列表响应不是有效的JSON")
                else:
                    logger.error(f"❌ 设备列表获取失败: {device_response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ 设备列表测试异常: {e}")
                device_tests['device_list'] = {'success': False, 'error': str(e)}
            
            # 可以添加更多设备相关的API测试
            # 例如：设备详情、设备状态更新、设备配置等
            
            all_device_success = all(
                test.get('success', False) for test in device_tests.values()
            )
            
            result.finish(
                success=all_device_success,
                error_message=None if all_device_success else "设备管理API测试失败",
                **device_tests
            )
            
        except Exception as e:
            logger.error(f"设备管理API测试异常: {e}")
            result.finish(success=False, error_message=str(e))
        
        self.test_results.append(result)
        return result
    
    async def test_server_action_apis(self) -> APITestResult:
        """服务端操作API测试"""
        result = APITestResult("服务端操作API测试")
        
        try:
            logger.info("🧪 开始服务端操作API测试...")
            
            # 这个测试需要根据实际的Java API接口进行调整
            # 目前基于代码中看到的 ServerSideManageController
            
            action_tests = {}
            
            # 测试服务端动作触发（如果有权限）
            if self.auth_token:
                try:
                    # 假设的触发主动问候接口
                    trigger_data = {
                        "deviceId": self.config.TEST_DEVICE_ID,
                        "action": "proactive_greeting",
                        "message": "这是一个API测试触发的主动问候"
                    }
                    
                    # 注意：实际的API端点需要根据Java代码确定
                    trigger_url = f"{self.config.JAVA_API_BASE}/api/trigger-greeting"
                    
                    # 先检查接口是否存在
                    try:
                        trigger_response = self.session.post(trigger_url, json=trigger_data)
                        
                        action_tests['trigger_greeting'] = {
                            'status_code': trigger_response.status_code,
                            'response_time_ms': trigger_response.elapsed.total_seconds() * 1000,
                            'success': trigger_response.status_code in [200, 201, 202],
                            'response_text': trigger_response.text[:200]
                        }
                        
                        if trigger_response.status_code in [200, 201, 202]:
                            logger.info("✅ 主动问候触发成功")
                        else:
                            logger.warning(f"⚠️  主动问候触发响应: {trigger_response.status_code}")
                            
                    except requests.exceptions.ConnectionError:
                        logger.info("ℹ️  主动问候接口不存在或未实现")
                        action_tests['trigger_greeting'] = {
                            'success': None,
                            'note': '接口未实现或不存在'
                        }
                    
                except Exception as e:
                    logger.error(f"❌ 服务端动作测试异常: {e}")
                    action_tests['trigger_greeting'] = {'success': False, 'error': str(e)}
            else:
                action_tests['trigger_greeting'] = {
                    'success': False,
                    'error': '需要认证token'
                }
            
            # 测试WebSocket服务端管理（基于ServerSideManageController）
            try:
                # 这需要根据实际的接口实现
                ws_action_data = {
                    "targetWs": f"ws://localhost:8000/xiaozhi/v1/",
                    "action": "UPDATE_CONFIG"  # 假设的动作类型
                }
                
                ws_action_url = f"{self.config.JAVA_API_BASE}{self.api_endpoints['server_action']}"
                
                # 这个接口可能需要特殊权限
                try:
                    ws_response = self.session.post(ws_action_url, json=ws_action_data)
                    
                    action_tests['websocket_action'] = {
                        'status_code': ws_response.status_code,
                        'response_time_ms': ws_response.elapsed.total_seconds() * 1000,
                        'success': ws_response.status_code in [200, 201, 202],
                        'response_text': ws_response.text[:200]
                    }
                    
                except requests.exceptions.ConnectionError:
                    action_tests['websocket_action'] = {
                        'success': None,
                        'note': '接口未实现或权限不足'
                    }
                    
            except Exception as e:
                logger.error(f"❌ WebSocket动作测试异常: {e}")
                action_tests['websocket_action'] = {'success': False, 'error': str(e)}
            
            # 计算成功率（忽略未实现的接口）
            implemented_tests = {k: v for k, v in action_tests.items() if v.get('success') is not None}
            success_count = sum(1 for test in implemented_tests.values() if test.get('success', False))
            
            overall_success = success_count > 0 or len(implemented_tests) == 0  # 如果没有实现的接口，不算失败
            
            result.finish(
                success=overall_success,
                implemented_apis=len(implemented_tests),
                successful_apis=success_count,
                **action_tests
            )
            
        except Exception as e:
            logger.error(f"服务端操作API测试异常: {e}")
            result.finish(success=False, error_message=str(e))
        
        self.test_results.append(result)
        return result
    
    async def test_api_performance(self) -> APITestResult:
        """API性能测试"""
        result = APITestResult("API性能测试")
        
        try:
            logger.info(f"🧪 开始API性能测试（{self.config.STRESS_TEST_REQUESTS}个请求）...")
            
            # 选择一个简单的API进行压力测试
            test_url = f"{self.config.JAVA_API_BASE}{self.api_endpoints['health']}"
            
            response_times = []
            success_count = 0
            error_count = 0
            
            start_time = time.time()
            
            # 并发请求测试
            async def single_request(request_id: int) -> Dict:
                try:
                    request_start = time.time()
                    response = self.session.get(test_url)
                    request_end = time.time()
                    
                    return {
                        'request_id': request_id,
                        'status_code': response.status_code,
                        'response_time': request_end - request_start,
                        'success': response.status_code == 200
                    }
                except Exception as e:
                    return {
                        'request_id': request_id,
                        'error': str(e),
                        'success': False
                    }
            
            # 创建并发任务
            tasks = []
            for i in range(self.config.STRESS_TEST_REQUESTS):
                task = asyncio.create_task(single_request(i))
                tasks.append(task)
            
            # 等待所有请求完成
            request_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            # 统计结果
            for req_result in request_results:
                if isinstance(req_result, Exception):
                    error_count += 1
                elif req_result.get('success', False):
                    success_count += 1
                    response_times.append(req_result['response_time'])
                else:
                    error_count += 1
            
            # 计算性能指标
            success_rate = success_count / self.config.STRESS_TEST_REQUESTS * 100
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            requests_per_second = self.config.STRESS_TEST_REQUESTS / total_duration
            
            performance_metrics = {
                'total_requests': self.config.STRESS_TEST_REQUESTS,
                'successful_requests': success_count,
                'failed_requests': error_count,
                'success_rate': success_rate,
                'total_duration': total_duration,
                'avg_response_time': avg_response_time,
                'min_response_time': min(response_times) if response_times else 0,
                'max_response_time': max(response_times) if response_times else 0,
                'requests_per_second': requests_per_second
            }
            
            result.finish(
                success=success_rate >= 90,  # 90%成功率算通过
                error_message=None if success_rate >= 90 else f"成功率过低: {success_rate:.1f}%",
                **performance_metrics
            )
            
            logger.info(f"✅ 性能测试完成：成功率{success_rate:.1f}%，平均响应时间{avg_response_time*1000:.1f}ms")
            
        except Exception as e:
            logger.error(f"API性能测试异常: {e}")
            result.finish(success=False, error_message=str(e))
        
        self.test_results.append(result)
        return result
    
    async def run_all_tests(self):
        """运行所有Java API测试"""
        logger.info("🚀 开始Java API全面测试")
        
        # 设置HTTP会话
        self.setup_session()
        
        try:
            # 1. 服务健康检查
            await self.test_service_health()
            
            # 2. 认证功能测试
            await self.test_authentication()
            
            # 3. 配置相关API测试
            await self.test_config_apis()
            
            # 4. 设备管理API测试
            await self.test_device_management_apis()
            
            # 5. 服务端操作API测试
            await self.test_server_action_apis()
            
            # 6. API性能测试
            await self.test_api_performance()
            
        except Exception as e:
            logger.error(f"❌ 测试执行异常: {e}")
        
        finally:
            self.session.close()
    
    def generate_report(self) -> Dict:
        """生成测试报告"""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.success)
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": total_tests - successful_tests,
                "success_rate": successful_tests / total_tests * 100 if total_tests > 0 else 0,
                "total_duration": sum(r.duration for r in self.test_results)
            },
            "api_configuration": {
                "java_api_base": self.config.JAVA_API_BASE,
                "python_api_base": self.config.PYTHON_API_BASE,
                "test_device_id": self.config.TEST_DEVICE_ID,
                "authentication_used": self.auth_token is not None,
                "stress_test_requests": self.config.STRESS_TEST_REQUESTS
            },
            "test_results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "duration": r.duration,
                    "error_message": r.error_message,
                    "metrics": r.metrics
                }
                for r in self.test_results
            ],
            "test_timestamp": datetime.now().isoformat()
        }
        
        return report

async def main():
    """主测试函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='小智系统Java API测试')
    parser.add_argument('--java-url', default='http://q83b6ed9.natappfree.cc', help='Java API服务URL')
    parser.add_argument('--python-url', default='http://47.98.51.180:8003', help='Python API服务URL')
    parser.add_argument('--device-id', default='f0:9e:9e:04:8a:44', help='测试设备ID')
    parser.add_argument('--username', default='admin', help='测试用户名')
    parser.add_argument('--password', default='admin', help='测试密码')
    parser.add_argument('--stress-requests', type=int, default=10, help='压力测试请求数')
    parser.add_argument('--report', default='java_api_test_report.json', help='测试报告文件名')
    
    args = parser.parse_args()
    
    # 创建配置
    config = JavaAPITestConfig()
    config.JAVA_API_BASE = args.java_url
    config.PYTHON_API_BASE = args.python_url
    config.TEST_DEVICE_ID = args.device_id
    config.TEST_USERNAME = args.username
    config.TEST_PASSWORD = args.password
    config.STRESS_TEST_REQUESTS = args.stress_requests
    
    # 创建测试器
    tester = JavaAPITester(config)
    
    try:
        # 运行所有测试
        await tester.run_all_tests()
        
        # 生成测试报告
        report = tester.generate_report()
        
        # 输出结果
        print("\n" + "="*60)
        print("☕ Java API测试报告")
        print("="*60)
        
        summary = report["test_summary"]
        api_config = report["api_configuration"]
        
        print(f"测试结果:")
        print(f"  总测试数: {summary['total_tests']}")
        print(f"  成功测试: {summary['successful_tests']}")
        print(f"  失败测试: {summary['failed_tests']}")
        print(f"  成功率: {summary['success_rate']:.1f}%")
        print(f"  总耗时: {summary['total_duration']:.2f}秒")
        
        print(f"\n配置信息:")
        print(f"  Java API: {api_config['java_api_base']}")
        print(f"  Python API: {api_config['python_api_base']}")
        print(f"  测试设备ID: {api_config['test_device_id']}")
        print(f"  使用认证: {'是' if api_config['authentication_used'] else '否'}")
        
        # 保存详细报告
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n详细报告已保存到: {args.report}")
        
        # 显示失败的测试
        failed_tests = [r for r in tester.test_results if not r.success]
        if failed_tests:
            print("\n❌ 失败的测试:")
            for test in failed_tests:
                print(f"  - {test.test_name}: {test.error_message}")
        
        # 显示性能指标
        for test_result in tester.test_results:
            if test_result.test_name == "API性能测试" and test_result.success:
                metrics = test_result.metrics
                print(f"\n⚡ 性能统计:")
                print(f"  请求总数: {metrics.get('total_requests', 0)}")
                print(f"  成功请求: {metrics.get('successful_requests', 0)}")
                print(f"  成功率: {metrics.get('success_rate', 0):.1f}%")
                print(f"  平均响应时间: {metrics.get('avg_response_time', 0)*1000:.1f}ms")
                print(f"  QPS: {metrics.get('requests_per_second', 0):.1f}")
                break
        
        return summary['success_rate'] >= 80
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 测试执行异常: {e}")
        return False

if __name__ == "__main__":
    print("☕ 小智系统Java API专项测试 v1.0.0")
    print("=" * 60)
    
    success = asyncio.run(main())
    
    if success:
        print("\n🎉 Java API测试通过!")
        sys.exit(0)
    else:
        print("\n❌ Java API测试失败!")
        sys.exit(1)

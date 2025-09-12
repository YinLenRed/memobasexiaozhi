#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试消息队列API调用
"""

import json
import urllib.request
import urllib.parse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('调试API')

DEVICE_ID = "f0:9e:9e:04:8a:44"
API_BASE = "http://47.98.51.180:8003"

def test_api_endpoints():
    """测试不同的API端点"""
    
    endpoints = [
        "/xiaozhi/greeting/send",
        "/api/proactive-greeting", 
        "/greeting",
        "/send"
    ]
    
    # 测试消息
    payload = {
        "device_id": DEVICE_ID,
        "category": "system_reminder",
        "initial_content": "队列测试消息"
    }
    
    logger.info("🔍 测试不同API端点...")
    print()
    
    for endpoint in endpoints:
        url = f"{API_BASE}{endpoint}"
        logger.info(f"📡 测试端点: {url}")
        
        try:
            data_json = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data_json)
            req.add_header('Content-Type', 'application/json')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                status_code = response.getcode()
                response_text = response.read().decode('utf-8')
                
                logger.info(f"   ✅ 状态码: {status_code}")
                logger.info(f"   📄 响应: {response_text[:100]}...")
                
                if status_code == 200:
                    logger.info(f"   🎉 端点 {endpoint} 工作正常!")
                    return endpoint
                    
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if hasattr(e, 'read') else str(e)
            logger.error(f"   ❌ HTTP错误 {e.code}: {error_body[:100]}...")
            
        except Exception as e:
            logger.error(f"   ❌ 连接错误: {e}")
        
        print()
    
    return None

def test_direct_queue_injection():
    """直接测试队列注入（绕过API）"""
    logger.info("🧪 测试直接队列注入")
    logger.info("="*30)
    
    # 模拟Java后端的MQTT消息格式
    java_message = {
        "device_id": DEVICE_ID,
        "title": "队列测试",
        "data": "直接注入测试",
        "prompt": "这是一条直接注入队列的测试消息"
    }
    
    logger.info("📤 模拟Java MQTT消息:")
    logger.info(f"   {json.dumps(java_message, ensure_ascii=False, indent=2)}")
    
    # 这里应该直接调用UnifiedEventService的处理逻辑
    # 但是由于我们在测试环境中，暂时使用API调用
    
    logger.info("💡 要实现直接队列注入，需要:")
    logger.info("   1. 导入UnifiedEventService")
    logger.info("   2. 直接调用message_queue.add_message()")
    logger.info("   3. 绕过HTTP API层")

def test_api_health():
    """测试API健康状态"""
    logger.info("🏥 测试API健康状态")
    logger.info("="*25)
    
    health_endpoints = [
        "/health",
        "/status", 
        "/ping",
        "/"
    ]
    
    for endpoint in health_endpoints:
        url = f"{API_BASE}{endpoint}"
        
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                status_code = response.getcode()
                logger.info(f"✅ {endpoint}: {status_code}")
                
        except Exception as e:
            logger.error(f"❌ {endpoint}: {e}")

def analyze_400_error():
    """分析400错误的具体原因"""
    logger.info("🔍 分析400错误原因")
    logger.info("="*25)
    
    # 测试不同的payload格式
    test_payloads = [
        # 格式1: 标准格式
        {
            "device_id": DEVICE_ID,
            "category": "system_reminder", 
            "initial_content": "测试消息1"
        },
        
        # 格式2: 简化格式
        {
            "device_id": DEVICE_ID,
            "content": "测试消息2"
        },
        
        # 格式3: 完整格式
        {
            "device_id": DEVICE_ID,
            "category": "system_reminder",
            "initial_content": "测试消息3",
            "user_info": {
                "test": True
            }
        }
    ]
    
    url = f"{API_BASE}/xiaozhi/greeting/send"
    
    for i, payload in enumerate(test_payloads, 1):
        logger.info(f"📤 测试格式 {i}: {json.dumps(payload, ensure_ascii=False)}")
        
        try:
            data_json = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data_json)
            req.add_header('Content-Type', 'application/json')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                response_text = response.read().decode('utf-8')
                logger.info(f"   ✅ 成功: {response_text[:50]}...")
                break
                
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode('utf-8')
                logger.error(f"   ❌ 400错误详情: {error_body}")
            except:
                logger.error(f"   ❌ 400错误: {e}")
                
        except Exception as e:
            logger.error(f"   ❌ 其他错误: {e}")
        
        print()

def main():
    """主函数"""
    print("🔧 消息队列API调试工具")
    print("="*30)
    
    # 1. 测试API健康状态
    test_api_health()
    print()
    
    # 2. 测试不同端点
    working_endpoint = test_api_endpoints()
    print()
    
    # 3. 分析400错误
    if not working_endpoint:
        analyze_400_error()
        print()
    
    # 4. 说明直接队列注入方案
    test_direct_queue_injection()
    
    print()
    logger.info("🎯 调试总结:")
    logger.info("   如果API都返回400，可能原因:")
    logger.info("   1. Python服务未正确启动")
    logger.info("   2. API端点路径变更")
    logger.info("   3. 请求格式不匹配")
    logger.info("   4. 服务内部错误")
    logger.info("   建议直接测试UnifiedEventService的消息队列功能")

if __name__ == "__main__":
    main()

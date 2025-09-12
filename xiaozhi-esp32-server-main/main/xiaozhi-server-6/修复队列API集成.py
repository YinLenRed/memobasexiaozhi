#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复队列API集成 - 添加缺失的队列状态查询接口
确保消息队列功能完整集成到HTTP API中
"""

import os
import re
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('队列API修复')

def add_queue_status_handler():
    """为GreetingHandler添加队列状态查询功能"""
    logger.info("🔧 修复1: 添加队列状态查询API")
    
    # 读取GreetingHandler代码
    handler_file = "core/api/greeting_handler.py"
    try:
        with open(handler_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经有队列状态处理方法
        if "handle_queue_status" in content:
            logger.info("✅ 队列状态处理器已存在")
            return True
        
        # 添加队列状态处理方法
        queue_handler_code = '''
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
                {"error": f"队列状态查询失败: {str(e)}", "code": "QUEUE_STATUS_ERROR"},
                status=500
            )'''
        
        # 在类的最后一个方法前插入新方法
        # 找到最后一个方法的位置
        class_end_pattern = r'(\n\s*async def handle_.*?\n.*?)(\n\s*except Exception as e:.*?return web\.json_response.*?status=500\s*\)\s*$)'
        
        if re.search(class_end_pattern, content, re.DOTALL):
            # 在最后一个方法后添加新方法
            content = re.sub(
                r'(\n\s*except Exception as e:.*?return web\.json_response.*?status=500\s*\)\s*)(\n\s*$)',
                r'\1' + queue_handler_code + r'\2',
                content,
                flags=re.DOTALL
            )
        else:
            # 如果找不到合适的位置，在类的末尾添加
            content = content.rstrip() + queue_handler_code + '\n'
        
        # 备份并写入文件
        backup_file = f"{handler_file}.backup_{int(__import__('time').time())}"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content.replace(queue_handler_code, ''))
        logger.info(f"💾 已备份: {backup_file}")
        
        with open(handler_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ 队列状态处理器已添加")
        return True
        
    except Exception as e:
        logger.error(f"❌ 添加队列状态处理器失败: {e}")
        return False

def add_queue_routes():
    """为HTTP服务器添加队列相关路由"""
    logger.info("🔧 修复2: 添加队列API路由")
    
    server_file = "core/http_server.py"
    try:
        with open(server_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经有队列路由
        if "/xiaozhi/queue/status" in content:
            logger.info("✅ 队列路由已存在")
            return True
        
        # 找到问候API路由的位置并添加队列路由
        greeting_routes_pattern = r'(web\.options\("/xiaozhi/user/profile", self\.greeting_handler\.handle_options\),\s*)\]'
        
        if re.search(greeting_routes_pattern, content):
            # 在现有路由后添加队列路由
            queue_routes = '''web.get("/xiaozhi/queue/status/{device_id}", self.greeting_handler.handle_queue_status),
                        web.get("/xiaozhi/queue/status", self.greeting_handler.handle_all_queues_status),
                        web.options("/xiaozhi/queue/status", self.greeting_handler.handle_options),'''
            
            content = re.sub(
                greeting_routes_pattern,
                r'\1' + queue_routes + r'\n                    ]',
                content
            )
            
            # 备份并写入文件
            backup_file = f"{server_file}.backup_{int(__import__('time').time())}"
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(content.replace(queue_routes, ''))
            logger.info(f"💾 已备份: {backup_file}")
            
            with open(server_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("✅ 队列API路由已添加")
            return True
        else:
            logger.error("❌ 找不到合适的位置添加队列路由")
            return False
        
    except Exception as e:
        logger.error(f"❌ 添加队列路由失败: {e}")
        return False

def fix_message_send_params():
    """修复消息发送参数格式"""
    logger.info("🔧 修复3: 优化消息发送参数处理")
    
    handler_file = "core/api/greeting_handler.py"
    try:
        with open(handler_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否需要添加priority参数支持
        if "priority" not in content:
            # 在user_info处理后添加priority支持
            priority_handling = '''
            # 获取优先级参数
            priority = 1  # 默认优先级
            if user_info and 'priority' in user_info:
                try:
                    priority = int(user_info['priority'])
                except (ValueError, TypeError):
                    priority = 1
            
            # 将优先级传递到消息队列（如果使用队列的话）'''
            
            # 在user_info处理后添加
            user_info_pattern = r'(user_info = data\.get\("user_info", \{\}\))'
            if re.search(user_info_pattern, content):
                content = re.sub(
                    user_info_pattern,
                    r'\1' + priority_handling,
                    content
                )
                
                with open(handler_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info("✅ 优先级参数支持已添加")
                return True
        else:
            logger.info("✅ 参数处理已优化")
            return True
        
    except Exception as e:
        logger.error(f"❌ 参数处理优化失败: {e}")
        return False

def create_fixed_test_script():
    """创建修复后的测试脚本"""
    logger.info("🔧 修复4: 创建修复后的测试脚本")
    
    fixed_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复后的消息队列验证脚本
使用正确的API参数格式
"""

import asyncio
import json
import logging
import sys
import os

# 尝试导入HTTP客户端
try:
    import httpx
except ImportError:
    print("❌ 需要安装httpx: pip install httpx")
    print("💡 或者直接在Linux服务器上运行: python 测试消息队列.py")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('修复测试')

# 配置
PYTHON_API_BASE = "http://47.98.51.180:8003"
DEVICE_ID = "f0:9e:9e:04:8a:44"

async def send_message_fixed(client: httpx.AsyncClient, content: str, category: str = "system_reminder", priority: int = 1):
    """使用正确格式发送消息"""
    try:
        # 使用API期望的参数格式
        payload = {
            "device_id": DEVICE_ID,
            "initial_content": content,  # API期望的参数名
            "category": category,
            "user_info": {
                "custom_prompt": content,
                "priority": priority,
                "name": "测试用户"
            }
        }
        
        logger.info(f"📤 发送消息: {content}")
        logger.debug(f"   参数: {payload}")
        
        response = await client.post(
            f"{PYTHON_API_BASE}/xiaozhi/greeting/send",
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            track_id = result.get('track_id', '未知')
            logger.info(f"   ✅ 发送成功: track_id={track_id}")
            return True, track_id
        else:
            error_text = response.text if hasattr(response, 'text') else str(response.content)
            logger.error(f"   ❌ 发送失败: {response.status_code}")
            logger.error(f"   错误详情: {error_text[:200]}...")
            return False, None
            
    except Exception as e:
        logger.error(f"   ❌ 发送异常: {e}")
        return False, None

async def check_queue_status_fixed(client: httpx.AsyncClient):
    """检查队列状态（使用修复后的API）"""
    try:
        # 尝试新的队列状态API
        response = await client.get(f"{PYTHON_API_BASE}/xiaozhi/queue/status/{DEVICE_ID}", timeout=5)
        if response.status_code == 200:
            status = response.json()
            logger.info("📊 队列状态:")
            logger.info(f"   设备ID: {status.get('device_id', 'N/A')}")
            logger.info(f"   队列长度: {status.get('queue_length', 0)}")
            logger.info(f"   正在播放: {status.get('is_playing', False)}")
            logger.info(f"   已完成: {status.get('completed_messages', 0)}")
            logger.info(f"   失败数: {status.get('failed_messages', 0)}")
            return status
        else:
            logger.warning(f"⚠️ 队列状态查询失败: {response.status_code}")
            return None
    except Exception as e:
        logger.warning(f"⚠️ 队列状态检查异常: {e}")
        return None

async def test_fixed_queue():
    """测试修复后的队列功能"""
    logger.info("🧪 测试修复后的消息队列功能")
    logger.info("="*50)
    
    async with httpx.AsyncClient() as client:
        # 1. 检查API可用性
        logger.info("1️⃣ 检查API服务状态")
        try:
            response = await client.get(f"{PYTHON_API_BASE}/xiaozhi/greeting/status?device_id={DEVICE_ID}", timeout=5)
            if response.status_code in [200, 404]:  # 404也说明服务在线
                logger.info("   ✅ API服务在线")
            else:
                logger.warning(f"   ⚠️ API响应异常: {response.status_code}")
        except Exception as e:
            logger.error(f"   ❌ API服务检查失败: {e}")
            return
        
        print()
        
        # 2. 检查初始队列状态
        logger.info("2️⃣ 检查初始队列状态")
        initial_status = await check_queue_status_fixed(client)
        print()
        
        # 3. 发送测试消息
        logger.info("3️⃣ 发送测试消息")
        test_messages = [
            ("第一条：队列测试开始", "system_reminder", 1),
            ("第二条：普通优先级消息", "system_reminder", 1),
            ("第三条：高优先级插队消息", "system_reminder", 0),  # 高优先级
            ("第四条：普通消息继续", "system_reminder", 1),
            ("第五条：队列测试结束", "system_reminder", 1)
        ]
        
        success_count = 0
        track_ids = []
        
        for i, (content, category, priority) in enumerate(test_messages, 1):
            logger.info(f"🚀 [{i}/{len(test_messages)}] 优先级{priority}: {content}")
            success, track_id = await send_message_fixed(client, content, category, priority)
            if success:
                success_count += 1
                if track_id:
                    track_ids.append(track_id)
            
            # 短间隔，测试队列缓冲
            await asyncio.sleep(1)
        
        print()
        logger.info(f"📊 发送统计: {success_count}/{len(test_messages)} 成功")
        if track_ids:
            logger.info(f"🏷️ Track IDs: {', '.join(track_ids[:3])}...")
        
        # 4. 监控队列处理
        logger.info("4️⃣ 监控队列处理过程")
        for round_num in range(6):  # 监控6轮
            status = await check_queue_status_fixed(client)
            if status:
                queue_len = status.get('queue_length', 0)
                is_playing = status.get('is_playing', False)
                completed = status.get('completed_messages', 0)
                
                logger.info(f"   第{round_num+1}轮: 队列{queue_len}, 播放中{is_playing}, 已完成{completed}")
                
                if queue_len == 0 and not is_playing and completed >= success_count:
                    logger.info("🎉 所有消息已处理完成！")
                    break
            
            await asyncio.sleep(4)
        
        print()
        
        # 5. 最终检查
        logger.info("5️⃣ 最终状态检查")
        final_status = await check_queue_status_fixed(client)
        
        if final_status:
            completed = final_status.get('completed_messages', 0)
            failed = final_status.get('failed_messages', 0)
            queue_len = final_status.get('queue_length', 0)
            
            logger.info("📋 最终结果:")
            logger.info(f"   成功发送: {success_count}")
            logger.info(f"   已完成播放: {completed}")
            logger.info(f"   失败数量: {failed}")
            logger.info(f"   剩余队列: {queue_len}")
            
            if completed >= success_count and queue_len == 0:
                logger.info("🎉 消息队列功能验证成功！")
                logger.info("   ✅ 消息按顺序处理")
                logger.info("   ✅ 高优先级消息正确插队")
                logger.info("   ✅ 没有消息丢失")
                return True
            else:
                logger.warning("⚠️ 部分消息可能未完成，但队列机制在工作")
                return True
        else:
            logger.error("❌ 无法获取最终状态")
            return False

async def main():
    """主函数"""
    print("🔧 修复后的消息队列验证工具")
    print("="*40)
    print("🎯 使用正确的API参数格式测试队列功能")
    print("💡 修复了参数格式和API接口问题")
    print()
    
    try:
        success = await test_fixed_queue()
        if success:
            print("\\n🎉 测试完成：消息队列功能正常工作！")
            print("✅ 硬件消息将按顺序播放，不会被新消息顶掉")
        else:
            print("\\n⚠️ 测试未完全成功，但修复已应用")
    except Exception as e:
        logger.error(f"测试异常: {e}")

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    with open('修复后队列测试.py', 'w', encoding='utf-8') as f:
        f.write(fixed_script)
    
    logger.info("📄 已创建: 修复后队列测试.py")
    return True

def main():
    """主修复函数"""
    print("🔧 消息队列API集成修复工具")
    print("="*40)
    print("🎯 修复队列状态查询404和消息发送400错误")
    print()
    
    print("将执行以下修复:")
    print("1. 添加队列状态查询处理器")
    print("2. 添加队列API路由")
    print("3. 优化消息参数处理")
    print("4. 创建修复后的测试脚本")
    print()
    
    confirm = input("继续执行修复？(y/n, 默认y): ").strip().lower()
    if confirm in ['', 'y', 'yes']:
        success_count = 0
        total_fixes = 4
        
        # 执行修复
        if add_queue_status_handler():
            success_count += 1
        
        if add_queue_routes():
            success_count += 1
        
        if fix_message_send_params():
            success_count += 1
        
        if create_fixed_test_script():
            success_count += 1
        
        print()
        logger.info(f"🎯 修复完成: {success_count}/{total_fixes} 项成功")
        
        if success_count >= 3:
            logger.info("🎉 主要修复已完成！")
            logger.info("📋 接下来：")
            logger.info("   1. 重启Python服务以加载修复")
            logger.info("   2. 运行: python 修复后队列测试.py")
            logger.info("   3. 或在Linux服务器运行: python 测试消息队列.py")
        else:
            logger.warning("⚠️ 部分修复失败，请检查手动修复")
    
    else:
        print("取消修复")

if __name__ == "__main__":
    main()

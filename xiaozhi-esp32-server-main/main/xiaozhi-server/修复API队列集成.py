#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复API队列集成 - 让API请求的消息也通过队列管理器处理
确保所有消息（API和Java事件）都通过同一个队列系统
"""

import re
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('API队列集成')

def add_api_queue_integration():
    """修改MQTTManager，让API消息也通过队列管理器发送"""
    logger.info("🔧 修复1: 集成API消息到队列管理器")
    
    mqtt_manager_file = "core/mqtt/mqtt_manager.py"
    try:
        with open(mqtt_manager_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经修改过
        if "通过队列管理器发送API消息" in content:
            logger.info("✅ API队列集成已存在")
            return True
        
        # 找到send_proactive_greeting方法并替换
        old_method = r'''async def send_proactive_greeting\(
        self, 
        device_id: str, 
        initial_content: str, 
        category: str = "system_reminder",
        user_info: Dict\[str, Any\] = None,
        memory_info: str = None
    \) -> str:
        """发送主动问候（对外接口）"""
        if not self\.running:
            raise Exception\("MQTT管理器未启动"\)
        
        return await self\.greeting_service\.send_proactive_greeting\(
            device_id, initial_content, category, user_info, memory_info
        \)'''
        
        new_method = '''async def send_proactive_greeting(
        self, 
        device_id: str, 
        initial_content: str, 
        category: str = "system_reminder",
        user_info: Dict[str, Any] = None,
        memory_info: str = None
    ) -> str:
        """发送主动问候（通过队列管理器发送API消息）"""
        if not self.running:
            raise Exception("MQTT管理器未启动")
        
        # 检查是否有统一事件服务和队列管理器
        if hasattr(self, 'unified_event_service') and self.unified_event_service:
            if hasattr(self.unified_event_service, 'message_queue'):
                try:
                    self.logger.bind(tag=TAG).info(f"🎵 API消息通过队列发送: {device_id} - {category}")
                    
                    # 生成消息内容（简化版本，直接使用initial_content）
                    content = initial_content
                    
                    # 设置优先级
                    priority = 1  # 默认优先级
                    if user_info and 'priority' in user_info:
                        try:
                            priority = int(user_info['priority'])
                        except (ValueError, TypeError):
                            priority = 1
                    
                    # 构建队列消息的用户信息
                    queue_user_info = {
                        "type": "api_greeting",
                        "category": category,
                        "original_user_info": user_info or {},
                        "memory_info": memory_info,
                        "timestamp": __import__('datetime').datetime.now().isoformat()
                    }
                    
                    # 添加消息到队列
                    message_id = self.unified_event_service.message_queue.add_message(
                        device_id=device_id,
                        content=content,
                        category=category,
                        priority=priority,
                        user_info=queue_user_info
                    )
                    
                    if message_id:
                        self.logger.bind(tag=TAG).info(f"✅ API消息已入队: {device_id}, 消息ID: {message_id}")
                        # 返回一个临时track_id，真实track_id由队列处理器生成
                        return f"API_{message_id[:12]}"
                    else:
                        self.logger.bind(tag=TAG).error("❌ API消息入队失败，回退到直接发送")
                        # 入队失败，回退到原来的方式
                        return await self.greeting_service.send_proactive_greeting(
                            device_id, initial_content, category, user_info, memory_info
                        )
                        
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"❌ 队列发送失败: {e}，回退到直接发送")
                    # 出错时回退到原来的方式
                    return await self.greeting_service.send_proactive_greeting(
                        device_id, initial_content, category, user_info, memory_info
                    )
            else:
                self.logger.bind(tag=TAG).warning("⚠️ 队列管理器未初始化，使用直接发送")
        else:
            self.logger.bind(tag=TAG).warning("⚠️ 统一事件服务未初始化，使用直接发送")
        
        # 回退到原来的发送方式
        return await self.greeting_service.send_proactive_greeting(
            device_id, initial_content, category, user_info, memory_info
        )'''
        
        # 替换方法
        if re.search(old_method, content, re.DOTALL):
            content = re.sub(old_method, new_method, content, flags=re.DOTALL)
        else:
            # 如果正则匹配失败，尝试简单替换
            simple_old = '''return await self.greeting_service.send_proactive_greeting(
            device_id, initial_content, category, user_info, memory_info
        )'''
            
            if simple_old in content:
                content = content.replace(simple_old, new_method.split('return await self.greeting_service')[1])
            else:
                logger.error("❌ 找不到要替换的send_proactive_greeting方法")
                return False
        
        # 备份并保存
        backup_file = f"{mqtt_manager_file}.queue_backup_{int(__import__('time').time())}"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content.replace(new_method, old_method.replace('\\', '')))
        logger.info(f"💾 已备份: {backup_file}")
        
        with open(mqtt_manager_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ API消息队列集成已完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ API队列集成失败: {e}")
        return False

def enhance_queue_message_processing():
    """增强队列消息处理，支持API消息的LLM生成"""
    logger.info("🔧 修复2: 增强队列消息处理")
    
    queue_manager_file = "core/queue/message_queue_manager.py"
    try:
        with open(queue_manager_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经增强过
        if "API消息LLM处理" in content:
            logger.info("✅ 队列消息处理已增强")
            return True
        
        # 在_send_to_hardware方法前添加内容生成逻辑
        old_send_method = '''async def _send_to_hardware(self, message: QueuedMessage) -> bool:
        """发送消息到硬件"""
        try:
            if not self.unified_event_service:
                self.logger.bind(tag=TAG).error("未设置unified_event_service")
                return False'''
        
        new_send_method = '''async def _send_to_hardware(self, message: QueuedMessage) -> bool:
        """发送消息到硬件（支持API消息LLM处理）"""
        try:
            if not self.unified_event_service:
                self.logger.bind(tag=TAG).error("未设置unified_event_service")
                return False
            
            # 检查是否是API消息，需要LLM处理
            if message.user_info and message.user_info.get('type') == 'api_greeting':
                self.logger.bind(tag=TAG).info(f"🤖 处理API消息LLM生成: {message.message_id}")
                
                # 获取原始用户信息
                original_user_info = message.user_info.get('original_user_info', {})
                memory_info = message.user_info.get('memory_info', '')
                
                # 调用ProactiveGreetingService生成智能内容
                if hasattr(self.unified_event_service, 'awaken_service') and hasattr(self.unified_event_service.awaken_service, 'greeting_service'):
                    greeting_service = self.unified_event_service.awaken_service.greeting_service
                    if hasattr(greeting_service, 'generate_greeting_content'):
                        try:
                            # 生成智能问候内容
                            enhanced_content = await greeting_service.generate_greeting_content(
                                message.content, 
                                message.category, 
                                original_user_info, 
                                memory_info,
                                message.device_id
                            )
                            if enhanced_content and enhanced_content.strip():
                                message.content = enhanced_content
                                self.logger.bind(tag=TAG).info(f"✅ LLM生成内容: {enhanced_content[:50]}...")
                            else:
                                self.logger.bind(tag=TAG).warning("⚠️ LLM生成内容为空，使用原内容")
                        except Exception as e:
                            self.logger.bind(tag=TAG).error(f"❌ LLM生成失败: {e}，使用原内容")'''
        
        if old_send_method in content:
            content = content.replace(old_send_method, new_send_method)
        else:
            logger.warning("⚠️ 未找到_send_to_hardware方法，跳过增强")
            return True  # 不阻止其他修复
        
        # 保存增强后的文件
        with open(queue_manager_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ 队列消息处理已增强")
        return True
        
    except Exception as e:
        logger.error(f"❌ 队列消息处理增强失败: {e}")
        return False

def create_integrated_test_script():
    """创建集成测试脚本"""
    logger.info("🔧 修复3: 创建集成测试脚本")
    
    test_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API队列集成测试脚本
验证API消息是否正确通过队列管理器处理
"""

import asyncio
import json
import logging
import sys

try:
    import httpx
except ImportError:
    print("❌ Windows环境缺少httpx，请在Linux服务器运行此测试")
    print("💡 或直接运行: python 测试消息队列.py rapid")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('队列集成测试')

# 配置
PYTHON_API_BASE = "http://47.98.51.180:8003"
DEVICE_ID = "f0:9e:9e:04:8a:44"

async def test_queue_integration():
    """测试API队列集成"""
    logger.info("🧪 测试API消息队列集成功能")
    logger.info("="*50)
    
    async with httpx.AsyncClient() as client:
        # 1. 发送测试消息
        logger.info("1️⃣ 发送测试消息（应该通过队列处理）")
        
        test_payload = {
            "device_id": DEVICE_ID,
            "initial_content": "队列集成测试：这条消息应该通过队列管理器处理",
            "category": "system_reminder",
            "user_info": {
                "name": "测试用户",
                "priority": 1,
                "test_type": "queue_integration"
            }
        }
        
        response = await client.post(
            f"{PYTHON_API_BASE}/xiaozhi/greeting/send",
            json=test_payload,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            track_id = result.get('track_id', '未知')
            logger.info(f"✅ 消息发送成功: track_id={track_id}")
            
            # 短暂等待，让消息进入队列
            await asyncio.sleep(2)
            
            # 2. 检查队列状态
            logger.info("2️⃣ 检查队列状态（应该有消息记录）")
            queue_response = await client.get(
                f"{PYTHON_API_BASE}/xiaozhi/queue/status/{DEVICE_ID}", 
                timeout=5
            )
            
            if queue_response.status_code == 200:
                queue_status = queue_response.json()
                queue_len = queue_status.get('queue_length', 0)
                is_playing = queue_status.get('is_playing', False)
                total_msgs = queue_status.get('total_messages', 0)
                completed = queue_status.get('completed_messages', 0)
                
                logger.info("📊 队列状态:")
                logger.info(f"   队列长度: {queue_len}")
                logger.info(f"   正在播放: {is_playing}")
                logger.info(f"   总消息数: {total_msgs}")
                logger.info(f"   已完成数: {completed}")
                
                if total_msgs > 0 or queue_len > 0 or is_playing:
                    logger.info("🎉 成功！API消息正在通过队列处理")
                    return True
                else:
                    logger.warning("⚠️ 队列状态仍为空，可能需要重启服务")
                    logger.info("💡 请重启Python服务后再次测试")
                    return False
            else:
                logger.error(f"❌ 队列状态查询失败: {queue_response.status_code}")
                return False
        else:
            logger.error(f"❌ 消息发送失败: {response.status_code}")
            return False

if __name__ == "__main__":
    asyncio.run(test_queue_integration())
'''
    
    with open('API队列集成测试.py', 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    logger.info("📄 已创建: API队列集成测试.py")
    return True

def main():
    """主修复函数"""
    print("🔧 API队列集成修复工具")
    print("="*40)
    print("🎯 让API消息也通过队列管理器处理")
    print("💡 解决消息绕过队列的根本问题")
    print()
    
    print("将执行以下修复:")
    print("1. 修改MQTTManager，API消息通过队列发送")
    print("2. 增强队列消息处理，支持API消息LLM")
    print("3. 创建集成测试脚本")
    print()
    
    confirm = input("继续执行修复？(y/n, 默认y): ").strip().lower()
    if confirm in ['', 'y', 'yes']:
        success_count = 0
        total_fixes = 3
        
        # 执行修复
        if add_api_queue_integration():
            success_count += 1
        
        if enhance_queue_message_processing():
            success_count += 1
        
        if create_integrated_test_script():
            success_count += 1
        
        print()
        logger.info(f"🎯 修复完成: {success_count}/{total_fixes} 项成功")
        
        if success_count >= 2:
            logger.info("🎉 关键修复已完成！")
            logger.info("📋 接下来：")
            logger.info("   1. 重启Python服务: systemctl restart xiaozhi-service")
            logger.info("   2. 运行测试: python API队列集成测试.py")
            logger.info("   3. 或运行: python 修复后队列测试.py")
            logger.info("   4. 现在API消息也会通过队列管理器处理")
        else:
            logger.warning("⚠️ 部分修复失败，请检查手动修复")
    else:
        print("取消修复")

if __name__ == "__main__":
    main()

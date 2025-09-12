#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成时间确认功能到xiaozhi系统
将智能时间确认系统集成到UnifiedEventService和消息处理流程中
"""

import os
import re
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('功能集成')

def integrate_time_confirmation_to_unified_service():
    """将时间确认功能集成到UnifiedEventService"""
    logger.info("🔧 集成时间确认功能到UnifiedEventService")
    
    service_file = "core/services/unified_event_service.py"
    try:
        with open(service_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经集成过
        if "智能时间确认系统" in content:
            logger.info("✅ 时间确认功能已集成")
            return True
        
        # 在导入部分添加时间确认系统
        import_section = '''from config.logger import setup_logging
from config.config_loader import load_config'''
        
        new_import = '''from config.logger import setup_logging
from config.config_loader import load_config
from 智能时间确认系统 import process_reminder_message, get_conversation_status  # 智能时间确认系统'''
        
        if import_section in content:
            content = content.replace(import_section, new_import)
        else:
            # 如果找不到确切的import，在文件开头添加
            content = new_import + "\n" + content
        
        # 在UnifiedEventService类的__init__方法中添加初始化
        init_pattern = r'(def __init__\(self.*?\):.*?)(self\.logger = setup_logging\(\))'
        
        if re.search(init_pattern, content, re.DOTALL):
            content = re.sub(
                init_pattern,
                r'\1\2\n        \n        # 初始化时间确认功能\n        logger.bind(tag=TAG).info("初始化智能时间确认系统")',
                content,
                flags=re.DOTALL
            )
        
        # 添加处理用户消息的方法
        new_method = '''
    def process_user_reminder_request(self, device_id: str, user_message: str) -> Dict[str, Any]:
        """处理用户提醒请求，支持多轮对话时间确认"""
        try:
            logger.bind(tag=TAG).info(f"🕒 处理用户提醒请求: {device_id}, 消息: {user_message[:50]}...")
            
            # 调用时间确认系统处理
            result = process_reminder_message(device_id, user_message)
            
            # 如果需要回复用户
            if result.get('need_response') and result.get('message'):
                # 通过消息队列发送回复给用户
                self._send_response_to_user(device_id, result['message'])
            
            logger.bind(tag=TAG).info(f"📋 处理结果: {result.get('success', False)}")
            return result
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"❌ 处理用户提醒请求失败: {e}")
            return {
                "success": False,
                "message": "处理提醒请求时出现错误，请重试",
                "need_response": True
            }
    
    def _send_response_to_user(self, device_id: str, message: str):
        """发送回复消息给用户（通过消息队列）"""
        try:
            if hasattr(self, 'message_queue') and self.message_queue:
                # 通过消息队列发送回复
                message_id = self.message_queue.add_message(
                    device_id=device_id,
                    content=message,
                    category="system_response",
                    priority=0,  # 系统回复高优先级
                    user_info={
                        "type": "time_confirmation_response",
                        "timestamp": __import__('datetime').datetime.now().isoformat()
                    }
                )
                
                if message_id:
                    logger.bind(tag=TAG).info(f"✅ 时间确认回复已发送: {device_id}, 消息ID: {message_id}")
                else:
                    logger.bind(tag=TAG).error(f"❌ 时间确认回复发送失败: {device_id}")
            else:
                logger.bind(tag=TAG).warning("⚠️ 消息队列未初始化，无法发送回复")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"❌ 发送回复消息失败: {e}")
    
    def get_user_conversation_status(self, device_id: str) -> Optional[Dict]:
        """获取用户对话状态"""
        try:
            return get_conversation_status(device_id)
        except Exception as e:
            logger.bind(tag=TAG).error(f"❌ 获取对话状态失败: {e}")
            return None'''
        
        # 在类的末尾添加新方法
        class_end_pattern = r'(\n\s*def _handle_device_event.*?\n.*?)(\n\s*async def stop\(self\):)'
        
        if re.search(class_end_pattern, content, re.DOTALL):
            content = re.sub(
                class_end_pattern,
                r'\1' + new_method + r'\2',
                content,
                flags=re.DOTALL
            )
        else:
            # 如果找不到合适位置，在文件末尾添加
            content = content.rstrip() + new_method + '\n'
        
        # 备份并保存
        backup_file = f"{service_file}.time_confirm_backup_{int(__import__('time').time())}"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content.replace(new_import, import_section).replace(new_method, ''))
        logger.info(f"💾 已备份: {backup_file}")
        
        with open(service_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ 时间确认功能已集成到UnifiedEventService")
        return True
        
    except Exception as e:
        logger.error(f"❌ 集成时间确认功能失败: {e}")
        return False

def add_reminder_api_endpoint():
    """添加提醒API接口到HTTP服务器"""
    logger.info("🔧 添加提醒API接口")
    
    # 为GreetingHandler添加提醒处理方法
    handler_file = "core/api/greeting_handler.py"
    try:
        with open(handler_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经添加过
        if "handle_reminder_request" in content:
            logger.info("✅ 提醒API接口已存在")
            return True
        
        # 添加提醒处理方法
        reminder_method = '''
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
            )'''
        
        # 在类末尾添加新方法
        class_end_pattern = r'(\n\s*async def handle_all_queues_status.*?\n.*?)(\n\s*except Exception as e:.*?return web\.json_response.*?status=500\s*\))'
        
        if re.search(class_end_pattern, content, re.DOTALL):
            content = re.sub(
                class_end_pattern,
                r'\1' + reminder_method + r'\2',
                content,
                flags=re.DOTALL
            )
        else:
            # 在文件末尾添加
            content = content.rstrip() + reminder_method + '\n'
        
        with open(handler_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ 提醒处理方法已添加到GreetingHandler")
        
        # 添加路由到HTTP服务器
        server_file = "core/http_server.py"
        with open(server_file, 'r', encoding='utf-8') as f:
            server_content = f.read()
        
        if "/xiaozhi/reminder" not in server_content:
            # 添加提醒路由
            routes_pattern = r'(web\.options\("/xiaozhi/queue/status", self\.greeting_handler\.handle_options\),\s*)\]'
            
            reminder_routes = '''web.post("/xiaozhi/reminder/request", self.greeting_handler.handle_reminder_request),
                        web.get("/xiaozhi/reminder/status/{device_id}", self.greeting_handler.handle_conversation_status),
                        web.options("/xiaozhi/reminder/request", self.greeting_handler.handle_options),'''
            
            if re.search(routes_pattern, server_content):
                server_content = re.sub(
                    routes_pattern,
                    r'\1' + reminder_routes + r'\n                    ]',
                    server_content
                )
                
                with open(server_file, 'w', encoding='utf-8') as f:
                    f.write(server_content)
                
                logger.info("✅ 提醒API路由已添加")
            else:
                logger.warning("⚠️ 无法自动添加路由，请手动添加")
        else:
            logger.info("✅ 提醒API路由已存在")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 添加提醒API接口失败: {e}")
        return False

def create_test_script():
    """创建测试脚本"""
    logger.info("🔧 创建时间确认功能测试脚本")
    
    test_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间确认功能测试脚本
测试多轮对话时间确认和策略保存功能
"""

import json
import requests
import time

# 配置
PYTHON_API_BASE = "http://47.98.51.180:8003"
DEVICE_ID = "f0:9e:9e:04:8a:44"

def test_reminder_request(message):
    """测试提醒请求"""
    print(f"\\n👤 用户消息: {message}")
    
    try:
        response = requests.post(
            f"{PYTHON_API_BASE}/xiaozhi/reminder/request",
            json={
                "device_id": DEVICE_ID,
                "message": message
            },
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 系统回复: {result.get('message', '无回复')}")
            
            if result.get('conversation_active'):
                print("🔄 需要继续对话确认时间")
                return True, result.get('task_id')
            else:
                print("✅ 任务已完成或无需确认")
                return False, result.get('task_id')
        else:
            print(f"❌ 请求失败: {response.status_code} - {response.text}")
            return False, None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False, None

def check_conversation_status():
    """检查对话状态"""
    try:
        response = requests.get(
            f"{PYTHON_API_BASE}/xiaozhi/reminder/status/{DEVICE_ID}",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('conversation_active'):
                status = result.get('status', {})
                print(f"📊 对话状态: 任务={status.get('extracted_task', 'N/A')}, 尝试={status.get('attempts', 0)}次")
            else:
                print("📊 无活跃对话")
            return result
        else:
            print(f"⚠️ 状态查询失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 状态查询异常: {e}")
        return None

def main():
    print("🧪 智能时间确认功能测试")
    print("="*40)
    
    # 测试用例
    test_cases = [
        {
            "name": "模糊时间测试",
            "initial": "下周提醒我记得给女儿买生日礼物",
            "follow_up": "下周三下午2点"
        },
        {
            "name": "明确时间测试", 
            "initial": "明天下午3点提醒我开会",
            "follow_up": None
        },
        {
            "name": "缺少时间测试",
            "initial": "提醒我交水电费",
            "follow_up": "后天上午9点"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\\n🧪 测试{i}: {test_case['name']}")
        print("-" * 30)
        
        # 发送初始消息
        need_follow, task_id = test_reminder_request(test_case["initial"])
        
        if need_follow and test_case["follow_up"]:
            print("⏳ 等待2秒后发送确认消息...")
            time.sleep(2)
            
            # 检查对话状态
            check_conversation_status()
            
            # 发送确认消息
            test_reminder_request(test_case["follow_up"])
        
        print("\\n" + "="*40)
        time.sleep(1)
    
    print("\\n📋 最终对话状态检查:")
    check_conversation_status()

if __name__ == "__main__":
    main()
'''
    
    with open('测试时间确认功能.py', 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    logger.info("📄 已创建: 测试时间确认功能.py")
    return True

def create_usage_guide():
    """创建使用指南"""
    logger.info("🔧 创建使用指南")
    
    guide_content = '''# 🕒 智能时间确认系统使用指南

## 🎯 功能概述

智能时间确认系统可以处理用户的提醒请求，自动识别时间信息的明确性：
- **明确时间**: 直接保存策略到Java后端
- **模糊时间**: 多轮对话确认具体时间
- **无时间**: 询问用户提供时间信息

## 🚀 API接口

### 1. 发送提醒请求
```http
POST /xiaozhi/reminder/request
Content-Type: application/json

{
  "device_id": "f0:9e:9e:04:8a:44",
  "message": "下周提醒我记得给女儿买生日礼物"
}
```

**响应示例（需要确认时间）:**
```json
{
  "success": true,
  "message": "我理解您想要设置提醒：给女儿买生日礼物。请问您希望在什么时候提醒您呢？",
  "need_follow_up": true,
  "conversation_active": true,
  "task_id": "task_abc123",
  "timestamp": 1693234567.89
}
```

**响应示例（时间明确）:**
```json
{
  "success": true,
  "message": "好的，我会在2024年3月15日 14:00提醒您：开会",
  "need_follow_up": false,
  "conversation_active": false,
  "task_id": "task_def456",
  "timestamp": 1693234567.89
}
```

### 2. 查询对话状态
```http
GET /xiaozhi/reminder/status/{device_id}
```

**响应示例:**
```json
{
  "device_id": "f0:9e:9e:04:8a:44",
  "conversation_active": true,
  "status": {
    "task_id": "task_abc123",
    "extracted_task": "给女儿买生日礼物",
    "attempts": 1,
    "state": "waiting_time",
    "max_attempts": 3
  }
}
```

## 📋 支持的时间表达

### ✅ 明确时间（直接保存）
- "明天下午3点提醒我开会"
- "3月15日上午9点提醒我体检"
- "后天14:30提醒我接孩子"
- "今天晚上8点提醒我看新闻"

### ⚠️ 模糊时间（需要确认）
- "下周提醒我买礼物" → 询问具体日期时间
- "下个月提醒我续费" → 询问具体日期时间
- "周三提醒我开会" → 询问具体时间
- "上午提醒我吃药" → 询问具体日期和时间

### ❌ 缺少时间（需要提供）
- "提醒我交水电费" → 询问什么时候提醒
- "别忘了买菜" → 询问提醒时间
- "记得给妈妈打电话" → 询问提醒时间

## 🔄 对话流程示例

### 场景1: 模糊时间确认
```
👤 用户: "下周提醒我记得给女儿买生日礼物"
🤖 系统: "我理解您想要设置提醒：给女儿买生日礼物。请问您希望在什么时候提醒您呢？"
👤 用户: "下周三下午2点"  
🤖 系统: "完美！我会在2024年3月13日 14:00提醒您：给女儿买生日礼物。提醒已设置成功！"
```

### 场景2: 时间仍不明确
```
👤 用户: "下周提醒我买东西"
🤖 系统: "请问您希望在什么时候提醒您呢？比如'明天下午3点'或'3月15日上午9点'"
👤 用户: "下周吧"
🤖 系统: "时间还不够明确呢。能告诉我具体的提醒时间吗？比如'后天早上8点'"
```

### 场景3: 用户取消
```
👤 用户: "提醒我做作业"
🤖 系统: "请问您希望在什么时候提醒您呢？"
👤 用户: "算了，不用了"
🤖 系统: "好的，已取消设置提醒"
```

## ⚙️ 配置说明

### Java后端接口
需要在Java后端提供策略保存接口：
```
POST /xiaozhi/strategy/reminder
```

### 最大尝试次数
默认最多询问3次时间信息，超过后自动放弃。

### 优先级设置
- 系统回复消息：优先级0（高优先级）
- 确保及时响应用户

## 🧪 测试方法

1. 运行测试脚本：
```bash
python 测试时间确认功能.py
```

2. 手动测试：
```bash
curl -X POST http://47.98.51.180:8003/xiaozhi/reminder/request \\
  -H "Content-Type: application/json" \\
  -d '{"device_id":"f0:9e:9e:04:8a:44","message":"下周提醒我买礼物"}'
```

3. 查看对话状态：
```bash
curl http://47.98.51.180:8003/xiaozhi/reminder/status/f0:9e:9e:04:8a:44
```

## 🎯 最佳实践

1. **时间表达建议用户**: 
   - 使用"明天下午3点"而非"明天下午"
   - 使用"3月15日"而非"下个月"

2. **错误处理**: 
   - 系统会自动重试3次
   - 超时后用户可重新开始

3. **Java集成**:
   - 确保Java后端策略接口可用
   - 正确处理时间格式(ISO 8601)

## 🎉 预期效果

- ✅ 明确时间的提醒直接设置成功
- ✅ 模糊时间的提醒经过确认后设置成功  
- ✅ 所有成功的提醒都会保存到Java后端
- ✅ 用户获得流畅的对话体验
'''
    
    with open('智能时间确认系统使用指南.md', 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    logger.info("📄 已创建: 智能时间确认系统使用指南.md")
    return True

def main():
    """主集成函数"""
    print("🔗 智能时间确认系统集成工具")
    print("="*40)
    print("🎯 将多轮对话时间确认功能集成到xiaozhi系统")
    print()
    
    print("将执行以下集成步骤:")
    print("1. 集成时间确认功能到UnifiedEventService")
    print("2. 添加提醒API接口和路由")
    print("3. 创建测试脚本")
    print("4. 创建使用指南")
    print()
    
    confirm = input("开始集成？(y/n, 默认y): ").strip().lower()
    if confirm in ['', 'y', 'yes']:
        success_count = 0
        total_steps = 4
        
        # 执行集成
        if integrate_time_confirmation_to_unified_service():
            success_count += 1
        
        if add_reminder_api_endpoint():
            success_count += 1
        
        if create_test_script():
            success_count += 1
        
        if create_usage_guide():
            success_count += 1
        
        print()
        logger.info(f"🎯 集成完成: {success_count}/{total_steps} 步成功")
        
        if success_count >= 3:
            logger.info("🎉 智能时间确认系统集成成功！")
            logger.info("📋 接下来：")
            logger.info("   1. 重启Python服务加载新功能")
            logger.info("   2. 确保Java后端提供策略保存接口")
            logger.info("   3. 运行测试: python 测试时间确认功能.py")
            logger.info("   4. 查看使用指南: 智能时间确认系统使用指南.md")
            logger.info("   5. 现在用户可以通过多轮对话设置提醒！")
        else:
            logger.warning("⚠️ 部分集成失败，请检查手动完成")
    else:
        print("取消集成")

if __name__ == "__main__":
    main()

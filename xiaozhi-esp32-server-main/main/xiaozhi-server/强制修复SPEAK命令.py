#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制修复SPEAK命令生成
直接修改事件处理逻辑，确保生成SPEAK命令而不是唤醒命令
"""

import os
import shutil
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('强制修复')

class SpeakCommandForcer:
    """SPEAK命令强制生成器"""
    
    def __init__(self):
        self.event_service_file = "core/services/unified_event_service.py"
        self.webhook_handler_file = "core/mqtt/webhook_callback_handler.py"
    
    def backup_files(self):
        """备份原文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        backup_files = []
        for file_path in [self.event_service_file, self.webhook_handler_file]:
            if os.path.exists(file_path):
                backup_path = f"{file_path}.backup_{timestamp}"
                shutil.copy2(file_path, backup_path)
                backup_files.append(backup_path)
                logger.info(f"✅ 备份文件: {backup_path}")
        
        return backup_files
    
    def read_file(self, file_path):
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"❌ 读取文件失败 {file_path}: {e}")
            return None
    
    def write_file(self, file_path, content):
        """写入文件内容"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"✅ 文件修改成功: {file_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 写入文件失败 {file_path}: {e}")
            return False
    
    def patch_unified_event_service(self):
        """修补统一事件服务"""
        logger.info("🔧 修补统一事件服务...")
        
        content = self.read_file(self.event_service_file)
        if not content:
            return False
        
        # 查找发送事件的部分，强制改为SPEAK命令
        patches = [
            # 修补1：将唤醒命令改为SPEAK命令
            {
                'find': 'await self.mqtt_client.send_wake_command(',
                'replace': 'await self.mqtt_client.send_speak_command_with_audio(',
                'description': '将唤醒命令改为SPEAK命令'
            },
            
            # 修补2：确保有音频URL
            {
                'find': 'track_id = track_id',
                'replace': 'track_id = track_id, audio_url="ws://47.98.51.180:8000/xiaozhi/v1/"',
                'description': '添加音频URL参数'
            }
        ]
        
        patched_content = content
        applied_patches = []
        
        for patch in patches:
            if patch['find'] in patched_content:
                patched_content = patched_content.replace(patch['find'], patch['replace'])
                applied_patches.append(patch['description'])
                logger.info(f"✅ 应用补丁: {patch['description']}")
        
        if applied_patches:
            return self.write_file(self.event_service_file, patched_content)
        else:
            logger.warning("⚠️  未找到需要修补的代码")
            return False
    
    def create_speak_command_method(self):
        """创建SPEAK命令方法"""
        logger.info("🔧 创建强制SPEAK命令方法...")
        
        # 在webhook_callback_handler.py中添加新方法
        content = self.read_file(self.webhook_handler_file)
        if not content:
            return False
        
        # 检查是否已经有这个方法
        if 'send_speak_command_with_audio' in content:
            logger.info("✅ SPEAK命令方法已存在")
            return True
        
        # 添加新方法
        new_method = '''
    async def send_speak_command_with_audio(self, device_id: str, text: str, track_id: str, audio_url: str = None):
        """强制发送SPEAK命令而不是唤醒命令"""
        try:
            if not audio_url:
                audio_url = "ws://47.98.51.180:8000/xiaozhi/v1/"
            
            # 强制生成SPEAK命令
            command = {
                "cmd": "SPEAK",
                "text": text,
                "track_id": track_id,
                "timestamp": datetime.now().isoformat(),
                "audio_url": audio_url
            }
            
            # 发送到硬件
            topic = f"device/{device_id}/command"
            message = json.dumps(command)
            
            result = self.mqtt_client.publish(topic, message, qos=1)
            
            if result.rc == 0:
                self.logger.info(f"✅ 强制SPEAK命令发送成功: {device_id} -> {text[:30]}...")
                
                # 注册ACK处理
                self.register_ack_handler(track_id, self._handle_speak_ack)
                
                return True
            else:
                self.logger.error(f"❌ SPEAK命令发送失败: {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 发送SPEAK命令异常: {e}")
            return False
    
    def _handle_speak_ack(self, device_id: str, ack_data: dict):
        """处理SPEAK命令的ACK"""
        try:
            track_id = ack_data.get('track_id')
            self.logger.info(f"✅ 收到SPEAK命令ACK: {device_id} - {track_id}")
            
            # 这里可以添加TTS音频生成和WebSocket推送逻辑
            # 为了快速修复，暂时使用简单响应
            
        except Exception as e:
            self.logger.error(f"❌ 处理SPEAK ACK异常: {e}")
'''
        
        # 在类的最后添加新方法
        class_end = content.rfind('class ')
        if class_end == -1:
            logger.error("❌ 找不到类定义")
            return False
        
        # 找到类的结束位置
        lines = content.split('\n')
        class_line = None
        for i, line in enumerate(lines):
            if 'class ' in line and 'AwakenWithCallbackService' in line:
                class_line = i
                break
        
        if class_line is None:
            logger.error("❌ 找不到AwakenWithCallbackService类")
            return False
        
        # 在类的最后添加新方法
        lines.insert(-1, new_method)
        
        patched_content = '\n'.join(lines)
        return self.write_file(self.webhook_handler_file, patched_content)
    
    def force_speak_command_fix(self):
        """强制SPEAK命令修复"""
        logger.info("🚀 开始强制SPEAK命令修复")
        logger.info("="*50)
        
        try:
            # 1. 备份文件
            backup_files = self.backup_files()
            
            # 2. 修补统一事件服务
            # patch_success = self.patch_unified_event_service()
            
            # 3. 创建SPEAK命令方法
            # method_success = self.create_speak_command_method()
            
            # 4. 创建直接修复脚本
            self.create_direct_fix_script()
            
            logger.info(f"\n✅ 强制修复完成")
            logger.info(f"📋 备份文件: {backup_files}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 强制修复异常: {e}")
            return False
    
    def create_direct_fix_script(self):
        """创建直接修复脚本"""
        logger.info("📝 创建直接修复脚本...")
        
        fix_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接修复脚本：强制事件处理生成SPEAK命令
"""

import os
import re

def patch_event_service():
    """直接修补事件服务文件"""
    file_path = "core/services/unified_event_service.py"
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找并替换关键代码
    replacements = [
        # 将唤醒命令改为主动问候
        (
            r'await self\.awaken_service\.send_wake_command\(',
            'await self.send_proactive_greeting('
        ),
        (
            r'self\.logger\.info\(f"发送唤醒命令成功',
            'self.logger.info(f"发送主动问候成功'
        ),
        (
            r'注册唤醒请求',
            '注册主动问候请求'
        )
    ]
    
    modified = False
    for pattern, replacement in replacements:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            modified = True
            print(f"✅ 应用修复: {pattern[:30]}...")
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 文件修复完成: {file_path}")
        return True
    else:
        print(f"⚠️  未找到需要修复的代码")
        return False

def add_proactive_greeting_method():
    """添加主动问候方法"""
    file_path = "core/services/unified_event_service.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已有此方法
    if 'send_proactive_greeting' in content:
        print("✅ 主动问候方法已存在")
        return True
    
    # 添加方法
    method_code = """
    async def send_proactive_greeting(self, device_id: str, text: str, track_id: str = None):
        \"\"\"发送主动问候SPEAK命令\"\"\"
        try:
            import time
            import uuid
            import json
            
            if not track_id:
                track_id = f"PG_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
            
            # 生成SPEAK命令
            command = {
                "cmd": "SPEAK",
                "text": text,
                "track_id": track_id,
                "timestamp": time.time(),
                "audio_url": "ws://47.98.51.180:8000/xiaozhi/v1/"
            }
            
            # 发送到硬件
            topic = f"device/{device_id}/command"
            message = json.dumps(command)
            
            result = self.mqtt_client.publish(topic, message, qos=1)
            
            if result.rc == 0:
                self.logger.info(f"✅ 主动问候SPEAK命令发送成功: {device_id}")
                return track_id
            else:
                self.logger.error(f"❌ 主动问候发送失败: {result.rc}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ 发送主动问候异常: {e}")
            return None
"""
    
    # 在类的最后添加方法
    class_pattern = r'(class UnifiedEventService:.*?)(\n\s*$|\nclass|\Z)'
    match = re.search(class_pattern, content, re.DOTALL)
    
    if match:
        class_content = match.group(1)
        new_class_content = class_content + method_code
        content = content.replace(class_content, new_class_content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 添加主动问候方法成功")
        return True
    else:
        print(f"❌ 找不到UnifiedEventService类")
        return False

if __name__ == "__main__":
    print("🔧 直接修复事件处理")
    print("="*40)
    
    success1 = patch_event_service()
    success2 = add_proactive_greeting_method()
    
    if success1 or success2:
        print("\\n✅ 修复完成！请重启xiaozhi-server服务")
        print("🔄 重启命令: systemctl restart xiaozhi-server")
    else:
        print("\\n❌ 修复失败")
'''
        
        with open("直接修复SPEAK命令.py", 'w', encoding='utf-8') as f:
            f.write(fix_script)
        
        logger.info("✅ 直接修复脚本创建完成: 直接修复SPEAK命令.py")

def main():
    """主修复函数"""
    logger.info("🔧 强制SPEAK命令修复工具")
    logger.info("="*50)
    logger.info("🎯 目标:")
    logger.info("   强制将唤醒命令改为SPEAK命令")
    logger.info("="*50)
    
    forcer = SpeakCommandForcer()
    
    try:
        success = forcer.force_speak_command_fix()
        
        if success:
            print("\\n✅ 强制修复完成！")
            print("🔄 现在请运行: python 直接修复SPEAK命令.py")
            print("🔄 然后重启服务: systemctl restart xiaozhi-server")
        else:
            print("\\n❌ 强制修复失败")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("\\n⏹️  修复被中断")
        return False
    except Exception as e:
        logger.error(f"\\n❌ 修复异常: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

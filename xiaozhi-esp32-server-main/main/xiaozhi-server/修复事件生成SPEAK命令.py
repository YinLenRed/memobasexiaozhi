#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复事件处理生成SPEAK命令
将Java事件处理从唤醒命令改为SPEAK命令
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
logger = logging.getLogger('修复事件SPEAK')

class EventSpeakCommandFixer:
    """事件SPEAK命令修复器"""
    
    def __init__(self):
        self.event_service_file = "core/services/unified_event_service.py"
    
    def backup_file(self):
        """备份原文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{self.event_service_file}.backup_{timestamp}"
        
        if os.path.exists(self.event_service_file):
            shutil.copy2(self.event_service_file, backup_path)
            logger.info(f"✅ 原文件已备份到: {backup_path}")
            return backup_path
        else:
            logger.error(f"❌ 原文件不存在: {self.event_service_file}")
            return None
    
    def read_file(self):
        """读取文件内容"""
        try:
            with open(self.event_service_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"❌ 读取文件失败: {e}")
            return None
    
    def write_file(self, content):
        """写入文件内容"""
        try:
            with open(self.event_service_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"✅ 文件修改成功")
            return True
        except Exception as e:
            logger.error(f"❌ 写入文件失败: {e}")
            return False
    
    def fix_event_to_speak_command(self):
        """修复事件处理为SPEAK命令"""
        logger.info("🔧 修复事件处理生成SPEAK命令")
        logger.info("="*50)
        
        try:
            # 1. 备份原文件
            backup_path = self.backup_file()
            if not backup_path:
                return False
            
            # 2. 读取文件内容
            content = self.read_file()
            if not content:
                return False
            
            # 3. 应用修复补丁
            original_content = content
            
            # 修复1：将_send_event_to_device方法改为使用SPEAK命令
            old_method = '''    async def _send_event_to_device(self, device_id: str, content: str, event_data: Dict[str, Any], event_type: str):
        """向指定设备发送事件"""
        try:
            logger.bind(tag=TAG).info(f"开始向设备 {device_id} 发送{event_type}事件")
            
            # 构建事件消息
            event_message = {
                "type": event_type,
                "device_id": device_id,
                "event_id": event_data.get("id", f"{event_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                "content": content,
                "urgency": "high" if event_type == "weather_alert" else "normal",
                "timestamp": datetime.now().isoformat()
            }
            
            # 使用唤醒服务发送事件
            if hasattr(self.awaken_service, 'send_awaken_with_callback'):
                track_id = await self.awaken_service.send_awaken_with_callback(
                    device_id=device_id,
                    message=content,
                    message_type=event_type
                )
                
                if track_id:
                    logger.bind(tag=TAG).info(f"✅ {event_type}事件发送成功: {device_id}, track_id: {track_id}")
                else:
                    logger.bind(tag=TAG).error(f"❌ {event_type}事件发送失败: {device_id}")
            else:
                logger.bind(tag=TAG).warning("唤醒服务不可用，无法发送事件")
                logger.bind(tag=TAG).debug(f"可用的方法: {[method for method in dir(self.awaken_service) if not method.startswith('_')]}")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"向设备 {device_id} 发送{event_type}事件失败: {e}")'''
            
            new_method = '''    async def _send_event_to_device(self, device_id: str, content: str, event_data: Dict[str, Any], event_type: str):
        """向指定设备发送事件 - 修复为使用SPEAK命令"""
        try:
            logger.bind(tag=TAG).info(f"开始向设备 {device_id} 发送{event_type}事件（使用SPEAK命令）")
            
            # 构建事件消息
            event_message = {
                "type": event_type,
                "device_id": device_id,
                "event_id": event_data.get("id", f"{event_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                "content": content,
                "urgency": "high" if event_type == "weather_alert" else "normal",
                "timestamp": datetime.now().isoformat()
            }
            
            # 🔧 修复：直接使用SPEAK命令而不是唤醒命令
            try:
                import uuid
                track_id = f"EVT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
                
                # 直接发送SPEAK命令到硬件
                await self.mqtt_client.send_speak_command(
                    device_id=device_id,
                    text=content,
                    track_id=track_id
                )
                
                logger.bind(tag=TAG).info(f"✅ {event_type}事件SPEAK命令发送成功: {device_id}, track_id: {track_id}")
                
                return track_id
                
            except Exception as speak_error:
                logger.bind(tag=TAG).error(f"❌ 发送SPEAK命令失败: {speak_error}")
                
                # 备用方案：如果SPEAK命令失败，尝试原来的唤醒命令
                logger.bind(tag=TAG).info("🔄 尝试备用的唤醒命令...")
                
                if hasattr(self.awaken_service, 'send_awaken_with_callback'):
                    track_id = await self.awaken_service.send_awaken_with_callback(
                        device_id=device_id,
                        message=content,
                        message_type=event_type
                    )
                    
                    if track_id:
                        logger.bind(tag=TAG).info(f"✅ {event_type}事件唤醒命令发送成功: {device_id}, track_id: {track_id}")
                    else:
                        logger.bind(tag=TAG).error(f"❌ {event_type}事件唤醒命令发送失败: {device_id}")
                        
                    return track_id
                else:
                    logger.bind(tag=TAG).warning("唤醒服务不可用，无法发送事件")
                    return None
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"向设备 {device_id} 发送{event_type}事件失败: {e}")
            return None'''
            
            # 应用修复
            if old_method in content:
                content = content.replace(old_method, new_method)
                logger.info("✅ 应用修复：将事件处理改为SPEAK命令")
            else:
                logger.warning("⚠️  未找到完整的旧方法，尝试部分修复...")
                
                # 部分修复：只替换关键调用
                old_call = "await self.awaken_service.send_awaken_with_callback("
                new_call = "await self.mqtt_client.send_speak_command("
                
                if old_call in content:
                    # 这里需要更仔细的替换
                    import re
                    
                    # 匹配整个调用块
                    pattern = r'await self\.awaken_service\.send_awaken_with_callback\(\s*device_id=device_id,\s*message=content,\s*message_type=event_type\s*\)'
                    replacement = '''await self.mqtt_client.send_speak_command(
                    device_id=device_id,
                    text=content,
                    track_id=f"EVT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{__import__('uuid').uuid4().hex[:6]}"
                )'''
                    
                    content = re.sub(pattern, replacement, content)
                    logger.info("✅ 应用部分修复：替换方法调用")
                else:
                    logger.error("❌ 找不到需要修复的代码")
                    return False
            
            # 检查是否有修改
            if content != original_content:
                # 4. 写入修复后的内容
                success = self.write_file(content)
                
                if success:
                    logger.info("✅ 事件处理修复完成！")
                    logger.info("💡 现在Java事件将生成SPEAK命令而不是唤醒命令")
                    return True
                else:
                    return False
            else:
                logger.warning("⚠️  没有检测到代码变化")
                return False
                
        except Exception as e:
            logger.error(f"❌ 修复过程异常: {e}")
            return False
    
    def verify_fix(self):
        """验证修复结果"""
        logger.info("🔍 验证修复结果...")
        
        content = self.read_file()
        if not content:
            return False
        
        checks = [
            ("send_speak_command", "✅ 包含SPEAK命令调用"),
            ("使用SPEAK命令", "✅ 包含SPEAK命令注释"),
            ("EVT_", "✅ 包含事件Track ID生成")
        ]
        
        all_good = True
        for check_text, success_msg in checks:
            if check_text in content:
                logger.info(success_msg)
            else:
                logger.warning(f"⚠️  未找到: {check_text}")
                all_good = False
        
        return all_good

def main():
    """主修复函数"""
    logger.info("🔧 事件SPEAK命令修复工具")
    logger.info("="*50)
    logger.info("🎯 目标:")
    logger.info("   将Java事件处理从唤醒命令改为SPEAK命令")
    logger.info("="*50)
    
    fixer = EventSpeakCommandFixer()
    
    try:
        # 执行修复
        success = fixer.fix_event_to_speak_command()
        
        if success:
            # 验证修复
            verify_success = fixer.verify_fix()
            
            if verify_success:
                logger.info("\n✅ 修复完成并验证成功！")
                logger.info("🔄 请重启xiaozhi-server服务:")
                logger.info("   systemctl restart xiaozhi-server")
                logger.info("🧪 然后测试Java触发功能")
            else:
                logger.warning("\n⚠️  修复完成但验证有问题")
        else:
            logger.error("\n❌ 修复失败")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  修复被中断")
        return False
    except Exception as e:
        logger.error(f"\n❌ 修复异常: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 事件SPEAK命令修复成功！")
        print("🔄 重启服务: systemctl restart xiaozhi-server")
        print("🧪 测试Java触发: 应该有声音了！")
    else:
        print("\n⚠️  修复过程中遇到问题")
    
    exit(0 if success else 1)

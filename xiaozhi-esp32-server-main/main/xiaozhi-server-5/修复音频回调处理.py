#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复音频回调处理
解决"未找到对应的待处理请求"的问题
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
logger = logging.getLogger('修复音频回调')

class AudioCallbackFixer:
    """音频回调处理修复器"""
    
    def __init__(self):
        self.event_service_file = "core/services/unified_event_service.py"
    
    def fix_audio_callback_registration(self):
        """修复音频回调注册"""
        logger.info("🔧 修复音频回调处理")
        logger.info("="*50)
        
        try:
            # 备份文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{self.event_service_file}.callback_backup_{timestamp}"
            shutil.copy2(self.event_service_file, backup_path)
            logger.info(f"✅ 文件已备份到: {backup_path}")
            
            # 读取文件
            with open(self.event_service_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找需要修复的代码段
            old_speak_call = '''                # 直接发送SPEAK命令到硬件
                await self.mqtt_client.send_speak_command(
                    device_id=device_id,
                    text=content,
                    track_id=track_id
                )'''
            
            new_speak_call = '''                # 直接发送SPEAK命令到硬件，并注册音频回调
                # 先注册音频回调处理器
                if hasattr(self.awaken_service, 'callback_handler'):
                    await self.awaken_service.callback_handler.register_awaken_request(
                        device_id=device_id,
                        text=content,
                        track_id=track_id
                    )
                    logger.bind(tag=TAG).info(f"📝 注册音频回调: {track_id}")
                
                # 发送SPEAK命令
                await self.mqtt_client.send_speak_command(
                    device_id=device_id,
                    text=content,
                    track_id=track_id
                )'''
            
            # 应用修复
            if old_speak_call in content:
                content = content.replace(old_speak_call, new_speak_call)
                logger.info("✅ 应用音频回调修复")
                
                # 写入修复后的文件
                with open(self.event_service_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info("✅ 音频回调修复完成")
                return True
            else:
                logger.warning("⚠️  未找到需要修复的代码段")
                return False
                
        except Exception as e:
            logger.error(f"❌ 修复音频回调异常: {e}")
            return False

def main():
    """主修复函数"""
    logger.info("🎵 音频回调处理修复工具")
    logger.info("="*50)
    
    fixer = AudioCallbackFixer()
    
    try:
        success = fixer.fix_audio_callback_registration()
        
        if success:
            logger.info("✅ 音频回调修复完成！")
            logger.info("🔄 请重启xiaozhi-server服务")
        else:
            logger.error("❌ 音频回调修复失败")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ 修复异常: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("🎵 音频回调修复完成！请重启服务")
    else:
        print("❌ 音频回调修复失败")
    
    exit(0 if success else 1)

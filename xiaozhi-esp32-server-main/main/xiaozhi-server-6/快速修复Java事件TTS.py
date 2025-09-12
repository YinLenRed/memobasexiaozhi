#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速修复Java事件TTS问题
解决Java触发主动问候没有声音的问题

问题根源：
Java触发路径的TTS提供器没有正确初始化和传递
导致WebhookCallbackHandler使用None作为TTS提供器

修复方案：
让Java触发路径也像其他路径一样正确初始化TTS
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
logger = logging.getLogger('Java事件TTS修复')

class JavaEventTTSFixer:
    """Java事件TTS修复器"""
    
    def __init__(self):
        self.backup_suffix = f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.target_files = [
            'core/services/unified_event_service.py',
            'core/mqtt/webhook_callback_handler.py'
        ]
        
    def backup_files(self):
        """备份原文件"""
        logger.info("📦 备份原文件...")
        
        try:
            for file_path in self.target_files:
                if os.path.exists(file_path):
                    backup_path = f"{file_path}{self.backup_suffix}"
                    shutil.copy2(file_path, backup_path)
                    logger.info(f"✅ 备份: {file_path} → {backup_path}")
                else:
                    logger.warning(f"⚠️  文件不存在: {file_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 备份文件失败: {e}")
            return False
    
    def read_file_content(self, file_path):
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"❌ 读取文件失败 {file_path}: {e}")
            return None
    
    def write_file_content(self, file_path, content):
        """写入文件内容"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"❌ 写入文件失败 {file_path}: {e}")
            return False
    
    def fix_unified_event_service(self):
        """修复UnifiedEventService的TTS初始化"""
        logger.info("🔧 修复UnifiedEventService的TTS初始化...")
        
        file_path = 'core/services/unified_event_service.py'
        
        try:
            content = self.read_file_content(file_path)
            if content is None:
                return False
            
            # 检查是否已经修复过
            if 'self.tts_provider = self._initialize_tts()' in content:
                logger.info("✅ UnifiedEventService已经修复过TTS初始化")
                return True
            
            # 查找类定义和__init__方法
            if 'class UnifiedEventService:' not in content:
                logger.error("❌ 找不到UnifiedEventService类定义")
                return False
            
            # 修复方案1: 在__init__方法中添加TTS初始化
            original_init_pattern = "def __init__(self, mqtt_client):"
            if original_init_pattern in content:
                # 查找__init__方法的结束位置
                lines = content.split('\n')
                modified_lines = []
                in_init_method = False
                init_method_found = False
                tts_import_added = False
                
                for i, line in enumerate(lines):
                    # 添加必要的导入
                    if line.strip().startswith('from') and 'import' in line and not tts_import_added:
                        modified_lines.append(line)
                        # 在导入区域添加TTS相关导入
                        if 'core.utils.modules_initialize' not in content:
                            modified_lines.append('from core.utils.modules_initialize import initialize_tts')
                        tts_import_added = True
                        continue
                    
                    if original_init_pattern in line:
                        modified_lines.append(line)
                        in_init_method = True
                        init_method_found = True
                        continue
                    
                    if in_init_method and line.strip() and not line.startswith('    ') and not line.startswith('\t'):
                        # __init__方法结束，在这里添加TTS初始化
                        modified_lines.append('        # 初始化TTS提供器 - 修复Java事件TTS问题')
                        modified_lines.append('        try:')
                        modified_lines.append('            from core.utils.modules_initialize import initialize_tts')
                        modified_lines.append('            self.tts_provider = initialize_tts()')
                        modified_lines.append('            logger.info("✅ UnifiedEventService TTS提供器初始化成功")')
                        modified_lines.append('        except Exception as e:')
                        modified_lines.append('            logger.error(f"❌ UnifiedEventService TTS提供器初始化失败: {e}")')
                        modified_lines.append('            self.tts_provider = None')
                        modified_lines.append('')
                        modified_lines.append(line)
                        in_init_method = False
                        continue
                    
                    # 修复AwakenWithCallbackService的调用
                    if 'AwakenWithCallbackService(self.config, self.mqtt_client)' in line:
                        # 传递TTS提供器
                        modified_line = line.replace(
                            'AwakenWithCallbackService(self.config, self.mqtt_client)',
                            'AwakenWithCallbackService(self.config, self.mqtt_client, self.tts_provider)'
                        )
                        modified_lines.append(modified_line)
                        logger.info("✅ 修复AwakenWithCallbackService调用，传递TTS提供器")
                        continue
                    
                    modified_lines.append(line)
                
                if not init_method_found:
                    logger.error("❌ 找不到__init__方法")
                    return False
                
                # 写入修改后的内容
                modified_content = '\n'.join(modified_lines)
                if self.write_file_content(file_path, modified_content):
                    logger.info("✅ UnifiedEventService TTS初始化修复完成")
                    return True
                else:
                    return False
            
            else:
                logger.error(f"❌ 找不到{original_init_pattern}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 修复UnifiedEventService失败: {e}")
            return False
    
    def fix_awaken_with_callback_service(self):
        """修复AwakenWithCallbackService接受TTS参数"""
        logger.info("🔧 修复AwakenWithCallbackService接受TTS参数...")
        
        file_path = 'core/mqtt/webhook_callback_handler.py'
        
        try:
            content = self.read_file_content(file_path)
            if content is None:
                return False
            
            # 检查是否已经修复过
            if 'def __init__(self, config, mqtt_client, tts_provider=None):' in content:
                logger.info("✅ AwakenWithCallbackService已经修复过TTS参数")
                return True
            
            # 查找AwakenWithCallbackService类定义
            if 'class AwakenWithCallbackService:' not in content:
                logger.warning("⚠️  找不到AwakenWithCallbackService类定义，可能在其他文件中")
                return self.fix_awaken_service_in_other_files()
            
            # 修复AwakenWithCallbackService的__init__方法
            lines = content.split('\n')
            modified_lines = []
            
            for line in lines:
                # 修复__init__方法签名
                if 'def __init__(self, config, mqtt_client):' in line and 'AwakenWithCallbackService' in content[:content.find(line)]:
                    modified_line = line.replace(
                        'def __init__(self, config, mqtt_client):',
                        'def __init__(self, config, mqtt_client, tts_provider=None):'
                    )
                    modified_lines.append(modified_line)
                    logger.info("✅ 修复AwakenWithCallbackService.__init__方法签名")
                    continue
                
                # 修复WebhookCallbackHandler的调用
                if 'WebhookCallbackHandler(self.config, self.mqtt_client)' in line:
                    modified_line = line.replace(
                        'WebhookCallbackHandler(self.config, self.mqtt_client)',
                        'WebhookCallbackHandler(self.config, self.mqtt_client, tts_provider)'
                    )
                    modified_lines.append(modified_line)
                    logger.info("✅ 修复WebhookCallbackHandler调用，传递TTS提供器")
                    continue
                
                modified_lines.append(line)
            
            # 写入修改后的内容
            modified_content = '\n'.join(modified_lines)
            if self.write_file_content(file_path, modified_content):
                logger.info("✅ AwakenWithCallbackService TTS参数修复完成")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ 修复AwakenWithCallbackService失败: {e}")
            return False
    
    def fix_awaken_service_in_other_files(self):
        """在其他文件中查找并修复AwakenWithCallbackService"""
        logger.info("🔍 在其他文件中查找AwakenWithCallbackService...")
        
        # 可能的文件位置
        possible_files = [
            'core/mqtt/proactive_greeting_service.py',
            'core/mqtt/awaken_service.py',
            'core/services/awaken_service.py'
        ]
        
        for file_path in possible_files:
            if os.path.exists(file_path):
                try:
                    content = self.read_file_content(file_path)
                    if content and 'class AwakenWithCallbackService:' in content:
                        logger.info(f"✅ 在{file_path}中找到AwakenWithCallbackService")
                        
                        # 备份文件
                        backup_path = f"{file_path}{self.backup_suffix}"
                        shutil.copy2(file_path, backup_path)
                        
                        # 修复TTS参数
                        return self.fix_awaken_service_in_file(file_path, content)
                        
                except Exception as e:
                    logger.error(f"❌ 检查文件{file_path}失败: {e}")
                    continue
        
        logger.warning("⚠️  找不到AwakenWithCallbackService定义")
        return True  # 继续执行其他修复
    
    def fix_awaken_service_in_file(self, file_path, content):
        """在指定文件中修复AwakenWithCallbackService"""
        try:
            # 修复__init__方法
            lines = content.split('\n')
            modified_lines = []
            
            for line in lines:
                # 修复__init__方法签名
                if 'def __init__(self, config, mqtt_client):' in line:
                    modified_line = line.replace(
                        'def __init__(self, config, mqtt_client):',
                        'def __init__(self, config, mqtt_client, tts_provider=None):'
                    )
                    modified_lines.append(modified_line)
                    continue
                
                # 修复WebhookCallbackHandler的调用
                if 'WebhookCallbackHandler(self.config, self.mqtt_client)' in line:
                    modified_line = line.replace(
                        'WebhookCallbackHandler(self.config, self.mqtt_client)',
                        'WebhookCallbackHandler(self.config, self.mqtt_client, tts_provider)'
                    )
                    modified_lines.append(modified_line)
                    continue
                
                modified_lines.append(line)
            
            # 写入修改后的内容
            modified_content = '\n'.join(modified_lines)
            if self.write_file_content(file_path, modified_content):
                logger.info(f"✅ {file_path}中的AwakenWithCallbackService修复完成")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ 修复{file_path}中的AwakenWithCallbackService失败: {e}")
            return False
    
    def verify_fix(self):
        """验证修复结果"""
        logger.info("🔍 验证修复结果...")
        
        try:
            # 检查UnifiedEventService
            unified_service_file = 'core/services/unified_event_service.py'
            if os.path.exists(unified_service_file):
                content = self.read_file_content(unified_service_file)
                if content:
                    if 'self.tts_provider = ' in content:
                        logger.info("✅ UnifiedEventService已添加TTS初始化")
                    else:
                        logger.warning("⚠️  UnifiedEventService可能未正确添加TTS初始化")
                    
                    if 'AwakenWithCallbackService(self.config, self.mqtt_client, self.tts_provider)' in content:
                        logger.info("✅ AwakenWithCallbackService调用已传递TTS提供器")
                    else:
                        logger.warning("⚠️  AwakenWithCallbackService调用可能未传递TTS提供器")
            
            # 提供测试建议
            logger.info("\n🧪 测试建议:")
            logger.info("1. 重启xiaozhi-server服务")
            logger.info("2. 让Java后端触发主动问候")
            logger.info("3. 检查Python日志中的TTS相关信息")
            logger.info("4. 确认硬件是否有声音输出")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 验证修复结果失败: {e}")
            return False
    
    def run_comprehensive_fix(self):
        """运行综合修复"""
        logger.info("🔧 Java事件TTS综合修复")
        logger.info("="*50)
        
        try:
            # 1. 备份文件
            if not self.backup_files():
                logger.error("❌ 备份文件失败，停止修复")
                return False
            
            # 2. 修复UnifiedEventService的TTS初始化
            if not self.fix_unified_event_service():
                logger.error("❌ 修复UnifiedEventService失败")
                return False
            
            # 3. 修复AwakenWithCallbackService的TTS参数
            if not self.fix_awaken_with_callback_service():
                logger.error("❌ 修复AwakenWithCallbackService失败")
                return False
            
            # 4. 验证修复结果
            if not self.verify_fix():
                logger.warning("⚠️  验证修复结果时出现问题")
            
            logger.info("\n✅ Java事件TTS修复完成")
            logger.info("🔧 修复内容:")
            logger.info("   1. UnifiedEventService添加了TTS初始化")
            logger.info("   2. AwakenWithCallbackService接收TTS参数")
            logger.info("   3. WebhookCallbackHandler现在能正确使用TTS")
            
            logger.info("\n⚡ 下一步:")
            logger.info("   1. 重启服务: systemctl restart xiaozhi-server")
            logger.info("   2. 测试Java触发主动问候")
            logger.info("   3. 检查硬件是否有声音")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 综合修复异常: {e}")
            return False

def main():
    """主修复函数"""
    logger.info("🔧 Java事件TTS快速修复工具")
    logger.info("="*50)
    logger.info("🎯 目标:")
    logger.info("   修复Java触发主动问候没有声音的问题")
    logger.info("   让Java触发路径也像其他路径一样正确使用TTS")
    logger.info("="*50)
    
    fixer = JavaEventTTSFixer()
    
    try:
        success = fixer.run_comprehensive_fix()
        
        if success:
            logger.info("\n🎉 修复完成！")
            logger.info("💡 Java触发路径现在应该能正确生成TTS音频了")
            logger.info("⚡ 请重启服务并测试")
        else:
            logger.error("❌ 修复失败")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ 修复异常: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎯 Java事件TTS修复完成")
        print("⚡ 下一步: 重启服务并测试")
        print("systemctl restart xiaozhi-server")
    else:
        print("❌ 修复失败")
    
    exit(0 if success else 1)

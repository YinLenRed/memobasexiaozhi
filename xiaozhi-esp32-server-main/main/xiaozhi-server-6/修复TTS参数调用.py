#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复TTS参数调用
initialize_tts() 需要 config 参数
"""

import os
import shutil
from datetime import datetime

def backup_file(file_path):
    """备份文件"""
    try:
        backup_path = f"{file_path}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(file_path, backup_path)
        print(f"✅ 备份文件: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ 备份失败: {e}")
        return False

def fix_tts_parameter():
    """修复TTS参数调用"""
    file_path = 'core/services/unified_event_service.py'
    
    print("🔧 修复TTS参数调用...")
    
    # 备份原文件
    if not backup_file(file_path):
        return False
    
    # 读取文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("📋 原文件内容已读取")
        
        # 修复TTS初始化调用
        old_call = "self.tts_provider = initialize_tts()"
        new_call = "self.tts_provider = initialize_tts(self.config)"
        
        if old_call in content:
            content = content.replace(old_call, new_call)
            print("✅ 修复TTS初始化调用，添加config参数")
        else:
            print("⚠️  找不到需要修复的TTS调用")
            return False
        
        # 写入修复后的内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 文件写入成功")
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False

def verify_fix():
    """验证修复"""
    file_path = 'core/services/unified_event_service.py'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "self.tts_provider = initialize_tts(self.config)" in content:
            print("✅ TTS参数修复验证成功")
            return True
        else:
            print("❌ TTS参数修复验证失败")
            return False
            
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def main():
    """主函数"""
    print("🎯 修复TTS参数调用")
    print("="*50)
    print("🔧 问题: initialize_tts() 需要 config 参数")
    print("⚡ 解决: 传递 self.config 给 initialize_tts()")
    print("="*50)
    
    try:
        # 修复TTS参数
        if not fix_tts_parameter():
            print("❌ TTS参数修复失败")
            return False
        
        # 验证修复
        if not verify_fix():
            print("❌ 修复验证失败")
            return False
        
        print("\n🎉 TTS参数修复完成！")
        print("⚡ 下一步: 重启服务")
        print("systemctl restart xiaozhi-server")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复过程异常: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n✅ 修复成功")
    else:
        print("\n❌ 修复失败")
    
    exit(0 if success else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证TTS修复是否正确应用
"""

import sys
import os

def check_unified_event_service():
    """检查UnifiedEventService的修复"""
    print("🔍 检查UnifiedEventService修复...")
    
    file_path = 'core/services/unified_event_service.py'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("✅ 文件读取成功")
        
        # 检查关键修复点
        checks = [
            ("TTS导入", "from core.utils.modules_initialize import initialize_tts" in content),
            ("TTS初始化", "self.tts_provider = initialize_tts()" in content),
            ("AwakenWithCallbackService调用", "AwakenWithCallbackService(self.config, mqtt_client, self.tts_provider)" in content),
        ]
        
        all_good = True
        for check_name, result in checks:
            if result:
                print(f"✅ {check_name}: 正确")
            else:
                print(f"❌ {check_name}: 错误")
                all_good = False
        
        # 显示__init__方法的关键行
        lines = content.split('\n')
        print("\n📋 __init__方法关键行:")
        for i, line in enumerate(lines, 1):
            if 93 <= i <= 120:
                marker = "➤" if i == 96 else " "
                print(f"{marker} {i:3d}: {line}")
        
        return all_good
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def check_import_path():
    """检查导入路径是否正确"""
    print("\n🔍 检查导入路径...")
    
    try:
        # 尝试导入
        sys.path.insert(0, '.')
        from core.utils.modules_initialize import initialize_tts
        print("✅ initialize_tts导入成功")
        
        # 尝试调用
        tts_provider = initialize_tts()
        print(f"✅ TTS初始化成功: {type(tts_provider).__name__}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 初始化错误: {e}")
        return False

def simulate_unified_event_service():
    """模拟UnifiedEventService初始化"""
    print("\n🧪 模拟UnifiedEventService初始化...")
    
    try:
        sys.path.insert(0, '.')
        
        # 导入必要模块
        from config.config_loader import load_config
        from core.mqtt.mqtt_client import MQTTClient
        from core.utils.modules_initialize import initialize_tts
        from core.mqtt.webhook_callback_handler import AwakenWithCallbackService
        
        print("✅ 所有模块导入成功")
        
        # 模拟初始化过程
        config = load_config()
        mqtt_client = MQTTClient(config.get('mqtt', {}))
        
        print("✅ 配置和MQTT客户端创建成功")
        
        # TTS初始化
        tts_provider = initialize_tts()
        print(f"✅ TTS提供器初始化成功: {type(tts_provider).__name__}")
        
        # AwakenWithCallbackService初始化
        awaken_service = AwakenWithCallbackService(config, mqtt_client, tts_provider)
        print("✅ AwakenWithCallbackService创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 模拟初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🔍 TTS修复验证工具")
    print("="*50)
    
    # 1. 检查文件修复
    file_ok = check_unified_event_service()
    
    # 2. 检查导入路径
    import_ok = check_import_path()
    
    # 3. 模拟初始化
    sim_ok = simulate_unified_event_service()
    
    print("\n📊 验证结果:")
    print(f"  文件修复: {'✅' if file_ok else '❌'}")
    print(f"  导入检查: {'✅' if import_ok else '❌'}")
    print(f"  模拟初始化: {'✅' if sim_ok else '❌'}")
    
    if file_ok and import_ok and sim_ok:
        print("\n🎉 TTS修复验证成功！")
        print("💡 如果服务还有问题，可能是缓存问题")
        print("⚡ 建议:")
        print("   1. 重新加载Python模块: systemctl restart xiaozhi-server")
        print("   2. 清除__pycache__: find . -name '__pycache__' -exec rm -rf {} +")
        return True
    else:
        print("\n❌ TTS修复验证失败！")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

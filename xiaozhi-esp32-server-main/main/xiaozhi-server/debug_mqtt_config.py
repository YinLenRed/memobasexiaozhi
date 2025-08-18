#!/usr/bin/env python3
"""
MQTT配置诊断脚本
用于排查主动问候404错误
"""

import os
import sys
import yaml

def check_config_file():
    """检查配置文件"""
    print("🔍 检查配置文件...")
    
    config_files = [
        "config.yaml",
        "data/.config.yaml", 
        "../config.yaml"
    ]
    
    config_path = None
    for path in config_files:
        if os.path.exists(path):
            config_path = path
            print(f"✅ 找到配置文件: {path}")
            break
    
    if not config_path:
        print("❌ 未找到配置文件")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"❌ 配置文件解析失败: {e}")
        return None

def check_mqtt_config(config):
    """检查MQTT配置"""
    print("\n🔍 检查MQTT配置...")
    
    if not config:
        print("❌ 配置为空")
        return False
    
    # 检查MQTT配置
    mqtt_config = config.get("mqtt", {})
    if not mqtt_config:
        print("❌ 配置中没有'mqtt'部分")
        return False
    
    print("✅ 找到MQTT配置:")
    print(f"   启用状态: {mqtt_config.get('enabled', False)}")
    print(f"   服务器: {mqtt_config.get('host', 'N/A')}")
    print(f"   端口: {mqtt_config.get('port', 'N/A')}")
    
    if not mqtt_config.get("enabled", False):
        print("⚠️ MQTT功能未启用，这会导致主动问候API不可用")
        return False
    
    return True

def check_proactive_greeting_config(config):
    """检查主动问候配置"""
    print("\n🔍 检查主动问候配置...")
    
    greeting_config = config.get("proactive_greeting", {})
    if not greeting_config:
        print("❌ 配置中没有'proactive_greeting'部分")
        return False
    
    print("✅ 找到主动问候配置:")
    print(f"   启用状态: {greeting_config.get('enabled', False)}")
    
    if not greeting_config.get("enabled", False):
        print("⚠️ 主动问候功能未启用")
        return False
    
    return True

def check_server_config(config):
    """检查服务器配置"""
    print("\n🔍 检查服务器配置...")
    
    server_config = config.get("server", {})
    if not server_config:
        print("❌ 配置中没有'server'部分")
        return False
    
    print("✅ 找到服务器配置:")
    print(f"   端口: {server_config.get('port', 'N/A')}")
    print(f"   主机: {server_config.get('host', 'N/A')}")
    
    return True

def generate_fix_suggestions(config):
    """生成修复建议"""
    print("\n🔧 修复建议:")
    
    mqtt_config = config.get("mqtt", {})
    greeting_config = config.get("proactive_greeting", {})
    
    if not mqtt_config.get("enabled", False):
        print("1. 启用MQTT功能:")
        print("   在config.yaml中设置: mqtt.enabled = true")
        print("   示例:")
        print("   mqtt:")
        print("     enabled: true")
        print("     host: 47.98.51.180")
        print("     port: 1883")
        print()
    
    if not greeting_config.get("enabled", False):
        print("2. 启用主动问候功能:")
        print("   在config.yaml中设置: proactive_greeting.enabled = true")
        print("   示例:")
        print("   proactive_greeting:")
        print("     enabled: true")
        print()
    
    print("3. 重启服务:")
    print("   修改配置后需要重启Python服务")
    print("   kill <python_process_id>")
    print("   python app.py")

def main():
    """主函数"""
    print("🎯 MQTT主动问候404错误诊断")
    print("=" * 50)
    
    # 检查当前目录
    print(f"📂 当前目录: {os.getcwd()}")
    print(f"📂 文件列表: {os.listdir('.')}")
    
    # 检查配置文件
    config = check_config_file()
    if not config:
        print("\n❌ 无法继续，请确保配置文件存在且正确")
        return
    
    # 检查各项配置
    mqtt_ok = check_mqtt_config(config)
    greeting_ok = check_proactive_greeting_config(config)  
    server_ok = check_server_config(config)
    
    # 生成建议
    if not (mqtt_ok and greeting_ok):
        generate_fix_suggestions(config)
    else:
        print("\n✅ 配置看起来正常，可能是其他问题:")
        print("1. 检查服务是否正常启动")
        print("2. 检查端口是否被占用")
        print("3. 查看详细日志: tail -f tmp/server.log")

if __name__ == "__main__":
    main()

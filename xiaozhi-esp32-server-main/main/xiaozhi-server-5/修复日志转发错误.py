#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复日志转发错误工具
"""

import yaml
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('修复工具')

def check_config_file():
    """检查配置文件中的日志转发设置"""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        manager_api = config.get('manager-api', {})
        enable_log_forward = manager_api.get('enable_log_forward', True)
        
        logger.info(f"📋 当前配置状态:")
        logger.info(f"   manager-api.enable_log_forward: {enable_log_forward}")
        logger.info(f"   manager-api.url: {manager_api.get('url', '未设置')}")
        
        return config, enable_log_forward
        
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        return None, None

def disable_log_forward():
    """禁用日志转发功能"""
    try:
        config, current_status = check_config_file()
        if not config:
            return False
        
        if not current_status:
            logger.info("✅ 日志转发已经是禁用状态")
            return True
        
        # 备份原配置
        backup_file = f"config_backup_log_forward_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
        with open(backup_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        logger.info(f"✅ 配置已备份到: {backup_file}")
        
        # 修改配置
        if 'manager-api' not in config:
            config['manager-api'] = {}
        
        config['manager-api']['enable_log_forward'] = False
        
        # 保存配置
        with open('config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info("✅ 日志转发已禁用")
        logger.info("💡 这将解决Java认证问题导致的日志转发错误")
        logger.info("💡 不影响主要的消息队列功能")
        
        return True
        
    except Exception as e:
        logger.error(f"禁用日志转发失败: {e}")
        return False

def enable_log_forward():
    """启用日志转发功能"""
    try:
        config, current_status = check_config_file()
        if not config:
            return False
        
        if current_status:
            logger.info("✅ 日志转发已经是启用状态")
            return True
        
        # 修改配置
        if 'manager-api' not in config:
            config['manager-api'] = {}
        
        config['manager-api']['enable_log_forward'] = True
        
        # 保存配置
        with open('config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info("✅ 日志转发已启用")
        logger.info("💡 确保Java后端认证配置正确")
        
        return True
        
    except Exception as e:
        logger.error(f"启用日志转发失败: {e}")
        return False

def test_error_handling():
    """测试错误处理"""
    logger.info("🧪 测试错误处理机制")
    logger.info("="*30)
    
    # 模拟Java认证错误
    test_errors = [
        'Cannot invoke "xiaozhi.modules.security.entity.SysUserTokenEntity.getUserId()" because "tokenEntity" is null',
        'object NoneType can\'t be used in \'await\' expression',
        'HTTP 401 Unauthorized',
        'Connection timeout'
    ]
    
    logger.info("📋 常见错误类型:")
    for i, error in enumerate(test_errors, 1):
        logger.info(f"   {i}. {error}")
    
    logger.info("\n💡 错误解决方案:")
    logger.info("   1. Java认证错误 → 禁用日志转发或修复Java认证")
    logger.info("   2. Python异步错误 → 已修复 (使用run_in_executor)")
    logger.info("   3. HTTP 401错误 → 检查API密钥配置")
    logger.info("   4. 连接超时 → 检查网络和Java服务状态")

def show_status():
    """显示当前状态"""
    logger.info("📊 日志转发状态检查")
    logger.info("="*30)
    
    config, enable_log_forward = check_config_file()
    
    if config:
        logger.info("✅ 配置文件读取成功")
        
        if enable_log_forward:
            logger.info("🟢 日志转发: 启用")
            logger.info("💡 如果遇到Java认证错误，建议运行: python 修复日志转发错误.py disable")
        else:
            logger.info("🔴 日志转发: 禁用")
            logger.info("💡 日志转发已禁用，不会影响消息队列功能")
    else:
        logger.error("❌ 配置文件读取失败")

def main():
    """主函数"""
    import sys
    
    print("🔧 日志转发错误修复工具")
    print("="*40)
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd == "disable":
            logger.info("🔄 禁用日志转发...")
            if disable_log_forward():
                logger.info("🎉 修复完成！")
                logger.info("🔄 建议重启xiaozhi-server服务")
            
        elif cmd == "enable":
            logger.info("🔄 启用日志转发...")
            if enable_log_forward():
                logger.info("🎉 设置完成！")
                logger.info("🔄 建议重启xiaozhi-server服务")
            
        elif cmd == "status":
            show_status()
            
        elif cmd == "test":
            test_error_handling()
            
        else:
            print("用法:")
            print("python 修复日志转发错误.py disable   # 禁用日志转发")
            print("python 修复日志转发错误.py enable    # 启用日志转发")
            print("python 修复日志转发错误.py status    # 查看状态")
            print("python 修复日志转发错误.py test      # 测试错误处理")
    else:
        print("🎯 快速修复选项:")
        print("1. python 修复日志转发错误.py disable   # 禁用日志转发（推荐）")
        print("2. python 修复日志转发错误.py status    # 查看当前状态")
        print("3. python 修复日志转发错误.py test      # 查看错误说明")
        print()
        
        choice = input("请选择操作 (disable/status/test): ").strip().lower()
        
        if choice == "disable":
            logger.info("🔄 禁用日志转发...")
            if disable_log_forward():
                logger.info("🎉 修复完成！")
                logger.info("🔄 建议重启xiaozhi-server服务")
                
        elif choice == "status":
            show_status()
            
        elif choice == "test":
            test_error_handling()
            
        else:
            logger.info("已取消操作")

if __name__ == "__main__":
    main()

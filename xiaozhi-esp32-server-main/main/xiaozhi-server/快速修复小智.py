#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速修复小智无声问题
"""

import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('快速修复')

DEVICE_ID = "f0:9e:9e:04:8a:44"
API_BASE = "http://47.98.51.180:8003"

def quick_test():
    """快速测试小智是否能说话"""
    logger.info("🧪 快速测试小智语音...")
    
    try:
        payload = {
            "device_id": DEVICE_ID,
            "category": "system_reminder",
            "initial_content": "测试小智语音，现在可以说话吗？"
        }
        
        response = requests.post(
            f"{API_BASE}/xiaozhi/greeting/send",
            json=payload,
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ 测试成功: {result['message']}")
            logger.info(f"📊 跟踪ID: {result['track_id']}")
            logger.info("💡 请检查硬件是否有声音")
            return True
        else:
            logger.error(f"❌ 测试失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}")
        return False

def check_service():
    """检查服务状态"""
    logger.info("🔍 检查服务状态...")
    
    try:
        # 检查服务健康状态
        response = requests.get(f"{API_BASE}/api/cron/health", timeout=5)
        if response.status_code == 200:
            logger.info("✅ HTTP服务正常")
        else:
            logger.error(f"❌ HTTP服务异常: {response.status_code}")
            return False
        
        # 检查设备状态
        response = requests.get(f"{API_BASE}/xiaozhi/greeting/status?device_id={DEVICE_ID}&simple=true", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("online"):
                logger.info("✅ 设备在线")
            else:
                logger.error("❌ 设备离线")
                return False
        else:
            logger.error(f"❌ 设备状态检查失败: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 服务检查失败: {e}")
        return False

def restore_original_config():
    """恢复原始配置"""
    logger.info("🔧 如果需要恢复原配置，请手动执行：")
    logger.info("1. 检查config_backup_*文件")
    logger.info("2. 找到最新的备份文件")
    logger.info("3. 复制为config.yaml")
    logger.info("4. 重启服务")

def main():
    """主函数"""
    logger.info("🔧 快速修复小智无声问题")
    logger.info("="*50)
    
    # 1. 检查服务状态
    if not check_service():
        logger.error("💡 服务异常，建议重启Python服务")
        return
    
    # 2. 快速测试
    if quick_test():
        logger.info("🎉 小智可以正常说话！")
    else:
        logger.error("❌ 小智仍然无法说话")
        logger.info("\n💡 建议修复步骤：")
        logger.info("1. 重启Python服务：systemctl restart xiaozhi-server")
        logger.info("2. 如果还不行，检查LLM配置是否有问题")
        logger.info("3. 考虑恢复之前的配置文件")
        
        restore_original_config()

if __name__ == "__main__":
    main()

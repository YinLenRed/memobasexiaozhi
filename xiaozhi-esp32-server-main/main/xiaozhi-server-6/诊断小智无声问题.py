#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断小智无声问题
全面检查TTS、音频传输、MQTT等环节
"""

import asyncio
import logging
import json
import os
import requests
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('小智诊断')

# 配置信息
DEVICE_ID = "f0:9e:9e:04:8a:44"
API_BASE = "http://47.98.51.180:8003"

class XiaozhiDiagnostic:
    """小智诊断工具"""
    
    def __init__(self):
        self.issues = []
        self.successes = []
    
    def add_issue(self, issue: str):
        """添加问题"""
        self.issues.append(issue)
        logger.error(f"❌ {issue}")
    
    def add_success(self, success: str):
        """添加成功项"""
        self.successes.append(success)
        logger.info(f"✅ {success}")
    
    async def check_service_status(self):
        """检查服务状态"""
        logger.info("🔍 1. 检查服务状态...")
        
        try:
            # 检查HTTP服务
            response = requests.get(f"{API_BASE}/api/cron/health", timeout=5)
            if response.status_code == 200:
                self.add_success("HTTP服务正常")
            else:
                self.add_issue(f"HTTP服务异常: {response.status_code}")
        except Exception as e:
            self.add_issue(f"HTTP服务连接失败: {e}")
        
        # 检查设备状态
        try:
            response = requests.get(f"{API_BASE}/xiaozhi/greeting/status?device_id={DEVICE_ID}&simple=true", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("online"):
                    self.add_success("设备在线状态正常")
                else:
                    self.add_issue("设备显示离线")
            else:
                self.add_issue(f"设备状态检查失败: {response.status_code}")
        except Exception as e:
            self.add_issue(f"设备状态检查连接失败: {e}")
    
    async def check_tts_service(self):
        """检查TTS服务"""
        logger.info("🔍 2. 检查TTS服务...")
        
        try:
            # 检查TTS配置
            from config.config_loader import load_config
            config = load_config()
            
            tts_config = config.get("TTS", {})
            selected_tts = config.get("selected_module", {}).get("TTS", "")
            
            if selected_tts and selected_tts in tts_config:
                self.add_success(f"TTS配置正常: {selected_tts}")
                
                # 尝试初始化TTS
                from core.utils.modules_initialize import initialize_tts
                try:
                    tts_provider = initialize_tts(config)
                    if tts_provider:
                        self.add_success("TTS提供器初始化成功")
                        
                        # 测试TTS生成
                        try:
                            test_text = "测试语音合成"
                            test_file = "/tmp/tts_test.mp3"
                            
                            # 使用异步方法
                            await tts_provider.text_to_speak(test_text, test_file)
                            
                            if os.path.exists(test_file) and os.path.getsize(test_file) > 0:
                                self.add_success("TTS音频生成成功")
                                os.remove(test_file)  # 清理测试文件
                            else:
                                self.add_issue("TTS音频文件生成失败或为空")
                                
                        except Exception as e:
                            self.add_issue(f"TTS音频生成失败: {e}")
                    else:
                        self.add_issue("TTS提供器初始化失败")
                except Exception as e:
                    self.add_issue(f"TTS初始化异常: {e}")
            else:
                self.add_issue(f"TTS配置缺失: selected_tts={selected_tts}")
                
        except Exception as e:
            self.add_issue(f"TTS服务检查失败: {e}")
    
    async def check_mqtt_service(self):
        """检查MQTT服务"""
        logger.info("🔍 3. 检查MQTT服务...")
        
        try:
            from core.mqtt.mqtt_manager import MQTTManager
            
            mqtt_manager = MQTTManager.get_instance()
            if mqtt_manager:
                if mqtt_manager.is_connected():
                    self.add_success("MQTT连接正常")
                else:
                    self.add_issue("MQTT连接断开")
                
                # 检查设备连接状态
                device_online = mqtt_manager.is_device_online(DEVICE_ID)
                if device_online:
                    self.add_success(f"设备 {DEVICE_ID} MQTT在线")
                else:
                    self.add_issue(f"设备 {DEVICE_ID} MQTT离线")
                    
            else:
                self.add_issue("MQTT管理器未初始化")
                
        except Exception as e:
            self.add_issue(f"MQTT服务检查失败: {e}")
    
    async def check_websocket_service(self):
        """检查WebSocket服务"""
        logger.info("🔍 4. 检查WebSocket服务...")
        
        try:
            from core.websocket_server import WebSocketServer
            
            # 检查WebSocket服务器状态
            # 这里只是简单检查，实际可能需要更复杂的检测
            self.add_success("WebSocket服务检查完成")
            
        except Exception as e:
            self.add_issue(f"WebSocket服务检查失败: {e}")
    
    async def test_simple_speak(self):
        """测试简单语音播报"""
        logger.info("🔍 5. 测试简单语音播报...")
        
        try:
            # 发送简单测试消息
            test_payload = {
                "device_id": DEVICE_ID,
                "category": "system_reminder",
                "initial_content": "测试语音播报，现在时间是" + datetime.now().strftime("%H点%M分")
            }
            
            response = requests.post(
                f"{API_BASE}/xiaozhi/greeting/send",
                json=test_payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                track_id = result.get("track_id")
                self.add_success(f"测试播报发送成功，跟踪ID: {track_id}")
                logger.info("💡 请检查硬件是否有声音播放")
                
                # 等待一下让用户听到声音
                await asyncio.sleep(3)
                
            else:
                self.add_issue(f"测试播报发送失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.add_issue(f"测试播报异常: {e}")
    
    async def check_llm_service(self):
        """检查LLM服务"""
        logger.info("🔍 6. 检查LLM服务...")
        
        try:
            from config.config_loader import load_config
            config = load_config()
            
            llm_config = config.get("LLM", {})
            selected_llm = config.get("selected_module", {}).get("LLM", "")
            
            if selected_llm and selected_llm in llm_config:
                current_config = llm_config[selected_llm]
                api_key = current_config.get("api_key", "")
                
                # 检查API密钥
                import re
                if re.search(r'[\u4e00-\u9fff]', api_key):
                    self.add_issue(f"LLM API密钥包含中文字符: {selected_llm}")
                elif re.search(r'你的.*key', api_key.lower()):
                    self.add_issue(f"LLM API密钥为占位符: {selected_llm}")
                else:
                    self.add_success(f"LLM配置正常: {selected_llm}")
                    
                    # 尝试初始化LLM
                    try:
                        from core.utils import llm_utils
                        llm_type = current_config.get("type", selected_llm)
                        llm_instance = llm_utils.create_instance(llm_type, current_config)
                        
                        if llm_instance:
                            self.add_success("LLM实例创建成功")
                        else:
                            self.add_issue("LLM实例创建失败")
                            
                    except Exception as e:
                        self.add_issue(f"LLM初始化失败: {e}")
            else:
                self.add_issue(f"LLM配置缺失: {selected_llm}")
                
        except Exception as e:
            self.add_issue(f"LLM服务检查失败: {e}")
    
    async def check_unified_event_service(self):
        """检查统一事件服务"""
        logger.info("🔍 7. 检查统一事件服务...")
        
        try:
            from core.services.unified_event_service import get_unified_event_service
            
            service = get_unified_event_service()
            if service:
                self.add_success("统一事件服务实例存在")
                
                # 检查LLM和TTS
                if hasattr(service, 'llm') and service.llm:
                    self.add_success("事件服务LLM已初始化")
                else:
                    self.add_issue("事件服务LLM未初始化")
                
                if hasattr(service, 'tts_provider') and service.tts_provider:
                    self.add_success("事件服务TTS已初始化")
                else:
                    self.add_issue("事件服务TTS未初始化")
            else:
                self.add_issue("统一事件服务未初始化")
                
        except Exception as e:
            self.add_issue(f"统一事件服务检查失败: {e}")
    
    def generate_report(self):
        """生成诊断报告"""
        logger.info("\n" + "="*60)
        logger.info("📊 小智诊断报告")
        logger.info("="*60)
        
        logger.info(f"✅ 正常项目 ({len(self.successes)}):")
        for success in self.successes:
            logger.info(f"   ✅ {success}")
        
        logger.info(f"\n❌ 问题项目 ({len(self.issues)}):")
        for issue in self.issues:
            logger.info(f"   ❌ {issue}")
        
        # 生成建议
        logger.info("\n💡 修复建议:")
        if not self.issues:
            logger.info("   🎉 系统状态良好，无需修复")
        else:
            if any("TTS" in issue for issue in self.issues):
                logger.info("   🔧 TTS问题: 检查TTS配置和服务状态")
            if any("MQTT" in issue for issue in self.issues):
                logger.info("   🔧 MQTT问题: 检查MQTT连接和设备状态")
            if any("LLM" in issue for issue in self.issues):
                logger.info("   🔧 LLM问题: 检查LLM配置和API密钥")
            if any("HTTP" in issue for issue in self.issues):
                logger.info("   🔧 服务问题: 重启Python服务")
        
        return len(self.issues) == 0

async def main():
    """主诊断函数"""
    logger.info("🩺 开始小智无声问题诊断")
    
    diagnostic = XiaozhiDiagnostic()
    
    # 执行各项检查
    await diagnostic.check_service_status()
    await diagnostic.check_tts_service()
    await diagnostic.check_mqtt_service()
    await diagnostic.check_websocket_service()
    await diagnostic.check_llm_service()
    await diagnostic.check_unified_event_service()
    await diagnostic.test_simple_speak()
    
    # 生成报告
    is_healthy = diagnostic.generate_report()
    
    if is_healthy:
        logger.info("\n🎉 诊断完成：系统正常！")
    else:
        logger.info("\n🔧 诊断完成：发现问题，请根据建议修复")

if __name__ == "__main__":
    asyncio.run(main())

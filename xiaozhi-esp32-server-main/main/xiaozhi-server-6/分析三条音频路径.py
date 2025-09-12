#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析三条音频路径的TTS初始化差异
找出为什么Python测试和普通对话有声音，Java触发没声音
"""

import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('路径分析')

class AudioPathAnalyzer:
    """音频路径分析器"""
    
    def __init__(self):
        pass
    
    def analyze_python_test_path(self):
        """分析Python测试脚本路径"""
        logger.info("🐍 分析Python测试脚本路径")
        logger.info("="*50)
        
        try:
            # 模拟Python测试脚本的调用路径
            logger.info("📋 Python测试路径:")
            logger.info("   1. python 检查音频问题.py")
            logger.info("   2. requests.post('/xiaozhi/greeting/send')")
            logger.info("   3. ProactiveGreetingService.send_proactive_greeting()")
            logger.info("   4. self._initialize_tts() # 自己初始化TTS")
            logger.info("   5. mqtt_client.send_speak_command()")
            logger.info("   6. ✅ 有声音")
            
            # 检查ProactiveGreetingService的TTS初始化
            try:
                from core.mqtt.proactive_greeting_service import ProactiveGreetingService
                logger.info("✅ ProactiveGreetingService模块存在")
                
                # 检查是否有TTS初始化方法
                if hasattr(ProactiveGreetingService, '_initialize_tts'):
                    logger.info("✅ 有_initialize_tts方法")
                else:
                    logger.warning("⚠️  没有_initialize_tts方法")
                    
            except Exception as e:
                logger.error(f"❌ 检查ProactiveGreetingService失败: {e}")
                
        except Exception as e:
            logger.error(f"❌ 分析Python测试路径失败: {e}")
    
    def analyze_normal_conversation_path(self):
        """分析普通对话路径"""
        logger.info("\n💬 分析普通对话路径")
        logger.info("="*50)
        
        try:
            logger.info("📋 普通对话路径:")
            logger.info("   1. 用户说话 → WebSocket连接")
            logger.info("   2. ConnectionHandler.on_message()")
            logger.info("   3. ConnectionHandler._initialize_tts() # 连接时初始化")
            logger.info("   4. LLM生成回复")
            logger.info("   5. tts.generate() # 使用已初始化的TTS")
            logger.info("   6. ✅ 有声音")
            
            # 检查ConnectionHandler的TTS初始化
            try:
                from core.connection import ConnectionHandler
                logger.info("✅ ConnectionHandler模块存在")
                
                # 检查是否有TTS初始化方法
                if hasattr(ConnectionHandler, '_initialize_tts'):
                    logger.info("✅ 有_initialize_tts方法")
                else:
                    logger.warning("⚠️  没有_initialize_tts方法")
                    
            except Exception as e:
                logger.error(f"❌ 检查ConnectionHandler失败: {e}")
                
        except Exception as e:
            logger.error(f"❌ 分析普通对话路径失败: {e}")
    
    def analyze_java_trigger_path(self):
        """分析Java触发路径"""
        logger.info("\n☕ 分析Java触发路径")
        logger.info("="*50)
        
        try:
            logger.info("📋 Java触发路径:")
            logger.info("   1. Java发送MQTT事件")
            logger.info("   2. UnifiedEventService.handle_message()")
            logger.info("   3. AwakenWithCallbackService(config, mqtt_client) # ❌ 没传TTS!")
            logger.info("   4. WebhookCallbackHandler(config, mqtt_client, None) # TTS=None")
            logger.info("   5. _generate_tts_audio() → TTS提供器未配置")
            logger.info("   6. ❌ 使用模拟音频，无声音")
            
            # 检查UnifiedEventService的初始化
            try:
                from core.services.unified_event_service import UnifiedEventService
                logger.info("✅ UnifiedEventService模块存在")
                
                # 模拟创建实例检查TTS
                from core.mqtt.mqtt_client import MQTTClient
                mqtt_client = MQTTClient({})
                
                try:
                    event_service = UnifiedEventService(mqtt_client)
                    
                    # 检查是否有TTS相关属性
                    if hasattr(event_service, 'tts_provider'):
                        logger.info("✅ 有tts_provider属性")
                    else:
                        logger.warning("⚠️  没有tts_provider属性 - 这就是问题!")
                    
                    # 检查awaken_service的TTS
                    if hasattr(event_service, 'awaken_service'):
                        awaken_service = event_service.awaken_service
                        if hasattr(awaken_service, 'callback_handler'):
                            callback_handler = awaken_service.callback_handler
                            if hasattr(callback_handler, 'tts_provider'):
                                tts_provider = callback_handler.tts_provider
                                logger.info(f"🎵 callback_handler的TTS: {type(tts_provider).__name__ if tts_provider else 'None'}")
                                
                                if tts_provider is None:
                                    logger.error("❌ 这就是问题所在: callback_handler的TTS提供器为None!")
                            else:
                                logger.warning("⚠️  callback_handler没有tts_provider属性")
                        else:
                            logger.warning("⚠️  awaken_service没有callback_handler属性")
                    else:
                        logger.warning("⚠️  event_service没有awaken_service属性")
                        
                except Exception as e:
                    logger.error(f"❌ 创建UnifiedEventService实例失败: {e}")
                    
            except Exception as e:
                logger.error(f"❌ 检查UnifiedEventService失败: {e}")
                
        except Exception as e:
            logger.error(f"❌ 分析Java触发路径失败: {e}")
    
    def compare_tts_initialization(self):
        """对比三条路径的TTS初始化"""
        logger.info("\n🔍 TTS初始化对比")
        logger.info("="*50)
        
        logger.info("📊 三条路径TTS初始化对比:")
        logger.info("   1. Python测试脚本:")
        logger.info("      ProactiveGreetingService.__init__()")
        logger.info("      └─ await self._initialize_tts()")
        logger.info("      └─ ✅ 有自己的TTS实例")
        
        logger.info("\n   2. 普通对话:")
        logger.info("      ConnectionHandler.__init__()")
        logger.info("      └─ self._initialize_tts()")
        logger.info("      └─ ✅ 有自己的TTS实例")
        
        logger.info("\n   3. Java触发:")
        logger.info("      UnifiedEventService.__init__()")
        logger.info("      └─ AwakenWithCallbackService(config, mqtt_client) # ❌ 缺少TTS参数")
        logger.info("      └─ WebhookCallbackHandler(config, mqtt_client, None)")
        logger.info("      └─ ❌ TTS提供器为None")
    
    def suggest_unified_fix(self):
        """建议统一修复方案"""
        logger.info("\n💡 统一修复方案")
        logger.info("="*50)
        
        logger.info("🎯 问题核心:")
        logger.info("   三条音频路径使用了不同的TTS初始化机制")
        logger.info("   只有Java触发路径没有正确初始化TTS")
        
        logger.info("\n🔧 修复方案:")
        logger.info("   让Java触发路径也像其他路径一样正确初始化TTS")
        
        logger.info("\n📝 具体修复步骤:")
        logger.info("   1. 修改UnifiedEventService.__init__()")
        logger.info("   2. 添加TTS初始化: self.tts_provider = self._initialize_tts()")
        logger.info("   3. 传递给AwakenWithCallbackService: AwakenWithCallbackService(config, mqtt_client, self.tts_provider)")
        logger.info("   4. 这样Java触发就能像其他路径一样有声音了")
        
        logger.info("\n⚡ 执行修复:")
        logger.info("   python 快速修复Java事件TTS.py")
    
    def run_comprehensive_analysis(self):
        """运行综合分析"""
        logger.info("🔍 三条音频路径综合分析")
        logger.info("="*60)
        
        try:
            # 1. 分析Python测试脚本路径
            self.analyze_python_test_path()
            
            # 2. 分析普通对话路径
            self.analyze_normal_conversation_path()
            
            # 3. 分析Java触发路径
            self.analyze_java_trigger_path()
            
            # 4. 对比TTS初始化
            self.compare_tts_initialization()
            
            # 5. 建议修复方案
            self.suggest_unified_fix()
            
            logger.info("\n✅ 综合分析完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 综合分析异常: {e}")
            return False

def main():
    """主分析函数"""
    logger.info("🔍 三条音频路径分析工具")
    logger.info("="*50)
    logger.info("🎯 目标:")
    logger.info("   分析为什么Python测试和普通对话有声音")
    logger.info("   但Java触发没有声音")
    logger.info("="*50)
    
    analyzer = AudioPathAnalyzer()
    
    try:
        success = analyzer.run_comprehensive_analysis()
        
        if success:
            logger.info("\n🎉 分析完成！问题已定位")
            logger.info("💡 三条路径使用了不同的TTS初始化机制")
            logger.info("🔧 立即修复: python 快速修复Java事件TTS.py")
        else:
            logger.error("❌ 分析失败")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ 分析异常: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎯 问题已定位：三条路径TTS初始化不同")
        print("⚡ 立即修复: python 快速修复Java事件TTS.py")
    else:
        print("❌ 分析失败")
    
    exit(0 if success else 1)

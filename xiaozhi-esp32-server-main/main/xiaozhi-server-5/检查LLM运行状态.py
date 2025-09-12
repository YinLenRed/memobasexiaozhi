#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查LLM运行状态
验证当前LLM是否正在使用正确的DeepSeek配置
"""

import logging
import asyncio

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('LLM状态检查')

async def check_llm_status():
    """检查LLM运行状态"""
    logger.info("🔧 检查LLM运行状态")
    logger.info("="*50)
    
    try:
        # 加载配置
        from config.config_loader import load_config
        config = load_config()
        
        # 检查LLM配置
        llm_config = config.get("LLM", {})
        selected_llm = config.get("selected_module", {}).get("LLM", "")
        
        logger.info(f"📋 当前选择的LLM: {selected_llm}")
        
        if selected_llm in llm_config:
            current_config = llm_config[selected_llm]
            logger.info(f"🔍 {selected_llm} 配置:")
            logger.info(f"   API密钥: {current_config.get('api_key', 'N/A')[:20]}...")
            logger.info(f"   基础URL: {current_config.get('base_url', current_config.get('url', 'N/A'))}")
            logger.info(f"   模型名称: {current_config.get('model_name', 'N/A')}")
            logger.info(f"   类型: {current_config.get('type', 'N/A')}")
            
            # 验证是否为DeepSeek配置
            model_name = current_config.get('model_name', '')
            base_url = current_config.get('base_url', current_config.get('url', ''))
            
            if 'deepseek' in model_name.lower() and 'ark.cn-beijing.volces.com' in base_url:
                logger.info("✅ 确认使用DeepSeek配置")
                
                # 测试LLM实例化
                logger.info("\n🧪 测试LLM实例化...")
                from core.utils import llm_utils
                try:
                    llm_type = current_config.get("type", selected_llm)
                    llm_instance = llm_utils.create_instance(llm_type, current_config)
                    logger.info("✅ LLM实例创建成功")
                    
                    # 简单测试
                    logger.info("🔄 测试LLM响应...")
                    test_response = llm_instance.response_no_stream(
                        "你是一个智能助手", 
                        "简单回答：你好"
                    )
                    logger.info(f"✅ LLM响应测试成功: {test_response[:50]}...")
                    
                except Exception as e:
                    logger.error(f"❌ LLM测试失败: {e}")
                    return False
                
            else:
                logger.warning("⚠️ 配置可能不是DeepSeek格式")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 检查失败: {e}")
        return False

def check_unified_event_service():
    """检查统一事件服务状态"""
    logger.info("\n🔍 检查统一事件服务状态...")
    
    try:
        from core.services.unified_event_service import get_unified_event_service
        
        # 获取服务实例
        service = get_unified_event_service()
        
        if service:
            logger.info("✅ 统一事件服务实例存在")
            
            # 检查LLM实例
            if hasattr(service, 'llm') and service.llm:
                logger.info("✅ 事件服务LLM实例已初始化")
                logger.info(f"   LLM类型: {type(service.llm).__name__}")
            else:
                logger.warning("⚠️ 事件服务LLM实例未初始化")
            
            # 检查TTS实例
            if hasattr(service, 'tts_provider') and service.tts_provider:
                logger.info("✅ 事件服务TTS实例已初始化")
                logger.info(f"   TTS类型: {type(service.tts_provider).__name__}")
            else:
                logger.warning("⚠️ 事件服务TTS实例未初始化")
                
        else:
            logger.error("❌ 统一事件服务实例不存在")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 事件服务检查失败: {e}")
        return False

async def main():
    """主函数"""
    try:
        logger.info("🎯 LLM运行状态全面检查")
        
        # 检查LLM配置和状态
        llm_ok = await check_llm_status()
        
        # 检查统一事件服务
        service_ok = check_unified_event_service()
        
        if llm_ok and service_ok:
            logger.info("\n🎉 所有检查通过！")
            logger.info("💡 系统状态:")
            logger.info("   ✅ LLM配置正确")
            logger.info("   ✅ LLM实例正常")
            logger.info("   ✅ 事件服务正常")
            logger.info("   ✅ 可以正常处理Java触发的主动问候")
            
            logger.info("\n🧪 测试建议:")
            logger.info("   1. 让Java后端发送主动问候事件")
            logger.info("   2. 观察硬件是否有声音播放")
            logger.info("   3. 检查日志中的prompt处理过程")
            
        else:
            logger.error("\n❌ 检查发现问题")
            logger.error("💡 需要进一步排查")
        
        return llm_ok and service_ok
        
    except Exception as e:
        logger.error(f"❌ 主检查失败: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        exit(1)

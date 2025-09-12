#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM错误保护机制
当LLM调用失败时，使用备用内容生成，避免系统崩溃
"""

import logging
import traceback
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger('LLM错误保护')

class LLMErrorHandler:
    """LLM错误处理器"""
    
    def __init__(self):
        self.error_count = 0
        self.max_errors = 5  # 连续错误阈值
        self.fallback_enabled = False
        
        # 备用内容模板
        self.fallback_templates = {
            "weather": [
                "收到天气信息，请注意天气变化。",
                "天气预报更新，请做好相应准备。",
                "气象信息提醒，关注天气变化。"
            ],
            "holiday": [
                "节日快乐！祝您节日愉快！",
                "节日祝福，祝您和家人身体健康！",
                "节日问候，愿您节日开心！"
            ],
            "solar_term": [
                "节气更迭，注意身体健康。",
                "时令变化，请适应季节转换。",
                "节气提醒，关注季节养生。"
            ],
            "default": [
                "收到消息，请查看相关信息。",
                "消息提醒，请注意查看。",
                "信息更新，请及时关注。"
            ]
        }
    
    def safe_llm_call(self, llm_instance, messages: List[Dict], event_type: str = "default", **kwargs) -> str:
        """安全的LLM调用，带错误保护"""
        try:
            if self.fallback_enabled:
                logger.warning("🛡️ LLM已进入备用模式，使用模板内容")
                return self._get_fallback_content(event_type)
            
            # 尝试正常LLM调用
            response = llm_instance.chat(messages, **kwargs)
            
            if response and len(response.strip()) > 0:
                # 检测OpenAI错误信息
                if "OpenAI服务响应异常" in response or "Error code:" in response:
                    logger.error("🚨 LLM返回错误信息，启用备用模式")
                    self._handle_error("LLM返回错误信息", event_type)
                    return self._get_fallback_content(event_type)
                
                # 重置错误计数
                self.error_count = 0
                return response.strip()
            else:
                logger.warning("⚠️ LLM返回空内容")
                return self._handle_error("LLM返回空内容", event_type)
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ LLM调用异常: {error_msg}")
            
            # 特殊处理OpenAI MissingParameter错误
            if "MissingParameter" in error_msg:
                logger.error("🔍 检测到MissingParameter错误，可能是API配置问题")
            elif "authentication" in error_msg.lower():
                logger.error("🔍 检测到认证错误，检查API密钥")
            elif "timeout" in error_msg.lower():
                logger.error("🔍 检测到超时错误，检查网络连接")
            
            return self._handle_error(error_msg, event_type)
    
    def _handle_error(self, error_msg: str, event_type: str) -> str:
        """处理LLM错误"""
        self.error_count += 1
        
        if self.error_count >= self.max_errors:
            logger.error(f"🚨 LLM连续错误超过阈值({self.max_errors})，启用备用模式")
            self.fallback_enabled = True
        
        return self._get_fallback_content(event_type)
    
    def _get_fallback_content(self, event_type: str) -> str:
        """获取备用内容"""
        import random
        
        templates = self.fallback_templates.get(event_type, self.fallback_templates["default"])
        content = random.choice(templates)
        
        logger.info(f"🛡️ 使用备用内容: {content}")
        return content
    
    def reset_fallback(self):
        """重置备用模式"""
        self.fallback_enabled = False
        self.error_count = 0
        logger.info("🔄 LLM备用模式已重置")
    
    def get_status(self) -> Dict[str, Any]:
        """获取错误处理状态"""
        return {
            "error_count": self.error_count,
            "max_errors": self.max_errors,
            "fallback_enabled": self.fallback_enabled,
            "status": "备用模式" if self.fallback_enabled else "正常模式"
        }

# 全局错误处理器实例
_error_handler: Optional[LLMErrorHandler] = None

def get_llm_error_handler() -> LLMErrorHandler:
    """获取全局LLM错误处理器"""
    global _error_handler
    if _error_handler is None:
        _error_handler = LLMErrorHandler()
    return _error_handler

def safe_llm_generate(llm_instance, messages: List[Dict], event_type: str = "default", **kwargs) -> str:
    """安全的LLM内容生成（全局函数）"""
    handler = get_llm_error_handler()
    return handler.safe_llm_call(llm_instance, messages, event_type, **kwargs)

def patch_unified_event_service():
    """为UnifiedEventService打补丁，集成错误保护"""
    try:
        import sys
        import importlib
        
        # 动态导入UnifiedEventService
        if 'core.services.unified_event_service' in sys.modules:
            unified_module = sys.modules['core.services.unified_event_service']
            
            # 获取UnifiedEventService类
            unified_service_class = getattr(unified_module, 'UnifiedEventService', None)
            if unified_service_class:
                # 备份原始方法
                original_generate = getattr(unified_service_class, '_generate_content_with_java_prompt', None)
                
                if original_generate:
                    def safe_generate_content_with_java_prompt(self, event_data: Dict[str, Any]) -> Optional[str]:
                        """安全的内容生成方法"""
                        try:
                            return original_generate(self, event_data)
                        except Exception as e:
                            logger.error(f"LLM内容生成失败: {e}")
                            
                            # 获取事件类型
                            event_type = "default"
                            if self.event_parser:
                                event_type = self.event_parser.detect_event_type(event_data)
                            
                            # 使用备用内容
                            handler = get_llm_error_handler()
                            return handler._get_fallback_content(event_type)
                    
                    # 替换方法
                    setattr(unified_service_class, '_generate_content_with_java_prompt', safe_generate_content_with_java_prompt)
                    logger.info("✅ UnifiedEventService错误保护补丁已应用")
                    
    except Exception as e:
        logger.error(f"❌ 错误保护补丁应用失败: {e}")

def main():
    """测试错误保护机制"""
    print("🛡️ LLM错误保护机制测试")
    print("="*30)
    
    handler = LLMErrorHandler()
    
    # 模拟LLM调用失败
    class MockLLM:
        def __init__(self, should_fail=True):
            self.should_fail = should_fail
            self.call_count = 0
        
        def chat(self, messages, **kwargs):
            self.call_count += 1
            if self.should_fail:
                if self.call_count <= 3:
                    raise Exception("OpenAI服务响应异常: Error code: 400 - {'error': {'code': 'MissingParameter'}}")
                else:
                    return "正常响应内容"
            return "正常响应"
    
    # 测试场景
    scenarios = [
        ("天气事件", "weather", True),
        ("节日事件", "holiday", True), 
        ("默认事件", "default", False)
    ]
    
    for name, event_type, should_fail in scenarios:
        print(f"\n🧪 测试场景: {name}")
        
        mock_llm = MockLLM(should_fail)
        messages = [{"role": "user", "content": "测试消息"}]
        
        for i in range(6):  # 测试多次调用
            result = handler.safe_llm_call(mock_llm, messages, event_type)
            print(f"  调用 {i+1}: {result}")
            
            status = handler.get_status()
            if status["fallback_enabled"]:
                print(f"  状态: {status['status']} (错误次数: {status['error_count']})")
                break
        
        # 重置状态
        handler.reset_fallback()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
稳健的LLM包装器 - 处理MissingParameter和预热问题
基于实际测试：前3次失败，第4次成功的模式
"""

import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger('LLM包装器')

class RobustLLMWrapper:
    """稳健的LLM包装器"""
    
    def __init__(self, llm_instance, config=None):
        self.llm_instance = llm_instance
        self.config = config or {}
        self.is_warmed_up = False
        self.call_count = 0
        
        # 从配置获取参数
        error_config = self.config.get('llm_error_handling', {})
        self.max_retry_attempts = error_config.get('max_retry_attempts', 4)
        self.retry_interval = error_config.get('retry_interval', 2)
        self.enable_fallback = error_config.get('enable_fallback', True)
        self.warmup_calls = error_config.get('warmup_calls', 2)
        
        logger.info(f"🛡️ LLM包装器已初始化，重试次数: {self.max_retry_attempts}")
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """稳健的LLM聊天调用"""
        self.call_count += 1
        
        # 根据实际测试结果：前3次可能失败，第4次开始稳定
        # 所以我们给更多的耐心和重试机会
        
        for attempt in range(1, self.max_retry_attempts + 1):
            try:
                logger.debug(f"🔄 LLM调用 #{self.call_count}, 尝试 {attempt}/{self.max_retry_attempts}")
                
                response = self.llm_instance.chat(messages, **kwargs)
                
                if response and len(response.strip()) > 0:
                    # 检查是否是错误响应
                    if self._is_error_response(response):
                        if attempt < self.max_retry_attempts:
                            logger.warning(f"⚠️ 第{attempt}次调用返回错误，{self.retry_interval}秒后重试...")
                            time.sleep(self.retry_interval)
                            continue
                        else:
                            logger.error(f"❌ {self.max_retry_attempts}次尝试后仍返回错误")
                            return self._get_fallback_response(messages)
                    
                    # 成功响应
                    if attempt > 1:
                        logger.info(f"✅ LLM调用成功 (第{attempt}次尝试)")
                    
                    # 标记为已预热
                    if not self.is_warmed_up and self.call_count >= self.warmup_calls:
                        self.is_warmed_up = True
                        logger.info("🔥 LLM已预热完成")
                    
                    return response.strip()
                else:
                    # 空响应
                    if attempt < self.max_retry_attempts:
                        logger.warning(f"⚠️ 第{attempt}次调用返回空，{self.retry_interval}秒后重试...")
                        time.sleep(self.retry_interval)
                        continue
                    else:
                        return self._get_fallback_response(messages)
                        
            except Exception as e:
                error_msg = str(e)
                
                # 特殊处理MissingParameter错误
                if "MissingParameter" in error_msg:
                    if attempt <= 3:  # 基于测试结果：前3次可能都是这个错误
                        logger.info(f"🔄 第{attempt}次MissingParameter (预期中)，{self.retry_interval}秒后重试...")
                        time.sleep(self.retry_interval)
                        continue
                    elif attempt < self.max_retry_attempts:
                        logger.warning(f"⚠️ 第{attempt}次仍有MissingParameter，{self.retry_interval}秒后重试...")
                        time.sleep(self.retry_interval)
                        continue
                    else:
                        logger.error(f"❌ {self.max_retry_attempts}次尝试后仍有MissingParameter")
                        return self._get_fallback_response(messages)
                else:
                    # 其他错误
                    logger.error(f"❌ LLM调用异常 (第{attempt}次): {e}")
                    if attempt < self.max_retry_attempts:
                        time.sleep(self.retry_interval)
                        continue
                    else:
                        return self._get_fallback_response(messages)
        
        # 所有尝试都失败了
        return self._get_fallback_response(messages)
    
    def _is_error_response(self, response: str) -> bool:
        """检查是否是错误响应"""
        error_indicators = [
            "OpenAI服务响应异常",
            "Error code:",
            "MissingParameter",
            "invalid_request_error"
        ]
        return any(indicator in response for indicator in error_indicators)
    
    def _get_fallback_response(self, messages: List[Dict]) -> str:
        """获取备用响应"""
        if not self.enable_fallback:
            return "系统暂时不可用，请稍后重试。"
        
        # 基于用户消息内容生成合适的备用响应
        user_content = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_content = msg.get("content", "")
                break
        
        # 智能备用响应
        if "天气" in user_content:
            return "收到天气信息，请注意天气变化。"
        elif "节日" in user_content or "节气" in user_content:
            return "节日快乐，祝您身体健康！"
        elif "预警" in user_content or "警报" in user_content:
            return "收到重要提醒，请注意查看。"
        else:
            return "收到消息，请注意查看相关信息。"
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_calls": self.call_count,
            "is_warmed_up": self.is_warmed_up,
            "max_retry_attempts": self.max_retry_attempts,
            "retry_interval": self.retry_interval,
            "enable_fallback": self.enable_fallback
        }

# 使用示例
def wrap_llm_instance(llm_instance, config=None):
    """包装LLM实例"""
    return RobustLLMWrapper(llm_instance, config)

if __name__ == "__main__":
    print("🛡️ 稳健LLM包装器")
    print("基于实际测试结果优化的LLM调用策略")
    print("解决前3次调用失败，第4次开始正常的问题")

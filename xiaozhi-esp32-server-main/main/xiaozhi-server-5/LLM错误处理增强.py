#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM错误处理增强补丁
确保LLM错误不会被发送给用户
"""

import logging
import time
from typing import List, Dict, Any

logger = logging.getLogger('LLM错误处理')

def safe_llm_call_with_content_filter(llm_instance, messages: List[Dict], max_attempts: int = 3) -> str:
    """安全的LLM调用，带内容过滤"""
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.debug(f"🔄 LLM调用尝试 {attempt}/{max_attempts}")
            
            response = llm_instance.chat(messages)
            
            if response and len(response.strip()) > 0:
                response_text = response.strip()
                
                # 关键：检查响应是否包含错误信息
                if _contains_error_content(response_text):
                    logger.warning(f"⚠️ LLM返回错误内容 (第{attempt}次): {response_text[:50]}...")
                    if attempt < max_attempts:
                        time.sleep(2)
                        continue
                    else:
                        logger.error("❌ 多次尝试后仍返回错误，使用安全内容")
                        return _get_safe_response(messages)
                
                # 正常响应
                logger.debug(f"✅ LLM调用成功 (第{attempt}次)")
                return response_text
            else:
                if attempt < max_attempts:
                    logger.warning(f"⚠️ LLM返回空 (第{attempt}次)，重试...")
                    time.sleep(1)
                    continue
                else:
                    return _get_safe_response(messages)
                    
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ LLM调用异常 (第{attempt}次): {error_msg}")
            
            if attempt < max_attempts:
                time.sleep(2)
                continue
            else:
                return _get_safe_response(messages)
    
    return _get_safe_response(messages)

def _contains_error_content(content: str) -> bool:
    """检查内容是否包含错误信息"""
    error_indicators = [
        "OpenAI服务响应异常",
        "Error code:",
        "MissingParameter", 
        "invalid_request_error",
        "API返回错误",
        "服务暂时不可用"
    ]
    
    for indicator in error_indicators:
        if indicator in content:
            return True
    
    return False

def _get_safe_response(messages: List[Dict]) -> str:
    """获取安全的响应内容"""
    # 分析用户消息内容，提供相应的安全响应
    user_content = ""
    for msg in messages:
        if msg.get("role") == "user":
            user_content = msg.get("content", "")
            break
    
    if "天气" in user_content:
        return "收到天气信息，请关注天气变化。"
    elif "节日" in user_content or "节气" in user_content:
        return "节日快乐，祝您身体健康！"
    elif "问候" in user_content:
        return "您好，祝您生活愉快！"
    else:
        return "消息已收到，谢谢您的关注。"

# 使用示例:
# safe_response = safe_llm_call_with_content_filter(llm_instance, messages)

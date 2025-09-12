#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立即修复脚本 - 防止错误内容被播放
可以直接在现有代码中调用
"""

def emergency_content_filter(content):
    """紧急内容过滤函数 - 可以直接插入现有代码"""
    if not content:
        return "消息已收到，请稍候。"
    
    content_str = str(content).strip()
    
    # 检查错误模式
    error_patterns = [
        "OpenAI服务响应异常",
        "Error code:",
        "MissingParameter",
        "invalid_request_error"
    ]
    
    for pattern in error_patterns:
        if pattern in content_str:
            print(f"🛡️ 过滤错误内容: {content_str[:30]}...")
            return get_friendly_message(content_str)
    
    # 检查长度 (错误信息通常很长)
    if len(content_str) > 150 and ("错误" in content_str or "异常" in content_str or "Error" in content_str):
        print(f"🛡️ 过滤长错误内容: {len(content_str)}字符")
        return get_friendly_message(content_str)
    
    return content_str

def get_friendly_message(original_content=""):
    """获取友好消息"""
    if "天气" in original_content:
        return "收到天气信息，请关注天气变化。"
    elif "节日" in original_content:
        return "节日快乐，祝您身体健康！"
    else:
        return "消息已收到，谢谢您的关注。"

# 立即使用方法：
# 在任何发送到TTS的地方，用这个函数包装内容：
# filtered_content = emergency_content_filter(original_content)
# tts_provider.text_to_speak(filtered_content, audio_file)

print("🛡️ 紧急内容过滤器已加载，可直接调用 emergency_content_filter(content)")

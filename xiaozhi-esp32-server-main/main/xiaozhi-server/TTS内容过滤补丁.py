
# TTS内容过滤补丁 - 插入到TTS调用前
import re

class EmergencyErrorContentFilter:
    """紧急错误内容过滤器"""
    
    def __init__(self):
        self.error_patterns = [
            r'OpenAI服务响应异常.*',
            r'Error code:.*',
            r'MissingParameter.*',
            r'invalid_request_error.*',
            r'【.*异常.*】',
            r'HTTP.*错误.*',
            r'API.*失败.*',
            r'连接.*超时.*'
        ]
        
        self.friendly_responses = [
            "收到您的消息，正在为您准备回复。",
            "消息已收到，请稍候。", 
            "正在处理您的请求，请稍等片刻。",
            "收到通知，请注意查看相关信息。"
        ]
    
    def is_error_content(self, content: str) -> bool:
        """检查内容是否为错误信息"""
        if not content:
            return False
            
        content = str(content).strip()
        
        # 检查错误模式
        for pattern in self.error_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
                
        # 检查长度异常 (错误信息通常很长)
        if len(content) > 200 and ("异常" in content or "错误" in content or "Error" in content):
            return True
            
        return False
    
    def get_friendly_replacement(self, original_content: str = "") -> str:
        """获取友好的替代内容"""
        import random
        
        # 根据原内容类型选择合适的回复
        if "天气" in original_content:
            return "收到天气信息，请注意天气变化。"
        elif "节日" in original_content or "节气" in original_content:
            return "节日快乐，祝您身体健康！"
        elif "问候" in original_content:
            return "您好，祝您生活愉快！"
        else:
            return random.choice(self.friendly_responses)

def filter_tts_content(content: str) -> str:
    """过滤TTS内容，防止错误信息被播放"""
    content_filter = EmergencyErrorContentFilter()
    
    if content_filter.is_error_content(content):
        friendly_content = content_filter.get_friendly_replacement(content)
        print(f"🛡️ TTS内容已过滤: {content[:30]}... → {friendly_content}")
        return friendly_content
    
    return content

# 在任何TTS调用前使用:
# filtered_content = filter_tts_content(original_content)
# tts_result = tts_provider.text_to_speak(filtered_content, audio_file)

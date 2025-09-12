import httpx
import openai
from openai.types import CompletionUsage
from config.logger import setup_logging
from core.utils.util import check_model_key
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        if "base_url" in config:
            self.base_url = config.get("base_url")
        else:
            self.base_url = config.get("url")
        # 增加timeout的配置项，单位为秒
        timeout = config.get("timeout", 300)
        self.timeout = int(timeout) if timeout else 300

        param_defaults = {
            "max_tokens": (500, int),
            "temperature": (0.7, lambda x: round(float(x), 1)),
            "top_p": (1.0, lambda x: round(float(x), 1)),
            "frequency_penalty": (0, lambda x: round(float(x), 1)),
        }

        for param, (default, converter) in param_defaults.items():
            value = config.get(param)
            try:
                setattr(
                    self,
                    param,
                    converter(value) if value not in (None, "") else default,
                )
            except (ValueError, TypeError):
                setattr(self, param, default)

        logger.debug(
            f"意图识别参数初始化: {self.temperature}, {self.max_tokens}, {self.top_p}, {self.frequency_penalty}"
        )

        model_key_msg = check_model_key("LLM", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
        # 全面设置UTF-8编码环境，确保LLM API调用正常工作
        import locale
        import os
        import sys
        
        # 设置多个环境变量确保UTF-8编码
        encoding_vars = {
            'PYTHONIOENCODING': 'utf-8',
            'LANG': 'en_US.UTF-8',
            'LC_ALL': 'en_US.UTF-8',
            'LC_CTYPE': 'en_US.UTF-8'
        }
        
        for var, value in encoding_vars.items():
            os.environ[var] = value
        
        # 设置Python默认编码
        if hasattr(sys, 'setdefaultencoding'):
            sys.setdefaultencoding('utf-8')
        
        # 尝试设置locale，多个fallback选项
        locale_options = ['en_US.UTF-8', 'C.UTF-8', 'en_US', 'C']
        for loc in locale_options:
            try:
                locale.setlocale(locale.LC_ALL, loc)
                logger.bind(tag=TAG).debug(f"成功设置locale: {loc}")
                break
            except:
                continue
        else:
            logger.bind(tag=TAG).warning("无法设置任何UTF-8 locale，可能影响中文处理")
        
        self.client = openai.OpenAI(
            api_key=self.api_key, 
            base_url=self.base_url, 
            timeout=httpx.Timeout(self.timeout)
        )

    def response(self, session_id, dialogue, **kwargs):
        try:
            # 全面清理消息内容，确保UTF-8编码和ASCII兼容性
            safe_dialogue = []
            for msg in dialogue:
                safe_msg = {}
                for key, value in msg.items():
                    if isinstance(value, str):
                        try:
                            # 多层编码保护
                            cleaned_value = value
                            
                            # 第一步：确保是有效的UTF-8
                            cleaned_value = cleaned_value.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
                            
                            # 第二步：移除或替换可能导致问题的控制字符
                            cleaned_value = ''.join(char for char in cleaned_value 
                                                   if char.isprintable() or char.isspace())
                            
                            # 第三步：如果仍有问题，进行ASCII清理（保留中文）
                            if any(ord(char) > 127 for char in cleaned_value):
                                # 确保中文字符正确编码
                                try:
                                    cleaned_value.encode('ascii')
                                except UnicodeEncodeError:
                                    # 中文字符正常，保持原样
                                    pass
                            
                            safe_msg[key] = cleaned_value
                            
                        except Exception:
                            # 如果所有方法都失败，使用安全fallback
                            safe_msg[key] = str(value).encode('ascii', 'ignore').decode('ascii')
                    else:
                        safe_msg[key] = value
                safe_dialogue.append(safe_msg)
            
            responses = self.client.chat.completions.create(
                model=self.model_name,
                messages=safe_dialogue,
                stream=True,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                top_p=kwargs.get("top_p", self.top_p),
                frequency_penalty=kwargs.get(
                    "frequency_penalty", self.frequency_penalty
                ),
            )

            is_active = True
            for chunk in responses:
                try:
                    # 检查是否存在有效的choice且content不为空
                    delta = (
                        chunk.choices[0].delta
                        if getattr(chunk, "choices", None)
                        else None
                    )
                    content = delta.content if hasattr(delta, "content") else ""
                except IndexError:
                    content = ""
                if content:
                    # 处理标签跨多个chunk的情况
                    if "<think>" in content:
                        is_active = False
                        content = content.split("<think>")[0]
                    if "</think>" in content:
                        is_active = True
                        content = content.split("</think>")[-1]
                    if is_active:
                        yield content

        except Exception as e:
            # 全面安全处理异常信息中的中文字符，避免ASCII编码错误
            try:
                # 尝试多种方式安全处理错误信息
                if hasattr(e, 'args') and e.args:
                    # 处理异常参数中的编码问题
                    safe_args = []
                    for arg in e.args:
                        if isinstance(arg, str):
                            safe_arg = arg.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
                        else:
                            safe_arg = str(arg).encode('utf-8', 'ignore').decode('utf-8', 'ignore')
                        safe_args.append(safe_arg)
                    error_msg = ' '.join(safe_args)
                else:
                    error_msg = str(e).encode('utf-8', 'ignore').decode('utf-8', 'ignore')
                
                # 移除可能导致编码问题的特殊字符
                error_msg = ''.join(char for char in error_msg if ord(char) < 127 or char.isalnum())
                
                # 限制错误信息长度，避免过长的消息
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                    
            except Exception:
                error_msg = "Unknown encoding error in LLM response"
            
            logger.bind(tag=TAG).error(f"Error in response generation: {error_msg}")

    def response_with_functions(self, session_id, dialogue, functions=None):
        try:
            # 全面清理消息内容，确保UTF-8编码和ASCII兼容性
            safe_dialogue = []
            for msg in dialogue:
                safe_msg = {}
                for key, value in msg.items():
                    if isinstance(value, str):
                        try:
                            # 确保是有效的UTF-8
                            cleaned_value = value.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
                            # 移除可能导致问题的控制字符
                            cleaned_value = ''.join(char for char in cleaned_value 
                                                   if char.isprintable() or char.isspace())
                            safe_msg[key] = cleaned_value
                        except Exception:
                            # 如果所有方法都失败，使用安全fallback
                            safe_msg[key] = str(value).encode('ascii', 'ignore').decode('ascii')
                    else:
                        safe_msg[key] = value
                safe_dialogue.append(safe_msg)
            
            stream = self.client.chat.completions.create(
                model=self.model_name, messages=safe_dialogue, stream=True, tools=functions
            )

            for chunk in stream:
                # 检查是否存在有效的choice且content不为空
                if getattr(chunk, "choices", None):
                    content = chunk.choices[0].delta.content
                    tool_calls = chunk.choices[0].delta.tool_calls
                    
                    # 安全处理返回的内容
                    if content:
                        try:
                            safe_content = content.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
                        except:
                            safe_content = str(content).encode('ascii', 'ignore').decode('ascii')
                    else:
                        safe_content = content
                    
                    yield safe_content, tool_calls
                    
                # 存在 CompletionUsage 消息时，生成 Token 消耗 log
                elif isinstance(getattr(chunk, "usage", None), CompletionUsage):
                    usage_info = getattr(chunk, "usage", None)
                    logger.bind(tag=TAG).info(
                        f"Token 消耗：输入 {getattr(usage_info, 'prompt_tokens', '未知')}，"
                        f"输出 {getattr(usage_info, 'completion_tokens', '未知')}，"
                        f"共计 {getattr(usage_info, 'total_tokens', '未知')}"
                    )

        except Exception as e:
            # 全面安全处理异常信息中的中文字符，避免ASCII编码错误
            try:
                if hasattr(e, 'args') and e.args:
                    # 处理异常参数中的编码问题
                    safe_args = []
                    for arg in e.args:
                        if isinstance(arg, str):
                            safe_arg = arg.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
                        else:
                            safe_arg = str(arg).encode('utf-8', 'ignore').decode('utf-8', 'ignore')
                        safe_args.append(safe_arg)
                    error_msg = ' '.join(safe_args)
                else:
                    error_msg = str(e).encode('utf-8', 'ignore').decode('utf-8', 'ignore')
                
                # 移除可能导致编码问题的特殊字符
                error_msg = ''.join(char for char in error_msg if ord(char) < 127 or char.isalnum())
                
                # 限制错误信息长度
                if len(error_msg) > 100:
                    error_msg = error_msg[:100] + "..."
                    
            except Exception:
                error_msg = "Unknown encoding error in function call"
            
            logger.bind(tag=TAG).error(f"Error in function call streaming: {error_msg}")
            yield f"【OpenAI服务响应异常: {error_msg}】", None

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码辅助工具
确保整个应用程序使用正确的UTF-8编码
"""

import os
import sys
import locale
import warnings

def setup_utf8_environment():
    """
    设置应用程序的UTF-8编码环境
    应在应用程序启动时调用
    """
    
    # 设置环境变量
    encoding_vars = {
        'PYTHONIOENCODING': 'utf-8',
        'LANG': 'en_US.UTF-8', 
        'LC_ALL': 'en_US.UTF-8',
        'LC_CTYPE': 'en_US.UTF-8',
        'PYTHONLEGACYWINDOWSSTDIO': '0'  # Windows兼容
    }
    
    for var, value in encoding_vars.items():
        os.environ[var] = value
    
    # 设置Python默认编码
    if hasattr(sys, 'setdefaultencoding'):
        sys.setdefaultencoding('utf-8')
    
    # 设置stdout/stderr编码
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
            sys.stderr.reconfigure(encoding='utf-8', errors='ignore')
        except:
            pass
    
    # 设置locale
    locale_options = ['en_US.UTF-8', 'C.UTF-8', 'en_US', 'C']
    for loc in locale_options:
        try:
            locale.setlocale(locale.LC_ALL, loc)
            print(f"✅ 成功设置locale: {loc}")
            break
        except:
            continue
    else:
        warnings.warn("⚠️ 无法设置UTF-8 locale，可能影响中文处理")

def safe_encode_string(text, fallback="<encoding error>"):
    """
    安全编码字符串，避免ASCII错误
    
    Args:
        text: 要编码的文本
        fallback: 编码失败时的fallback文本
    
    Returns:
        安全编码后的字符串
    """
    if not isinstance(text, str):
        text = str(text)
    
    try:
        # 第一步：UTF-8编码清理
        cleaned = text.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
        
        # 第二步：移除控制字符
        cleaned = ''.join(char for char in cleaned 
                         if char.isprintable() or char.isspace())
        
        # 第三步：验证结果
        cleaned.encode('utf-8')
        return cleaned
        
    except Exception:
        return fallback

def safe_encode_dict(data):
    """
    安全编码字典中的所有字符串值
    
    Args:
        data: 要处理的字典
    
    Returns:
        编码安全的字典
    """
    if not isinstance(data, dict):
        return data
    
    safe_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            safe_data[key] = safe_encode_string(value)
        elif isinstance(value, dict):
            safe_data[key] = safe_encode_dict(value)
        elif isinstance(value, list):
            safe_data[key] = [safe_encode_string(item) if isinstance(item, str) 
                             else item for item in value]
        else:
            safe_data[key] = value
    
    return safe_data

def get_encoding_info():
    """
    获取当前编码环境信息
    
    Returns:
        编码信息字典
    """
    info = {
        'default_encoding': sys.getdefaultencoding(),
        'filesystem_encoding': sys.getfilesystemencoding(),
        'stdout_encoding': getattr(sys.stdout, 'encoding', 'unknown'),
        'stderr_encoding': getattr(sys.stderr, 'encoding', 'unknown'),
        'locale': locale.getlocale(),
        'preferred_encoding': locale.getpreferredencoding(),
        'environment': {
            'PYTHONIOENCODING': os.environ.get('PYTHONIOENCODING'),
            'LANG': os.environ.get('LANG'),
            'LC_ALL': os.environ.get('LC_ALL'),
        }
    }
    
    return info

if __name__ == "__main__":
    # 测试编码设置
    print("🔧 测试UTF-8编码设置...")
    
    setup_utf8_environment()
    
    print("\n📊 编码环境信息:")
    info = get_encoding_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\n🧪 测试中文字符处理:")
    test_strings = [
        "今天吃药了吗？",
        "李叔，记得按时吃降压药哦！",
        "Hello, 世界!",
        "测试ASCII和中文混合：Test 123 测试"
    ]
    
    for test_str in test_strings:
        safe_str = safe_encode_string(test_str)
        print(f"  原文: {test_str}")
        print(f"  安全: {safe_str}")
        print(f"  长度: {len(safe_str)} 字符")
        print()

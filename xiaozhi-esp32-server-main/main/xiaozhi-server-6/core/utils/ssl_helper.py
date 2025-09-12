#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSL辅助工具
为HTTPS请求提供SSL配置，解决证书验证问题
"""

import ssl
import aiohttp
from typing import Optional

def create_ssl_context(verify_ssl: bool = False) -> ssl.SSLContext:
    """
    创建SSL上下文
    
    Args:
        verify_ssl: 是否验证SSL证书，默认False（跳过验证）
        
    Returns:
        SSL上下文对象
    """
    ssl_context = ssl.create_default_context()
    
    if not verify_ssl:
        # 跳过SSL证书验证，解决证书问题
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    
    return ssl_context

def create_http_connector(verify_ssl: bool = False) -> aiohttp.TCPConnector:
    """
    创建HTTP连接器
    
    Args:
        verify_ssl: 是否验证SSL证书，默认False（跳过验证）
        
    Returns:
        TCP连接器对象
    """
    ssl_context = create_ssl_context(verify_ssl)
    return aiohttp.TCPConnector(ssl=ssl_context)

def create_secure_session(verify_ssl: bool = False) -> aiohttp.ClientSession:
    """
    创建安全的HTTP会话
    
    Args:
        verify_ssl: 是否验证SSL证书，默认False（跳过验证）
        
    Returns:
        HTTP客户端会话对象
    """
    connector = create_http_connector(verify_ssl)
    return aiohttp.ClientSession(connector=connector)

# 为了向后兼容，提供简化的函数
def get_secure_session(verify_ssl: bool = False) -> aiohttp.ClientSession:
    """
    获取安全的HTTP会话（简化函数）
    
    Args:
        verify_ssl: 是否验证SSL证书，默认False（跳过验证）
        
    Returns:
        HTTP客户端会话对象
    """
    return create_secure_session(verify_ssl)

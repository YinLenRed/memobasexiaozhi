#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复LLM配置MissingParameter错误
诊断和修复DeepSeek API调用问题
"""

import yaml
import json
import logging
import sys
import os
from typing import Dict, Any, Optional

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('LLM配置修复')

def load_current_config() -> Dict[str, Any]:
    """加载当前配置"""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info("✅ 配置文件加载成功")
        return config
    except Exception as e:
        logger.error(f"❌ 配置文件加载失败: {e}")
        return {}

def test_deepseek_api_direct():
    """直接测试DeepSeek API调用"""
    logger.info("🧪 直接测试DeepSeek API")
    
    try:
        import requests
        import time
        
        # 当前配置
        api_key = "ba769173-7dc6-43c5-b402-c1d08606e242"
        base_url = "https://ark.cn-beijing.volces.com/api/v3"
        model_name = "deepseek-v3-250324"
        
        # 测试请求
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "你好，请说一句话测试"}
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }
        
        logger.info(f"📤 发送请求到: {base_url}/chat/completions")
        logger.info(f"   模型: {model_name}")
        logger.info(f"   API密钥: {api_key[:20]}...")
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        logger.info(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "无内容")
            logger.info(f"✅ API调用成功!")
            logger.info(f"   响应内容: {content}")
            return True
        else:
            error_detail = response.text
            logger.error(f"❌ API调用失败: {response.status_code}")
            logger.error(f"   错误详情: {error_detail}")
            
            # 分析具体错误
            if "MissingParameter" in error_detail:
                logger.error("🔍 MissingParameter错误分析:")
                logger.error("   可能原因: 请求缺少必要参数")
            elif "invalid_request_error" in error_detail:
                logger.error("🔍 Invalid request错误:")
                logger.error("   可能原因: API密钥无效或模型名称错误")
            elif "authentication" in error_detail.lower():
                logger.error("🔍 认证错误:")
                logger.error("   可能原因: API密钥无效或过期")
            
            return False
            
    except Exception as e:
        logger.error(f"❌ API测试异常: {e}")
        return False

def try_alternative_configs():
    """尝试替代配置"""
    logger.info("🔧 尝试替代配置")
    
    # 替代配置列表
    alternatives = [
        {
            "name": "DeepSeek官方API",
            "api_key": "ba769173-7dc6-43c5-b402-c1d08606e242",
            "base_url": "https://api.deepseek.com/v1",
            "model_name": "deepseek-chat"
        },
        {
            "name": "火山引擎标准格式",
            "api_key": "ba769173-7dc6-43c5-b402-c1d08606e242", 
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "model_name": "deepseek-chat"  # 尝试标准模型名
        },
        {
            "name": "兼容模式测试",
            "api_key": "ba769173-7dc6-43c5-b402-c1d08606e242",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "model_name": "gpt-3.5-turbo"  # 使用通用模型名
        }
    ]
    
    for alt in alternatives:
        logger.info(f"🧪 测试配置: {alt['name']}")
        
        try:
            import requests
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {alt['api_key']}"
            }
            
            payload = {
                "model": alt['model_name'],
                "messages": [{"role": "user", "content": "测试"}],
                "max_tokens": 20,
                "temperature": 0.7
            }
            
            response = requests.post(
                f"{alt['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                logger.info(f"✅ {alt['name']} 配置工作正常!")
                return alt
            else:
                logger.warning(f"❌ {alt['name']} 失败: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"❌ {alt['name']} 异常: {e}")
    
    return None

def create_fixed_config(working_config: Dict[str, Any]):
    """创建修复后的配置"""
    logger.info("📝 创建修复后的配置")
    
    # 加载当前配置
    config = load_current_config()
    if not config:
        return
    
    # 更新LLM配置
    if "LLM" in config and "ChatGLMLLM" in config["LLM"]:
        config["LLM"]["ChatGLMLLM"].update({
            "api_key": working_config["api_key"],
            "base_url": working_config["base_url"], 
            "model_name": working_config["model_name"],
            "type": "openai"
        })
        
        # 备份原配置
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = f"config_backup_llm_fix_{timestamp}.yaml"
        
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, ensure_ascii=False, default_flow_style=False)
            logger.info(f"💾 原配置已备份到: {backup_file}")
        except Exception as e:
            logger.warning(f"⚠️ 配置备份失败: {e}")
        
        # 写入新配置
        try:
            with open('config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(config, f, ensure_ascii=False, default_flow_style=False)
            
            logger.info("✅ 配置更新成功!")
            logger.info("📋 新的LLM配置:")
            logger.info(f"   API密钥: {working_config['api_key'][:20]}...")
            logger.info(f"   基础URL: {working_config['base_url']}")
            logger.info(f"   模型名称: {working_config['model_name']}")
            
        except Exception as e:
            logger.error(f"❌ 配置写入失败: {e}")

def test_local_llm_call():
    """测试本地LLM调用"""
    logger.info("🧪 测试本地LLM调用")
    
    try:
        from config.config_loader import load_config
        from core.utils import llm as llm_utils
        
        # 重新加载配置
        config = load_config()
        
        # 获取LLM配置
        llm_config = config.get("LLM", {})
        selected_llm = config.get("selected_module", {}).get("LLM", "ChatGLMLLM")
        
        if selected_llm not in llm_config:
            logger.error(f"❌ 未找到LLM配置: {selected_llm}")
            return False
        
        # 创建LLM实例
        llm_type = llm_config[selected_llm].get("type", selected_llm)
        llm_instance = llm_utils.create_instance(llm_type, llm_config[selected_llm])
        
        # 测试调用
        test_messages = [
            {"role": "user", "content": "你好，请简单回复一句话测试"}
        ]
        
        logger.info("📤 测试LLM调用...")
        response = llm_instance.chat(test_messages)
        
        if response and len(response.strip()) > 0:
            logger.info(f"✅ LLM调用成功!")
            logger.info(f"   响应: {response}")
            return True
        else:
            logger.error("❌ LLM返回空响应")
            return False
            
    except Exception as e:
        logger.error(f"❌ 本地LLM调用失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    logger.info("🔧 LLM配置MissingParameter错误修复工具")
    logger.info("="*50)
    
    # 1. 测试当前配置
    logger.info("🔍 步骤1: 测试当前DeepSeek配置")
    current_works = test_deepseek_api_direct()
    
    if current_works:
        logger.info("✅ 当前配置正常，问题可能在别处")
        logger.info("💡 建议检查:")
        logger.info("   1. LLM调用的参数传递")
        logger.info("   2. 异步调用的错误处理")
        logger.info("   3. 网络连接稳定性")
    else:
        # 2. 尝试替代配置
        logger.info("🔍 步骤2: 尝试替代配置")
        working_config = try_alternative_configs()
        
        if working_config:
            logger.info(f"✅ 找到可用配置: {working_config['name']}")
            
            # 3. 更新配置文件
            logger.info("🔍 步骤3: 更新配置文件")
            create_fixed_config(working_config)
            
            # 4. 测试本地调用
            logger.info("🔍 步骤4: 测试修复后的本地调用")
            if test_local_llm_call():
                logger.info("🎉 LLM配置修复成功!")
                logger.info("💡 请重启Python服务以使配置生效")
            else:
                logger.error("❌ 本地调用仍有问题，需要进一步检查")
        else:
            logger.error("❌ 所有配置都失败")
            logger.info("💡 建议:")
            logger.info("   1. 检查API密钥是否有效")
            logger.info("   2. 联系DeepSeek支持")
            logger.info("   3. 暂时切换到其他LLM提供商")

if __name__ == "__main__":
    main()

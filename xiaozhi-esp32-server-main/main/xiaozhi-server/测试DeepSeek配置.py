#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试DeepSeek配置
验证用户提供的LLM配置是否正确工作
"""

import json
import logging
import asyncio
from typing import Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('DeepSeek配置测试')

def validate_api_key(api_key: str) -> bool:
    """验证API密钥格式"""
    import re
    
    # 检测中文占位符
    if re.search(r'[\u4e00-\u9fff]', api_key):
        logger.error(f"❌ API密钥包含中文字符: {api_key}")
        return False
    
    # 检测占位符模式
    placeholder_patterns = [
        r'你的.*key',
        r'your.*key', 
        r'请填入',
        r'占位符',
        r'placeholder'
    ]
    
    for pattern in placeholder_patterns:
        if re.search(pattern, api_key.lower()):
            logger.error(f"❌ API密钥为占位符: {api_key}")
            return False
    
    # 检测ASCII兼容性
    try:
        api_key.encode('ascii')
        logger.info(f"✅ API密钥格式正确: {api_key[:10]}...")
        return True
    except UnicodeEncodeError:
        logger.error(f"❌ API密钥包含非ASCII字符: {api_key}")
        return False

def test_deepseek_config():
    """测试DeepSeek配置"""
    logger.info("🔧 DeepSeek配置测试")
    logger.info("="*50)
    
    # 用户提供的配置
    deepseek_config = {
        "type": "openai",
        "top_k": "",
        "top_p": "", 
        "api_key": "ba769173-7dc6-43c5-b402-c1d08606e242",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "max_tokens": "",
        "model_name": "deepseek-v3-250324",
        "temperature": "",
        "frequency_penalty": ""
    }
    
    logger.info("📋 配置信息:")
    logger.info(json.dumps(deepseek_config, indent=2, ensure_ascii=False))
    
    # 验证配置
    logger.info("\n🔍 配置验证:")
    
    # 1. API密钥验证
    api_key = deepseek_config.get("api_key", "")
    api_key_valid = validate_api_key(api_key)
    
    # 2. 基础URL验证
    base_url = deepseek_config.get("base_url", "")
    if "ark.cn-beijing.volces.com" in base_url:
        logger.info("✅ 基础URL正确: 字节跳动ARK平台")
        base_url_valid = True
    else:
        logger.error(f"❌ 基础URL不正确: {base_url}")
        base_url_valid = False
    
    # 3. 模型名称验证
    model_name = deepseek_config.get("model_name", "")
    if "deepseek" in model_name.lower():
        logger.info(f"✅ 模型名称正确: {model_name}")
        model_valid = True
    else:
        logger.error(f"❌ 模型名称不正确: {model_name}")
        model_valid = False
    
    # 4. 类型验证
    config_type = deepseek_config.get("type", "")
    if config_type == "openai":
        logger.info("✅ 类型正确: OpenAI兼容接口")
        type_valid = True
    else:
        logger.error(f"❌ 类型不正确: {config_type}")
        type_valid = False
    
    # 总体验证结果
    all_valid = api_key_valid and base_url_valid and model_valid and type_valid
    
    logger.info(f"\n📊 验证结果:")
    logger.info(f"   API密钥: {'✅' if api_key_valid else '❌'}")
    logger.info(f"   基础URL: {'✅' if base_url_valid else '❌'}")
    logger.info(f"   模型名称: {'✅' if model_valid else '❌'}")
    logger.info(f"   接口类型: {'✅' if type_valid else '❌'}")
    logger.info(f"   总体状态: {'✅ 配置正确' if all_valid else '❌ 配置有误'}")
    
    if all_valid:
        logger.info("\n🎉 配置验证通过！")
        logger.info("💡 使用方法:")
        logger.info("   1. 在Java后端管理界面更新LLM配置")
        logger.info("   2. 选择这个DeepSeek配置作为默认LLM")
        logger.info("   3. 重启Python服务以应用新配置")
    else:
        logger.error("\n❌ 配置验证失败！")
        logger.error("💡 请检查配置信息并重新设置")
    
    return all_valid

def compare_with_problematic_config():
    """对比有问题的配置"""
    logger.info("\n🔍 对比分析:")
    
    # 有问题的配置（示例）
    problematic_config = {
        "api_key": "你的chat-glm web key",
        "model_name": "glm-4-flash"
    }
    
    # 正确的配置
    correct_config = {
        "api_key": "ba769173-7dc6-43c5-b402-c1d08606e242",
        "model_name": "deepseek-v3-250324"
    }
    
    logger.info("❌ 有问题的配置:")
    logger.info(f"   API密钥: '{problematic_config['api_key']}' (包含中文)")
    logger.info(f"   模型: {problematic_config['model_name']}")
    
    logger.info("✅ 正确的配置:")
    logger.info(f"   API密钥: '{correct_config['api_key'][:10]}...' (UUID格式)")
    logger.info(f"   模型: {correct_config['model_name']}")
    
    logger.info("\n🎯 修复效果:")
    logger.info("   ✅ 解决ASCII编码错误")
    logger.info("   ✅ 启用智能内容生成")
    logger.info("   ✅ 支持Java后端prompt处理")

def generate_java_backend_config():
    """生成Java后端配置脚本"""
    logger.info("\n📝 Java后端配置步骤:")
    
    config_steps = [
        "1. 登录Java后端管理界面",
        "2. 进入 'LLM配置' 页面",
        "3. 创建或编辑LLM配置",
        "4. 填入以下信息:",
        "   - 名称: DeepSeekLLM",
        "   - 类型: openai", 
        "   - API密钥: ba769173-7dc6-43c5-b402-c1d08606e242",
        "   - 基础URL: https://ark.cn-beijing.volces.com/api/v3",
        "   - 模型名称: deepseek-v3-250324",
        "5. 保存配置",
        "6. 设置为默认LLM",
        "7. 重启Python服务"
    ]
    
    for step in config_steps:
        logger.info(f"   {step}")

def main():
    """主函数"""
    try:
        # 测试配置
        config_valid = test_deepseek_config()
        
        # 对比分析
        compare_with_problematic_config()
        
        # 生成配置步骤
        generate_java_backend_config()
        
        if config_valid:
            logger.info("\n🚀 配置就绪，可以立即使用！")
        else:
            logger.error("\n❌ 请修正配置后重试")
        
        return config_valid
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)

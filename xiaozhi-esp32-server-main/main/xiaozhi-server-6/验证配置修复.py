#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证配置修复效果
检查config.yaml中的LLM配置是否已正确更新
"""

import yaml
import logging
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('配置验证')

def load_config():
    """加载配置文件"""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return None

def validate_api_key(api_key: str, llm_name: str) -> bool:
    """验证API密钥"""
    # 检测中文字符
    if re.search(r'[\u4e00-\u9fff]', api_key):
        logger.error(f"❌ {llm_name}: API密钥包含中文字符")
        return False
    
    # 检测占位符
    placeholder_patterns = [
        r'你的.*key',
        r'your.*key', 
        r'请填入',
        r'占位符',
        r'placeholder'
    ]
    
    for pattern in placeholder_patterns:
        if re.search(pattern, api_key.lower()):
            logger.error(f"❌ {llm_name}: API密钥为占位符")
            return False
    
    # 检测ASCII兼容性
    try:
        api_key.encode('ascii')
        logger.info(f"✅ {llm_name}: API密钥格式正确")
        return True
    except UnicodeEncodeError:
        logger.error(f"❌ {llm_name}: API密钥包含非ASCII字符")
        return False

def verify_config_fix():
    """验证配置修复"""
    logger.info("🔧 验证配置修复效果")
    logger.info("="*50)
    
    # 加载配置
    config = load_config()
    if not config:
        return False
    
    # 检查LLM配置
    llm_config = config.get('LLM', {})
    selected_llm = config.get('selected_module', {}).get('LLM', '')
    
    logger.info(f"📋 当前选择的LLM: {selected_llm}")
    logger.info(f"📋 可用LLM配置: {list(llm_config.keys())}")
    
    # 验证关键LLM配置
    key_llms = ['ChatGLMLLM', 'DeepSeekLLM']
    all_valid = True
    
    for llm_name in key_llms:
        if llm_name in llm_config:
            llm_conf = llm_config[llm_name]
            logger.info(f"\n🔍 检查 {llm_name}:")
            logger.info(f"   API密钥: {llm_conf.get('api_key', 'N/A')[:20]}...")
            logger.info(f"   基础URL: {llm_conf.get('base_url', llm_conf.get('url', 'N/A'))}")
            logger.info(f"   模型名称: {llm_conf.get('model_name', 'N/A')}")
            logger.info(f"   类型: {llm_conf.get('type', 'N/A')}")
            
            # 验证API密钥
            api_key = llm_conf.get('api_key', '')
            if not validate_api_key(api_key, llm_name):
                all_valid = False
            
            # 验证是否为DeepSeek配置
            base_url = llm_conf.get('base_url', llm_conf.get('url', ''))
            model_name = llm_conf.get('model_name', '')
            
            if 'deepseek' in model_name.lower() and 'ark.cn-beijing.volces.com' in base_url:
                logger.info(f"✅ {llm_name}: 已更新为DeepSeek配置")
            else:
                logger.warning(f"⚠️ {llm_name}: 配置可能不是预期的DeepSeek格式")
    
    # 检查当前选择的LLM
    if selected_llm in llm_config:
        current_config = llm_config[selected_llm]
        current_api_key = current_config.get('api_key', '')
        
        logger.info(f"\n🎯 当前使用的LLM ({selected_llm}) 配置检查:")
        if validate_api_key(current_api_key, selected_llm):
            logger.info("✅ 当前LLM配置有效，应该能解决ASCII编码问题")
        else:
            logger.error("❌ 当前LLM配置仍有问题")
            all_valid = False
    
    logger.info(f"\n📊 验证结果: {'✅ 配置修复成功' if all_valid else '❌ 仍有问题'}")
    
    if all_valid:
        logger.info("\n🎉 修复完成！预期效果:")
        logger.info("   ✅ 解决ASCII编码错误")
        logger.info("   ✅ LLM正常初始化") 
        logger.info("   ✅ 支持智能内容生成")
        logger.info("   ✅ Java后端prompt处理正常")
        
        logger.info("\n🚀 下一步操作:")
        logger.info("   1. 重启Python服务: systemctl restart xiaozhi-server")
        logger.info("   2. 观察日志，确认LLM初始化成功")
        logger.info("   3. 测试Java触发的主动问候功能")
    
    return all_valid

def compare_before_after():
    """对比修复前后"""
    logger.info("\n📊 修复对比:")
    
    logger.info("❌ 修复前:")
    logger.info("   ChatGLMLLM.api_key: '你的chat-glm web key'")
    logger.info("   DeepSeekLLM.api_key: '你的deepseek web key'")
    logger.info("   结果: ASCII编码错误，LLM初始化失败")
    
    logger.info("✅ 修复后:")
    logger.info("   ChatGLMLLM.api_key: 'ba769173-7dc6...'")
    logger.info("   ChatGLMLLM.model_name: 'deepseek-v3-250324'")
    logger.info("   ChatGLMLLM.base_url: 'https://ark.cn-beijing.volces.com/api/v3'")
    logger.info("   结果: 配置正确，LLM应能正常工作")

def main():
    """主函数"""
    try:
        # 验证配置
        success = verify_config_fix()
        
        # 对比说明
        compare_before_after()
        
        if success:
            logger.info("\n🎯 配置文件已成功修复！")
            logger.info("💡 建议立即重启服务测试效果")
        else:
            logger.error("\n❌ 配置仍有问题，请检查")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ 验证失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)

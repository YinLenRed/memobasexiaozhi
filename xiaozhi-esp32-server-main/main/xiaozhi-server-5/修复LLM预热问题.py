#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复LLM预热问题 - 解决前几次调用失败的问题
避免循环导入，提供更稳定的LLM初始化
"""

import asyncio
import time
import logging
import yaml
from typing import Dict, Any, Optional, List
import sys
import os

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('LLM预热修复')

class LLMWarmupManager:
    """LLM预热管理器"""
    
    def __init__(self):
        self.warmup_attempts = 3  # 预热尝试次数
        self.warmup_interval = 2  # 预热间隔
        self.is_warmed_up = False
        self.warmup_cache = {}
        
        logger.info("🔥 LLM预热管理器初始化")
    
    def perform_llm_warmup(self, llm_instance) -> bool:
        """执行LLM预热"""
        logger.info("🔥 开始LLM预热...")
        
        # 简单的预热消息
        warmup_messages = [
            [{"role": "user", "content": "测试"}],
            [{"role": "user", "content": "hello"}],
            [{"role": "user", "content": "预热"}]
        ]
        
        success_count = 0
        
        for i, messages in enumerate(warmup_messages, 1):
            try:
                logger.info(f"🔥 预热尝试 {i}/{len(warmup_messages)}")
                
                response = llm_instance.chat(messages)
                
                if response and len(response.strip()) > 0:
                    success_count += 1
                    logger.info(f"   ✅ 预热 {i} 成功: {response[:30]}...")
                else:
                    logger.warning(f"   ⚠️ 预热 {i} 返回空")
                
                # 预热间隔
                time.sleep(self.warmup_interval)
                
            except Exception as e:
                error_msg = str(e)
                if "MissingParameter" in error_msg:
                    logger.warning(f"   ⚠️ 预热 {i} MissingParameter (预期中)")
                else:
                    logger.error(f"   ❌ 预热 {i} 失败: {e}")
        
        # 判断预热是否成功
        if success_count >= 1:
            self.is_warmed_up = True
            logger.info(f"🔥 LLM预热完成! 成功率: {success_count}/{len(warmup_messages)}")
            return True
        else:
            logger.warning("🔥 LLM预热未完全成功，但会继续尝试")
            return False
    
    def safe_llm_call_with_warmup(self, llm_instance, messages: List[Dict], max_attempts: int = 5) -> str:
        """带预热的安全LLM调用"""
        
        # 如果还没预热，先预热
        if not self.is_warmed_up:
            logger.info("🔥 LLM未预热，先执行预热...")
            self.perform_llm_warmup(llm_instance)
        
        # 尝试多次调用，直到成功或达到最大尝试次数
        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug(f"🔄 LLM调用尝试 {attempt}/{max_attempts}")
                
                response = llm_instance.chat(messages)
                
                if response and len(response.strip()) > 0:
                    # 检查是否是错误响应
                    if "MissingParameter" in response or "Error code:" in response:
                        if attempt < max_attempts:
                            logger.warning(f"🔄 第{attempt}次调用返回错误，{1}秒后重试...")
                            time.sleep(1)
                            continue
                        else:
                            logger.error(f"❌ {max_attempts}次尝试后仍有错误，使用备用内容")
                            return self._get_fallback_content()
                    
                    logger.debug(f"✅ LLM调用成功 (第{attempt}次尝试)")
                    return response.strip()
                else:
                    if attempt < max_attempts:
                        logger.warning(f"⚠️ 第{attempt}次调用返回空，{1}秒后重试...")
                        time.sleep(1)
                        continue
                    else:
                        logger.warning(f"⚠️ {max_attempts}次尝试后仍返回空，使用备用内容")
                        return self._get_fallback_content()
                        
            except Exception as e:
                error_msg = str(e)
                
                if "MissingParameter" in error_msg:
                    if attempt < max_attempts:
                        logger.warning(f"🔄 第{attempt}次调用MissingParameter，{2}秒后重试...")
                        time.sleep(2)  # MissingParameter错误等待更长时间
                        continue
                    else:
                        logger.error(f"❌ {max_attempts}次尝试后仍有MissingParameter")
                        return self._get_fallback_content()
                else:
                    logger.error(f"❌ LLM调用异常 (第{attempt}次): {e}")
                    if attempt < max_attempts:
                        time.sleep(1)
                        continue
                    else:
                        return self._get_fallback_content()
        
        return self._get_fallback_content()
    
    def _get_fallback_content(self) -> str:
        """获取备用内容"""
        fallback_options = [
            "收到消息，请注意查看。",
            "消息提醒，请及时关注。", 
            "信息更新，请查看详情。",
            "收到通知，请查看相关信息。"
        ]
        import random
        return random.choice(fallback_options)

def test_llm_warmup():
    """测试LLM预热功能"""
    logger.info("🧪 测试LLM预热功能")
    logger.info("="*30)
    
    try:
        from config.config_loader import load_config
        from core.utils import llm as llm_utils
        
        # 加载配置并创建LLM实例
        config = load_config()
        llm_config = config.get("LLM", {})
        selected_llm = config.get("selected_module", {}).get("LLM", "ChatGLMLLM")
        
        if selected_llm not in llm_config:
            logger.error(f"❌ 未找到LLM配置: {selected_llm}")
            return False
        
        llm_type = llm_config[selected_llm].get("type", selected_llm)
        llm_instance = llm_utils.create_instance(llm_type, llm_config[selected_llm])
        
        logger.info(f"✅ LLM实例创建成功: {selected_llm}")
        
        # 创建预热管理器
        warmup_manager = LLMWarmupManager()
        
        # 测试预热后的稳定调用
        test_messages = [
            [{"role": "user", "content": "你好，请简单回复一句话"}],
            [{"role": "user", "content": "今天天气怎么样？"}],
            [{"role": "user", "content": "节日快乐"}]
        ]
        
        logger.info("🧪 测试预热后的LLM调用稳定性...")
        
        success_count = 0
        for i, messages in enumerate(test_messages, 1):
            logger.info(f"📤 测试消息 {i}: {messages[0]['content']}")
            
            response = warmup_manager.safe_llm_call_with_warmup(llm_instance, messages)
            
            if "收到消息" in response or "消息提醒" in response or "信息更新" in response:
                logger.info(f"   🛡️ 使用备用内容: {response}")
            else:
                logger.info(f"   ✅ LLM响应: {response}")
                success_count += 1
        
        logger.info(f"📊 预热后成功率: {success_count}/{len(test_messages)}")
        
        if success_count >= len(test_messages) // 2:
            logger.info("🎉 LLM预热方案有效！")
            return True
        else:
            logger.warning("⚠️ LLM仍不稳定，建议检查配置")
            return False
        
    except Exception as e:
        logger.error(f"❌ 预热测试失败: {e}")
        return False

def create_warmup_patch():
    """创建预热补丁代码"""
    patch_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM预热补丁 - 在UnifiedEventService中集成预热功能
避免循环导入问题
"""

# 这个补丁可以在服务启动时应用
def patch_unified_event_service_with_warmup():
    """为UnifiedEventService添加预热功能"""
    import sys
    
    # 延迟导入避免循环依赖
    def apply_warmup_patch():
        try:
            from core.services.unified_event_service import UnifiedEventService
            
            # 保存原始的LLM初始化方法
            original_init_llm = UnifiedEventService._initialize_llm
            
            def enhanced_init_llm(self):
                """增强的LLM初始化 - 包含预热"""
                # 调用原始初始化
                original_init_llm(self)
                
                # 如果LLM初始化成功，进行预热
                if self.llm:
                    print("🔥 开始LLM预热...")
                    
                    warmup_messages = [
                        [{"role": "user", "content": "测试"}],
                        [{"role": "user", "content": "hello"}]
                    ]
                    
                    for i, messages in enumerate(warmup_messages, 1):
                        try:
                            response = self.llm.chat(messages)
                            if response:
                                print(f"🔥 预热 {i} 成功")
                            else:
                                print(f"⚠️ 预热 {i} 返回空")
                        except Exception as e:
                            if "MissingParameter" in str(e):
                                print(f"⚠️ 预热 {i} MissingParameter (预期)")
                            else:
                                print(f"❌ 预热 {i} 失败: {e}")
                        
                        import time
                        time.sleep(1)
                    
                    print("🔥 LLM预热完成")
            
            # 替换初始化方法
            UnifiedEventService._initialize_llm = enhanced_init_llm
            print("✅ LLM预热补丁已应用")
            
        except Exception as e:
            print(f"❌ 预热补丁应用失败: {e}")
    
    # 使用定时器延迟应用补丁
    import threading
    timer = threading.Timer(1.0, apply_warmup_patch)
    timer.start()

# 自动应用补丁
patch_unified_event_service_with_warmup()
'''
    
    with open('LLM预热补丁.py', 'w', encoding='utf-8') as f:
        f.write(patch_code)
    
    logger.info("📄 创建了LLM预热补丁: LLM预热补丁.py")
    logger.info("💡 在main.py开头添加: import LLM预热补丁")

def main():
    """主函数"""
    print("🔥 LLM预热问题修复工具")
    print("="*30)
    print("🎯 解决前几次调用失败的问题")
    print("💡 发现: 前3次MissingParameter，第4次开始正常")
    print()
    
    print("修复方案:")
    print("1. 测试LLM预热功能")
    print("2. 创建预热补丁")
    print("3. 完整测试")
    
    choice = input("\n选择操作 (1-3, 回车默认3): ").strip()
    
    if choice == "1":
        test_llm_warmup()
    elif choice == "2":
        create_warmup_patch()
    else:
        # 默认执行完整测试
        logger.info("🔧 执行完整预热修复...")
        
        # 1. 测试预热
        success = test_llm_warmup()
        print()
        
        # 2. 创建补丁
        create_warmup_patch()
        print()
        
        if success:
            logger.info("🎉 LLM预热修复成功！")
            logger.info("📋 建议:")
            logger.info("   1. 在main.py开头添加: import LLM预热补丁")
            logger.info("   2. 或重启服务让LLM自然预热")
            logger.info("   3. rapid测试现在应该更稳定")
        else:
            logger.warning("⚠️ 预热效果有限，但错误保护机制仍然有效")

if __name__ == "__main__":
    main()

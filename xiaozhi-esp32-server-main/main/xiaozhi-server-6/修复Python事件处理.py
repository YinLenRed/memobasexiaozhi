#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复Python事件处理问题
确保Java发送的事件能正确生成SPEAK命令给硬件
"""

import os
import yaml
import logging
from datetime import datetime
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('修复事件处理')

class EventProcessingFixer:
    """事件处理修复器"""
    
    def __init__(self):
        self.config_file = "config.yaml"
        
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info("✅ 配置文件加载成功")
                return config
        except Exception as e:
            logger.error(f"❌ 加载配置文件失败: {e}")
            return None
    
    def check_llm_config_issue(self, config):
        """检查LLM配置问题"""
        logger.info("🔍 检查LLM配置问题...")
        
        llm_config = config.get('LLM', {})
        
        # 查找ChatGLM配置（从错误信息看是这个有问题）
        chatglm_config = llm_config.get('ChatGLMLLM', {})
        
        if chatglm_config:
            api_key = chatglm_config.get('api_key', '')
            logger.info(f"ChatGLM API密钥: {api_key}")
            
            if '你的chat-glm web key' in api_key:
                logger.error("❌ ChatGLM API密钥未配置，仍是占位符")
                return True, 'ChatGLM API密钥未配置'
            elif ' ' in api_key:
                logger.error("❌ ChatGLM API密钥包含空格，可能导致编码问题")
                return True, 'API密钥包含空格'
        
        return False, None
    
    def check_event_processing_flow(self):
        """检查事件处理流程"""
        logger.info("🔍 检查事件处理流程...")
        
        # 检查关键文件是否存在
        key_files = [
            "core/services/unified_event_service.py",
            "core/mqtt/webhook_callback_handler.py", 
            "core/mqtt/proactive_greeting_service.py"
        ]
        
        missing_files = []
        for file_path in key_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            logger.error(f"❌ 缺少关键文件: {missing_files}")
            return False
        
        logger.info("✅ 关键文件都存在")
        return True
    
    def analyze_problem_root_cause(self):
        """分析问题根本原因"""
        logger.info("🕵️ 分析问题根本原因...")
        
        logger.info("📋 从日志分析得出:")
        logger.info("   1. Java正确发送了事件到Python")
        logger.info("   2. Python收到了事件并开始处理")
        logger.info("   3. Python尝试调用LLM生成内容")
        logger.info("   4. LLM调用失败：Bearer token编码问题")
        logger.info("   5. 系统回退到硬编码模式")
        logger.info("   6. 发送的是'唤醒命令'而不是'SPEAK命令'")
        
        logger.info("\n💡 关键发现:")
        logger.info("   ❌ '唤醒命令' ≠ 'SPEAK命令'")
        logger.info("   ❌ 只有'SPEAK命令'才有音频数据")
        logger.info("   ❌ '唤醒命令'只是唤醒，没有TTS音频")
        
        return {
            'root_cause': 'LLM配置问题导致事件处理回退',
            'symptom': '生成唤醒命令而非SPEAK命令',
            'solution': '修复LLM配置或改进事件处理逻辑'
        }
    
    def create_temp_llm_fix(self):
        """创建临时LLM修复方案"""
        logger.info("🔧 创建临时LLM修复方案...")
        
        # 方案1：修改事件处理逻辑，即使LLM失败也生成SPEAK命令
        event_service_patch = '''
# 临时修复：在unified_event_service.py中
# 当LLM生成失败时，确保仍然生成SPEAK命令而不是唤醒命令

def generate_speak_command_fallback(self, device_id, event_type, data):
    """LLM失败时的SPEAK命令备用生成"""
    
    # 根据事件类型生成基础内容
    fallback_content = {
        'solar_term': f"今天是{data}节气，注意身体健康。",
        'holiday': f"今天是{data}，祝您节日快乐！",
        'weather': f"天气信息：{data}",
        'schedule': f"日程提醒：{data}",
        'default': f"收到消息：{data}"
    }
    
    content = fallback_content.get(event_type, fallback_content['default'])
    
    # 重要：生成SPEAK命令而不是唤醒命令
    track_id = f"FALLBACK_{int(time.time() * 1000)}"
    
    return {
        'cmd': 'SPEAK',  # 关键：必须是SPEAK
        'text': content,
        'track_id': track_id,
        'audio_url': 'ws://47.98.51.180:8000/xiaozhi/v1/',  # 添加音频URL
        'fallback_mode': True
    }
'''
        
        logger.info("📝 临时修复方案:")
        logger.info("   1. 确保即使LLM失败也生成SPEAK命令")
        logger.info("   2. 为SPEAK命令添加音频URL")
        logger.info("   3. 避免回退到硬编码唤醒模式")
        
        return event_service_patch
    
    def suggest_immediate_fixes(self):
        """建议立即修复方案"""
        logger.info("\n" + "="*60)
        logger.info("🔧 立即修复方案建议")
        logger.info("="*60)
        
        logger.info("🎯 问题核心:")
        logger.info("   Java → Python 通信正常")
        logger.info("   Python LLM处理失败")
        logger.info("   回退生成错误的命令类型")
        
        logger.info("\n💡 修复方案（按优先级）:")
        
        logger.info("\n🥇 方案1：修复LLM配置")
        logger.info("   1. 编辑 config.yaml")
        logger.info("   2. 找到 ChatGLMLLM 配置")
        logger.info("   3. 替换 'api_key: 你的chat-glm web key' 为有效密钥")
        logger.info("   4. 或者禁用ChatGLM，使用其他LLM")
        
        logger.info("\n🥈 方案2：修改事件处理逻辑")
        logger.info("   1. 修改 core/services/unified_event_service.py")
        logger.info("   2. 确保LLM失败时生成SPEAK命令")
        logger.info("   3. 添加音频URL到命令中")
        
        logger.info("\n🥉 方案3：临时绕过LLM")
        logger.info("   1. 直接在事件处理中生成固定内容")
        logger.info("   2. 强制使用SPEAK命令")
        logger.info("   3. 确保硬件收到音频数据")
        
        logger.info("\n⚡ 最快修复（推荐）:")
        logger.info("   编辑 config.yaml，禁用有问题的LLM:")
        logger.info("   ```yaml")
        logger.info("   LLM:")
        logger.info("     ChatGLMLLM:")
        logger.info("       enabled: false  # 添加这行")
        logger.info("       api_key: 你的chat-glm web key")
        logger.info("   ```")
    
    def generate_config_fix(self):
        """生成配置修复方案"""
        logger.info("📝 生成配置修复...")
        
        config = self.load_config()
        if not config:
            return False
        
        # 检查当前LLM配置
        llm_config = config.get('LLM', {})
        
        # 找出有问题的LLM
        problematic_llms = []
        for llm_name, llm_settings in llm_config.items():
            api_key = llm_settings.get('api_key', '')
            if isinstance(api_key, str) and ('你的' in api_key or api_key == ''):
                problematic_llms.append(llm_name)
        
        if problematic_llms:
            logger.info(f"\n🔧 建议禁用以下LLM:")
            
            fixed_config = config.copy()
            for llm_name in problematic_llms:
                if llm_name in fixed_config['LLM']:
                    fixed_config['LLM'][llm_name]['enabled'] = False
                    logger.info(f"   - {llm_name}: 已标记为禁用")
            
            # 保存修复后的配置
            backup_file = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
            try:
                import shutil
                shutil.copy2(self.config_file, backup_file)
                logger.info(f"✅ 原配置已备份到: {backup_file}")
                
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(fixed_config, f, default_flow_style=False, allow_unicode=True, indent=2)
                
                logger.info("✅ 修复配置已保存")
                return True
                
            except Exception as e:
                logger.error(f"❌ 保存配置失败: {e}")
                return False
        
        return True
    
    def run_analysis(self):
        """运行完整分析"""
        logger.info("🔍 Python事件处理问题分析")
        logger.info("="*50)
        
        try:
            # 1. 加载和检查配置
            config = self.load_config()
            if not config:
                return False
            
            # 2. 检查LLM配置问题
            has_llm_issue, issue_desc = self.check_llm_config_issue(config)
            
            # 3. 检查事件处理流程
            self.check_event_processing_flow()
            
            # 4. 分析根本原因
            analysis = self.analyze_problem_root_cause()
            
            # 5. 提供修复建议
            self.suggest_immediate_fixes()
            
            # 6. 生成配置修复
            if has_llm_issue:
                logger.info(f"\n🚨 检测到LLM问题: {issue_desc}")
                return self.generate_config_fix()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 分析异常: {e}")
            return False

def main():
    """主分析函数"""
    logger.info("🔍 Python事件处理问题分析工具")
    logger.info("="*50)
    logger.info("🎯 目标:")
    logger.info("   分析为什么Java事件没有生成SPEAK命令")
    logger.info("="*50)
    
    fixer = EventProcessingFixer()
    
    try:
        success = fixer.run_analysis()
        
        if success:
            print("\n✅ 分析完成！请根据建议进行修复")
            print("🔄 修复后请重启xiaozhi-server服务")
        else:
            print("\n❌ 分析过程中遇到问题")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  分析被中断")
        return False
    except Exception as e:
        logger.error(f"\n❌ 分析异常: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎯 请按照上述建议修复配置，然后重启服务")
    else:
        print("\n⚠️  分析过程中遇到问题")
    
    exit(0 if success else 1)

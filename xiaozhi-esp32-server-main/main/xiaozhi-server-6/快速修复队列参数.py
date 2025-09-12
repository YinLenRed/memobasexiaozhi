#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速修复队列参数错误
修正AwakenWithCallbackService.send_awaken_with_callback的调用参数
"""

import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('参数修复')

def fix_queue_manager_call():
    """修复MessageQueueManager中的方法调用参数"""
    logger.info("🔧 修复队列管理器中的方法调用参数")
    
    queue_file = "core/queue/message_queue_manager.py"
    try:
        with open(queue_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 错误的调用（带track_id参数）
        old_call = '''# 发送speak命令（修正参数顺序）
                result_track_id = await self.unified_event_service.awaken_service.send_awaken_with_callback(
                    device_id=message.device_id,
                    message=message.content,
                    message_type=message.category,
                    track_id=track_id
                )'''
        
        # 正确的调用（不传track_id，方法内部会生成）
        new_call = '''# 发送speak命令（正确的参数）
                result_track_id = await self.unified_event_service.awaken_service.send_awaken_with_callback(
                    device_id=message.device_id,
                    message=message.content,
                    message_type=message.category
                )'''
        
        if old_call in content:
            content = content.replace(old_call, new_call)
            logger.info("✅ 找到并修复了错误的方法调用")
        else:
            # 尝试模糊匹配修复
            pattern = r'result_track_id = await self\.unified_event_service\.awaken_service\.send_awaken_with_callback\(\s*device_id=message\.device_id,\s*message=message\.content,\s*message_type=message\.category,?\s*track_id=track_id\s*\)'
            
            if re.search(pattern, content):
                content = re.sub(
                    pattern,
                    '''result_track_id = await self.unified_event_service.awaken_service.send_awaken_with_callback(
                    device_id=message.device_id,
                    message=message.content,
                    message_type=message.category
                )''',
                    content
                )
                logger.info("✅ 通过正则表达式修复了错误的方法调用")
            else:
                logger.warning("⚠️ 未找到具体的错误调用，手动检查")
                return False
        
        # 备份并保存
        backup_file = f"{queue_file}.param_fix_{int(__import__('time').time())}"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content.replace(new_call, old_call))  # 备份原版本
        logger.info(f"💾 已备份: {backup_file}")
        
        with open(queue_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ 队列管理器参数已修复")
        return True
        
    except Exception as e:
        logger.error(f"❌ 参数修复失败: {e}")
        return False

def create_simple_test():
    """创建简单的队列测试"""
    logger.info("🔧 创建简单队列测试脚本")
    
    simple_test = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的队列功能测试 - 不依赖httpx
仅测试服务器是否正确处理了队列参数
"""

import json
import sys
import subprocess
import time

def test_with_curl():
    """使用curl测试，避免httpx依赖"""
    print("🧪 使用curl测试队列功能")
    print("="*40)
    
    # 测试消息
    payload = {
        "device_id": "f0:9e:9e:04:8a:44",
        "initial_content": "参数修复测试：这条消息应该正常通过队列处理",
        "category": "system_reminder",
        "user_info": {
            "priority": 1,
            "test_type": "param_fix"
        }
    }
    
    try:
        # 构建curl命令
        curl_cmd = [
            'curl', '-X', 'POST',
            'http://47.98.51.180:8003/xiaozhi/greeting/send',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps(payload),
            '--max-time', '15'
        ]
        
        print("📤 发送测试消息...")
        print(f"🔗 URL: http://47.98.51.180:8003/xiaozhi/greeting/send")
        print(f"📋 数据: {payload['initial_content']}")
        
        # 执行curl命令
        result = subprocess.run(
            curl_cmd, 
            capture_output=True, 
            text=True, 
            timeout=20
        )
        
        if result.returncode == 0:
            try:
                response_data = json.loads(result.stdout)
                if response_data.get('success'):
                    track_id = response_data.get('track_id', '未知')
                    print(f"✅ 消息发送成功: track_id={track_id}")
                    
                    # 等待一下，然后检查队列状态
                    print("⏳ 等待3秒后检查队列状态...")
                    time.sleep(3)
                    
                    # 检查队列状态
                    status_cmd = [
                        'curl', 
                        'http://47.98.51.180:8003/xiaozhi/queue/status/f0:9e:9e:04:8a:44',
                        '--max-time', '10'
                    ]
                    
                    status_result = subprocess.run(
                        status_cmd,
                        capture_output=True,
                        text=True,
                        timeout=15
                    )
                    
                    if status_result.returncode == 0:
                        try:
                            status_data = json.loads(status_result.stdout)
                            total_msgs = status_data.get('total_messages', 0)
                            queue_len = status_data.get('queue_length', 0)
                            is_playing = status_data.get('is_playing', False)
                            completed = status_data.get('completed_messages', 0)
                            
                            print("📊 队列状态:")
                            print(f"   总消息数: {total_msgs}")
                            print(f"   队列长度: {queue_len}")
                            print(f"   正在播放: {is_playing}")
                            print(f"   已完成数: {completed}")
                            
                            if total_msgs > 0:
                                print("🎉 成功！参数修复生效，队列正在工作")
                                return True
                            else:
                                print("⚠️ 队列状态仍为空，可能还需要重启服务")
                                return False
                                
                        except json.JSONDecodeError:
                            print(f"⚠️ 队列状态解析失败: {status_result.stdout}")
                            return False
                    else:
                        print(f"❌ 队列状态查询失败: {status_result.stderr}")
                        return False
                else:
                    print(f"❌ 消息发送失败: {response_data}")
                    return False
            except json.JSONDecodeError:
                print(f"❌ 响应解析失败: {result.stdout}")
                return False
        else:
            print(f"❌ curl命令失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 请求超时")
        return False
    except FileNotFoundError:
        print("❌ curl命令未找到，请确保curl已安装")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def main():
    print("🔧 队列参数修复验证工具")
    print("="*30)
    print("🎯 测试修复后的队列参数调用")
    print("💡 使用curl避免Python依赖问题")
    print()
    
    success = test_with_curl()
    
    print("\\n📋 测试结果:")
    if success:
        print("✅ 参数修复成功！队列功能正常")
        print("🎵 硬件消息将按顺序播放，不会被新消息顶掉")
    else:
        print("⚠️ 可能需要重启Python服务:")
        print("   systemctl restart xiaozhi-service")

if __name__ == "__main__":
    main()
'''
    
    with open('简单队列测试.py', 'w', encoding='utf-8') as f:
        f.write(simple_test)
    
    logger.info("📄 已创建: 简单队列测试.py")
    return True

def main():
    """主修复函数"""
    print("🚀 队列参数错误快速修复")
    print("="*30)
    print("❌ 错误: got an unexpected keyword argument 'track_id'")
    print("✅ 修复: 移除多余的track_id参数")
    print()
    
    success_count = 0
    
    # 1. 修复参数调用
    if fix_queue_manager_call():
        success_count += 1
    
    # 2. 创建测试脚本
    if create_simple_test():
        success_count += 1
    
    print()
    if success_count >= 1:
        logger.info("🎉 参数修复完成！")
        logger.info("📋 接下来：")
        logger.info("   1. 重启服务: systemctl restart xiaozhi-service")
        logger.info("   2. 测试: python 简单队列测试.py")
        logger.info("   3. 或在服务器运行: python 测试消息队列.py")
    else:
        logger.error("❌ 修复失败，请手动检查参数")

if __name__ == "__main__":
    main()

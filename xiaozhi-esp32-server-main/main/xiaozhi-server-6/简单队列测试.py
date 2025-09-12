#!/usr/bin/env python3
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
    
    print("\n📋 测试结果:")
    if success:
        print("✅ 参数修复成功！队列功能正常")
        print("🎵 硬件消息将按顺序播放，不会被新消息顶掉")
    else:
        print("⚠️ 可能需要重启Python服务:")
        print("   systemctl restart xiaozhi-service")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 一键硬件音频播放测试
结合API调用和MQTT监控的简化版本
"""

import subprocess
import json
import sys
import time
from datetime import datetime

def log(message, level="INFO"):
    """带时间戳和级别的日志"""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
    icon = icons.get(level, "📝")
    print(f"[{timestamp}] {icon} {message}")

def run_api_call(device_id, text):
    """使用curl调用API"""
    log("🚀 发送健康提醒API请求...")
    
    api_url = "http://172.20.12.204:8003/xiaozhi/greeting/send"
    payload = {
        "device_id": device_id,
        "initial_content": text,
        "category": "system_reminder"
    }
    
    curl_cmd = [
        "curl", "-s", "-X", "POST", api_url,
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload)
    ]
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            response = json.loads(result.stdout)
            if response.get("success"):
                track_id = response.get("track_id")
                log(f"✅ API调用成功! Track ID: {track_id}", "SUCCESS")
                return track_id
            else:
                log(f"❌ API返回错误: {response}", "ERROR")
                return None
        else:
            log(f"❌ curl命令失败: {result.stderr}", "ERROR")
            return None
    except Exception as e:
        log(f"❌ API调用异常: {e}", "ERROR")
        return None

def monitor_device(device_id, track_id, timeout=180):
    """监控设备响应"""
    log(f"📡 开始监控设备 {device_id} 的响应...")
    
    # 构建mosquitto_sub命令
    mqtt_cmd = [
        "mosquitto_sub", "-h", "47.97.185.142", "-p", "1883",
        "-u", "admin", "-P", "Jyxd@2025",
        "-t", f"device/{device_id}/+", "-v"
    ]
    
    try:
        log(f"⏰ 监控硬件响应（最多{timeout}秒）...")
        start_time = time.time()
        ack_received = False
        completed = False
        
        process = subprocess.Popen(
            mqtt_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        while time.time() - start_time < timeout:
            if process.poll() is not None:
                break
                
            try:
                # 设置较短的超时来检查新消息
                line = process.stdout.readline()
                if line:
                    line = line.strip()
                    log(f"📥 收到MQTT消息: {line}")
                    
                    # 解析消息
                    if "/ack " in line:
                        try:
                            topic, payload = line.split(" ", 1)
                            data = json.loads(payload)
                            
                            if data.get("track_id") == track_id:
                                ack_received = True
                                elapsed = time.time() - start_time
                                log(f"✅ 硬件ACK确认成功! 用时: {elapsed:.1f}秒", "SUCCESS")
                                log("🌐 硬件正在连接WebSocket接收音频...", "INFO")
                        except:
                            pass
                    
                    elif "/event " in line:
                        try:
                            topic, payload = line.split(" ", 1)
                            data = json.loads(payload)
                            
                            if data.get("track_id") == track_id and data.get("evt") == "EVT_SPEAK_DONE":
                                completed = True
                                total_time = time.time() - start_time
                                log(f"🎉 音频播放完成! 总用时: {total_time:.1f}秒", "SUCCESS")
                                process.terminate()
                                return True, ack_received, completed
                        except:
                            pass
                
                # 每30秒显示状态
                elapsed = time.time() - start_time
                if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                    log(f"⏳ 监控中... 已用时: {elapsed:.0f}秒, ACK={ack_received}, 完成={completed}")
                    time.sleep(1)  # 避免重复输出
                    
            except:
                time.sleep(0.1)
        
        # 超时处理
        process.terminate()
        elapsed = time.time() - start_time
        log(f"⏰ 监控超时 ({elapsed:.1f}秒)", "WARNING")
        return False, ack_received, completed
        
    except Exception as e:
        log(f"❌ 监控异常: {e}", "ERROR")
        return False, False, False

def print_results(device_id, track_id, success, ack_received, completed):
    """打印测试结果"""
    print("\n" + "=" * 60)
    print("🎯 一键硬件音频播放测试结果")
    print("=" * 60)
    
    print(f"📱 测试设备: {device_id}")
    print(f"🎯 Track ID: {track_id}")
    print()
    
    steps = [
        ("🚀 API调用", bool(track_id)),
        ("📥 硬件ACK确认", ack_received),
        ("🎵 音频播放完成", completed)
    ]
    
    passed = 0
    for step_name, status in steps:
        icon = "✅" if status else "❌"
        status_text = "成功" if status else "失败"
        print(f"{icon} {step_name:<15} : {status_text}")
        if status:
            passed += 1
    
    print("-" * 60)
    print(f"📈 总体结果: {passed}/{len(steps)} 步骤成功")
    
    if success:
        print("🎉 恭喜！完整的硬件音频播放测试成功！")
    elif ack_received:
        print("⚠️ 硬件响应正常，但音频播放可能未完成")
    else:
        print("❌ 硬件无响应，请检查设备状态")
    
    print("=" * 60)

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python one_click_test.py <device_id> [text]")
        print("示例: python one_click_test.py 7c:2c:67:8d:89:78")
        print("示例: python one_click_test.py 7c:2c:67:8d:89:78 '现在该吃药了，记得按时服药哦！'")
        sys.exit(1)
    
    device_id = sys.argv[1]
    text = sys.argv[2] if len(sys.argv) > 2 else "现在是下午2点，该吃午餐了。饭后记得按时服药哦！"
    
    print("🎯 一键硬件音频播放测试")
    print("📋 测试内容: 健康提醒音频播放")
    print("🔄 测试流程: API → TTS → MQTT → WebSocket → 硬件播放")
    print("=" * 60)
    print(f"📱 目标设备: {device_id}")
    print(f"📝 提醒内容: {text}")
    print()
    
    # 步骤1: API调用
    track_id = run_api_call(device_id, text)
    if not track_id:
        log("API调用失败，测试终止", "ERROR")
        print_results(device_id, None, False, False, False)
        sys.exit(1)
    
    # 步骤2: 监控设备响应
    success, ack_received, completed = monitor_device(device_id, track_id)
    
    # 打印结果
    print_results(device_id, track_id, success, ack_received, completed)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
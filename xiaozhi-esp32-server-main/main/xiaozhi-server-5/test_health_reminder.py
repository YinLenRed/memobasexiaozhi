#!/usr/bin/env python3
"""
🏥 健康提醒测试脚本
测试主动问候生成健康提醒内容：今天吃药了吗
"""

import requests
import json
import time
import sys
from datetime import datetime

class HealthReminderTest:
    def __init__(self, device_id="f0:9e:9e:04:8a:44"):
        self.device_id = device_id
        self.base_url = "http://172.20.12.204:8003"
        self.test_results = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        if level == "SUCCESS":
            prefix = "✅"
        elif level == "ERROR":
            prefix = "❌"
        elif level == "WARNING":
            prefix = "⚠️"
        else:
            prefix = "ℹ️"
            
        print(f"[{timestamp}] {prefix} {message}")

    def test_basic_health_reminder(self):
        """测试基础健康提醒"""
        self.log("🧪 测试1: 基础健康提醒")
        
        payload = {
            "device_id": self.device_id,
            "initial_content": "今天吃药了吗？",
            "category": "system_reminder"
        }
        
        return self.send_greeting_request(payload, "基础健康提醒")
    
    def test_personalized_health_reminder(self):
        """测试个性化健康提醒"""
        self.log("🧪 测试2: 个性化健康提醒")
        
        payload = {
            "device_id": self.device_id,
            "initial_content": "记得按时吃降压药哦",
            "category": "system_reminder",
            "user_info": {
                "name": "李叔",
                "age": 68,
                "location": "北京",
                "health_info": "高血压患者，需要按时服药"
            },
            "memory_info": "李叔每天早上8点和晚上8点需要服用降压药，有时会忘记"
        }
        
        return self.send_greeting_request(payload, "个性化健康提醒")
    
    def test_medication_schedule_reminder(self):
        """测试用药时间提醒"""
        self.log("🧪 测试3: 用药时间提醒")
        
        current_hour = datetime.now().hour
        if current_hour < 12:
            time_context = "早上好"
            med_time = "早上的药"
        elif current_hour < 18:
            time_context = "下午好"
            med_time = "下午的药"
        else:
            time_context = "晚上好"
            med_time = "晚上的药"
            
        payload = {
            "device_id": self.device_id,
            "initial_content": f"{time_context}，该吃{med_time}了",
            "category": "system_reminder",
            "user_info": {
                "name": "王奶奶",
                "age": 72,
                "health_info": "糖尿病患者，需要定时服药测血糖"
            }
        }
        
        return self.send_greeting_request(payload, "用药时间提醒")
    
    def test_health_check_reminder(self):
        """测试健康检查提醒"""
        self.log("🧪 测试4: 健康检查提醒")
        
        payload = {
            "device_id": self.device_id,
            "initial_content": "今天测血压了吗？记得每天监测哦",
            "category": "system_reminder",
            "user_info": {
                "name": "张爷爷",
                "age": 75,
                "health_info": "需要每日监测血压血糖",
                "preferences": "关注健康数据变化"
            },
            "memory_info": "张爷爷习惯每天早上测血压，最近血压有些偏高需要密切关注"
        }
        
        return self.send_greeting_request(payload, "健康检查提醒")
    
    def test_exercise_reminder(self):
        """测试运动提醒"""
        self.log("🧪 测试5: 运动健康提醒")
        
        payload = {
            "device_id": self.device_id,
            "initial_content": "今天散步了吗？适量运动有助健康",
            "category": "system_reminder",
            "user_info": {
                "name": "陈阿姨",
                "age": 65,
                "location": "上海",
                "preferences": "喜欢散步，关注健康养生"
            },
            "memory_info": "陈阿姨每天下午喜欢到公园散步，但最近天气不好很少出门"
        }
        
        return self.send_greeting_request(payload, "运动健康提醒")

    def send_greeting_request(self, payload, test_name):
        """发送问候请求"""
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/xiaozhi/greeting/send",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=10
            )
            
            request_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                track_id = data.get("track_id")
                
                self.log(f"✅ {test_name}发送成功")
                self.log(f"📋 Track ID: {track_id}")
                self.log(f"⏱️ 请求耗时: {request_time:.1f}ms")
                
                # 监控任务状态
                result = self.monitor_task_completion(track_id, test_name)
                
                self.test_results.append({
                    "test_name": test_name,
                    "track_id": track_id,
                    "request_time_ms": request_time,
                    "success": result["success"],
                    "completion_time_s": result.get("completion_time", 0),
                    "final_status": result.get("status", "unknown")
                })
                
                return result
                
            else:
                self.log(f"❌ {test_name}发送失败: {response.status_code}", "ERROR")
                self.log(f"📄 错误内容: {response.text}", "ERROR")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            self.log(f"❌ {test_name}请求异常: {e}", "ERROR")
            return {"success": False, "error": str(e)}
    
    def monitor_task_completion(self, track_id, test_name, timeout=180):
        """监控任务完成状态"""
        self.log(f"🔍 监控{test_name}完成状态...")
        
        start_time = time.time()
        check_interval = 2  # 每2秒检查一次
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.base_url}/xiaozhi/greeting/status",
                    params={"device_id": self.device_id},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    task_state = data.get("state", {}).get(track_id)
                    
                    if task_state:
                        status = task_state.get("status")
                        
                        if status == "speak_done":
                            completion_time = time.time() - start_time
                            completed_timestamp = task_state.get("completed_timestamp")
                            
                            self.log(f"🎉 {test_name}完成！", "SUCCESS")
                            self.log(f"⏱️ 完成耗时: {completion_time:.1f}s")
                            self.log(f"📅 完成时间: {completed_timestamp}")
                            
                            return {
                                "success": True,
                                "completion_time": completion_time,
                                "status": status,
                                "completed_timestamp": completed_timestamp
                            }
                        elif status in ["command_sent", "ack_received"]:
                            elapsed = time.time() - start_time
                            self.log(f"⏳ {test_name}进行中... ({status}, {elapsed:.1f}s)")
                        else:
                            self.log(f"📊 {test_name}状态: {status}")
                            
                time.sleep(check_interval)
                
            except Exception as e:
                self.log(f"⚠️ 状态检查异常: {e}", "WARNING")
                time.sleep(check_interval)
        
        # 超时
        elapsed = time.time() - start_time
        self.log(f"⏰ {test_name}监控超时 ({elapsed:.1f}s)", "WARNING")
        
        return {
            "success": False,
            "completion_time": elapsed,
            "status": "timeout"
        }
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 70)
        print("📊 健康提醒测试总结")
        print("=" * 70)
        print(f"📱 测试设备: {self.device_id}")
        print(f"🌐 服务地址: {self.base_url}")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if not self.test_results:
            print("❌ 无测试结果")
            return
        
        # 详细结果
        success_count = 0
        total_request_time = 0
        total_completion_time = 0
        
        for i, result in enumerate(self.test_results, 1):
            status_icon = "✅" if result["success"] else "❌"
            status_text = "成功" if result["success"] else "失败"
            
            print(f"{status_icon} 测试{i}: {result['test_name']:<20} - {status_text}")
            print(f"    📋 Track ID: {result['track_id']}")
            print(f"    ⏱️ 请求时间: {result['request_time_ms']:.1f}ms")
            
            if result["success"]:
                print(f"    🎯 完成时间: {result['completion_time_s']:.1f}s")
                success_count += 1
                total_completion_time += result['completion_time_s']
            else:
                print(f"    ❌ 最终状态: {result['final_status']}")
            
            total_request_time += result['request_time_ms']
            print()
        
        # 统计信息
        print("-" * 70)
        print(f"📈 成功率: {success_count}/{len(self.test_results)} ({success_count/len(self.test_results)*100:.1f}%)")
        print(f"⚡ 平均请求时间: {total_request_time/len(self.test_results):.1f}ms")
        
        if success_count > 0:
            avg_completion = total_completion_time / success_count
            print(f"🎯 平均完成时间: {avg_completion:.1f}s")
            
            # 性能评级
            if avg_completion < 10:
                print("🚀 整体性能: 优秀")
            elif avg_completion < 30:
                print("⚡ 整体性能: 良好")
            elif avg_completion < 60:
                print("📊 整体性能: 一般")
            else:
                print("🐌 整体性能: 需优化")
        
        print("-" * 70)
        
        if success_count == len(self.test_results):
            print("🎉 所有健康提醒测试通过！主动问候功能完全正常！")
        elif success_count > 0:
            print(f"⚠️ 部分测试通过，请检查失败的测试项目")
        else:
            print("❌ 所有测试失败，请检查系统配置")

def main():
    """主函数"""
    device_id = "f0:9e:9e:04:8a:44"
    if len(sys.argv) > 1:
        device_id = sys.argv[1]
    
    print("🏥 健康提醒主动问候测试工具")
    print("=" * 50)
    print(f"📱 目标设备: {device_id}")
    print(f"🎯 测试场景: 健康提醒 (今天吃药了吗)")
    print()
    
    tester = HealthReminderTest(device_id)
    
    try:
        # 运行所有测试
        print("🚀 开始健康提醒测试...")
        print()
        
        tester.test_basic_health_reminder()
        time.sleep(3)  # 间隔3秒
        
        tester.test_personalized_health_reminder()
        time.sleep(3)
        
        tester.test_medication_schedule_reminder()
        time.sleep(3)
        
        tester.test_health_check_reminder()
        time.sleep(3)
        
        tester.test_exercise_reminder()
        
        # 等待所有任务完成
        print()
        print("⏳ 等待所有测试完成...")
        time.sleep(10)
        
        # 打印总结
        tester.print_summary()
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
        tester.print_summary()
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        tester.print_summary()

if __name__ == "__main__":
    main()

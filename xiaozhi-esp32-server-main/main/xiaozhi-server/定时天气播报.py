#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时天气播报服务
"""

import time
import json
import urllib.request
import logging
from datetime import datetime, time as time_obj
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('定时天气')

DEVICE_ID = "f0:9e:9e:04:8a:44"
API_BASE = "http://47.98.51.180:8003"

class WeatherScheduler:
    """定时天气播报调度器"""
    
    def __init__(self):
        self.running = False
        self.schedule_thread = None
        
        # 默认播报时间点
        self.broadcast_times = [
            time_obj(8, 0),   # 早上8点
            time_obj(12, 0),  # 中午12点
            time_obj(18, 0),  # 下午6点
            time_obj(22, 0)   # 晚上10点
        ]
        
        # 城市列表
        self.cities = ["北京", "上海", "广州", "深圳"]
        self.current_city_index = 0
    
    def http_request(self, url, data=None, timeout=25):
        """HTTP请求"""
        try:
            if data:
                data_json = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, data=data_json)
                req.add_header('Content-Type', 'application/json')
            else:
                req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode('utf-8')
                
        except Exception as e:
            logger.error(f"HTTP请求失败: {e}")
            return None
    
    def get_weather_data(self, city):
        """获取天气数据"""
        hour = datetime.now().hour
        day = datetime.now().day
        
        # 根据时间和城市生成合理的天气数据
        temp_base = {"北京": 20, "上海": 22, "广州": 26, "深圳": 25}
        base_temp = temp_base.get(city, 20)
        
        if hour < 6:
            conditions = ["清晨微凉", "晨雾"]
            temp = base_temp - 5 + (day % 3)
        elif hour < 12:
            conditions = ["晴朗", "多云"]
            temp = base_temp + (day % 5)
        elif hour < 18:
            conditions = ["晴热", "午后阳光"]
            temp = base_temp + 5 + (day % 4)
        else:
            conditions = ["傍晚微风", "夜晚清爽"]
            temp = base_temp - 2 + (day % 3)
        
        condition = conditions[day % len(conditions)]
        
        # 生成建议
        if temp > 30:
            advice = "炎热，注意防暑"
        elif temp < 10:
            advice = "寒冷，注意保暖"
        elif "晴" in condition:
            advice = "天气不错，适合外出"
        else:
            advice = "天气一般，注意添衣"
        
        return {
            "city": city,
            "temperature": temp,
            "condition": condition,
            "advice": advice
        }
    
    def format_broadcast_content(self, weather_data, time_period=""):
        """格式化播报内容"""
        city = weather_data["city"]
        temp = weather_data["temperature"]
        condition = weather_data["condition"]
        advice = weather_data["advice"]
        
        current_time = datetime.now().strftime("%H点%M分")
        
        # 根据时间段调整问候语
        if time_period:
            greeting = time_period
        else:
            hour = datetime.now().hour
            if hour < 6:
                greeting = "凌晨时光"
            elif hour < 12:
                greeting = "早上好"
            elif hour < 14:
                greeting = "中午好"
            elif hour < 18:
                greeting = "下午好"
            else:
                greeting = "晚上好"
        
        content = f"{greeting}！{city}天气播报，现在{current_time}，今天{condition}，温度{temp}度，{advice}"
        
        return content
    
    def send_weather_broadcast(self, content):
        """发送天气播报"""
        payload = {
            "device_id": DEVICE_ID,
            "category": "weather",
            "initial_content": content
        }
        
        url = f"{API_BASE}/xiaozhi/greeting/send"
        
        try:
            response_text = self.http_request(url, payload)
            
            if response_text:
                response_data = json.loads(response_text)
                if response_data.get("success"):
                    track_id = response_data.get("track_id", "未知")
                    logger.info(f"✅ 天气播报成功，跟踪ID: {track_id}")
                    return True
                else:
                    logger.error(f"❌ 播报失败: {response_data}")
                    return False
            else:
                logger.error("❌ 无响应")
                return False
                
        except Exception as e:
            logger.error(f"❌ 发送异常: {e}")
            return False
    
    def broadcast_weather(self, city=None, time_period=""):
        """执行天气播报"""
        if not city:
            city = self.cities[self.current_city_index]
            self.current_city_index = (self.current_city_index + 1) % len(self.cities)
        
        logger.info(f"🌤️ 定时天气播报 - {city}")
        
        # 获取天气数据
        weather_data = self.get_weather_data(city)
        
        # 格式化内容
        content = self.format_broadcast_content(weather_data, time_period)
        logger.info(f"📄 播报内容: {content}")
        
        # 发送播报
        success = self.send_weather_broadcast(content)
        
        if success:
            logger.info(f"🎉 {city}定时天气播报成功")
        else:
            logger.error(f"❌ {city}定时天气播报失败")
        
        return success
    
    def check_schedule(self):
        """检查播报计划"""
        now = datetime.now().time()
        current_minute = now.hour * 60 + now.minute
        
        for broadcast_time in self.broadcast_times:
            target_minute = broadcast_time.hour * 60 + broadcast_time.minute
            
            # 在目标时间的1分钟内触发播报
            if abs(current_minute - target_minute) <= 1:
                hour = broadcast_time.hour
                if hour == 8:
                    time_period = "早上好"
                elif hour == 12:
                    time_period = "中午好"
                elif hour == 18:
                    time_period = "下午好"
                elif hour == 22:
                    time_period = "晚上好"
                else:
                    time_period = ""
                
                self.broadcast_weather(time_period=time_period)
                time.sleep(60)  # 避免重复播报
    
    def schedule_loop(self):
        """调度循环"""
        logger.info("⏰ 定时天气播报服务启动")
        logger.info(f"📅 播报时间: {[t.strftime('%H:%M') for t in self.broadcast_times]}")
        
        while self.running:
            try:
                self.check_schedule()
                time.sleep(30)  # 每30秒检查一次
            except KeyboardInterrupt:
                logger.info("📴 接收到停止信号")
                break
            except Exception as e:
                logger.error(f"❌ 调度异常: {e}")
                time.sleep(60)
        
        logger.info("⏹️ 定时天气播报服务已停止")
    
    def start(self):
        """启动定时服务"""
        if self.running:
            logger.warning("⚠️ 服务已在运行")
            return
        
        self.running = True
        self.schedule_thread = threading.Thread(target=self.schedule_loop)
        self.schedule_thread.daemon = True
        self.schedule_thread.start()
        
        logger.info("🚀 定时天气播报服务已启动")
    
    def stop(self):
        """停止定时服务"""
        self.running = False
        if self.schedule_thread:
            self.schedule_thread.join(timeout=5)
        logger.info("⏹️ 定时天气播报服务已停止")
    
    def add_broadcast_time(self, hour, minute=0):
        """添加播报时间"""
        new_time = time_obj(hour, minute)
        if new_time not in self.broadcast_times:
            self.broadcast_times.append(new_time)
            self.broadcast_times.sort()
            logger.info(f"✅ 添加播报时间: {new_time.strftime('%H:%M')}")
        else:
            logger.warning(f"⚠️ 播报时间已存在: {new_time.strftime('%H:%M')}")
    
    def remove_broadcast_time(self, hour, minute=0):
        """移除播报时间"""
        target_time = time_obj(hour, minute)
        if target_time in self.broadcast_times:
            self.broadcast_times.remove(target_time)
            logger.info(f"✅ 移除播报时间: {target_time.strftime('%H:%M')}")
        else:
            logger.warning(f"⚠️ 播报时间不存在: {target_time.strftime('%H:%M')}")

def quick_weather(city="北京"):
    """快速天气播报"""
    scheduler = WeatherScheduler()
    return scheduler.broadcast_weather(city)

def start_auto_weather():
    """启动自动天气播报"""
    scheduler = WeatherScheduler()
    
    print("🌤️ 定时天气播报服务")
    print("="*30)
    print("默认播报时间: 8:00, 12:00, 18:00, 22:00")
    print("按 Ctrl+C 停止服务")
    print()
    
    try:
        scheduler.start()
        
        # 立即播报一次作为测试
        logger.info("🧪 执行启动测试播报...")
        scheduler.broadcast_weather(time_period="服务启动")
        
        # 保持运行
        while scheduler.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n📴 停止定时天气播报服务...")
        scheduler.stop()

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd == "start" or cmd == "auto":
            start_auto_weather()
        elif cmd == "test":
            city = sys.argv[2] if len(sys.argv) > 2 else "北京"
            quick_weather(city)
        elif cmd in ["北京", "上海", "广州", "深圳"]:
            quick_weather(cmd)
        else:
            print("用法:")
            print("python 定时天气播报.py start      # 启动定时服务")
            print("python 定时天气播报.py test 北京  # 快速测试")
            print("python 定时天气播报.py 上海       # 指定城市播报")
    else:
        print("🌤️ 定时天气播报工具")
        print("="*20)
        print("1. python 定时天气播报.py start   - 启动定时服务")
        print("2. python 定时天气播报.py test    - 快速测试")
        print("3. python 定时天气播报.py 北京    - 指定城市")
        print()
        
        choice = input("选择功能 (start/test/北京): ").strip().lower()
        
        if choice in ["start", "auto"]:
            start_auto_weather()
        elif choice == "test":
            quick_weather()
        elif choice in ["北京", "上海", "广州", "深圳"]:
            quick_weather(choice)
        else:
            print("🔄 默认执行快速测试...")
            quick_weather()

if __name__ == "__main__":
    main()

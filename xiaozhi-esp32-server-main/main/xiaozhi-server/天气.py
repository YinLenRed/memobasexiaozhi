#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天气播报快捷命令
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入天气功能
try:
    from 无依赖天气获取 import main_weather_broadcast
    from 定时天气播报 import WeatherScheduler, quick_weather, start_auto_weather
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保相关文件存在")
    sys.exit(1)

def show_help():
    """显示帮助信息"""
    print("🌤️ 天气播报命令工具")
    print("="*30)
    print("🔹 基础命令:")
    print("  python 天气.py              # 北京天气")
    print("  python 天气.py 上海         # 指定城市")
    print("  python 天气.py now          # 立即播报")
    print()
    print("🔹 定时功能:")
    print("  python 天气.py auto         # 启动定时播报")
    print("  python 天气.py schedule     # 查看播报时间表")
    print()
    print("🔹 快捷城市:")
    print("  python 天气.py bj           # 北京")
    print("  python 天气.py sh           # 上海") 
    print("  python 天气.py gz           # 广州")
    print("  python 天气.py sz           # 深圳")
    print()
    print("🔹 其他:")
    print("  python 天气.py help         # 显示帮助")
    print("  python 天气.py test         # 测试播报")

def main():
    """主函数"""
    # 城市快捷映射
    city_map = {
        "bj": "北京",
        "sh": "上海", 
        "gz": "广州",
        "sz": "深圳",
        "beijing": "北京",
        "shanghai": "上海",
        "guangzhou": "广州",
        "shenzhen": "深圳"
    }
    
    if len(sys.argv) == 1:
        # 默认北京天气
        print("🌤️ 默认播报北京天气...")
        main_weather_broadcast("北京")
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd in ["help", "h", "-h", "--help"]:
        show_help()
        
    elif cmd in ["now", "current"]:
        city = sys.argv[2] if len(sys.argv) > 2 else "北京"
        city = city_map.get(city.lower(), city)
        print(f"🌤️ 立即播报{city}天气...")
        main_weather_broadcast(city)
        
    elif cmd in ["auto", "schedule", "timer"]:
        print("🕐 启动定时天气播报...")
        start_auto_weather()
        
    elif cmd == "test":
        print("🧪 测试天气播报功能...")
        quick_weather("北京")
        
    elif cmd in city_map:
        city = city_map[cmd]
        print(f"🌤️ 播报{city}天气...")
        main_weather_broadcast(city)
        
    elif cmd in ["北京", "上海", "广州", "深圳", "天津", "重庆", "杭州", "南京", "武汉", "西安"]:
        print(f"🌤️ 播报{cmd}天气...")
        main_weather_broadcast(cmd)
        
    else:
        # 将输入作为城市名处理
        print(f"🌤️ 播报{cmd}天气...")
        main_weather_broadcast(cmd)

if __name__ == "__main__":
    main()

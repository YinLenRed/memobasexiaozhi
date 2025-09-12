#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动天气MQTT发布服务
为硬件人员提供持续的天气数据推送
"""

import asyncio
import signal
import sys
from datetime import datetime
from config.config_loader import load_config
from core.mqtt.weather_publisher import MQTTWeatherPublisher
from core.mqtt.mqtt_client import MQTTClient

class WeatherMQTTService:
    """天气MQTT发布服务"""
    
    def __init__(self):
        self.config = load_config()
        self.mqtt_client = None
        self.weather_publisher = None
        self.running = False
        
    async def start(self):
        """启动服务"""
        print("🚀 启动天气MQTT发布服务")
        print("=" * 50)
        
        try:
            # 初始化MQTT客户端
            print("📡 1. 初始化MQTT连接...")
            self.mqtt_client = MQTTClient(self.config)
            await self.mqtt_client.start()
            print("   ✅ MQTT连接成功")
            
            # 初始化天气发布器
            print("\n🌤️ 2. 初始化天气发布器...")
            self.weather_publisher = MQTTWeatherPublisher(self.config, self.mqtt_client)
            await self.weather_publisher.start_weather_publisher()
            print("   ✅ 天气发布器初始化成功")
            
            # 立即发布一次天气数据
            print("\n📤 3. 立即发布天气数据...")
            await self.weather_publisher.manual_publish_all()
            print("   ✅ 首次天气数据发布完成")
            
            # 启动定时发布
            print(f"\n⏰ 4. 启动定时发布服务...")
            publish_interval = self.config.get("weather_publisher", {}).get("publish_interval", 30)
            print(f"   📅 发布间隔: 每{publish_interval}分钟")
            print(f"   🎯 目标设备: {self.config.get('weather_publisher', {}).get('devices', [])}")
            print(f"   🏙️ 目标城市: {self.config.get('weather_publisher', {}).get('cities', [])}")
            
            self.running = True
            # 天气发布器已经在start_weather_publisher()中启动了定时任务
            
        except Exception as e:
            print(f"❌ 服务启动失败: {e}")
            await self.stop()
            return
        
        print("\n🎉 天气MQTT服务已启动!")
        print("=" * 50)
        print("📊 服务状态:")
        print(f"   🔗 MQTT服务器: {self.config.get('mqtt', {}).get('host')}:{self.config.get('mqtt', {}).get('port')}")
        print(f"   📡 发布主题:")
        
        topics = self.config.get("weather_publisher", {}).get("topics", {})
        for topic_name, topic_pattern in topics.items():
            print(f"      - {topic_name}: {topic_pattern}")
        
        print(f"\n💡 硬件人员订阅指南:")
        print(f"   📋 查看完整文档: HARDWARE_MQTT_GUIDE.md")
        print(f"   🧪 测试订阅命令:")
        mqtt_config = self.config.get("mqtt", {})
        print(f"      mosquitto_sub -h {mqtt_config.get('host')} -p {mqtt_config.get('port')} \\")
        print(f"                    -u {mqtt_config.get('username')} -P {mqtt_config.get('password')} \\")
        print(f"                    -t 'weather/#' -v")
        
        print(f"\n🔄 按Ctrl+C停止服务")
        
        # 保持服务运行
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print(f"\n⏹️ 收到停止信号...")
            await self.stop()
    
    async def stop(self):
        """停止服务"""
        print("🛑 正在停止天气MQTT服务...")
        self.running = False
        
        if self.weather_publisher:
            # 停止天气发布器（通过设置enabled为False）
            self.weather_publisher.enabled = False
            print("   ✅ 天气发布器已停止")
        
        if self.mqtt_client:
            await self.mqtt_client.stop()
            print("   ✅ MQTT连接已断开")
        
        print("✅ 天气MQTT服务已停止")
    
    async def status(self):
        """显示服务状态"""
        print("📊 天气MQTT服务状态")
        print("=" * 30)
        
        if self.mqtt_client and self.mqtt_client.connected:
            print("🟢 MQTT连接: 正常")
        else:
            print("🔴 MQTT连接: 断开")
        
        if self.weather_publisher and self.running:
            print("🟢 天气发布: 运行中")
        else:
            print("🔴 天气发布: 停止")
        
        # 显示最近发布的数据
        print(f"\n📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="天气MQTT发布服务")
    parser.add_argument("--action", choices=["start", "test", "status"], default="start",
                       help="操作类型: start(启动服务), test(测试发布), status(查看状态)")
    
    args = parser.parse_args()
    
    service = WeatherMQTTService()
    
    # 设置信号处理
    def signal_handler(signum, frame):
        print(f"\n⚠️ 收到信号 {signum}，正在关闭服务...")
        asyncio.create_task(service.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.action == "start":
            await service.start()
        elif args.action == "test":
            print("🧪 测试天气数据发布...")
            await service.start()
            # 发布一次后停止
            await asyncio.sleep(5)
            await service.stop()
        elif args.action == "status":
            await service.status()
            
    except Exception as e:
        print(f"❌ 服务异常: {e}")
        import traceback
        print(f"错误详情: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 服务已手动停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

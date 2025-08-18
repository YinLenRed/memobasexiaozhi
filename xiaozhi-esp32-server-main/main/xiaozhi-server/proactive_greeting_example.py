#!/usr/bin/env python3
"""
ESP32 AI设备主动问候功能示例

本示例展示如何使用主动问候功能：
1. 发送不同类型的问候消息
2. 查询设备状态
3. 管理用户档案
4. 错误处理示例
5. 批量操作示例
6. 状态监控示例

使用前请确保：
1. 已启动xiaozhi服务器
2. 已配置MQTT连接
3. ESP32设备在线

运行方式：
python proactive_greeting_example.py
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any, Optional


class ProactiveGreetingExample:
    """主动问候功能示例类"""
    
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url.rstrip('/')
    
    async def send_greeting(
        self, 
        device_id: str, 
        content: str, 
        category: str,
        user_info: Optional[Dict] = None,
        memory_info: Optional[str] = None
    ) -> Dict[str, Any]:
        """发送主动问候"""
        data = {
            "device_id": device_id,
            "initial_content": content,
            "category": category
        }
        
        if user_info:
            data["user_info"] = user_info
        if memory_info:
            data["memory_info"] = memory_info
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.base_url}/xiaozhi/greeting/send',
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    result = await response.json()
                    if response.status == 200:
                        print(f"✅ 发送成功: track_id={result.get('track_id', 'N/A')}")
                    else:
                        print(f"❌ 发送失败: {result}")
                    return result
        except Exception as e:
            print(f"❌ 发送失败: {e}")
            return {"error": str(e)}
    
    async def get_device_status(
        self, 
        device_id: str, 
        track_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询设备状态"""
        params = {"device_id": device_id}
        if track_id:
            params["track_id"] = track_id
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{self.base_url}/xiaozhi/greeting/status',
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    result = await response.json()
                    if response.status == 200:
                        print(f"📊 设备 {device_id} 连接状态: {'在线' if result.get('connected') else '离线'}")
                        if 'state' in result and result['state']:
                            for tid, info in result['state'].items():
                                print(f"   跟踪ID {tid}: {info.get('status', 'unknown')}")
                    else:
                        print(f"❌ 查询失败: {result}")
                    return result
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            return {"error": str(e)}
    
    async def update_user_profile(
        self, 
        device_id: str, 
        user_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新用户档案"""
        data = {
            "device_id": device_id,
            "user_info": user_info
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.base_url}/xiaozhi/user/profile',
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    result = await response.json()
                    if response.status == 200:
                        print(f"✅ 档案更新成功: {user_info.get('name', device_id)}")
                    else:
                        print(f"❌ 档案更新失败: {result}")
                    return result
        except Exception as e:
            print(f"❌ 档案更新失败: {e}")
            return {"error": str(e)}
    
    async def get_user_profile(self, device_id: str) -> Dict[str, Any]:
        """获取用户档案"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{self.base_url}/xiaozhi/user/profile',
                    params={"device_id": device_id},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    result = await response.json()
                    if response.status == 200:
                        profile = result.get('user_profile', {})
                        print(f"👤 用户档案: {profile.get('name', '未设置')} ({device_id})")
                    else:
                        print(f"❌ 获取档案失败: {result}")
                    return result
        except Exception as e:
            print(f"❌ 获取档案失败: {e}")
            return {"error": str(e)}


async def demo_basic_greeting():
    """基础问候示例"""
    print("\n" + "="*50)
    print("🚀 基础问候示例")
    print("="*50)
    
    client = ProactiveGreetingExample()
    device_id = "ESP32_001"
    
    # 天气问候
    print("📤 发送天气问候...")
    result = await client.send_greeting(
        device_id=device_id,
        content="今天最高气温38℃，建议减少户外活动",
        category="weather",
        user_info={
            "id": "user_001",  # 用户ID，用于memobase记忆查询
            "name": "李叔", 
            "age": 65,
            "location": "广州"
        },
        memory_info="平时喜欢晨练，关注健康"
    )
    
    if "track_id" in result:
        # 等待一会儿再查询状态
        print("⏳ 等待2秒后查询状态...")
        await asyncio.sleep(2)
        await client.get_device_status(device_id, result["track_id"])


async def demo_different_categories():
    """不同类别问候示例"""
    print("\n" + "="*50)
    print("📋 不同类别问候示例")
    print("="*50)
    
    client = ProactiveGreetingExample()
    device_id = "ESP32_002"
    
    user_info = {
        "id": "user_002",  # 用户ID，用于memobase记忆查询
        "name": "王阿姨",
        "age": 68,
        "location": "深圳",
        "health_info": "糖尿病患者"
    }
    
    categories = [
        ("system_reminder", "该吃晚饭药了", "每天晚饭后需要服用降糖药"),
        ("schedule", "明天上午10点有体检预约", None),
        ("entertainment", "今晚8点有您喜欢的戏曲节目", "喜欢听京剧和粤剧"),
        ("news", "今日健康资讯：多吃绿叶蔬菜有助控制血糖", None)
    ]
    
    for category, content, memory in categories:
        print(f"📤 发送{category}类问候...")
        await client.send_greeting(
            device_id=device_id,
            content=content,
            category=category,
            user_info=user_info,
            memory_info=memory
        )
        await asyncio.sleep(1)


async def demo_user_profile_management():
    """用户档案管理示例"""
    print("\n" + "="*50)
    print("👤 用户档案管理示例")
    print("="*50)
    
    client = ProactiveGreetingExample()
    device_id = "ESP32_003"
    
    # 更新用户档案
    print("📝 更新用户档案...")
    user_info = {
        "name": "张大爷",
        "age": 72,
        "location": "北京市朝阳区",
        "preferences": "喜欢听新闻、下象棋",
        "health_info": "高血压、轻微耳背",
        "family": "独居，儿子在上海工作",
        "schedule": "早上7点起床，晚上9点睡觉",
        "emergency_contact": "13812345678"
    }
    
    await client.update_user_profile(device_id, user_info)
    
    # 获取用户档案
    print("📖 获取用户档案...")
    await client.get_user_profile(device_id)
    
    # 基于档案信息发送个性化问候
    print("📤 发送个性化问候...")
    await client.send_greeting(
        device_id=device_id,
        content="今天有重要新闻播报",
        category="news",
        user_info=user_info,
        memory_info="每天关注时事新闻，特别关心国际新闻"
    )


async def demo_error_handling():
    """错误处理示例"""
    print("\n" + "="*50)
    print("⚠️  错误处理示例")
    print("="*50)
    
    client = ProactiveGreetingExample()
    
    # 错误示例1：缺少必需字段
    print("1. 测试缺少必需字段:")
    await client.send_greeting("", "", "")
    
    # 错误示例2：无效的类别
    print("\n2. 测试无效的类别:")
    await client.send_greeting(
        device_id="ESP32_TEST",
        content="测试内容",
        category="invalid_category"
    )
    
    # 错误示例3：查询不存在的设备
    print("\n3. 测试查询不存在的设备:")
    await client.get_device_status("NONEXISTENT_DEVICE")


async def demo_batch_operations():
    """批量操作示例"""
    print("\n" + "="*50)
    print("🔄 批量操作示例")
    print("="*50)
    
    client = ProactiveGreetingExample()
    
    # 模拟多个设备
    devices = [
        {
            "device_id": "ESP32_101",
            "user_info": {"id": "user_101", "name": "李奶奶", "age": 70, "location": "上海"},
            "content": "今天空气质量良好，适合外出散步",
            "category": "weather"
        },
        {
            "device_id": "ESP32_102", 
            "user_info": {"id": "user_102", "name": "陈爷爷", "age": 75, "location": "杭州"},
            "content": "记得按时服用血压药",
            "category": "system_reminder"
        },
        {
            "device_id": "ESP32_103",
            "user_info": {"id": "user_103", "name": "周阿姨", "age": 68, "location": "成都"},
            "content": "今晚有您喜欢的川剧表演",
            "category": "entertainment"
        }
    ]
    
    print(f"📤 并发发送 {len(devices)} 条问候消息...")
    
    # 并发发送问候
    tasks = []
    for device in devices:
        task = client.send_greeting(
            device_id=device["device_id"],
            content=device["content"],
            category=device["category"],
            user_info=device["user_info"]
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = len([r for r in results if isinstance(r, dict) and 'track_id' in r])
    print(f"✅ 批量发送完成，成功: {success_count}/{len(devices)}")
    
    # 批量查询状态
    print("\n⏳ 等待3秒后批量查询设备状态...")
    await asyncio.sleep(3)
    
    status_tasks = []
    for device in devices:
        task = client.get_device_status(device["device_id"])
        status_tasks.append(task)
    
    await asyncio.gather(*status_tasks, return_exceptions=True)


async def demo_monitoring():
    """状态监控示例"""
    print("\n" + "="*50)
    print("📈 状态监控示例")
    print("="*50)
    
    client = ProactiveGreetingExample()
    device_id = "ESP32_MONITOR"
    
    # 发送问候并监控状态变化
    print("📤 发送测试消息并开始状态监控...")
    result = await client.send_greeting(
        device_id=device_id,
        content="这是一条测试消息，用于演示状态监控",
        category="system_reminder",
        user_info={"name": "测试用户", "age": 30}
    )
    
    if "track_id" in result:
        track_id = result["track_id"]
        print(f"🔍 开始监控 track_id: {track_id}")
        
        # 定期查询状态，直到完成或超时
        max_attempts = 10
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            print(f"\n📊 第 {attempt} 次状态检查 ({datetime.now().strftime('%H:%M:%S')}):")
            
            status = await client.get_device_status(device_id, track_id)
            
            if "state" in status and track_id in status["state"]:
                current_status = status["state"][track_id]["status"]
                print(f"   当前状态: {current_status}")
                
                if current_status == "speak_done":
                    completed_time = status["state"][track_id].get("completed_timestamp", "")
                    print(f"✅ 问候播放完成！完成时间: {completed_time}")
                    break
                elif current_status == "command_sent":
                    print("📡 命令已发送，等待设备响应...")
                elif current_status == "ack_received":
                    print("📩 设备已确认，正在播放...")
            else:
                print("   等待状态更新...")
            
            if attempt < max_attempts:
                await asyncio.sleep(2)
        
        if attempt >= max_attempts:
            print("⏰ 监控超时，可能设备未响应")
    else:
        print("❌ 发送失败，无法监控状态")


async def demo_real_world_scenarios():
    """真实场景示例"""
    print("\n" + "="*50)
    print("🌟 真实场景示例")
    print("="*50)
    
    client = ProactiveGreetingExample()
    
    # 场景1：早晨健康提醒
    print("🌅 场景1：早晨健康提醒")
    await client.send_greeting(
        device_id="ESP32_MORNING",
        content="早上好！今天天气晴朗，温度22-28℃",
        category="weather",
        user_info={
            "name": "李爷爷",
            "age": 73,
            "health_info": "高血压、糖尿病",
            "schedule": "每天早上7点吃药"
        },
        memory_info="喜欢早起，有晨练习惯，需要定时服药"
    )
    
    await asyncio.sleep(1)
    
    # 场景2：服药提醒
    print("\n💊 场景2：服药提醒")
    await client.send_greeting(
        device_id="ESP32_MEDICINE",
        content="该服用早晨的降压药了",
        category="system_reminder",
        user_info={
            "name": "王奶奶",
            "age": 69,
            "health_info": "高血压"
        },
        memory_info="每天早上8点和晚上8点需要服用降压药"
    )
    
    await asyncio.sleep(1)
    
    # 场景3：子女关怀提醒
    print("\n👨‍👩‍👧‍👦 场景3：子女关怀提醒") 
    await client.send_greeting(
        device_id="ESP32_FAMILY",
        content="小明今天生日，记得给他打电话祝贺",
        category="schedule",
        user_info={
            "name": "陈阿姨",
            "age": 65,
            "family": "有一个儿子小明在外地工作"
        },
        memory_info="很想念在外地工作的儿子，经常担心他"
    )
    
    await asyncio.sleep(1)
    
    # 场景4：天气变化提醒
    print("\n🌦️ 场景4：天气变化提醒")
    await client.send_greeting(
        device_id="ESP32_WEATHER",
        content="今天下午有雷阵雨，外出记得带伞",
        category="weather",
        user_info={
            "name": "赵大爷",
            "age": 70,
            "preferences": "喜欢下午出门买菜"
        },
        memory_info="每天下午3点左右会出门买菜，很关注天气变化"
    )


async def demo_comprehensive_test():
    """综合测试示例"""
    print("\n" + "="*50)
    print("🧪 综合测试示例")
    print("="*50)
    
    client = ProactiveGreetingExample()
    device_id = "ESP32_COMPREHENSIVE"
    
    # 1. 设置用户档案
    print("1️⃣ 设置用户档案...")
    user_info = {
        "name": "综合测试用户",
        "age": 68,
        "location": "测试城市",
        "health_info": "身体健康",
        "preferences": "喜欢听音乐"
    }
    await client.update_user_profile(device_id, user_info)
    
    # 2. 发送多种类型问候
    print("\n2️⃣ 发送多种类型问候...")
    test_messages = [
        ("weather", "今天天气很好"),
        ("system_reminder", "记得按时吃药"), 
        ("news", "今天有重要新闻"),
        ("entertainment", "推荐一首好听的歌曲"),
        ("schedule", "明天有重要安排")
    ]
    
    track_ids = []
    for category, content in test_messages:
        result = await client.send_greeting(
            device_id=device_id,
            content=content,
            category=category,
            user_info=user_info
        )
        if "track_id" in result:
            track_ids.append(result["track_id"])
        await asyncio.sleep(0.5)
    
    # 3. 监控所有消息状态
    print(f"\n3️⃣ 监控 {len(track_ids)} 条消息状态...")
    await asyncio.sleep(2)
    
    for i, track_id in enumerate(track_ids):
        print(f"   消息 {i+1}: ", end="")
        await client.get_device_status(device_id, track_id)
    
    # 4. 获取最终状态
    print("\n4️⃣ 获取设备最终状态...")
    await client.get_device_status(device_id)
    
    print("✅ 综合测试完成")


async def demo_news_broadcast():
    """新闻播报功能示例"""
    print("\n" + "="*50)
    print("📰 新闻播报功能示例")
    print("="*50)
    
    client = ProactiveGreetingExample()
    device_id = "ESP32_NEWS"
    
    user_info = {
        "id": "user_news",
        "name": "张伯伯",
        "age": 72,
        "location": "北京",
        "interests": ["健康", "社区活动", "养生"]
    }
    
    # 新闻播报示例
    news_scenarios = [
        {
            "content": "为您播报今日重要新闻",
            "description": "基础新闻播报"
        },
        {
            "content": "健康新闻：专家建议老年人适量运动",
            "description": "健康类新闻"
        },
        {
            "content": "社区新闻：本周末将举办老年人活动",
            "description": "社区类新闻"
        },
        {
            "content": "养生资讯：秋季养生小贴士",
            "description": "养生类新闻"
        }
    ]
    
    for scenario in news_scenarios:
        print(f"📤 发送新闻播报：{scenario['description']}")
        await client.send_greeting(
            device_id=device_id,
            content=scenario['content'],
            category="news",
            user_info=user_info
        )
        await asyncio.sleep(2)  # 等待处理
    
    print("✅ 新闻播报示例完成")


async def demo_music_playback():
    """音乐播放功能示例"""
    print("\n" + "="*50)
    print("🎵 音乐播放功能示例")
    print("="*50)
    
    client = ProactiveGreetingExample()
    device_id = "ESP32_MUSIC"
    
    user_info = {
        "id": "user_music",
        "name": "李奶奶",
        "age": 68,
        "location": "上海",
        "interests": ["民谣", "古典音乐", "老歌"],
        "preferences": {
            "music_style": "peaceful",
            "favorite_era": "80s",
            "language": "中文"
        }
    }
    
    # 音乐播放示例
    music_scenarios = [
        {
            "content": "为您播放轻松的音乐",
            "description": "基础音乐播放",
            "category": "music"
        },
        {
            "content": "今天天气不错，让我们听点轻松的音乐放松一下",
            "description": "轻松音乐推荐",
            "category": "music"
        },
        {
            "content": "播放一些您喜欢的怀旧老歌",
            "description": "怀旧音乐播放",
            "category": "entertainment"
        },
        {
            "content": "为您推荐一些适合老年人的古典音乐",
            "description": "古典音乐推荐",
            "category": "music"
        },
        {
            "content": "晚上时光，播放一些宁静的音乐帮助您放松",
            "description": "夜晚放松音乐",
            "category": "entertainment"
        }
    ]
    
    for scenario in music_scenarios:
        print(f"🎶 发送音乐播放：{scenario['description']}")
        await client.send_greeting(
            device_id=device_id,
            content=scenario['content'],
            category=scenario['category'],
            user_info=user_info
        )
        await asyncio.sleep(2)  # 等待处理
    
    print("✅ 音乐播放示例完成")


async def main():
    """主函数 - 运行所有示例"""
    print("🎉 ESP32 AI设备主动问候功能示例")
    print("="*60)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📋 将运行以下示例:")
    print("   1. 基础问候示例")
    print("   2. 不同类别问候示例") 
    print("   3. 新闻播报功能示例")
    print("   4. 音乐播放功能示例 (新增)")
    print("   5. 用户档案管理示例")
    print("   6. 错误处理示例")
    print("   7. 批量操作示例")
    print("   8. 状态监控示例")
    print("   9. 真实场景示例")
    print("  10. 综合测试示例")
    print("-" * 60)
    
    try:
        # 运行各种示例
        await demo_basic_greeting()
        await demo_different_categories()
        await demo_news_broadcast()  # 新闻播报示例
        await demo_music_playback()  # 新增音乐播放示例
        await demo_user_profile_management()
        await demo_error_handling()
        await demo_batch_operations()
        await demo_monitoring()
        await demo_real_world_scenarios()
        await demo_comprehensive_test()
        
        print("\n" + "="*60)
        print("🎊 所有示例运行完成！")
        print("💡 提示：请检查ESP32设备端是否正常接收和处理消息")
        
    except Exception as e:
        print(f"\n❌ 示例运行出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    print("🚀 启动主动问候功能示例...")
    print("📋 请确保:")
    print("   ✓ xiaozhi 服务器已启动")
    print("   ✓ MQTT 功能已启用")
    print("   ✓ EMQX 服务器可访问 (47.98.51.180)")
    print("   ✓ ESP32 设备在线并已订阅相关主题")
    print("\n⌨️  按 Ctrl+C 可随时退出\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⛔ 用户中断，程序退出")
    except Exception as e:
        print(f"\n\n💥 程序异常退出: {e}")
        import traceback
        traceback.print_exc()
#!/usr/bin/env python3
"""
第三方新闻API主动问候演示脚本
展示如何使用第三方新闻API生成智能问候语
"""

import json
import urllib.request
import urllib.parse
import time


def get_third_party_news():
    """获取第三方新闻"""
    print("📡 获取第三方新闻...")
    
    api_url = "https://whyta.cn/api/tx/bulletin"
    api_key = "d8c6d4c75ba0"
    
    try:
        params = urllib.parse.urlencode({"key": api_key})
        full_url = f"{api_url}?{params}"
        
        request = urllib.request.Request(full_url)
        request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                if data.get('code') == 200:
                    news_list = data.get('result', {}).get('list', [])
                    print(f"✅ 成功获取 {len(news_list)} 条新闻")
                    return news_list[:5]  # 返回前5条
    except Exception as e:
        print(f"❌ 获取新闻失败: {e}")
    
    return []


def filter_elderly_friendly_news(news_list):
    """筛选适合老年人的新闻"""
    print("🔍 筛选适合老年人的新闻...")
    
    friendly_news = []
    
    # 定义适合老年人的关键词
    positive_keywords = ["健康", "养生", "医疗", "社区", "服务", "便民", "保健", "安全", "政策", "福利"]
    # 定义需要过滤的关键词
    negative_keywords = ["暴力", "犯罪", "事故", "死亡", "灾难", "冲突"]
    
    for news in news_list:
        title = news.get('title', '')
        digest = news.get('digest', '')
        
        # 检查是否包含不适合的内容
        if any(keyword in title or keyword in digest for keyword in negative_keywords):
            continue
        
        # 优先选择包含正面关键词的新闻
        score = 0
        for keyword in positive_keywords:
            if keyword in title or keyword in digest:
                score += 1
        
        # 添加评分信息
        news['elderly_score'] = score
        friendly_news.append(news)
    
    # 按评分排序，优先推荐更适合的新闻
    friendly_news.sort(key=lambda x: x.get('elderly_score', 0), reverse=True)
    
    print(f"✅ 筛选出 {len(friendly_news)} 条适合老年人的新闻")
    return friendly_news[:3]  # 返回前3条最适合的


def format_news_for_greeting(news_list, user_info):
    """将新闻格式化为问候语"""
    print("🎙️ 格式化新闻为问候语...")
    
    if not news_list:
        return "今天暂无特别新闻，祝您有个愉快的一天！"
    
    user_name = user_info.get('name', '您')
    
    # 选择最合适的新闻
    main_news = news_list[0]
    title = main_news.get('title', '')
    digest = main_news.get('digest', '')
    
    # 推断新闻类别
    category = "综合"
    if any(keyword in title for keyword in ["健康", "医疗", "养生"]):
        category = "健康"
    elif any(keyword in title for keyword in ["社区", "服务", "便民"]):
        category = "社区"
    elif any(keyword in title for keyword in ["政策", "福利"]):
        category = "政策"
    
    # 生成个性化问候语
    if category == "健康":
        greeting = f"{user_name}，今天为您分享一条健康资讯：{title}。{digest[:40]}，希望对您的健康有帮助。"
    elif category == "社区":
        greeting = f"{user_name}，今天有社区方面的好消息：{title}。{digest[:40]}，让我们的生活更加便利。"
    elif category == "政策":
        greeting = f"{user_name}，今天有重要政策消息：{title}。{digest[:40]}，请您关注。"
    else:
        greeting = f"{user_name}，今天为您播报：{title}。{digest[:40]}。"
    
    # 控制长度
    if len(greeting) > 80:
        greeting = greeting[:77] + "..."
    
    print(f"✅ 生成问候语: {greeting}")
    return greeting


def simulate_llm_processing(greeting_text, user_info):
    """模拟LLM处理过程（实际应该调用真正的LLM）"""
    print("🤖 模拟LLM优化问候语...")
    
    user_name = user_info.get('name', '您')
    user_age = user_info.get('age', 0)
    
    # 模拟LLM优化（实际应该调用真正的LLM API）
    if user_age >= 70:
        # 老年人用更温和的语气
        optimized = greeting_text.replace("今天为您", "今天想和您")
        optimized = optimized.replace("播报", "分享")
        optimized = f"早上好，{user_name}！{optimized} 记得保重身体哦！"
    elif user_age >= 60:
        # 中老年人用亲切的语气
        optimized = f"您好，{user_name}！{greeting_text} 祝您今天心情愉快！"
    else:
        # 普通成年人
        optimized = f"您好！{greeting_text}"
    
    print(f"✅ LLM优化后: {optimized}")
    return optimized


def simulate_tts_and_delivery(final_text, device_id):
    """模拟TTS合成和语音下发"""
    print("🎤 模拟TTS语音合成...")
    print(f"📱 模拟发送到设备: {device_id}")
    
    # 模拟MQTT消息
    mqtt_message = {
        "cmd": "SPEAK",
        "text": final_text,
        "category": "news",
        "track_id": f"NEWS_{int(time.time())}",
        "timestamp": time.strftime("%H:%M:%S")
    }
    
    print("📨 模拟MQTT消息:")
    print(json.dumps(mqtt_message, ensure_ascii=False, indent=2))
    
    # 模拟设备响应
    print("✅ 模拟设备收到消息并播放语音")
    print("🔊 设备开始播放新闻问候语...")
    print("✅ 播放完成，设备进入对话模式")


def main():
    """主演示流程"""
    print("🎯 第三方新闻API主动问候完整演示")
    print("=" * 60)
    
    # 模拟用户信息
    user_info = {
        "id": "user_001",
        "name": "张奶奶",
        "age": 72,
        "interests": ["健康", "社区", "新闻"],
        "location": "北京"
    }
    
    device_id = "ESP32_NEWS_DEMO"
    
    print(f"👤 用户信息: {user_info['name']}, {user_info['age']}岁")
    print(f"📱 设备ID: {device_id}")
    print()
    
    # 步骤1: 获取第三方新闻
    news_list = get_third_party_news()
    if not news_list:
        print("❌ 无法获取新闻，演示结束")
        return
    
    print("\n📰 获取到的原始新闻:")
    for i, news in enumerate(news_list[:3], 1):
        print(f"   {i}. {news.get('title', 'N/A')}")
    print()
    
    # 步骤2: 筛选适合老年人的新闻
    filtered_news = filter_elderly_friendly_news(news_list)
    
    print("🎯 筛选后的新闻:")
    for i, news in enumerate(filtered_news, 1):
        score = news.get('elderly_score', 0)
        print(f"   {i}. {news.get('title', 'N/A')} (适合度: {score})")
    print()
    
    # 步骤3: 格式化为问候语
    greeting_text = format_news_for_greeting(filtered_news, user_info)
    print()
    
    # 步骤4: LLM优化
    optimized_text = simulate_llm_processing(greeting_text, user_info)
    print()
    
    # 步骤5: TTS和设备下发
    simulate_tts_and_delivery(optimized_text, device_id)
    
    print("\n" + "=" * 60)
    print("🎉 完整的新闻问候流程演示完成!")
    print()
    print("📋 流程总结:")
    print("1. ✅ 从第三方API获取最新新闻")
    print("2. ✅ 智能筛选适合老年人的内容")
    print("3. ✅ 格式化为个性化问候语")
    print("4. ✅ 通过LLM优化语言风格")
    print("5. ✅ TTS合成并推送到ESP32设备")
    print()
    print("💡 实际集成说明:")
    print("- 这个演示展示了完整的数据流程")
    print("- 在实际系统中，会自动调用真正的LLM和TTS服务")
    print("- Java后端不可用时，自动切换到第三方API")
    print("- 通过MQTT实时推送到ESP32设备")
    print("- 设备播放完成后自动进入对话模式")


if __name__ == "__main__":
    main()

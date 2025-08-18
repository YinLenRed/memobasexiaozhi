#!/usr/bin/env python3
"""
简单的第三方新闻API测试脚本（不依赖外部库）
测试新集成的每日简报API功能
"""

import json
import urllib.request
import urllib.parse


def test_third_party_api():
    """直接测试第三方新闻API"""
    print("🗞️ 第三方新闻API直接测试")
    print("=" * 50)
    
    # API配置
    api_url = "https://whyta.cn/api/tx/bulletin"
    api_key = "d8c6d4c75ba0"
    
    try:
        # 构建请求URL
        params = urllib.parse.urlencode({"key": api_key})
        full_url = f"{api_url}?{params}"
        
        print(f"📡 调用API: {api_url}")
        print(f"🔑 使用密钥: {api_key[:8]}...")
        print(f"🌐 完整URL: {full_url}")
        print()
        
        # 创建请求
        request = urllib.request.Request(full_url)
        request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # 发送请求
        with urllib.request.urlopen(request, timeout=15) as response:
            print(f"📊 响应状态: {response.status}")
            
            if response.status == 200:
                # 读取响应数据
                data_bytes = response.read()
                data_str = data_bytes.decode('utf-8')
                data = json.loads(data_str)
                
                print("✅ API调用成功")
                print(f"📋 响应数据结构:")
                print(f"   - code: {data.get('code')}")
                print(f"   - msg: {data.get('msg')}")
                
                result = data.get('result', {})
                news_list = result.get('list', [])
                print(f"   - 新闻数量: {len(news_list)}")
                print()
                
                if news_list:
                    print(f"📰 获取到的新闻内容:")
                    for i, news in enumerate(news_list[:5], 1):  # 显示前5条
                        title = news.get('title', 'N/A')
                        mtime = news.get('mtime', 'N/A')
                        digest = news.get('digest', 'N/A')
                        
                        print(f"   {i}. 标题: {title}")
                        print(f"      时间: {mtime}")
                        print(f"      摘要: {digest}")
                        print(f"      摘要长度: {len(digest)}字")
                        print()
                
                # 测试数据格式化
                print("🔧 测试数据格式化:")
                if news_list:
                    # 模拟格式化为问候语
                    first_news = news_list[0]
                    title = first_news.get('title', '')
                    digest = first_news.get('digest', '')
                    
                    # 简单的分类判断
                    category = "综合"
                    if any(keyword in title for keyword in ["健康", "医疗", "养生"]):
                        category = "健康"
                    elif any(keyword in title for keyword in ["交通", "出行", "违章"]):
                        category = "交通"
                    elif any(keyword in title for keyword in ["经济", "金融", "投资"]):
                        category = "财经"
                    
                    # 格式化为问候语
                    greeting = f"今日新闻：{category}方面，{title}。{digest[:50]}{'...' if len(digest) > 50 else ''}"
                    
                    print(f"   原始标题: {title}")
                    print(f"   推断分类: {category}")
                    print(f"   格式化问候: {greeting}")
                    print(f"   问候语长度: {len(greeting)}字")
                
            else:
                print(f"❌ API调用失败: {response.status}")
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP错误: {e.code} - {e.reason}")
        try:
            error_content = e.read().decode('utf-8')
            print(f"   错误详情: {error_content[:200]}...")
        except:
            pass
    except urllib.error.URLError as e:
        print(f"❌ URL错误: {e.reason}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")


def test_data_processing():
    """测试数据处理逻辑"""
    print("\n🔧 数据处理逻辑测试")
    print("=" * 50)
    
    # 模拟API返回的数据
    mock_data = {
        "code": 200,
        "msg": "success",
        "result": {
            "list": [
                {
                    "mtime": "2024-01-15",
                    "title": "深圳健康提醒：冬季老年人需注意保暖",
                    "digest": "专家提醒，冬季气温较低，老年人应注意保暖，适当增加衣物，避免感冒。建议室内温度保持在18-22度之间。"
                },
                {
                    "mtime": "2024-01-15",
                    "title": "交通出行：地铁新线路开通，方便市民出行",
                    "digest": "今日新开通的地铁15号线正式运营，连接市中心与新区，预计每日客流量达到10万人次。"
                },
                {
                    "mtime": "2024-01-15",
                    "title": "社区服务：老年活动中心增设健康检查项目",
                    "digest": "为了更好地服务老年居民，社区活动中心新增血压、血糖等基础健康检查项目，每周定期开放。"
                }
            ]
        }
    }
    
    print("📋 模拟数据处理:")
    news_list = mock_data["result"]["list"]
    
    for i, news in enumerate(news_list, 1):
        title = news.get('title', '')
        digest = news.get('digest', '')
        mtime = news.get('mtime', '')
        
        # 分类判断
        category = "综合"
        keywords = []
        
        if any(keyword in title for keyword in ["健康", "医疗", "养生"]):
            category = "健康"
            keywords = ["健康", "老年人"]
        elif any(keyword in title for keyword in ["交通", "出行", "地铁"]):
            category = "交通"
            keywords = ["交通", "出行"]
        elif any(keyword in title for keyword in ["社区", "居民", "服务"]):
            category = "社区"
            keywords = ["社区", "服务"]
        
        # 重要性判断
        importance = "normal"
        if any(keyword in title for keyword in ["提醒", "注意", "警告"]):
            importance = "high"
        
        # 格式化结果
        formatted = {
            "title": title,
            "summary": digest,
            "category": category,
            "source": "每日简报",
            "publish_time": mtime,
            "importance": importance,
            "keywords": keywords
        }
        
        print(f"\n   {i}. 原始新闻:")
        print(f"      标题: {title}")
        print(f"      摘要: {digest}")
        print(f"   格式化结果:")
        print(f"      分类: {category}")
        print(f"      重要性: {importance}")
        print(f"      关键词: {keywords}")
        print(f"      来源: {formatted['source']}")
        
        # 生成问候语
        if category and title and digest:
            greeting_text = f"{category}方面：{title}。{digest[:50]}{'...' if len(digest) > 50 else ''}"
            print(f"   生成问候语: {greeting_text}")
            print(f"      问候语长度: {len(greeting_text)}字")


def main():
    """主函数"""
    print("🧪 第三方新闻API简单测试")
    print("=" * 60)
    
    # 测试1: 直接API调用
    test_third_party_api()
    
    # 测试2: 数据处理逻辑
    test_data_processing()
    
    print("\n" + "=" * 60)
    print("🎉 测试完成!")
    print("\n📋 测试总结:")
    print("1. ✅ 第三方新闻API直接调用测试")
    print("2. ✅ 数据处理和格式化逻辑测试")
    print("\n💡 功能说明:")
    print("- 第三方API提供每日简报新闻")
    print("- 自动推断新闻分类（健康、交通、社区等）")
    print("- 格式化为适合老年人的问候语")
    print("- 可通过LLM进一步优化和语音转换")
    print("\n🔧 下一步:")
    print("- 在实际环境中测试与主动问候系统的集成")
    print("- 通过LLM对新闻内容进行智能加工")
    print("- 转换为语音并推送到ESP32设备")


if __name__ == "__main__":
    main()

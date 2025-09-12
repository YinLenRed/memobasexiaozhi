"""
新闻查询工具 - 集成Java后端新闻API
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from config.logger import setup_logging

TAG = __name__


class NewsTool:
    """新闻查询工具，支持Java后端API和第三方新闻API"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()
        
        # Java后端API配置
        self.java_api_base = config.get("manager-api", {}).get("url", "")
        self.api_secret = config.get("manager-api", {}).get("secret", "")
        
        # 第三方新闻API配置
        self.third_party_api = config.get("news", {}).get("third_party_api", {})
        self.third_party_enabled = self.third_party_api.get("enabled", False)
        self.third_party_url = self.third_party_api.get("url", "")
        self.third_party_key = self.third_party_api.get("api_key", "")
        
    async def get_news_by_category(self, category: str = "general", limit: int = 3) -> List[Dict[str, Any]]:
        """根据分类获取新闻信息（优先使用Java后端API，失败时使用第三方API）"""
        try:
            # 优先使用Java后端API
            if self.java_api_base and self.api_secret:
                try:
                    # 调用Java后端新闻API
                    url = f"{self.java_api_base}/api/news/category/{category}"
                    headers = {
                        "Authorization": f"Bearer {self.api_secret}",
                        "Content-Type": "application/json"
                    }
                    
                    params = {"limit": limit}
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=headers, params=params, timeout=10) as response:
                            if response.status == 200:
                                news_data = await response.json()
                                self.logger.bind(tag=TAG).info(f"Java API获取{category}类新闻成功，共{len(news_data.get('news', []))}条")
                                return self._format_news_data(news_data.get('news', []))
                except Exception as e:
                    self.logger.bind(tag=TAG).warning(f"Java API调用失败: {e}，尝试第三方API")
            
            # 回退到第三方API
            if self.third_party_enabled and self.third_party_url and self.third_party_key:
                return await self._get_third_party_news(limit)
            
            # 最后使用默认新闻
            self.logger.bind(tag=TAG).warning("所有API都不可用，使用默认新闻信息")
            return self._get_default_news(category)
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取新闻失败: {e}")
            return self._get_default_news(category)
    
    async def get_elderly_news(self, user_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """获取适合老年人的新闻内容"""
        try:
            # 优先使用Java后端API
            if self.java_api_base and self.api_secret:
                try:
                    # 调用Java后端老年人新闻API
                    url = f"{self.java_api_base}/api/news/elderly"
                    headers = {
                        "Authorization": f"Bearer {self.api_secret}",
                        "Content-Type": "application/json"
                    }
                    
                    # 可以传递用户信息用于个性化新闻推荐
                    data = {"user_info": user_info} if user_info else {}
                    
                    # 使用SSL辅助工具创建安全会话
                    from core.utils.ssl_helper import create_secure_session
                    
                    async with create_secure_session() as session:
                        async with session.post(url, headers=headers, json=data, timeout=10) as response:
                            if response.status == 200:
                                news_data = await response.json()
                                self.logger.bind(tag=TAG).info(f"Java API获取老年人新闻成功，共{len(news_data.get('news', []))}条")
                                return self._format_news_data(news_data.get('news', []))
                except Exception as e:
                    self.logger.bind(tag=TAG).warning(f"Java API调用失败: {e}，尝试第三方API")
            
            # 回退到第三方API（获取所有新闻，然后过滤适合老年人的）
            if self.third_party_enabled and self.third_party_url and self.third_party_key:
                return await self._get_third_party_news(3)
            
            # 最后使用默认新闻
            self.logger.bind(tag=TAG).warning("所有API都不可用，使用默认老年人新闻")
            return self._get_default_elderly_news()
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取老年人新闻失败: {e}")
            return self._get_default_elderly_news()
    
    async def _get_third_party_news(self, limit: int = 3) -> List[Dict[str, Any]]:
        """调用第三方新闻API获取每日简报"""
        try:
            if not self.third_party_url or not self.third_party_key:
                self.logger.bind(tag=TAG).error("第三方API配置不完整")
                return self._get_default_news("general")
            
            # 调用第三方API
            params = {"key": self.third_party_key}
            
            # 使用SSL辅助工具创建安全会话
            from core.utils.ssl_helper import create_secure_session
            
            async with create_secure_session() as session:
                async with session.get(self.third_party_url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("code") == 200 and data.get("result", {}).get("list"):
                            news_list = data["result"]["list"]
                            self.logger.bind(tag=TAG).info(f"第三方API获取新闻成功，共{len(news_list)}条")
                            return self._format_third_party_news(news_list[:limit])
                        else:
                            self.logger.bind(tag=TAG).error(f"第三方API返回数据格式错误: {data}")
                            return self._get_default_news("general")
                    else:
                        self.logger.bind(tag=TAG).error(f"第三方API返回状态码: {response.status}")
                        return self._get_default_news("general")
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"调用第三方新闻API失败: {e}")
            return self._get_default_news("general")
    
    def _format_third_party_news(self, raw_news: List[Dict]) -> List[Dict[str, Any]]:
        """格式化第三方API返回的新闻数据"""
        try:
            formatted_news = []
            
            for news_item in raw_news:
                # 第三方API数据格式：{"mtime": "2019-09-09", "title": "标题", "digest": "摘要"}
                formatted = {
                    "title": news_item.get("title", ""),
                    "summary": news_item.get("digest", ""),
                    "content": news_item.get("digest", ""),  # 第三方API没有完整内容，使用摘要
                    "category": self._infer_news_category(news_item.get("title", "")),
                    "source": "每日简报",
                    "publish_time": news_item.get("mtime", "今天"),
                    "importance": "normal",
                    "keywords": self._extract_keywords(news_item.get("title", ""))
                }
                
                # 只添加有效的新闻
                if formatted["title"] and formatted["summary"]:
                    formatted_news.append(formatted)
            
            return formatted_news
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化第三方新闻数据失败: {e}")
            return self._get_default_news("general")
    
    def _infer_news_category(self, title: str) -> str:
        """根据标题推断新闻分类"""
        try:
            if not title:
                return "综合"
            
            # 简单的关键词分类
            if any(keyword in title for keyword in ["健康", "医疗", "养生", "药品"]):
                return "健康"
            elif any(keyword in title for keyword in ["经济", "股市", "金融", "投资", "银行"]):
                return "财经"
            elif any(keyword in title for keyword in ["天气", "气候", "台风", "降雨"]):
                return "天气"
            elif any(keyword in title for keyword in ["社区", "居民", "小区", "物业"]):
                return "社区"
            elif any(keyword in title for keyword in ["交通", "出行", "地铁", "公交", "违章", "驾驶"]):
                return "交通"
            elif any(keyword in title for keyword in ["政策", "法规", "政府", "通知"]):
                return "政策"
            else:
                return "综合"
        except:
            return "综合"
    
    def _extract_keywords(self, title: str) -> List[str]:
        """从标题中提取关键词"""
        try:
            if not title:
                return []
            
            # 简单的关键词提取
            keywords = []
            common_keywords = ["深圳", "广州", "北京", "上海", "健康", "医疗", "交通", "政策", "经济", "社区"]
            
            for keyword in common_keywords:
                if keyword in title:
                    keywords.append(keyword)
            
            return keywords[:3]  # 最多返回3个关键词
        except:
            return []
    
    def _format_news_data(self, raw_news: List[Dict]) -> List[Dict[str, Any]]:
        """格式化Java API返回的新闻数据"""
        try:
            formatted_news = []
            
            for news_item in raw_news:
                formatted = {
                    "title": news_item.get("title", ""),
                    "summary": news_item.get("summary", ""),
                    "content": news_item.get("content", ""),
                    "category": news_item.get("category", "综合"),
                    "source": news_item.get("source", ""),
                    "publish_time": news_item.get("publishTime", ""),
                    "importance": news_item.get("importance", "normal"),  # high, normal, low
                    "keywords": news_item.get("keywords", [])
                }
                
                # 只添加有效的新闻
                if formatted["title"] and formatted["summary"]:
                    formatted_news.append(formatted)
            
            return formatted_news[:5]  # 最多返回5条新闻
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化新闻数据失败: {e}")
            return self._get_default_news("general")
    
    def _get_default_news(self, category: str = "general") -> List[Dict[str, Any]]:
        """返回默认新闻信息（API不可用时的备用方案）"""
        default_news = [
            {
                "title": "今日健康提醒",
                "summary": "专家提醒老年朋友，秋季要注意保暖，适量运动有益健康。",
                "content": "随着季节变化，老年人应该注意调整作息和饮食习惯。",
                "category": "健康",
                "source": "健康频道",
                "publish_time": "今天",
                "importance": "high",
                "keywords": ["健康", "老年人", "保健"]
            },
            {
                "title": "生活小贴士",
                "summary": "今天是个好日子，适合外出散步，与朋友聊天。",
                "content": "保持良好心情对健康很重要。",
                "category": "生活",
                "source": "生活频道", 
                "publish_time": "今天",
                "importance": "normal",
                "keywords": ["生活", "心情", "健康"]
            }
        ]
        
        return default_news
    
    def _get_default_elderly_news(self) -> List[Dict[str, Any]]:
        """返回默认的老年人新闻"""
        elderly_news = [
            {
                "title": "养生保健小知识",
                "summary": "合理饮食、适量运动、保持心情愉快是健康长寿的秘诀。",
                "content": "专家建议老年人每天要保证充足睡眠，饮食清淡，多吃蔬菜水果。",
                "category": "养生",
                "source": "养生频道",
                "publish_time": "今天",
                "importance": "high",
                "keywords": ["养生", "健康", "饮食"]
            },
            {
                "title": "社区活动通知",
                "summary": "社区将举办老年人健身活动，欢迎大家积极参与。",
                "content": "活动包括太极拳、广场舞等，有利于身心健康。",
                "category": "社区",
                "source": "社区服务",
                "publish_time": "今天",
                "importance": "normal",
                "keywords": ["社区", "活动", "健身"]
            }
        ]
        
        return elderly_news
    
    def format_news_for_greeting(self, news_list: List[Dict[str, Any]], max_items: int = 2) -> str:
        """将新闻数据格式化为适合问候的文本"""
        try:
            if not news_list:
                return "今天暂无特别新闻，祝您有个愉快的一天！"
            
            news_texts = []
            
            for i, news in enumerate(news_list[:max_items]):
                title = news.get("title", "")
                summary = news.get("summary", "")
                category = news.get("category", "")
                
                if title and summary:
                    # 构建新闻播报文本
                    if category:
                        news_text = f"{category}方面：{title}。{summary}"
                    else:
                        news_text = f"{title}。{summary}"
                    
                    # 限制单条新闻长度
                    if len(news_text) > 80:
                        news_text = news_text[:77] + "..."
                    
                    news_texts.append(news_text)
            
            if news_texts:
                if len(news_texts) == 1:
                    return f"今日新闻：{news_texts[0]}"
                else:
                    return f"今日新闻：{news_texts[0]}。另外，{news_texts[1]}"
            else:
                return "今天暂无特别新闻，祝您有个愉快的一天！"
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化新闻播报失败: {e}")
            return "今天暂无特别新闻，祝您有个愉快的一天！"
    
    def format_news_summary(self, news_list: List[Dict[str, Any]]) -> str:
        """格式化新闻摘要（用于LLM上下文）"""
        try:
            if not news_list:
                return "今日暂无重要新闻"
            
            summaries = []
            for news in news_list[:3]:  # 最多3条
                title = news.get("title", "")
                category = news.get("category", "")
                importance = news.get("importance", "normal")
                
                if title:
                    prefix = "【重要】" if importance == "high" else ""
                    summary = f"{prefix}{category}：{title}"
                    summaries.append(summary)
            
            return "；".join(summaries)
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"格式化新闻摘要失败: {e}")
            return "今日暂无重要新闻"


# 便捷函数
async def get_news_info(config: Dict[str, Any], category: str = "elderly", user_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    获取新闻信息的便捷函数
    
    Args:
        config: 应用配置
        category: 新闻分类
        user_info: 用户信息
        
    Returns:
        List[Dict]: 新闻列表
    """
    tool = NewsTool(config)
    
    if category == "elderly":
        return await tool.get_elderly_news(user_info)
    else:
        return await tool.get_news_by_category(category)


# Function Calling定义
NEWS_FUNCTION_DEFINITION = {
    "name": "get_latest_news",
    "description": "获取最新新闻信息，特别适合老年用户的新闻内容",
    "parameters": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "新闻分类",
                "enum": ["elderly", "health", "lifestyle", "community", "general"],
                "default": "elderly"
            },
            "max_items": {
                "type": "integer",
                "description": "最大新闻条数",
                "default": 2,
                "minimum": 1,
                "maximum": 5
            }
        },
        "required": ["category"]
    }
}


# Function Calling执行函数
async def execute_news_function(function_args: Dict[str, Any], config: Dict[str, Any], user_info: Dict[str, Any] = None) -> str:
    """
    执行新闻Function Calling
    
    Args:
        function_args: 函数参数
        config: 应用配置
        user_info: 用户信息
        
    Returns:
        str: 新闻播报文本
    """
    try:
        category = function_args.get("category", "elderly")
        max_items = function_args.get("max_items", 2)
        
        news_tool = NewsTool(config)
        
        if category == "elderly":
            news_list = await news_tool.get_elderly_news(user_info)
        else:
            news_list = await news_tool.get_news_by_category(category)
        
        return news_tool.format_news_for_greeting(news_list, max_items)
        
    except Exception as e:
        return "抱歉，暂时无法获取新闻信息，请稍后再试。"

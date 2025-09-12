"""
智能MCP条件过滤器
根据用户输入智能判断是否需要调用MCP功能，提升对话效率，节省不必要的费用
"""

import re
from typing import List, Dict, Any
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class SmartMCPFilter:
    """智能MCP调用条件过滤器"""
    
    def __init__(self):
        # 🔍 搜索相关关键词
        self.search_keywords = [
            # 直接搜索词
            "搜索", "查找", "查询", "搜一下", "搜一搜", "找一下", "找找",
            "帮我找", "帮我搜", "查看", "了解一下", "想知道", "想了解",
            
            # 网络搜索相关
            "百度", "谷歌", "网上搜", "上网查", "在线查询", "网络搜索",
            "互联网搜索", "网页搜索", "浏览器搜索",
            
            # 查询动作词
            "调查", "研究", "探索", "发现", "寻找", "获取信息",
            "获取资料", "查资料", "找资料", "要资料"
        ]
        
        # 🌐 实时性需求关键词
        self.realtime_keywords = [
            # 天气相关
            "天气", "气温", "温度", "下雨", "晴天", "阴天", "多云", "雪", "风",
            "气象", "天气预报", "今天天气", "明天天气", "最近天气", "湿度", "紫外线",
            
            # 股市金融
            "股价", "股票", "基金", "期货", "黄金价格", "汇率", "美元", "人民币",
            "上证指数", "深证指数", "恒生指数", "纳斯达克", "道琼斯",
            "比特币", "以太坊", "数字货币", "加密货币", "A股", "港股", "美股",
            "涨停", "跌停", "涨幅", "跌幅", "成交量", "市值", "PE", "PB",
            
            # 新闻时事  
            "新闻", "时事", "最新消息", "今日新闻", "头条", "热搜",
            "最近发生", "刚刚发生", "最新发生", "时政", "国际新闻",
            "突发新闻", "实时新闻", "今日要闻", "热点新闻",
            
            # 实时信息
            "现在", "当前", "最新", "实时", "即时", "刚刚", "最近",
            "今天", "昨天", "明天", "这几天", "近期", "最新情况",
            "实时数据", "即时数据", "最新数据", "当天", "今日",
            
            # 交通出行
            "路况", "堵车", "交通", "地铁", "公交", "航班", "火车",
            "高速", "限行", "出行", "导航", "实时路况", "交通状况",
            
            # 生活服务
            "开放时间", "营业时间", "电话号码", "地址", "位置",
            "附近", "周边", "距离", "怎么去", "路线", "门店", "商家",
            
            # 价格查询
            "价格", "多少钱", "费用", "收费", "成本", "报价",
            "最新价格", "当前价格", "市场价", "行情", "房价", "油价",
            
            # 体育赛事
            "比赛", "比分", "赛程", "球赛", "足球", "篮球", "比赛结果",
            "世界杯", "奥运会", "NBA", "英超", "中超", "实时比分",
            
            # 特定实时需求（用户示例：当天黄金价格）
            "当天", "当日", "今日", "现在的", "目前的", "最新的"
        ]
        
        # 🎵 娱乐查询关键词
        self.entertainment_keywords = [
            # 影视娱乐
            "电影", "电视剧", "综艺", "动漫", "纪录片", "短剧",
            "票房", "影评", "演员", "导演", "明星", "娱乐圈",
            
            # 音乐
            "歌曲", "音乐", "歌手", "专辑", "演唱会", "音乐排行榜",
            "新歌", "热门歌曲", "流行音乐",
            
            # 游戏
            "游戏", "手游", "端游", "网游", "游戏攻略", "游戏评测",
            "游戏排行", "新游戏"
        ]
        
        # 🚫 明确不需要MCP的场景
        self.exclude_keywords = [
            # 日常对话
            "你好", "再见", "谢谢", "不客气", "没关系", "好的", "知道了",
            "明白了", "收到", "嗯", "哦", "是的", "对的", "没错",
            
            # 设备控制（本地功能）
            "调节音量", "设置亮度", "开关", "播放音乐", "暂停", "停止",
            "调节", "设置", "控制", "打开", "关闭",
            
            # 系统功能（本地时间、任务管理等）
            "定时提醒", "设置闹钟", "任务列表", "修改任务", "删除任务",
            "现在几点", "几点了", "星期几", "今天几号", "电量", "存储空间",
            "设置提醒", "提醒我", "闹钟", "定时器", "倒计时",
            
            # 简单问答（不需要实时信息）
            "什么意思", "怎么读", "怎么写", "是什么", "为什么",
            "告诉我", "解释一下", "说说", "聊聊", "笑话", "故事"
        ]
        
        # 🔧 系统功能模式检测（优先级更高）
        self.system_function_patterns = [
            # 时间查询（本地功能）
            r"现在几点|几点了|当前时间|现在时间",
            # 任务管理（本地功能）  
            r"设置.*提醒|提醒.*设置|设置.*闹钟|闹钟.*设置",
            r"定时.*提醒|提醒.*定时|设置.*定时",
            # 播放控制（本地功能）
            r"播放.*音乐|音乐.*播放|播放.*歌",
            # 设备控制（本地功能）
            r"调节.*音量|音量.*调节|设置.*亮度|亮度.*设置"
        ]
    
    def should_enable_mcp(self, user_input: str) -> Dict[str, Any]:
        """
        判断是否需要启用MCP功能
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            Dict包含:
            - enabled: bool, 是否启用MCP
            - reason: str, 判断原因
            - keywords_matched: List[str], 匹配到的关键词
            - confidence: float, 置信度 (0-1)
        """
        user_input = user_input.strip().lower()
        
        # 预处理：移除标点符号
        clean_input = re.sub(r'[，。！？、；：""''（）【】\s]+', '', user_input)
        
        result = {
            "enabled": False,
            "reason": "default_disable",
            "keywords_matched": [],
            "confidence": 0.0
        }
        
        # 1. 🔧 优先检查系统功能模式（使用正则表达式，优先级最高）
        system_pattern_matched = self._check_system_patterns(clean_input)
        if system_pattern_matched:
            result.update({
                "enabled": False,
                "reason": "system_function_detected",
                "keywords_matched": [system_pattern_matched],
                "confidence": 0.95
            })
            logger.bind(tag=TAG).debug(f"🔧 检测到系统功能: {system_pattern_matched}")
            return result
        
        # 2. 🚫 检查排除关键词
        exclude_matched = self._check_keywords(clean_input, self.exclude_keywords)
        if exclude_matched:
            result.update({
                "enabled": False,
                "reason": "excluded_by_keywords",
                "keywords_matched": exclude_matched,
                "confidence": 0.9
            })
            logger.bind(tag=TAG).debug(f"🚫 排除MCP调用: 匹配排除关键词 {exclude_matched}")
            return result
        
        # 3. 🔍 检查搜索需求
        search_matched = self._check_keywords(clean_input, self.search_keywords)
        if search_matched:
            result.update({
                "enabled": True,
                "reason": "search_request",
                "keywords_matched": search_matched,
                "confidence": 0.95
            })
            logger.bind(tag=TAG).info(f"🔍 启用MCP: 检测到搜索需求 {search_matched}")
            return result
        
        # 3. 🌐 检查实时性需求
        realtime_matched = self._check_keywords(clean_input, self.realtime_keywords)
        if realtime_matched:
            result.update({
                "enabled": True,
                "reason": "realtime_request",
                "keywords_matched": realtime_matched,
                "confidence": 0.9
            })
            logger.bind(tag=TAG).info(f"🌐 启用MCP: 检测到实时性需求 {realtime_matched}")
            return result
        
        # 4. 🎵 检查娱乐查询需求
        entertainment_matched = self._check_keywords(clean_input, self.entertainment_keywords)
        if entertainment_matched:
            result.update({
                "enabled": True,
                "reason": "entertainment_request",
                "keywords_matched": entertainment_matched,
                "confidence": 0.8
            })
            logger.bind(tag=TAG).info(f"🎵 启用MCP: 检测到娱乐查询需求 {entertainment_matched}")
            return result
        
        # 5. 🤔 模糊判断：包含疑问词且可能需要外部信息
        if self._is_information_query(clean_input):
            result.update({
                "enabled": True,
                "reason": "potential_information_query",
                "keywords_matched": ["疑问词+信息需求"],
                "confidence": 0.6
            })
            logger.bind(tag=TAG).info(f"🤔 启用MCP: 检测到潜在信息查询需求")
            return result
        
        # 6. 默认不启用
        logger.bind(tag=TAG).debug(f"💬 不启用MCP: 识别为日常对话")
        return result
    
    def _check_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """检查文本中是否包含指定关键词"""
        matched = []
        for keyword in keywords:
            if keyword in text:
                matched.append(keyword)
        return matched
    
    def _check_system_patterns(self, text: str) -> str:
        """检查是否匹配系统功能模式（使用正则表达式）"""
        for pattern in self.system_function_patterns:
            if re.search(pattern, text):
                return pattern
        return ""
    
    def _is_information_query(self, text: str) -> bool:
        """判断是否为信息查询类问题"""
        # 疑问词
        question_words = ["什么", "怎么", "如何", "为什么", "哪里", "哪个", "谁", "何时", "多少"]
        
        # 信息需求词
        info_words = ["介绍", "原理", "方法", "步骤", "流程", "过程", "发展", "历史", "特点", "优缺点"]
        
        has_question = any(word in text for word in question_words)
        has_info_need = any(word in text for word in info_words)
        
        # 长度判断：较长的问题更可能需要外部信息
        is_complex = len(text) > 10
        
        return (has_question and has_info_need) or (has_question and is_complex)
    
    def get_filtered_mcp_tools(self, all_mcp_tools: List[Dict], filter_result: Dict[str, Any]) -> List[Dict]:
        """
        根据过滤结果返回相应的MCP工具子集
        
        Args:
            all_mcp_tools: 所有可用的MCP工具
            filter_result: should_enable_mcp的返回结果
            
        Returns:
            List[Dict]: 过滤后的MCP工具列表
        """
        if not filter_result["enabled"]:
            return []
        
        reason = filter_result["reason"]
        
        # 根据不同原因返回不同的工具子集
        if reason == "search_request":
            # 搜索需求：返回搜索相关工具
            return self._filter_tools_by_name(all_mcp_tools, ["search", "web", "bocha"])
        
        elif reason == "realtime_request":
            # 实时需求：返回实时信息工具
            return self._filter_tools_by_name(all_mcp_tools, ["weather", "news", "stock", "realtime"])
        
        elif reason == "entertainment_request":
            # 娱乐需求：返回娱乐相关工具
            return self._filter_tools_by_name(all_mcp_tools, ["movie", "music", "entertainment"])
        
        else:
            # 其他情况：返回所有工具（但优先级较低）
            return all_mcp_tools
    
    def _filter_tools_by_name(self, tools: List[Dict], keywords: List[str]) -> List[Dict]:
        """根据工具名称关键词过滤工具"""
        filtered = []
        for tool in tools:
            tool_name = tool.get("function", {}).get("name", "").lower()
            tool_desc = tool.get("function", {}).get("description", "").lower()
            
            # 检查工具名称或描述是否包含关键词
            if any(keyword in tool_name or keyword in tool_desc for keyword in keywords):
                filtered.append(tool)
        
        # 如果没有匹配的专用工具，返回所有工具
        return filtered if filtered else tools


# 全局实例
smart_mcp_filter = SmartMCPFilter()


def should_enable_mcp_for_input(user_input: str) -> Dict[str, Any]:
    """
    对外接口：判断输入是否需要MCP功能
    
    Args:
        user_input: 用户输入
        
    Returns:
        Dict: 包含enabled, reason, keywords_matched, confidence
    """
    return smart_mcp_filter.should_enable_mcp(user_input)


def get_smart_filtered_mcp_tools(user_input: str, all_mcp_tools: List[Dict]) -> List[Dict]:
    """
    对外接口：获取智能过滤后的MCP工具列表
    
    Args:
        user_input: 用户输入
        all_mcp_tools: 所有可用的MCP工具
        
    Returns:
        List[Dict]: 过滤后的MCP工具列表
    """
    filter_result = smart_mcp_filter.should_enable_mcp(user_input)
    return smart_mcp_filter.get_filtered_mcp_tools(all_mcp_tools, filter_result)

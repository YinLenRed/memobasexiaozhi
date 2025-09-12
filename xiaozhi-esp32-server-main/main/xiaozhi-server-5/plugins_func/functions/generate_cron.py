import re
from datetime import datetime, timedelta
from plugins_func.register import register_function, ToolType, ActionResponse, Action

generate_cron_function_desc = {
    "type": "function",
    "function": {
        "name": "generate_cron",
        "description": (
            "根据用户描述的时间生成cron表达式。"
            "支持解析各种自然语言时间描述，如：每天几点、每周几、每月几号、具体时间等。"
            "可以处理如'每天早上8点'、'每周一上午9点半'、'每月15号下午2点'等描述。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "time_description": {
                    "type": "string",
                    "description": "用户描述的时间，例如：'每天早上8点'、'每周一上午9点半'、'每月15号下午2点'等",
                },
                "timezone": {
                    "type": "string",
                    "description": "时区，默认为'Asia/Shanghai'",
                    "default": "Asia/Shanghai"
                }
            },
            "required": ["time_description"],
        },
    },
}


class CronGenerator:
    """Cron表达式生成器"""
    
    def __init__(self):
        # 时间关键词映射
        self.time_keywords = {
            '早上': (6, 12), '上午': (6, 12), '早晨': (6, 12),
            '中午': (12, 14), '下午': (12, 18), '傍晚': (17, 20),
            '晚上': (18, 23), '夜里': (0, 6), '深夜': (23, 6),
            '凌晨': (0, 6)
        }
        
        # 星期映射
        self.weekday_map = {
            '周一': 1, '星期一': 1, '礼拜一': 1,
            '周二': 2, '星期二': 2, '礼拜二': 2,
            '周三': 3, '星期三': 3, '礼拜三': 3,
            '周四': 4, '星期四': 4, '礼拜四': 4,
            '周五': 5, '星期五': 5, '礼拜五': 5,
            '周六': 6, '星期六': 6, '礼拜六': 6,
            '周日': 0, '周天': 0, '星期日': 0, '星期天': 0, '礼拜日': 0, '礼拜天': 0
        }
        
        # 频率映射
        self.frequency_map = {
            '每天': 'daily', '天天': 'daily', '每日': 'daily',
            '每周': 'weekly', '每星期': 'weekly',
            '每月': 'monthly', '每个月': 'monthly',
            '每年': 'yearly', '每隔': 'interval'
        }

    def parse_time_description(self, description):
        """解析时间描述"""
        description = description.strip()
        result = {
            'frequency': 'once',  # daily, weekly, monthly, yearly, interval, once
            'hour': None,
            'minute': 0,
            'day_of_month': None,
            'day_of_week': None,
            'month': None,
            'interval': None
        }
        
        # 检测频率
        for freq_key, freq_value in self.frequency_map.items():
            if freq_key in description:
                result['frequency'] = freq_value
                break
        
        # 检测星期
        for week_key, week_value in self.weekday_map.items():
            if week_key in description:
                result['day_of_week'] = week_value
                result['frequency'] = 'weekly'
                break
        
        # 解析具体时间（小时:分钟）
        time_patterns = [
            r'(\d{1,2})[：:点](\d{1,2})[分]?',  # 8:30, 8点30分
            r'(\d{1,2})[点]半',  # 8点半
            r'(\d{1,2})[点]',  # 8点
            r'(\d{1,2})[：:](\d{1,2})',  # 8:30
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, description)
            if match:
                hour = int(match.group(1))
                if '半' in pattern:
                    minute = 30
                elif len(match.groups()) > 1:
                    minute = int(match.group(2))
                else:
                    minute = 0
                
                # 处理12小时制
                if any(keyword in description for keyword in ['下午', '晚上', '傍晚']) and hour < 12:
                    hour += 12
                elif any(keyword in description for keyword in ['早上', '上午', '凌晨']) and hour == 12:
                    hour = 0
                
                result['hour'] = hour
                result['minute'] = minute
                break
        
        # 如果没有具体时间但有时间段关键词，使用默认时间
        if result['hour'] is None:
            for keyword, (start_hour, end_hour) in self.time_keywords.items():
                if keyword in description:
                    result['hour'] = start_hour
                    break
        
        # 解析月份中的日期
        day_match = re.search(r'(\d{1,2})[号日]', description)
        if day_match:
            result['day_of_month'] = int(day_match.group(1))
            result['frequency'] = 'monthly'
        
        # 解析月份
        month_match = re.search(r'(\d{1,2})[月]', description)
        if month_match:
            result['month'] = int(month_match.group(1))
            result['frequency'] = 'yearly'
        
        # 解析间隔
        interval_match = re.search(r'每隔(\d+)([天小时分钟])', description)
        if interval_match:
            interval_num = int(interval_match.group(1))
            interval_unit = interval_match.group(2)
            result['interval'] = (interval_num, interval_unit)
            result['frequency'] = 'interval'
        
        return result

    def generate_cron_expression(self, parsed_time):
        """根据解析结果生成cron表达式"""
        # cron格式: 秒 分 时 日 月 周
        minute = parsed_time.get('minute', 0)
        hour = parsed_time.get('hour', 0)
        day_of_month = parsed_time.get('day_of_month', '*')
        month = parsed_time.get('month', '*')
        day_of_week = parsed_time.get('day_of_week', '*')
        frequency = parsed_time.get('frequency', 'once')
        
        # 处理不同频率
        if frequency == 'daily':
            # 每天
            return f"0 {minute} {hour} * * *"
        
        elif frequency == 'weekly':
            # 每周
            return f"0 {minute} {hour} * * {day_of_week}"
        
        elif frequency == 'monthly':
            # 每月
            day = day_of_month if day_of_month != '*' else 1
            return f"0 {minute} {hour} {day} * *"
        
        elif frequency == 'yearly':
            # 每年
            day = day_of_month if day_of_month != '*' else 1
            month_val = month if month != '*' else 1
            return f"0 {minute} {hour} {day} {month_val} *"
        
        elif frequency == 'interval':
            # 间隔执行
            interval_num, interval_unit = parsed_time.get('interval', (1, '天'))
            if interval_unit == '天':
                return f"0 {minute} {hour} */{interval_num} * *"
            elif interval_unit == '小时':
                return f"0 {minute} */{interval_num} * * *"
            elif interval_unit == '分钟':
                return f"0 */{interval_num} * * * *"
        
        else:
            # 一次性执行（默认每天）
            return f"0 {minute} {hour} * * *"

    def get_cron_description(self, cron_expression, time_description):
        """获取cron表达式的描述"""
        parts = cron_expression.split()
        if len(parts) != 6:
            return "无效的cron表达式"
        
        second, minute, hour, day, month, weekday = parts
        
        desc_parts = []
        
        # 时间部分
        if hour != '*' and minute != '*':
            if minute.isdigit():
                desc_parts.append(f"{hour}:{int(minute):02d}")
            else:
                desc_parts.append(f"{hour}点{minute}分")
        elif hour != '*':
            desc_parts.append(f"{hour}点")
        
        # 频率部分
        if day != '*' and month != '*':
            desc_parts.append(f"每年{month}月{day}日")
        elif day != '*':
            desc_parts.append(f"每月{day}日")
        elif weekday != '*':
            weekday_names = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
            if weekday.isdigit():
                desc_parts.append(f"每{weekday_names[int(weekday)]}")
        else:
            desc_parts.append("每天")
        
        return " ".join(desc_parts) + f" (原描述: {time_description})"


@register_function("generate_cron", generate_cron_function_desc, ToolType.WAIT)
def generate_cron(time_description, timezone="Asia/Shanghai"):
    """
    根据用户描述的时间生成cron表达式
    
    Args:
        time_description: 用户描述的时间
        timezone: 时区，默认为Asia/Shanghai
    
    Returns:
        ActionResponse: 包含cron表达式和说明的响应
    """
    try:
        generator = CronGenerator()
        
        # 解析时间描述
        parsed_time = generator.parse_time_description(time_description)
        
        # 生成cron表达式
        cron_expression = generator.generate_cron_expression(parsed_time)
        
        # 生成描述
        description = generator.get_cron_description(cron_expression, time_description)
        
        # 构建响应文本
        response_text = f"""根据您的时间描述生成了以下cron表达式：

时间描述: {time_description}
Cron表达式: {cron_expression}
执行规律: {description}
时区: {timezone}

Cron表达式格式说明: 秒 分 时 日 月 周
- 秒: 0-59
- 分: 0-59  
- 时: 0-23
- 日: 1-31
- 月: 1-12
- 周: 0-6 (0表示周日)

解析详情:
- 频率类型: {parsed_time.get('frequency', '未知')}
- 小时: {parsed_time.get('hour', '未指定')}
- 分钟: {parsed_time.get('minute', 0)}
- 日期: {parsed_time.get('day_of_month', '未指定')}
- 星期: {parsed_time.get('day_of_week', '未指定')}
- 月份: {parsed_time.get('month', '未指定')}
"""
        
        return ActionResponse(Action.REQLLM, response_text, {
            'cron_expression': cron_expression,
            'description': description,
            'parsed_time': parsed_time,
            'timezone': timezone
        })
        
    except Exception as e:
        error_text = f"生成cron表达式时出现错误: {str(e)}\n请检查时间描述是否正确，例如：'每天早上8点'、'每周一上午9点半'等"
        return ActionResponse(Action.REQLLM, error_text, None)

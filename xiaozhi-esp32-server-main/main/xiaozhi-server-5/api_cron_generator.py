#!/usr/bin/env python3
"""
Cron表达式生成API模块
为Java后端提供完整的cron表达式生成功能
基于现有的CronGenerator重构，提供标准化的API接口
"""

import re
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional


class CronGenerator:
    """Cron表达式生成器 - Java Quartz兼容版本"""
    
    def __init__(self):
        # 时间关键词映射
        self.time_keywords = {
            '早上': (6, 12), '上午': (6, 12), '早晨': (6, 12),
            '中午': (12, 14), '下午': (12, 18), '傍晚': (17, 20),
            '晚上': (18, 23), '夜里': (0, 6), '深夜': (23, 6),
            '凌晨': (0, 6)
        }
        
        # 星期映射 - Java Quartz格式 (1=周一, 0=周日)
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

    def parse_time_description(self, description: str) -> Dict[str, Any]:
        """解析时间描述"""
        description = description.strip()
        result = {
            'frequency': 'daily',  # 默认每天
            'hour': 8,             # 默认8点
            'minute': 0,           # 默认0分
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
        # 只有在没有解析到具体时间的情况下才使用时间段默认值
        time_found = False
        for pattern in time_patterns:
            if re.search(pattern, description):
                time_found = True
                break
        
        if not time_found:
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
        
        return result

    def generate_cron_expression(self, parsed_time: Dict[str, Any]) -> str:
        """根据解析结果生成Java Quartz兼容的cron表达式"""
        # Java Quartz格式: 秒 分 时 日 月 周
        minute = parsed_time.get('minute', 0)
        hour = parsed_time.get('hour', 8)
        day_of_month = parsed_time.get('day_of_month')
        month = parsed_time.get('month')
        day_of_week = parsed_time.get('day_of_week')
        frequency = parsed_time.get('frequency', 'daily')
        
        # 处理不同频率
        if frequency == 'daily':
            # 每天 - 日字段和周字段不能同时指定，使用?
            return f"0 {minute} {hour} * * ?"
        
        elif frequency == 'weekly':
            # 每周 - 当指定星期时，日字段必须为?
            return f"0 {minute} {hour} ? * {day_of_week}"
        
        elif frequency == 'monthly':
            # 每月 - 当指定日期时，周字段必须为?
            day = day_of_month if day_of_month else 1
            return f"0 {minute} {hour} {day} * ?"
        
        elif frequency == 'yearly':
            # 每年 - 当指定日期时，周字段必须为?
            day = day_of_month if day_of_month else 1
            month_val = month if month else 1
            return f"0 {minute} {hour} {day} {month_val} ?"
        
        else:
            # 默认每天
            return f"0 {minute} {hour} * * ?"

    def get_cron_description(self, cron_expression: str, original_description: str) -> str:
        """获取cron表达式的可读描述"""
        parts = cron_expression.split()
        if len(parts) != 6:
            return "无效的cron表达式"
        
        second, minute, hour, day, month, weekday = parts
        
        desc_parts = []
        
        # 时间部分
        if hour != '*' and minute != '*':
            desc_parts.append(f"每天{hour}:{int(minute):02d}")
        elif hour != '*':
            desc_parts.append(f"每天{hour}:00")
        
        # 频率部分
        if day != '*' and day != '?' and month != '*':
            desc_parts = [f"每年{month}月{day}日{hour}:{int(minute):02d}"]
        elif day != '*' and day != '?':
            desc_parts = [f"每月{day}日{hour}:{int(minute):02d}"]
        elif weekday != '*' and weekday != '?':
            weekday_names = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
            if weekday.isdigit() and 0 <= int(weekday) <= 6:
                desc_parts = [f"每{weekday_names[int(weekday)]}{hour}:{int(minute):02d}"]
        
        description = " ".join(desc_parts) if desc_parts else f"每天{hour}:{int(minute):02d}"
        return f"{description}执行"


class CronAPI:
    """Cron表达式生成API类 - 为Java后端提供标准化接口"""
    
    @staticmethod
    def generate_cron_expression(time_description: str, timezone: str = "Asia/Shanghai") -> Dict[str, Any]:
        """
        生成单个cron表达式
        
        Args:
            time_description: 时间描述，如"每天早上8点13分"
            timezone: 时区，默认Asia/Shanghai
            
        Returns:
            包含成功状态和cron表达式的字典
        """
        try:
            generator = CronGenerator()
            
            # 解析时间描述
            parsed_time = generator.parse_time_description(time_description)
            
            # 生成cron表达式
            cron_expression = generator.generate_cron_expression(parsed_time)
            
            # 生成描述
            description = generator.get_cron_description(cron_expression, time_description)
            
            return {
                "success": True,
                "data": {
                    "cron_expression": cron_expression,
                    "description": description,
                    "timezone": timezone,
                    "input_description": time_description,
                    "parsed_time": parsed_time
                },
                "message": "cron表达式生成成功",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"生成cron表达式失败: {str(e)}",
                "message": "cron表达式生成失败",
                "timestamp": datetime.now().isoformat()
            }
    
    @staticmethod
    def batch_generate(time_descriptions: List[str], timezone: str = "Asia/Shanghai") -> Dict[str, Any]:
        """
        批量生成cron表达式
        
        Args:
            time_descriptions: 时间描述列表
            timezone: 时区，默认Asia/Shanghai
            
        Returns:
            包含批量生成结果的字典
        """
        try:
            results = []
            success_count = 0
            failed_count = 0
            
            for desc in time_descriptions:
                result = CronAPI.generate_cron_expression(desc, timezone)
                results.append(result)
                
                if result["success"]:
                    success_count += 1
                else:
                    failed_count += 1
            
            return {
                "success": True,
                "total": len(time_descriptions),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results,
                "message": f"批量生成完成: {success_count}/{len(time_descriptions)} 成功",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"批量生成失败: {str(e)}",
                "message": "批量生成失败",
                "timestamp": datetime.now().isoformat()
            }
    
    @staticmethod
    def validate_cron_expression(cron_expression: str) -> bool:
        """
        验证cron表达式格式
        
        Args:
            cron_expression: 要验证的cron表达式
            
        Returns:
            是否为有效的Java Quartz格式
        """
        try:
            # 基本格式检查
            parts = cron_expression.strip().split()
            
            # Java Quartz格式必须有6个字段
            if len(parts) != 6:
                return False
            
            second, minute, hour, day, month, weekday = parts
            
            # 验证各字段范围
            # 秒: 0-59
            if not CronAPI._validate_field(second, 0, 59):
                return False
            
            # 分: 0-59
            if not CronAPI._validate_field(minute, 0, 59):
                return False
            
            # 时: 0-23
            if not CronAPI._validate_field(hour, 0, 23):
                return False
            
            # 日: 1-31 或 ?
            if day != '?' and not CronAPI._validate_field(day, 1, 31):
                return False
            
            # 月: 1-12
            if not CronAPI._validate_field(month, 1, 12):
                return False
            
            # 周: 0-6 或 ?
            if weekday != '?' and not CronAPI._validate_field(weekday, 0, 6):
                return False
            
            # Java Quartz规则：日字段和周字段不能同时指定
            if day != '?' and weekday != '?':
                return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def _validate_field(field: str, min_val: int, max_val: int) -> bool:
        """验证单个cron字段"""
        if field == '*':
            return True
        
        if field.isdigit():
            val = int(field)
            return min_val <= val <= max_val
        
        # 支持范围表达式，如 1-5
        if '-' in field:
            try:
                start, end = field.split('-')
                start_val = int(start)
                end_val = int(end)
                return (min_val <= start_val <= max_val and 
                       min_val <= end_val <= max_val and 
                       start_val <= end_val)
            except:
                return False
        
        # 支持列表表达式，如 1,3,5
        if ',' in field:
            try:
                values = field.split(',')
                for val in values:
                    if not val.isdigit():
                        return False
                    if not (min_val <= int(val) <= max_val):
                        return False
                return True
            except:
                return False
        
        # 支持步长表达式，如 */5
        if '/' in field:
            try:
                base, step = field.split('/')
                if base != '*' and not base.isdigit():
                    return False
                if not step.isdigit():
                    return False
                step_val = int(step)
                return step_val > 0
            except:
                return False
        
        return False
    
    @staticmethod
    def generate_cron_with_validation(time_description: str, timezone: str = "Asia/Shanghai") -> Dict[str, Any]:
        """
        生成cron表达式并验证
        
        Args:
            time_description: 时间描述
            timezone: 时区
            
        Returns:
            包含详细信息的生成结果
        """
        result = CronAPI.generate_cron_expression(time_description, timezone)
        
        if result["success"]:
            cron_expr = result["data"]["cron_expression"]
            is_valid = CronAPI.validate_cron_expression(cron_expr)
            
            result["data"]["validation"] = {
                "is_valid": is_valid,
                "format": "Java Quartz兼容" if is_valid else "格式错误"
            }
        
        return result


# 测试函数
def test_cron_generator():
    """测试cron生成器功能"""
    test_cases = [
        "每天早上8点13分",
        "每周一上午9点",
        "每月15号下午2点",
        "每年1月1日上午8点",
        "每天中午12点",
        "每周五下午6点半"
    ]
    
    print("🧪 测试Cron表达式生成器")
    print("=" * 50)
    
    for desc in test_cases:
        result = CronAPI.generate_cron_expression(desc)
        if result["success"]:
            data = result["data"]
            print(f"✅ {desc}")
            print(f"   → {data['cron_expression']}")
            print(f"   → {data['description']}")
            print()
        else:
            print(f"❌ {desc}: {result['error']}")
            print()


if __name__ == "__main__":
    test_cron_generator()

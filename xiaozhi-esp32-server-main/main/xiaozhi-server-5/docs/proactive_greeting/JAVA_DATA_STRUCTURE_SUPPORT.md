# Java后端新数据结构支持说明

## 📊 **数据结构变化**

### **新的Java后端数据结构**
```json
{
  "device_id": "f0:9e:9e:04:8a:44",
  "topic": "天气预报",
  "data": [
    {
      "title": "北京天气预报",
      "content": "天气json"
    }
  ],
  "prompt": "这是prompt"
}
```

### **处理后的单个事件**
```json
{
  "device_id": "f0:9e:9e:04:8a:44",
  "topic": "天气预报",
  "prompt": "这是prompt",
  "title": "北京天气预报",
  "content": "天气json"
}
```

## 🔧 **代码修改详情**

### **1. 事件类型检测增强**
`unified_event_service.py` - EventParser类

#### **天气事件检测**
```python
@staticmethod
def _is_weather_alert(data: Dict[str, Any]) -> bool:
    # 新增：支持topic字段检测
    topic = str(data.get("topic", ""))
    if "天气" in topic and ("预警" in topic or "警报" in topic or "预报" in topic):
        return True
    # 原有检测逻辑保持不变...
```

#### **节气事件检测**
```python
@staticmethod
def _is_solar_term(data: Dict[str, Any]) -> bool:
    # 新增：支持topic字段检测
    topic = str(data.get("topic", ""))
    if "节气" in topic or "立春" in topic or "立夏" in topic or "立秋" in topic or "立冬" in topic:
        return True
    # 原有检测逻辑保持不变...
```

#### **节假日事件检测**
```python
@staticmethod
def _is_holiday(data: Dict[str, Any]) -> bool:
    # 新增：支持topic字段检测
    topic = str(data.get("topic", ""))
    if ("节假日" in topic or "节日" in topic or "假期" in topic or 
        "春节" in topic or "中秋" in topic or "国庆" in topic or "元旦" in topic):
        return True
    # 原有检测逻辑保持不变...
```

### **2. 内容提取逻辑增强**
`unified_event_service.py` - `_generate_content_with_java_prompt`方法

#### **多字段内容提取**
```python
# 兼容Java后端的多种数据字段
result = (event_data.get("result") or 
         event_data.get("content") or      # 新增：支持content字段
         event_data.get("data") or 
         event_data.get("festival"))

# 如果没有单独的内容字段，尝试从title+content构建
if not result and event_data.get("title"):
    title = event_data.get("title", "")
    content = event_data.get("content", "")
    result = f"{title}: {content}" if content else title
```

## 🎯 **支持的事件类型映射**

| Topic关键词 | 识别类型 | 示例 |
|------------|----------|------|
| 天气预报、天气预警 | WEATHER_ALERT | "天气预报"、"天气预警" |
| 节气、立春等 | SOLAR_TERM | "立春节气"、"节气提醒" |
| 节假日、春节等 | HOLIDAY | "春节假期"、"国庆节日" |
| 其他 | UNKNOWN | "一般消息" |

## 📝 **数据处理流程**

### **1. 事件消息接收**
```python
# Java后端发送的完整数据
{
  "device_id": "f0:9e:9e:04:8a:44",
  "topic": "天气预报",
  "data": [...],
  "prompt": "这是prompt"
}
```

### **2. 全局字段提取**
```python
# 提取除data外的所有字段作为全局字段
global_fields = {
  "device_id": "f0:9e:9e:04:8a:44",
  "topic": "天气预报", 
  "prompt": "这是prompt"
}
```

### **3. 单个事件处理**
```python
# 遍历data数组，每个元素与全局字段合并
for single_event in data_array:
    merged_event = {**global_fields, **single_event}
    # 进行事件类型检测和内容生成
```

### **4. 事件类型检测**
- 检查`topic`字段关键词
- 检查传统字段（向后兼容）
- 返回相应的事件类型

### **5. 内容生成**
- 提取`prompt`字段
- 提取`content`或`title+content`组合
- 如果LLM可用，使用prompt生成智能内容
- 否则使用硬编码内容

## ✅ **兼容性保证**

### **向后兼容**
- ✅ 原有数据结构仍然支持
- ✅ 传统事件检测逻辑保持不变
- ✅ 现有配置和流程不受影响

### **渐进式增强**
- ✅ 新增`topic`字段支持
- ✅ 新增`content`字段支持
- ✅ 新增`title+content`组合支持
- ✅ 新增`prompt`字段的智能内容生成

## 🧪 **测试验证**

### **测试用例**
1. **天气预报事件**
   - Topic: "天气预报"
   - 期望类型: WEATHER_ALERT
   - Content提取: "北京天气预报: 天气json"

2. **节假日事件**
   - Topic: "春节假期"  
   - 期望类型: HOLIDAY
   - Prompt支持: ✅

3. **节气事件**
   - Topic: "立春节气"
   - 期望类型: SOLAR_TERM
   - Prompt支持: ✅

### **验证脚本**
- `简单测试Java数据结构.py` - 基础逻辑验证
- `测试Java新数据结构.py` - 完整服务验证

## 🎉 **修改效果**

### **功能增强**
- ✅ **智能事件识别** - 基于topic字段的快速事件分类
- ✅ **灵活内容提取** - 支持多种内容字段格式
- ✅ **智能内容生成** - 基于prompt的LLM内容生成
- ✅ **完整兼容性** - 支持新旧数据结构

### **系统稳定性**
- ✅ **渐进式部署** - 新旧格式同时支持
- ✅ **错误容错** - 字段缺失时的优雅降级
- ✅ **日志完整** - 详细的处理过程记录

## 📋 **使用建议**

### **Java后端配置**
1. **数据结构** - 使用新的topic+data+prompt格式
2. **Topic设置** - 使用清晰的中文关键词
3. **Prompt优化** - 提供详细的内容生成指导

### **Python服务**
1. **自动识别** - 无需手动配置，自动支持新格式
2. **LLM配置** - 确保LLM正确配置以启用智能内容生成
3. **监控日志** - 观察事件处理过程和效果

## 🚀 **后续扩展**

### **可能的增强**
- 更多事件类型支持
- 更复杂的topic解析规则
- 多语言支持
- 自定义事件类型配置

---

**📚 这份文档记录了为支持Java后端新数据结构所做的全部修改，确保系统的向前兼容性和功能扩展性！**

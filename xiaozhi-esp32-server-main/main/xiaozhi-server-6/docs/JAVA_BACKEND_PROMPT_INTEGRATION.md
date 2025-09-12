# Java后端Prompt机制集成指南

## 🎯 功能概述

系统现已支持Java后端的智能prompt机制，可以根据Java后端提供的`prompt`和`result`字段，使用LLM动态生成个性化的播报内容。

## 📋 Java后端事件格式规范

### 标准格式

```json
{
  "device_id": "设备ID",
  "event_type": "事件类型",
  "title": "事件标题", 
  "result": "API返回的原始信息",
  "prompt": "LLM处理提示词"
}
```

### 支持的事件类型

1. **天气预警** (`weather_alert`)
2. **24节气** (`solar_term`)  
3. **节假日** (`holiday`)

## 🔧 使用示例

### 天气预警事件

```json
{
  "device_id": "ESP32_001",
  "event_type": "weather_alert",
  "title": "北京市暴雨预警",
  "result": "明天上午8点左右有暴雨，预计降雨量50-80毫米，伴有大风。",
  "prompt": "请根据天气信息，用关怀的语气提醒用户注意安全，包含具体的防护建议。",
  "level": "Orange",
  "sender": "北京市气象局"
}
```

**生成的播报内容示例：**
> "亲爱的用户，明天上午8点左右将有暴雨来袭，预计降雨量50-80毫米，还会伴有大风。请您提前做好防护准备：外出时携带雨具，避免在低洼地区停留，注意交通安全。如非必要，建议减少外出。请注意安全！"

### 24节气事件

```json
{
  "device_id": "ESP32_002", 
  "event_type": "solar_term",
  "title": "立秋",
  "result": "今天是立秋，秋季开始，天气渐凉，是养生的好时节。",
  "prompt": "请用温馨的语气介绍立秋节气，提供一些实用的养生建议。",
  "festival": "立秋"
}
```

**生成的播报内容示例：**
> "今天是立秋，意味着秋天正式开始了。虽然天气渐凉，但这也是养生的好时节呢。建议您多吃些润燥的食物，如梨、蜂蜜，适当增减衣物，保持规律作息。让我们一起迎接这个收获的季节吧！"

### 节假日事件

```json
{
  "device_id": "ESP32_003",
  "event_type": "holiday",
  "title": "春节", 
  "result": "今天是农历新年，春节快乐！",
  "prompt": "请用欢快喜庆的语气送上春节祝福，营造节日氛围。"
}
```

**生成的播报内容示例：**
> "恭喜发财！今天是农历新年，春节快乐！在这个团圆喜庆的日子里，祝您和家人身体健康、万事如意、新年大吉！愿新的一年里，好运连连，幸福满满！"

## 🔄 向后兼容性

系统完全支持传统事件格式，当事件数据中没有`prompt`和`result`字段时，会自动使用原有的硬编码内容生成逻辑。

### 传统格式示例

```json
{
  "device_id": "ESP32_004",
  "id": "alert-001",
  "title": "暴雨蓝色预警",
  "level": "Blue",
  "sender": "西平县气象局", 
  "text": "预计今晚到明天上午有中到大雨，局部暴雨。",
  "type": "1003",
  "typeName": "Rainstorm"
}
```

## 🚀 工作流程

1. **事件接收** - 系统接收Java后端推送的MQTT事件
2. **格式检测** - 自动检测是否包含`prompt`和`result`字段
3. **内容生成** - 
   - **有prompt**: 使用LLM结合prompt和result生成个性化内容
   - **无prompt**: 使用传统硬编码逻辑生成内容
4. **设备推送** - 将生成的内容推送给目标设备

## 📊 日志监控

### 成功日志示例

```
🎯 使用Java后端prompt生成内容
📋 Prompt: 请根据天气信息，用关怀的语气提醒用户注意安全
📄 Result: 明天上午8点左右有暴雨，预计降雨量50-80毫米
✅ Java后端prompt生成内容: 亲爱的用户，明天上午8点左右将有暴雨来袭...
✅ 使用Java后端prompt生成天气预警内容
```

### 兼容性日志示例

```
事件数据不包含prompt或result字段，使用传统处理方式
使用传统硬编码方式生成天气预警内容
```

## 🧪 测试方式

### 1. 运行测试脚本

```bash
python test_java_prompt.py
```

### 2. 实时监控

```bash
# 查看Java后端prompt处理日志
tail -f logs/app_unified.log | grep -E "(🎯|📋|📄|✅|Java后端prompt)"

# 查看所有事件处理日志
tail -f logs/app_unified.log | grep -E "(📨|📄|🔍|✅|事件|统一)"
```

## ⚙️ 配置要求

### LLM配置

确保`config.yaml`中正确配置了LLM：

```yaml
selected_module:
  LLM: ChatGLMLLM

LLM:
  ChatGLMLLM:
    type: ChatGLMLLM
    # 其他LLM配置...
```

### MQTT配置

确保订阅了正确的Java后端事件主题：

```yaml
event_system:
  enabled: true
  topics:
    - "server/dev/report/event"
```

## 🔧 故障排除

### 常见问题

1. **LLM初始化失败**
   - 检查LLM配置是否正确
   - 查看日志中的具体错误信息

2. **prompt内容生成失败**
   - 检查事件数据中是否包含`prompt`和`result`字段
   - 验证LLM服务是否正常

3. **事件类型检测错误**
   - 确保事件数据中包含`event_type`字段
   - 或检查title字段是否包含关键词

### 调试技巧

1. **查看详细日志**
   ```bash
   tail -f logs/app_unified.log | grep -E "(UnifiedEventService|Java后端prompt)"
   ```

2. **测试特定事件**
   - 修改`test_java_prompt.py`中的测试用例
   - 添加自定义的事件数据进行测试

## 📈 性能优化

- LLM调用是异步的，不会阻塞其他事件处理
- 失败时自动回退到传统处理方式
- 支持多设备并发处理

## 🎉 总结

Java后端Prompt机制为事件播报带来了以下优势：

- **智能化** - LLM动态生成个性化内容
- **灵活性** - Java后端可自定义prompt策略  
- **兼容性** - 完全兼容现有传统格式
- **可扩展** - 易于添加新的事件类型和处理逻辑

现在Java后端只需要在事件JSON中添加`prompt`和`result`字段，系统就能自动使用LLM生成更加智能和个性化的播报内容！

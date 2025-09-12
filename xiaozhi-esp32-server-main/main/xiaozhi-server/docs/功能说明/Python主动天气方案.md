# Python主动调用天气播报方案

## 🎯 **方案总览**

作为Python开发人员，您有以下几种方式主动触发天气播报：

---

## 🚀 **方案1：HTTP API调用（推荐）**

### **使用现有的主动问候API**

```bash
# 使用curl命令
curl -X POST http://47.98.51.180:8003/api/proactive-greeting \
  -H "Content-Type: application/json" \
  -d '{
    "device_ids": ["f0:9e:9e:04:8a:44"],
    "category": "weather",
    "content": "北京今天晴天，温度18-25度，微风，适合外出活动",
    "custom_prompt": "请用友好的语调播报天气信息"
  }'
```

### **Python代码示例**

```python
import requests
import json

def trigger_weather():
    url = "http://47.98.51.180:8003/api/proactive-greeting"
    payload = {
        "device_ids": ["f0:9e:9e:04:8a:44"],
        "category": "weather",
        "content": "北京今天晴天，温度18-25度，微风，适合外出活动",
        "custom_prompt": "请用友好的语调播报天气信息"
    }
    
    response = requests.post(url, json=payload)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")

# 调用
trigger_weather()
```

---

## 🔧 **方案2：直接调用Python服务内部API**

### **在Python服务内部调用**

```python
# 在小智服务内部使用
from api.proactive_greeting import ProactiveGreetingService

async def trigger_internal_weather():
    service = ProactiveGreetingService()
    
    result = await service.send_proactive_greeting(
        device_ids=["f0:9e:9e:04:8a:44"],
        category="weather",
        content="北京今天晴天，温度18-25度，微风，适合外出活动",
        custom_prompt="请用友好的语调播报天气信息"
    )
    
    print(f"结果: {result}")
```

---

## 📡 **方案3：MQTT直接发送**

### **模拟Java后端发送MQTT事件**

```python
import json
import asyncio

async def send_weather_via_mqtt():
    # 构建Java兼容的天气数据
    weather_data = {
        "device_id": "f0:9e:9e:04:8a:44",
        "topic": "天气预报",
        "data": [
            {
                "title": "实时天气播报",
                "content": "北京今天晴天，温度18-25度，微风，适合外出活动"
            }
        ],
        "prompt": "请用友好的语调播报天气信息"
    }
    
    # 获取统一事件服务
    from core.services.unified_event_service import get_unified_event_service
    
    event_service = get_unified_event_service()
    if event_service:
        # 模拟MQTT消息
        class MockMessage:
            def __init__(self, topic, payload):
                self.topic = topic
                self.payload = payload.encode('utf-8')
        
        topic = "xiaozhi/java-to-python/event/weather"
        payload = json.dumps(weather_data)
        mock_message = MockMessage(topic, payload)
        
        # 直接调用事件处理
        await event_service._handle_event_message(None, None, mock_message)
        print("✅ 天气事件已发送")
    else:
        print("❌ 事件服务未初始化")

# 调用
asyncio.run(send_weather_via_mqtt())
```

---

## 🎨 **方案4：定制化天气播报**

### **不同场景的天气播报**

```python
# 日常天气
def daily_weather():
    return {
        "content": "北京今天晴天，温度18-25度，微风，空气质量良好，适合外出活动",
        "prompt": "请用轻松友好的语调播报今日天气"
    }

# 天气预警
def weather_warning():
    return {
        "content": "北京发布大风蓝色预警，阵风可达6-7级，请注意防范，避免户外活动",
        "prompt": "这是天气预警信息，请用清晰严肃的语调播报，提醒用户注意安全"
    }

# 恶劣天气
def severe_weather():
    return {
        "content": "北京发布暴雨红色预警，请立即停止户外活动，注意人身安全",
        "prompt": "这是紧急天气预警，请用紧急严肃的语调播报，强调安全重要性"
    }
```

---

## 🧪 **立即测试**

### **方式1：使用curl命令**

```bash
# 复制这个命令到终端运行
curl -X POST http://47.98.51.180:8003/api/proactive-greeting \
  -H "Content-Type: application/json" \
  -d '{
    "device_ids": ["f0:9e:9e:04:8a:44"],
    "category": "weather",
    "content": "测试天气播报：北京今天晴天，温度20度，适合外出",
    "custom_prompt": "请用友好的语调播报天气"
  }'
```

### **方式2：使用Python脚本**

```python
# 保存为 test_weather.py
import subprocess
import json

def test_weather_curl():
    """使用curl测试天气播报"""
    data = {
        "device_ids": ["f0:9e:9e:04:8a:44"],
        "category": "weather",
        "content": "测试天气播报：北京今天晴天，温度20度，适合外出",
        "custom_prompt": "请用友好的语调播报天气"
    }
    
    cmd = [
        "curl", "-X", "POST",
        "http://47.98.51.180:8003/api/proactive-greeting",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(data)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"状态码: {result.returncode}")
    print(f"输出: {result.stdout}")
    print(f"错误: {result.stderr}")

# 运行测试
test_weather_curl()
```

---

## 💡 **使用建议**

### **对于不同需求**

- **简单测试**: 使用curl命令
- **脚本集成**: 使用HTTP API方案
- **服务内部**: 使用内部API方案
- **高级定制**: 使用MQTT方案

### **最佳实践**

1. **内容要具体**: 包含温度、天气状况、建议等
2. **prompt要清晰**: 指定语调和播报风格
3. **测试要充分**: 不同天气场景都要测试
4. **错误要处理**: 加入重试和异常处理

---

## 🎯 **快速上手**

**最简单的方式 - 复制这个curl命令到终端运行：**

```bash
curl -X POST http://47.98.51.180:8003/api/proactive-greeting \
  -H "Content-Type: application/json" \
  -d '{"device_ids":["f0:9e:9e:04:8a:44"],"category":"weather","content":"北京今天晴天，温度20度，适合外出","custom_prompt":"请用友好的语调播报天气"}'
```

**硬件应该立即播放天气语音！** 🌤️🔊

# 主动问候功能 API 参考文档

## 基础信息

**Base URL:** `http://your-server:8003`

**Content-Type:** `application/json`

## API 接口列表

### 1. 发送主动问候

发送智能问候消息到指定ESP32设备。

**请求**
```
POST /xiaozhi/greeting/send
```

**请求头**
```http
Content-Type: application/json
```

**请求体参数**

| 参数名 | 类型 | 必需 | 描述 | 示例 |
|--------|------|------|------|------|
| device_id | string | 是 | ESP32设备唯一标识 | "ESP32_001" |
| initial_content | string | 是 | 初始问候内容 | "今天天气很好" |
| category | string | 是 | 问候类别 | "weather" |
| user_info | object | 否 | 用户基础信息 | 见下表 |
| memory_info | string | 否 | 用户记忆信息 | "喜欢晨练" |

**user_info 对象参数**

| 参数名 | 类型 | 描述 | 示例 |
|--------|------|------|------|
| name | string | 用户姓名 | "李叔" |
| age | number | 用户年龄 | 65 |
| location | string | 用户位置 | "广州" |
| preferences | string | 用户偏好 | "喜欢晨练" |
| health_info | string | 健康信息 | "需要关注血压" |

**问候类别说明**

| 类别 | 描述 | 使用场景 |
|------|------|----------|
| system_reminder | 系统提醒 | 服药提醒、健康提醒等 |
| schedule | 用户日程 | 日程安排、重要事项提醒 |
| weather | 天气信息 | 天气播报、出行建议 |
| entertainment | 娱乐内容 | 音乐、节目推荐等 |
| news | 新闻资讯 | 新闻播报、资讯分享 |

**请求示例**
```json
{
  "device_id": "ESP32_001",
  "initial_content": "今天最高气温38℃，建议减少户外活动",
  "category": "weather",
  "user_info": {
    "name": "李叔",
    "age": 65,
    "location": "广州",
    "preferences": "喜欢晨练",
    "health_info": "高血压患者"
  },
  "memory_info": "平时喜欢早上6点出门晨练，关注健康养生"
}
```

**响应**

**成功响应 (200)**
```json
{
  "success": true,
  "message": "主动问候发送成功",
  "track_id": "WX20241201123456ABC123",
  "device_id": "ESP32_001",
  "timestamp": 1701234567.89
}
```

**错误响应**

| 状态码 | 错误代码 | 描述 |
|--------|----------|------|
| 400 | MISSING_FIELDS | 缺少必需字段 |
| 400 | INVALID_CATEGORY | 无效的问候类别 |
| 400 | INVALID_JSON | JSON格式错误 |
| 500 | SEND_FAILED | 发送失败 |
| 503 | MQTT_NOT_AVAILABLE | MQTT服务不可用 |
| 503 | MQTT_NOT_CONNECTED | MQTT未连接 |

```json
{
  "error": "缺少必需字段: device_id",
  "code": "MISSING_FIELDS"
}
```

---

### 2. 查询设备状态

查询ESP32设备的连接状态和消息处理状态。

**请求**
```
GET /xiaozhi/greeting/status
```

**查询参数**

| 参数名 | 类型 | 必需 | 描述 | 示例 |
|--------|------|------|------|------|
| device_id | string | 是 | 设备ID | ESP32_001 |
| track_id | string | 否 | 跟踪ID，查询特定消息状态 | WX20241201123456ABC123 |

**请求示例**
```
GET /xiaozhi/greeting/status?device_id=ESP32_001&track_id=WX20241201123456ABC123
```

**响应**

**成功响应 (200)**
```json
{
  "device_id": "ESP32_001",
  "connected": true,
  "state": {
    "WX20241201123456ABC123": {
      "status": "speak_done",
      "timestamp": "2024-12-01T12:34:56",
      "completed_timestamp": "2024-12-01T12:35:02",
      "text": "李叔，今天最高气温38℃，建议减少户外活动，记得多喝水保持身体健康。"
    }
  }
}
```

**状态字段说明**

| 状态 | 描述 |
|------|------|
| command_sent | 命令已发送到MQTT |
| ack_received | 设备已确认接收 |
| speak_done | 语音播放完成 |

**错误响应**
```json
{
  "error": "缺少device_id参数",
  "code": "MISSING_DEVICE_ID"
}
```

---

### 3. 更新用户档案

更新指定设备的用户基础信息。

**请求**
```
POST /xiaozhi/user/profile
```

**请求体参数**

| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| device_id | string | 是 | 设备ID |
| user_info | object | 是 | 用户信息 |

**请求示例**
```json
{
  "device_id": "ESP32_001",
  "user_info": {
    "name": "李叔",
    "age": 65,
    "location": "广州市天河区",
    "preferences": "喜欢晨练、听新闻",
    "health_info": "高血压、糖尿病",
    "family": "独居，女儿住在深圳",
    "schedule": "早上6点晨练，晚上8点看新闻"
  }
}
```

**成功响应 (200)**
```json
{
  "success": true,
  "message": "用户档案更新成功",
  "device_id": "ESP32_001"
}
```

---

### 4. 获取用户档案

获取指定设备的用户档案信息。

**请求**
```
GET /xiaozhi/user/profile
```

**查询参数**

| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| device_id | string | 是 | 设备ID |

**请求示例**
```
GET /xiaozhi/user/profile?device_id=ESP32_001
```

**成功响应 (200)**
```json
{
  "device_id": "ESP32_001",
  "user_profile": {
    "name": "李叔",
    "age": 65,
    "location": "广州市天河区",
    "preferences": "喜欢晨练、听新闻",
    "health_info": "高血压、糖尿病",
    "family": "独居，女儿住在深圳",
    "schedule": "早上6点晨练，晚上8点看新闻"
  }
}
```

---

## CORS 支持

所有API接口都支持CORS预检请求：

```
OPTIONS /xiaozhi/greeting/*
OPTIONS /xiaozhi/user/*
```

**响应头**
```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 3600
```

---

## 错误处理

### 通用错误格式

```json
{
  "error": "错误描述信息",
  "code": "ERROR_CODE"
}
```

### 常见错误代码

| 错误代码 | HTTP状态码 | 描述 | 解决方案 |
|----------|------------|------|----------|
| MISSING_FIELDS | 400 | 缺少必需字段 | 检查请求参数完整性 |
| INVALID_JSON | 400 | JSON格式错误 | 检查请求体格式 |
| INVALID_CATEGORY | 400 | 无效的问候类别 | 使用有效的类别值 |
| MISSING_DEVICE_ID | 400 | 缺少设备ID | 提供有效的device_id |
| MQTT_NOT_AVAILABLE | 503 | MQTT服务不可用 | 检查MQTT服务状态 |
| MQTT_NOT_CONNECTED | 503 | MQTT未连接 | 等待MQTT重连或重启服务 |
| SEND_FAILED | 500 | 发送失败 | 检查网络和服务状态 |
| INTERNAL_ERROR | 500 | 服务器内部错误 | 查看服务器日志 |

---

## 限制和约束

### 请求限制
- 最大请求体大小：1MB
- 超时时间：30秒
- 并发连接：100

### 内容限制
- 问候文本最大长度：100字符
- 用户名最大长度：50字符
- track_id格式：WX + 时间戳 + 随机字符

### 频率限制
- 每设备每分钟最多10次问候请求
- 每IP每分钟最多100次API调用

---

## SDK 和示例

### Python SDK示例

```python
import aiohttp
import asyncio

class XiaozhiGreetingClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
    
    async def send_greeting(self, device_id, content, category, user_info=None, memory_info=None):
        data = {
            "device_id": device_id,
            "initial_content": content,
            "category": category
        }
        if user_info:
            data["user_info"] = user_info
        if memory_info:
            data["memory_info"] = memory_info
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.base_url}/xiaozhi/greeting/send',
                json=data
            ) as response:
                return await response.json()
    
    async def get_device_status(self, device_id, track_id=None):
        params = {"device_id": device_id}
        if track_id:
            params["track_id"] = track_id
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{self.base_url}/xiaozhi/greeting/status',
                params=params
            ) as response:
                return await response.json()

# 使用示例
async def main():
    client = XiaozhiGreetingClient("http://localhost:8003")
    
    result = await client.send_greeting(
        device_id="ESP32_001",
        content="今天天气不错",
        category="weather",
        user_info={"name": "李叔", "age": 65}
    )
    print(f"发送结果: {result}")

asyncio.run(main())
```

### JavaScript SDK示例

```javascript
class XiaozhiGreetingClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
    }
    
    async sendGreeting(deviceId, content, category, userInfo = null, memoryInfo = null) {
        const data = {
            device_id: deviceId,
            initial_content: content,
            category: category
        };
        
        if (userInfo) data.user_info = userInfo;
        if (memoryInfo) data.memory_info = memoryInfo;
        
        const response = await fetch(`${this.baseUrl}/xiaozhi/greeting/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        return await response.json();
    }
    
    async getDeviceStatus(deviceId, trackId = null) {
        const params = new URLSearchParams({ device_id: deviceId });
        if (trackId) params.append('track_id', trackId);
        
        const response = await fetch(`${this.baseUrl}/xiaozhi/greeting/status?${params}`);
        return await response.json();
    }
}

// 使用示例
const client = new XiaozhiGreetingClient('http://localhost:8003');

client.sendGreeting(
    'ESP32_001',
    '今天天气不错',
    'weather',
    { name: '李叔', age: 65 }
).then(result => {
    console.log('发送结果:', result);
});
```

---

## 版本信息

**当前版本：** v1.0.0

**更新历史：**
- v1.0.0 (2024-12-01): 初始版本，支持基础主动问候功能

**兼容性：**
- Python 3.8+
- MQTT Protocol 3.1.1/5.0
- HTTP/1.1

# 🔔 小智主动问候功能 - 硬件集成指南

## 📋 概述

本文档为硬件开发人员提供小智主动问候功能的完整测试指南，包括MQTT通信、WebSocket连接和事件上报流程。

---

## 🏗️ 系统架构

```
Java后端 → Python服务 → MQTT → 硬件设备 → WebSocket → Python服务
    ↓           ↓                    ↓              ↓
  事件触发    LLM生成内容        设备唤醒        音频播放
```

### 📡 **通信流程图**
```
1. Python生成主动问候内容
2. Python发布MQTT → device/{device-id}/cmd
3. 设备收到命令 → 模拟唤醒 → 回复MQTT device/{device-id}/ack  
4. Python收到ack → 发送TTS音频 → 设备播放
5. 设备播放完成 → WebSocket上报播放状态
6. 设备通过MQTT上报事件 → device/{device-id}/event
```

---

## 🔧 硬件设备配置要求

### 📍 **网络配置**
- **MQTT服务器**: `47.97.185.142:1883`
- **WebSocket服务器**: `ws://172.20.12.204:8000/xiaozhi/v1/`
- **HTTP服务器**: `http://172.20.12.204:8003`

### 🆔 **设备标识**
- **设备ID格式**: MAC地址 (例如: `00:0c:29:fc:b7:b9`)
- **客户端ID**: 设备ID + 随机后缀 (例如: `esp32-2af5a99d`)

---

## 📡 MQTT通信协议

### 1️⃣ **订阅主题 (设备需要订阅)**

| 主题格式 | 用途 | 示例 |
|----------|------|------|
| `device/{device-id}/cmd` | 接收Python发送的命令 | `device/00:0c:29:fc:b7:b9/cmd` |

### 2️⃣ **发布主题 (设备需要发布)**

| 主题格式 | 用途 | 示例 |
|----------|------|------|
| `device/{device-id}/ack` | 确认收到命令 | `device/00:0c:29:fc:b7:b9/ack` |
| `device/{device-id}/event` | 上报设备事件 | `device/00:0c:29:fc:b7:b9/event` |

### 3️⃣ **消息格式**

#### **接收命令格式 (device/{device-id}/cmd)**
```json
{
  "cmd": "SPEAK",
  "text": "李叔，今天最高38°C，注意防暑降温哦！",
  "track_id": "WX20240809"
}
```

#### **回复确认格式 (device/{device-id}/ack)**
```json
{
  "evt": "CMD_RECEIVED", 
  "track_id": "WX20240809",
  "timestamp": "09:30:02"
}
```

#### **事件上报格式 (device/{device-id}/event)**
```json
{
  "evt": "EVT_SPEAK_DONE",
  "track_id": "WX20240809", 
  "timestamp": "09:30:02"
}
```

---

## 🌐 WebSocket通信协议

### 📍 **连接地址**
```
ws://172.20.12.204:8000/xiaozhi/v1/?device-id={device-id}&client-id={client-id}
```

### 📋 **认证参数**
- `device-id`: 设备MAC地址
- `client-id`: 唯一客户端标识

### 📤 **连接示例**
```
ws://172.20.12.204:8000/xiaozhi/v1/?device-id=00:0c:29:fc:b7:b9&client-id=esp32-test001
```

### 📨 **消息格式**
```json
{
  "type": "audio",
  "data": "播放状态或事件信息",
  "timestamp": "2025-08-21T10:30:00"
}
```

---

## 🧪 测试步骤

### 🔧 **准备工作**

1. **配置设备网络**
   ```
   WiFi连接 → 获取IP地址 → 配置MQTT和WebSocket服务器地址
   ```

2. **设置设备ID**
   ```c
   // ESP32示例代码片段
   String deviceId = WiFi.macAddress();  // 获取MAC地址作为设备ID
   String clientId = "esp32-" + String(random(100000, 999999));
   ```

### 1️⃣ **MQTT连接测试**

```c
// ESP32 Arduino示例代码
#include <WiFi.h>
#include <PubSubClient.h>

const char* mqtt_server = "47.97.185.142";
const int mqtt_port = 1883;
String deviceId = "00:0c:29:fc:b7:b9";  // 替换为实际MAC地址

WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  // WiFi连接代码...
  
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  
  // 连接MQTT
  if (client.connect(deviceId.c_str())) {
    Serial.println("✅ MQTT连接成功");
    
    // 订阅命令主题
    String cmdTopic = "device/" + deviceId + "/cmd";
    client.subscribe(cmdTopic.c_str());
    Serial.println("✅ 订阅成功: " + cmdTopic);
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.println("📥 收到消息: " + message);
  
  // 解析JSON并回复ACK
  // ... JSON解析代码 ...
  
  // 发送ACK确认
  String ackTopic = "device/" + deviceId + "/ack";
  String ackMessage = "{\"evt\":\"CMD_RECEIVED\",\"track_id\":\"" + track_id + "\",\"timestamp\":\"" + getTimestamp() + "\"}";
  
  client.publish(ackTopic.c_str(), ackMessage.c_str());
  Serial.println("✅ 发送ACK: " + ackMessage);
}
```

### 2️⃣ **WebSocket连接测试**

```c
// ESP32 WebSocket示例
#include <WebSocketsClient.h>

WebSocketsClient webSocket;

void setup() {
  // ... WiFi连接代码 ...
  
  // WebSocket连接
  String wsUrl = "/xiaozhi/v1/?device-id=" + deviceId + "&client-id=esp32-test001";
  webSocket.begin("172.20.12.204", 8000, wsUrl);
  webSocket.onEvent(webSocketEvent);
}

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_CONNECTED:
      Serial.println("✅ WebSocket连接成功");
      break;
    case WStype_DISCONNECTED:
      Serial.println("❌ WebSocket断开连接");
      break;
    case WStype_TEXT:
      Serial.printf("📥 收到消息: %s\n", payload);
      break;
  }
}
```

### 3️⃣ **完整测试流程**

#### **步骤1: 触发主动问候**
```bash
# 手动触发测试（在Python服务器上执行）
python -c "
from core.mqtt.proactive_greeting_service import ProactiveGreetingService
# 触发主动问候逻辑
"
```

#### **步骤2: 设备响应流程**
1. **设备收到MQTT命令**
   ```
   📥 topic: device/00:0c:29:fc:b7:b9/cmd
   📄 message: {"cmd":"SPEAK","text":"今天天气很好！","track_id":"WX20240809"}
   ```

2. **设备发送ACK确认**
   ```
   📤 topic: device/00:0c:29:fc:b7:b9/ack  
   📄 message: {"evt":"CMD_RECEIVED","track_id":"WX20240809","timestamp":"09:30:02"}
   ```

3. **设备接收并播放TTS音频**
   ```
   📥 通过WebSocket接收音频数据
   🔊 播放TTS合成的语音
   ```

4. **设备上报播放完成事件**
   ```
   📤 topic: device/00:0c:29:fc:b7:b9/event
   📄 message: {"evt":"EVT_SPEAK_DONE","track_id":"WX20240809","timestamp":"09:30:12"}
   ```

---

## 🛠️ 测试工具

### 1️⃣ **MQTT客户端测试**

```bash
# 订阅设备命令主题（模拟设备接收）
mosquitto_sub -h 47.97.185.142 -p 1883 -t "device/+/cmd"

# 发布ACK确认（模拟设备回复）
mosquitto_pub -h 47.97.185.142 -p 1883 -t "device/00:0c:29:fc:b7:b9/ack" \
  -m '{"evt":"CMD_RECEIVED","track_id":"TEST123","timestamp":"10:30:00"}'

# 发布设备事件（模拟播放完成）
mosquitto_pub -h 47.97.185.142 -p 1883 -t "device/00:0c:29:fc:b7:b9/event" \
  -m '{"evt":"EVT_SPEAK_DONE","track_id":"TEST123","timestamp":"10:30:10"}'
```

### 2️⃣ **WebSocket测试页面**

创建HTML测试页面：
```html
<!DOCTYPE html>
<html>
<head>
    <title>小智WebSocket测试</title>
</head>
<body>
    <h1>小智WebSocket连接测试</h1>
    <div id="status">未连接</div>
    <div id="messages"></div>
    
    <script>
        const deviceId = '00:0c:29:fc:b7:b9';  // 替换为你的设备ID
        const clientId = 'web-test-' + Date.now();
        const wsUrl = `ws://172.20.12.204:8000/xiaozhi/v1/?device-id=${deviceId}&client-id=${clientId}`;
        
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = function() {
            document.getElementById('status').innerHTML = '✅ 已连接';
            console.log('WebSocket连接成功');
        };
        
        ws.onmessage = function(event) {
            const messages = document.getElementById('messages');
            messages.innerHTML += '<div>📥 ' + event.data + '</div>';
            console.log('收到消息:', event.data);
        };
        
        ws.onclose = function() {
            document.getElementById('status').innerHTML = '❌ 连接断开';
        };
        
        ws.onerror = function(error) {
            console.error('WebSocket错误:', error);
        };
    </script>
</body>
</html>
```

---

## 🔍 故障排除

### ❌ **常见问题和解决方案**

#### **1. MQTT连接失败**
```
问题: 无法连接到MQTT服务器
解决: 
- 检查网络连接
- 确认服务器地址: 47.97.185.142:1883
- 检查防火墙设置
- 使用mosquitto_pub/sub工具测试连通性
```

#### **2. WebSocket连接失败**
```
问题: WebSocket握手失败
解决:
- 确认URL格式正确
- 检查device-id和client-id参数
- 确认服务器地址: 172.20.12.204:8000
- 查看浏览器控制台错误信息
```

#### **3. 消息格式错误**
```
问题: 发送的JSON格式不正确
解决:
- 使用JSON在线验证工具检查格式
- 确保所有字符串使用双引号
- 检查时间戳格式
- 验证track_id字段存在
```

#### **4. 设备ID不匹配**
```
问题: 收不到针对性的命令
解决:
- 确认设备ID格式为MAC地址
- 检查主题订阅是否正确
- 确认设备ID在系统中已注册
```

### 🔧 **调试命令**

```bash
# 检查MQTT服务器状态
telnet 47.97.185.142 1883

# 检查WebSocket服务器状态  
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: test" \
  http://172.20.12.204:8000/xiaozhi/v1/

# 监控所有MQTT消息
mosquitto_sub -h 47.97.185.142 -p 1883 -t "#"

# 查看Python服务日志
tail -f logs/app_unified.log | grep -E "(MQTT|WebSocket|问候)"
```

---

## 📝 测试检查清单

### ✅ **必须验证的功能点**

- [ ] **网络连接**
  - [ ] WiFi连接正常
  - [ ] 可以ping通MQTT服务器
  - [ ] 可以访问WebSocket服务器

- [ ] **MQTT通信**
  - [ ] 成功连接MQTT服务器
  - [ ] 正确订阅 `device/{device-id}/cmd` 主题
  - [ ] 能够接收Python发送的命令消息
  - [ ] 能够发布ACK确认到 `device/{device-id}/ack`
  - [ ] 能够上报事件到 `device/{device-id}/event`

- [ ] **WebSocket通信**
  - [ ] 成功建立WebSocket连接
  - [ ] 认证参数正确传递
  - [ ] 能够接收服务器消息
  - [ ] 连接保持稳定

- [ ] **消息处理**
  - [ ] 正确解析JSON格式命令
  - [ ] 提取track_id并在回复中使用
  - [ ] 生成正确的时间戳格式
  - [ ] 处理播放完成事件上报

- [ ] **异常处理**
  - [ ] 网络断开自动重连
  - [ ] 消息格式错误处理
  - [ ] 超时重试机制

---

## 📞 技术支持

### 🆘 **遇到问题时**

1. **查看日志**
   - 设备端串口输出
   - Python服务端日志: `logs/app_unified.log`

2. **使用测试工具**
   - MQTT客户端测试连通性
   - WebSocket在线测试工具

3. **联系开发团队**
   - 提供详细的错误日志
   - 说明测试步骤和现象
   - 提供设备ID和网络环境信息

---

## 🎯 成功标准

**测试成功的标志：**
- ✅ 设备能稳定接收MQTT命令
- ✅ 正确回复ACK确认消息
- ✅ WebSocket连接保持稳定
- ✅ 能够上报播放完成事件
- ✅ 整个交互流程无异常

**测试完成后，设备应该能够：**
1. 自动接收Python服务的主动问候
2. 播放TTS合成的语音内容
3. 向服务器确认播放状态
4. 维持长期稳定的通信连接

---

*📅 文档更新时间: 2025-08-21*
*🔧 适用版本: 小智ESP32服务器 v0.7.3*

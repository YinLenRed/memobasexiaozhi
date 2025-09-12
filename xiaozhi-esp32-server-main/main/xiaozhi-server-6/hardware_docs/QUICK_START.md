# 🚀 硬件集成快速开始指南

> **5分钟了解小智主动问候功能实现要求**

## 🎯 你需要实现什么？

硬件设备需要实现一个**双向通信流程**：

```
Python服务 → MQTT命令 → 硬件设备 → 播放音频 → 上报完成
```

## 📡 核心配置

```c
// 必须配置的服务器地址
#define MQTT_SERVER "47.97.185.142"
#define MQTT_PORT 1883
#define WS_SERVER "172.20.12.204"
#define WS_PORT 8000

// 设备标识
String deviceId = WiFi.macAddress();  // 例如: "00:0c:29:fc:b7:b9"
String clientId = "esp32-" + String(random(100000));
```

## 🔄 实现流程

### 1️⃣ **连接服务**
```c
// 连接MQTT
client.connect(deviceId.c_str());

// 订阅命令主题
String cmdTopic = "device/" + deviceId + "/cmd";
client.subscribe(cmdTopic.c_str());

// 连接WebSocket
String wsUrl = "/xiaozhi/v1/?device-id=" + deviceId + "&client-id=" + clientId;
webSocket.begin(WS_SERVER, WS_PORT, wsUrl);
```

### 2️⃣ **处理MQTT命令**
```c
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  // 解析JSON: {"cmd":"SPEAK","text":"问候内容","track_id":"WX123"}
  
  // 立即发送ACK确认
  String ackTopic = "device/" + deviceId + "/ack";
  String ackMsg = "{\"evt\":\"CMD_RECEIVED\",\"track_id\":\"" + track_id + "\",\"timestamp\":\"" + getTime() + "\"}";
  client.publish(ackTopic.c_str(), ackMsg.c_str());
}
```

### 3️⃣ **接收并播放音频**
```c
void onWebSocketMessage(uint8_t * payload, size_t length) {
  // 接收TTS音频数据
  // 播放音频
  
  // 播放完成后上报事件
  String eventTopic = "device/" + deviceId + "/event";
  String eventMsg = "{\"evt\":\"EVT_SPEAK_DONE\",\"track_id\":\"" + track_id + "\",\"timestamp\":\"" + getTime() + "\"}";
  client.publish(eventTopic.c_str(), eventMsg.c_str());
}
```

## 📋 关键消息格式

### 📥 接收命令 (MQTT)
```json
{
  "cmd": "SPEAK",
  "text": "李叔，今天最高38°C，注意防暑降温哦！",
  "track_id": "WX20240809"
}
```

### 📤 回复确认 (MQTT)
```json
{
  "evt": "CMD_RECEIVED",
  "track_id": "WX20240809", 
  "timestamp": "09:30:02"
}
```

### 📤 播放完成 (MQTT)
```json
{
  "evt": "EVT_SPEAK_DONE",
  "track_id": "WX20240809",
  "timestamp": "09:30:12"
}
```

## 🧪 快速测试

### 1️⃣ **测试MQTT连接**
```bash
# 订阅你的设备命令主题
mosquitto_sub -h 47.97.185.142 -p 1883 -t "device/你的MAC地址/cmd"

# 手动发送测试命令
mosquitto_pub -h 47.97.185.142 -p 1883 -t "device/你的MAC地址/cmd" \
  -m '{"cmd":"SPEAK","text":"测试消息","track_id":"TEST123"}'
```

### 2️⃣ **测试WebSocket连接**
```javascript
// 浏览器控制台测试
const ws = new WebSocket('ws://172.20.12.204:8000/xiaozhi/v1/?device-id=你的MAC&client-id=test');
ws.onopen = () => console.log('✅ 连接成功');
```

### 3️⃣ **自动化验证**
```bash
# 运行完整测试
python test_integration.py 你的MAC地址
```

## ⚠️ 常见问题

### ❌ **MQTT连接失败**
- 检查网络连接
- 确认服务器地址：47.97.185.142:1883
- 查看串口输出错误信息

### ❌ **WebSocket连接失败** 
- 确认URL格式正确
- 检查device-id和client-id参数
- 确认服务器地址：172.20.12.204:8000

### ❌ **收不到命令**
- 确认订阅了正确的主题：`device/{你的MAC}/cmd`
- 检查设备MAC地址格式
- 确认JSON解析正确

## 🎯 成功标准

看到这些输出就说明成功了：

```
✅ MQTT连接成功
✅ 订阅主题: device/00:0c:29:fc:b7:b9/cmd
✅ 收到SPEAK命令
✅ 发送ACK确认
✅ WebSocket连接成功
✅ 音频播放完成
✅ 事件上报成功
```

## 📚 下一步

- 📖 **详细实现**: 查看 [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)
- ⚡ **配置速查**: 查看 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
- 🧪 **完整测试**: 运行 `python test_integration.py`

---

**🚀 开始编码吧！5分钟就能实现基本功能！**

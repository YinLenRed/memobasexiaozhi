# 🎵 硬件WebSocket音频接收实现指南

## 📋 问题现状

当前测试显示：
- ✅ MQTT通信正常（SPEAK命令、ACK确认）
- ✅ 健康检查正常（/check/hello）
- ❌ **缺少WebSocket音频传输实现**

## 🎯 需要实现的功能

硬件端收到SPEAK命令后，需要：

1. **解析audio_url**：从SPEAK命令中提取WebSocket地址
2. **连接WebSocket**：建立音频传输连接
3. **接收音频数据**：处理TTS音频流
4. **播放音频**：本地播放并发送完成事件

---

## 📡 SPEAK命令格式回顾

```json
{
  "cmd": "SPEAK",
  "track_id": "TEST2025082510261887d3f2",
  "content": "这是要播放的文本",
  "audio_url": "ws://47.98.51.180:8000/xiaozhi/v1/"
}
```

**关键字段**：
- `audio_url`：WebSocket音频服务器地址
- `track_id`：用于关联播放完成事件

---

## 💻 ESP32 WebSocket音频实现

### 1. 依赖库添加

```cpp
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
```

### 2. 核心实现代码

```cpp
// WebSocket客户端
WebSocketsClient webSocket;
String currentTrackId = "";
bool audioReceiving = false;

// WebSocket事件处理
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.println("🔌 WebSocket断开连接");
            break;
            
        case WStype_CONNECTED:
            Serial.println("✅ WebSocket连接成功");
            // 发送hello消息
            webSocket.sendTXT("{\"type\":\"hello\"}");
            break;
            
        case WStype_TEXT:
            handleWebSocketMessage((char*)payload);
            break;
            
        case WStype_BIN:
            // 接收音频数据
            handleAudioData(payload, length);
            break;
    }
}

// 处理WebSocket文本消息
void handleWebSocketMessage(String message) {
    DynamicJsonDocument doc(1024);
    deserializeJson(doc, message);
    
    String type = doc["type"];
    if (type == "audio_start") {
        Serial.println("🎵 开始接收音频");
        audioReceiving = true;
    }
    else if (type == "audio_end") {
        Serial.println("🎵 音频接收完成");
        audioReceiving = false;
        // 发送播放完成事件
        sendPlaybackCompleteEvent();
    }
}

// 处理音频数据
void handleAudioData(uint8_t* data, size_t length) {
    if (audioReceiving) {
        // 播放音频数据
        playAudioChunk(data, length);
    }
}

// 连接WebSocket音频服务器
void connectAudioWebSocket(String audioUrl, String trackId) {
    currentTrackId = trackId;
    
    // 解析URL
    // 例如: ws://47.98.51.180:8000/xiaozhi/v1/
    String host = extractHostFromUrl(audioUrl);
    int port = extractPortFromUrl(audioUrl);
    String path = extractPathFromUrl(audioUrl);
    
    Serial.println("🔗 连接WebSocket: " + audioUrl);
    
    webSocket.begin(host, port, path);
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(5000);
}

// 发送播放完成事件
void sendPlaybackCompleteEvent() {
    String topic = "device/" + deviceId + "/event";
    
    DynamicJsonDocument doc(256);
    doc["evt"] = "PLAYBACK_COMPLETE";
    doc["track_id"] = currentTrackId;
    doc["timestamp"] = getTimestamp();
    doc["status"] = "success";
    
    String message;
    serializeJson(doc, message);
    
    mqttClient.publish(topic.c_str(), message.c_str());
    Serial.println("📤 发送播放完成事件: " + message);
    
    // 断开WebSocket连接
    webSocket.disconnect();
}
```

### 3. SPEAK命令处理修改

```cpp
void handleSpeakCommand(JsonObject cmd) {
    String trackId = cmd["track_id"];
    String content = cmd["content"];
    String audioUrl = cmd["audio_url"];
    
    Serial.println("🔊 收到SPEAK命令:");
    Serial.println("📱 Track ID: " + trackId);
    Serial.println("📄 内容: " + content);
    Serial.println("🌐 音频URL: " + audioUrl);
    
    // 1. 发送ACK确认
    sendAckMessage(trackId);
    
    // 2. 连接WebSocket获取音频
    connectAudioWebSocket(audioUrl, trackId);
}
```

### 4. 主循环中添加

```cpp
void loop() {
    mqttClient.loop();
    webSocket.loop();  // 添加WebSocket循环
    
    // 其他逻辑...
}
```

---

## 🧪 测试步骤

1. **烧录更新后的固件**
2. **运行Python测试**：
   ```bash
   python test_python_hardware_flow.py 7c:2c:67:8d:89:78
   ```
3. **观察日志**：
   - 确认WebSocket连接成功
   - 确认音频数据接收
   - 确认播放完成事件发送

---

## 🔧 URL解析辅助函数

```cpp
String extractHostFromUrl(String url) {
    // ws://47.98.51.180:8000/xiaozhi/v1/
    int start = url.indexOf("://") + 3;
    int end = url.indexOf(":", start);
    return url.substring(start, end);
}

int extractPortFromUrl(String url) {
    int start = url.lastIndexOf(":") + 1;
    int end = url.indexOf("/", start);
    return url.substring(start, end).toInt();
}

String extractPathFromUrl(String url) {
    int start = url.indexOf("/", 8); // 跳过协议部分
    return url.substring(start);
}
```

---

## 📋 完整流程总结

```
1. 收到SPEAK命令 ✅
2. 发送ACK确认 ✅
3. 解析audio_url 🔄 (需实现)
4. 连接WebSocket 🔄 (需实现)
5. 接收音频数据 🔄 (需实现)
6. 播放音频 🔄 (需实现)
7. 发送完成事件 🔄 (需实现)
```

**硬件团队实现了上述WebSocket音频接收功能后，全流程测试就能通过了！**

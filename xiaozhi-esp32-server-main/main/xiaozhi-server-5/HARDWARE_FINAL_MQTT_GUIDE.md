# 🛠️ 硬件团队最终实现指南

## 🎯 **问题总结**
经过完整测试，**Python服务端功能完全正常**，硬件端需要补充以下功能：

### **✅ 硬件当前能做到的：**
- 连接MQTT并接收命令 ✅
- 连接WebSocket获取配置 ✅

### **❌ 硬件缺少的关键功能：**
- MQTT ACK确认回复 ❌
- 播放完成事件上报 ❌
- WebSocket音频数据播放 ❌

---

## 🔧 **必须实现的3个核心功能**

### **1. MQTT ACK确认 (最高优先级)**
```cpp
// 收到SPEAK命令后立即发送ACK
void sendAck(String trackId) {
    String ackMsg = "{\"evt\":\"CMD_RECEIVED\",\"track_id\":\"" + trackId + "\",\"timestamp\":\"" + getCurrentTime() + "\"}";
    mqtt.publish("device/7c:2c:67:8d:89:78/ack", ackMsg);
}
```

### **2. WebSocket音频播放**
```cpp
// 连接WebSocket并播放音频
void connectAndPlayAudio(String trackId) {
    webSocket.begin("47.98.51.180", 8000, "/xiaozhi/v1/");
    // 接收音频数据并播放
    // 当接收完成后，调用下面的函数
}
```

### **3. 播放完成事件 (最高优先级)**
```cpp
// 音频播放完成后发送事件
void sendPlayComplete(String trackId) {
    String eventMsg = "{\"evt\":\"EVT_SPEAK_DONE\",\"track_id\":\"" + trackId + "\",\"timestamp\":\"" + getCurrentTime() + "\"}";
    mqtt.publish("device/7c:2c:67:8d:89:78/event", eventMsg);
}
```

---

## 📡 **MQTT配置信息**

### **服务器信息：**
- **MQTT服务器**: `47.97.185.142:1883`
- **用户名**: `admin`
- **密码**: `Jyxd@2025`

### **主题配置：**
```cpp
// 订阅命令主题
mqtt.subscribe("device/7c:2c:67:8d:89:78/command");

// 发送ACK到
mqtt.publish("device/7c:2c:67:8d:89:78/ack", ackMessage);

// 发送事件到  
mqtt.publish("device/7c:2c:67:8d:89:78/event", eventMessage);
```

---

## 🌐 **WebSocket配置**

### **连接信息：**
- **地址**: `ws://47.98.51.180:8000/xiaozhi/v1/`
- **Headers**: `Device-ID: 7c:2c:67:8d:89:78`

---

## 🧪 **验证测试**

实现上述功能后，运行Python测试工具：

```bash
# 完整功能测试
python complete_hardware_simulation.py 7c:2c:67:8d:89:78

# 快速验证测试
python one_click_test.py 7c:2c:67:8d:89:78
```

**期望结果：**
```
✅ API调用成功
✅ 硬件ACK确认成功  
✅ 音频播放完成
🎉 完整的硬件音频播放测试成功！
```

---

## 📋 **完整流程示例**

```cpp
// 1. 收到SPEAK命令
void onMqttMessage(String topic, String payload) {
    if (topic.endsWith("/command")) {
        // 解析JSON获取track_id
        String trackId = parseTrackId(payload);
        
        // 立即发送ACK
        sendAck(trackId);
        
        // 开始音频播放
        connectAndPlayAudio(trackId);
    }
}

// 2. WebSocket音频播放完成后
void onAudioPlayComplete(String trackId) {
    // 发送播放完成事件
    sendPlayComplete(trackId);
}
```

---

## ⚡ **关键要点**

1. **ACK必须立即发送** - 收到命令后马上回复
2. **播放完成必须上报** - 音频播放结束后发送EVT_SPEAK_DONE
3. **JSON格式正确** - 确保消息格式与示例一致
4. **时间戳格式** - 使用HH:MM:SS格式，如"17:30:45"

---

## 🎯 **测试用例**

硬件实现后，应该能处理这个完整流程：

1. **接收**: `{"cmd": "SPEAK", "text": "现在该吃药了", "track_id": "WX123", "audio_url": "ws://47.98.51.180:8000/xiaozhi/v1/"}`

2. **回复ACK**: `{"evt": "CMD_RECEIVED", "track_id": "WX123", "timestamp": "17:30:45"}`

3. **连接WebSocket**: `ws://47.98.51.180:8000/xiaozhi/v1/`

4. **播放音频**: 接收并播放音频数据

5. **完成事件**: `{"evt": "EVT_SPEAK_DONE", "track_id": "WX123", "timestamp": "17:32:15"}`

---

🎯 **实现这3个功能后，硬件将能完美配合Python服务实现主动问候音频播放！**
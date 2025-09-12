# 🎯 硬件端TTS播放完成确认方案

## 📋 **问题描述**
硬件在TTS音频播放过程中过早进入聆听模式，影响用户体验。

## 🔧 **硬件端需要实现的功能**

### **1. 播放完成事件上报**
```cpp
// 音频播放完成后发送事件
void sendPlayCompleteEvent(String trackId) {
    StaticJsonDocument<200> eventMsg;
    eventMsg["evt"] = "EVT_SPEAK_DONE";           // 播放完成事件
    eventMsg["track_id"] = trackId;               // 追踪ID
    eventMsg["status"] = "completed";             // 状态：completed/failed
    eventMsg["timestamp"] = getCurrentTime();     // 时间戳
    
    String eventJson;
    serializeJson(eventMsg, eventJson);
    
    // 发送到 device/{device_id}/event 主题
    String topic = "device/" + deviceId + "/event";
    mqtt.publish(topic.c_str(), eventJson.c_str());
    
    Serial.println("📢 TTS播放完成事件已上报: " + trackId);
}
```

### **2. 音频播放状态管理**
```cpp
class AudioPlayer {
private:
    bool isPlaying = false;
    String currentTrackId = "";
    
public:
    void startPlay(String trackId, uint8_t* audioData, size_t length) {
        isPlaying = true;
        currentTrackId = trackId;
        
        // 播放音频数据
        playAudioBuffer(audioData, length);
        
        Serial.println("🔊 开始播放音频: " + trackId);
    }
    
    void onPlayComplete() {
        if (isPlaying && currentTrackId.length() > 0) {
            // 发送播放完成事件
            sendPlayCompleteEvent(currentTrackId);
            
            // 重置状态
            isPlaying = false;
            currentTrackId = "";
        }
    }
};
```

### **3. WebSocket音频接收处理**
```cpp
void handleTTSAudio() {
    webSocket.onBinaryEvent([](uint8_t* payload, size_t length) {
        // 解析音频消息头部获取track_id
        String trackId = extractTrackIdFromHeader(payload);
        
        // 播放音频并监听完成事件
        audioPlayer.startPlay(trackId, payload, length);
    });
    
    // 监听音频播放完成
    audioPlayer.setCompletionCallback([]() {
        audioPlayer.onPlayComplete();
    });
}
```

## 📡 **MQTT消息格式**

### **播放完成事件**
```json
{
  "evt": "EVT_SPEAK_DONE",
  "track_id": "WX20250829111820abc123",
  "status": "completed",
  "timestamp": "2025-08-29 11:18:25",
  "duration": 3.2
}
```

### **播放失败事件**
```json
{
  "evt": "EVT_SPEAK_DONE", 
  "track_id": "WX20250829111820abc123",
  "status": "failed",
  "error": "audio_decode_error",
  "timestamp": "2025-08-29 11:18:25"
}
```

## 🔄 **完整交互流程**

```
1. 服务端 → 硬件: TTS音频数据 (WebSocket)
2. 硬件 → 开始播放音频
3. 硬件 → 播放完成
4. 硬件 → 服务端: EVT_SPEAK_DONE事件 (MQTT)  
5. 服务端 → 确认播放完成
6. 服务端 → 启动VAD聆听模式 ✅
```

## 🛠️ **硬件实现要点**

### **关键点1：准确检测播放完成**
```cpp
// 使用音频缓冲区状态或播放回调确保准确性
bool isAudioPlaybackComplete() {
    return (audioBuffer.isEmpty() && !audioProcessor.isActive());
}
```

### **关键点2：网络异常处理**
```cpp
void sendEventWithRetry(String eventJson, int maxRetries = 3) {
    for (int i = 0; i < maxRetries; i++) {
        if (mqtt.publish(topic.c_str(), eventJson.c_str())) {
            Serial.println("✅ 事件发送成功");
            return;
        }
        delay(1000 * (i + 1)); // 递增延迟重试
    }
    Serial.println("❌ 事件发送失败，已达最大重试次数");
}
```

### **关键点3：时序同步**
```cpp
// 确保事件发送不阻塞音频播放
void sendEventAsync(String eventJson) {
    // 使用任务队列或独立线程发送
    xTaskCreate(sendEventTask, "SendEvent", 2048, 
                (void*)eventJson.c_str(), 1, NULL);
}
```

## ✅ **验证方法**

### **测试步骤**：
1. 发送TTS请求到硬件
2. 观察硬件播放音频
3. 确认收到`EVT_SPEAK_DONE`事件
4. 验证服务端在收到事件后才启动聆听

### **日志验证**：
```
硬件端：📢 TTS播放完成事件已上报: WX20250829111820abc123
服务端：🎯 确认播放完成: f0:9e:9e:04:8a:44, track_id: WX20250829111820abc123
服务端：🎤 启动VAD聆听模式
```

## 🎯 **预期效果**

实现后用户体验：
- **音频播放完整** → 不会被中断
- **聆听时机准确** → 音频结束后再启动VAD
- **交互更自然** → 避免"说话说一半就进入聆听"的问题

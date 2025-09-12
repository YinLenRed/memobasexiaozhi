# ⚠️ **服务器地址配置统一方案**

> **紧急解决：硬件人员WebSocket地址不一致问题**

---

## 🔍 **地址配置说明**

已明确服务器地址配置：

| 服务 | 公网地址（对外） | 内网地址（实际部署） | 用途 |
|------|----------------|-------------------|------|
| MQTT | `47.97.185.142:1883` | `47.97.185.142:1883` | 设备命令通信 |
| WebSocket | `ws://47.98.51.180:8000/xiaozhi/v1/` | `ws://172.20.12.204:8000/xiaozhi/v1/` | 音频流传输 |
| HTTP API | `http://47.98.51.180:8003` | `http://172.20.12.204:8003` | Java后端调用 |

**📋 硬件开发使用公网地址：`ws://47.98.51.180:8000/xiaozhi/v1/`**

---

## 🎯 **硬件开发配置指南**

### **硬件端配置**

硬件设备应使用以下公网地址：

```cpp
// ESP32配置
#define MQTT_SERVER "47.97.185.142"
#define MQTT_PORT 1883
#define WEBSOCKET_URL "ws://47.98.51.180:8000/xiaozhi/v1/"

// 设备ID使用MAC地址格式
String deviceId = WiFi.macAddress();
```

### **主动问候完整流程**
1. **Java后端** → `POST http://47.98.51.180:8003/xiaozhi/greeting/send`
2. **MQTT命令** → `device/{device_id}/cmd` (via 47.97.185.142)
3. **硬件ACK** → `device/{device_id}/ack`
4. **WebSocket音频** → `ws://47.98.51.180:8000/xiaozhi/v1/`
5. **播放完成** → `device/{device_id}/event`

---

## 🧪 **测试验证**

### **硬件端测试步骤**

#### **1. MQTT连接测试**
```cpp
// ESP32测试代码
void testMQTTConnection() {
  if (mqtt.connect("ESP32_Test", "admin", "your_password")) {
    Serial.println("✅ MQTT连接成功");
    // 订阅测试主题
    mqtt.subscribe("device/000c29fcb7b9/cmd");
  } else {
    Serial.println("❌ MQTT连接失败");
  }
}
```

#### **2. WebSocket连接测试**
```cpp
void testWebSocketConnection() {
  webSocket.begin("47.98.51.180", 8000, "/xiaozhi/v1/");
  webSocket.onEvent([](WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
      case WStype_CONNECTED:
        Serial.println("✅ WebSocket连接成功");
        break;
      case WStype_DISCONNECTED:
        Serial.println("❌ WebSocket连接断开");
        break;
      case WStype_TEXT:
        Serial.println("📨 收到消息: " + String((char*)payload));
        break;
    }
  });
}
```

### **3. 完整流程测试**

---

## 🧪 **验证测试**

### **测试WebSocket连接**
```javascript
// 浏览器Console测试
const ws = new WebSocket('ws://47.97.185.142:8000/xiaozhi/v1/');
ws.onopen = () => console.log('✅ WebSocket连接成功');
ws.onerror = (e) => console.log('❌ 连接失败:', e);
```

### **测试完整主动问候流程**
```bash
# 1. 发送问候请求
curl -X POST http://172.20.12.204:8003/xiaozhi/greeting/send \
  -H "Content-Type: application/json" \
  -d '{"device_id":"ESP32_001","initial_content":"测试","category":"weather"}'

# 2. 检查设备状态
curl -X GET "http://172.20.12.204:8003/xiaozhi/greeting/status?device_id=ESP32_001"
```

---

## 📋 **实施检查清单**

### **服务器端**
- [ ] 确认47.97.185.142服务器8000端口开放
- [ ] Python WebSocket服务正确启动
- [ ] MQTT和WebSocket服务都正常运行
- [ ] 防火墙配置允许8000和8003端口

### **硬件端**
- [ ] ESP32连接到正确的WebSocket地址
- [ ] MQTT连接正常
- [ ] 能够接收SPEAK命令
- [ ] 能够发送ACK确认
- [ ] WebSocket音频接收正常

### **测试验证**
- [ ] MQTT消息收发正常
- [ ] WebSocket连接稳定
- [ ] 音频数据传输无误
- [ ] 完整问候流程测试通过

---

## 🚨 **紧急处理步骤**

### **立即执行（5分钟）**
1. **确认当前服务器部署状态**
   ```bash
   # 检查47.97.185.142上是否有WebSocket服务
   telnet 47.97.185.142 8000
   
   # 检查172.20.12.204上的服务状态
   curl -I http://172.20.12.204:8003/xiaozhi/greeting/status?device_id=test
   ```

2. **临时解决方案：Nginx代理**
   ```bash
   # 在47.97.185.142上快速配置代理
   sudo nginx -s reload
   ```

### **永久解决（30分钟）**
1. **统一服务部署**
2. **更新文档配置**
3. **完整流程测试**

---

## 📞 **联系方式**

**遇到问题请立即联系：**
- **硬件问题**：检查ESP32代码中的WebSocket地址配置
- **服务器问题**：确认Python服务是否在正确地址启动
- **网络问题**：检查防火墙和端口开放状态

---

## 💡 **建议**

**为了避免类似问题，建议：**
1. **统一配置管理**：使用配置中心管理所有服务地址
2. **环境标识**：明确区分开发/测试/生产环境
3. **文档同步**：确保硬件和后端文档配置一致
4. **自动化测试**：定期检查服务连通性

---

**🔥 这个地址不一致问题是导致主动问候功能异常的根本原因，需要立即解决！**

**🎯 推荐采用方案A：将所有服务统一到47.97.185.142，这样最简单可靠！**

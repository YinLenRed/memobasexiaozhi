# 🔄 Java向Python发送设备状态 - MQTT消息设计

## 📡 **消息流向架构**

```
Java后端 → MQTT Broker → Python服务
```

### **架构说明**
- **Java端**：设备管理中心，掌握设备真实在线状态
- **Python端**：接收设备状态，提供统一查询接口
- **MQTT**：作为消息传输通道

---

## 📨 **MQTT消息格式设计**

### **主题(Topic)格式**
```
xiaozhi/java-to-python/device-status/{device_id}
```

### **消息体格式**
```json
{
  "device_id": "ESP32_001",
  "status": "online",
  "timestamp": "2024-08-22T15:30:45.123Z",
  "source": "java-backend",
  "additional_info": {
    "last_seen": "2024-08-22T15:30:40.000Z",
    "connection_type": "wifi",
    "signal_strength": -45,
    "firmware_version": "1.2.3",
    "location": "客厅"
  }
}
```

### **状态值说明**
```json
{
  "online": "设备在线",
  "offline": "设备离线", 
  "reconnecting": "重连中",
  "maintenance": "维护模式",
  "error": "设备异常"
}
```

---

## ☕ **Java端发送示例**

### **Spring Boot代码**
```java
@Service
public class DeviceStatusPublisher {
    
    @Autowired
    private MqttTemplate mqttTemplate;
    
    private final String TOPIC_PREFIX = "xiaozhi/java-to-python/device-status/";
    
    /**
     * 发送设备状态到Python服务
     */
    public void publishDeviceStatus(String deviceId, DeviceStatus status) {
        try {
            DeviceStatusMessage message = DeviceStatusMessage.builder()
                .deviceId(deviceId)
                .status(status.getValue())
                .timestamp(Instant.now().toString())
                .source("java-backend")
                .additionalInfo(buildAdditionalInfo(status))
                .build();
            
            String topic = TOPIC_PREFIX + deviceId;
            String jsonMessage = objectMapper.writeValueAsString(message);
            
            mqttTemplate.convertAndSend(topic, jsonMessage);
            
            log.info("📡 设备状态已发送: {} -> {}", deviceId, status.getValue());
            
        } catch (Exception e) {
            log.error("❌ 发送设备状态失败: deviceId={}, error={}", deviceId, e.getMessage());
        }
    }
    
    /**
     * 批量发送设备状态
     */
    public void publishBatchDeviceStatus(Map<String, DeviceStatus> deviceStatuses) {
        deviceStatuses.forEach((deviceId, status) -> {
            CompletableFuture.runAsync(() -> publishDeviceStatus(deviceId, status));
        });
    }
    
    private Map<String, Object> buildAdditionalInfo(DeviceStatus status) {
        return Map.of(
            "last_seen", status.getLastSeen().toString(),
            "connection_type", status.getConnectionType(),
            "signal_strength", status.getSignalStrength(),
            "firmware_version", status.getFirmwareVersion(),
            "location", status.getLocation()
        );
    }
}
```

### **设备状态枚举**
```java
public enum DeviceStatus {
    ONLINE("online", "设备在线"),
    OFFLINE("offline", "设备离线"),
    RECONNECTING("reconnecting", "重连中"),
    MAINTENANCE("maintenance", "维护模式"),
    ERROR("error", "设备异常");
    
    private final String value;
    private final String description;
    
    DeviceStatus(String value, String description) {
        this.value = value;
        this.description = description;
    }
    
    // getters...
}
```

### **设备监控服务**
```java
@Service
@Slf4j
public class DeviceMonitoringService {
    
    @Autowired
    private DeviceStatusPublisher statusPublisher;
    
    @Autowired
    private DeviceRepository deviceRepository;
    
    /**
     * 监控设备状态变化并发布
     */
    @Scheduled(fixedRate = 30000) // 30秒检查一次
    public void monitorDeviceStatus() {
        List<Device> devices = deviceRepository.findAll();
        
        for (Device device : devices) {
            DeviceStatus currentStatus = checkDeviceStatus(device);
            DeviceStatus lastStatus = device.getLastStatus();
            
            // 状态发生变化或定期同步
            if (!currentStatus.equals(lastStatus) || shouldSyncStatus(device)) {
                statusPublisher.publishDeviceStatus(device.getDeviceId(), currentStatus);
                device.setLastStatus(currentStatus);
                deviceRepository.save(device);
            }
        }
    }
    
    private DeviceStatus checkDeviceStatus(Device device) {
        // 实现设备状态检查逻辑
        // 例如：ping设备、检查最后心跳时间等
        
        if (isDeviceReachable(device)) {
            return DeviceStatus.ONLINE;
        } else {
            return DeviceStatus.OFFLINE;
        }
    }
    
    private boolean shouldSyncStatus(Device device) {
        // 每5分钟强制同步一次状态
        return System.currentTimeMillis() - device.getLastSyncTime() > 300000;
    }
}
```

---

## 🐍 **Python端接收处理**

### **MQTT消息处理器**
```python
# 在 mqtt_client.py 中添加
def _handle_java_device_status(self, device_id: str, message_data: Dict):
    """处理Java发送的设备状态更新"""
    try:
        status = message_data.get("status")
        timestamp = message_data.get("timestamp")
        additional_info = message_data.get("additional_info", {})
        
        with self.lock:
            if device_id not in self.device_states:
                self.device_states[device_id] = {}
            
            # 更新设备状态
            self.device_states[device_id]["java_status"] = {
                "status": status,
                "timestamp": timestamp,
                "last_updated": datetime.now().isoformat(),
                "source": "java-backend",
                "additional_info": additional_info
            }
        
        self.logger.bind(tag=TAG).info(f"📥 收到Java设备状态: {device_id} -> {status}")
        
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"处理Java设备状态失败: {e}")
```

### **订阅Java状态主题**
```python
# 在 mqtt_client.py 的 start() 方法中添加
async def start(self):
    # ... 现有代码 ...
    
    # 订阅Java设备状态主题
    java_status_topic = "xiaozhi/java-to-python/device-status/+"
    self.client.subscribe(java_status_topic, qos=1)
    self.logger.bind(tag=TAG).info(f"订阅Java设备状态主题: {java_status_topic}")
```

### **消息路由处理**
```python
def _on_message(self, client, userdata, msg):
    """MQTT消息回调"""
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        # 处理Java设备状态消息
        if topic.startswith("xiaozhi/java-to-python/device-status/"):
            device_id = topic.split("/")[-1]
            message_data = json.loads(payload)
            self._handle_java_device_status(device_id, message_data)
            return
        
        # ... 处理其他消息类型 ...
        
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"处理MQTT消息失败: {e}")
```

---

## 🌐 **Python端查询接口**

### **更新的状态查询响应**
```json
{
  "device_id": "ESP32_001",
  "connected": true,
  "java_reported_status": "online",
  "mqtt_server_connected": true,
  "state": {
    "java_status": {
      "status": "online",
      "timestamp": "2024-08-22T15:30:45.123Z",
      "last_updated": "2024-08-22T15:30:46.000Z",
      "source": "java-backend",
      "additional_info": {
        "last_seen": "2024-08-22T15:30:40.000Z",
        "connection_type": "wifi",
        "signal_strength": -45,
        "firmware_version": "1.2.3",
        "location": "客厅"
      }
    },
    "python_operations": {
      "last_greeting": "2024-08-22T15:25:30.456Z",
      "pending_tasks": 0
    }
  }
}
```

### **更新的设备在线判断逻辑**
```python
def _is_device_online(self, device_state: dict) -> bool:
    """判断设备是否在线（优先使用Java状态）"""
    if not device_state:
        return False
    
    # 优先使用Java报告的状态
    java_status = device_state.get("java_status")
    if java_status:
        status = java_status.get("status", "").lower()
        timestamp = java_status.get("timestamp")
        
        # 检查状态是否过时（超过10分钟认为过时）
        if timestamp:
            try:
                from datetime import datetime, timedelta
                last_update = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if datetime.now() - last_update < timedelta(minutes=10):
                    return status == "online"
            except:
                pass
    
    # 回退到基于Python端操作活动的判断
    return self._is_device_online_by_activity(device_state)
```

---

## ❓ **关于是否需要单独查询接口**

### **✅ 建议提供查询接口**

**理由：**
1. **系统解耦** - 其他服务可能需要查询设备状态
2. **前端展示** - Web管理界面需要显示设备状态
3. **监控告警** - 运维系统需要查询接口进行健康检查
4. **API统一性** - 保持RESTful API的完整性
5. **调试排查** - 开发阶段便于调试和排查问题

### **🎯 最终架构**
```
┌─────────────┐    MQTT     ┌─────────────┐    HTTP     ┌─────────────┐
│ Java后端     │ ──────────→ │ Python服务   │ ──────────→ │ 其他系统     │
│ (设备管理)   │  设备状态    │ (状态存储)   │  状态查询    │ (前端/监控)  │
└─────────────┘             └─────────────┘             └─────────────┘
```

---

## 🚀 **立即可用的测试**

### **Java端测试**
```java
// 发送设备上线消息
deviceStatusPublisher.publishDeviceStatus("ESP32_001", DeviceStatus.ONLINE);

// 发送设备离线消息  
deviceStatusPublisher.publishDeviceStatus("ESP32_001", DeviceStatus.OFFLINE);
```

### **Python端查询测试**
```bash
# 查询设备状态（包含Java报告的状态）
curl -X GET "http://172.20.12.204:8003/xiaozhi/greeting/status?device_id=ESP32_001"
```

---

## 📋 **配置建议**

### **application.yml (Java)**
```yaml
spring:
  mqtt:
    url: tcp://47.97.185.142:1883
    client-id: java-backend-${random.value}
    username: your_username
    password: your_password
    
xiaozhi:
  device-status:
    sync-interval: 30s
    force-sync-interval: 5m
    topic-prefix: xiaozhi/java-to-python/device-status/
```

---

## 🎯 **总结回答您的问题**

### **是的，建议提供单独的查询接口**

**原因：**
- Java → Python：通过MQTT发送设备状态
- Python → 其他系统：通过HTTP提供查询接口
- 实现系统解耦，满足不同系统的查询需求

**🚀 这样设计的好处：**
1. Java负责设备监控和状态管理
2. Python负责状态存储和API服务
3. 其他系统通过统一接口查询状态
4. 架构清晰，职责分明

**您觉得这个设计方案如何？需要我立即实现Python端的接收逻辑吗？**

# ☕ **Java端发送设备状态 - 完整实现**

## 🎯 **方案B实现：接收Java状态 + 提供简单查询接口**

### **架构流程**
```
Java后端 → MQTT → Python服务 → HTTP接口 → 其他系统查询
```

---

## 📡 **MQTT消息格式**

### **主题(Topic)**
```
xiaozhi/java-to-python/device-status/{device_id}
```

### **消息体格式**
```json
{
  "device_id": "ESP32_001",
  "status": "online",
  "timestamp": "2024-08-22T15:30:45.123Z",
  "source": "java-backend"
}
```

### **状态值**
- `"online"` - 设备在线
- `"offline"` - 设备离线

---

## ☕ **Java端实现代码**

### **1. Maven依赖**
```xml
<dependency>
    <groupId>org.springframework.integration</groupId>
    <artifactId>spring-integration-mqtt</artifactId>
</dependency>
```

### **2. 配置类**
```java
@Configuration
@EnableConfigurationProperties(MqttProperties.class)
public class MqttConfig {
    
    @Autowired
    private MqttProperties mqttProperties;
    
    @Bean
    public MqttPahoClientFactory mqttClientFactory() {
        DefaultMqttPahoClientFactory factory = new DefaultMqttPahoClientFactory();
        MqttConnectOptions options = new MqttConnectOptions();
        
        options.setServerURIs(new String[]{mqttProperties.getUrl()});
        options.setUserName(mqttProperties.getUsername());
        options.setPassword(mqttProperties.getPassword().toCharArray());
        options.setCleanSession(true);
        
        factory.setConnectionOptions(options);
        return factory;
    }
    
    @Bean
    public MqttPahoMessageHandler mqttOutbound() {
        MqttPahoMessageHandler messageHandler = 
            new MqttPahoMessageHandler("java-backend-publisher", mqttClientFactory());
        messageHandler.setAsync(true);
        messageHandler.setDefaultTopic("default-topic");
        return messageHandler;
    }
    
    @Bean
    @ServiceActivator(inputChannel = "mqttOutboundChannel")
    public MessageHandler mqttOutboundHandler() {
        return mqttOutbound();
    }
}
```

### **3. 配置属性**
```java
@ConfigurationProperties(prefix = "mqtt")
@Data
public class MqttProperties {
    private String url = "tcp://47.97.185.142:1883";
    private String username;
    private String password;
    private String clientId = "java-backend-${random.value}";
}
```

### **4. 设备状态发布服务**
```java
@Service
@Slf4j
public class DeviceStatusPublisher {
    
    @Autowired
    private MqttGateway mqttGateway;
    
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final String TOPIC_PREFIX = "xiaozhi/java-to-python/device-status/";
    
    /**
     * 发送设备在线状态
     */
    public void publishDeviceOnline(String deviceId) {
        publishDeviceStatus(deviceId, "online");
    }
    
    /**
     * 发送设备离线状态
     */
    public void publishDeviceOffline(String deviceId) {
        publishDeviceStatus(deviceId, "offline");
    }
    
    /**
     * 发送设备状态
     */
    public void publishDeviceStatus(String deviceId, String status) {
        try {
            DeviceStatusMessage message = DeviceStatusMessage.builder()
                .deviceId(deviceId)
                .status(status.toLowerCase())
                .timestamp(Instant.now().toString())
                .source("java-backend")
                .build();
            
            String topic = TOPIC_PREFIX + deviceId;
            String jsonMessage = objectMapper.writeValueAsString(message);
            
            mqttGateway.sendToMqtt(jsonMessage, topic);
            
            log.info("📡 设备状态已发送: {} -> {}", deviceId, status);
            
        } catch (Exception e) {
            log.error("❌ 发送设备状态失败: deviceId={}, status={}, error={}", 
                     deviceId, status, e.getMessage());
        }
    }
    
    /**
     * 批量发送设备状态
     */
    public void publishBatchDeviceStatus(Map<String, String> deviceStatuses) {
        deviceStatuses.forEach((deviceId, status) -> {
            CompletableFuture.runAsync(() -> publishDeviceStatus(deviceId, status));
        });
    }
}
```

### **5. MQTT网关接口**
```java
@MessagingGateway(defaultRequestChannel = "mqttOutboundChannel")
public interface MqttGateway {
    
    void sendToMqtt(@Payload String data, @Header(MqttHeaders.TOPIC) String topic);
}
```

### **6. 数据传输对象**
```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DeviceStatusMessage {
    private String deviceId;
    private String status;
    private String timestamp;
    private String source;
}
```

### **7. 设备监控服务**
```java
@Service
@Slf4j
public class DeviceMonitoringService {
    
    @Autowired
    private DeviceStatusPublisher statusPublisher;
    
    @Autowired
    private DeviceRepository deviceRepository;
    
    // 存储设备上次状态，避免重复发送
    private final Map<String, String> lastDeviceStatus = new ConcurrentHashMap<>();
    
    /**
     * 定期监控设备状态
     */
    @Scheduled(fixedRate = 30000) // 30秒检查一次
    public void monitorDeviceStatus() {
        List<Device> devices = deviceRepository.findAll();
        
        for (Device device : devices) {
            String currentStatus = checkDeviceStatus(device) ? "online" : "offline";
            String lastStatus = lastDeviceStatus.get(device.getDeviceId());
            
            // 状态发生变化才发送消息
            if (!currentStatus.equals(lastStatus)) {
                statusPublisher.publishDeviceStatus(device.getDeviceId(), currentStatus);
                lastDeviceStatus.put(device.getDeviceId(), currentStatus);
                
                log.info("🔄 设备状态变化: {} {} -> {}", 
                        device.getDeviceId(), lastStatus, currentStatus);
            }
        }
    }
    
    /**
     * 强制同步所有设备状态
     */
    @Scheduled(fixedRate = 300000) // 5分钟强制同步一次
    public void forceSyncAllDeviceStatus() {
        List<Device> devices = deviceRepository.findAll();
        
        Map<String, String> statusMap = new HashMap<>();
        for (Device device : devices) {
            String status = checkDeviceStatus(device) ? "online" : "offline";
            statusMap.put(device.getDeviceId(), status);
            lastDeviceStatus.put(device.getDeviceId(), status);
        }
        
        statusPublisher.publishBatchDeviceStatus(statusMap);
        log.info("🔄 强制同步设备状态: {} 个设备", devices.size());
    }
    
    /**
     * 检查单个设备状态
     */
    private boolean checkDeviceStatus(Device device) {
        try {
            // 实现具体的设备状态检查逻辑
            // 例如：ping设备、检查心跳时间、查询设备管理系统等
            
            // 示例：检查设备最后心跳时间
            if (device.getLastHeartbeat() != null) {
                long timeDiff = System.currentTimeMillis() - device.getLastHeartbeat().getTime();
                return timeDiff < 60000; // 1分钟内有心跳认为在线
            }
            
            return false;
            
        } catch (Exception e) {
            log.error("检查设备状态失败: deviceId={}, error={}", device.getDeviceId(), e.getMessage());
            return false;
        }
    }
}
```

---

## 🐍 **Python端已实现功能**

### **✅ 自动接收Java设备状态**
- 订阅主题：`xiaozhi/java-to-python/device-status/+`
- 自动解析并存储设备在线/离线状态
- 线程安全的状态管理

### **✅ 提供简单查询接口**

#### **完整状态查询**
```bash
curl -X GET "http://172.20.12.204:8003/xiaozhi/greeting/status?device_id=ESP32_001"
```

**响应：**
```json
{
  "device_id": "ESP32_001",
  "connected": true,
  "mqtt_server_connected": true,
  "state": { ... }
}
```

#### **简化状态查询**
```bash
curl -X GET "http://172.20.12.204:8003/xiaozhi/greeting/status?device_id=ESP32_001&simple=true"
```

**响应：**
```json
{
  "device_id": "ESP32_001",
  "online": true
}
```

---

## 🚀 **测试步骤**

### **1. Java端发送测试**
```java
@RestController
@RequestMapping("/test")
public class DeviceStatusTestController {
    
    @Autowired
    private DeviceStatusPublisher statusPublisher;
    
    @PostMapping("/device/{deviceId}/online")
    public ResponseEntity<?> setDeviceOnline(@PathVariable String deviceId) {
        statusPublisher.publishDeviceOnline(deviceId);
        return ResponseEntity.ok(Map.of("message", "设备上线状态已发送", "device_id", deviceId));
    }
    
    @PostMapping("/device/{deviceId}/offline")
    public ResponseEntity<?> setDeviceOffline(@PathVariable String deviceId) {
        statusPublisher.publishDeviceOffline(deviceId);
        return ResponseEntity.ok(Map.of("message", "设备离线状态已发送", "device_id", deviceId));
    }
}
```

### **2. 测试流程**
```bash
# 1. 发送设备上线状态
curl -X POST http://localhost:8080/test/device/ESP32_001/online

# 2. 查询Python端状态（简化版）
curl -X GET "http://172.20.12.204:8003/xiaozhi/greeting/status?device_id=ESP32_001&simple=true"
# 期待响应: {"device_id": "ESP32_001", "online": true}

# 3. 发送设备离线状态
curl -X POST http://localhost:8080/test/device/ESP32_001/offline

# 4. 再次查询Python端状态
curl -X GET "http://172.20.12.204:8003/xiaozhi/greeting/status?device_id=ESP32_001&simple=true"
# 期待响应: {"device_id": "ESP32_001", "online": false}
```

---

## 📋 **配置文件**

### **application.yml**
```yaml
# MQTT配置
mqtt:
  url: tcp://47.97.185.142:1883
  username: your_username
  password: your_password
  client-id: java-backend-${random.value}

# 设备监控配置
device-monitoring:
  status-check-interval: 30s
  force-sync-interval: 5m
  heartbeat-timeout: 60s

# 定时任务配置
spring:
  task:
    scheduling:
      enabled: true
```

---

## 🎯 **方案B总结**

### **✅ 已实现的功能**
1. **Java → Python 状态推送** - 通过MQTT发送设备在线/离线状态
2. **Python状态存储** - 自动接收并存储Java报告的设备状态
3. **简单查询接口** - 提供HTTP接口查询设备是否在线
4. **状态变化监控** - Java端只在状态变化时发送消息
5. **定期同步机制** - 避免状态不一致

### **🚀 使用场景**
- **主要用途**：Python内部判断设备是否在线，决定是否发送问候
- **次要用途**：其他系统通过HTTP接口查询设备状态
- **运维用途**：调试时可以直接查看设备状态

### **📈 扩展性**
- 如果后续需要Web界面显示设备状态，无需修改架构
- 如果需要监控告警，可以直接使用查询接口
- 如果需要更复杂的设备信息，只需扩展消息格式

**🎉 方案B实现完成！Java端可以开始发送设备状态，Python端已准备好接收和提供查询服务！**

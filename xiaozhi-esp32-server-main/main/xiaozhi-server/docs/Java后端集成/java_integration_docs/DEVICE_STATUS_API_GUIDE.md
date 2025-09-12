# 📱 **设备状态查询 API 完整指南**

## 🎯 **Java开发人员必读**

### **❓ 常见问题解答**

**Q: 需要设备在线状态是吗？**
✅ **是的，完全支持！** API会返回设备的实时在线状态。

**Q: 我可在MQTT消息里给你？**
✅ **不需要！** Python端已经通过MQTT自动监控设备状态，Java端只需调用HTTP API即可。

**Q: 需要单独接口查询吗？**
✅ **已经提供！** 单独的GET接口专门用于设备状态查询。

---

## 🌐 **API接口详情**

### **接口地址**
```
GET http://172.20.12.204:8003/xiaozhi/greeting/status
```

### **请求参数**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `device_id` | string | ✅ | 设备唯一标识 |
| `track_id` | string | ⭕ | 特定问候跟踪ID |

### **请求示例**
```bash
# 查询基本设备状态
curl -X GET "http://172.20.12.204:8003/xiaozhi/greeting/status?device_id=ESP32_001"

# 查询特定问候状态
curl -X GET "http://172.20.12.204:8003/xiaozhi/greeting/status?device_id=ESP32_001&track_id=WX202508221053399f03c0"
```

---

## 📊 **响应数据结构**

### **基本设备状态响应**
```json
{
  "device_id": "ESP32_001",
  "connected": true,
  "state": {
    "last_seen": "2024-08-22T10:53:45.123Z",
    "last_greeting": "2024-08-22T10:53:39.985Z",
    "mqtt_status": "online",
    "pending_tasks": 0,
    "hardware_info": {
      "version": "1.0.0",
      "memory_free": "45KB",
      "wifi_strength": -45
    }
  }
}
```

### **包含特定问候跟踪的响应**
```json
{
  "device_id": "ESP32_001",
  "connected": true,
  "track_id": "WX202508221053399f03c0",
  "state": {
    "last_seen": "2024-08-22T10:53:45.123Z",
    "last_greeting": "2024-08-22T10:53:39.985Z",
    "mqtt_status": "online",
    "pending_tasks": 0,
    "greeting_status": {
      "track_id": "WX202508221053399f03c0",
      "status": "completed",
      "sent_at": "2024-08-22T10:53:39.985Z",
      "completed_at": "2024-08-22T10:53:42.156Z",
      "category": "weather",
      "content_preview": "Java集成测试成功！今天天气..."
    },
    "hardware_info": {
      "version": "1.0.0",
      "memory_free": "45KB", 
      "wifi_strength": -45
    }
  }
}
```

### **设备离线响应**
```json
{
  "device_id": "ESP32_002",
  "connected": false,
  "state": {
    "last_seen": "2024-08-22T09:30:12.456Z",
    "mqtt_status": "offline",
    "offline_duration": "01:23:45",
    "last_greeting": "2024-08-22T09:15:30.123Z"
  }
}
```

---

## 🔍 **状态字段详解**

### **连接状态 (`connected`)**
- `true`: 设备在线，MQTT连接正常
- `false`: 设备离线，MQTT连接断开

### **MQTT状态 (`mqtt_status`)**
- `"online"`: MQTT连接活跃
- `"offline"`: MQTT连接断开
- `"connecting"`: 正在重连
- `"error"`: 连接异常

### **问候状态 (`greeting_status.status`)**
- `"sent"`: 已发送，等待设备响应
- `"received"`: 设备已接收
- `"processing"`: 设备正在处理
- `"completed"`: 问候完成
- `"failed"`: 发送失败
- `"timeout"`: 响应超时

---

## ☕ **Java集成代码**

### **1. 设备状态查询服务**
```java
@Service
public class DeviceStatusService {
    
    @Value("${xiaozhi.python.api.url}")
    private String pythonApiUrl;
    
    private final RestTemplate restTemplate;
    
    public DeviceStatusService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }
    
    /**
     * 查询设备基本状态
     */
    public DeviceStatusResponse getDeviceStatus(String deviceId) {
        String url = pythonApiUrl + "/xiaozhi/greeting/status?device_id=" + deviceId;
        
        try {
            ResponseEntity<DeviceStatusResponse> response = restTemplate.getForEntity(
                url, DeviceStatusResponse.class);
            return response.getBody();
        } catch (Exception e) {
            log.error("查询设备状态失败: deviceId={}, error={}", deviceId, e.getMessage());
            return createOfflineStatus(deviceId);
        }
    }
    
    /**
     * 查询特定问候状态
     */
    public DeviceStatusResponse getGreetingStatus(String deviceId, String trackId) {
        String url = pythonApiUrl + "/xiaozhi/greeting/status" +
                    "?device_id=" + deviceId + "&track_id=" + trackId;
        
        try {
            ResponseEntity<DeviceStatusResponse> response = restTemplate.getForEntity(
                url, DeviceStatusResponse.class);
            return response.getBody();
        } catch (Exception e) {
            log.error("查询问候状态失败: deviceId={}, trackId={}, error={}", 
                     deviceId, trackId, e.getMessage());
            return createOfflineStatus(deviceId);
        }
    }
    
    /**
     * 批量查询设备状态
     */
    public Map<String, DeviceStatusResponse> batchGetDeviceStatus(List<String> deviceIds) {
        Map<String, DeviceStatusResponse> results = new HashMap<>();
        
        // 并行查询提高效率
        List<CompletableFuture<Void>> futures = deviceIds.stream()
            .map(deviceId -> CompletableFuture.runAsync(() -> {
                DeviceStatusResponse status = getDeviceStatus(deviceId);
                results.put(deviceId, status);
            }))
            .collect(Collectors.toList());
        
        // 等待所有查询完成
        CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();
        
        return results;
    }
    
    /**
     * 检查设备是否在线
     */
    public boolean isDeviceOnline(String deviceId) {
        DeviceStatusResponse status = getDeviceStatus(deviceId);
        return status != null && status.isConnected();
    }
    
    private DeviceStatusResponse createOfflineStatus(String deviceId) {
        DeviceStatusResponse status = new DeviceStatusResponse();
        status.setDeviceId(deviceId);
        status.setConnected(false);
        // ... 设置其他默认值
        return status;
    }
}
```

### **2. 数据传输对象**
```java
@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class DeviceStatusResponse {
    private String deviceId;
    private boolean connected;
    private String trackId;
    private DeviceState state;
    
    @Data
    public static class DeviceState {
        private String lastSeen;
        private String lastGreeting;
        private String mqttStatus;
        private int pendingTasks;
        private String offlineDuration;
        private GreetingStatus greetingStatus;
        private HardwareInfo hardwareInfo;
    }
    
    @Data
    public static class GreetingStatus {
        private String trackId;
        private String status;
        private String sentAt;
        private String completedAt;
        private String category;
        private String contentPreview;
    }
    
    @Data
    public static class HardwareInfo {
        private String version;
        private String memoryFree;
        private int wifiStrength;
    }
}
```

### **3. REST控制器**
```java
@RestController
@RequestMapping("/api/device")
public class DeviceController {
    
    private final DeviceStatusService deviceStatusService;
    
    @GetMapping("/status/{deviceId}")
    public ResponseEntity<DeviceStatusResponse> getDeviceStatus(@PathVariable String deviceId) {
        DeviceStatusResponse status = deviceStatusService.getDeviceStatus(deviceId);
        return ResponseEntity.ok(status);
    }
    
    @GetMapping("/status/{deviceId}/greeting/{trackId}")
    public ResponseEntity<DeviceStatusResponse> getGreetingStatus(
            @PathVariable String deviceId, 
            @PathVariable String trackId) {
        DeviceStatusResponse status = deviceStatusService.getGreetingStatus(deviceId, trackId);
        return ResponseEntity.ok(status);
    }
    
    @PostMapping("/status/batch")
    public ResponseEntity<Map<String, DeviceStatusResponse>> batchGetStatus(
            @RequestBody List<String> deviceIds) {
        Map<String, DeviceStatusResponse> statuses = 
            deviceStatusService.batchGetDeviceStatus(deviceIds);
        return ResponseEntity.ok(statuses);
    }
    
    @GetMapping("/online/{deviceId}")
    public ResponseEntity<Map<String, Object>> checkOnline(@PathVariable String deviceId) {
        boolean isOnline = deviceStatusService.isDeviceOnline(deviceId);
        return ResponseEntity.ok(Map.of(
            "device_id", deviceId,
            "online", isOnline,
            "checked_at", Instant.now()
        ));
    }
}
```

---

## 🚀 **实用场景**

### **场景1: 定时任务执行前检查**
```java
@Scheduled(cron = "0 */5 * * * ?")
public void executeScheduledGreetings() {
    List<Strategy> strategies = getActiveStrategies();
    
    for (Strategy strategy : strategies) {
        // 执行前检查设备状态
        if (deviceStatusService.isDeviceOnline(strategy.getDeviceId())) {
            // 设备在线，执行问候
            executeSingleGreeting(strategy);
        } else {
            // 设备离线，记录日志并跳过
            log.warn("设备离线，跳过问候: deviceId={}", strategy.getDeviceId());
            logSkippedExecution(strategy, "设备离线");
        }
    }
}
```

### **场景2: 问候执行状态跟踪**
```java
public void trackGreetingExecution(String deviceId, String trackId) {
    // 定期检查问候执行状态
    ScheduledExecutorService executor = Executors.newSingleThreadScheduledExecutor();
    
    executor.scheduleAtFixedRate(() -> {
        DeviceStatusResponse status = deviceStatusService.getGreetingStatus(deviceId, trackId);
        
        if (status.getState().getGreetingStatus() != null) {
            String greetingStatus = status.getState().getGreetingStatus().getStatus();
            
            switch (greetingStatus) {
                case "completed":
                    log.info("问候执行完成: trackId={}", trackId);
                    updateExecutionLog(trackId, "SUCCESS");
                    executor.shutdown();
                    break;
                case "failed":
                    log.error("问候执行失败: trackId={}", trackId);
                    updateExecutionLog(trackId, "FAILED");
                    executor.shutdown();
                    break;
                case "timeout":
                    log.warn("问候执行超时: trackId={}", trackId);
                    updateExecutionLog(trackId, "TIMEOUT");
                    executor.shutdown();
                    break;
                default:
                    log.debug("问候执行中: trackId={}, status={}", trackId, greetingStatus);
            }
        }
    }, 2, 2, TimeUnit.SECONDS);
    
    // 30秒后强制停止检查
    executor.schedule(() -> {
        executor.shutdown();
        log.warn("问候状态检查超时: trackId={}", trackId);
    }, 30, TimeUnit.SECONDS);
}
```

### **场景3: 设备健康监控**
```java
@Component
public class DeviceHealthMonitor {
    
    @Scheduled(fixedRate = 60000) // 每分钟检查一次
    public void monitorDeviceHealth() {
        List<String> allDevices = getAllRegisteredDevices();
        Map<String, DeviceStatusResponse> statuses = 
            deviceStatusService.batchGetDeviceStatus(allDevices);
        
        statuses.forEach((deviceId, status) -> {
            if (!status.isConnected()) {
                handleOfflineDevice(deviceId, status);
            } else if (status.getState().getPendingTasks() > 5) {
                handleOverloadedDevice(deviceId, status);
            }
        });
    }
    
    private void handleOfflineDevice(String deviceId, DeviceStatusResponse status) {
        // 发送告警通知
        alertService.sendAlert(
            AlertLevel.WARNING,
            "设备离线告警",
            String.format("设备 %s 已离线，最后在线时间: %s", 
                         deviceId, status.getState().getLastSeen())
        );
        
        // 暂停该设备的所有策略
        strategyService.pauseDeviceStrategies(deviceId);
    }
    
    private void handleOverloadedDevice(String deviceId, DeviceStatusResponse status) {
        log.warn("设备任务过载: deviceId={}, pendingTasks={}", 
                deviceId, status.getState().getPendingTasks());
        
        // 降低该设备的问候频率
        strategyService.reduceDeviceFrequency(deviceId);
    }
}
```

---

## 📋 **配置建议**

### **application.yml**
```yaml
xiaozhi:
  device-monitor:
    health-check-interval: 60s
    offline-threshold: 300s
    overload-task-limit: 5
    retry-attempts: 3
    timeout: 10s
```

### **RestTemplate配置**
```java
@Bean
public RestTemplate restTemplate() {
    HttpComponentsClientHttpRequestFactory factory = 
        new HttpComponentsClientHttpRequestFactory();
    factory.setConnectTimeout(5000);
    factory.setReadTimeout(10000);
    
    return new RestTemplate(factory);
}
```

---

## ❓ **FAQ**

### **Q: 设备状态多久更新一次？**
A: 设备通过MQTT心跳每30秒更新一次，API查询返回的是实时状态。

### **Q: 如果Python服务重启，设备状态会丢失吗？**
A: 不会，Python服务启动后会自动重新连接MQTT并恢复设备状态。

### **Q: 可以自定义状态查询超时时间吗？**
A: 可以，通过RestTemplate配置`readTimeout`参数调整。

### **Q: 支持WebSocket实时推送设备状态变化吗？**
A: 目前是HTTP轮询模式，如需实时推送可考虑后续版本添加WebSocket支持。

---

## 🎯 **总结**

✅ **设备在线状态** - 完全支持，通过`connected`字段判断  
✅ **MQTT自动监控** - Python端自动处理，Java端无需关心MQTT细节  
✅ **独立查询接口** - 专门的GET接口，支持单个和批量查询  
✅ **状态实时同步** - 30秒心跳，保证状态准确性  
✅ **完整Java集成** - 提供完整的Service和Controller代码  

**🚀 Java开发人员现在可以放心使用设备状态API了！**

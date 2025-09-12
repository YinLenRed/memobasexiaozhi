# 🧪 API测试示例 - 更新后的地址

## 🌐 **服务地址**

**Python服务**: `http://172.20.12.204:8003`

---

## 🚀 **快速测试命令**

### **1. 测试服务连通性**
```bash
curl -X GET http://172.20.12.204:8003/xiaozhi/greeting/status?device_id=test
```

### **2. 发送测试问候**
```bash
curl -X POST http://172.20.12.204:8003/xiaozhi/greeting/send \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_TEST",
    "initial_content": "Java集成测试消息",
    "category": "weather",
    "user_info": {
      "id": "java_test",
      "name": "Java开发者"
    }
  }'
```

### **3. 查询特定设备状态**
```bash
curl -X GET "http://172.20.12.204:8003/xiaozhi/greeting/status?device_id=ESP32_001"
```

---

## ☕ **Java代码示例**

### **基本连接测试**
```java
@RestController
public class PythonApiTestController {
    
    private final String PYTHON_API_BASE = "http://172.20.12.204:8003";
    private final RestTemplate restTemplate = new RestTemplate();
    
    @GetMapping("/test/python-connection")
    public ResponseEntity<?> testConnection() {
        try {
            String url = PYTHON_API_BASE + "/xiaozhi/greeting/status?device_id=test";
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
            
            return ResponseEntity.ok(Map.of(
                "status", "success",
                "message", "Python API连接正常",
                "python_response", response.getBody()
            ));
        } catch (Exception e) {
            return ResponseEntity.status(500)
                .body(Map.of("error", "连接失败: " + e.getMessage()));
        }
    }
    
    @PostMapping("/test/send-greeting")
    public ResponseEntity<?> testSendGreeting() {
        try {
            String url = PYTHON_API_BASE + "/xiaozhi/greeting/send";
            
            Map<String, Object> request = Map.of(
                "device_id", "ESP32_JAVA_TEST",
                "initial_content", "Java集成测试成功！",
                "category", "weather",
                "user_info", Map.of(
                    "id", "java_developer",
                    "name", "Java开发者"
                )
            );
            
            ResponseEntity<Map> response = restTemplate.postForEntity(url, request, Map.class);
            
            return ResponseEntity.ok(Map.of(
                "status", "success", 
                "message", "问候发送成功",
                "python_response", response.getBody()
            ));
        } catch (Exception e) {
            return ResponseEntity.status(500)
                .body(Map.of("error", "发送失败: " + e.getMessage()));
        }
    }
}
```

---

## 📋 **配置文件示例**

### **application.yml**
```yaml
# 开发环境配置
xiaozhi:
  python:
    api:
      # 实际的内网地址
      url: http://172.20.12.204:8003
      timeout: 30s
  proactive-greeting:
    enabled: true
    
# HTTP客户端配置
spring:
  web:
    resources:
      add-mappings: false
  mvc:
    throw-exception-if-no-handler-found: true

# RestTemplate配置
http:
  client:
    connection-timeout: 5000
    read-timeout: 10000
```

### **Spring Boot配置类**
```java
@Configuration
public class HttpClientConfig {
    
    @Value("${xiaozhi.python.api.url:http://172.20.12.204:8003}")
    private String pythonApiUrl;
    
    @Bean
    public RestTemplate restTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(10000);
        return new RestTemplate(factory);
    }
    
    @Bean
    public PythonApiClient pythonApiClient(RestTemplate restTemplate) {
        return new PythonApiClient(pythonApiUrl, restTemplate);
    }
}
```

---

## 🔍 **故障排除**

### **连接测试**
```bash
# 检查网络连通性
ping 172.20.12.204

# 检查端口开放
telnet 172.20.12.204 8003

# 检查服务响应
curl -i http://172.20.12.204:8003/xiaozhi/greeting/status?device_id=test
```

### **常见错误处理**
```java
@Component
public class PythonApiErrorHandler {
    
    public ResponseEntity<?> handleConnectionError(Exception e) {
        if (e instanceof ResourceAccessException) {
            return ResponseEntity.status(503)
                .body(Map.of(
                    "error", "Python服务不可达",
                    "message", "请检查服务地址: http://172.20.12.204:8003",
                    "suggestion", "确认Python服务是否启动且网络可达"
                ));
        }
        
        if (e instanceof HttpClientErrorException) {
            HttpClientErrorException httpError = (HttpClientErrorException) e;
            return ResponseEntity.status(httpError.getStatusCode())
                .body(Map.of(
                    "error", "Python API错误",
                    "status", httpError.getStatusCode().value(),
                    "message", httpError.getResponseBodyAsString()
                ));
        }
        
        return ResponseEntity.status(500)
            .body(Map.of("error", "未知错误: " + e.getMessage()));
    }
}
```

---

## ✅ **成功响应示例**

### **设备状态查询成功**
```json
{
  "success": true,
  "device_id": "ESP32_001",
  "status": "connected",
  "last_greeting": "2024-08-21T15:30:12",
  "pending_requests": 0
}
```

### **问候发送成功**
```json
{
  "success": true,
  "message": "主动问候发送成功",
  "track_id": "WX20240821153012abc123",
  "device_id": "ESP32_TEST",
  "timestamp": 1724234567.123
}
```

---

**🎯 所有地址已更新为实际的内网地址！Java开发可以直接使用！** ✅

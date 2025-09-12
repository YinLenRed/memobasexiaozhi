# 🚀 Java后端快速集成 - 主动问候功能

> **5分钟快速集成指南**

## 🎯 Python端已准备就绪

✅ **MQTT通信** - 完整实现  
✅ **问候服务** - 智能内容生成  
✅ **TTS合成** - 多提供商支持  
✅ **HTTP API** - 供Java调用  
✅ **设备管理** - 状态跟踪  

## 📡 核心API接口

### 发送问候
```bash
curl -X POST http://172.20.12.204:8003/xiaozhi/greeting/send \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "initial_content": "今天天气很好！",
    "category": "weather",
    "user_info": {
      "id": "user001", 
      "name": "张三"
    }
  }'
```

### 查询设备状态
```bash
curl -X GET http://172.20.12.204:8003/xiaozhi/greeting/status?device_id=ESP32_001
```

## ⏰ Java端需要实现

### 1. 定时任务调度
```java
@Scheduled(cron = "0 * * * * ?")
public void executeGreetingStrategies() {
    // 获取需要执行的策略
    List<Strategy> strategies = getActiveStrategies();
    
    for (Strategy strategy : strategies) {
        // 调用Python API
        restTemplate.postForObject(
            "http://172.20.12.204:8003/xiaozhi/greeting/send",
            buildRequest(strategy),
            GreetingResponse.class
        );
    }
}
```

### 2. 策略数据表
```sql
CREATE TABLE greeting_strategy (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    device_ids JSON,
    cron_expression VARCHAR(50),
    content_template TEXT,
    enabled TINYINT DEFAULT 1
);
```

### 3. API客户端
```java
@Service
public class PythonApiClient {
    private final RestTemplate restTemplate;
    
    @Value("${python.api.url:http://172.20.12.204:8003}")
    private String pythonApiUrl;
    
    public GreetingResponse sendGreeting(GreetingRequest request) {
        return restTemplate.postForObject(
            pythonApiUrl + "/xiaozhi/greeting/send",
            request,
            GreetingResponse.class
        );
    }
}
```

## 🔧 配置要求

### application.yml
```yaml
python:
  api:
    url: http://172.20.12.204:8003

spring:
  task:
    scheduling:
      pool:
        size: 5
```

## 📋 CRON表达式示例

| 描述 | CRON表达式 |
|------|------------|
| 每天8点 | `0 0 8 * * ?` |
| 工作日9点 | `0 0 9 ? * MON-FRI` |
| 每小时整点 | `0 0 * * * ?` |
| 每30分钟 | `0 */30 * * * ?` |

## ✅ 测试步骤

1. **启动Python服务**
2. **测试API连通性**
3. **创建测试策略**
4. **验证定时执行**

## 📞 问题咨询

详细文档：[JAVA_CRON_INTEGRATION_GUIDE.md](./JAVA_CRON_INTEGRATION_GUIDE.md)

---
**Python端已就绪，等待您的集成！** 🎉

# ⏰ Cron表达式生成器使用指南

## 🎯 功能概述

提供中文自然语言到Java Quartz兼容cron表达式的转换功能，支持多种时间描述格式。

### ✅ **核心功能**
- 🇨🇳 **中文时间解析**: 支持自然语言时间描述
- ☕ **Java兼容**: 生成Java Quartz调度器兼容格式  
- 🔄 **批量处理**: 支持批量生成cron表达式
- ✅ **格式验证**: 自动验证生成的表达式
- 📋 **详细信息**: 提供解析过程和执行说明

---

## 🚀 快速开始

### 1️⃣ **基本使用**

```python
from java_cron_generator import generate_cron

# 生成cron表达式
result = generate_cron("每天早上8点13分")
print(result)  # 输出: 0 13 8 * * ?
```

### 2️⃣ **API接口使用**

```python
from api_cron_generator import CronAPI

# 单个表达式生成
result = CronAPI.generate_cron_expression("每天早上8点13分")
print(result["cron_expression"])  # 输出: 0 13 8 * * ?

# 详细信息生成
detailed = CronAPI.generate_cron_with_validation("每周一上午9点")
print(detailed["cron_expression"])  # 输出: 0 0 9 ? * 1
```

---

## 📋 支持的时间格式

### 🔄 **频率类型**

| 中文描述 | 示例 | 生成结果 |
|----------|------|----------|
| **每天** | `每天早上8点13分` | `0 13 8 * * ?` |
| **每周** | `每周一上午9点` | `0 0 9 ? * 1` |
| **每月** | `每月15号下午2点` | `0 0 14 15 * ?` |
| **每年** | `每年1月1日上午8点` | `0 0 8 1 1 ?` |

### ⏰ **时间格式**

| 格式类型 | 示例 | 说明 |
|----------|------|------|
| **小时+分钟** | `8点13分`、`8:13` | 精确时间 |
| **只有小时** | `8点`、`上午8点` | 分钟默认为0 |
| **半点时间** | `8点半` | 分钟为30 |
| **时间段** | `早上`、`下午`、`晚上` | 使用时间段默认小时 |

### 📅 **日期格式**

| 类型 | 示例 | 说明 |
|------|------|------|
| **星期** | `周一`、`星期二`、`礼拜三` | 支持多种表达 |
| **日期** | `15号`、`1日` | 月内日期 |
| **月份** | `1月`、`12月` | 年内月份 |

---

## 🧪 测试命令

### **快速验证**
```bash
cd /home/web/xiaozhi-esp32-server-main/main/xiaozhi-server
python simple_cron_test.py
```

### **完整测试**
```bash
python api_cron_generator.py
```

### **批量测试**
```bash
python -c "
from api_cron_generator import CronAPI
test_cases = ['每天早上8点13分', '每周一上午9点', '每月15号下午2点']
result = CronAPI.batch_generate(test_cases)
for item in result['results']:
    print(f'{item[\"time_description\"]} -> {item[\"cron_expression\"]}')
"
```

---

## ☕ Java后端集成

### 1️⃣ **Python服务端**

```python
from api_cron_generator import CronAPI
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/generate-cron', methods=['POST'])
def generate_cron_api():
    data = request.get_json()
    time_description = data.get('time_description')
    timezone = data.get('timezone', 'Asia/Shanghai')
    
    result = CronAPI.generate_cron_expression(time_description, timezone)
    return jsonify(result)

@app.route('/api/batch-generate-cron', methods=['POST'])
def batch_generate_cron_api():
    data = request.get_json()
    time_descriptions = data.get('time_descriptions', [])
    timezone = data.get('timezone', 'Asia/Shanghai')
    
    result = CronAPI.batch_generate(time_descriptions, timezone)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
```

### 2️⃣ **Java客户端调用**

```java
import org.springframework.web.client.RestTemplate;
import com.fasterxml.jackson.databind.ObjectMapper;

public class CronGeneratorClient {
    
    private final RestTemplate restTemplate = new RestTemplate();
    private final String apiUrl = "http://python-server:5001";
    
    public String generateCron(String timeDescription) {
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("time_description", timeDescription);
            request.put("timezone", "Asia/Shanghai");
            
            ResponseEntity<Map> response = restTemplate.postForEntity(
                apiUrl + "/api/generate-cron", 
                request, 
                Map.class
            );
            
            Map<String, Object> result = response.getBody();
            if ((Boolean) result.get("success")) {
                return (String) result.get("cron_expression");
            } else {
                throw new RuntimeException("生成失败: " + result.get("error"));
            }
            
        } catch (Exception e) {
            throw new RuntimeException("调用Python API失败", e);
        }
    }
    
    // 使用示例
    public void scheduleTask() {
        String cronExpression = generateCron("每天早上8点13分");
        // cronExpression = "0 13 8 * * ?"
        
        // 使用Spring Schedule或Quartz
        taskScheduler.schedule(myTask, new CronTrigger(cronExpression));
    }
}
```

### 3️⃣ **Spring Boot集成**

```java
@RestController
@RequestMapping("/api/cron")
public class CronController {
    
    @Autowired
    private CronGeneratorClient cronClient;
    
    @PostMapping("/generate")
    public ResponseEntity<?> generateCron(@RequestBody CronRequest request) {
        try {
            String cronExpression = cronClient.generateCron(request.getTimeDescription());
            return ResponseEntity.ok(new CronResponse(true, cronExpression));
        } catch (Exception e) {
            return ResponseEntity.badRequest()
                .body(new CronResponse(false, e.getMessage()));
        }
    }
}
```

---

## 🔧 部署配置

### **Docker部署**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5001

CMD ["python", "cron_api_server.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  cron-generator:
    build: .
    ports:
      - "5001:5001"
    environment:
      - TIMEZONE=Asia/Shanghai
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### **Kubernetes部署**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cron-generator
spec:
  replicas: 2
  selector:
    matchLabels:
      app: cron-generator
  template:
    metadata:
      labels:
        app: cron-generator
    spec:
      containers:
      - name: cron-generator
        image: your-registry/cron-generator:latest
        ports:
        - containerPort: 5001
        env:
        - name: TIMEZONE
          value: "Asia/Shanghai"
---
apiVersion: v1
kind: Service
metadata:
  name: cron-generator-service
spec:
  selector:
    app: cron-generator
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5001
```

---

## 📊 API响应格式

### **成功响应**
```json
{
  "success": true,
  "cron_expression": "0 13 8 * * ?",
  "time_description": "每天早上8点13分",
  "timezone": "Asia/Shanghai",
  "generated_at": "2025-01-19T17:30:00",
  "message": "Cron表达式生成成功"
}
```

### **失败响应**
```json
{
  "success": false,
  "error": "无法解析时间描述",
  "time_description": "无效输入",
  "timezone": "Asia/Shanghai",
  "message": "Cron表达式生成失败"
}
```

### **批量响应**
```json
{
  "success": true,
  "total": 3,
  "success_count": 2,
  "failed_count": 1,
  "results": [
    {
      "success": true,
      "cron_expression": "0 13 8 * * ?",
      "time_description": "每天早上8点13分"
    }
  ],
  "message": "批量生成完成: 2/3 成功"
}
```

---

## ⚠️ 注意事项

### **Java Quartz规则**
- 日字段和周字段不能同时指定
- 当指定日期时，周字段必须为`?`
- 当指定星期时，日字段必须为`?`
- `?` 表示该字段被忽略

### **时区处理**
- 默认时区：`Asia/Shanghai`
- 支持标准时区名称
- Java端需要确保时区一致性

### **错误处理**
- 无效时间描述返回错误信息
- 提供详细的错误原因
- 支持批量处理中的部分失败

---

## 🎉 验证结果

**✅ 核心功能测试通过：**
```
输入: 每天早上8点13分
输出: 0 13 8 * * ?
期望: 0 13 8 * * ?
匹配: ✅ 成功
```

**🚀 现在可以安全集成到Java后端系统中！**

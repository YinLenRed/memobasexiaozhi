# ⏰ Java后端Cron API集成指南

## 🎯 API概述

小智系统现已集成Cron表达式生成API，支持中文自然语言转换为Java Quartz兼容的cron表达式。

### ✅ **核心功能**
- 🇨🇳 **中文自然语言解析**: 支持"每天早上8点13分"等自然表达
- ☕ **Java Quartz兼容**: 生成标准Java调度器格式
- 🔄 **批量处理**: 支持批量生成多个cron表达式
- ✅ **格式验证**: 自动验证生成的表达式
- 📡 **RESTful API**: 标准HTTP接口，易于集成

---

## 🚀 快速开始

### 📍 **API基础信息**

**基础URL**: `http://YOUR_SERVER_IP:8003/api/cron`

**支持格式**: JSON
**字符编码**: UTF-8
**请求方式**: GET / POST

---

## 📋 API端点说明

### 1️⃣ **生成单个Cron表达式**

**端点**: `POST /api/cron/generate`

**请求示例**:
```json
{
  "time_description": "每天早上8点13分",
  "timezone": "Asia/Shanghai"
}
```

**响应示例**:
```json
{
  "success": true,
  "timestamp": "2025-08-21T16:30:00.000Z",
  "message": "生成成功",
  "data": {
    "cron_expression": "0 13 8 * * ?",
    "description": "每天上午8点13分执行",
    "timezone": "Asia/Shanghai",
    "input_description": "每天早上8点13分"
  }
}
```

### 2️⃣ **批量生成Cron表达式**

**端点**: `POST /api/cron/batch-generate`

**请求示例**:
```json
{
  "time_descriptions": [
    "每天早上8点13分",
    "每周一上午9点", 
    "每月15号下午2点"
  ],
  "timezone": "Asia/Shanghai"
}
```

**响应示例**:
```json
{
  "success": true,
  "timestamp": "2025-08-21T16:30:00.000Z", 
  "message": "批量生成完成",
  "data": {
    "total": 3,
    "success_count": 3,
    "failed_count": 0,
    "results": [
      {
        "success": true,
        "data": {
          "cron_expression": "0 13 8 * * ?",
          "description": "每天上午8点13分执行"
        }
      }
    ]
  }
}
```

### 3️⃣ **验证Cron表达式**

**端点**: `POST /api/cron/validate`

**请求示例**:
```json
{
  "cron_expression": "0 13 8 * * ?"
}
```

**响应示例**:
```json
{
  "success": true,
  "timestamp": "2025-08-21T16:30:00.000Z",
  "message": "cron表达式有效", 
  "data": {
    "cron_expression": "0 13 8 * * ?",
    "is_valid": true,
    "format": "Java Quartz格式"
  }
}
```

### 4️⃣ **健康检查**

**端点**: `GET /api/cron/health`

**响应示例**:
```json
{
  "success": true,
  "timestamp": "2025-08-21T16:30:00.000Z",
  "message": "服务健康",
  "data": {
    "status": "healthy",
    "service": "xiaozhi-cron-generator",
    "version": "1.0.0"
  }
}
```

### 5️⃣ **获取示例**

**端点**: `GET /api/cron/examples`

**响应示例**:
```json
{
  "success": true,
  "data": {
    "examples": [
      {
        "description": "每天早上8点13分",
        "cron_expression": "0 13 8 * * ?",
        "explanation": "每天上午8点13分执行"
      }
    ]
  }
}
```

---

## ☕ Java集成示例

### 1️⃣ **使用Spring RestTemplate**

```java
@Service
public class CronGeneratorService {
    
    private static final String CRON_API_BASE_URL = "http://xiaozhi-server:8003/api/cron";
    
    @Autowired
    private RestTemplate restTemplate;
    
    /**
     * 生成单个cron表达式
     */
    public String generateCronExpression(String timeDescription) {
        try {
            // 构建请求
            Map<String, String> request = new HashMap<>();
            request.put("time_description", timeDescription);
            request.put("timezone", "Asia/Shanghai");
            
            // 发送请求
            HttpEntity<Map<String, String>> entity = new HttpEntity<>(request);
            ResponseEntity<CronApiResponse> response = restTemplate.postForEntity(
                CRON_API_BASE_URL + "/generate", 
                entity, 
                CronApiResponse.class
            );
            
            // 处理响应
            if (response.getStatusCode().is2xxSuccessful() && 
                response.getBody().isSuccess()) {
                return response.getBody().getData().getCronExpression();
            }
            
            throw new RuntimeException("Cron生成失败: " + response.getBody().getMessage());
            
        } catch (Exception e) {
            log.error("调用Cron生成API失败", e);
            throw new RuntimeException("Cron生成服务不可用", e);
        }
    }
    
    /**
     * 批量生成cron表达式
     */
    public List<String> batchGenerateCronExpressions(List<String> timeDescriptions) {
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("time_descriptions", timeDescriptions);
            request.put("timezone", "Asia/Shanghai");
            
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request);
            ResponseEntity<BatchCronApiResponse> response = restTemplate.postForEntity(
                CRON_API_BASE_URL + "/batch-generate",
                entity,
                BatchCronApiResponse.class
            );
            
            if (response.getStatusCode().is2xxSuccessful() && 
                response.getBody().isSuccess()) {
                
                return response.getBody().getData().getResults().stream()
                    .filter(result -> result.isSuccess())
                    .map(result -> result.getData().getCronExpression())
                    .collect(Collectors.toList());
            }
            
            throw new RuntimeException("批量Cron生成失败");
            
        } catch (Exception e) {
            log.error("批量调用Cron生成API失败", e);
            return Collections.emptyList();
        }
    }
}
```

### 2️⃣ **响应实体类**

```java
// 基础响应类
@Data
public class CronApiResponse {
    private boolean success;
    private String timestamp;
    private String message;
    private CronData data;
}

@Data
public class CronData {
    private String cronExpression;
    private String description;
    private String timezone;
    private String inputDescription;
}

// 批量响应类
@Data
public class BatchCronApiResponse {
    private boolean success;
    private String timestamp;
    private String message;
    private BatchCronData data;
}

@Data
public class BatchCronData {
    private int total;
    private int successCount;
    private int failedCount;
    private List<CronResult> results;
}

@Data
public class CronResult {
    private boolean success;
    private CronData data;
    private String message;
}
```

### 3️⃣ **配置RestTemplate**

```java
@Configuration
public class RestTemplateConfig {
    
    @Bean
    public RestTemplate restTemplate() {
        RestTemplate restTemplate = new RestTemplate();
        
        // 设置超时时间
        HttpComponentsClientHttpRequestFactory factory = 
            new HttpComponentsClientHttpRequestFactory();
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(10000);
        restTemplate.setRequestFactory(factory);
        
        // 设置消息转换器
        restTemplate.getMessageConverters().add(0, new StringHttpMessageConverter(StandardCharsets.UTF_8));
        
        return restTemplate;
    }
}
```

### 4️⃣ **使用示例**

```java
@RestController
@RequestMapping("/api/schedule")
public class ScheduleController {
    
    @Autowired
    private CronGeneratorService cronGeneratorService;
    
    @PostMapping("/create-task")
    public ResponseEntity<String> createScheduledTask(@RequestBody CreateTaskRequest request) {
        try {
            // 生成cron表达式
            String cronExpression = cronGeneratorService.generateCronExpression(
                request.getTimeDescription()
            );
            
            // 创建定时任务
            scheduleTask(request.getTaskName(), cronExpression, request.getTaskAction());
            
            return ResponseEntity.ok("定时任务创建成功，cron表达式: " + cronExpression);
            
        } catch (Exception e) {
            return ResponseEntity.badRequest().body("创建定时任务失败: " + e.getMessage());
        }
    }
    
    @Scheduled(cron = "#{@cronGeneratorService.generateCronExpression('每天早上8点')}")
    public void dailyTask() {
        // 动态生成的定时任务
        log.info("执行每日任务");
    }
}
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

---

## 🔧 错误处理

### 常见错误码

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| `MISSING_TIME_DESCRIPTION` | 缺少时间描述参数 | 检查请求参数 |
| `GENERATION_FAILED` | cron表达式生成失败 | 检查时间描述格式 |
| `INVALID_JSON` | JSON格式错误 | 检查请求体格式 |
| `TOO_MANY_REQUESTS` | 批量请求超限 | 减少批量数量(<50) |

### 错误响应示例

```json
{
  "success": false,
  "timestamp": "2025-08-21T16:30:00.000Z",
  "message": "time_description参数不能为空",
  "data": {
    "error": "time_description参数不能为空",
    "error_code": "MISSING_TIME_DESCRIPTION"
  }
}
```

---

## 🚀 部署和配置

### 1️⃣ **环境要求**
- Python 3.8+
- 小智服务器运行在端口8003
- 网络连通性确保Java后端可访问

### 2️⃣ **配置检查**
```bash
# 检查API服务状态
curl http://YOUR_SERVER_IP:8003/api/cron/health

# 测试基本功能
curl -X POST http://YOUR_SERVER_IP:8003/api/cron/generate \
  -H "Content-Type: application/json" \
  -d '{"time_description":"每天早上8点"}'
```

### 3️⃣ **性能优化建议**
- 使用连接池管理HTTP连接
- 实现缓存机制避免重复调用
- 设置合适的超时时间
- 监控API调用频率和错误率

---

## 🎉 总结

现在Java后端可以通过标准HTTP API调用小智的Cron表达式生成功能：

- ✅ **简单易用**: 标准RESTful API接口
- ✅ **功能完整**: 支持生成、验证、批量处理
- ✅ **格式兼容**: 生成Java Quartz兼容的cron表达式
- ✅ **错误处理**: 完善的错误码和错误信息
- ✅ **文档完整**: 详细的API文档和Java集成示例

**🚀 现在就可以开始在Java项目中集成使用！**

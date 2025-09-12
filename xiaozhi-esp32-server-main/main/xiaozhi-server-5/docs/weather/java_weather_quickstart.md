# 🚀 Java后端天气接口快速实现指南

**快速上手时间**: 30分钟  
**完成后即可与Python端联调**

---

## 📋 快速实现清单

### ✅ 第一步：创建Controller (5分钟)

```java
package com.xiaozhi.controller;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.beans.factory.annotation.Value;
import lombok.extern.slf4j.Slf4j;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import java.util.HashMap;

@RestController
@RequestMapping("/api/weather")
@Slf4j
public class WeatherController {
    
    @Value("${api.secret:your-api-secret-key}")
    private String apiSecret;
    
    @GetMapping("/device/{deviceId}")
    public ResponseEntity<?> getWeatherByDevice(
        @PathVariable String deviceId,
        @RequestHeader("Authorization") String authorization
    ) {
        try {
            // 1. 验证认证
            if (!isValidAuth(authorization)) {
                return ResponseEntity.status(401).body(Map.of("error", "认证失败"));
            }
            
            // 2. 根据设备ID返回天气数据 (先返回模拟数据)
            Map<String, Object> weather = getWeatherData(deviceId);
            
            log.info("天气查询成功: deviceId={}", deviceId);
            return ResponseEntity.ok(weather);
            
        } catch (Exception e) {
            log.error("天气API异常: {}", e.getMessage());
            return ResponseEntity.status(500).body(Map.of("error", "服务内部错误"));
        }
    }
    
    private boolean isValidAuth(String auth) {
        if (auth == null || !auth.startsWith("Bearer ")) return false;
        return apiSecret.equals(auth.substring(7));
    }
    
    private Map<String, Object> getWeatherData(String deviceId) {
        // 🔥 临时模拟数据，后续替换为真实API调用
        Map<String, Object> weather = new HashMap<>();
        weather.put("city", "广州");
        weather.put("temperature", "28");
        weather.put("weather", "晴");
        weather.put("high", "32");
        weather.put("low", "24");
        weather.put("wind", "东南风2级");
        weather.put("humidity", "65%");
        weather.put("suggestion", "天气晴朗，适合外出活动。老年人请注意防晒。");
        weather.put("updateTime", LocalDateTime.now().format(
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
        return weather;
    }
}
```

### ✅ 第二步：配置文件 (2分钟)

**application.yml**
```yaml
# API安全配置
api:
  secret: your-api-secret-key  # 与Python端保持一致

# 服务端口
server:
  port: 8080

# 日志配置
logging:
  level:
    com.xiaozhi: DEBUG
```

### ✅ 第三步：启动类配置 (1分钟)

```java
package com.xiaozhi;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class XiaozhiApplication {
    public static void main(String[] args) {
        SpringApplication.run(XiaozhiApplication.class, args);
    }
}
```

---

## 🧪 立即测试

### 1. 启动Java服务
```bash
mvn spring-boot:run
# 或
./gradlew bootRun
```

### 2. 测试天气接口
```bash
curl -H "Authorization: Bearer your-api-secret-key" \
     "http://localhost:8080/api/weather/device/ESP32_001"
```

### 3. 预期响应
```json
{
  "city": "广州",
  "temperature": "28",
  "weather": "晴",
  "high": "32",
  "low": "24",
  "wind": "东南风2级", 
  "humidity": "65%",
  "suggestion": "天气晴朗，适合外出活动。老年人请注意防晒。",
  "updateTime": "2025-08-14 15:30:00"
}
```

### 4. 更新Python配置
在 `config.yaml` 中确认：
```yaml
manager-api:
  url: "http://localhost:8080"  # Java服务地址
  secret: "your-api-secret-key"  # 与Java端一致
```

### 5. 测试Python集成
```bash
cd xiaozhi-esp32-server-main/main/xiaozhi-server
python test_http_memobase.py  # 会自动测试天气功能
```

---

## 🔧 后续完善 (可分步实现)

### 第二阶段：真实天气API集成

**添加依赖**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

**WeatherService实现**
```java
@Service
@Slf4j
public class WeatherService {
    
    @Value("${weather.api.key:}")
    private String weatherApiKey;
    
    @Autowired
    private RestTemplate restTemplate;
    
    public Map<String, Object> getRealWeather(String cityCode) {
        try {
            // 调用和风天气API示例
            String url = String.format(
                "https://devapi.qweather.com/v7/weather/now?location=%s&key=%s",
                cityCode, weatherApiKey);
            
            // 这里实现真实的API调用
            WeatherResponse response = restTemplate.getForObject(url, WeatherResponse.class);
            
            return convertResponse(response);
            
        } catch (Exception e) {
            log.error("天气API调用失败: {}", e.getMessage());
            return getDefaultWeather();
        }
    }
}
```

### 第三阶段：设备-城市绑定

**数据库表**
```sql
CREATE TABLE device_location (
    device_id VARCHAR(50) PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL,
    city_code VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入测试数据
INSERT INTO device_location VALUES 
('ESP32_001', '广州', '440100', NOW()),
('ESP32_002', '深圳', '440300', NOW());
```

**DeviceService实现**
```java
@Service
public class DeviceService {
    
    @Autowired
    private JdbcTemplate jdbcTemplate;
    
    public String getCityCodeByDevice(String deviceId) {
        try {
            return jdbcTemplate.queryForObject(
                "SELECT city_code FROM device_location WHERE device_id = ?",
                String.class, deviceId);
        } catch (Exception e) {
            log.warn("设备{}未绑定城市", deviceId);
            return "440100"; // 默认广州
        }
    }
}
```

---

## 📊 开发进度规划

| 阶段 | 功能 | 预计时间 | 状态 |
|------|------|----------|------|
| 阶段1 | 基础接口 + 模拟数据 | ✅ 30分钟 | 可立即测试 |
| 阶段2 | 真实天气API集成 | 🔄 2小时 | 建议本周完成 |
| 阶段3 | 设备-城市绑定管理 | 🔄 4小时 | 建议下周完成 |
| 阶段4 | 监控 + 优化 | 🔄 2小时 | 可后续优化 |

---

## 🚨 重要提醒

### 立即可用的最小配置

1. **✅ 第一步实现** - 30分钟内即可与Python端联调
2. **🔑 关键配置** - 确保API密钥与Python端一致  
3. **🧪 测试优先** - 先跑通基础流程，再逐步完善

### 配置要点

**Java端**
```yaml
api:
  secret: your-api-secret-key  # 🔥 关键：与Python端保持一致
```

**Python端**
```yaml
manager-api:
  url: "http://localhost:8080"     # 🔥 关键：Java服务实际地址
  secret: "your-api-secret-key"    # 🔥 关键：与Java端保持一致
```

---

## 🎯 验证成功标准

### ✅ 基础功能验证
- [ ] Java接口返回200状态码
- [ ] 返回数据格式正确
- [ ] Python端能成功调用
- [ ] 天气问候功能正常

### ✅ 集成测试验证
```bash
# Python端天气问候测试
curl -X POST http://localhost:8003/xiaozhi/greeting/send \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "category": "weather",
    "initial_content": "今天天气不错",
    "user_info": {"name": "李叔", "age": 65}
  }'
```

**预期结果**: 返回包含实际天气信息的个性化问候内容。

---

**🎉 Java后端天气接口实现30分钟即可完成基础版本，立即支持ESP32天气问候功能！** 🌤️

---

**快速实现指南**: 2025年8月14日  
**联调支持**: Python团队随时协助  
**技术栈**: Spring Boot + RestTemplate**

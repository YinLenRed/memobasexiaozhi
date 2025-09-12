# 🌤️ Java后端天气接口需求规范

**需求确认日期**: 2025年8月14日  
**集成状态**: Python端已完成，等待Java后端实现  
**优先级**: 🔴 **高优先级** - 天气问候功能依赖此接口

---

## 📋 需求背景

ESP32老年人AI设备的主动问候功能已经完整实现，其中天气类问候需要调用Java后端的天气API来获取实时天气数据，为老年用户提供贴心的天气提醒和建议。

**Python端已完成:**
- ✅ 天气工具模块 (`core/tools/weather_tool.py`)
- ✅ 主动问候服务集成
- ✅ LLM Function Calling支持
- ✅ 错误处理和备用方案

**需要Java后端配合:**
- ❌ 天气API接口实现
- ❌ 设备-城市绑定管理
- ❌ 第三方天气数据集成

---

## 🔧 必需的API接口

### 1. 核心天气接口

#### **接口地址**
```
GET /api/weather/device/{device_id}
```

#### **请求参数**
- **Path参数**: `device_id` (String) - ESP32设备ID，如 "ESP32_001"
- **Header**: `Authorization: Bearer {api_secret}` - API认证密钥

#### **请求示例**
```http
GET /api/weather/device/ESP32_001 HTTP/1.1
Host: your-java-server:8080
Authorization: Bearer your-api-secret-key
Content-Type: application/json
```

#### **成功响应 (HTTP 200)**
```json
{
  "city": "广州",
  "temperature": "28",
  "weather": "晴",
  "high": "32", 
  "low": "24",
  "wind": "东南风2级",
  "humidity": "65%",
  "suggestion": "天气晴朗，适合外出活动。建议老年人上午或傍晚时段外出散步。",
  "updateTime": "2025-08-14 14:30:00"
}
```

#### **错误响应示例**

**设备未找到 (HTTP 404)**
```json
{
  "error": "设备未找到或未绑定城市",
  "code": "DEVICE_NOT_FOUND",
  "deviceId": "ESP32_001"
}
```

**认证失败 (HTTP 401)**
```json
{
  "error": "认证失败",
  "code": "UNAUTHORIZED"
}
```

**服务异常 (HTTP 500)**
```json
{
  "error": "获取天气信息失败",
  "code": "INTERNAL_ERROR",
  "message": "第三方天气API调用失败"
}
```

---

## 💾 数据库设计建议

### 设备-城市绑定表
```sql
CREATE TABLE device_location (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL UNIQUE,
    city_name VARCHAR(100) NOT NULL,
    city_code VARCHAR(20),  -- 第三方天气API的城市代码
    province VARCHAR(50),
    latitude DECIMAL(10,8),  -- 纬度（可选，用于精确定位）
    longitude DECIMAL(11,8), -- 经度（可选，用于精确定位）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_device_id (device_id)
);
```

### 示例数据
```sql
INSERT INTO device_location (device_id, city_name, city_code, province) VALUES
('ESP32_001', '广州', '440100', '广东省'),
('ESP32_002', '深圳', '440300', '广东省'),
('ESP32_003', '北京', '110100', '北京市');
```

---

## 🔧 Java后端实现建议

### Spring Boot Controller示例

```java
@RestController
@RequestMapping("/api/weather")
@Slf4j
public class WeatherController {
    
    @Autowired
    private DeviceLocationService deviceLocationService;
    
    @Autowired
    private WeatherService weatherService;
    
    @Value("${api.secret}")
    private String apiSecret;
    
    @GetMapping("/device/{deviceId}")
    public ResponseEntity<?> getWeatherByDevice(
        @PathVariable String deviceId,
        @RequestHeader("Authorization") String authorization
    ) {
        try {
            // 1. 认证验证
            if (!isValidAuthorization(authorization)) {
                log.warn("无效的API认证: deviceId={}", deviceId);
                return ResponseEntity.status(401).body(Map.of(
                    "error", "认证失败",
                    "code", "UNAUTHORIZED"
                ));
            }
            
            // 2. 查找设备绑定的城市
            DeviceLocation location = deviceLocationService.getByDeviceId(deviceId);
            if (location == null) {
                log.warn("设备未找到或未绑定城市: deviceId={}", deviceId);
                return ResponseEntity.status(404).body(Map.of(
                    "error", "设备未找到或未绑定城市",
                    "code", "DEVICE_NOT_FOUND",
                    "deviceId", deviceId
                ));
            }
            
            // 3. 获取天气数据
            WeatherInfo weather = weatherService.getWeatherByCityCode(location.getCityCode());
            if (weather == null) {
                log.error("获取天气数据失败: cityCode={}", location.getCityCode());
                return ResponseEntity.status(500).body(Map.of(
                    "error", "获取天气信息失败",
                    "code", "WEATHER_API_ERROR"
                ));
            }
            
            // 4. 构建响应
            Map<String, Object> response = buildWeatherResponse(weather, location);
            
            log.info("天气查询成功: deviceId={}, city={}", deviceId, location.getCityName());
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            log.error("天气API异常: deviceId={}, error={}", deviceId, e.getMessage(), e);
            return ResponseEntity.status(500).body(Map.of(
                "error", "服务内部错误",
                "code", "INTERNAL_ERROR"
            ));
        }
    }
    
    private boolean isValidAuthorization(String authorization) {
        if (authorization == null || !authorization.startsWith("Bearer ")) {
            return false;
        }
        String token = authorization.substring(7);
        return apiSecret.equals(token);
    }
    
    private Map<String, Object> buildWeatherResponse(WeatherInfo weather, DeviceLocation location) {
        return Map.of(
            "city", location.getCityName(),
            "temperature", String.valueOf(weather.getTemperature()),
            "weather", weather.getWeatherDesc(),
            "high", String.valueOf(weather.getHighTemp()),
            "low", String.valueOf(weather.getLowTemp()),
            "wind", weather.getWindDesc(),
            "humidity", weather.getHumidity() + "%",
            "suggestion", generateElderlyAdvice(weather),
            "updateTime", weather.getUpdateTime().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"))
        );
    }
    
    private String generateElderlyAdvice(WeatherInfo weather) {
        // 根据天气情况生成老年人专用建议
        StringBuilder advice = new StringBuilder();
        
        if (weather.getTemperature() > 30) {
            advice.append("天气较热，建议减少外出，多补充水分。");
        } else if (weather.getTemperature() < 10) {
            advice.append("天气较冷，外出请注意保暖。");
        } else {
            advice.append("天气宜人，适合外出活动。");
        }
        
        if (weather.getWeatherDesc().contains("雨")) {
            advice.append("有降雨，外出请携带雨具，注意路滑。");
        }
        
        return advice.toString();
    }
}
```

### 服务层实现建议

```java
@Service
@Slf4j
public class WeatherService {
    
    @Value("${weather.api.key}")
    private String weatherApiKey;
    
    @Value("${weather.api.url}")
    private String weatherApiUrl;
    
    @Autowired
    private RestTemplate restTemplate;
    
    public WeatherInfo getWeatherByCityCode(String cityCode) {
        try {
            // 调用第三方天气API（如和风天气、心知天气等）
            String url = String.format("%s/weather/now?location=%s&key=%s", 
                weatherApiUrl, cityCode, weatherApiKey);
            
            // 发送HTTP请求
            WeatherApiResponse response = restTemplate.getForObject(url, WeatherApiResponse.class);
            
            if (response != null && response.isSuccess()) {
                return convertToWeatherInfo(response);
            }
            
            log.error("第三方天气API调用失败: cityCode={}", cityCode);
            return null;
            
        } catch (Exception e) {
            log.error("天气API调用异常: cityCode={}, error={}", cityCode, e.getMessage(), e);
            return null;
        }
    }
    
    private WeatherInfo convertToWeatherInfo(WeatherApiResponse response) {
        // 转换第三方API响应为内部WeatherInfo对象
        WeatherInfo info = new WeatherInfo();
        info.setTemperature(response.getNow().getTemp());
        info.setWeatherDesc(response.getNow().getText());
        // ... 其他字段转换
        return info;
    }
}
```

---

## ⚙️ 配置要求

### application.yml配置
```yaml
# 天气API配置
weather:
  api:
    key: your-weather-api-key
    url: https://devapi.qweather.com/v7  # 和风天气API示例
    timeout: 5000

# API安全配置
api:
  secret: your-api-secret-key  # 与Python端配置保持一致
```

### Python端配置 (config.yaml)
```yaml
# Java后端API配置
manager-api:
  url: "http://your-java-server:8080"  # Java后端地址
  secret: "your-api-secret-key"        # 与Java端保持一致
  timeout: 30
  max_retries: 3
  retry_delay: 5
```

---

## 🧪 测试方案

### 1. API接口测试

```bash
# 正常请求测试
curl -H "Authorization: Bearer your-api-secret-key" \
     -H "Content-Type: application/json" \
     "http://your-java-server:8080/api/weather/device/ESP32_001"

# 预期响应
{
  "city": "广州",
  "temperature": "28",
  "weather": "晴",
  "high": "32",
  "low": "24",
  "wind": "东南风2级",
  "humidity": "65%",
  "suggestion": "天气晴朗，适合外出活动。建议老年人上午或傍晚时段外出散步。",
  "updateTime": "2025-08-14 14:30:00"
}
```

### 2. 错误场景测试

```bash
# 设备不存在
curl -H "Authorization: Bearer your-api-secret-key" \
     "http://your-java-server:8080/api/weather/device/NOT_EXIST"

# 认证失败
curl -H "Authorization: Bearer invalid-token" \
     "http://your-java-server:8080/api/weather/device/ESP32_001"
```

### 3. Python端集成测试

```python
# 测试天气类问候
import requests

response = requests.post('http://localhost:8003/xiaozhi/greeting/send', 
    json={
        "device_id": "ESP32_001",
        "initial_content": "今天天气不错",
        "category": "weather",
        "user_info": {
            "name": "李叔",
            "age": 65,
            "location": "广州"
        }
    }
)
print(response.json())
```

---

## 📋 开发清单

### Java后端需要实现
- [ ] **WeatherController** - 天气API控制器
- [ ] **DeviceLocationService** - 设备位置管理服务
- [ ] **WeatherService** - 第三方天气API集成
- [ ] **设备-城市绑定数据表** - 数据库表创建
- [ ] **API认证机制** - Bearer Token验证
- [ ] **老年人专用建议生成** - 针对老年用户的天气建议

### 可选增强功能
- [ ] **天气预警推送** - 恶劣天气主动推送
- [ ] **设备位置管理接口** - 支持动态绑定城市
- [ ] **天气数据缓存** - 避免频繁调用第三方API
- [ ] **多天气源支持** - 提高数据可靠性

---

## 🚀 集成后效果

### 天气问候示例
```
问候前: "李叔，下午好！"
集成后: "李叔，下午好！广州今天晴天，当前温度28℃，最高32℃。天气晴朗，适合外出活动。建议您上午或傍晚时段外出散步。"
```

### 用户价值
- **🌤️ 实时天气**: 准确的本地天气信息
- **👴 老年友好**: 专门的老年人天气建议
- **🔔 贴心提醒**: 根据天气情况的生活建议
- **📱 智能集成**: 无缝融入主动问候流程

---

## ⏰ 开发时间线建议

| 阶段 | 工作内容 | 预计时间 | 优先级 |
|------|----------|----------|--------|
| 第1周 | 数据库设计、基础API实现 | 2-3天 | 🔴 高 |
| 第2周 | 第三方天气API集成、测试 | 2-3天 | 🔴 高 |
| 第3周 | 老年人建议优化、错误处理 | 1-2天 | 🟡 中 |
| 第4周 | 增强功能、性能优化 | 1-2天 | 🟢 低 |

---

**🎯 Java后端天气接口是ESP32主动问候功能的重要组成部分，Python端已完全准备就绪，等待Java后端实现即可完成天气功能的完整集成！** 🌤️

---

**文档创建时间**: 2025年8月14日  
**负责人**: Python团队  
**状态**: 等待Java后端实现  
**联系方式**: [技术对接群]

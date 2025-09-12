# Java后端天气API集成说明

## 📋 集成背景

根据Java后端工程师的建议，我们已经为主动问候功能集成了天气查询API。Java后端负责提供天气数据，Python端负责调用API并生成智能问候内容。

## 🔧 Python端已完成的修改

### 1. 新增天气工具模块

**文件：** `core/tools/weather_tool.py`

**功能：**
- 调用Java后端天气API
- 格式化天气数据
- 支持LLM Function Calling
- 提供备用方案（API不可用时）

**主要特性：**
```python
class WeatherTool:
    async def get_weather_by_device(self, device_id: str) -> Dict[str, Any]
    def format_weather_for_greeting(self, weather_data: Dict[str, Any]) -> str
```

### 2. 升级主动问候服务

**文件：** `core/mqtt/proactive_greeting_service.py`

**新增功能：**
- 集成天气工具
- 支持Function Calling
- 天气类问候自动调用天气API
- 增强的内容生成逻辑

**核心改进：**
```python
# 自动获取天气信息
if category == "weather" and device_id:
    weather_info = await self.weather_tool.get_weather_by_device(device_id)
    weather_text = self.weather_tool.format_weather_for_greeting(weather_info)
    enhanced_content = f"{initial_content}。{weather_text}"
```

## 🌐 Java后端需要提供的API

### API接口规范

**接口地址：** `GET /api/weather/device/{device_id}`

**请求头：**
```http
Authorization: Bearer {api_secret}
Content-Type: application/json
```

**成功响应格式：**
```json
{
  "city": "广州",
  "temperature": "28",
  "weather": "晴",
  "high": "32", 
  "low": "24",
  "wind": "东南风2级",
  "humidity": "65%",
  "suggestion": "天气晴朗，适合外出活动",
  "updateTime": "2024-12-01 14:00:00"
}
```

**错误响应格式：**
```json
{
  "error": "设备未找到或未绑定城市",
  "code": "DEVICE_NOT_FOUND"
}
```

### Java后端实现建议

```java
@RestController
@RequestMapping("/api/weather")
public class WeatherController {
    
    @GetMapping("/device/{deviceId}")
    public ResponseEntity<?> getWeatherByDevice(
        @PathVariable String deviceId,
        @RequestHeader("Authorization") String authorization
    ) {
        try {
            // 1. 验证授权
            if (!isValidAuthorization(authorization)) {
                return ResponseEntity.status(401).body(Map.of("error", "Unauthorized"));
            }
            
            // 2. 根据device_id查找绑定的城市
            String city = deviceService.getCityByDeviceId(deviceId);
            if (city == null) {
                return ResponseEntity.status(404).body(Map.of(
                    "error", "设备未找到或未绑定城市",
                    "code", "DEVICE_NOT_FOUND"
                ));
            }
            
            // 3. 调用天气API获取数据
            WeatherInfo weatherInfo = weatherService.getWeatherByCity(city);
            
            // 4. 格式化返回数据
            Map<String, Object> response = Map.of(
                "city", weatherInfo.getCity(),
                "temperature", weatherInfo.getTemperature(),
                "weather", weatherInfo.getWeather(),
                "high", weatherInfo.getHigh(),
                "low", weatherInfo.getLow(),
                "wind", weatherInfo.getWind(),
                "humidity", weatherInfo.getHumidity(),
                "suggestion", weatherInfo.getSuggestion(),
                "updateTime", weatherInfo.getUpdateTime()
            );
            
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            return ResponseEntity.status(500).body(Map.of(
                "error", "获取天气信息失败",
                "code", "INTERNAL_ERROR"
            ));
        }
    }
}
```

## ⚙️ Python配置修改

在 `config.yaml` 中确保以下配置正确：

```yaml
# Java后端API配置（已存在，确认配置正确）
manager-api:
  url: "http://your-java-server:8080"  # Java后端地址
  secret: "your-api-secret"            # API密钥
  timeout: 30
  max_retries: 3
  retry_delay: 5

# 确保MQTT和主动问候功能已启用
mqtt:
  enabled: true
  host: 47.98.51.180

proactive_greeting:
  enabled: true
```

## 🧪 测试方案

### 1. Java后端API测试

```bash
# 测试天气API
curl -H "Authorization: Bearer your-api-secret" \
     -H "Content-Type: application/json" \
     "http://your-java-server:8080/api/weather/device/ESP32_001"
```

### 2. Python端集成测试

```python
# 测试天气类问候
curl -X POST http://localhost:8003/xiaozhi/greeting/send \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "initial_content": "今天天气不错",
    "category": "weather",
    "user_info": {
      "name": "李叔",
      "age": 65
    }
  }'
```

### 3. 完整流程测试

```python
# 运行示例程序，测试天气问候
python proactive_greeting_example.py
```

## 🔄 消息流程

```
1. Java后端收到天气问候请求
2. Python调用 /api/weather/device/{device_id}
3. Java后端根据device_id查找绑定城市
4. Java后端调用天气API获取实时数据
5. Java后端返回格式化的天气信息
6. Python端合并天气信息和用户内容
7. LLM生成个性化天气问候
8. 通过MQTT发送到ESP32设备
```

## 📊 数据流示例

**原始请求：**
```json
{
  "device_id": "ESP32_001",
  "initial_content": "今天天气不错",
  "category": "weather"
}
```

**Java API返回：**
```json
{
  "city": "广州",
  "temperature": "28",
  "weather": "晴",
  "high": "32",
  "low": "24",
  "suggestion": "天气晴朗，适合外出活动"
}
```

**Python增强后的内容：**
```
今天天气不错。广州今天晴，当前温度28℃，最高32℃，最低24℃。天气晴朗，适合外出活动
```

**LLM生成的最终问候：**
```
李叔，广州今天天气晴朗，气温28℃，最高32℃，很适合出门散步晒太阳呢！
```

## ⚠️ 注意事项

### Java后端注意点：
1. **API安全性：** 确保验证Authorization头
2. **错误处理：** 提供清晰的错误信息
3. **性能优化：** 考虑天气数据缓存
4. **数据格式：** 严格按照约定的JSON格式返回

### Python端注意点：
1. **容错处理：** Java API不可用时有备用方案
2. **超时设置：** 避免长时间等待Java API响应
3. **日志记录：** 记录API调用状态用于调试
4. **数据验证：** 验证Java API返回的数据格式

## 🔧 故障排查

### 常见问题

**Q1: 天气信息获取失败**
```bash
# 检查Java API是否可访问
curl -I http://your-java-server:8080/api/weather/device/test

# 查看Python日志
tail -f tmp/server.log | grep -i weather
```

**Q2: Authorization失败**
```bash
# 检查config.yaml中的API配置
grep -A 5 "manager-api:" config.yaml
```

**Q3: 设备未绑定城市**
- 确保Java后端有device_id到城市的映射关系
- 检查设备注册和城市绑定流程

## 📈 性能优化建议

### Java后端优化：
1. **缓存机制：** 同一城市的天气数据缓存5-10分钟
2. **限流控制：** 避免天气API调用过于频繁
3. **异步处理：** 考虑异步获取天气数据

### Python端优化：
1. **连接池：** 复用HTTP连接
2. **并发控制：** 限制同时进行的天气API调用
3. **数据缓存：** 本地缓存最近的天气数据

---

**文档创建时间：** 2024年12月1日  
**适用版本：** ESP32主动问候功能 v1.0.0  
**依赖关系：** 需要Java后端配合实现

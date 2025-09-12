# ESP32主动问候功能快速入门

## 5分钟快速体验

### 第一步：确认环境

确保以下服务正常运行：

```bash
# 检查xiaozhi服务器状态
curl http://localhost:8003/xiaozhi/greeting/status?device_id=test

# 检查MQTT服务器连接
mosquitto_pub -h 47.97.185.142 -p 1883 -t "test/topic" -m "hello"
```

### 第二步：配置启用

在 `config.yaml` 中确认以下配置已启用：

```yaml
# MQTT配置
mqtt:
  enabled: true  # 启用MQTT功能
  host: 47.97.185.142
  port: 1883

# 主动问候配置  
proactive_greeting:
  enabled: true  # 启用主动问候功能
```

### 第三步：重启服务

```bash
# 重启xiaozhi服务器
python app.py
```

启动成功后应该看到：
```
MQTT主动问候功能已启用
MQTT连接成功
```

### 第四步：发送第一条问候

使用curl命令测试：

```bash
curl -X POST http://localhost:8003/xiaozhi/greeting/send \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "initial_content": "Hello，这是测试消息",
    "category": "system_reminder",
    "user_info": {
      "name": "测试用户",
      "age": 30
    }
  }'
```

成功响应：
```json
{
  "success": true,
  "message": "主动问候发送成功", 
  "track_id": "WX20241201123456ABC123",
  "device_id": "ESP32_001",
  "timestamp": 1701234567.89
}
```

### 第五步：查询状态

```bash
curl "http://localhost:8003/xiaozhi/greeting/status?device_id=ESP32_001"
```

### 第六步：运行完整示例

```bash
cd xiaozhi-esp32-server-main/main/xiaozhi-server
python proactive_greeting_example.py
```

---

## ESP32设备端配置

### 1. 订阅主题

设备需要订阅以下MQTT主题：
```
device/{device_id}/cmd  # 接收命令
```

### 2. 发布主题

设备需要发布到以下MQTT主题：
```
device/{device_id}/ack    # 确认接收
device/{device_id}/event  # 状态事件
```

### 3. 消息格式

**接收命令格式：**
```json
{
  "cmd": "SPEAK",
  "text": "问候内容",
  "track_id": "WX20241201123456ABC123"
}
```

**回复ACK格式：**
```json
{
  "track_id": "WX20241201123456ABC123",
  "status": "received",
  "timestamp": "12:34:56"
}
```

**完成事件格式：**
```json
{
  "evt": "EVT_SPEAK_DONE",
  "track_id": "WX20241201123456ABC123", 
  "timestamp": "12:35:02"
}
```

---

## Java后端集成

### 1. 发送问候接口

```java
@PostMapping("/send-greeting")
public ResponseEntity<?> sendGreeting(@RequestBody GreetingRequest request) {
    RestTemplate restTemplate = new RestTemplate();
    String url = "http://python-service:8003/xiaozhi/greeting/send";
    
    Map<String, Object> payload = Map.of(
        "device_id", request.getDeviceId(),
        "initial_content", request.getContent(),
        "category", request.getCategory(),
        "user_info", request.getUserInfo()
    );
    
    return restTemplate.postForEntity(url, payload, Map.class);
}
```

### 2. 状态查询接口

```java
@GetMapping("/greeting-status/{deviceId}")
public ResponseEntity<?> getGreetingStatus(@PathVariable String deviceId) {
    RestTemplate restTemplate = new RestTemplate();
    String url = "http://python-service:8003/xiaozhi/greeting/status?device_id=" + deviceId;
    
    return restTemplate.getForEntity(url, Map.class);
}
```

---

## 常见问题解决

### Q: MQTT连接失败
**A:** 检查网络连接和EMQX服务器状态
```bash
telnet 47.97.185.142 1883
```

### Q: 设备收不到消息
**A:** 检查设备ID和MQTT主题订阅
```bash
mosquitto_sub -h 47.97.185.142 -p 1883 -t "device/+/cmd"
```

### Q: LLM生成失败
**A:** 检查LLM配置和API密钥
```bash
# 查看日志
tail -f tmp/server.log | grep LLM
```

### Q: TTS合成失败
**A:** 检查TTS配置和网络连接
```bash
# 查看日志
tail -f tmp/server.log | grep TTS
```

---

## 下一步

1. 📖 阅读完整文档：[功能使用指南](./proactive_greeting_guide.md)
2. 📋 查看API参考：[API参考文档](./api_reference.md)
3. 🔧 运行示例代码：`python proactive_greeting_example.py`
4. 🚀 开发你的应用：参考示例代码进行开发

---

## 获得帮助

- 📚 查看完整文档
- 🐛 提交Issue到GitHub
- 💬 联系技术支持团队

# ESP32 AI设备主动问候功能文档

## 📚 文档目录

### 🚀 快速开始
- **[快速入门指南](./quickstart.md)** - 5分钟快速体验主动问候功能
- **[功能使用指南](./proactive_greeting_guide.md)** - 完整的功能介绍和使用说明

### 📖 API文档  
- **[API参考文档](./api_reference.md)** - 详细的API接口说明和示例

### 💻 代码示例
- **[Python示例](../proactive_greeting_example.py)** - 完整的Python客户端示例
- **[配置示例](../config.yaml)** - 配置文件示例

### 🔧 开发文档
- **[开发变更日志](./development_changelog.md)** - 详细的文件变更记录和开发说明

- **天气文档**
  - **[Java天气API集成](./weather/java_weather_integration.md)**
  - **[天气API更新总结](./weather/weather_api_update.md)**
  - **[Java天气接口快速实现](./weather/java_weather_quickstart.md)**
  - **[Java后端天气接口需求](./weather/java_backend_requirements.md)**
  - **[第三方天气API集成指南](./weather/third_party_weather_integration.md)** ⭐

- **新闻文档**
  - **[Java新闻API接口规范](./news/java_news_api_spec.md)**
  - **[Java新闻接口快速实现](./news/java_news_quickstart.md)**
  - **[新闻功能集成指南](./news/news_integration_guide.md)**
  - **[第三方新闻API集成指南](./news/third_party_news_integration.md)** ⭐

- **音乐文档**
  - **[Java音乐API接口规范](./music/java_music_api_spec.md)**
  - **[Java音乐接口快速实现](./music/java_music_quickstart.md)**
  - **[音乐功能集成指南](./music/music_integration_guide.md)**

- **Memobase 文档**
  - **[Memobase记忆数据库集成](./memobase_integration.md)**
  - **[Memobase集成状态报告](./memobase_status_report.md)**

---

## 🎯 功能概述

ESP32 AI设备主动问候功能是一个完整的智能问候系统，主要特性包括：

### ✨ 核心功能
- 🧠 **智能内容生成** - 基于LLM、用户信息和记忆生成个性化问候
- 📡 **MQTT通信** - 可靠的设备消息传输机制
- 🔊 **语音合成** - TTS语音合成和音频下发
- 📊 **状态追踪** - 完整的消息状态管理
- 🔗 **后端集成** - 支持Java后端API调用

### 🏗️ 系统架构
```
Java后端 → HTTP API → Python服务 → MQTT → ESP32设备
                ↓
           LLM生成问候内容
                ↓  
           TTS语音合成
                ↓
           音频下发到设备
```

### 📋 支持的问候类别
- `system_reminder` - 系统提醒（服药、健康提醒等）
- `schedule` - 日程安排（预约、重要事项等）
- `weather` - 天气信息（天气播报、出行建议等）
- `entertainment` - 娱乐内容（音乐、节目推荐等）
- `music` - 音乐播放（智能推荐、个性化播放等）⭐
- `news` - 新闻资讯（新闻播报、资讯分享等）

---

## 🚀 快速开始

### 1. 环境要求
- Python 3.8+
- 已部署的EMQX MQTT服务器 (47.98.51.180)
- ESP32设备在线并支持MQTT

### 2. 安装依赖
```bash
pip install paho-mqtt==2.1.0
```

### 3. 配置启用
在 `config.yaml` 中启用MQTT功能：
```yaml
mqtt:
  enabled: true
  host: 47.98.51.180

proactive_greeting:
  enabled: true
```

### 4. 启动服务
```bash
python app.py
```

### 5. 测试功能
```bash
# 发送问候
curl -X POST http://localhost:8003/xiaozhi/greeting/send \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "initial_content": "Hello，测试消息",
    "category": "system_reminder"
  }'

# 查询状态  
curl "http://localhost:8003/xiaozhi/greeting/status?device_id=ESP32_001"
```

### 6. 运行示例
```bash
python proactive_greeting_example.py
```

---

## 📋 API 接口

### 发送主动问候
```http
POST /xiaozhi/greeting/send
```

### 查询设备状态  
```http
GET /xiaozhi/greeting/status?device_id={device_id}
```

### 用户档案管理
```http
POST /xiaozhi/user/profile
GET /xiaozhi/user/profile?device_id={device_id}
```

详细接口说明请参考 [API参考文档](./api_reference.md)

---

## 🔧 配置说明

### MQTT配置
```yaml
mqtt:
  host: 47.98.51.180      # MQTT服务器地址
  port: 1883              # MQTT端口  
  username: ""            # 用户名（可选）
  password: ""            # 密码（可选）
  enabled: true           # 启用MQTT功能
```

### 主动问候配置
```yaml
proactive_greeting:
  enabled: true           # 启用主动问候
  content_generation:
    max_length: 100       # 最大字符数
    use_memory: true      # 使用记忆信息
    use_user_info: true   # 使用用户信息
```

完整配置说明请参考 [功能使用指南](./proactive_greeting_guide.md)

---

## 📱 ESP32设备集成

### MQTT主题订阅
```cpp
// 订阅命令主题
client.subscribe("device/ESP32_001/cmd");
```

### 消息处理示例
```cpp
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
    // 解析JSON命令
    DynamicJsonDocument doc(1024);
    deserializeJson(doc, payload);
    
    String cmd = doc["cmd"];
    String text = doc["text"];
    String trackId = doc["track_id"];
    
    if (cmd == "SPEAK") {
        // 发送ACK确认
        sendAck(trackId);
        
        // 播放语音
        playText(text);
        
        // 发送完成事件
        sendSpeakDone(trackId);
    }
}
```

详细设备端代码请参考 [功能使用指南](./proactive_greeting_guide.md)

---

## 🔗 Java后端集成

### Spring Boot示例
```java
@RestController
@RequestMapping("/api/greeting")
public class GreetingController {
    
    @PostMapping("/send")
    public ResponseEntity<?> sendGreeting(@RequestBody GreetingRequest request) {
        // 调用Python服务API
        String url = "http://python-service:8003/xiaozhi/greeting/send";
        return restTemplate.postForEntity(url, request, Map.class);
    }
}
```

详细集成代码请参考 [功能使用指南](./proactive_greeting_guide.md)

---

## 🧪 测试和示例

### 运行完整示例
```bash
python proactive_greeting_example.py
```

示例包含：
- ✅ 基础问候发送
- ✅ 不同类别问候
- ✅ 用户档案管理  
- ✅ 错误处理演示
- ✅ 批量操作示例
- ✅ 状态监控示例
- ✅ 真实场景演示

### 使用MQTT工具测试
```bash
# 监听所有设备消息
mosquitto_sub -h 47.98.51.180 -t "device/+/+"

# 手动发送测试命令
mosquitto_pub -h 47.98.51.180 -t "device/ESP32_001/cmd" \
  -m '{"cmd":"SPEAK","text":"测试消息","track_id":"TEST123"}'
```

---

## 🐛 故障排除

### 常见问题

#### MQTT连接失败
```bash
# 检查网络连接
ping 47.98.51.180

# 检查端口可达性
telnet 47.98.51.180 1883
```

#### 设备收不到消息
```bash
# 检查MQTT订阅
mosquitto_sub -h 47.98.51.180 -t "device/ESP32_001/cmd"
```

#### 语音合成失败
```bash
# 查看TTS日志
tail -f tmp/server.log | grep TTS
```

详细故障排除指南请参考 [功能使用指南](./proactive_greeting_guide.md)

---

## 📊 监控和日志

### 查看服务状态
```bash
# 服务器日志
tail -f tmp/server.log

# MQTT连接状态
curl "http://localhost:8003/xiaozhi/greeting/status?device_id=test"
```

### 性能监控
- 消息发送成功率
- 设备响应时间
- 语音合成耗时
- LLM生成耗时

---

## 🚧 开发计划

### 已完成功能 ✅
- [x] MQTT通信机制
- [x] 智能内容生成
- [x] TTS语音合成
- [x] 设备状态管理
- [x] Java后端集成
- [x] API接口实现

### 规划中功能 🔄
- [ ] 消息队列优化
- [ ] 设备群组管理
- [ ] 定时任务支持
- [ ] 消息模板管理
- [ ] 数据统计分析

---

## 📞 技术支持

### 获得帮助
- 📖 查看完整文档
- 🐛 提交Issue
- 💬 联系技术团队

### 文档反馈
如果发现文档问题或有改进建议，请：
1. 提交Issue描述问题
2. 提供具体的改进建议
3. 贡献代码和文档

---

## 📄 许可证

本项目遵循项目根目录的LICENSE文件规定。

---

## 🙏 致谢

感谢所有为ESP32 AI设备主动问候功能开发做出贡献的开发者和测试人员。

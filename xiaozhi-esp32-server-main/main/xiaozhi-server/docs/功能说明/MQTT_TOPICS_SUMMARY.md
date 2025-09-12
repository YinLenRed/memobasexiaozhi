# 🔍 MQTT主题完整列表

## 📤 **发布主题 (Python → 硬件/外部)**

### **1. 设备命令主题**
```
device/{device_id}/cmd
```
- **用途**: 发送语音播放命令给硬件
- **消息内容**: SPEAK命令，包含track_id和文本
- **发送方法**: `send_speak_command()`
- **配置位置**: `config.yaml` → `mqtt.topics.command`

### **2. 设备唤醒主题**
```
device/{device_id}/awaken
```
- **用途**: 发送设备唤醒命令
- **消息内容**: 唤醒消息和类型
- **发送方法**: `send_awaken_command()`

### **3. 天气发布主题**
```
weather/global                    # 全局天气
weather/device/{device_id}        # 设备专用天气
weather/city/{city_name}          # 城市天气
weather/alert                     # 天气预警
```
- **用途**: 定期发布天气信息
- **发布服务**: `MQTTWeatherPublisher`
- **发布频率**: 30分钟（可配置）

### **4. 通用消息主题**
```
{任意主题}
```
- **用途**: 通过 `send_message_to_topic()` 发送任意消息
- **发送方法**: `send_message_to_topic(topic, message)`

---

## 📥 **订阅主题 (硬件/外部 → Python)**

### **1. 设备确认主题**
```
device/+/ack
```
- **用途**: 接收硬件设备的ACK确认消息
- **消息内容**: 命令执行确认，包含track_id
- **处理**: 触发音频发送流程

### **2. 设备事件主题**
```
device/+/event
```
- **用途**: 接收硬件设备的事件消息
- **消息内容**: EVT_SPEAK_DONE等事件
- **处理**: 更新设备状态

### **3. Java后端设备状态主题**
```
xiaozhi/java-to-python/device-status/+
```
- **用途**: 接收Java后端推送的设备状态信息
- **消息内容**: 设备在线状态、天气信息等

---

## 🔧 **主题配置**

### **配置文件位置**: `config.yaml`
```yaml
mqtt:
  host: 47.97.185.142
  port: 1883
  username: admin
  password: Jyxd@2025
  client_id: xiaozhi-prod-yinlenred-1755671623-faa6f1af
  enabled: true
  topics:
    ack: device/{device_id}/ack           # 设备确认主题
    command: device/{device_id}/cmd       # 设备命令主题
    event: device/{device_id}/event       # 设备事件主题
```

### **天气发布配置**:
```yaml
weather_publisher:
  enabled: true
  publish_interval: 30  # 分钟
  devices: ["ESP32_001", "ESP32_002"]
  cities: ["广州", "北京", "上海"]
  topics:
    global_weather: "weather/global"
    device_weather: "weather/device/{device_id}"
    city_weather: "weather/city/{city_name}"
    weather_alert: "weather/alert"
```

---

## 📊 **消息流向图**

```
Java后端 ──MQTT──→ Python后端 ──WebSocket──→ 硬件
    ↓                   ↓                     ↓
设备状态推送         处理业务逻辑          播放音频
    ↑                   ↑                     ↑
    └─────MQTT ACK──────┴──────MQTT───────────┘
```

### **主要流程**:
1. **主动问候**: Java → `HTTP API` → Python → `device/{id}/cmd` → 硬件
2. **设备确认**: 硬件 → `device/{id}/ack` → Python → `WebSocket音频`
3. **播放完成**: 硬件 → `device/{id}/event` → Python
4. **状态同步**: Java → `xiaozhi/java-to-python/device-status/{id}` → Python

---

## ⚠️ **已知问题**

### **主题不匹配问题** (已修复)
- **问题**: 硬件订阅 `/cmd`，但API发送 `/command`
- **解决**: 配置统一使用 `/cmd` 主题
- **参考**: `MQTT_TOPIC_FIX_GUIDE.md`

### **连接地址不一致**
- **MQTT**: `47.97.185.142:1883`
- **WebSocket**: `ws://172.20.12.204:8000` (应统一为47.97.185.142)

---

## 🛠️ **测试工具**

1. **`simple_hardware_test.py`** - 模拟硬件MQTT交互
2. **`complete_hardware_simulation.py`** - 完整硬件模拟
3. **`quick_speak_test.py`** - 快速语音测试

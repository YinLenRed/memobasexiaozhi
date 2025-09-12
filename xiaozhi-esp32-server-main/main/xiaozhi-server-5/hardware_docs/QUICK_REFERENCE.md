# 🚀 小智主动问候 - 硬件快速参考卡

## ⚡ 核心配置 (必须记住)

```
MQTT服务器: 47.97.185.142:1883
WebSocket: ws://172.20.12.204:8000/xiaozhi/v1/
设备ID格式: MAC地址 (如: 00:0c:29:fc:b7:b9)
```

## 📡 关键MQTT主题

| 用途 | 主题格式 | 说明 |
|------|----------|------|
| **订阅** | `device/{device-id}/cmd` | 接收Python命令 |
| **发布** | `device/{device-id}/ack` | 回复命令确认 |
| **发布** | `device/{device-id}/event` | 上报播放完成 |

## 📨 消息格式速查

### 📥 接收命令
```json
{"cmd":"SPEAK","text":"问候内容","track_id":"WX20240809"}
```

### 📤 回复确认  
```json
{"evt":"CMD_RECEIVED","track_id":"WX20240809","timestamp":"09:30:02"}
```

### 📤 播放完成
```json
{"evt":"EVT_SPEAK_DONE","track_id":"WX20240809","timestamp":"09:30:12"}
```

## 🔗 WebSocket连接
```
ws://172.20.12.204:8000/xiaozhi/v1/?device-id=你的MAC&client-id=esp32-随机数
```

## 🧪 快速测试

```bash
# 订阅命令 (用于观察)
mosquitto_sub -h 47.97.185.142 -p 1883 -t "device/+/cmd"

# 模拟ACK回复
mosquitto_pub -h 47.97.185.142 -p 1883 -t "device/你的MAC/ack" \
  -m '{"evt":"CMD_RECEIVED","track_id":"TEST","timestamp":"10:30:00"}'
```

## ✅ 测试成功标志
- MQTT连接成功 ✅
- 能收到SPEAK命令 ✅  
- ACK回复成功 ✅
- WebSocket连接正常 ✅
- 事件上报成功 ✅

---
**详细文档**: [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)

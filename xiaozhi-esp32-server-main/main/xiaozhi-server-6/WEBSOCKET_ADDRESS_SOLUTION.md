# 🌐 WebSocket地址配置解决方案

## ✅ 正确的地址配置

您之前提到的是正确的！应该使用**公网地址**：

| 服务类型 | 正确地址 | 说明 |
|---------|-----------|------|
| **WebSocket音频** | `ws://47.98.51.180:8000/xiaozhi/v1/` | 🎯 **硬件应使用此地址** |
| MQTT通信 | `47.97.185.142:1883` | 设备命令/事件通信 |
| HTTP API | `http://47.98.51.180:8003` | Java后端调用接口 |

---

## 🔧 问题分析

### 之前的问题
测试脚本 `test_python_hardware_flow.py` 使用了**内网地址**：
```
❌ 错误: ws://172.20.12.204:8888/xiaozhi/v1/
```

### 正确配置
硬件应该连接**公网地址**：
```
✅ 正确: ws://47.98.51.180:8000/xiaozhi/v1/
```

---

## 🎯 解决方案

### 1. 硬件端配置
```cpp
// ESP32正确配置
#define WEBSOCKET_SERVER "47.98.51.180"
#define WEBSOCKET_PORT 8000
#define WEBSOCKET_PATH "/xiaozhi/v1/"

// 完整WebSocket URL
String audioUrl = "ws://47.98.51.180:8000/xiaozhi/v1/";
```

### 2. 测试验证
```bash
# 测试生产环境WebSocket连接
python test_websocket_only.py 7c:2c:67:8d:89:78 production

# 测试连接诊断
python diagnose_production.py
```

### 3. 完整流程测试
```bash
# 生产环境测试
python flexible_test.py 7c:2c:67:8d:89:78 production
```

---

## 📋 验证步骤

### ✅ 1. 确认生产服务器状态
从您的诊断结果看，生产服务器**完全正常**：
```
✅ TCP连接              : 通过
✅ HTTP健康检查           : 通过  
✅ WebSocket连接        : 通过
✅ 小智服务状态             : 通过
```

### ✅ 2. 硬件配置检查
确保ESP32代码中使用：
```cpp
webSocket.begin("47.98.51.180", 8000, "/xiaozhi/v1/");
```

### ✅ 3. 音频URL解析
SPEAK命令中的 `audio_url` 字段应该是：
```json
{
  "audio_url": "ws://47.98.51.180:8000/xiaozhi/v1/"
}
```

---

## 🚀 下一步行动

1. **硬件团队**：
   - 修改ESP32代码，使用公网地址 `47.98.51.180:8000`
   - 实现WebSocket音频接收功能（参考 `HARDWARE_WEBSOCKET_AUDIO_GUIDE.md`）

2. **测试验证**：
   ```bash
   # 测试WebSocket连接
   python test_websocket_only.py 7c:2c:67:8d:89:78 production
   
   # 完整流程测试
   python flexible_test.py 7c:2c:67:8d:89:78 production
   ```

3. **预期结果**：
   - WebSocket连接成功 ✅
   - 音频数据接收正常 ✅
   - 播放完成事件上报 ✅

---

## 💡 关键要点

- **生产服务器已就绪**：`ws://47.98.51.180:8000/xiaozhi/v1/` 完全可用
- **硬件需要实现**：WebSocket音频客户端功能
- **地址统一使用**：公网地址 `47.98.51.180`

**🎯 一旦硬件实现WebSocket音频客户端，整个主动问候系统就能完美工作！**

# 🔧 硬件WebSocket音频实现指南

## 🎯 **问题诊断结果**

经过完整的系统测试，确认问题所在：

### ✅ **正常工作的组件**
- ✅ Java API → Python服务通信
- ✅ Python TTS音频生成
- ✅ Python MQTT SPEAK命令发送
- ✅ 硬件MQTT客户端（接收命令 + 发送ACK）

### ❌ **问题组件**
- ❌ **硬件WebSocket客户端缺失或有问题**

## 📊 **测试数据证明**

```bash
# MQTT测试 - 成功
[15:23:12] ✅ SPEAK命令发送成功
[15:23:12] ✅ 硬件ACK响应: 72.2ms

# WebSocket测试 - 失败
[15:25:26] ❌ WebSocket服务器: 只有健康检查连接
[15:25:26] ❌ 没有硬件IP的WebSocket连接尝试
```

## 🔧 **硬件需要实现的WebSocket功能**

### **1. SPEAK命令解析**
硬件收到MQTT SPEAK命令后，需要解析：
```json
{
  "cmd": "SPEAK",
  "text": "今天吃药了吗？",
  "track_id": "TRACK123456",
  "audio_url": "ws://47.98.51.180:8000/xiaozhi/v1/"
}
```

### **2. WebSocket连接建立**
```python
# 伪代码示例
def handle_speak_command(speak_data):
    # 1. 发送ACK（已实现✅）
    send_ack(speak_data["track_id"])
    
    # 2. 解析WebSocket URL（需要实现❌）
    audio_url = speak_data["audio_url"]
    
    # 3. 建立WebSocket连接（需要实现❌）
    websocket_client = create_websocket_connection(audio_url)
    
    # 4. 接收音频流（需要实现❌）
    audio_stream = websocket_client.receive_audio()
    
    # 5. 播放音频（需要实现❌）
    play_audio(audio_stream)
```

### **3. WebSocket握手要求**
```http
GET /xiaozhi/v1/ HTTP/1.1
Host: 47.98.51.180:8000
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: [Base64编码的随机16字节]
Sec-WebSocket-Version: 13
Sec-WebSocket-Protocol: xiaozhi-audio
```

### **4. 音频数据处理**
- 🎵 **格式**: WebSocket二进制帧
- 🎵 **编码**: PCM/Opus (根据实际TTS输出)
- 🎵 **播放**: 实时流式播放
- 🎵 **结束**: WebSocket连接关闭时停止

## 🌐 **网络配置**

### **生产环境**
- 📡 **MQTT服务器**: `47.97.185.142:1883` ✅
- 🎵 **WebSocket服务器**: `ws://47.98.51.180:8000/xiaozhi/v1/` ❌

### **测试环境**
- 📡 **MQTT服务器**: `47.97.185.142:1883` ✅  
- 🎵 **WebSocket测试服务器**: `ws://47.98.51.180:8888/xiaozhi/v1/` ❌

## 🔍 **调试方法**

### **1. 验证WebSocket连接能力**
```bash
# 使用WebSocket测试工具
python test_websocket_compatibility.py 8888
```

### **2. 硬件WebSocket客户端测试**
```python
# 硬件端伪代码
import websocket

def test_websocket():
    ws_url = "ws://47.98.51.180:8888/xiaozhi/v1/"
    ws = websocket.WebSocket()
    ws.connect(ws_url)
    print("WebSocket连接成功!")
    ws.close()
```

### **3. 完整流程测试**
```bash
# 触发SPEAK命令
python quick_speak_test.py [device_id]

# 观察WebSocket服务器是否收到硬件连接
```

## 📋 **实现检查清单**

### **阶段1: 基础WebSocket连接**
- [ ] 解析SPEAK命令中的`audio_url`字段
- [ ] 实现WebSocket客户端连接
- [ ] 验证能够成功建立WebSocket握手

### **阶段2: 音频流处理**
- [ ] 接收WebSocket二进制音频数据
- [ ] 实现音频流解码(如果需要)
- [ ] 实现实时音频播放

### **阶段3: 错误处理**
- [ ] 网络连接失败处理
- [ ] 音频播放异常处理
- [ ] 超时和重试机制

## 🎯 **验收标准**

当硬件实现WebSocket功能后，应该能看到：

### **WebSocket服务器日志**
```bash
[时间] ✅ 新连接: (硬件真实IP, 端口)
[时间] ℹ️ 原始数据: b'GET /xiaozhi/v1/ HTTP/1.1...'
[时间] ✅ WebSocket握手成功
[时间] 📤 发送音频数据...
```

### **硬件端效果**
- 🔊 **音频播放**: 清晰播放"今天吃药了吗？"等问候内容
- ⏱️ **响应速度**: 收到SPEAK命令后3-5秒内开始播放
- 🔄 **稳定性**: 多次测试均能正常播放

## 🆘 **技术支持**

如果在实现过程中遇到问题：

1. 📧 **WebSocket握手问题**: 检查HTTP请求头格式
2. 🔌 **网络连接问题**: 确认防火墙和网络配置
3. 🎵 **音频播放问题**: 验证音频格式和解码器
4. 🐛 **调试支持**: 使用提供的测试工具进行诊断

---

## 📈 **当前状态总结**

| 组件 | 状态 | 说明 |
|------|------|------|
| Java API | ✅ 正常 | HTTP通信正常 |
| Python服务 | ✅ 正常 | TTS、MQTT、WebSocket服务器全部正常 |
| 硬件MQTT | ✅ 正常 | 能接收命令、发送ACK |
| **硬件WebSocket** | ❌ **缺失** | **需要实现** |

**下一步：硬件团队实现WebSocket客户端功能** 🎯

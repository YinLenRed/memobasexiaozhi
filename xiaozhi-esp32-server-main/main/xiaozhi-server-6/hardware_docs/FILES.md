# 📁 硬件文档文件清单

## 📚 文档文件

| 文件名 | 用途 | 阅读顺序 |
|--------|------|----------|
| **📖 [README.md](./README.md)** | 文档包总览和快速导航 | 🥇 1 |
| **🚀 [QUICK_START.md](./QUICK_START.md)** | 5分钟快速上手指南 | 🥈 2 |
| **⚡ [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** | 配置和命令速查卡片 | 🥉 3 |
| **📋 [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)** | 完整技术实现指南 | 📖 4 |
| **📄 [FILES.md](./FILES.md)** | 本文件清单 | 📋 - |

## 🛠️ 代码示例

| 文件名 | 内容 | 适用平台 |
|--------|------|----------|
| **🔧 [esp32_example.ino](./esp32_example.ino)** | 完整ESP32 Arduino代码示例 | ESP32 Arduino |
| **📨 [message_examples.json](./message_examples.json)** | 消息格式和测试用例 | 通用参考 |

## 🧪 测试工具

| 文件名 | 功能 | 使用方法 |
|--------|------|----------|
| **🔬 [test_integration.py](./test_integration.py)** | 自动化硬件集成测试 | `python test_integration.py MAC地址` |

## 📖 阅读建议

### 🚀 **新手入门**
1. 先读 `README.md` 了解整体架构
2. 看 `QUICK_START.md` 快速上手
3. 参考 `esp32_example.ino` 开始编码
4. 用 `test_integration.py` 验证实现

### 💻 **开发实现**
1. 详读 `INTEGRATION_GUIDE.md` 了解技术细节
2. 参考 `message_examples.json` 理解消息格式
3. 使用 `QUICK_REFERENCE.md` 作为速查表
4. 持续用 `test_integration.py` 验证功能

### 🔧 **问题排查**
1. 查看 `INTEGRATION_GUIDE.md` 的故障排除部分
2. 对照 `message_examples.json` 检查消息格式
3. 运行 `test_integration.py` 定位问题
4. 参考 `esp32_example.ino` 的注释说明

## 🎯 核心要点速览

### 📡 **必须实现的功能**
- [x] MQTT连接和订阅 `device/{MAC}/cmd`
- [x] JSON消息解析和SPEAK命令处理
- [x] ACK确认回复到 `device/{MAC}/ack` 
- [x] WebSocket连接接收TTS音频
- [x] 播放完成事件上报到 `device/{MAC}/event`

### 🌐 **关键服务器地址**
```
MQTT: 47.97.185.142:1883
WebSocket: ws://172.20.12.204:8000/xiaozhi/v1/
HTTP: http://172.20.12.204:8003
```

### 📨 **核心消息格式**
```json
// 接收命令
{"cmd":"SPEAK","text":"内容","track_id":"WX123"}

// 回复确认
{"evt":"CMD_RECEIVED","track_id":"WX123","timestamp":"09:30:02"}

// 播放完成  
{"evt":"EVT_SPEAK_DONE","track_id":"WX123","timestamp":"09:30:12"}
```

## 🆘 技术支持

### 📞 **需要帮助时**
1. **文档问题**: 查看具体文档的相关章节
2. **代码问题**: 参考 `esp32_example.ino` 示例
3. **测试问题**: 运行 `test_integration.py` 获取详细报告
4. **连接问题**: 查看 `INTEGRATION_GUIDE.md` 故障排除部分

### 📋 **提供技术支持时请包含**
- 设备MAC地址
- 错误日志和串口输出
- 测试脚本运行结果
- 网络环境描述

## 📅 版本信息

- **文档版本**: v1.0
- **适用系统**: 小智ESP32服务器 v0.7.3  
- **更新时间**: 2025-08-21
- **维护团队**: 小智开发组

---

**🎉 祝开发顺利！有问题随时查阅相关文档或联系开发团队。**

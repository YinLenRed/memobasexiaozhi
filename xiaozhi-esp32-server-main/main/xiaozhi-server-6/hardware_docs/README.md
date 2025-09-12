# 🛠️ 硬件开发文档包

> **📋 专为硬件开发人员提供的完整测试和集成指南**

## 📚 文档清单

| 文档 | 用途 | 重要性 |
|------|------|--------|
| **🚀 [快速开始](./QUICK_START.md)** | 5分钟快速上手 | ⭐⭐⭐⭐⭐ |
| **📢 [主动问候指南](./PROACTIVE_GREETING_FOR_HARDWARE.md)** | 🔥 **专为硬件开发详细说明** | ⭐⭐⭐⭐⭐ |
| **📖 [完整指南](./INTEGRATION_GUIDE.md)** | 详细技术文档 | ⭐⭐⭐⭐ |
| **⚡ [快速参考](./QUICK_REFERENCE.md)** | 配置速查卡片 | ⭐⭐⭐⭐ |
| **🧪 [测试工具](./test_integration.py)** | 自动化验证脚本 | ⭐⭐⭐⭐⭐ |
| **📋 [配置示例](./config_examples/)** | 各种配置文件示例 | ⭐⭐⭐ |

## 🚀 快速开始

### 1️⃣ **了解系统架构（2分钟）**
```bash
cat QUICK_START.md
```

### 2️⃣ **查看核心配置（1分钟）**
```bash
cat QUICK_REFERENCE.md
```

### 3️⃣ **验证硬件实现（5分钟）**
```bash
python test_integration.py 你的设备MAC地址
```

## 🎯 核心信息速览

```
🌐 MQTT服务器: 47.97.185.142:1883
🔌 WebSocket: ws://47.98.51.180:8000/xiaozhi/v1/ （硬件开发使用的公网地址）
📱 设备ID格式: MAC地址 (如: 00:0c:29:fc:b7:b9)
🌐 HTTP API: http://47.98.51.180:8003
```

🎯 **硬件开发重点**：使用公网地址 `ws://47.98.51.180:8000/xiaozhi/v1/` 进行WebSocket连接

**📢 主动问候详细说明**：[主动问候硬件指南](./PROACTIVE_GREETING_FOR_HARDWARE.md)
**🔧 完整配置指南**：[../ADDRESS_CONFIG_SOLUTION.md](../ADDRESS_CONFIG_SOLUTION.md)

## 📡 关键主题

| 用途 | MQTT主题格式 |
|------|-------------|
| 订阅命令 | `device/{device-id}/cmd` |
| 回复确认 | `device/{device-id}/ack` |
| 上报事件 | `device/{device-id}/event` |

## ✅ 测试成功标准

- [x] 能连接MQTT服务器
- [x] 正确订阅命令主题
- [x] 解析SPEAK命令
- [x] 发送ACK确认
- [x] 建立WebSocket连接
- [x] 播放TTS音频
- [x] 上报播放完成事件

## 🆘 需要帮助？

1. **查看故障排除**: [INTEGRATION_GUIDE.md#故障排除](./INTEGRATION_GUIDE.md#🔍-故障排除)
2. **运行测试工具**: `python test_integration.py`
3. **联系开发团队**: 提供测试日志和错误信息

## 📅 版本信息

- **文档版本**: v1.0
- **适用系统**: 小智ESP32服务器 v0.7.3
- **更新时间**: 2025-08-21
- **维护团队**: 小智开发组

---

**🎉 祝你测试顺利！有问题随时联系开发团队。**

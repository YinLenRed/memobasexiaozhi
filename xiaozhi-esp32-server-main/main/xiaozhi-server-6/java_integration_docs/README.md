# 📋 Java后端集成文档包

> **专为Java后端开发人员提供的主动问候功能集成文档**

---

## 📚 文档清单

| 文档 | 用途 | 阅读顺序 |
|------|------|----------|
| **📋 [开发人员指南](./FOR_JAVA_DEVELOPERS.md)** | 总览和入口指南 | 🥇 1 |
| **🚀 [快速集成](./JAVA_QUICK_INTEGRATION.md)** | 5分钟快速上手 | 🥈 2 |
| **📖 [详细指南](./JAVA_CRON_INTEGRATION_GUIDE.md)** | 完整技术实现 | 🥉 3 |
| **💬 [开发人员问答](./JAVA_DEVELOPER_ANSWERS.md)** | 🆘 **直接回答您的疑问** | 🚨 必读 |
| **📡 [设备状态推送](./JAVA_SEND_DEVICE_STATUS.md)** | ✅ **方案B完整实现** | 🔥 热门 |
| **📱 [设备状态查询](./DEVICE_STATUS_API_GUIDE.md)** | 设备状态API完整指南 | 🔍 4 |
| **🧪 [API测试示例](./API_TEST_EXAMPLES.md)** | 测试命令和代码 | 🔧 5 |
| **📋 [类别使用指南](./CATEGORY_GUIDE.md)** | Category参数说明 | 📚 6 |

---

## 🎯 快速开始

### **第1步：了解整体情况**
```bash
cat FOR_JAVA_DEVELOPERS.md
```

### **第2步：快速测试集成**
```bash
cat JAVA_QUICK_INTEGRATION.md
```

### **第3步：完整开发实现**
```bash
cat JAVA_CRON_INTEGRATION_GUIDE.md
```

---

## ✅ Python端已完成功能

- **📡 MQTT设备通信** - 完整实现
- **🧠 LLM内容生成** - 智能问候
- **🔊 TTS语音合成** - 多提供商支持
- **🌐 HTTP API接口** - 供Java调用
- **📊 状态管理** - 设备跟踪

---

## 🎯 Java端需要实现

- **⏰ 定时任务调度** - CRON表达式
- **📋 策略管理** - CRUD操作
- **🎨 Web界面** - 策略配置
- **📊 执行日志** - 统计监控

---

## 🌐 核心API地址

**Python服务**: `http://172.20.12.204:8003`

- `POST /xiaozhi/greeting/send` - 发送主动问候
- `GET /xiaozhi/greeting/status` - 查询设备状态和问候执行状态
- `GET /xiaozhi/greeting/status?simple=true` - 简化设备状态查询（仅返回online/offline）
- `POST /xiaozhi/greeting/user` - 更新用户档案
- `GET /xiaozhi/greeting/user` - 获取用户档案

---

## 📡 **设备状态方案B已实现**

### **架构流程**
```
Java后端 → MQTT → Python服务 → HTTP接口 → 其他系统查询
```

### **Java端功能**
- ✅ 发送设备在线/离线状态到MQTT
- ✅ 定期监控设备状态变化
- ✅ 批量状态同步

### **Python端功能**  
- ✅ 自动接收Java设备状态
- ✅ 提供简单查询接口
- ✅ 优先使用Java报告的设备状态

---

## 📞 技术支持

**需要帮助时请查看：**
- **开发问题**: [JAVA_DEVELOPER_ANSWERS.md](./JAVA_DEVELOPER_ANSWERS.md)
- **设备状态**: [JAVA_SEND_DEVICE_STATUS.md](./JAVA_SEND_DEVICE_STATUS.md) 🔥
- **快速问题**: [JAVA_QUICK_INTEGRATION.md](./JAVA_QUICK_INTEGRATION.md)
- **详细实现**: [JAVA_CRON_INTEGRATION_GUIDE.md](./JAVA_CRON_INTEGRATION_GUIDE.md)
- **API查询**: [DEVICE_STATUS_API_GUIDE.md](./DEVICE_STATUS_API_GUIDE.md)
- **硬件文档**: [../hardware_docs/](../hardware_docs/)

---

**🚀 Python端已就绪，期待与您的Java代码完美配合！**

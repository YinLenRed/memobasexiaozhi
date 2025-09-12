# 🤖 小智系统全流程测试指南

## 📋 概述

本测试套件为小智ESP32智能对话系统提供全面的自动化测试解决方案，覆盖从Java API到硬件设备的完整通信链路。

### 系统架构
```
触发源(Java API) → Python服务 → MQTT服务器 → 硬件设备 → WebSocket服务器
     ↓              ↓            ↓           ↓              ↓
  主动问候触发    LLM生成智能内容   推送命令      设备唤醒        音频播放
```

## 🚀 快速开始

### 1. 环境准备
```bash
# 克隆或下载测试文件
# 确保Python 3.8+已安装

# 安装依赖包
pip install asyncio websockets paho-mqtt requests

# 创建必要目录
mkdir -p test_logs test_reports test_audio_data
```

### 2. 一键运行所有测试

**🎯 最简单方式（推荐）：**
```bash
# Linux/Mac用户 - 直接运行
chmod +x 启动测试.sh
./启动测试.sh

# 或使用Python图形化界面
python 快速测试.py
```

**🔧 命令行方式：**
```bash
# 运行完整测试套件（已配置你的Java后端地址）
python run_all_tests.py

# 或指定其他配置参数
python run_all_tests.py \
    --java-url http://q83b6ed9.natappfree.cc \
    --python-url http://47.98.51.180:8003 \
    --device-id 7c:2c:67:8d:89:78 \
    --concurrent 3
```

### 3. 单独运行特定测试
```bash
# Java API测试（已配置你的后端地址）
python test_java_api.py

# MQTT通信测试
python test_mqtt_communication.py --device-id 7c:2c:67:8d:89:78

# WebSocket音频测试
python test_websocket_audio.py --websocket-url ws://47.98.51.180:8000/xiaozhi/v1/

# 完整端到端流程测试
python test_full_flow.py --device-id 7c:2c:67:8d:89:78
```

### 4. 使用硬件模拟器（无真实硬件时）
```bash
# 启动硬件模拟器
python hardware_simulator.py 7c:2c:67:8d:89:78

# 在另一个终端运行测试
python test_mqtt_communication.py
```

## 📊 测试组件详情

### 🔧 1. Java API测试 (`test_java_api.py`)
**测试内容:**
- 服务健康检查
- 用户认证功能
- 配置获取API
- 设备管理API
- 服务端操作API
- API性能压力测试

**运行示例:**
```bash
python test_java_api.py \
    --java-url http://localhost:8080 \
    --username admin \
    --password admin \
    --stress-requests 10
```

### 📡 2. MQTT通信测试 (`test_mqtt_communication.py`)
**测试内容:**
- MQTT连接建立
- SPEAK命令发送
- ACK确认接收
- 事件上报处理
- 并发消息测试
- 消息持久化测试

**运行示例:**
```bash
python test_mqtt_communication.py \
    --host 47.97.185.142 \
    --port 1883 \
    --device-id 7c:2c:67:8d:89:78 \
    --concurrent 5
```

### 🎵 3. WebSocket音频测试 (`test_websocket_audio.py`)
**测试内容:**
- WebSocket连接建立
- 音频数据接收
- 并发音频流测试
- 连接重连测试
- 音频格式兼容性测试

**运行示例:**
```bash
python test_websocket_audio.py \
    --websocket-url ws://47.98.51.180:8000/xiaozhi/v1/ \
    --concurrent 3 \
    --audio-timeout 30
```

### 🔄 4. 端到端流程测试 (`test_full_flow.py`)
**测试内容:**
- 完整流程链路测试
- 各组件集成测试
- 性能指标测试
- 错误处理测试

**运行示例:**
```bash
python test_full_flow.py --device-id 7c:2c:67:8d:89:78
```

### 🤖 5. 硬件设备模拟器 (`hardware_simulator.py`)
**功能特性:**
- 模拟ESP32设备行为
- MQTT命令接收和响应
- WebSocket音频数据接收
- 设备状态上报
- 故障场景模拟

**运行示例:**
```bash
# 基础模拟器
python hardware_simulator.py

# 指定设备ID
python hardware_simulator.py 7c:2c:67:8d:89:78

# 可在代码中调整故障模拟参数
```

## 📈 测试报告

### 报告类型
1. **JSON详细报告** - 机器可读的完整测试数据
2. **HTML可视化报告** - 人类友好的图表展示
3. **控制台实时输出** - 测试过程中的即时反馈

### 报告位置
```
test_reports/
├── master_test_report_20250127_143022.json    # 主报告
├── master_test_report_20250127_143022.html    # HTML报告
├── java_api_report.json                       # Java API详细报告
├── mqtt_report.json                           # MQTT通信详细报告
├── websocket_audio_report.json                # WebSocket音频详细报告
└── full_flow_report.json                      # 端到端流程详细报告
```

## ⚙️ 配置说明

### 系统配置文件位置
```python
# 在代码中修改以下配置类
class SystemConfig:
    # 服务地址配置
    JAVA_API_BASE = "http://q83b6ed9.natappfree.cc"  # 你的Java后端地址
    PYTHON_API_BASE = "http://47.98.51.180:8003"     # 你的Python服务地址
    MQTT_HOST = "47.97.185.142"
    MQTT_PORT = 1883
    WEBSOCKET_URL = "ws://47.98.51.180:8000/xiaozhi/v1/"
    
    # 认证配置
    MQTT_USERNAME = "admin"
    MQTT_PASSWORD = "Jyxd@2025"
    
    # 测试设备配置
    TEST_DEVICE_ID = "7c:2c:67:8d:89:78"
```

### 常用命令行参数
```bash
--java-url          # Java API服务地址
--python-url        # Python API服务地址
--mqtt-host         # MQTT服务器地址
--mqtt-port         # MQTT服务器端口
--websocket-url     # WebSocket服务器地址
--device-id         # 测试设备ID
--concurrent        # 并发测试数量
--timeout           # 测试超时时间(秒)
--report            # 报告文件名
--no-simulator      # 禁用硬件模拟器
--stress-requests   # 压力测试请求数
```

## 🔍 故障排查

### 常见问题及解决方案

#### 1. Java API连接失败
```bash
# 检查Java服务状态
curl http://localhost:8080/actuator/health

# 解决方案:
# - 确认Java API服务已启动
# - 检查端口8080是否开放
# - 验证网络连接
```

#### 2. MQTT连接超时
```bash
# 测试MQTT连接
telnet 47.97.185.142 1883

# 解决方案:
# - 检查防火墙端口1883
# - 验证MQTT用户名密码
# - 确认网络连接稳定
```

#### 3. WebSocket音频传输失败
```bash
# 测试WebSocket连接
wscat -c ws://47.98.51.180:8000/xiaozhi/v1/

# 解决方案:
# - 检查WebSocket服务器状态
# - 验证设备ID格式正确
# - 确认音频服务启用
```

#### 4. 硬件设备无响应
```bash
# 使用硬件模拟器替代测试
python hardware_simulator.py 7c:2c:67:8d:89:78

# 解决方案:
# - 检查设备网络连接
# - 验证设备MQTT配置
# - 确认设备固件版本
```

## 📝 自定义测试

### 添加新的测试用例
```python
# 在相应的测试文件中添加新方法
async def test_custom_feature(self) -> TestResult:
    result = TestResult("自定义功能测试")
    
    try:
        # 您的测试逻辑
        # ...
        
        result.finish(success=True, custom_metric=value)
    except Exception as e:
        result.finish(success=False, error_message=str(e))
    
    self.test_results.append(result)
    return result
```

### 修改测试参数
```python
# 在配置类中调整参数
class CustomTestConfig:
    TEST_TIMEOUT = 60  # 自定义超时时间
    RETRY_ATTEMPTS = 3  # 重试次数
    CUSTOM_DEVICE_IDS = ["device1", "device2"]  # 多设备测试
```

## 🎯 测试最佳实践

### 1. 测试前准备
- ✅ 确保所有服务正常运行
- ✅ 验证网络连接稳定
- ✅ 检查系统资源充足
- ✅ 备份重要数据

### 2. 测试执行
- ✅ 按组件顺序逐步测试
- ✅ 观察实时日志输出
- ✅ 记录异常情况和错误信息
- ✅ 保存测试报告和日志文件

### 3. 测试后分析
- ✅ 查看综合测试报告
- ✅ 分析失败测试的原因
- ✅ 验证性能指标是否达标
- ✅ 制定问题修复计划

## 🔧 高级功能

### 1. 自动化CI/CD集成
```bash
# 在CI/CD流水线中集成测试
#!/bin/bash
set -e

echo "启动小智系统测试..."
python run_all_tests.py --no-simulator --timeout 180

if [ $? -eq 0 ]; then
    echo "✅ 所有测试通过，可以部署"
else
    echo "❌ 测试失败，停止部署"
    exit 1
fi
```

### 2. 定时健康检查
```bash
# 使用cron定时运行健康检查
# 添加到crontab: 0 */4 * * * /path/to/health_check.sh

#!/bin/bash
cd /path/to/xiaozhi-tests
python test_java_api.py --report health_check.json
python test_mqtt_communication.py --report mqtt_health.json

# 发送告警邮件或通知
```

### 3. 性能基准测试
```python
# 创建性能基准
class PerformanceBaseline:
    API_RESPONSE_TIME_MS = 100  # API响应时间基准
    MQTT_ACK_TIME_MS = 50       # MQTT ACK响应基准
    AUDIO_STREAM_MBPS = 1.0     # 音频流传输速度基准
    
    def validate_performance(self, test_results):
        # 验证性能是否符合基准
        pass
```

## 📞 技术支持

### 联系方式
- 📧 邮箱: support@xiaozhi.com
- 💬 技术群: 小智系统开发者群
- 📚 文档: https://docs.xiaozhi.com
- 🐛 问题报告: https://github.com/xiaozhi/issues

### 获取帮助
1. 查看本文档常见问题部分
2. 查看测试日志文件定位问题
3. 在技术群中求助
4. 提交GitHub Issue

---

## 📄 版本历史

### v1.0.0 (2025-01-27)
- ✨ 初始版本发布
- ✨ Java API测试组件
- ✨ MQTT通信测试组件
- ✨ WebSocket音频测试组件
- ✨ 端到端流程测试
- ✨ 硬件设备模拟器
- ✨ 一键运行测试套件
- ✨ HTML可视化报告

---

**🎉 祝您测试愉快！如有问题请随时联系技术支持团队。**

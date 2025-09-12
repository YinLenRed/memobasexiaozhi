# 用户策略功能使用指南

## 功能概述

用户策略功能允许用户通过自然语言向小智助手提出各种提醒、任务和策略请求，系统会自动将这些请求保存到Java后端，并通过MQTT主题进行消息推送。

## 功能特性

- 🎯 **智能识别**: 自动识别用户的策略类型（提醒、闹钟、会议、吃药等）
- 🔄 **Java后端集成**: 直接保存到Java后端API (`/api/saveJob`)
- 📡 **MQTT推送**: 通过`server/dev/report/userPolicy`主题发送消息
- 💬 **自然语言**: 支持各种自然表达方式

## 支持的策略类型

| 类型 | 关键词 | 示例 |
|------|--------|------|
| 提醒任务 | 提醒、叫我、通知我 | "下午三点提醒我开会" |
| 闹钟设置 | 闹钟、起床 | "明天八点叫我起床" |
| 会议安排 | 会议、开会 | "周五下午两点会议提醒" |
| 吃药提醒 | 吃药 | "每天晚上九点提醒我吃药" |
| 生日提醒 | 生日 | "下周五提醒我朋友生日" |
| 其他任务 | - | "记住明天要交报告" |

## 使用方法

### 用户语音/文字输入示例

1. **设置提醒**
   - "明天八点叫我起床"
   - "下午三点提醒我开会"
   - "每天晚上九点提醒我吃药"

2. **任务安排**
   - "记住明天要交报告"
   - "提醒我下周一联系客户"
   - "周五下午两点有个重要会议"

3. **定期提醒**
   - "每天早上七点叫醒我"
   - "每周三提醒我开例会"
   - "每个月5号提醒我交房租"

### 系统响应

系统会自动：
1. 解析用户请求内容
2. 识别任务类型和关键信息
3. 调用Java后端API保存策略
4. 给用户确认反馈

**成功响应示例**：
```
好的，我已经帮您保存了「闹钟提醒」: 明天八点叫我起床。系统会按照您的要求执行相关操作。
```

## 技术实现

### API接口

**Java后端接口**: `POST /api/saveJob`

**请求参数**:
```json
{
  "device_id": "00:0c:29:fc:b7:b9",
  "title": "闹钟提醒",
  "data": "明天八点叫我起床"
}
```

**响应格式**:
```json
{
  "success": true,
  "message": "策略保存成功",
  "data": {...}
}
```

### MQTT主题

- **主题**: `server/dev/report/userPolicy`
- **消息格式**: JSON格式包含设备ID、标题和策略内容

### 配置要求

在`config.yaml`中配置Java后端API：

```yaml
manager-api:
  url: "http://your-java-backend:8080"
  secret: "your_api_secret"
```

## 文件结构

```
xiaozhi-server/
├── core/tools/
│   └── java_backend_strategy.py     # Java后端API服务
├── plugins_func/functions/
│   └── save_user_strategy.py        # 用户策略功能插件
└── docs/
    └── user_strategy_guide.md       # 本使用指南
```

## 错误处理

- **配置缺失**: 提示用户"系统暂未配置策略保存功能"
- **网络错误**: 提示用户"保存策略时遇到网络问题，请稍后再试"
- **服务器错误**: 显示具体错误信息并建议重试
- **超时处理**: 15秒超时保护

## 开发说明

### 添加新的策略类型

1. 在`JavaBackendStrategyService._parse_user_input()`中添加关键词匹配
2. 在`SAVE_USER_STRATEGY_FUNCTION_DESC`中更新task_type枚举
3. 更新本文档的策略类型表格

### 自定义响应消息

修改`JavaBackendStrategyService.process_user_strategy_request()`中的响应文本生成逻辑。

### 集成其他后端

可以扩展`JavaBackendStrategyService`类来支持其他后端API或数据库。

## 常见问题

**Q: 用户说了策略相关的话，但系统没有调用保存功能？**
A: 检查LLM的function calling配置，确保`save_user_strategy`函数已正确注册。

**Q: 保存总是失败？**
A: 检查Java后端API配置和网络连接，确认`/api/saveJob`接口正常工作。

**Q: 如何查看保存的策略？**
A: 策略保存在Java后端数据库中，可以通过Java后端的管理界面查看。

## 更新日志

- **v1.0**: 初始版本，支持基础策略保存功能
- 支持多种任务类型识别
- 集成Java后端API
- 支持MQTT消息推送

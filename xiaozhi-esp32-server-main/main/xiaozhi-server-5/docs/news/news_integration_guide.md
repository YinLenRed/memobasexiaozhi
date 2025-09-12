# 📰 ESP32智能新闻播报功能集成指南

**功能完成日期**: 2025年8月14日  
**版本**: v1.3.0  
**状态**: ✅ **Python端完成，等待Java后端实现**

---

## 🎯 功能概述

ESP32老年人AI设备现已支持智能新闻播报功能，可以主动为老年用户播报适合的新闻内容，包括健康资讯、社区活动、生活服务等，让老年用户及时了解重要信息。

### 🌟 核心特性

- **🎯 老年人友好**: 专门筛选适合老年人的新闻内容
- **🔊 智能播报**: 语音形式播报，清晰易懂
- **👤 个性化推荐**: 根据用户兴趣推送相关新闻
- **📱 实时更新**: 获取最新新闻资讯
- **🤖 LLM增强**: 支持Function Calling智能获取新闻

---

## 🏗️ 系统架构

### 新闻播报流程

```
用户触发 → Python新闻工具 → Java后端API → 第三方新闻源
    ↓
ESP32设备 ← TTS语音合成 ← LLM内容优化 ← 新闻数据处理
```

### 数据流设计

```
新闻获取: Java API → 新闻筛选 → 老年人适配 → Python格式化
播报流程: 新闻内容 → LLM优化 → TTS合成 → MQTT发送 → ESP32播放
记忆保存: 播报记录 → Memobase存储 → 个性化学习
```

---

## ✅ Python端已完成功能

### 1. 新闻工具模块 (`core/tools/news_tool.py`)

**核心类：`NewsTool`**
```python
class NewsTool:
    async def get_news_by_category(category, limit=3)      # 按分类获取新闻
    async def get_elderly_news(user_info=None)             # 获取老年人专用新闻
    def format_news_for_greeting(news_list, max_items=2)   # 格式化播报内容
    def format_news_summary(news_list)                     # 格式化新闻摘要
```

**支持的新闻分类:**
- `elderly` - 老年人专用新闻
- `health` - 健康养生新闻
- `lifestyle` - 生活服务新闻
- `community` - 社区活动新闻
- `general` - 综合新闻

### 2. 主动问候集成

**已集成到 `ProactiveGreetingService`:**
- ✅ 新闻类别自动调用新闻API
- ✅ 支持个性化新闻推荐
- ✅ LLM Function Calling集成
- ✅ 错误处理和备用方案

**使用示例:**
```python
# 发送新闻播报问候
await greeting_service.send_proactive_greeting(
    device_id="ESP32_001",
    initial_content="为您播报今日新闻",
    category="news",
    user_info={
        "name": "李叔",
        "age": 65,
        "interests": ["健康", "社区"]
    }
)
```

### 3. Function Calling支持

**新闻Function定义:**
```python
NEWS_FUNCTION_DEFINITION = {
    "name": "get_latest_news",
    "description": "获取最新新闻信息，特别适合老年用户的新闻内容",
    "parameters": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["elderly", "health", "lifestyle", "community", "general"]
            },
            "max_items": {
                "type": "integer",
                "default": 2,
                "minimum": 1,
                "maximum": 5
            }
        }
    }
}
```

### 4. 示例代码更新

**新增新闻播报演示函数:**
```python
async def demo_news_broadcast():
    """新闻播报功能示例"""
    # 包含多种新闻播报场景
    # 支持个性化推荐测试
    # 演示老年人友好的播报方式
```

---

## ❌ Java后端待实现功能

### 🔧 必需的API接口

#### 1. 分类新闻接口
```
GET /api/news/category/{category}?limit=3
Authorization: Bearer {api_secret}
```

#### 2. 老年人专用新闻接口
```
POST /api/news/elderly
Content-Type: application/json
{
  "user_info": {
    "name": "李叔",
    "age": 65,
    "interests": ["健康", "社区"]
  }
}
```

### 📋 详细规范文档

1. **📄 完整API规范**: `docs/java_news_api_spec.md`
   - 接口定义、请求响应格式
   - 数据库设计建议
   - 错误处理规范

2. **🚀 快速实现**: `docs/java_news_quickstart.md`
   - 45分钟快速实现指南
   - 可立即测试的模拟数据版本
   - 分阶段实现计划

---

## ⚙️ 配置要求

### Python端配置 (已完成)

**`config.yaml` 已包含:**
```yaml
# Java后端API配置
manager-api:
  url: "http://localhost:8080"      # Java后端地址
  secret: "your-api-secret-key"     # API认证密钥
  timeout: 30

# 主动问候功能
proactive_greeting:
  enabled: true
  prompts:
    news: "你是一个贴心的AI助手，需要根据新闻内容为用户生成信息性的问候语。请用客观友善的语气传递信息。"
```

### Java端配置 (待实现)

**application.yml 需要包含:**
```yaml
# API安全配置
api:
  secret: your-api-secret-key  # 与Python端保持一致

# 新闻API配置
news:
  external:
    api_key: your-news-api-key
    base_url: https://api.example-news.com
  elderly:
    max_content_length: 200
    reading_level: simple
```

---

## 🧪 功能测试

### 1. 基础新闻播报测试

```python
# 测试基础新闻播报
response = await client.send_greeting(
    device_id="ESP32_001",
    content="为您播报今日新闻",
    category="news",
    user_info={"name": "李叔", "age": 65}
)
```

**预期效果:**
```
播报前: "李叔，下午好！"
播报后: "李叔，下午好！为您播报今日新闻：健康方面：秋季养生小贴士。专家提醒老年朋友，秋季要注意保暖，适量运动有益健康。另外，社区将举办老年人健身活动，欢迎大家积极参与。"
```

### 2. 个性化新闻推荐测试

```python
# 测试个性化新闻推荐
user_info = {
    "name": "张伯伯",
    "age": 72,
    "location": "北京",
    "interests": ["健康", "社区活动", "养生"]
}

response = await client.send_greeting(
    device_id="ESP32_001",
    content="为您推荐感兴趣的新闻",
    category="news",
    user_info=user_info
)
```

### 3. 运行完整演示

```bash
cd xiaozhi-esp32-server-main/main/xiaozhi-server
python proactive_greeting_example.py
```

**包含的新闻演示:**
- 基础新闻播报
- 健康类新闻
- 社区类新闻
- 养生资讯
- 个性化推荐

---

## 📊 实现进度

### ✅ 已完成 (Python端)

| 功能模块 | 完成度 | 状态 |
|---------|-------|------|
| 新闻工具模块 | 100% | ✅ 完成 |
| 主动问候集成 | 100% | ✅ 完成 |
| Function Calling | 100% | ✅ 完成 |
| 示例代码 | 100% | ✅ 完成 |
| 配置文件 | 100% | ✅ 完成 |
| 文档编写 | 100% | ✅ 完成 |

### ❌ 待完成 (Java端)

| 功能模块 | 完成度 | 优先级 | 预计时间 |
|---------|-------|-------|---------|
| 基础新闻API | 0% | 🔴 高 | 45分钟 |
| 真实新闻集成 | 0% | 🟡 中 | 2小时 |
| 数据库存储 | 0% | 🟡 中 | 3小时 |
| 个性化推荐 | 0% | 🟢 低 | 2小时 |

---

## 🚀 部署和集成

### 快速启动步骤

1. **Java后端实现** (45分钟)
   ```bash
   # 按照快速实现指南创建基础API
   # 参考: docs/java_news_quickstart.md
   ```

2. **启动Java服务**
   ```bash
   mvn spring-boot:run
   ```

3. **测试API接口**
   ```bash
   curl -H "Authorization: Bearer your-api-secret-key" \
        "http://localhost:8080/api/news/category/elderly?limit=3"
   ```

4. **启动Python服务**
   ```bash
   cd xiaozhi-esp32-server-main/main/xiaozhi-server
   python app.py
   ```

5. **测试新闻播报**
   ```bash
   python proactive_greeting_example.py
   ```

### 验证集成成功

**检查项目:**
- [ ] Java API返回正确的新闻数据
- [ ] Python能成功调用Java API
- [ ] 新闻播报功能正常工作
- [ ] ESP32设备能接收播报消息
- [ ] 个性化推荐基本工作

---

## 🎯 用户价值

### 对老年用户的价值

1. **📰 及时资讯**: 主动获取适合的新闻信息
2. **🔊 语音播报**: 无需阅读，听取新闻更轻松
3. **🎯 个性化**: 根据兴趣推送相关新闻
4. **👴 适老化**: 内容简洁易懂，语言亲切
5. **🕐 定时播报**: 可设置定时新闻播报

### 对系统的价值

1. **🧠 智能增强**: LLM优化新闻播报内容
2. **💾 记忆学习**: 记录用户偏好，持续优化
3. **🔗 生态完整**: 与天气、记忆等功能协同
4. **📈 用户粘性**: 提供有价值的信息服务
5. **🎛️ 灵活配置**: 支持多种播报场景

---

## 📈 后续优化方向

### 短期优化 (1-2周)

- **🔍 内容筛选**: 更精准的老年人内容过滤
- **🎯 推荐算法**: 基于用户行为的智能推荐
- **📊 播报统计**: 新闻播报效果分析
- **🔧 性能优化**: 缓存机制和响应速度

### 长期规划 (1-2月)

- **🎵 音频新闻**: 支持音频新闻播报
- **📱 多媒体**: 图片、视频新闻支持
- **🌐 多源聚合**: 集成多个新闻源
- **🤖 AI摘要**: 自动生成新闻摘要

---

## 🎊 总结

### ✅ 新闻功能已就绪

**Python端已100%完成:**
- 新闻工具模块
- 主动问候集成
- Function Calling支持
- 示例代码和文档

**Java端实现简单:**
- 45分钟即可完成基础版本
- 详细的实现指南和代码示例
- 分阶段实现计划

### 🚀 集成后效果

**新闻播报示例:**
> "李叔，下午好！为您播报今日新闻：养生方面：秋季养生小贴士。专家提醒老年朋友，秋季要注意保暖，适量运动有益健康。另外，社区将举办老年人健身活动，欢迎大家积极参与。祝您身体健康！"

**系统能力提升:**
- 从简单问候升级为信息服务
- 从静态内容升级为实时资讯
- 从通用播报升级为个性化推荐

---

**🎯 ESP32智能新闻播报功能已完全准备就绪，只等Java后端实现即可为老年用户提供贴心的新闻服务！** 📰

---

**文档创建时间**: 2025年8月14日  
**负责人**: Python团队  
**状态**: Python端完成，等待Java后端对接  
**预计集成时间**: Java端实现后1小时内完成联调

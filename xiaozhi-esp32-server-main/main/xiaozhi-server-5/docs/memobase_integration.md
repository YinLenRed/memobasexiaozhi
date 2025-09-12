# Memobase记忆数据库集成指南

## 📅 集成信息

**服务地址：** 47.98.51.180:8019  
**集成版本：** v1.2.0  
**更新日期：** 2025年8月14日  
**部署方式：** Docker容器化部署  

### 🐳 **Docker容器架构**
- **API服务：** `server-memobase-server-api` (8019→8000)
- **数据库：** `pgvector/pgvector:pg17` (15432→5432) 
- **缓存：** `redis:7.4` (16379→6379)  

## 🎯 功能概述

Memobase集成为ESP32主动问候功能提供了强大的用户记忆管理能力，实现了：

- **智能记忆查询** - 自动获取用户历史交互记忆
- **个性化问候** - 基于历史记忆生成个性化问候内容
- **记忆自动保存** - 将每次交互自动保存到记忆数据库
- **偏好学习** - 学习用户偏好，优化问候策略

## 🏗️ 系统架构

### 集成架构图

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────────────────┐
│   Java后端      │    │   Python服务     │    │        Memobase服务集群         │
│                 │    │                  │    │       (Docker容器化)           │
├─────────────────┤    ├──────────────────┤    ├─────────────────────────────────┤
│ • 用户管理      │───▶│ • 问候服务       │───▶│ server-memobase-server-api      │
│ • 设备管理      │    │ • LLM生成        │    │ (8019→8000) FastAPI/Django      │
│ • 天气API       │    │ • TTS合成        │    │          ↓                      │
│ • 触发请求      │    │ • MQTT通信       │    │ pgvector/pgvector:pg17          │
└─────────────────┘    └──────────────────┘    │ (15432→5432) 向量数据库         │
                                               │          ↓                      │
                                               │ redis:7.4                       │
                                               │ (16379→6379) 缓存层             │
                                               └─────────────────────────────────┘
```

### 数据流程

```
1. 问候请求 → Python服务
2. 用户ID识别 → Memobase查询历史记忆
3. 记忆数据 → 增强用户上下文
4. LLM生成 → 个性化问候内容  
5. 问候发送 → ESP32设备
6. 交互记录 → 保存到Memobase
```

## ⚙️ 配置设置

### Python端配置

在 `config.yaml` 中添加以下配置：

```yaml
proactive_greeting:
  # 启用主动问候功能
  enabled: true
  
  # 问候内容生成配置
  content_generation:
    # 最大字符数限制
    max_length: 100
    # 是否使用用户记忆信息
    use_memory: true
    # 是否使用用户基础信息
    use_user_info: true
    
    # 记忆数据库配置
    memobase:
      # 记忆数据库服务地址
      host: "47.98.51.180"
      port: 8019
      # 记忆数据库API配置
      api_endpoint: "http://47.98.51.180:8019"
      # 连接超时时间（秒）
      timeout: 10
      # 是否启用记忆服务
      enabled: true
```

### 环境检查

确保以下条件满足：

- [ ] Memobase服务已部署并运行在 47.98.51.180:8019
- [ ] Python服务可以访问Memobase服务
- [ ] 网络防火墙允许HTTP通信
- [ ] 用户数据包含唯一的用户ID

## 🔧 API接口规范

### Memobase需要提供的API接口

#### 1. 获取用户记忆

```http
GET /api/memory/user
```

**请求参数：**
```json
{
  "user_id": "user_001",
  "device_id": "ESP32_001", 
  "limit": 5,
  "type": "greeting"
}
```

**成功响应：**
```json
{
  "status": "success",
  "memories": [
    {
      "id": "memory_001",
      "user_id": "user_001",
      "device_id": "ESP32_001",
      "type": "greeting",
      "content": {
        "greeting": "李叔，下午2点了，该测血压了",
        "user_response": "好的，谢谢提醒",
        "timestamp": 1640995200,
        "success": true
      },
      "tags": ["health", "reminder"],
      "importance": 0.8,
      "created_at": "2024-01-01 14:00:00"
    }
  ]
}
```

#### 2. 保存交互记忆

```http
POST /api/memory/save
```

**请求体：**
```json
{
  "user_id": "user_001",
  "device_id": "ESP32_001",
  "type": "greeting",
  "content": {
    "greeting": "李叔，今天天气晴朗，适合散步",
    "user_response": null,
    "timestamp": 1640995200,
    "success": false
  },
  "tags": ["proactive_greeting", "weather"],
  "importance": 0.7
}
```

**成功响应：**
```json
{
  "status": "success",
  "memory_id": "memory_002",
  "message": "记忆保存成功"
}
```

#### 3. 获取用户偏好

```http
GET /api/memory/preferences/{user_id}
```

**成功响应：**
```json
{
  "status": "success",
  "preferences": {
    "greeting_time": ["14:00", "18:00"],
    "favorite_topics": ["health", "weather", "family"],
    "communication_style": "friendly",
    "reminder_frequency": "daily"
  }
}
```

#### 4. 健康检查

```http
GET /api/health
```

**成功响应：**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 86400
}
```

## 💻 使用示例

### Python客户端示例

```python
import asyncio
from core.tools.memobase_client import MemobaseClient

async def example_usage():
    # 初始化配置
    config = {
        "proactive_greeting": {
            "content_generation": {
                "memobase": {
                    "host": "47.98.51.180",
                    "port": 8019,
                    "api_endpoint": "http://47.98.51.180:8019",
                    "timeout": 10,
                    "enabled": True
                }
            }
        }
    }
    
    # 创建客户端
    client = MemobaseClient(config)
    
    # 获取用户记忆
    memories = await client.get_user_memory("user_001", "ESP32_001")
    print(f"获取到 {len(memories)} 条记忆")
    
    # 格式化记忆为问候文本
    memory_text = client.format_memories_for_greeting(memories)
    print(f"记忆文本: {memory_text}")
    
    # 保存新的交互记忆
    success = await client.save_interaction_memory(
        user_id="user_001",
        device_id="ESP32_001", 
        greeting_content="李叔，今天天气不错，适合散步",
        user_response="好的，我一会儿就去",
        interaction_type="greeting"
    )
    print(f"记忆保存: {'成功' if success else '失败'}")

# 运行示例
asyncio.run(example_usage())
```

### 主动问候API示例

```python
import aiohttp
import asyncio

async def send_greeting_with_memory():
    """发送带记忆增强的主动问候"""
    
    url = "http://localhost:8003/xiaozhi/greeting/send"
    data = {
        "device_id": "ESP32_001",
        "initial_content": "该测血压了",
        "category": "system_reminder",
        "user_info": {
            "id": "user_001",  # 关键：用户ID用于记忆查询
            "name": "李叔",
            "age": 65,
            "location": "广州"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            result = await response.json()
            print(f"问候发送结果: {result}")

asyncio.run(send_greeting_with_memory())
```

## 🔍 记忆数据格式

### 记忆内容结构

```json
{
  "content": {
    "greeting": "生成的问候内容",
    "user_response": "用户回应内容（可选）",
    "timestamp": 1640995200,
    "success": true,
    "category": "weather",
    "context": {
      "weather": "晴天",
      "temperature": "28℃",
      "user_mood": "愉快"
    }
  }
}
```

### 记忆重要性评级

- **0.9-1.0：** 极重要（用户明确反馈、健康相关）
- **0.7-0.8：** 重要（日常交互、偏好信息）
- **0.5-0.6：** 一般（常规问候、系统提醒）
- **0.3-0.4：** 较低（测试数据、错误记录）

### 记忆标签分类

- **健康类：** `health`, `medication`, `exercise`, `checkup`
- **日常类：** `daily`, `routine`, `habit`, `schedule`
- **情感类：** `emotion`, `mood`, `family`, `social`
- **偏好类：** `preference`, `favorite`, `dislike`, `interest`

## 🧪 测试验证

### 1. Docker服务状态检查

```bash
# 检查memobase相关容器状态
docker ps | grep memobase

# 预期输出类似：
# server-memobase-server-api   Up 2 days   0.0.0.0:8019->8000/tcp
# pgvector/pgvector:pg17       Up 2 days   0.0.0.0:15432->5432/tcp  
# redis:7.4                    Up 2 days   0.0.0.0:16379->6379/tcp

# 检查容器日志
docker logs server-memobase-server-api
```

### 2. 连接测试

```bash
# 测试Memobase API服务健康状态
curl http://47.98.51.180:8019/api/health

# 测试API根路径
curl http://47.98.51.180:8019/

# 运行Python测试脚本
cd xiaozhi-esp32-server-main/main/xiaozhi-server
python test_memobase_connection.py
```

### 2. 记忆查询测试

```bash
# 测试获取用户记忆
curl "http://47.98.51.180:8019/api/memory/user?user_id=user_001&limit=5"
```

### 3. 完整流程测试

```python
# 运行完整的记忆增强问候测试
python proactive_greeting_example.py
```

### 4. 性能测试

```python
async def performance_test():
    """记忆服务性能测试"""
    client = MemobaseClient(config)
    
    # 并发记忆查询测试
    tasks = []
    for i in range(10):
        task = client.get_user_memory(f"user_{i:03d}", "ESP32_001")
        tasks.append(task)
    
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    print(f"并发查询10个用户记忆耗时: {end_time - start_time:.2f}秒")
```

## 🚀 性能优化

### 缓存策略

```python
# 建议在MemobaseClient中实现本地缓存
import asyncio
from cachetools import TTLCache

class MemobaseClientWithCache(MemobaseClient):
    def __init__(self, config):
        super().__init__(config)
        self.memory_cache = TTLCache(maxsize=100, ttl=300)  # 5分钟缓存
    
    async def get_user_memory(self, user_id: str, device_id: str = None, limit: int = 5):
        cache_key = f"{user_id}:{device_id}:{limit}"
        
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        memories = await super().get_user_memory(user_id, device_id, limit)
        self.memory_cache[cache_key] = memories
        return memories
```

### 批量操作

```python
async def batch_save_memories(self, memory_list: List[Dict]) -> List[bool]:
    """批量保存记忆，提高性能"""
    if not self.enabled:
        return [True] * len(memory_list)
    
    url = f"{self.api_endpoint}/api/memory/batch_save"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"memories": memory_list}) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("results", [False] * len(memory_list))
            else:
                return [False] * len(memory_list)
```

## 🔧 故障排查

### 常见问题

**Q1: Memobase连接失败**
```bash
# 检查服务是否运行
curl -I http://47.98.51.180:8019/api/health

# 检查网络连通性
ping 47.98.51.180

# 查看Python日志
tail -f tmp/server.log | grep -i memobase
```

**Q2: 记忆查询为空**
- 确认用户ID格式正确
- 检查记忆数据是否已保存
- 验证查询参数和过滤条件

**Q3: 记忆保存失败**
- 检查请求数据格式
- 确认Memobase存储空间充足
- 验证API权限和配置

### 调试技巧

```python
# 启用详细日志
import logging
logging.getLogger('aiohttp').setLevel(logging.DEBUG)

# 记忆查询调试
async def debug_memory_query(user_id: str):
    client = MemobaseClient(config)
    
    # 健康检查
    health = await client.health_check()
    print(f"Memobase健康状态: {health}")
    
    # 记忆查询
    memories = await client.get_user_memory(user_id)
    print(f"查询到记忆数量: {len(memories)}")
    
    for i, memory in enumerate(memories):
        print(f"记忆 {i+1}: {memory}")
```

## 📈 监控指标

### 关键指标

- **记忆查询成功率** - 应保持在95%以上
- **记忆保存成功率** - 应保持在98%以上  
- **平均响应时间** - 记忆查询<500ms，保存<1s
- **缓存命中率** - 应保持在80%以上

### 监控实现

```python
import time
from collections import defaultdict

class MemobaseMonitor:
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def record_query_time(self, duration: float):
        self.metrics['query_times'].append(duration)
    
    def record_save_success(self, success: bool):
        self.metrics['save_results'].append(success)
    
    def get_stats(self):
        return {
            'avg_query_time': sum(self.metrics['query_times']) / len(self.metrics['query_times']),
            'save_success_rate': sum(self.metrics['save_results']) / len(self.metrics['save_results']),
            'total_operations': len(self.metrics['query_times']) + len(self.metrics['save_results'])
        }
```

## 🔮 未来规划

### 短期优化

- [ ] 添加记忆数据压缩
- [ ] 实现智能记忆过期
- [ ] 优化记忆查询算法
- [ ] 添加记忆分析工具

### 长期规划

- [ ] 支持多模态记忆（文本、图像、语音）
- [ ] 实现记忆关联分析
- [ ] 添加记忆推荐系统
- [ ] 集成情感分析

---

**文档创建时间：** 2025年8月14日  
**适用版本：** ESP32主动问候功能 v1.2.0  
**依赖服务：** Memobase 记忆数据库 47.98.51.180:8019

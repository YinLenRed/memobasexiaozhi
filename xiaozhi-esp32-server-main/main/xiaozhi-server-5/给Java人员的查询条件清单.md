# 📋 给Java人员的查询条件清单

## 🎯 **定时器管理功能查询条件**

### 1️⃣ **查询定时器列表**
**功能名**: `list_relative_timers`

**必须参数**:
- `device_id` (string): 设备唯一标识，如 `"f0:9e:9e:04:8a:44"`

**固定过滤条件**:
- `status = "active"`: 只查询活跃状态的定时器
- `target_time > 当前时间`: 只显示未来的定时器

**返回数据结构**:
```json
{
  "timer_id": "设备ID_时间戳_序号",
  "content": "提醒内容",
  "action_type": "动作类型", 
  "target_time": "2025-09-01T12:31:00",
  "duration_description": "30分钟",
  "remaining_time": "剩余时间"
}
```

---

### 2️⃣ **删除定时器**
**功能名**: `cancel_relative_timer`

**必须参数**:
- `device_id` (string): 设备唯一标识
- `confirm_action` (string): 操作类型 `"list"` 或 `"cancel"`

**可选参数**:
- `target_time` (string): 时间匹配，如 `"12点"`, `"12:30"`
- `content_keyword` (string): 内容关键词，如 `"吃饭"`, `"开会"`

**匹配逻辑**:
- **时间匹配**: 支持模糊匹配，`"12点"` 可以匹配 `"12:30"`
- **内容匹配**: 支持包含匹配，`"吃饭"` 可以匹配 `"提醒我吃饭"`
- **优先级**: 时间匹配优先于内容匹配

---

### 3️⃣ **修改定时器**
**功能名**: `modify_relative_timer`

**必须参数**:
- `device_id` (string): 设备唯一标识
- `confirm_action` (string): 操作类型 `"list"` / `"select"` / `"modify"`

**可选参数**:
- `target_time` (string): 要修改的定时器时间
- `new_time` (string): 新的定时时间，如 `"30分钟后"`, `"1小时后"`
- `content_keyword` (string): 内容关键词匹配

**操作流程**:
1. `confirm_action="list"` → 显示所有定时器
2. `confirm_action="select"` → 选择要修改的定时器
3. `confirm_action="modify"` → 执行修改操作

---

## 🔍 **重要技术细节**

### 数据隔离
- **按设备隔离**: 每个查询必须带 `device_id`，只返回该设备的定时器
- **状态过滤**: 只处理 `status="active"` 的定时器
- **时间过滤**: 只显示 `target_time > 当前时间` 的定时器

### 模糊匹配规则
```python
# 时间匹配示例
"12点" 匹配 "12:30"
"下午3" 匹配 "15:00"  
"8点" 匹配 "08:00"

# 内容匹配示例
"吃饭" 匹配 "提醒我吃饭"
"会议" 匹配 "开会提醒"
"药" 匹配 "吃药时间"
```

### 多轮对话状态
- **confirm_action** 参数控制对话流程
- 支持用户逐步确认，避免误操作
- 每个操作都有完整的确认机制

---

## 📊 **数据表结构建议**

### timer_registry 表字段:
```sql
timer_id VARCHAR(50) PRIMARY KEY,
device_id VARCHAR(20) NOT NULL,
content VARCHAR(200),
action_type VARCHAR(50),
target_time DATETIME,
duration_description VARCHAR(50),
timer_type VARCHAR(20),
created_time DATETIME,
status VARCHAR(20)
```

### 索引建议:
```sql
INDEX idx_device_status (device_id, status)
INDEX idx_target_time (target_time)
INDEX idx_device_target (device_id, target_time)
```

---

## 🎯 **关键点总结**

1. **必须按设备隔离**: 所有查询都要带 `device_id`
2. **支持模糊匹配**: 时间和内容都支持部分匹配
3. **多轮对话**: 通过 `confirm_action` 控制流程
4. **状态管理**: 只处理活跃状态的定时器
5. **时间过滤**: 只显示未来的定时器

**这套查询条件设计既保证了数据安全隔离，又提供了灵活的用户交互体验。** ✨

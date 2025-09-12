# 📋 Category 类别使用指南

> **主动问候功能支持的类别说明**

---

## ✅ **支持的类别**

| 类别 | 英文名 | 中文说明 | 使用场景 | 示例内容 |
|------|--------|----------|----------|----------|
| **系统提醒** | `system_reminder` | 健康、服药等提醒 | 定时提醒、健康管理 | "该吃药了，记得按时服用" |
| **日程安排** | `schedule` | 日程、会议等安排 | 日程提醒、重要事项 | "今天下午3点有重要会议" |
| **天气信息** | `weather` | 天气播报和建议 | 天气预报、出行建议 | "今天有雨，记得带伞" |
| **娱乐内容** | `entertainment` | 音乐、娱乐推荐 | 音乐播放、娱乐推荐 | "为您播放一首轻松的音乐" |
| **新闻资讯** | `news` | 新闻播报 | 新闻推送、资讯分享 | "今日重要新闻播报" |

---

## 🚫 **不支持的类别**

❌ `test` - 测试类别（无效）  
❌ `custom` - 自定义类别（无效）  
❌ `other` - 其他类别（无效）

---

## 🧪 **正确的测试命令**

### **天气类别测试**
```bash
curl -X POST http://172.20.12.204:8003/xiaozhi/greeting/send \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "initial_content": "Java集成测试 - 天气信息",
    "category": "weather"
  }'
```

### **系统提醒类别测试**
```bash
curl -X POST http://172.20.12.204:8003/xiaozhi/greeting/send \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "initial_content": "Java集成测试 - 系统提醒",
    "category": "system_reminder"
  }'
```

### **娱乐内容类别测试**
```bash
curl -X POST http://172.20.12.204:8003/xiaozhi/greeting/send \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "initial_content": "Java集成测试 - 娱乐推荐",
    "category": "entertainment"
  }'
```

### **日程安排类别测试**
```bash
curl -X POST http://172.20.12.204:8003/xiaozhi/greeting/send \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "initial_content": "Java集成测试 - 日程提醒",
    "category": "schedule"
  }'
```

### **新闻资讯类别测试**
```bash
curl -X POST http://172.20.12.204:8003/xiaozhi/greeting/send \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "initial_content": "Java集成测试 - 新闻播报",
    "category": "news"
  }'
```

---

## ☕ **Java代码示例**

### **根据场景选择类别**
```java
@Service
public class GreetingCategoryService {
    
    public String determineCategory(String content) {
        if (content.contains("温度") || content.contains("天气") || content.contains("下雨")) {
            return "weather";
        } else if (content.contains("吃药") || content.contains("提醒") || content.contains("健康")) {
            return "system_reminder";
        } else if (content.contains("会议") || content.contains("安排") || content.contains("日程")) {
            return "schedule";
        } else if (content.contains("音乐") || content.contains("娱乐") || content.contains("电影")) {
            return "entertainment";
        } else if (content.contains("新闻") || content.contains("资讯")) {
            return "news";
        } else {
            // 默认使用天气类别
            return "weather";
        }
    }
    
    public GreetingRequest buildRequest(String deviceId, String content) {
        GreetingRequest request = new GreetingRequest();
        request.setDeviceId(deviceId);
        request.setInitialContent(content);
        request.setCategory(determineCategory(content)); // 自动确定类别
        return request;
    }
}
```

### **验证类别的工具方法**
```java
@Component
public class CategoryValidator {
    
    private static final Set<String> VALID_CATEGORIES = Set.of(
        "system_reminder", "schedule", "weather", "entertainment", "news"
    );
    
    public boolean isValidCategory(String category) {
        return VALID_CATEGORIES.contains(category);
    }
    
    public void validateCategory(String category) {
        if (!isValidCategory(category)) {
            throw new IllegalArgumentException(
                "无效的类别: " + category + 
                ", 支持的类别: " + String.join(", ", VALID_CATEGORIES)
            );
        }
    }
}
```

---

## 🛠️ **策略配置建议**

### **数据库表字段**
```sql
CREATE TABLE greeting_strategy (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    strategy_name VARCHAR(100) NOT NULL,
    device_ids JSON,
    cron_expression VARCHAR(50),
    -- 使用枚举约束类别
    category ENUM('system_reminder', 'schedule', 'weather', 'entertainment', 'news') NOT NULL,
    content_template TEXT,
    enabled TINYINT DEFAULT 1
);
```

### **前端选择器配置**
```javascript
// Vue.js 选择器选项
const categoryOptions = [
    { value: 'system_reminder', label: '系统提醒', icon: '🔔' },
    { value: 'schedule', label: '日程安排', icon: '📅' },
    { value: 'weather', label: '天气信息', icon: '🌤️' },
    { value: 'entertainment', label: '娱乐内容', icon: '🎵' },
    { value: 'news', label: '新闻资讯', icon: '📰' }
];
```

---

## 📊 **使用统计建议**

```java
@Entity
public class CategoryUsageStats {
    private String category;
    private LocalDate date;
    private Integer usageCount;
    private Integer successCount;
    private Integer failureCount;
    
    // 可以统计每个类别的使用情况
    // 帮助优化问候策略
}
```

---

**🎯 现在请使用正确的类别进行测试！推荐先用 `weather` 类别测试。** ✅

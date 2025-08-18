# 📰 Java后端新闻API接口规范

**需求确认日期**: 2025年8月14日  
**集成状态**: Python端已完成，等待Java后端实现  
**优先级**: 🟡 **中优先级** - 新闻播报功能

---

## 📋 需求背景

ESP32老年人AI设备需要提供主动新闻播报功能，为老年用户提供适合的新闻内容。系统将根据老年用户的特点，筛选和推送健康、生活、社区等相关新闻。

**Python端已完成:**
- ✅ 新闻工具模块 (`core/tools/news_tool.py`)
- ✅ 主动问候服务集成
- ✅ LLM Function Calling支持
- ✅ 老年人专用新闻格式化

**需要Java后端配合:**
- ❌ 新闻API接口实现
- ❌ 老年人新闻内容筛选
- ❌ 第三方新闻源集成

---

## 🔧 必需的API接口

### 1. 分类新闻接口

#### **接口地址**
```
GET /api/news/category/{category}
```

#### **请求参数**
- **Path参数**: `category` (String) - 新闻分类
  - `general` - 综合新闻
  - `health` - 健康新闻
  - `lifestyle` - 生活新闻
  - `community` - 社区新闻
  - `elderly` - 老年人专用新闻
- **Query参数**: `limit` (Integer) - 返回新闻数量，默认3，最大10
- **Header**: `Authorization: Bearer {api_secret}` - API认证密钥

#### **请求示例**
```http
GET /api/news/category/elderly?limit=3 HTTP/1.1
Host: your-java-server:8080
Authorization: Bearer your-api-secret-key
Content-Type: application/json
```

#### **成功响应 (HTTP 200)**
```json
{
  "news": [
    {
      "title": "秋季养生小贴士",
      "summary": "专家提醒老年朋友，秋季要注意保暖，适量运动有益健康。",
      "content": "随着秋季的到来，老年人应该注意调整作息和饮食习惯...",
      "category": "养生",
      "source": "健康时报",
      "publishTime": "2025-08-14 10:30:00",
      "importance": "high",
      "keywords": ["养生", "老年人", "秋季", "健康"]
    },
    {
      "title": "社区健身活动通知",
      "summary": "社区将举办老年人健身活动，欢迎大家积极参与。",
      "content": "为了促进老年人身心健康，社区决定举办健身活动...",
      "category": "社区",
      "source": "社区服务中心",
      "publishTime": "2025-08-14 09:15:00",
      "importance": "normal",
      "keywords": ["社区", "健身", "活动"]
    }
  ],
  "total": 15,
  "category": "elderly"
}
```

### 2. 老年人专用新闻接口

#### **接口地址**
```
POST /api/news/elderly
```

#### **请求参数**
- **Body**: JSON格式的用户信息（可选，用于个性化推荐）

#### **请求体示例**
```json
{
  "user_info": {
    "name": "李叔",
    "age": 65,
    "location": "广州",
    "interests": ["健康", "运动", "社区活动"],
    "reading_level": "简单"
  }
}
```

#### **成功响应 (HTTP 200)**
```json
{
  "news": [
    {
      "title": "适合老年人的室内运动",
      "summary": "专家推荐几种适合老年人在家进行的运动方式。",
      "content": "对于行动不便的老年人，室内运动是很好的选择...",
      "category": "健康",
      "source": "老年健康",
      "publishTime": "2025-08-14 11:00:00",
      "importance": "high",
      "keywords": ["运动", "室内", "老年人", "健康"],
      "readingDifficulty": "简单",
      "elderlyFriendly": true
    }
  ],
  "total": 8,
  "personalized": true
}
```

### 3. 新闻详情接口

#### **接口地址**
```
GET /api/news/detail/{newsId}
```

#### **请求参数**
- **Path参数**: `newsId` (String) - 新闻ID
- **Header**: `Authorization: Bearer {api_secret}`

#### **成功响应 (HTTP 200)**
```json
{
  "news": {
    "id": "news_001",
    "title": "秋季养生小贴士",
    "summary": "专家提醒老年朋友，秋季要注意保暖，适量运动有益健康。",
    "content": "完整的新闻内容...",
    "category": "养生",
    "source": "健康时报",
    "author": "张医生",
    "publishTime": "2025-08-14 10:30:00",
    "updateTime": "2025-08-14 10:30:00",
    "importance": "high",
    "keywords": ["养生", "老年人", "秋季", "健康"],
    "readCount": 1250,
    "elderlyFriendly": true,
    "audioAvailable": false
  }
}
```

---

## 🔧 错误响应格式

### 认证失败 (HTTP 401)
```json
{
  "error": "认证失败",
  "code": "UNAUTHORIZED"
}
```

### 分类不存在 (HTTP 404)
```json
{
  "error": "新闻分类不存在",
  "code": "CATEGORY_NOT_FOUND",
  "category": "invalid_category"
}
```

### 服务异常 (HTTP 500)
```json
{
  "error": "获取新闻失败",
  "code": "NEWS_API_ERROR",
  "message": "第三方新闻API调用失败"
}
```

---

## 💾 数据库设计建议

### 新闻表
```sql
CREATE TABLE news_articles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    news_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    summary VARCHAR(500),
    content TEXT,
    category VARCHAR(50) NOT NULL,
    source VARCHAR(100),
    author VARCHAR(100),
    publish_time TIMESTAMP,
    importance ENUM('high', 'normal', 'low') DEFAULT 'normal',
    elderly_friendly BOOLEAN DEFAULT FALSE,
    reading_difficulty ENUM('simple', 'medium', 'complex') DEFAULT 'simple',
    keywords JSON,
    read_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_publish_time (publish_time),
    INDEX idx_elderly_friendly (elderly_friendly)
);
```

### 新闻分类表
```sql
CREATE TABLE news_categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    category_code VARCHAR(50) UNIQUE NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    description VARCHAR(200),
    elderly_priority INT DEFAULT 0,  -- 老年人优先级
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认分类
INSERT INTO news_categories (category_code, category_name, description, elderly_priority) VALUES
('elderly', '老年专用', '专门为老年人筛选的新闻', 10),
('health', '健康养生', '健康、养生、医疗相关新闻', 9),
('lifestyle', '生活服务', '日常生活、实用信息', 8),
('community', '社区活动', '社区、邻里、本地新闻', 7),
('general', '综合新闻', '一般性新闻资讯', 5);
```

---

## 🔧 Java后端实现建议

### Spring Boot Controller实现

```java
@RestController
@RequestMapping("/api/news")
@Slf4j
public class NewsController {
    
    @Autowired
    private NewsService newsService;
    
    @Value("${api.secret}")
    private String apiSecret;
    
    @GetMapping("/category/{category}")
    public ResponseEntity<?> getNewsByCategory(
        @PathVariable String category,
        @RequestParam(defaultValue = "3") int limit,
        @RequestHeader("Authorization") String authorization
    ) {
        try {
            // 验证认证
            if (!isValidAuthorization(authorization)) {
                return ResponseEntity.status(401).body(Map.of("error", "认证失败"));
            }
            
            // 验证分类
            if (!newsService.isCategoryValid(category)) {
                return ResponseEntity.status(404).body(Map.of(
                    "error", "新闻分类不存在",
                    "code", "CATEGORY_NOT_FOUND",
                    "category", category
                ));
            }
            
            // 获取新闻
            List<NewsArticle> newsList = newsService.getNewsByCategory(category, limit);
            int total = newsService.getTotalCountByCategory(category);
            
            Map<String, Object> response = Map.of(
                "news", newsList.stream().map(this::convertToDto).collect(Collectors.toList()),
                "total", total,
                "category", category
            );
            
            log.info("分类新闻查询成功: category={}, count={}", category, newsList.size());
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            log.error("新闻API异常: category={}, error={}", category, e.getMessage(), e);
            return ResponseEntity.status(500).body(Map.of(
                "error", "获取新闻失败",
                "code", "NEWS_API_ERROR"
            ));
        }
    }
    
    @PostMapping("/elderly")
    public ResponseEntity<?> getElderlyNews(
        @RequestBody(required = false) Map<String, Object> request,
        @RequestHeader("Authorization") String authorization
    ) {
        try {
            // 验证认证
            if (!isValidAuthorization(authorization)) {
                return ResponseEntity.status(401).body(Map.of("error", "认证失败"));
            }
            
            // 提取用户信息
            Map<String, Object> userInfo = null;
            if (request != null) {
                userInfo = (Map<String, Object>) request.get("user_info");
            }
            
            // 获取老年人专用新闻
            List<NewsArticle> newsList = newsService.getElderlyFriendlyNews(userInfo);
            int total = newsService.getTotalElderlyNewsCount();
            
            Map<String, Object> response = Map.of(
                "news", newsList.stream().map(this::convertToDto).collect(Collectors.toList()),
                "total", total,
                "personalized", userInfo != null
            );
            
            log.info("老年人新闻查询成功: count={}, personalized={}", 
                newsList.size(), userInfo != null);
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            log.error("老年人新闻API异常: error={}", e.getMessage(), e);
            return ResponseEntity.status(500).body(Map.of(
                "error", "获取新闻失败",
                "code", "NEWS_API_ERROR"
            ));
        }
    }
    
    private boolean isValidAuthorization(String authorization) {
        if (authorization == null || !authorization.startsWith("Bearer ")) {
            return false;
        }
        return apiSecret.equals(authorization.substring(7));
    }
    
    private Map<String, Object> convertToDto(NewsArticle article) {
        return Map.of(
            "title", article.getTitle(),
            "summary", article.getSummary(),
            "content", article.getContent(),
            "category", article.getCategory(),
            "source", article.getSource(),
            "publishTime", article.getPublishTime().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")),
            "importance", article.getImportance(),
            "keywords", article.getKeywords()
        );
    }
}
```

### 服务层实现建议

```java
@Service
@Slf4j
public class NewsService {
    
    @Autowired
    private NewsRepository newsRepository;
    
    @Autowired
    private ExternalNewsApiClient externalNewsClient;
    
    public List<NewsArticle> getNewsByCategory(String category, int limit) {
        // 从数据库获取新闻
        List<NewsArticle> dbNews = newsRepository.findByCategoryOrderByPublishTimeDesc(
            category, PageRequest.of(0, limit));
        
        // 如果数据库新闻不足，从外部API补充
        if (dbNews.size() < limit) {
            try {
                List<NewsArticle> externalNews = externalNewsClient.fetchNewsByCategory(category);
                saveAndMergeNews(externalNews, dbNews, limit);
            } catch (Exception e) {
                log.warn("外部新闻API调用失败: {}", e.getMessage());
            }
        }
        
        return dbNews.stream().limit(limit).collect(Collectors.toList());
    }
    
    public List<NewsArticle> getElderlyFriendlyNews(Map<String, Object> userInfo) {
        // 基础老年人友好新闻查询
        List<NewsArticle> elderlyNews = newsRepository.findElderlyFriendlyNews();
        
        // 如果有用户信息，进行个性化筛选
        if (userInfo != null) {
            elderlyNews = personalizeNewsForUser(elderlyNews, userInfo);
        }
        
        // 限制返回数量
        return elderlyNews.stream()
            .sorted(Comparator.comparing(NewsArticle::getPublishTime).reversed())
            .limit(5)
            .collect(Collectors.toList());
    }
    
    private List<NewsArticle> personalizeNewsForUser(List<NewsArticle> news, Map<String, Object> userInfo) {
        // 根据用户信息个性化新闻
        String location = (String) userInfo.get("location");
        List<String> interests = (List<String>) userInfo.get("interests");
        
        return news.stream()
            .filter(article -> isRelevantToUser(article, location, interests))
            .collect(Collectors.toList());
    }
    
    private boolean isRelevantToUser(NewsArticle article, String location, List<String> interests) {
        // 实现个性化逻辑
        if (location != null && article.getContent().contains(location)) {
            return true;
        }
        
        if (interests != null) {
            return interests.stream().anyMatch(interest -> 
                article.getKeywords().contains(interest) || 
                article.getCategory().contains(interest));
        }
        
        return true;
    }
}
```

---

## ⚙️ 配置要求

### application.yml配置
```yaml
# 新闻API配置
news:
  external:
    # 第三方新闻API配置（如头条API、聚合数据等）
    api_key: your-news-api-key
    base_url: https://api.example-news.com
    timeout: 5000
  
  elderly:
    # 老年人新闻筛选配置
    max_content_length: 200  # 最大内容长度
    reading_level: simple    # 阅读难度
    preferred_sources:       # 首选新闻源
      - "健康时报"
      - "老年文摘"
      - "社区服务"

# API安全配置
api:
  secret: your-api-secret-key  # 与Python端保持一致
```

---

## 🧪 测试方案

### 1. 分类新闻测试

```bash
# 获取老年人新闻
curl -H "Authorization: Bearer your-api-secret-key" \
     "http://localhost:8080/api/news/category/elderly?limit=3"

# 获取健康新闻
curl -H "Authorization: Bearer your-api-secret-key" \
     "http://localhost:8080/api/news/category/health?limit=2"
```

### 2. 个性化新闻测试

```bash
curl -X POST \
  -H "Authorization: Bearer your-api-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_info": {
      "name": "李叔",
      "age": 65,
      "location": "广州",
      "interests": ["健康", "运动"]
    }
  }' \
  "http://localhost:8080/api/news/elderly"
```

### 3. Python端集成测试

```python
# 测试新闻类问候
import requests

response = requests.post('http://localhost:8003/xiaozhi/greeting/send', 
    json={
        "device_id": "ESP32_001",
        "initial_content": "为您播报今日新闻",
        "category": "news",
        "user_info": {
            "name": "李叔",
            "age": 65,
            "interests": ["健康", "社区"]
        }
    }
)
print(response.json())
```

---

## 📋 开发清单

### Java后端需要实现
- [ ] **NewsController** - 新闻API控制器
- [ ] **NewsService** - 新闻业务逻辑服务
- [ ] **NewsRepository** - 新闻数据访问层
- [ ] **ExternalNewsApiClient** - 第三方新闻API客户端
- [ ] **数据库表设计** - 新闻和分类表
- [ ] **老年人新闻筛选算法** - 内容适配逻辑

### 可选增强功能
- [ ] **新闻缓存机制** - Redis缓存热门新闻
- [ ] **新闻推荐算法** - 基于用户行为的推荐
- [ ] **音频新闻支持** - TTS音频新闻播报
- [ ] **新闻统计分析** - 阅读量、用户偏好分析

---

## 🚀 集成后效果

### 新闻播报示例
```
播报前: "李叔，下午好！"
集成后: "李叔，下午好！为您播报今日新闻：养生方面：秋季养生小贴士。专家提醒老年朋友，秋季要注意保暖，适量运动有益健康。另外，社区将举办老年人健身活动，欢迎大家积极参与。"
```

### 用户价值
- **📰 实时新闻**: 获取最新的适老新闻资讯
- **🎯 个性化推荐**: 根据用户兴趣推送相关新闻
- **👴 老年友好**: 内容简洁易懂，语言亲切
- **🔔 智能播报**: 自动筛选重要新闻进行播报

---

**🎯 Java后端新闻API是ESP32主动新闻播报功能的核心支撑，Python端已完全准备就绪，等待Java后端实现即可实现智能新闻播报！** 📰

---

**文档创建时间**: 2025年8月14日  
**负责人**: Python团队  
**状态**: 等待Java后端实现  
**技术栈**: Spring Boot + MySQL + 第三方新闻API

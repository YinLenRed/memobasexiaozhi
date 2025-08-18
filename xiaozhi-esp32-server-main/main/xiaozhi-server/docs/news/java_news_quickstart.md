# 🚀 Java后端新闻API快速实现指南

**快速上手时间**: 45分钟  
**完成后即可支持ESP32新闻播报功能**

---

## 📋 快速实现清单

### ✅ 第一步：创建新闻Controller (10分钟)

```java
package com.xiaozhi.controller;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.beans.factory.annotation.Value;
import lombok.extern.slf4j.Slf4j;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

@RestController
@RequestMapping("/api/news")
@Slf4j
public class NewsController {
    
    @Value("${api.secret:your-api-secret-key}")
    private String apiSecret;
    
    @GetMapping("/category/{category}")
    public ResponseEntity<?> getNewsByCategory(
        @PathVariable String category,
        @RequestParam(defaultValue = "3") int limit,
        @RequestHeader("Authorization") String authorization
    ) {
        try {
            // 验证认证
            if (!isValidAuth(authorization)) {
                return ResponseEntity.status(401).body(Map.of("error", "认证失败"));
            }
            
            // 获取对应分类的新闻
            List<Map<String, Object>> news = getNewsMockData(category, limit);
            
            Map<String, Object> response = Map.of(
                "news", news,
                "total", news.size(),
                "category", category
            );
            
            log.info("新闻查询成功: category={}, count={}", category, news.size());
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            log.error("新闻API异常: {}", e.getMessage());
            return ResponseEntity.status(500).body(Map.of("error", "获取新闻失败"));
        }
    }
    
    @PostMapping("/elderly")
    public ResponseEntity<?> getElderlyNews(
        @RequestBody(required = false) Map<String, Object> request,
        @RequestHeader("Authorization") String authorization
    ) {
        try {
            // 验证认证
            if (!isValidAuth(authorization)) {
                return ResponseEntity.status(401).body(Map.of("error", "认证失败"));
            }
            
            // 提取用户信息
            Map<String, Object> userInfo = null;
            if (request != null) {
                userInfo = (Map<String, Object>) request.get("user_info");
            }
            
            // 获取老年人专用新闻
            List<Map<String, Object>> news = getElderlyNewsMockData(userInfo);
            
            Map<String, Object> response = Map.of(
                "news", news,
                "total", news.size(),
                "personalized", userInfo != null
            );
            
            log.info("老年人新闻查询成功: count={}, personalized={}", 
                news.size(), userInfo != null);
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            log.error("老年人新闻API异常: {}", e.getMessage());
            return ResponseEntity.status(500).body(Map.of("error", "获取新闻失败"));
        }
    }
    
    private boolean isValidAuth(String auth) {
        if (auth == null || !auth.startsWith("Bearer ")) return false;
        return apiSecret.equals(auth.substring(7));
    }
    
    private List<Map<String, Object>> getNewsMockData(String category, int limit) {
        // 🔥 临时模拟数据，后续替换为真实新闻API
        List<Map<String, Object>> allNews = Arrays.asList(
            createNewsItem("秋季养生小贴士", "专家提醒老年朋友，秋季要注意保暖，适量运动有益健康。", "健康", "high"),
            createNewsItem("社区健身活动通知", "社区将举办老年人健身活动，欢迎大家积极参与。", "社区", "normal"),
            createNewsItem("血压管理新方法", "医学研究发现，规律作息对血压控制很重要。", "健康", "high"),
            createNewsItem("今日天气提醒", "今天气温适宜，适合外出散步，注意补充水分。", "生活", "normal"),
            createNewsItem("营养膳食建议", "营养师推荐老年人多吃蔬菜水果，少油少盐。", "健康", "normal")
        );
        
        // 根据分类过滤
        List<Map<String, Object>> filteredNews = allNews.stream()
            .filter(news -> category.equals("general") || 
                          news.get("category").toString().contains(getChineseCategoryName(category)))
            .limit(limit)
            .collect(ArrayList::new, (list, item) -> list.add(new HashMap<>(item)), 
                    (list1, list2) -> list1.addAll(list2));
        
        return filteredNews;
    }
    
    private List<Map<String, Object>> getElderlyNewsMockData(Map<String, Object> userInfo) {
        // 老年人专用新闻
        List<Map<String, Object>> elderlyNews = Arrays.asList(
            createNewsItem("老年人健康生活指南", "保持规律作息、适量运动、均衡饮食是健康长寿的关键。", "养生", "high"),
            createNewsItem("防跌倒安全提示", "老年人要注意居家安全，避免滑倒摔伤。", "安全", "high"),
            createNewsItem("心理健康小贴士", "保持乐观心态，多与家人朋友交流，有益身心健康。", "心理", "normal"),
            createNewsItem("用药安全提醒", "按时服药，不要随意增减药量，有疑问及时咨询医生。", "医疗", "high"),
            createNewsItem("季节性疾病预防", "注意季节变化，及时增减衣物，预防感冒。", "健康", "normal")
        );
        
        // 如果有用户信息，进行简单的个性化筛选
        if (userInfo != null) {
            String location = (String) userInfo.get("location");
            if (location != null && location.contains("北京")) {
                elderlyNews.add(createNewsItem("北京老年活动中心通知", "北京市老年活动中心本周将举办健康讲座。", "本地", "normal"));
            }
        }
        
        return elderlyNews.stream().limit(3).collect(ArrayList::new, 
            (list, item) -> list.add(new HashMap<>(item)), 
            (list1, list2) -> list1.addAll(list2));
    }
    
    private Map<String, Object> createNewsItem(String title, String summary, String category, String importance) {
        Map<String, Object> news = new HashMap<>();
        news.put("title", title);
        news.put("summary", summary);
        news.put("content", summary + "详细内容请关注相关健康资讯。");
        news.put("category", category);
        news.put("source", category.equals("健康") ? "健康时报" : "生活日报");
        news.put("publishTime", LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
        news.put("importance", importance);
        news.put("keywords", Arrays.asList(category, "老年人", "健康"));
        return news;
    }
    
    private String getChineseCategoryName(String category) {
        switch (category) {
            case "health": return "健康";
            case "lifestyle": return "生活";
            case "community": return "社区";
            case "elderly": return "养生";
            default: return "综合";
        }
    }
}
```

### ✅ 第二步：配置文件 (2分钟)

**application.yml**
```yaml
# API安全配置
api:
  secret: your-api-secret-key  # 与Python端保持一致

# 新闻API配置
news:
  cache:
    enabled: true
    ttl: 300  # 缓存5分钟
  elderly:
    max_items: 5
    reading_level: simple

# 服务端口
server:
  port: 8080

# 日志配置
logging:
  level:
    com.xiaozhi: DEBUG
```

### ✅ 第三步：启动类确认 (1分钟)

```java
package com.xiaozhi;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class XiaozhiApplication {
    public static void main(String[] args) {
        SpringApplication.run(XiaozhiApplication.class, args);
    }
}
```

---

## 🧪 立即测试

### 1. 启动Java服务
```bash
mvn spring-boot:run
# 或
./gradlew bootRun
```

### 2. 测试新闻接口

**分类新闻测试**
```bash
# 获取老年人新闻
curl -H "Authorization: Bearer your-api-secret-key" \
     "http://localhost:8080/api/news/category/elderly?limit=3"

# 获取健康新闻
curl -H "Authorization: Bearer your-api-secret-key" \
     "http://localhost:8080/api/news/category/health?limit=2"
```

**个性化新闻测试**
```bash
curl -X POST \
  -H "Authorization: Bearer your-api-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_info": {
      "name": "张伯伯",
      "age": 72,
      "location": "北京",
      "interests": ["健康", "运动"]
    }
  }' \
  "http://localhost:8080/api/news/elderly"
```

### 3. 预期响应示例

**分类新闻响应**
```json
{
  "news": [
    {
      "title": "秋季养生小贴士",
      "summary": "专家提醒老年朋友，秋季要注意保暖，适量运动有益健康。",
      "content": "专家提醒老年朋友，秋季要注意保暖，适量运动有益健康。详细内容请关注相关健康资讯。",
      "category": "养生",
      "source": "健康时报",
      "publishTime": "2025-08-14 16:30:00",
      "importance": "high",
      "keywords": ["养生", "老年人", "健康"]
    }
  ],
  "total": 1,
  "category": "elderly"
}
```

### 4. 更新Python配置
确认 `config.yaml` 中的配置：
```yaml
manager-api:
  url: "http://localhost:8080"  # Java服务地址
  secret: "your-api-secret-key"  # 与Java端一致
```

### 5. 测试Python集成
```bash
cd xiaozhi-esp32-server-main/main/xiaozhi-server
python proactive_greeting_example.py  # 会自动测试新闻功能
```

---

## 🔧 后续完善 (可分步实现)

### 第二阶段：真实新闻API集成 (推荐时间：2小时)

**添加依赖**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
</dependency>
<dependency>
    <groupId>mysql</groupId>
    <artifactId>mysql-connector-java</artifactId>
</dependency>
```

**NewsService实现**
```java
@Service
@Slf4j
public class NewsService {
    
    @Value("${news.external.api-key:}")
    private String newsApiKey;
    
    @Autowired
    private RestTemplate restTemplate;
    
    @Autowired
    private NewsRepository newsRepository;
    
    public List<NewsArticle> getRealNews(String category) {
        try {
            // 调用第三方新闻API（如聚合数据、今日头条API等）
            String url = String.format(
                "https://api.example-news.com/v1/news?category=%s&key=%s",
                category, newsApiKey);
            
            NewsApiResponse response = restTemplate.getForObject(url, NewsApiResponse.class);
            
            return processAndFilterNews(response, category);
            
        } catch (Exception e) {
            log.error("获取真实新闻失败: {}", e.getMessage());
            // 返回缓存或默认新闻
            return getDefaultNews(category);
        }
    }
    
    private List<NewsArticle> processAndFilterNews(NewsApiResponse response, String category) {
        return response.getResults().stream()
            .filter(this::isElderlyFriendly)  // 老年人友好过滤
            .map(this::convertToNewsArticle)
            .limit(10)
            .collect(Collectors.toList());
    }
    
    private boolean isElderlyFriendly(ExternalNewsItem item) {
        String content = item.getTitle() + " " + item.getContent();
        
        // 过滤不适合老年人的内容
        String[] excludeKeywords = {"暴力", "恐怖", "复杂", "技术性"};
        for (String keyword : excludeKeywords) {
            if (content.contains(keyword)) {
                return false;
            }
        }
        
        // 优先包含适合老年人的内容
        String[] includeKeywords = {"健康", "养生", "社区", "家庭", "安全"};
        for (String keyword : includeKeywords) {
            if (content.contains(keyword)) {
                return true;
            }
        }
        
        return content.length() < 200;  // 内容简洁
    }
}
```

### 第三阶段：数据库存储 (推荐时间：3小时)

**NewsEntity实现**
```java
@Entity
@Table(name = "news_articles")
public class NewsArticle {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(unique = true)
    private String newsId;
    
    private String title;
    private String summary;
    
    @Column(columnDefinition = "TEXT")
    private String content;
    
    private String category;
    private String source;
    private LocalDateTime publishTime;
    
    @Enumerated(EnumType.STRING)
    private Importance importance;
    
    private boolean elderlyFriendly = false;
    
    // getters and setters...
}
```

**NewsRepository实现**
```java
@Repository
public interface NewsRepository extends JpaRepository<NewsArticle, Long> {
    
    List<NewsArticle> findByCategoryOrderByPublishTimeDesc(String category, Pageable pageable);
    
    @Query("SELECT n FROM NewsArticle n WHERE n.elderlyFriendly = true ORDER BY n.publishTime DESC")
    List<NewsArticle> findElderlyFriendlyNews();
    
    @Query("SELECT COUNT(n) FROM NewsArticle n WHERE n.category = :category")
    int countByCategory(@Param("category") String category);
}
```

---

## 📊 开发进度规划

| 阶段 | 功能 | 预计时间 | 状态 |
|------|------|----------|------|
| 阶段1 | 基础接口 + 模拟数据 | ✅ 45分钟 | 可立即测试 |
| 阶段2 | 真实新闻API集成 | 🔄 2小时 | 建议本周完成 |
| 阶段3 | 数据库存储 + 缓存 | 🔄 3小时 | 建议下周完成 |
| 阶段4 | 个性化推荐 + 监控 | 🔄 2小时 | 可后续优化 |

---

## 🚨 重要提醒

### 立即可用的最小配置

1. **✅ 第一步实现** - 45分钟内即可与Python端联调
2. **🔑 关键配置** - 确保API密钥与Python端一致  
3. **🧪 测试优先** - 先跑通基础流程，再逐步完善

### 配置要点

**Java端**
```yaml
api:
  secret: your-api-secret-key  # 🔥 关键：与Python端保持一致
```

**Python端**
```yaml
manager-api:
  url: "http://localhost:8080"     # 🔥 关键：Java服务实际地址
  secret: "your-api-secret-key"    # 🔥 关键：与Java端保持一致
```

---

## 🎯 验证成功标准

### ✅ 基础功能验证
- [ ] Java接口返回200状态码
- [ ] 返回新闻数据格式正确
- [ ] Python端能成功调用
- [ ] 新闻播报功能正常

### ✅ 集成测试验证
```bash
# Python端新闻播报测试
curl -X POST http://localhost:8003/xiaozhi/greeting/send \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "category": "news",
    "initial_content": "为您播报今日新闻",
    "user_info": {"name": "张伯伯", "age": 72, "interests": ["健康"]}
  }'
```

**预期结果**: 返回包含实际新闻信息的个性化播报内容。

---

## 🌟 新闻播报效果预览

### 播报前
```
"李叔，下午好！"
```

### 集成后
```
"李叔，下午好！为您播报今日新闻：养生方面：秋季养生小贴士。专家提醒老年朋友，秋季要注意保暖，适量运动有益健康。另外，社区将举办老年人健身活动，欢迎大家积极参与。"
```

---

**🎉 Java后端新闻API实现45分钟即可完成基础版本，立即支持ESP32智能新闻播报功能！** 📰

---

**快速实现指南**: 2025年8月14日  
**联调支持**: Python团队随时协助  
**技术栈**: Spring Boot + RestTemplate + 第三方新闻API

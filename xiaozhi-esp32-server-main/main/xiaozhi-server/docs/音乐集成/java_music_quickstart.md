# Java音乐接口快速实现指南

本指南帮助Java后端开发者快速实现ESP32 AI设备音乐播放功能所需的API接口。

## 📋 目录

- [快速开始](#快速开始)
- [依赖配置](#依赖配置)
- [核心代码](#核心代码)
- [数据模型](#数据模型)
- [配置文件](#配置文件)
- [测试验证](#测试验证)
- [部署说明](#部署说明)

## 快速开始

### 1. 添加Maven依赖

```xml
<dependencies>
    <!-- Spring Boot Starter Web -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    
    <!-- Spring Boot Starter Data JPA -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    
    <!-- MySQL Driver -->
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
        <scope>runtime</scope>
    </dependency>
    
    <!-- JSON处理 -->
    <dependency>
        <groupId>com.fasterxml.jackson.core</groupId>
        <artifactId>jackson-databind</artifactId>
    </dependency>
</dependencies>
```

### 2. 创建Controller

```java
package com.xiaozhi.music.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import com.xiaozhi.music.service.MusicService;
import com.xiaozhi.music.dto.*;

@RestController
@RequestMapping("/api/music")
@CrossOrigin(origins = "*")
public class MusicController {
    
    @Autowired
    private MusicService musicService;
    
    /**
     * 获取音乐推荐
     */
    @PostMapping("/recommend")
    public ResponseEntity<?> recommendMusic(@RequestBody MusicRecommendRequest request) {
        try {
            return ResponseEntity.ok(musicService.recommendMusic(request));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(
                new ApiResponse(500, "获取音乐推荐失败: " + e.getMessage())
            );
        }
    }
    
    /**
     * 获取老年人音乐
     */
    @PostMapping("/elderly")
    public ResponseEntity<?> getElderlyMusic(@RequestBody ElderlyMusicRequest request) {
        try {
            return ResponseEntity.ok(musicService.getElderlyMusic(request));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(
                new ApiResponse(500, "获取老年人音乐失败: " + e.getMessage())
            );
        }
    }
    
    /**
     * 播放音乐
     */
    @PostMapping("/play")
    public ResponseEntity<?> playMusic(@RequestBody PlayMusicRequest request) {
        try {
            return ResponseEntity.ok(musicService.playMusic(request));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(
                new ApiResponse(500, "播放音乐失败: " + e.getMessage())
            );
        }
    }
}
```

## 依赖配置

### 核心Service实现

```java
package com.xiaozhi.music.service;

import org.springframework.stereotype.Service;
import com.xiaozhi.music.dto.*;
import java.util.*;

@Service
public class MusicService {
    
    /**
     * 音乐推荐
     */
    public MusicRecommendResponse recommendMusic(MusicRecommendRequest request) {
        List<MusicInfo> musicList = new ArrayList<>();
        
        // 根据音乐类型推荐
        switch (request.getMusicType()) {
            case "elderly":
                musicList = getElderlyMusicList();
                break;
            case "relaxing":
                musicList = getRelaxingMusicList();
                break;
            case "classical":
                musicList = getClassicalMusicList();
                break;
            default:
                musicList = getDefaultMusicList();
        }
        
        // 根据用户信息过滤和排序
        if (request.getUserInfo() != null) {
            musicList = filterByUserPreferences(musicList, request.getUserInfo());
        }
        
        // 限制返回数量
        int limit = request.getLimit() != null ? request.getLimit() : 5;
        if (musicList.size() > limit) {
            musicList = musicList.subList(0, limit);
        }
        
        return MusicRecommendResponse.builder()
            .code(200)
            .message("获取音乐推荐成功")
            .data(MusicListData.builder()
                .musicList(musicList)
                .total(musicList.size())
                .recommendationReason("根据您的喜好推荐")
                .build())
            .build();
    }
    
    /**
     * 老年人音乐
     */
    public ElderlyMusicResponse getElderlyMusic(ElderlyMusicRequest request) {
        List<MusicInfo> musicList = getElderlyMusicByMood(request.getMood());
        
        // 根据时间段调整推荐
        if (request.getTimePeriod() != null) {
            musicList = filterByTimePeriod(musicList, request.getTimePeriod());
        }
        
        int limit = request.getLimit() != null ? request.getLimit() : 3;
        if (musicList.size() > limit) {
            musicList = musicList.subList(0, limit);
        }
        
        return ElderlyMusicResponse.builder()
            .code(200)
            .message("获取老年人音乐成功")
            .data(ElderlyMusicData.builder()
                .musicList(musicList)
                .total(musicList.size())
                .category("elderly_music")
                .build())
            .build();
    }
    
    /**
     * 播放音乐
     */
    public PlayMusicResponse playMusic(PlayMusicRequest request) {
        // 验证音乐是否存在
        MusicInfo music = findMusicById(request.getMusicId());
        if (music == null) {
            throw new RuntimeException("音乐不存在");
        }
        
        // 生成播放ID
        String playId = "play_" + System.currentTimeMillis();
        String streamUrl = generateStreamUrl(request.getMusicId());
        
        PlayResult result = PlayResult.builder()
            .playId(playId)
            .musicInfo(music)
            .playStatus("playing")
            .streamUrl(streamUrl)
            .volume(request.getVolume() != null ? request.getVolume() : 70)
            .build();
        
        return PlayMusicResponse.builder()
            .code(200)
            .message("音乐播放成功")
            .data(result)
            .build();
    }
    
    // 私有辅助方法
    private List<MusicInfo> getElderlyMusicList() {
        return Arrays.asList(
            MusicInfo.builder()
                .musicId("elderly_001")
                .title("夕阳红")
                .artist("经典老歌")
                .album("怀旧金曲")
                .genre("流行")
                .duration(240)
                .url("https://example.com/music/elderly_001.mp3")
                .description("温暖的旋律，适合老年朋友聆听")
                .mood("peaceful")
                .era("80s")
                .language("中文")
                .popularity(88)
                .suitableForElderly(true)
                .tags(Arrays.asList("怀旧", "温暖", "经典"))
                .healthBenefits(Arrays.asList("放松心情", "降低血压"))
                .build(),
            
            MusicInfo.builder()
                .musicId("elderly_002")
                .title("高山流水")
                .artist("古筝演奏")
                .album("古筝名曲")
                .genre("民族")
                .duration(300)
                .url("https://example.com/music/elderly_002.mp3")
                .description("清雅的古筝曲，心灵的净化")
                .mood("peaceful")
                .era("古典")
                .language("纯音乐")
                .popularity(82)
                .suitableForElderly(true)
                .tags(Arrays.asList("古典", "宁静", "民族"))
                .healthBenefits(Arrays.asList("静心", "减压"))
                .build()
        );
    }
    
    private List<MusicInfo> getRelaxingMusicList() {
        return Arrays.asList(
            MusicInfo.builder()
                .musicId("relax_001")
                .title("春江花月夜")
                .artist("民族音乐")
                .album("中国古典名曲")
                .genre("古典")
                .duration(240)
                .url("https://example.com/music/relax_001.mp3")
                .description("优美的古典音乐，适合放松心情")
                .mood("peaceful")
                .era("古典")
                .language("纯音乐")
                .popularity(85)
                .suitableForElderly(true)
                .tags(Arrays.asList("古典", "优美", "放松"))
                .build()
        );
    }
    
    private List<MusicInfo> getClassicalMusicList() {
        return Arrays.asList(
            MusicInfo.builder()
                .musicId("classical_001")
                .title("月光曲")
                .artist("贝多芬")
                .album("贝多芬钢琴名曲")
                .genre("古典")
                .duration(300)
                .url("https://example.com/music/classical_001.mp3")
                .description("宁静优美的钢琴曲")
                .mood("peaceful")
                .era("古典")
                .language("纯音乐")
                .popularity(90)
                .suitableForElderly(true)
                .tags(Arrays.asList("古典", "钢琴", "优美"))
                .build()
        );
    }
    
    private List<MusicInfo> getDefaultMusicList() {
        return getElderlyMusicList(); // 默认返回老年人音乐
    }
    
    private List<MusicInfo> filterByUserPreferences(List<MusicInfo> musicList, UserInfo userInfo) {
        // 根据用户年龄、兴趣等过滤音乐
        return musicList.stream()
            .filter(music -> {
                if (userInfo.getAge() != null && userInfo.getAge() >= 60) {
                    return music.isSuitableForElderly();
                }
                return true;
            })
            .collect(java.util.stream.Collectors.toList());
    }
    
    private List<MusicInfo> getElderlyMusicByMood(String mood) {
        List<MusicInfo> allMusic = getElderlyMusicList();
        if (mood == null) {
            return allMusic;
        }
        
        return allMusic.stream()
            .filter(music -> mood.equals(music.getMood()))
            .collect(java.util.stream.Collectors.toList());
    }
    
    private List<MusicInfo> filterByTimePeriod(List<MusicInfo> musicList, String timePeriod) {
        // 根据时间段过滤音乐
        // 这里可以根据具体需求实现
        return musicList;
    }
    
    private MusicInfo findMusicById(String musicId) {
        // 从数据库或缓存中查找音乐
        List<MusicInfo> allMusic = new ArrayList<>();
        allMusic.addAll(getElderlyMusicList());
        allMusic.addAll(getRelaxingMusicList());
        allMusic.addAll(getClassicalMusicList());
        
        return allMusic.stream()
            .filter(music -> musicId.equals(music.getMusicId()))
            .findFirst()
            .orElse(null);
    }
    
    private String generateStreamUrl(String musicId) {
        return "https://stream.example.com/music/" + musicId;
    }
}
```

## 数据模型

### DTO类定义

```java
// 音乐推荐请求
@Data
@Builder
public class MusicRecommendRequest {
    private String deviceId;
    private String musicType;
    private UserInfo userInfo;
    private Integer limit;
}

// 老年人音乐请求
@Data
@Builder
public class ElderlyMusicRequest {
    private UserInfo userInfo;
    private String mood;
    private String timePeriod;
    private Integer limit;
}

// 播放音乐请求
@Data
@Builder
public class PlayMusicRequest {
    private String deviceId;
    private String musicId;
    private Integer volume;
    private Integer startTime;
}

// 音乐信息
@Data
@Builder
public class MusicInfo {
    private String musicId;
    private String title;
    private String artist;
    private String album;
    private String genre;
    private Integer duration;
    private String url;
    private String description;
    private String mood;
    private String era;
    private String language;
    private Integer popularity;
    private boolean suitableForElderly;
    private List<String> tags;
    private List<String> healthBenefits;
    private List<String> recommendedTime;
}

// 用户信息
@Data
@Builder
public class UserInfo {
    private String id;
    private String name;
    private Integer age;
    private String healthStatus;
    private List<String> interests;
    private Map<String, Object> preferences;
}

// 响应类
@Data
@Builder
public class MusicRecommendResponse {
    private Integer code;
    private String message;
    private MusicListData data;
}

@Data
@Builder
public class MusicListData {
    private List<MusicInfo> musicList;
    private Integer total;
    private String recommendationReason;
}

@Data
@Builder
public class ElderlyMusicResponse {
    private Integer code;
    private String message;
    private ElderlyMusicData data;
}

@Data
@Builder
public class ElderlyMusicData {
    private List<MusicInfo> musicList;
    private Integer total;
    private String category;
}

@Data
@Builder
public class PlayMusicResponse {
    private Integer code;
    private String message;
    private PlayResult data;
}

@Data
@Builder
public class PlayResult {
    private String playId;
    private MusicInfo musicInfo;
    private String playStatus;
    private String streamUrl;
    private Integer volume;
}

@Data
@Builder
public class ApiResponse {
    private Integer code;
    private String message;
    
    public ApiResponse(Integer code, String message) {
        this.code = code;
        this.message = message;
    }
}
```

## 配置文件

### application.yml

```yaml
server:
  port: 8080

spring:
  application:
    name: xiaozhi-music-service
  
  datasource:
    url: jdbc:mysql://localhost:3306/xiaozhi_music?useUnicode=true&characterEncoding=utf8&useSSL=false
    username: xiaozhi
    password: your_password
    driver-class-name: com.mysql.cj.jdbc.Driver
  
  jpa:
    hibernate:
      ddl-auto: update
    show-sql: true
    properties:
      hibernate:
        dialect: org.hibernate.dialect.MySQL8Dialect

# 自定义配置
xiaozhi:
  music:
    api:
      secret: "your-api-secret"
      timeout: 10s
    
    storage:
      base-url: "https://storage.example.com/music"
      cdn-url: "https://cdn.example.com/music"
    
    stream:
      base-url: "https://stream.example.com"
      buffer-size: 8192
    
    recommendation:
      default-limit: 5
      max-limit: 20
      cache-duration: 3600

logging:
  level:
    com.xiaozhi.music: DEBUG
  pattern:
    console: "%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n"
```

### 安全配置

```java
package com.xiaozhi.music.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.springframework.web.servlet.HandlerInterceptor;

@Configuration
public class SecurityConfig implements WebMvcConfigurer {
    
    @Value("${xiaozhi.music.api.secret}")
    private String apiSecret;
    
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new ApiAuthInterceptor())
               .addPathPatterns("/api/**");
    }
    
    private class ApiAuthInterceptor implements HandlerInterceptor {
        @Override
        public boolean preHandle(HttpServletRequest request, 
                               HttpServletResponse response, 
                               Object handler) throws Exception {
            
            String authorization = request.getHeader("Authorization");
            if (authorization == null || !authorization.startsWith("Bearer ")) {
                response.setStatus(401);
                response.getWriter().write("{\"code\":401,\"message\":\"认证失败\"}");
                return false;
            }
            
            String token = authorization.substring(7);
            if (!apiSecret.equals(token)) {
                response.setStatus(401);
                response.getWriter().write("{\"code\":401,\"message\":\"认证失败\"}");
                return false;
            }
            
            return true;
        }
    }
}
```

## 测试验证

### 单元测试

```java
package com.xiaozhi.music.service;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.junit.jupiter.SpringJUnitConfig;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@SpringJUnitConfig
public class MusicServiceTest {
    
    @Autowired
    private MusicService musicService;
    
    @Test
    public void testRecommendMusic() {
        MusicRecommendRequest request = MusicRecommendRequest.builder()
            .deviceId("ESP32_001")
            .musicType("elderly")
            .limit(3)
            .build();
        
        MusicRecommendResponse response = musicService.recommendMusic(request);
        
        assertNotNull(response);
        assertEquals(200, response.getCode());
        assertNotNull(response.getData());
        assertTrue(response.getData().getMusicList().size() <= 3);
    }
    
    @Test
    public void testGetElderlyMusic() {
        ElderlyMusicRequest request = ElderlyMusicRequest.builder()
            .mood("peaceful")
            .limit(2)
            .build();
        
        ElderlyMusicResponse response = musicService.getElderlyMusic(request);
        
        assertNotNull(response);
        assertEquals(200, response.getCode());
        assertNotNull(response.getData());
        assertTrue(response.getData().getMusicList().size() <= 2);
    }
    
    @Test
    public void testPlayMusic() {
        PlayMusicRequest request = PlayMusicRequest.builder()
            .deviceId("ESP32_001")
            .musicId("elderly_001")
            .volume(70)
            .build();
        
        PlayMusicResponse response = musicService.playMusic(request);
        
        assertNotNull(response);
        assertEquals(200, response.getCode());
        assertNotNull(response.getData());
        assertEquals("playing", response.getData().getPlayStatus());
    }
}
```

### 集成测试

```java
package com.xiaozhi.music.controller;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureWebMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import org.springframework.test.web.servlet.result.MockMvcResultMatchers;

@SpringBootTest
@AutoConfigureWebMvc
public class MusicControllerTest {
    
    @Autowired
    private MockMvc mockMvc;
    
    @Test
    public void testRecommendMusicApi() throws Exception {
        String requestBody = """
            {
                "device_id": "ESP32_001",
                "music_type": "elderly",
                "limit": 3
            }
            """;
        
        mockMvc.perform(MockMvcRequestBuilders.post("/api/music/recommend")
                .header("Authorization", "Bearer your-api-secret")
                .contentType("application/json")
                .content(requestBody))
               .andExpect(MockMvcResultMatchers.status().isOk())
               .andExpect(MockMvcResultMatchers.jsonPath("$.code").value(200))
               .andExpect(MockMvcResultMatchers.jsonPath("$.data.music_list").isArray());
    }
}
```

## 部署说明

### 1. 构建项目

```bash
# Maven构建
mvn clean package -DskipTests

# 生成的JAR文件
target/xiaozhi-music-service-1.0.0.jar
```

### 2. Docker部署

```dockerfile
FROM openjdk:11-jre-slim

WORKDIR /app

COPY target/xiaozhi-music-service-1.0.0.jar app.jar

EXPOSE 8080

CMD ["java", "-jar", "app.jar"]
```

```bash
# 构建镜像
docker build -t xiaozhi-music-service .

# 运行容器
docker run -d \
  --name xiaozhi-music \
  -p 8080:8080 \
  -e SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/xiaozhi_music \
  -e SPRING_DATASOURCE_USERNAME=xiaozhi \
  -e SPRING_DATASOURCE_PASSWORD=your_password \
  xiaozhi-music-service
```

### 3. 验证部署

```bash
# 健康检查
curl -X POST "http://localhost:8080/api/music/recommend" \
  -H "Authorization: Bearer your-api-secret" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"ESP32_001","music_type":"elderly","limit":1}'

# 预期响应
{
  "code": 200,
  "message": "获取音乐推荐成功",
  "data": {
    "music_list": [...],
    "total": 1,
    "recommendation_reason": "根据您的喜好推荐"
  }
}
```

## 扩展功能

### 数据库集成

如需集成真实数据库，可以添加以下Entity：

```java
@Entity
@Table(name = "music")
public class MusicEntity {
    @Id
    @Column(name = "id")
    private String musicId;
    
    @Column(name = "title")
    private String title;
    
    @Column(name = "artist")
    private String artist;
    
    // ... 其他字段
}

@Repository
public interface MusicRepository extends JpaRepository<MusicEntity, String> {
    List<MusicEntity> findByGenreAndSuitableForElderlyTrue(String genre);
    List<MusicEntity> findByMoodAndSuitableForElderlyTrue(String mood);
}
```

### 缓存优化

```java
@Service
public class MusicService {
    
    @Cacheable(value = "musicRecommendations", key = "#request.deviceId + '_' + #request.musicType")
    public MusicRecommendResponse recommendMusic(MusicRecommendRequest request) {
        // 实现逻辑
    }
}
```

---

## 📞 技术支持

如有疑问或需要技术支持，请联系开发团队。

### 相关文档
- [Java音乐API接口规范](./java_music_api_spec.md)
- [音乐功能集成指南](./music_integration_guide.md)
- [主动问候开发文档](../development_changelog.md)

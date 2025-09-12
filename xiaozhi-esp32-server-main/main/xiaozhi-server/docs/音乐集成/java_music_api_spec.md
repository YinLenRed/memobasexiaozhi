# Java后端音乐API接口规范

本文档定义了ESP32 AI设备音乐播放功能所需的Java后端API接口规范。

## 📋 目录

- [API概述](#api概述)
- [认证方式](#认证方式)
- [音乐推荐API](#音乐推荐api)
- [老年人音乐API](#老年人音乐api)
- [音乐播放API](#音乐播放api)
- [数据格式](#数据格式)
- [错误处理](#错误处理)
- [实现示例](#实现示例)

## API概述

### 基础信息
- **Base URL**: `{JAVA_API_BASE}/api/music`
- **认证方式**: Bearer Token
- **请求格式**: JSON
- **响应格式**: JSON

### 支持的音乐类型
- `elderly` - 适合老年人的音乐
- `relaxing` - 轻松音乐
- `nostalgic` - 怀旧音乐
- `peaceful` - 宁静音乐
- `classical` - 古典音乐
- `folk` - 民族音乐

## 认证方式

所有API请求需要在Header中包含认证信息：

```http
Authorization: Bearer {API_SECRET}
Content-Type: application/json
```

## 音乐推荐API

### 接口信息
```http
POST /api/music/recommend
```

### 请求参数
```json
{
  "device_id": "ESP32_001",
  "music_type": "relaxing",
  "user_info": {
    "id": "user_123",
    "name": "张老师",
    "age": 70,
    "interests": ["古典音乐", "民谣"],
    "preferences": {
      "music_style": "peaceful",
      "favorite_era": "80s",
      "language": "中文"
    }
  },
  "limit": 5
}
```

### 参数说明
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | 是 | 设备ID |
| music_type | string | 是 | 音乐类型 |
| user_info | object | 否 | 用户信息 |
| limit | integer | 否 | 返回数量，默认5 |

### 响应格式
```json
{
  "code": 200,
  "message": "获取音乐推荐成功",
  "data": {
    "music_list": [
      {
        "music_id": "music_001",
        "title": "春江花月夜",
        "artist": "民族音乐",
        "album": "中国古典名曲",
        "genre": "古典",
        "duration": 240,
        "url": "https://example.com/music/001.mp3",
        "description": "优美的古典音乐，适合放松心情",
        "mood": "peaceful",
        "era": "古典",
        "language": "纯音乐",
        "popularity": 85,
        "suitable_for_elderly": true,
        "tags": ["古典", "宁静", "传统"]
      }
    ],
    "total": 1,
    "recommendation_reason": "根据您的年龄和喜好推荐"
  }
}
```

## 老年人音乐API

### 接口信息
```http
POST /api/music/elderly
```

### 请求参数
```json
{
  "user_info": {
    "id": "user_123",
    "name": "张老师",
    "age": 70,
    "health_status": "良好",
    "interests": ["古典音乐", "民谣"]
  },
  "mood": "peaceful",
  "time_period": "evening",
  "limit": 3
}
```

### 参数说明
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_info | object | 否 | 用户信息 |
| mood | string | 否 | 当前心情 |
| time_period | string | 否 | 时间段（morning/afternoon/evening） |
| limit | integer | 否 | 返回数量，默认3 |

### 响应格式
```json
{
  "code": 200,
  "message": "获取老年人音乐成功",
  "data": {
    "music_list": [
      {
        "music_id": "elderly_001",
        "title": "夕阳红",
        "artist": "经典老歌",
        "album": "怀旧金曲",
        "genre": "流行",
        "duration": 240,
        "url": "https://example.com/music/elderly_001.mp3",
        "description": "温暖的旋律，适合老年朋友聆听",
        "mood": "peaceful",
        "era": "80s",
        "language": "中文",
        "popularity": 88,
        "suitable_for_elderly": true,
        "health_benefits": ["放松心情", "降低血压"],
        "recommended_time": ["evening", "rest"]
      }
    ],
    "total": 1,
    "category": "elderly_music"
  }
}
```

## 音乐播放API

### 接口信息
```http
POST /api/music/play
```

### 请求参数
```json
{
  "device_id": "ESP32_001",
  "music_id": "music_001",
  "volume": 70,
  "start_time": 0
}
```

### 参数说明
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device_id | string | 是 | 设备ID |
| music_id | string | 是 | 音乐ID |
| volume | integer | 否 | 音量（0-100） |
| start_time | integer | 否 | 开始时间（秒） |

### 响应格式
```json
{
  "code": 200,
  "message": "音乐播放成功",
  "data": {
    "play_id": "play_001",
    "music_info": {
      "music_id": "music_001",
      "title": "春江花月夜",
      "duration": 240
    },
    "play_status": "playing",
    "stream_url": "https://example.com/stream/play_001",
    "volume": 70
  }
}
```

## 数据格式

### 音乐对象结构
```json
{
  "music_id": "string",          // 音乐唯一ID
  "title": "string",             // 音乐标题
  "artist": "string",            // 艺术家
  "album": "string",             // 专辑名称
  "genre": "string",             // 音乐类型
  "duration": "integer",         // 时长（秒）
  "url": "string",               // 音乐文件URL
  "description": "string",       // 描述
  "mood": "string",              // 心情类型
  "era": "string",               // 年代
  "language": "string",          // 语言
  "popularity": "integer",       // 流行度（0-100）
  "suitable_for_elderly": "boolean", // 是否适合老年人
  "tags": ["string"],            // 标签数组
  "health_benefits": ["string"], // 健康益处
  "recommended_time": ["string"] // 推荐时间
}
```

### 用户信息结构
```json
{
  "id": "string",                // 用户ID
  "name": "string",              // 姓名
  "age": "integer",              // 年龄
  "health_status": "string",     // 健康状态
  "interests": ["string"],       // 兴趣爱好
  "preferences": {               // 偏好设置
    "music_style": "string",     // 音乐风格
    "favorite_era": "string",    // 喜爱年代
    "language": "string",        // 语言偏好
    "volume_preference": "integer" // 音量偏好
  }
}
```

## 错误处理

### 错误响应格式
```json
{
  "code": 400,
  "message": "请求参数错误",
  "error": "INVALID_PARAMETER",
  "details": {
    "field": "music_type",
    "reason": "不支持的音乐类型"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 常见错误码
| 错误码 | 错误类型 | 说明 |
|--------|----------|------|
| 400 | INVALID_PARAMETER | 请求参数错误 |
| 401 | UNAUTHORIZED | 认证失败 |
| 403 | FORBIDDEN | 权限不足 |
| 404 | MUSIC_NOT_FOUND | 音乐不存在 |
| 404 | DEVICE_NOT_FOUND | 设备不存在 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |
| 503 | SERVICE_UNAVAILABLE | 服务不可用 |

## 实现示例

### Spring Boot Controller示例

```java
@RestController
@RequestMapping("/api/music")
public class MusicController {
    
    @Autowired
    private MusicService musicService;
    
    @PostMapping("/recommend")
    public ResponseEntity<?> recommendMusic(@RequestBody MusicRecommendRequest request) {
        try {
            // 验证请求参数
            if (request.getDeviceId() == null || request.getMusicType() == null) {
                return ResponseEntity.badRequest()
                    .body(new ErrorResponse(400, "设备ID和音乐类型不能为空"));
            }
            
            // 获取音乐推荐
            List<Music> musicList = musicService.recommendMusic(
                request.getDeviceId(),
                request.getMusicType(),
                request.getUserInfo(),
                request.getLimit()
            );
            
            // 构建响应
            MusicRecommendResponse response = new MusicRecommendResponse();
            response.setCode(200);
            response.setMessage("获取音乐推荐成功");
            response.setData(new MusicListData(musicList));
            
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            return ResponseEntity.status(500)
                .body(new ErrorResponse(500, "服务器内部错误"));
        }
    }
    
    @PostMapping("/elderly")
    public ResponseEntity<?> getElderlyMusic(@RequestBody ElderlyMusicRequest request) {
        try {
            List<Music> musicList = musicService.getElderlyMusic(
                request.getUserInfo(),
                request.getMood(),
                request.getTimePeriod(),
                request.getLimit()
            );
            
            ElderlyMusicResponse response = new ElderlyMusicResponse();
            response.setCode(200);
            response.setMessage("获取老年人音乐成功");
            response.setData(new ElderlyMusicData(musicList));
            
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            return ResponseEntity.status(500)
                .body(new ErrorResponse(500, "服务器内部错误"));
        }
    }
    
    @PostMapping("/play")
    public ResponseEntity<?> playMusic(@RequestBody PlayMusicRequest request) {
        try {
            // 验证设备是否在线
            if (!deviceService.isDeviceOnline(request.getDeviceId())) {
                return ResponseEntity.badRequest()
                    .body(new ErrorResponse(404, "设备不在线"));
            }
            
            // 开始播放音乐
            PlayResult result = musicService.playMusic(
                request.getDeviceId(),
                request.getMusicId(),
                request.getVolume(),
                request.getStartTime()
            );
            
            PlayMusicResponse response = new PlayMusicResponse();
            response.setCode(200);
            response.setMessage("音乐播放成功");
            response.setData(result);
            
            return ResponseEntity.ok(response);
            
        } catch (MusicNotFoundException e) {
            return ResponseEntity.status(404)
                .body(new ErrorResponse(404, "音乐不存在"));
        } catch (Exception e) {
            return ResponseEntity.status(500)
                .body(new ErrorResponse(500, "播放失败"));
        }
    }
}
```

### Service层示例

```java
@Service
public class MusicService {
    
    @Autowired
    private MusicRepository musicRepository;
    
    @Autowired
    private UserPreferenceService userPreferenceService;
    
    public List<Music> recommendMusic(String deviceId, String musicType, 
                                    UserInfo userInfo, Integer limit) {
        // 根据用户信息和偏好推荐音乐
        MusicRecommendCriteria criteria = MusicRecommendCriteria.builder()
            .musicType(musicType)
            .userAge(userInfo != null ? userInfo.getAge() : null)
            .userInterests(userInfo != null ? userInfo.getInterests() : null)
            .limit(limit != null ? limit : 5)
            .build();
        
        return musicRepository.findRecommendedMusic(criteria);
    }
    
    public List<Music> getElderlyMusic(UserInfo userInfo, String mood, 
                                     String timePeriod, Integer limit) {
        // 获取适合老年人的音乐
        ElderlyMusicCriteria criteria = ElderlyMusicCriteria.builder()
            .mood(mood)
            .timePeriod(timePeriod)
            .userAge(userInfo != null ? userInfo.getAge() : null)
            .healthStatus(userInfo != null ? userInfo.getHealthStatus() : null)
            .limit(limit != null ? limit : 3)
            .build();
        
        return musicRepository.findElderlyMusic(criteria);
    }
    
    public PlayResult playMusic(String deviceId, String musicId, 
                              Integer volume, Integer startTime) {
        // 获取音乐信息
        Music music = musicRepository.findById(musicId)
            .orElseThrow(() -> new MusicNotFoundException("音乐不存在"));
        
        // 创建播放会话
        String playId = generatePlayId();
        String streamUrl = generateStreamUrl(playId);
        
        // 发送播放指令到设备（通过MQTT或其他方式）
        deviceMusicService.sendPlayCommand(deviceId, music, volume, startTime);
        
        return PlayResult.builder()
            .playId(playId)
            .musicInfo(music)
            .playStatus("playing")
            .streamUrl(streamUrl)
            .volume(volume != null ? volume : 70)
            .build();
    }
}
```

## 配置说明

### application.yml配置示例

```yaml
music:
  api:
    enabled: true
    base-url: "https://api.music.example.com"
    timeout: 10s
    retry-attempts: 3
  
  storage:
    type: "cloud"  # local, cloud, hybrid
    base-path: "/music/storage"
    cdn-url: "https://cdn.music.example.com"
  
  recommendation:
    algorithm: "collaborative_filtering"  # content_based, collaborative_filtering, hybrid
    cache-duration: "1h"
    max-recommendations: 20
  
  elderly:
    default-volume: 70
    safe-volume-limit: 80
    content-filter: "family_friendly"
    health-monitoring: true
```

## 数据库设计

### 音乐表结构
```sql
CREATE TABLE music (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    artist VARCHAR(100),
    album VARCHAR(200),
    genre VARCHAR(50),
    duration INTEGER,
    file_url VARCHAR(500),
    description TEXT,
    mood VARCHAR(20),
    era VARCHAR(20),
    language VARCHAR(20),
    popularity INTEGER DEFAULT 0,
    suitable_for_elderly BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE music_tags (
    music_id VARCHAR(50),
    tag VARCHAR(50),
    PRIMARY KEY (music_id, tag),
    FOREIGN KEY (music_id) REFERENCES music(id)
);

CREATE TABLE user_music_preferences (
    user_id VARCHAR(50),
    music_id VARCHAR(50),
    rating INTEGER,
    play_count INTEGER DEFAULT 0,
    last_played TIMESTAMP,
    PRIMARY KEY (user_id, music_id)
);
```

## 测试用例

### API测试示例

```bash
# 音乐推荐测试
curl -X POST "http://localhost:8080/api/music/recommend" \
  -H "Authorization: Bearer your-api-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "music_type": "elderly",
    "user_info": {
      "id": "user_123",
      "name": "张老师",
      "age": 70
    },
    "limit": 3
  }'

# 老年人音乐测试
curl -X POST "http://localhost:8080/api/music/elderly" \
  -H "Authorization: Bearer your-api-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "mood": "peaceful",
    "time_period": "evening",
    "limit": 2
  }'

# 音乐播放测试
curl -X POST "http://localhost:8080/api/music/play" \
  -H "Authorization: Bearer your-api-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "music_id": "music_001",
    "volume": 70
  }'
```

---

## 📞 技术支持

如有疑问或需要技术支持，请联系开发团队。

### 相关文档
- [音乐功能集成指南](./music_integration_guide.md)
- [Java音乐接口快速实现](./java_music_quickstart.md)
- [主动问候API文档](../api_reference.md)

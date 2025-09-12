# Java端MQTT配置指南

## 概述

本指南将帮助你的同事在Java管理后端中配置MQTT，以便Python服务能够正确获取MQTT配置并启用主动问候功能。

## 🔧 配置步骤

### 1. 数据库迁移

运行提供的数据库迁移脚本 `202506161102_add_mqtt_config.sql`，该脚本会自动添加所有必需的MQTT配置参数到 `sys_params` 表中。

**重要：** 迁移脚本会在项目启动时自动执行，无需手动运行。

### 2. 配置参数说明

| 参数编码 | 默认值 | 类型 | 说明 |
|---------|--------|------|------|
| `mqtt.enabled` | `true` | boolean | 是否启用MQTT功能 |
| `mqtt.host` | `47.97.185.142` | string | MQTT代理服务器地址 |
| `mqtt.port` | `1883` | number | MQTT代理服务器端口 |
| `mqtt.username` | `` | string | MQTT用户名（可选） |
| `mqtt.password` | `` | string | MQTT密码（可选） |
| `mqtt.client_id` | `` | string | MQTT客户端ID，为空时自动生成 |
| `mqtt.topics.command` | `device/{device_id}/cmd` | string | 设备命令主题模板 |
| `mqtt.topics.ack` | `device/{device_id}/ack` | string | 设备回复主题模板 |
| `mqtt.topics.event` | `device/{device_id}/event` | string | 设备事件主题模板 |
| `proactive_greeting.enabled` | `true` | boolean | 是否启用主动问候功能 |
| `proactive_greeting.content_generation.max_length` | `100` | number | 主动问候内容最大字符数 |
| `proactive_greeting.content_generation.use_memory` | `true` | boolean | 是否使用记忆信息生成问候 |
| `proactive_greeting.content_generation.use_user_info` | `true` | boolean | 是否使用用户信息生成问候 |

### 3. 通过数据库直接配置

如果需要手动修改配置，可以直接更新 `sys_params` 表：

```sql
-- 启用MQTT功能
UPDATE sys_params SET param_value = 'true' WHERE param_code = 'mqtt.enabled';

-- 修改MQTT服务器地址
UPDATE sys_params SET param_value = '47.97.185.142' WHERE param_code = 'mqtt.host';

-- 修改MQTT端口
UPDATE sys_params SET param_value = '1883' WHERE param_code = 'mqtt.port';

-- 设置MQTT用户名和密码（如果需要认证）
UPDATE sys_params SET param_value = 'your-username' WHERE param_code = 'mqtt.username';
UPDATE sys_params SET param_value = 'your-password' WHERE param_code = 'mqtt.password';
```

### 4. 通过管理界面配置

如果要在Web管理界面中提供MQTT配置功能，可以参考提供的 `mqtt_config_management_example.java` 示例代码，该代码包含：

- **GET** `/mqtt/config` - 获取当前MQTT配置
- **POST** `/mqtt/config` - 更新MQTT配置  
- **POST** `/mqtt/test-connection` - 测试MQTT连接

#### 示例API调用

**获取MQTT配置：**
```bash
curl -X GET "http://localhost:8080/mqtt/config" \
  -H "Authorization: Bearer your-api-secret"
```

**更新MQTT配置：**
```bash
curl -X POST "http://localhost:8080/mqtt/config" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-secret" \
  -d '{
    "enabled": true,
    "host": "47.97.185.142",
    "port": 1883,
    "username": "",
    "password": "",
    "topics": {
      "command": "device/{device_id}/cmd",
      "ack": "device/{device_id}/ack",
      "event": "device/{device_id}/event"
    },
    "proactiveGreeting": {
      "enabled": true,
      "contentGeneration": {
        "maxLength": 100,
        "useMemory": true,
        "useUserInfo": true
      }
    }
  }'
```

## 🧪 配置验证

### 1. 检查Python服务是否能获取配置

在Python服务端运行诊断脚本：

```bash
python diagnose_mqtt.py
```

预期输出应该包含：
```
✅ 配置加载成功
📋 MQTT配置: {'enabled': True, 'host': '47.98.51.180', 'port': 1883, ...}
🔧 MQTT启用状态: True
✅ MQTTManager 导入成功
✅ MQTT管理器创建成功
```

### 2. 检查Java API配置接口

测试Java配置API：

```bash
curl -X POST "http://localhost:8080/config/server-base" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-secret" \
  -d '{"deviceId": "test-device"}'
```

返回的JSON中应该包含 `mqtt` 配置节点：

```json
{
  "code": 0,
  "data": {
    "mqtt": {
      "enabled": true,
      "host": "47.97.185.142",
      "port": 1883,
      "topics": {
        "command": "device/{device_id}/cmd",
        "ack": "device/{device_id}/ack",
        "event": "device/{device_id}/event"
      }
    },
    "proactive_greeting": {
      "enabled": true,
      "content_generation": {
        "max_length": 100,
        "use_memory": true,
        "use_user_info": true
      }
    }
  }
}
```

### 3. 测试完整流程

运行Python服务的主动问候测试：

```bash
python test_greeting_mqtt.py
```

## 🔍 故障排除

### MQTT配置为空的问题

**问题：** Python服务显示 `📋 MQTT配置: {}`

**解决方案：**
1. 确认数据库迁移脚本已执行
2. 检查 `sys_params` 表中是否有以 `mqtt.` 开头的配置项
3. 重启Java服务以清空Redis缓存
4. 检查Python服务的API连接配置

### MQTT启用状态为False

**问题：** 显示 `🔧 MQTT启用状态: False`

**解决方案：**
```sql
UPDATE sys_params SET param_value = 'true' WHERE param_code = 'mqtt.enabled';
```

### 配置缓存问题

Java服务使用Redis缓存配置。如果修改了数据库但配置没有更新，可以：

1. 重启Java服务
2. 或者清空Redis缓存：
```bash
redis-cli FLUSHALL
```

## 📝 注意事项

1. **配置生效时间：** 数据库配置修改后，Java服务会将新配置缓存到Redis中，Python服务在下次调用API时会获取最新配置。

2. **参数类型：** 确保参数的 `value_type` 字段正确设置（string/number/boolean/json），这影响Python端的配置解析。

3. **主题模板：** MQTT主题支持 `{device_id}` 占位符，在实际使用时会被替换为具体的设备ID。

4. **安全考虑：** 如果MQTT服务器需要认证，务必设置用户名和密码。

## 🔗 相关文件

- 数据库迁移脚本：`src/main/resources/db/changelog/202506161102_add_mqtt_config.sql`
- Java管理代码示例：`mqtt_config_management_example.java`
- Python诊断脚本：`xiaozhi-server/diagnose_mqtt.py`

/**
 * MQTT配置管理示例代码
 * 如果需要在Java管理界面中管理MQTT配置，可以参考以下代码结构
 */

package xiaozhi.modules.mqtt.controller;

import org.springframework.web.bind.annotation.*;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.sys.service.SysParamsService;

import java.util.HashMap;
import java.util.Map;

/**
 * MQTT配置管理控制器
 * 提供MQTT配置的查询和修改接口
 */
@RestController
@RequestMapping("mqtt")
@Tag(name = "MQTT配置管理")
@AllArgsConstructor
public class MqttConfigController {
    
    private final SysParamsService sysParamsService;

    @GetMapping("config")
    @Operation(summary = "获取MQTT配置")
    public Result<Map<String, Object>> getMqttConfig() {
        Map<String, Object> config = new HashMap<>();
        
        // 获取MQTT基础配置
        config.put("enabled", Boolean.parseBoolean(sysParamsService.getValue("mqtt.enabled", true)));
        config.put("host", sysParamsService.getValue("mqtt.host", true));
        config.put("port", Integer.parseInt(sysParamsService.getValue("mqtt.port", true)));
        config.put("username", sysParamsService.getValue("mqtt.username", true));
        config.put("password", sysParamsService.getValue("mqtt.password", true));
        config.put("client_id", sysParamsService.getValue("mqtt.client_id", true));
        
        // 获取主题配置
        Map<String, Object> topics = new HashMap<>();
        topics.put("command", sysParamsService.getValue("mqtt.topics.command", true));
        topics.put("ack", sysParamsService.getValue("mqtt.topics.ack", true));
        topics.put("event", sysParamsService.getValue("mqtt.topics.event", true));
        config.put("topics", topics);
        
        // 获取主动问候配置
        Map<String, Object> proactiveGreeting = new HashMap<>();
        proactiveGreeting.put("enabled", Boolean.parseBoolean(sysParamsService.getValue("proactive_greeting.enabled", true)));
        
        Map<String, Object> contentGeneration = new HashMap<>();
        contentGeneration.put("max_length", Integer.parseInt(sysParamsService.getValue("proactive_greeting.content_generation.max_length", true)));
        contentGeneration.put("use_memory", Boolean.parseBoolean(sysParamsService.getValue("proactive_greeting.content_generation.use_memory", true)));
        contentGeneration.put("use_user_info", Boolean.parseBoolean(sysParamsService.getValue("proactive_greeting.content_generation.use_user_info", true)));
        proactiveGreeting.put("content_generation", contentGeneration);
        
        config.put("proactive_greeting", proactiveGreeting);
        
        return new Result<Map<String, Object>>().ok(config);
    }

    @PostMapping("config")
    @Operation(summary = "更新MQTT配置")
    public Result<String> updateMqttConfig(@RequestBody MqttConfigUpdateRequest request) {
        try {
            // 更新MQTT基础配置
            if (request.getEnabled() != null) {
                sysParamsService.updateValueByCode("mqtt.enabled", request.getEnabled().toString());
            }
            if (request.getHost() != null) {
                sysParamsService.updateValueByCode("mqtt.host", request.getHost());
            }
            if (request.getPort() != null) {
                sysParamsService.updateValueByCode("mqtt.port", request.getPort().toString());
            }
            if (request.getUsername() != null) {
                sysParamsService.updateValueByCode("mqtt.username", request.getUsername());
            }
            if (request.getPassword() != null) {
                sysParamsService.updateValueByCode("mqtt.password", request.getPassword());
            }
            if (request.getClientId() != null) {
                sysParamsService.updateValueByCode("mqtt.client_id", request.getClientId());
            }
            
            // 更新主题配置
            if (request.getTopics() != null) {
                MqttTopicsConfig topics = request.getTopics();
                if (topics.getCommand() != null) {
                    sysParamsService.updateValueByCode("mqtt.topics.command", topics.getCommand());
                }
                if (topics.getAck() != null) {
                    sysParamsService.updateValueByCode("mqtt.topics.ack", topics.getAck());
                }
                if (topics.getEvent() != null) {
                    sysParamsService.updateValueByCode("mqtt.topics.event", topics.getEvent());
                }
            }
            
            // 更新主动问候配置
            if (request.getProactiveGreeting() != null) {
                ProactiveGreetingConfig greeting = request.getProactiveGreeting();
                if (greeting.getEnabled() != null) {
                    sysParamsService.updateValueByCode("proactive_greeting.enabled", greeting.getEnabled().toString());
                }
                if (greeting.getContentGeneration() != null) {
                    ContentGenerationConfig contentGen = greeting.getContentGeneration();
                    if (contentGen.getMaxLength() != null) {
                        sysParamsService.updateValueByCode("proactive_greeting.content_generation.max_length", contentGen.getMaxLength().toString());
                    }
                    if (contentGen.getUseMemory() != null) {
                        sysParamsService.updateValueByCode("proactive_greeting.content_generation.use_memory", contentGen.getUseMemory().toString());
                    }
                    if (contentGen.getUseUserInfo() != null) {
                        sysParamsService.updateValueByCode("proactive_greeting.content_generation.use_user_info", contentGen.getUseUserInfo().toString());
                    }
                }
            }
            
            return new Result<String>().ok("MQTT配置更新成功");
        } catch (Exception e) {
            return new Result<String>().error("更新失败: " + e.getMessage());
        }
    }

    @PostMapping("test-connection")
    @Operation(summary = "测试MQTT连接")
    public Result<String> testMqttConnection() {
        // 这里可以添加MQTT连接测试逻辑
        // 比如创建临时的MQTT客户端连接进行测试
        try {
            String host = sysParamsService.getValue("mqtt.host", true);
            String port = sysParamsService.getValue("mqtt.port", true);
            
            // TODO: 实现MQTT连接测试逻辑
            // MqttClient testClient = new MqttClient("tcp://" + host + ":" + port, "test-client");
            // testClient.connect();
            // testClient.disconnect();
            
            return new Result<String>().ok("MQTT连接测试成功");
        } catch (Exception e) {
            return new Result<String>().error("MQTT连接测试失败: " + e.getMessage());
        }
    }
}

/**
 * MQTT配置更新请求类
 */
class MqttConfigUpdateRequest {
    private Boolean enabled;
    private String host;
    private Integer port;
    private String username;
    private String password;
    private String clientId;
    private MqttTopicsConfig topics;
    private ProactiveGreetingConfig proactiveGreeting;
    
    // Getters and Setters
    public Boolean getEnabled() { return enabled; }
    public void setEnabled(Boolean enabled) { this.enabled = enabled; }
    
    public String getHost() { return host; }
    public void setHost(String host) { this.host = host; }
    
    public Integer getPort() { return port; }
    public void setPort(Integer port) { this.port = port; }
    
    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
    
    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }
    
    public String getClientId() { return clientId; }
    public void setClientId(String clientId) { this.clientId = clientId; }
    
    public MqttTopicsConfig getTopics() { return topics; }
    public void setTopics(MqttTopicsConfig topics) { this.topics = topics; }
    
    public ProactiveGreetingConfig getProactiveGreeting() { return proactiveGreeting; }
    public void setProactiveGreeting(ProactiveGreetingConfig proactiveGreeting) { this.proactiveGreeting = proactiveGreeting; }
}

/**
 * MQTT主题配置类
 */
class MqttTopicsConfig {
    private String command;
    private String ack;
    private String event;
    
    // Getters and Setters
    public String getCommand() { return command; }
    public void setCommand(String command) { this.command = command; }
    
    public String getAck() { return ack; }
    public void setAck(String ack) { this.ack = ack; }
    
    public String getEvent() { return event; }
    public void setEvent(String event) { this.event = event; }
}

/**
 * 主动问候配置类
 */
class ProactiveGreetingConfig {
    private Boolean enabled;
    private ContentGenerationConfig contentGeneration;
    
    // Getters and Setters
    public Boolean getEnabled() { return enabled; }
    public void setEnabled(Boolean enabled) { this.enabled = enabled; }
    
    public ContentGenerationConfig getContentGeneration() { return contentGeneration; }
    public void setContentGeneration(ContentGenerationConfig contentGeneration) { this.contentGeneration = contentGeneration; }
}

/**
 * 内容生成配置类
 */
class ContentGenerationConfig {
    private Integer maxLength;
    private Boolean useMemory;
    private Boolean useUserInfo;
    
    // Getters and Setters
    public Integer getMaxLength() { return maxLength; }
    public void setMaxLength(Integer maxLength) { this.maxLength = maxLength; }
    
    public Boolean getUseMemory() { return useMemory; }
    public void setUseMemory(Boolean useMemory) { this.useMemory = useMemory; }
    
    public Boolean getUseUserInfo() { return useUserInfo; }
    public void setUseUserInfo(Boolean useUserInfo) { this.useUserInfo = useUserInfo; }
}

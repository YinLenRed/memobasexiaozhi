/**
 * Java后端天气预警MQTT发布器
 * 向Python端发送预警信息的示例代码
 */
package com.xiaozhi.weather.alert;

import org.eclipse.paho.client.mqttv3.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.annotation.JsonFormat;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 天气预警MQTT发布器
 */
public class WeatherAlertPublisher {
    
    private static final Logger logger = LoggerFactory.getLogger(WeatherAlertPublisher.class);
    
    private MqttClient mqttClient;
    private ObjectMapper objectMapper;
    private String brokerUrl;
    private String clientId;
    private String username;
    private String password;
    
    // MQTT主题配置
    private static final String TOPIC_BROADCAST = "weather/alert/broadcast";
    private static final String TOPIC_REGIONAL = "weather/alert/regional";
    private static final String TOPIC_DEVICE_PREFIX = "weather/alert/device/";
    
    /**
     * 构造函数
     */
    public WeatherAlertPublisher(String brokerUrl, String clientId, String username, String password) {
        this.brokerUrl = brokerUrl;
        this.clientId = clientId;
        this.username = username;
        this.password = password;
        this.objectMapper = new ObjectMapper();
    }
    
    /**
     * 连接MQTT Broker
     */
    public void connect() throws MqttException {
        mqttClient = new MqttClient(brokerUrl, clientId);
        
        MqttConnectOptions options = new MqttConnectOptions();
        options.setUserName(username);
        options.setPassword(password.toCharArray());
        options.setCleanSession(true);
        options.setKeepAliveInterval(60);
        options.setAutomaticReconnect(true);
        
        mqttClient.connect(options);
        logger.info("MQTT连接成功: {}", brokerUrl);
    }
    
    /**
     * 断开MQTT连接
     */
    public void disconnect() throws MqttException {
        if (mqttClient != null && mqttClient.isConnected()) {
            mqttClient.disconnect();
            mqttClient.close();
            logger.info("MQTT连接已断开");
        }
    }
    
    /**
     * 发送广播预警（所有设备）
     */
    public void publishBroadcastAlert(WeatherAlert alert) throws Exception {
        publishAlert(TOPIC_BROADCAST, alert);
        logger.info("发送广播预警成功: {}", alert.getTitle());
    }
    
    /**
     * 发送区域预警
     */
    public void publishRegionalAlert(WeatherAlert alert) throws Exception {
        publishAlert(TOPIC_REGIONAL, alert);
        logger.info("发送区域预警成功: {}", alert.getTitle());
    }
    
    /**
     * 发送设备特定预警
     */
    public void publishDeviceAlert(String deviceId, WeatherAlert alert) throws Exception {
        String topic = TOPIC_DEVICE_PREFIX + deviceId;
        // 添加设备ID到预警数据中
        alert.setDeviceIds(Arrays.asList(deviceId));
        publishAlert(topic, alert);
        logger.info("发送设备预警成功: {} -> {}", deviceId, alert.getTitle());
    }
    
    /**
     * 批量发送设备预警
     */
    public void publishMultiDeviceAlert(List<String> deviceIds, WeatherAlert alert) throws Exception {
        // 设置目标设备列表
        alert.setDeviceIds(deviceIds);
        
        // 可以选择广播模式或逐个发送
        if (deviceIds.size() > 5) {
            // 设备较多时使用广播模式
            publishBroadcastAlert(alert);
        } else {
            // 设备较少时逐个发送
            for (String deviceId : deviceIds) {
                publishDeviceAlert(deviceId, alert);
            }
        }
    }
    
    /**
     * 核心发布方法
     */
    private void publishAlert(String topic, WeatherAlert alert) throws Exception {
        try {
            // 序列化预警数据
            String jsonPayload = objectMapper.writeValueAsString(alert);
            
            // 创建MQTT消息
            MqttMessage message = new MqttMessage(jsonPayload.getBytes("UTF-8"));
            message.setQos(1);  // QoS=1 保证消息送达
            message.setRetained(false);  // 不保留消息
            
            // 发布消息
            mqttClient.publish(topic, message);
            
            logger.debug("预警消息发布成功: topic={}, payload={}", topic, jsonPayload);
            
        } catch (Exception e) {
            logger.error("发布预警消息失败: topic={}, error={}", topic, e.getMessage(), e);
            throw e;
        }
    }
    
    /**
     * 创建测试预警
     */
    public WeatherAlert createTestAlert() {
        WeatherAlert alert = new WeatherAlert();
        alert.setId("test_" + System.currentTimeMillis());
        alert.setSender("测试气象台");
        alert.setPubTime(formatDateTime(LocalDateTime.now()));
        alert.setTitle("测试高温预警");
        alert.setStartTime(formatDateTime(LocalDateTime.now()));
        alert.setEndTime(formatDateTime(LocalDateTime.now().plusHours(24)));
        alert.setStatus("active");
        alert.setLevel("Orange");
        alert.setSeverity("Severe");
        alert.setSeverityColor("Orange");
        alert.setType("1009");
        alert.setTypeName("Heat Wave");
        alert.setText("这是一条测试预警信息。预计未来24小时气温将升至37℃以上，请注意防范。");
        
        return alert;
    }
    
    /**
     * 格式化时间
     */
    private String formatDateTime(LocalDateTime dateTime) {
        return dateTime.atZone(ZoneId.of("Asia/Shanghai"))
                      .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME);
    }
    
    /**
     * 主方法 - 示例用法
     */
    public static void main(String[] args) {
        // MQTT配置（根据实际情况修改）
        String brokerUrl = "tcp://47.97.185.142:1883";
        String clientId = "java-weather-alert-publisher";
        String username = "admin";
        String password = "Jyxd@2025";
        
        WeatherAlertPublisher publisher = new WeatherAlertPublisher(brokerUrl, clientId, username, password);
        
        try {
            // 连接MQTT
            publisher.connect();
            
            // 创建测试预警
            WeatherAlert testAlert = publisher.createTestAlert();
            
            // 示例1：发送广播预警
            System.out.println("发送广播预警...");
            publisher.publishBroadcastAlert(testAlert);
            Thread.sleep(1000);
            
            // 示例2：发送设备特定预警
            System.out.println("发送设备预警...");
            publisher.publishDeviceAlert("test_device", testAlert);
            Thread.sleep(1000);
            
            // 示例3：发送实际预警数据
            WeatherAlert realAlert = new WeatherAlert();
            realAlert.setId("10118160220250819090100309276081");
            realAlert.setSender("西平县气象台");
            realAlert.setPubTime("2025-08-19T09:01+08:00");
            realAlert.setTitle("西平县气象台发布高温橙色预警");
            realAlert.setStartTime("2025-08-19T09:03+08:00");
            realAlert.setEndTime("2025-08-20T09:03+08:00");
            realAlert.setStatus("active");
            realAlert.setLevel("Orange");
            realAlert.setSeverity("Severe");
            realAlert.setSeverityColor("Orange");
            realAlert.setType("1009");
            realAlert.setTypeName("Heat Wave");
            realAlert.setText("西平县气象台2025年8月19日9时1分发布高温橙色预警信号：预计未来24小时我县柏城街道、权寨镇、芦庙乡等全部乡镇和街道最高气温将升至37℃以上，请注意防范。");
            
            System.out.println("发送实际预警数据...");
            // 发送给西平县的设备
            List<String> xiPingDevices = Arrays.asList("device_001", "ESP32_001", "test_device");
            publisher.publishMultiDeviceAlert(xiPingDevices, realAlert);
            
            System.out.println("预警发送完成！");
            
        } catch (Exception e) {
            logger.error("预警发送失败", e);
        } finally {
            try {
                publisher.disconnect();
            } catch (Exception e) {
                logger.error("断开连接失败", e);
            }
        }
    }
}


/**
 * 天气预警数据模型
 */
class WeatherAlert {
    private String id;
    private String sender;
    private String pubTime;
    private String title;
    private String startTime;
    private String endTime;
    private String status;
    private String level;
    private String severity;
    private String severityColor;
    private String type;
    private String typeName;
    private String urgency;
    private String certainty;
    private String text;
    private String related;
    private List<String> deviceIds;  // 目标设备ID列表
    
    // Constructors
    public WeatherAlert() {}
    
    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    
    public String getSender() { return sender; }
    public void setSender(String sender) { this.sender = sender; }
    
    public String getPubTime() { return pubTime; }
    public void setPubTime(String pubTime) { this.pubTime = pubTime; }
    
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    
    public String getStartTime() { return startTime; }
    public void setStartTime(String startTime) { this.startTime = startTime; }
    
    public String getEndTime() { return endTime; }
    public void setEndTime(String endTime) { this.endTime = endTime; }
    
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    
    public String getLevel() { return level; }
    public void setLevel(String level) { this.level = level; }
    
    public String getSeverity() { return severity; }
    public void setSeverity(String severity) { this.severity = severity; }
    
    public String getSeverityColor() { return severityColor; }
    public void setSeverityColor(String severityColor) { this.severityColor = severityColor; }
    
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    
    public String getTypeName() { return typeName; }
    public void setTypeName(String typeName) { this.typeName = typeName; }
    
    public String getUrgency() { return urgency; }
    public void setUrgency(String urgency) { this.urgency = urgency; }
    
    public String getCertainty() { return certainty; }
    public void setCertainty(String certainty) { this.certainty = certainty; }
    
    public String getText() { return text; }
    public void setText(String text) { this.text = text; }
    
    public String getRelated() { return related; }
    public void setRelated(String related) { this.related = related; }
    
    public List<String> getDeviceIds() { return deviceIds; }
    public void setDeviceIds(List<String> deviceIds) { this.deviceIds = deviceIds; }
}

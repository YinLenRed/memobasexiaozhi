/*
 * 小智主动问候功能 ESP32示例代码
 * 
 * 功能：
 * - 连接WiFi
 * - 连接MQTT服务器并订阅命令主题
 * - 接收SPEAK命令并回复ACK
 * - 连接WebSocket接收TTS音频
 * - 模拟播放音频并上报完成事件
 * 
 * 适用于：ESP32 Arduino开发环境
 * 依赖库：PubSubClient, WebSocketsClient, ArduinoJson
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

// WiFi配置
const char* ssid = "你的WiFi名称";
const char* password = "你的WiFi密码";

// 服务器配置
const char* mqtt_server = "47.97.185.142";
const int mqtt_port = 1883;
const char* ws_server = "172.20.12.204";
const int ws_port = 8000;

// 设备信息
String deviceId;
String clientId;

// 客户端对象
WiFiClient espClient;
PubSubClient mqttClient(espClient);
WebSocketsClient webSocket;

// 全局变量
String currentTrackId = "";
bool isPlaying = false;

void setup() {
  Serial.begin(115200);
  Serial.println("🚀 小智主动问候功能启动");
  
  // 获取设备MAC地址作为设备ID
  deviceId = WiFi.macAddress();
  deviceId.replace(":", "");  // 移除冒号，如果需要的话
  clientId = "esp32-" + String(random(100000, 999999));
  
  Serial.println("📱 设备ID: " + deviceId);
  Serial.println("🆔 客户端ID: " + clientId);
  
  // 初始化WiFi
  setupWiFi();
  
  // 初始化MQTT
  setupMQTT();
  
  // 初始化WebSocket
  setupWebSocket();
}

void loop() {
  // 保持MQTT连接
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();
  
  // 保持WebSocket连接
  webSocket.loop();
  
  // 其他业务逻辑
  delay(100);
}

void setupWiFi() {
  Serial.println("🔌 连接WiFi...");
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("");
  Serial.println("✅ WiFi连接成功");
  Serial.println("📍 IP地址: " + WiFi.localIP().toString());
}

void setupMQTT() {
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(onMqttMessage);
  
  Serial.println("📡 连接MQTT服务器...");
  reconnectMQTT();
}

void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.println("🔄 尝试MQTT连接...");
    
    if (mqttClient.connect(deviceId.c_str())) {
      Serial.println("✅ MQTT连接成功");
      
      // 订阅命令主题
      String cmdTopic = "device/" + deviceId + "/cmd";
      mqttClient.subscribe(cmdTopic.c_str());
      Serial.println("📡 订阅主题: " + cmdTopic);
      
    } else {
      Serial.print("❌ MQTT连接失败，状态码: ");
      Serial.print(mqttClient.state());
      Serial.println(" 5秒后重试...");
      delay(5000);
    }
  }
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  Serial.println("📥 收到MQTT消息");
  Serial.println("📍 主题: " + String(topic));
  
  // 转换payload为字符串
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println("📄 内容: " + message);
  
  // 解析JSON
  DynamicJsonDocument doc(1024);
  DeserializationError error = deserializeJson(doc, message);
  
  if (error) {
    Serial.println("❌ JSON解析失败: " + String(error.c_str()));
    return;
  }
  
  // 检查是否是SPEAK命令
  if (doc["cmd"] == "SPEAK") {
    String text = doc["text"];
    String trackId = doc["track_id"];
    
    Serial.println("🔊 收到SPEAK命令:");
    Serial.println("   文本: " + text);
    Serial.println("   跟踪ID: " + trackId);
    
    // 保存当前track_id
    currentTrackId = trackId;
    
    // 立即发送ACK确认
    sendAckMessage(trackId);
    
    // 模拟开始播放
    startPlaying(text);
  }
}

void sendAckMessage(String trackId) {
  String ackTopic = "device/" + deviceId + "/ack";
  
  // 构建ACK消息
  DynamicJsonDocument doc(256);
  doc["evt"] = "CMD_RECEIVED";
  doc["track_id"] = trackId;
  doc["timestamp"] = getCurrentTimestamp();
  
  String ackMessage;
  serializeJson(doc, ackMessage);
  
  // 发布ACK消息
  mqttClient.publish(ackTopic.c_str(), ackMessage.c_str());
  
  Serial.println("✅ 发送ACK确认:");
  Serial.println("   主题: " + ackTopic);
  Serial.println("   内容: " + ackMessage);
}

void sendEventMessage(String trackId, String eventType) {
  String eventTopic = "device/" + deviceId + "/event";
  
  // 构建事件消息
  DynamicJsonDocument doc(256);
  doc["evt"] = eventType;
  doc["track_id"] = trackId;
  doc["timestamp"] = getCurrentTimestamp();
  
  String eventMessage;
  serializeJson(doc, eventMessage);
  
  // 发布事件消息
  mqttClient.publish(eventTopic.c_str(), eventMessage.c_str());
  
  Serial.println("✅ 发送事件:");
  Serial.println("   主题: " + eventTopic);
  Serial.println("   内容: " + eventMessage);
}

void setupWebSocket() {
  String wsPath = "/xiaozhi/v1/?device-id=" + deviceId + "&client-id=" + clientId;
  
  Serial.println("🌐 连接WebSocket...");
  Serial.println("📍 服务器: " + String(ws_server) + ":" + String(ws_port));
  Serial.println("📄 路径: " + wsPath);
  
  webSocket.begin(ws_server, ws_port, wsPath);
  webSocket.onEvent(onWebSocketEvent);
  webSocket.setReconnectInterval(5000);
}

void onWebSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.println("❌ WebSocket断开连接");
      break;
      
    case WStype_CONNECTED:
      Serial.println("✅ WebSocket连接成功");
      Serial.println("📍 服务器地址: " + webSocket.remoteIP(0).toString());
      break;
      
    case WStype_TEXT:
      Serial.println("📥 WebSocket文本消息: " + String((char*)payload));
      break;
      
    case WStype_BIN:
      Serial.println("📥 WebSocket二进制消息，长度: " + String(length));
      // 这里可以处理TTS音频数据
      handleAudioData(payload, length);
      break;
      
    case WStype_ERROR:
      Serial.println("❌ WebSocket错误");
      break;
      
    default:
      break;
  }
}

void handleAudioData(uint8_t* data, size_t length) {
  Serial.println("🎵 处理音频数据: " + String(length) + " 字节");
  
  // 这里添加实际的音频播放代码
  // 例如：通过I2S、DAC或外部音频芯片播放
  
  // 模拟播放延时
  delay(2000);
  
  // 播放完成，发送事件
  if (currentTrackId != "") {
    sendEventMessage(currentTrackId, "EVT_SPEAK_DONE");
    isPlaying = false;
    Serial.println("🎵 音频播放完成");
  }
}

void startPlaying(String text) {
  Serial.println("🎵 开始播放: " + text);
  isPlaying = true;
  
  // 这里可以添加实际的播放逻辑
  // 如果没有收到WebSocket音频数据，可以模拟播放完成
  
  // 模拟情况：3秒后自动完成
  // 在实际应用中，应该等待真实的音频播放完成
}

String getCurrentTimestamp() {
  // 简单的时间戳格式 HH:MM:SS
  // 在实际应用中，建议使用RTC或NTP获取准确时间
  unsigned long now = millis();
  int seconds = (now / 1000) % 60;
  int minutes = (now / 60000) % 60;
  int hours = (now / 3600000) % 24;
  
  char timestamp[9];
  sprintf(timestamp, "%02d:%02d:%02d", hours, minutes, seconds);
  return String(timestamp);
}

// 辅助函数：打印调试信息
void printStatus() {
  Serial.println("📊 系统状态:");
  Serial.println("   WiFi: " + String(WiFi.status() == WL_CONNECTED ? "✅ 已连接" : "❌ 断开"));
  Serial.println("   MQTT: " + String(mqttClient.connected() ? "✅ 已连接" : "❌ 断开"));
  Serial.println("   WebSocket: " + String(webSocket.isConnected() ? "✅ 已连接" : "❌ 断开"));
  Serial.println("   播放状态: " + String(isPlaying ? "🎵 播放中" : "⏸️ 空闲"));
}

/*
 * 使用说明：
 * 
 * 1. 安装必要的库：
 *    - PubSubClient (by Nick O'Leary)
 *    - WebSocketsClient (by Markus Sattler) 
 *    - ArduinoJson (by Benoit Blanchon)
 * 
 * 2. 修改WiFi配置：
 *    - 设置正确的ssid和password
 * 
 * 3. 根据需要调整设备ID格式：
 *    - 当前使用MAC地址
 *    - 可以改为固定ID或其他格式
 * 
 * 4. 添加实际的音频播放代码：
 *    - 替换handleAudioData()中的模拟播放
 *    - 添加I2S、DAC或外部音频芯片支持
 * 
 * 5. 测试步骤：
 *    - 上传代码到ESP32
 *    - 打开串口监视器查看连接状态
 *    - 运行Python测试脚本验证功能
 * 
 * 6. 调试技巧：
 *    - 观察串口输出的连接状态
 *    - 使用MQTT客户端工具手动发送命令测试
 *    - 检查WebSocket连接参数是否正确
 */

# 🔧 WebSocket握手问题调试指南

## ❌ 当前错误
```
EOFError: line without CRLF
connection closed while reading HTTP request line  
did not receive a valid HTTP request
```

## 🔍 问题分析

### 1. HTTP请求格式错误
硬件发送的WebSocket握手请求可能缺少正确的CRLF结尾符。

### 2. 常见硬件端问题

#### ❌ 错误的实现
```cpp
// 可能的问题代码
String request = "GET /xiaozhi/v1/ HTTP/1.1\n";  // ❌ 只有\n
request += "Host: 47.98.51.180\n";              // ❌ 缺少\r
client.print(request);
```

#### ✅ 正确的实现
```cpp
// 正确的WebSocket握手请求
String request = "GET /xiaozhi/v1/ HTTP/1.1\r\n";
request += "Host: 47.98.51.180\r\n";
request += "Upgrade: websocket\r\n";
request += "Connection: Upgrade\r\n"; 
request += "Sec-WebSocket-Key: " + generateKey() + "\r\n";
request += "Sec-WebSocket-Version: 13\r\n";
request += "\r\n";  // 重要：空行结束
client.print(request);
```

## 🛠️ 解决方案

### 方案1：修正硬件WebSocket客户端

#### 检查点1：确保正确的CRLF
```cpp
// 每个HTTP头部行必须以\r\n结尾
void sendWebSocketRequest() {
    client.print("GET /xiaozhi/v1/ HTTP/1.1\r\n");
    client.print("Host: 47.98.51.180\r\n");
    client.print("Upgrade: websocket\r\n");
    client.print("Connection: Upgrade\r\n");
    client.print("Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n");
    client.print("Sec-WebSocket-Version: 13\r\n");
    client.print("\r\n");  // 空行表示头部结束
}
```

#### 检查点2：使用可靠的WebSocket库
```cpp
// 推荐使用成熟的WebSocket库
#include <WebSocketsClient.h>

WebSocketsClient webSocket;

void connectWebSocket() {
    webSocket.begin("47.98.51.180", 8000, "/xiaozhi/v1/");
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(5000);
}
```

#### 检查点3：添加错误处理
```cpp
void connectWebSocket() {
    if (!client.connect("47.98.51.180", 8000)) {
        Serial.println("❌ TCP连接失败");
        return;
    }
    
    Serial.println("✅ TCP连接成功，发送WebSocket握手");
    sendWebSocketRequest();
    
    // 等待握手响应
    unsigned long timeout = millis() + 5000;
    while (millis() < timeout) {
        if (client.available()) {
            String response = client.readString();
            if (response.indexOf("101 Switching Protocols") > 0) {
                Serial.println("✅ WebSocket握手成功");
                return;
            }
        }
        delay(10);
    }
    Serial.println("❌ WebSocket握手超时");
}
```

### 方案2：使用标准WebSocket库

#### Arduino WebSocket库推荐
```cpp
// 1. ArduinoWebsockets库 (推荐)
#include <ArduinoWebsockets.h>
using namespace websockets;

WebsocketsClient client;

void setup() {
    client.connect("ws://47.98.51.180:8000/xiaozhi/v1/");
}

// 2. WebSocketsClient库
#include <WebSocketsClient.h>

WebSocketsClient webSocket;

void setup() {
    webSocket.begin("47.98.51.180", 8000, "/xiaozhi/v1/");
    webSocket.onEvent(webSocketEvent);
}
```

## 🧪 调试步骤

### 1. 启用详细日志
```cpp
void debugWebSocketConnection() {
    Serial.println("🔧 开始WebSocket连接调试");
    
    // 1. 测试TCP连接
    if (client.connect("47.98.51.180", 8000)) {
        Serial.println("✅ TCP连接成功");
    } else {
        Serial.println("❌ TCP连接失败");
        return;
    }
    
    // 2. 发送握手请求
    Serial.println("📤 发送WebSocket握手请求");
    client.print("GET /xiaozhi/v1/ HTTP/1.1\r\n");
    client.print("Host: 47.98.51.180\r\n");
    client.print("Upgrade: websocket\r\n");
    client.print("Connection: Upgrade\r\n");
    client.print("Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n");
    client.print("Sec-WebSocket-Version: 13\r\n");
    client.print("\r\n");
    
    // 3. 读取服务器响应
    delay(1000);
    if (client.available()) {
        String response = client.readString();
        Serial.println("📥 服务器响应:");
        Serial.println(response);
    }
}
```

### 2. 检查网络稳定性
```cpp
void testNetworkStability() {
    for (int i = 0; i < 5; i++) {
        Serial.printf("🔧 测试连接 %d/5\n", i+1);
        
        if (client.connect("47.98.51.180", 8000)) {
            Serial.println("✅ 连接成功");
            client.stop();
            delay(1000);
        } else {
            Serial.println("❌ 连接失败");
        }
    }
}
```

## 💡 最佳实践

### 1. 使用成熟的WebSocket库
- 避免手动实现WebSocket协议
- 选择经过验证的开源库

### 2. 添加重连机制
```cpp
void connectWithRetry() {
    int attempts = 0;
    while (attempts < 3) {
        if (webSocket.connect("ws://47.98.51.180:8000/xiaozhi/v1/")) {
            Serial.println("✅ WebSocket连接成功");
            return;
        }
        attempts++;
        Serial.printf("❌ 连接失败，重试 %d/3\n", attempts);
        delay(2000);
    }
    Serial.println("❌ WebSocket连接最终失败");
}
```

### 3. 设置合适的超时
```cpp
webSocket.setReconnectInterval(5000);
webSocket.enableHeartbeat(15000, 3000, 2);
```

## 🎯 检查清单

- [ ] HTTP请求行以\r\n结尾
- [ ] 所有头部字段格式正确
- [ ] 请求以空行(\r\n)结束
- [ ] 使用标准WebSocket库
- [ ] 添加错误处理和重连
- [ ] 测试网络连接稳定性
- [ ] 检查服务器地址和端口
- [ ] 验证WebSocket路径正确

## 🚀 验证测试

使用修正后的代码重新测试：
```bash
python flexible_test.py f0:9e:9e:04:8a:44 --mode production
```

预期看到稳定的WebSocket连接，无握手错误。

# 🧪 WebSocket连接测试指南

## 🎯 **测试目标**

根据启动日志，WebSocket服务地址为：
```
ws://172.20.12.204:8000/xiaozhi/v1/
```

## 📋 **测试方法汇总**

### 🚀 **方法1：浏览器测试 (推荐，最简单)**

1. **打开浏览器开发者工具** (F12)
2. **切换到控制台** (Console标签)
3. **复制并执行以下代码**：

```javascript
const ws = new WebSocket('ws://172.20.12.204:8000/xiaozhi/v1/');

ws.onopen = function(event) {
    console.log('✅ WebSocket连接成功!');
    console.log('连接状态:', ws.readyState);
    
    // 发送测试消息
    ws.send(JSON.stringify({
        type: 'test',
        message: 'browser test',
        timestamp: new Date().toISOString()
    }));
};

ws.onmessage = function(event) {
    console.log('📥 收到消息:', event.data);
};

ws.onerror = function(error) {
    console.log('❌ WebSocket错误:', error);
};

ws.onclose = function(event) {
    console.log('🔌 连接关闭:', event.code, event.reason);
};
```

4. **观察控制台输出**：
   - ✅ 如果看到"WebSocket连接成功" → 说明服务正常
   - ❌ 如果看到连接错误 → 说明网络或服务有问题

### 🖥️ **方法2：HTML测试页面**

运行以下命令创建测试页面：
```bash
python test_websocket_local.py
```

然后在浏览器中打开生成的 `websocket_test.html` 文件。

### 🐧 **方法3：服务器端测试**

**在服务器上执行**（SSH登录到172.20.12.204）：

```bash
# 1. 检查端口监听
ss -tlnp | grep :8000
# 或者
netstat -tlnp | grep :8000

# 2. 测试本地连接
python test_websocket_local.py

# 3. 使用curl测试WebSocket握手
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: test" \
  -H "Sec-WebSocket-Version: 13" \
  http://localhost:8000/xiaozhi/v1/
```

### 📱 **方法4：移动端测试**

如果有移动设备在同一网络：

```javascript
// 在移动浏览器控制台执行
const ws = new WebSocket('ws://172.20.12.204:8000/xiaozhi/v1/');
// ... (相同的事件处理代码)
```

## 🔍 **结果判断**

### ✅ **连接成功的标志**
- 浏览器控制台显示：`✅ WebSocket连接成功!`
- WebSocket状态：`readyState: 1` (OPEN)
- 能够发送和接收消息
- 无错误信息

### ❌ **连接失败的原因**

#### **1. 网络问题**
```
Error: Connection refused
Error: Network unreachable
```
**解决方案**：
- 检查网络连接
- 确认能ping通172.20.12.204
- 检查防火墙设置

#### **2. 服务未启动**
```
Error: Connection refused (port 8000)
```
**解决方案**：
- 确认小智服务正在运行
- 检查端口8000是否监听
- 查看服务启动日志

#### **3. 路径错误**
```
Error: 404 Not Found
```
**解决方案**：
- 确认路径为 `/xiaozhi/v1/`
- 检查服务器路由配置

#### **4. 协议错误**
```
Error: Invalid handshake response
```
**解决方案**：
- 确认使用 `ws://` 而不是 `http://`
- 检查WebSocket版本支持

## 🛠️ **故障排查步骤**

### **Step 1: 基础连接测试**
```bash
# 测试TCP连接
telnet 172.20.12.204 8000
```

### **Step 2: HTTP响应测试**
```bash
# 测试HTTP响应
curl -v http://172.20.12.204:8000/
```

### **Step 3: 检查服务状态**
```bash
# 在服务器上检查
ps aux | grep app.py
ss -tlnp | grep :8000
```

### **Step 4: 查看服务日志**
```bash
# 查看WebSocket相关日志
tail -f logs/app.log | grep -i websocket
```

## 💡 **常见问题解答**

### **Q: 浏览器显示"连接被拒绝"**
**A:** 检查网络连接和服务器状态，确认能访问172.20.12.204:8000

### **Q: 连接成功但收不到消息**
**A:** 这是正常的，WebSocket主要用于双向通信，测试连接成功即可

### **Q: 移动设备无法连接**
**A:** 确认移动设备和服务器在同一网络，检查WiFi设置

### **Q: 代理环境下连接失败**
**A:** 配置代理支持WebSocket，或在无代理环境下测试

## 🎯 **测试成功标准**

满足以下任一条件即表示WebSocket修复成功：

1. ✅ **浏览器测试成功** - 控制台显示连接成功
2. ✅ **HTML页面测试成功** - 页面显示连接状态为成功
3. ✅ **服务器本地测试成功** - 本地localhost连接正常
4. ✅ **客户端应用连接成功** - 实际设备能够正常连接

## 📞 **获取帮助**

如果所有测试都失败，请提供：

1. **浏览器测试的完整控制台输出**
2. **服务器的详细日志信息**
3. **网络环境描述**（是否有代理、防火墙等）
4. **具体的错误信息截图**

---

**🎉 开始测试WebSocket连接吧！**

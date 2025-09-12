#!/usr/bin/env python3
"""
聆听超时机制测试脚本
用于验证强化后的超时机制是否正常工作
"""

import asyncio
import websockets
import json
import time
from datetime import datetime

class TimeoutTestClient:
    def __init__(self, server_url="ws://localhost:8080"):
        self.server_url = server_url
        self.websocket = None
        self.session_id = f"test-{int(time.time())}"
        
    async def connect(self):
        """连接到服务器"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print(f"✅ 已连接到服务器: {self.server_url}")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    async def send_hello(self):
        """发送hello消息建立会话"""
        hello_message = {
            "type": "hello",
            "session_id": self.session_id,
            "timestamp": int(time.time() * 1000)
        }
        
        await self.websocket.send(json.dumps(hello_message))
        print(f"📤 发送hello消息: {hello_message}")
        
        # 等待响应
        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            print(f"📥 收到响应: {response}")
        except asyncio.TimeoutError:
            print("⚠️ hello响应超时")
    
    async def start_listening(self):
        """开始聆听（模拟按键）"""
        listen_message = {
            "type": "listen",
            "state": "start",
            "mode": "manual",
            "session_id": self.session_id,
            "timestamp": int(time.time() * 1000)
        }
        
        await self.websocket.send(json.dumps(listen_message))
        print(f"🎤 开始聆听: {datetime.now().strftime('%H:%M:%S')}")
        print(f"📤 发送消息: {listen_message}")
    
    async def listen_for_messages(self, duration=10):
        """监听服务器消息"""
        print(f"👂 开始监听服务器消息，持续 {duration} 秒...")
        start_time = time.time()
        
        timeout_detected = False
        
        try:
            while time.time() - start_time < duration:
                try:
                    # 设置短超时，避免阻塞太久
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    print(f"📥 [{timestamp}] 收到消息: {message}")
                    
                    # 解析消息检查是否是超时停止信号
                    try:
                        msg_json = json.loads(message)
                        if (msg_json.get("type") == "listening" and 
                            msg_json.get("state") == "stop"):
                            
                            reason = msg_json.get("reason", "unknown")
                            force = msg_json.get("force", False)
                            
                            if reason == "timeout":
                                print(f"🎯 检测到超时停止信号 (reason=timeout)")
                                timeout_detected = True
                            elif force:
                                print(f"🎯 检测到强制停止信号 (force=true)")
                                timeout_detected = True
                            else:
                                print(f"🎯 检测到其他停止信号: {msg_json}")
                        
                        elif msg_json.get("type") == "abort":
                            print(f"🎯 检测到abort信号: {msg_json}")
                            timeout_detected = True
                            
                    except json.JSONDecodeError:
                        pass
                        
                except asyncio.TimeoutError:
                    # 正常的接收超时，继续监听
                    elapsed = time.time() - start_time
                    print(f"⏰ 已等待 {elapsed:.1f} 秒...")
                    continue
                    
        except Exception as e:
            print(f"❌ 监听消息时出错: {e}")
        
        return timeout_detected
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 已断开连接")

async def test_timeout_mechanism():
    """测试聆听超时机制"""
    print("🧪 开始测试聆听超时机制")
    print("=" * 50)
    
    client = TimeoutTestClient()
    
    try:
        # 1. 连接到服务器
        if not await client.connect():
            return False
        
        # 2. 发送hello建立会话
        await client.send_hello()
        await asyncio.sleep(1)
        
        # 3. 开始聆听
        await client.start_listening()
        
        print(f"\n⏳ 等待超时机制触发...")
        print(f"   预期5秒后收到超时停止信号")
        print(f"   实际超时配置请查看config.yaml中的listening_timeout设置")
        
        # 4. 监听消息，等待超时信号
        timeout_detected = await client.listen_for_messages(duration=15)
        
        # 5. 结果评估
        print("\n" + "=" * 50)
        if timeout_detected:
            print("✅ 测试成功：检测到超时停止信号")
            print("   硬件端应该已收到停止聆听的信号")
            print("   如果硬件屏幕仍显示聆听状态，说明硬件端处理有问题")
        else:
            print("❌ 测试失败：未检测到超时停止信号")
            print("   可能的原因：")
            print("   1. 超时机制没有触发")
            print("   2. 超时时间设置过长")
            print("   3. 按键立即发送了stop信号取消了超时")
        
        return timeout_detected
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False
    
    finally:
        await client.disconnect()

async def test_multiple_signals():
    """测试多重信号发送"""
    print("\n🔄 测试多重信号发送机制")
    print("=" * 50)
    
    client = TimeoutTestClient()
    signal_count = 0
    
    try:
        if not await client.connect():
            return False
        
        await client.send_hello()
        await asyncio.sleep(1)
        
        await client.start_listening()
        
        print(f"📊 统计接收到的停止信号数量...")
        start_time = time.time()
        
        while time.time() - start_time < 12:
            try:
                message = await asyncio.wait_for(client.websocket.recv(), timeout=1.0)
                
                try:
                    msg_json = json.loads(message)
                    if ((msg_json.get("type") == "listening" and msg_json.get("state") == "stop") or
                        msg_json.get("type") == "abort"):
                        signal_count += 1
                        signal_type = "abort" if msg_json.get("type") == "abort" else "listening-stop"
                        print(f"📡 收到停止信号 #{signal_count}: {signal_type}")
                        
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                continue
        
        print(f"\n📊 测试结果：共收到 {signal_count} 个停止信号")
        if signal_count >= 3:
            print("✅ 多重信号机制工作正常")
        elif signal_count > 0:
            print("⚠️ 收到部分信号，可能存在通信问题")
        else:
            print("❌ 未收到任何停止信号")
            
        return signal_count > 0
        
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        return False
    
    finally:
        await client.disconnect()

if __name__ == "__main__":
    print("🎤 聆听超时机制测试工具")
    print("用于验证修复后的超时机制是否正常工作")
    print("请确保xiaozhi服务正在运行 (python app.py)")
    print()
    
    async def main():
        # 测试基本超时机制
        success1 = await test_timeout_mechanism()
        
        await asyncio.sleep(2)
        
        # 测试多重信号机制
        success2 = await test_multiple_signals()
        
        print("\n🏁 测试总结")
        print("=" * 50)
        if success1 and success2:
            print("✅ 所有测试通过！超时机制工作正常")
        elif success1:
            print("⚠️ 基本超时机制工作，但多重信号可能有问题")
        else:
            print("❌ 超时机制存在问题，需要进一步检查")
            
        print("\n🔧 如果测试失败，请检查：")
        print("1. xiaozhi服务是否正在运行")
        print("2. config.yaml中的listening_timeout配置")
        print("3. 查看服务端日志中的超时相关信息")
        print("4. 确认WebSocket连接正常")
    
    asyncio.run(main())

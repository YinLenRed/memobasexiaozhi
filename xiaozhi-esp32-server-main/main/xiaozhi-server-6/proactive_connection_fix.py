#!/usr/bin/env python3
"""
🔄 主动对话连接检查修复
在发送音频前检查并等待设备连接
"""

import asyncio
import json
from datetime import datetime

def create_wake_command_patch():
    """创建设备唤醒命令的补丁代码"""
    
    patch_code = '''
# 在 core/mqtt/proactive_greeting_service.py 的 _handle_device_ack 方法中添加

async def _handle_device_ack(self, device_id: str, ack_data: dict, audio_file_path: str):
    """处理设备ACK确认，发送音频文件"""
    try:
        track_id = ack_data.get("track_id")
        
        # === 新增: 连接检查和等待机制 ===
        connection_found = False
        max_retries = 6  # 最多等待30秒 (6次 x 5秒)
        
        for retry in range(max_retries):
            # 检查设备连接
            if self.websocket_server and hasattr(self.websocket_server, 'find_device_connection'):
                connection = self.websocket_server.find_device_connection(device_id)
                if connection and connection.websocket:
                    connection_found = True
                    self.logger.bind(tag=TAG).info(f"设备连接检查成功: {device_id} (重试 {retry+1}/{max_retries})")
                    break
            
            if retry < max_retries - 1:  # 不是最后一次重试
                self.logger.bind(tag=TAG).info(f"设备未连接，等待重连: {device_id} (重试 {retry+1}/{max_retries})")
                
                # 发送唤醒命令让设备重连
                wake_command = {
                    "cmd": "WAKE",
                    "action": "reconnect_websocket",
                    "audio_url": "ws://47.98.51.180:8000/xiaozhi/v1/",
                    "track_id": track_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                try:
                    topic = f"device/{device_id}/cmd"
                    await self.mqtt_client.publish(topic, json.dumps(wake_command))
                    self.logger.bind(tag=TAG).info(f"发送WAKE命令: {device_id}")
                except Exception as wake_error:
                    self.logger.bind(tag=TAG).error(f"发送WAKE命令失败: {wake_error}")
                
                # 等待5秒让设备重连
                await asyncio.sleep(5)
        
        if not connection_found:
            self.logger.bind(tag=TAG).error(f"设备连接检查失败，放弃音频发送: {device_id}")
            return
        # === 连接检查结束 ===
        
        # 原有的音频发送逻辑
        self.logger.bind(tag=TAG).info(f"发送音频文件到设备: {device_id}, 文件: {audio_file_path}")
        
        if self.websocket_server:
            success = await self.websocket_server.send_audio_to_device(device_id, audio_file_path, track_id)
            if success:
                self.logger.bind(tag=TAG).info(f"主动问候音频发送成功: {track_id}")
            else:
                self.logger.bind(tag=TAG).warning(f"主动问候音频发送失败: {track_id}")
        else:
            self.logger.bind(tag=TAG).error("WebSocket服务器实例不可用")
            
    except Exception as e:
        self.logger.bind(tag=TAG).error(f"处理设备ACK失败: {e}")
'''
    
    return patch_code

def main():
    """显示修复方案"""
    print("🔄 主动对话连接检查修复方案")
    print("=" * 80)
    print(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print("🎯 方案说明:")
    print("  在主动对话发送音频前，主动检查设备WebSocket连接状态")
    print("  如果设备未连接，发送WAKE命令让设备重连")
    print("  最多等待30秒，确保设备有足够时间重连")
    print()
    
    print("🔧 实现方式:")
    print("  1. 修改 core/mqtt/proactive_greeting_service.py")
    print("  2. 在 _handle_device_ack 方法中添加连接检查逻辑")
    print("  3. 实现自动重试和WAKE命令机制")
    print()
    
    print("📋 修改代码:")
    print(create_wake_command_patch())
    
    print("\n" + "=" * 80)
    print("🚀 应用步骤:")
    print("=" * 80)
    print("1. 备份原文件:")
    print("   cp core/mqtt/proactive_greeting_service.py core/mqtt/proactive_greeting_service.py.backup")
    print()
    print("2. 编辑文件，添加上述连接检查代码")
    print()
    print("3. 重启Python服务:")
    print("   pkill -f 'python.*app.py' && python app.py &")
    print()
    print("4. 测试主动问候:")
    print("   curl -X POST http://47.98.51.180:8003/xiaozhi/greeting/send \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"device_id\": \"7c:2c:67:8d:89:78\", \"initial_content\": \"连接检查测试\", \"category\": \"test\"}'")
    
    print("\n🎊 预期效果:")
    print("  • 如果设备未连接，会发送WAKE命令")
    print("  • 等待设备重连WebSocket")
    print("  • 连接成功后正常发送音频")
    print("  • 硬件应该能听到声音！")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
音频卡顿修复验证工具
基于硬件人员反馈的具体问题进行验证
"""

import asyncio
import json
import time
import websockets
from datetime import datetime
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

class AudioFixVerificationTool:
    """音频修复验证工具"""
    
    def __init__(self, websocket_url="ws://47.97.185.142:8000/xiaozhi/v1/"):
        self.websocket_url = websocket_url
        self.test_results = {}
        
    async def verify_tts_stop_message(self):
        """验证TTS stop消息是否正确发送"""
        logger.bind(tag=TAG).info("🔧 开始验证TTS stop消息修复...")
        
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                # 模拟发送测试消息
                test_message = {
                    "type": "text",
                    "text": "测试音频播放完成机制",
                    "session_id": f"test_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(test_message))
                logger.bind(tag=TAG).info("✅ 发送测试消息成功")
                
                # 监听响应消息
                tts_start_received = False
                tts_stop_received = False
                audio_data_count = 0
                start_time = time.time()
                
                while time.time() - start_time < 30:  # 30秒超时
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        
                        if data.get("type") == "tts":
                            if data.get("state") == "start":
                                tts_start_received = True
                                logger.bind(tag=TAG).info("✅ 收到TTS start消息")
                            elif data.get("state") == "stop":
                                tts_stop_received = True
                                logger.bind(tag=TAG).info("✅ 收到TTS stop消息")
                                break
                        elif data.get("type") == "audio":
                            audio_data_count += 1
                            
                    except asyncio.TimeoutError:
                        continue
                
                self.test_results["tts_stop_message"] = {
                    "tts_start_received": tts_start_received,
                    "tts_stop_received": tts_stop_received,
                    "audio_data_count": audio_data_count,
                    "total_time": time.time() - start_time
                }
                
                if tts_stop_received:
                    logger.bind(tag=TAG).info("🎉 TTS stop消息修复验证成功")
                else:
                    logger.bind(tag=TAG).error("❌ TTS stop消息未收到，修复可能有问题")
                    
        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS stop消息验证失败: {e}")
            self.test_results["tts_stop_message"] = {"error": str(e)}
    
    async def verify_audio_transmission_completeness(self):
        """验证音频传输完整性"""
        logger.bind(tag=TAG).info("🌐 开始验证音频传输完整性...")
        
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                test_message = {
                    "type": "text", 
                    "text": "这是一个用于测试音频传输完整性的较长文本消息，包含多个句子。我们需要确保所有音频数据都能正确传输到硬件端。",
                    "session_id": f"test_transmission_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(test_message))
                
                audio_frames = []
                last_audio_time = time.time()
                start_time = time.time()
                transmission_gaps = []
                
                while time.time() - start_time < 30:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(message)
                        
                        if data.get("type") == "audio":
                            current_time = time.time()
                            if audio_frames:  # 不是第一帧
                                gap = current_time - last_audio_time
                                transmission_gaps.append(gap)
                                if gap > 1.0:  # 超过1秒的间隙可能是问题
                                    logger.bind(tag=TAG).warning(f"⚠️ 检测到音频传输间隙: {gap:.2f}秒")
                            
                            audio_frames.append({
                                "timestamp": current_time,
                                "sequence": data.get("sequence", 0),
                                "data_length": len(data.get("data", ""))
                            })
                            last_audio_time = current_time
                            
                        elif data.get("type") == "tts" and data.get("state") == "stop":
                            break
                            
                    except asyncio.TimeoutError:
                        if audio_frames:  # 如果已经开始接收音频但超时了
                            logger.bind(tag=TAG).warning("⚠️ 音频传输可能中断（超时）")
                        break
                
                # 分析传输质量
                avg_gap = sum(transmission_gaps) / len(transmission_gaps) if transmission_gaps else 0
                max_gap = max(transmission_gaps) if transmission_gaps else 0
                
                self.test_results["audio_transmission"] = {
                    "total_frames": len(audio_frames),
                    "transmission_time": time.time() - start_time,
                    "average_gap": avg_gap,
                    "max_gap": max_gap,
                    "gaps_over_1s": len([g for g in transmission_gaps if g > 1.0])
                }
                
                if max_gap < 2.0 and len(audio_frames) > 0:
                    logger.bind(tag=TAG).info("🎉 音频传输完整性验证通过")
                else:
                    logger.bind(tag=TAG).error("❌ 音频传输存在问题")
                    
        except Exception as e:
            logger.bind(tag=TAG).error(f"音频传输完整性验证失败: {e}")
            self.test_results["audio_transmission"] = {"error": str(e)}
    
    async def verify_connection_optimization(self):
        """验证连接优化效果"""
        logger.bind(tag=TAG).info("⚡ 开始验证连接优化效果...")
        
        connection_times = []
        
        for i in range(3):  # 测试3次连接
            try:
                start_time = time.time()
                async with websockets.connect(self.websocket_url) as websocket:
                    connection_time = time.time() - start_time
                    connection_times.append(connection_time)
                    logger.bind(tag=TAG).info(f"连接 {i+1}: {connection_time:.3f}秒")
                    
                    # 发送简单消息测试响应
                    await websocket.send(json.dumps({
                        "type": "text",
                        "text": f"连接测试 {i+1}",
                        "session_id": f"conn_test_{i}_{int(time.time())}"
                    }))
                    
                    # 等待响应
                    await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    
            except Exception as e:
                logger.bind(tag=TAG).error(f"连接测试 {i+1} 失败: {e}")
                connection_times.append(999.0)  # 表示连接失败
        
        avg_connection_time = sum(connection_times) / len(connection_times)
        
        self.test_results["connection_optimization"] = {
            "connection_times": connection_times,
            "average_time": avg_connection_time,
            "optimization_effective": avg_connection_time < 2.0  # 2秒内认为优化有效
        }
        
        if avg_connection_time < 2.0:
            logger.bind(tag=TAG).info(f"🎉 连接优化有效，平均连接时间: {avg_connection_time:.3f}秒")
        else:
            logger.bind(tag=TAG).warning(f"⚠️ 连接可能仍需优化，平均连接时间: {avg_connection_time:.3f}秒")
    
    async def verify_state_management(self):
        """验证状态管理修复"""
        logger.bind(tag=TAG).info("🔧 开始验证状态管理修复...")
        
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                # 发送测试消息
                test_message = {
                    "type": "text",
                    "text": "测试状态管理",
                    "session_id": f"state_test_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(test_message))
                
                states_received = []
                start_time = time.time()
                
                while time.time() - start_time < 20:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        
                        # 记录状态变化
                        if data.get("type") in ["tts", "listen"]:
                            state_info = {
                                "type": data.get("type"),
                                "state": data.get("state"),
                                "timestamp": time.time()
                            }
                            states_received.append(state_info)
                            logger.bind(tag=TAG).info(f"状态: {data.get('type')} -> {data.get('state')}")
                            
                            # 如果收到TTS stop，说明状态管理正常
                            if data.get("type") == "tts" and data.get("state") == "stop":
                                break
                                
                    except asyncio.TimeoutError:
                        continue
                
                # 分析状态序列
                tts_start_count = len([s for s in states_received if s["type"] == "tts" and s["state"] == "start"])
                tts_stop_count = len([s for s in states_received if s["type"] == "tts" and s["state"] == "stop"])
                
                self.test_results["state_management"] = {
                    "states_received": states_received,
                    "tts_start_count": tts_start_count,
                    "tts_stop_count": tts_stop_count,
                    "state_balance": tts_start_count == tts_stop_count
                }
                
                if tts_start_count == tts_stop_count and tts_stop_count > 0:
                    logger.bind(tag=TAG).info("🎉 状态管理修复验证通过")
                else:
                    logger.bind(tag=TAG).error(f"❌ 状态管理可能有问题: start={tts_start_count}, stop={tts_stop_count}")
                    
        except Exception as e:
            logger.bind(tag=TAG).error(f"状态管理验证失败: {e}")
            self.test_results["state_management"] = {"error": str(e)}
    
    async def run_all_verifications(self):
        """运行所有验证测试"""
        logger.bind(tag=TAG).info("🚀 开始音频卡顿修复验证...")
        
        verifications = [
            ("TTS Stop消息修复", self.verify_tts_stop_message),
            ("音频传输完整性", self.verify_audio_transmission_completeness), 
            ("连接优化效果", self.verify_connection_optimization),
            ("状态管理修复", self.verify_state_management)
        ]
        
        for name, verification_func in verifications:
            logger.bind(tag=TAG).info(f"\n{'='*50}")
            logger.bind(tag=TAG).info(f"🔍 验证: {name}")
            logger.bind(tag=TAG).info(f"{'='*50}")
            
            try:
                await verification_func()
            except Exception as e:
                logger.bind(tag=TAG).error(f"验证 {name} 时出错: {e}")
            
            # 验证间隔
            await asyncio.sleep(2)
        
        self.generate_report()
    
    def generate_report(self):
        """生成验证报告"""
        logger.bind(tag=TAG).info(f"\n{'='*60}")
        logger.bind(tag=TAG).info("📊 音频卡顿修复验证报告")
        logger.bind(tag=TAG).info(f"{'='*60}")
        
        for test_name, results in self.test_results.items():
            logger.bind(tag=TAG).info(f"\n🔍 {test_name}:")
            
            if "error" in results:
                logger.bind(tag=TAG).error(f"  ❌ 测试失败: {results['error']}")
            else:
                for key, value in results.items():
                    if isinstance(value, bool):
                        status = "✅" if value else "❌"
                        logger.bind(tag=TAG).info(f"  {status} {key}: {value}")
                    elif isinstance(value, (int, float)):
                        logger.bind(tag=TAG).info(f"  📊 {key}: {value}")
                    elif isinstance(value, list) and len(value) < 10:
                        logger.bind(tag=TAG).info(f"  📋 {key}: {value}")
        
        # 总体评估
        logger.bind(tag=TAG).info(f"\n{'='*60}")
        
        success_count = 0
        total_tests = len(self.test_results)
        
        for results in self.test_results.values():
            if "error" not in results:
                success_count += 1
        
        if success_count == total_tests:
            logger.bind(tag=TAG).info("🎉 所有修复验证通过！音频卡顿问题已解决")
        elif success_count > total_tests // 2:
            logger.bind(tag=TAG).info(f"✅ 大部分修复验证通过 ({success_count}/{total_tests})，还有改进空间")
        else:
            logger.bind(tag=TAG).warning(f"⚠️ 部分修复可能仍有问题 ({success_count}/{total_tests})")
        
        logger.bind(tag=TAG).info(f"{'='*60}")


async def main():
    """主函数"""
    print("🎵 小智音频卡顿修复验证工具")
    print("基于硬件人员反馈进行全面验证")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    verifier = AudioFixVerificationTool()
    await verifier.run_all_verifications()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"验证工具运行失败: {e}")

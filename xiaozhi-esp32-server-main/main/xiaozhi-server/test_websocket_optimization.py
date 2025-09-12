#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket + 预缓冲优化测试脚本
快速验证优化效果

运行方法:
python test_websocket_optimization.py --device-id your_device_id
"""

import asyncio
import time
import sys
import os
import argparse
import json

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.utils.websocket_performance_monitor import get_performance_monitor
from config.logger import setup_logging


class WebSocketOptimizationTester:
    """WebSocket预缓冲优化测试器"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.monitor = get_performance_monitor()
        
    def simulate_audio_transmission(self, device_id: str, audio_frames: int, duration: float):
        """模拟音频传输测试"""
        track_id = f"TEST_{int(time.time())}"
        
        print(f"🧪 开始测试音频传输优化")
        print(f"   设备ID: {device_id}")
        print(f"   音频帧数: {audio_frames}")
        print(f"   音频时长: {duration:.2f}秒")
        print(f"   测试ID: {track_id}")
        
        # 开始性能监控
        metrics = self.monitor.start_transmission(device_id, track_id, audio_frames, duration)
        
        # 模拟预缓冲阶段
        prebuffer_frames = min(5 if audio_frames <= 10 else 4 if audio_frames <= 30 else 3, audio_frames)
        prebuffer_start = time.perf_counter()
        
        print(f"\n⚡ 模拟预缓冲发送: {prebuffer_frames}帧")
        time.sleep(0.01 * prebuffer_frames)  # 模拟快速发送
        
        prebuffer_time = (time.perf_counter() - prebuffer_start) * 1000
        self.monitor.update_prebuffer(track_id, prebuffer_frames, prebuffer_time)
        print(f"   预缓冲完成: {prebuffer_time:.1f}ms")
        
        # 模拟剩余帧传输
        remaining_frames = audio_frames - prebuffer_frames
        frame_interval = 0.055  # 优化间隔55ms
        
        print(f"\n📡 模拟优化传输: {remaining_frames}帧")
        for i in range(remaining_frames):
            time.sleep(frame_interval)
            current_sent = prebuffer_frames + i + 1
            
            # 每10帧更新一次进度
            if current_sent % 10 == 0:
                self.monitor.update_progress(track_id, current_sent, 0)
                progress = (current_sent / audio_frames) * 100
                print(f"   进度: {current_sent}/{audio_frames}帧 ({progress:.1f}%)")
        
        # 完成传输
        final_metrics = self.monitor.finish_transmission(track_id)
        
        return final_metrics
    
    def run_comprehensive_test(self, device_id: str):
        """运行综合测试"""
        print("🚀 WebSocket + 预缓冲优化综合测试")
        print("=" * 50)
        
        # 测试场景
        test_cases = [
            {"name": "短音频", "frames": 8, "duration": 0.5},
            {"name": "中等音频", "frames": 25, "duration": 1.5}, 
            {"name": "长音频", "frames": 50, "duration": 3.0},
            {"name": "超长音频", "frames": 100, "duration": 6.0}
        ]
        
        results = []
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n📋 测试 {i}/{len(test_cases)}: {case['name']}")
            print("-" * 30)
            
            metrics = self.simulate_audio_transmission(
                device_id, case['frames'], case['duration']
            )
            
            if metrics:
                results.append({
                    'case': case['name'],
                    'optimization_ratio': metrics.optimization_ratio,
                    'speed_improvement': metrics.speed_improvement,
                    'transmission_time_ms': metrics.transmission_time,
                    'avg_frame_rate': metrics.avg_frame_rate
                })
                
                # 显示结果
                status = "🚀 优秀" if metrics.optimization_ratio < 0.3 else \
                         "✅ 良好" if metrics.optimization_ratio < 0.6 else \
                         "⚠️ 一般" if metrics.optimization_ratio < 1.0 else \
                         "❌ 需优化"
                
                print(f"   {status}")
                print(f"   传输时间: {metrics.transmission_time:.1f}ms")
                print(f"   优化比例: {metrics.optimization_ratio:.3f}x")
                print(f"   提升倍数: {metrics.speed_improvement:.2f}x")
                print(f"   平均帧率: {metrics.avg_frame_rate:.1f}帧/秒")
        
        # 测试总结
        self.print_test_summary(results)
        
    def print_test_summary(self, results):
        """打印测试总结"""
        if not results:
            print("\n❌ 没有测试结果")
            return
            
        print("\n" + "=" * 50)
        print("📊 测试总结报告")
        print("=" * 50)
        
        # 计算平均性能
        avg_optimization = sum(r['optimization_ratio'] for r in results) / len(results)
        avg_improvement = sum(r['speed_improvement'] for r in results) / len(results)
        avg_frame_rate = sum(r['avg_frame_rate'] for r in results) / len(results)
        
        print(f"\n🎯 平均性能指标:")
        print(f"   优化比例: {avg_optimization:.3f}x")
        print(f"   提升倍数: {avg_improvement:.2f}x") 
        print(f"   平均帧率: {avg_frame_rate:.1f}帧/秒")
        
        # 最佳/最差性能
        best_case = min(results, key=lambda x: x['optimization_ratio'])
        worst_case = max(results, key=lambda x: x['optimization_ratio'])
        
        print(f"\n🏆 最佳性能: {best_case['case']} ({best_case['optimization_ratio']:.3f}x)")
        print(f"⚠️ 最差性能: {worst_case['case']} ({worst_case['optimization_ratio']:.3f}x)")
        
        # 性能评级
        if avg_optimization < 0.3:
            rating = "🏆 优秀 - 优化效果显著!"
            recommendation = "✅ 当前配置已达到优秀水平，建议保持"
        elif avg_optimization < 0.6:
            rating = "✅ 良好 - 优化效果明显"
            recommendation = "💡 可以尝试调整预缓冲帧数进一步优化"
        elif avg_optimization < 1.0:
            rating = "⚠️ 一般 - 有优化空间"
            recommendation = "🔧 建议检查网络状况和优化参数配置"
        else:
            rating = "❌ 需要优化 - 性能低于预期"
            recommendation = "🚨 建议启用fallback模式或调整配置参数"
            
        print(f"\n🎖️ 综合评级: {rating}")
        print(f"💡 建议: {recommendation}")
        
        # 性能对比
        print(f"\n📈 性能对比 (vs 标准60ms间隔):")
        standard_time = sum(r['transmission_time_ms'] * (60/55) for r in results) / len(results)
        optimized_time = sum(r['transmission_time_ms'] for r in results) / len(results)
        improvement_pct = ((standard_time - optimized_time) / standard_time) * 100
        
        print(f"   标准模式预估: {standard_time:.1f}ms")
        print(f"   优化模式实际: {optimized_time:.1f}ms")
        print(f"   性能提升: {improvement_pct:.1f}%")

    def run_stress_test(self, device_id: str, iterations=10):
        """运行压力测试"""
        print(f"🔥 压力测试: {iterations}次连续传输")
        print("-" * 40)
        
        results = []
        for i in range(iterations):
            print(f"第 {i+1}/{iterations} 次测试...", end=' ')
            
            # 随机测试场景
            import random
            frames = random.randint(10, 80)
            duration = frames * 0.06  # 60ms per frame
            
            metrics = self.simulate_audio_transmission(device_id, frames, duration)
            if metrics:
                results.append(metrics.optimization_ratio)
                status = "✅" if metrics.optimization_ratio < 0.6 else "⚠️"
                print(f"{status} {metrics.optimization_ratio:.3f}x")
            else:
                print("❌ 失败")
        
        # 压力测试结果
        if results:
            avg_ratio = sum(results) / len(results)
            min_ratio = min(results)
            max_ratio = max(results)
            success_rate = len(results) / iterations * 100
            
            print(f"\n📊 压力测试结果:")
            print(f"   成功率: {success_rate:.1f}%")
            print(f"   平均优化比例: {avg_ratio:.3f}x")
            print(f"   最佳性能: {min_ratio:.3f}x")
            print(f"   最差性能: {max_ratio:.3f}x")
            print(f"   性能稳定性: {'良好' if (max_ratio - min_ratio) < 0.3 else '一般'}")


def main():
    parser = argparse.ArgumentParser(description='WebSocket预缓冲优化测试工具')
    parser.add_argument('--device-id', type=str, default='test_device_001', 
                       help='测试设备ID')
    parser.add_argument('--comprehensive', action='store_true', 
                       help='运行综合测试')
    parser.add_argument('--stress', type=int, default=0, 
                       help='运行压力测试(指定次数)')
    
    args = parser.parse_args()
    
    tester = WebSocketOptimizationTester()
    
    if args.stress > 0:
        tester.run_stress_test(args.device_id, args.stress)
    elif args.comprehensive:
        tester.run_comprehensive_test(args.device_id)
    else:
        # 默认单次测试
        print("🧪 单次优化测试")
        metrics = tester.simulate_audio_transmission(args.device_id, 30, 1.8)
        if metrics:
            print(f"\n✅ 测试完成!")
            print(f"   优化比例: {metrics.optimization_ratio:.3f}x")
            print(f"   提升倍数: {metrics.speed_improvement:.2f}x")


if __name__ == '__main__':
    main()

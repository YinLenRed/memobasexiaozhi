#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket音频传输性能监控工具
用于实时查看预缓冲优化效果

使用方法:
1. 实时监控: python tools/websocket_monitor.py --live
2. 查看摘要: python tools/websocket_monitor.py --summary
3. 设备详情: python tools/websocket_monitor.py --device <device_id>
4. 导出报告: python tools/websocket_monitor.py --export report.json
"""

import argparse
import json
import time
import sys
import os
import threading

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils.websocket_performance_monitor import get_performance_monitor
from config.logger import setup_logging


class WebSocketMonitorTool:
    """WebSocket性能监控工具"""
    
    def __init__(self):
        self.monitor = get_performance_monitor()
        self.logger = setup_logging()
        self.running = False
        
    def show_current_stats(self):
        """显示当前统计信息"""
        stats = self.monitor.get_current_stats()
        print(f"\n📊 当前状态:")
        print(f"   活跃传输: {stats['active_transmissions']}")
        print(f"   已完成传输: {stats['completed_count']}")
        print(f"   在线设备: {stats['current_devices']}")
        
    def show_performance_summary(self, last_n=20):
        """显示性能摘要"""
        summary = self.monitor.get_performance_summary(last_n)
        
        if summary['status'] == 'no_data':
            print(f"\n❌ {summary['message']}")
            return
            
        print(f"\n🚀 WebSocket预缓冲优化效果摘要 (最近{summary['sample_size']}次传输):")
        print(f"   📈 平均传输时间: {summary['avg_transmission_time_ms']:.1f}ms")
        print(f"   ⚡ 平均帧率: {summary['avg_frame_rate']:.1f} 帧/秒")
        print(f"   🎯 平均优化比例: {summary['avg_optimization_ratio']:.3f}x")
        print(f"   🚀 平均提升倍数: {summary['avg_speed_improvement']:.2f}x")
        print(f"   ✅ 成功率: {summary['success_rate_percent']:.1f}%")
        print(f"   🏆 最佳优化: {summary['best_optimization']:.3f}x")
        print(f"   ⚠️  最差优化: {summary['worst_optimization']:.3f}x")
        
        # 性能评级
        avg_ratio = summary['avg_optimization_ratio']
        if avg_ratio < 0.3:
            rating = "🏆 优秀"
        elif avg_ratio < 0.6:
            rating = "✅ 良好" 
        elif avg_ratio < 1.0:
            rating = "⚠️ 一般"
        else:
            rating = "❌ 需优化"
            
        print(f"   🎖️  综合评级: {rating}")
        
    def show_device_details(self, device_id):
        """显示特定设备的详细信息"""
        details = self.monitor.get_detailed_report(device_id)
        
        if not details:
            print(f"\n❌ 设备 {device_id} 无传输记录")
            return
            
        print(f"\n📱 设备 {device_id} 详细报告:")
        print(f"   总传输次数: {len(details)}")
        
        for i, record in enumerate(details[-10:], 1):  # 显示最近10次
            status = "🟢" if record['success_rate'] > 95 else "🟡" if record['success_rate'] > 80 else "🔴"
            print(f"\n   [{i}] Track: {record['track_id'][:8]}...")
            print(f"       {status} 成功率: {record['success_rate']:.1f}%")
            print(f"       ⏱️ 传输时间: {record['transmission_time_ms']:.1f}ms")
            print(f"       🎯 优化比例: {record['optimization_ratio']:.3f}x")
            print(f"       ⚡ 帧率: {record['avg_frame_rate']:.1f} 帧/秒")
            print(f"       📦 预缓冲: {record['prebuffer_frames']}帧")
            
    def live_monitor(self, interval=5):
        """实时监控模式"""
        print("🔴 启动实时监控模式 (Ctrl+C 退出)")
        print("=" * 60)
        
        self.running = True
        try:
            while self.running:
                # 清屏 (兼容Windows和Linux)
                os.system('cls' if os.name == 'nt' else 'clear')
                
                print(f"🚀 WebSocket音频传输实时监控 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 60)
                
                self.show_current_stats()
                self.show_performance_summary(10)
                
                print(f"\n⏱️ 下次更新: {interval}秒后 (Ctrl+C 退出)")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 退出实时监控")
            self.running = False
            
    def export_report(self, filename):
        """导出详细报告"""
        try:
            # 获取所有数据
            current_stats = self.monitor.get_current_stats()
            performance_summary = self.monitor.get_performance_summary(50)
            detailed_report = self.monitor.get_detailed_report()
            
            # 组装报告
            report = {
                'timestamp': time.time(),
                'current_stats': current_stats,
                'performance_summary': performance_summary,
                'detailed_transmissions': detailed_report,
                'metadata': {
                    'total_records': len(detailed_report),
                    'export_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'tool_version': '1.0.0'
                }
            }
            
            # 写入文件
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
                
            print(f"✅ 报告已导出到: {filename}")
            print(f"📊 包含 {len(detailed_report)} 条传输记录")
            
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            
    def interactive_mode(self):
        """交互模式"""
        print("🎯 WebSocket音频传输监控工具")
        print("=" * 40)
        
        while True:
            print("\n📋 可用命令:")
            print("  1. 当前状态 (current)")
            print("  2. 性能摘要 (summary)")
            print("  3. 设备详情 (device)")
            print("  4. 实时监控 (live)")
            print("  5. 导出报告 (export)")
            print("  6. 退出 (quit)")
            
            choice = input("\n👉 请选择 (1-6): ").strip().lower()
            
            if choice in ['1', 'current']:
                self.show_current_stats()
            elif choice in ['2', 'summary']:
                self.show_performance_summary()
            elif choice in ['3', 'device']:
                device_id = input("👉 请输入设备ID: ").strip()
                if device_id:
                    self.show_device_details(device_id)
            elif choice in ['4', 'live']:
                self.live_monitor()
            elif choice in ['5', 'export']:
                filename = input("👉 请输入文件名 (默认: websocket_report.json): ").strip()
                if not filename:
                    filename = "websocket_report.json"
                self.export_report(filename)
            elif choice in ['6', 'quit', 'exit']:
                print("👋 再见!")
                break
            else:
                print("❌ 无效选择，请重试")


def main():
    parser = argparse.ArgumentParser(
        description='WebSocket音频传输性能监控工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python tools/websocket_monitor.py --live              # 实时监控
  python tools/websocket_monitor.py --summary           # 查看性能摘要
  python tools/websocket_monitor.py --device abc123     # 查看特定设备
  python tools/websocket_monitor.py --export report.json # 导出报告
  python tools/websocket_monitor.py                     # 交互模式
        """
    )
    
    parser.add_argument('--live', action='store_true', help='实时监控模式')
    parser.add_argument('--summary', action='store_true', help='显示性能摘要')
    parser.add_argument('--device', type=str, help='查看特定设备详情')
    parser.add_argument('--export', type=str, help='导出报告到文件')
    parser.add_argument('--interval', type=int, default=5, help='实时监控刷新间隔(秒)')
    
    args = parser.parse_args()
    
    tool = WebSocketMonitorTool()
    
    if args.live:
        tool.live_monitor(args.interval)
    elif args.summary:
        tool.show_current_stats()
        tool.show_performance_summary()
    elif args.device:
        tool.show_device_details(args.device)
    elif args.export:
        tool.export_report(args.export)
    else:
        # 无参数时进入交互模式
        tool.interactive_mode()


if __name__ == '__main__':
    main()

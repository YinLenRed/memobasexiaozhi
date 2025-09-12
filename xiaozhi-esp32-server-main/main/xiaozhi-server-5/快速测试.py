#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小智系统快速测试启动脚本
使用你的Java后端地址进行快速测试
"""

import asyncio
import subprocess
import sys
import os
from datetime import datetime

def print_banner():
    """打印测试横幅"""
    print("🤖 小智系统快速测试")
    print("=" * 50)
    print(f"Java后端: http://q83b6ed9.natappfree.cc")
    print(f"Python服务: http://47.98.51.180:8003")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

def check_dependencies():
    """检查依赖包"""
    print("🔍 检查依赖包...")
    
    required_packages = ['websockets', 'paho-mqtt', 'requests']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package}")
    
    if missing_packages:
        print("\n⚠️  缺少依赖包，正在安装...")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install'
            ] + missing_packages)
            print("✅ 依赖包安装完成")
        except subprocess.CalledProcessError:
            print("❌ 依赖包安装失败，请手动安装:")
            print(f"   pip install {' '.join(missing_packages)}")
            return False
    
    return True

def run_quick_test():
    """运行快速测试"""
    print("\n🚀 启动快速测试...")
    
    # 检查测试脚本是否存在
    scripts = {
        '1': ('Java API测试', 'test_java_api.py'),
        '2': ('MQTT通信测试', 'test_mqtt_communication.py'), 
        '3': ('WebSocket音频测试', 'test_websocket_audio.py'),
        '4': ('完整流程测试', 'test_full_flow.py'),
        '5': ('全套测试', 'run_all_tests.py')
    }
    
    print("\n请选择要运行的测试:")
    for key, (name, script) in scripts.items():
        status = "✅" if os.path.exists(script) else "❌"
        print(f"  {key}. {status} {name}")
    
    choice = input("\n请输入选择 (1-5) 或按回车运行全套测试: ").strip()
    
    if not choice:
        choice = '5'  # 默认运行全套测试
    
    if choice in scripts:
        _, script_name = scripts[choice]
        
        if not os.path.exists(script_name):
            print(f"❌ 测试脚本不存在: {script_name}")
            return False
        
        print(f"\n🧪 运行测试: {script_name}")
        print("-" * 30)
        
        try:
            # 运行选择的测试脚本
            result = subprocess.run([
                sys.executable, script_name,
                '--java-url', 'http://q83b6ed9.natappfree.cc',
                '--python-url', 'http://47.98.51.180:8003',
                '--device-id', 'f0:9e:9e:04:8a:44'
            ], check=False)
            
            if result.returncode == 0:
                print(f"\n🎉 测试完成: {script_name}")
                return True
            else:
                print(f"\n❌ 测试失败: {script_name}")
                return False
                
        except KeyboardInterrupt:
            print("\n⚠️  测试被用户中断")
            return False
        except Exception as e:
            print(f"\n❌ 运行测试时发生异常: {e}")
            return False
    else:
        print("❌ 无效选择")
        return False

def main():
    """主函数"""
    print_banner()
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，无法继续")
        input("按回车键退出...")
        return
    
    # 创建必要的目录
    dirs = ['test_logs', 'test_reports', 'test_audio_data']
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
    
    # 运行测试
    if run_quick_test():
        print("\n✅ 测试执行完成！")
        print("\n📊 查看测试报告:")
        print("  - test_reports/ 目录下的JSON和HTML报告")
        print("  - test_logs/ 目录下的日志文件")
    else:
        print("\n❌ 测试执行失败！")
        print("\n🔧 故障排查:")
        print("  1. 确认Java后端服务正常运行")
        print("  2. 检查网络连接")
        print("  3. 查看test_logs/目录下的日志文件")
    
    print(f"\n🕐 测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    input("\n按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        input("按回车键退出...")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速修复测试脚本
验证MQTT兼容性修复是否成功
"""

import sys
import asyncio

def test_mqtt_import():
    """测试MQTT导入和兼容性"""
    print("🔍 测试MQTT库导入和兼容性...")
    
    try:
        import paho.mqtt.client as mqtt
        print("✅ paho-mqtt 导入成功")
        
        # 检查版本
        try:
            version = mqtt.__version__
            print(f"📦 paho-mqtt 版本: {version}")
        except:
            print("⚠️  无法获取版本信息")
        
        # 测试CallbackAPIVersion
        try:
            from paho.mqtt.client import CallbackAPIVersion
            print("✅ CallbackAPIVersion 导入成功 (paho-mqtt 2.0+)")
            has_callback_api = True
        except ImportError:
            print("ℹ️  使用 paho-mqtt 1.x 版本")
            has_callback_api = False
        
        # 测试客户端创建
        try:
            if has_callback_api:
                client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1, client_id="test_client")
                print("✅ MQTT客户端创建成功 (2.0+ API)")
            else:
                client = mqtt.Client("test_client")
                print("✅ MQTT客户端创建成功 (1.x API)")
            
            client.disconnect()  # 立即断开
            return True
            
        except Exception as e:
            print(f"❌ MQTT客户端创建失败: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ MQTT库导入失败: {e}")
        return False

def test_websockets_import():
    """测试WebSocket库"""
    print("\n🔍 测试WebSocket库...")
    
    try:
        import websockets
        print("✅ websockets 导入成功")
        return True
    except ImportError as e:
        print(f"❌ websockets 导入失败: {e}")
        return False

def test_requests_import():
    """测试requests库"""
    print("\n🔍 测试requests库...")
    
    try:
        import requests
        print("✅ requests 导入成功")
        return True
    except ImportError as e:
        print(f"❌ requests 导入失败: {e}")
        return False

async def test_basic_functionality():
    """测试基本功能"""
    print("\n🧪 测试基本异步功能...")
    
    try:
        # 测试异步功能
        await asyncio.sleep(0.1)
        print("✅ asyncio 功能正常")
        return True
    except Exception as e:
        print(f"❌ asyncio 测试失败: {e}")
        return False

def install_missing_packages():
    """安装缺失的包"""
    print("\n📦 检查并安装缺失的依赖包...")
    
    import subprocess
    
    packages_to_check = ['paho-mqtt', 'websockets', 'requests']
    missing_packages = []
    
    for package in packages_to_check:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"⚠️  发现缺失包: {', '.join(missing_packages)}")
        print("正在安装...")
        
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install'
            ] + missing_packages)
            print("✅ 依赖包安装完成")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 安装失败: {e}")
            return False
    else:
        print("✅ 所有依赖包都已安装")
        return True

async def main():
    """主测试函数"""
    print("🔧 小智系统MQTT兼容性修复验证")
    print("=" * 50)
    
    # 检查并安装依赖
    if not install_missing_packages():
        print("\n❌ 依赖包安装失败，请手动安装")
        return False
    
    # 测试各个组件
    mqtt_ok = test_mqtt_import()
    websocket_ok = test_websockets_import()
    requests_ok = test_requests_import()
    async_ok = await test_basic_functionality()
    
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    print(f"  MQTT库: {'✅ 正常' if mqtt_ok else '❌ 异常'}")
    print(f"  WebSocket库: {'✅ 正常' if websocket_ok else '❌ 异常'}")
    print(f"  Requests库: {'✅ 正常' if requests_ok else '❌ 异常'}")
    print(f"  异步功能: {'✅ 正常' if async_ok else '❌ 异常'}")
    
    all_ok = mqtt_ok and websocket_ok and requests_ok and async_ok
    
    if all_ok:
        print("\n🎉 修复成功！现在可以运行测试脚本了：")
        print("   python test_mqtt_communication.py --device-id f0:9e:9e:04:8a:44")
        print("   python run_all_tests.py")
    else:
        print("\n❌ 仍有问题需要解决")
        print("请检查错误信息并手动安装相关依赖包")
    
    return all_ok

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试执行异常: {e}")
        sys.exit(1)

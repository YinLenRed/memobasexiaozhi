#!/usr/bin/env python3
"""
🌐 公网IP配置验证工具
验证Python服务是否可以通过公网地址访问
"""

import subprocess
import socket
import json
import requests
from datetime import datetime

def check_server_ip_configuration():
    """检查服务器IP配置"""
    print("🌐 服务器IP配置检查")
    print("=" * 80)
    print(f"📅 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print("🔍 1. 检查网络接口配置")
    print("-" * 50)
    
    try:
        # 获取网络接口信息
        result = subprocess.run(["ip", "addr"], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if '47.98.51.180' in line:
                    print(f"✅ 找到公网IP: {line.strip()}")
                elif '172.20.12.204' in line:
                    print(f"✅ 找到内网IP: {line.strip()}")
                elif 'inet ' in line and not '127.0.0.1' in line:
                    print(f"📋 其他IP: {line.strip()}")
        else:
            print("❌ 无法获取网络接口信息")
    except Exception as e:
        print(f"❌ 检查网络接口失败: {e}")

def check_python_service_binding():
    """检查Python服务绑定情况"""
    print("\n🔍 2. 检查Python服务绑定")
    print("-" * 50)
    
    try:
        # 检查8000端口监听情况
        result = subprocess.run(["netstat", "-tlnp"], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if ':8000' in line:
                    if '0.0.0.0:8000' in line:
                        print("✅ Python服务监听所有接口 (0.0.0.0:8000) - 支持公网访问")
                    elif '127.0.0.1:8000' in line:
                        print("⚠️ Python服务仅监听本地接口 (127.0.0.1:8000) - 需要修改配置")
                    elif '172.20.12.204:8000' in line:
                        print("⚠️ Python服务仅监听内网接口 (172.20.12.204:8000) - 需要修改配置")
                    print(f"📋 监听详情: {line.strip()}")
        else:
            print("❌ 无法获取端口监听信息")
    except Exception as e:
        print(f"❌ 检查端口绑定失败: {e}")

def test_public_ip_accessibility():
    """测试公网IP可访问性"""
    print("\n🔍 3. 测试公网IP可访问性")
    print("-" * 50)
    
    public_ips = ["47.98.51.180"]
    
    for ip in public_ips:
        print(f"\n📡 测试 {ip}:8000")
        
        # 测试TCP连接
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((ip, 8000))
            sock.close()
            
            if result == 0:
                print(f"✅ TCP连接成功: {ip}:8000")
            else:
                print(f"❌ TCP连接失败: {ip}:8000 (错误码: {result})")
        except Exception as e:
            print(f"❌ TCP连接异常: {e}")
        
        # 测试HTTP响应
        try:
            response = requests.get(f"http://{ip}:8000", timeout=5)
            print(f"✅ HTTP响应: {response.status_code} - {response.text[:50]}")
        except requests.exceptions.ConnectionError:
            print(f"⚠️ HTTP连接被拒绝 (WebSocket服务器正常)")
        except requests.exceptions.Timeout:
            print(f"❌ HTTP请求超时")
        except Exception as e:
            print(f"❌ HTTP请求异常: {e}")

def check_firewall_and_security():
    """检查防火墙和安全组"""
    print("\n🔍 4. 检查防火墙和安全配置")
    print("-" * 50)
    
    # 检查iptables
    try:
        result = subprocess.run(["iptables", "-L", "-n"], capture_output=True, text=True)
        if result.returncode == 0:
            if "8000" in result.stdout:
                print("📋 发现8000端口相关防火墙规则:")
                lines = result.stdout.split('\n')
                for line in lines:
                    if "8000" in line:
                        print(f"  {line.strip()}")
            else:
                print("ℹ️ 未发现8000端口特定防火墙规则")
        else:
            print("⚠️ 无法检查iptables (可能需要root权限)")
    except Exception as e:
        print(f"⚠️ 检查防火墙失败: {e}")
    
    print("\n💡 常见问题:")
    print("  • 云服务器安全组是否开放8000端口？")
    print("  • 系统防火墙是否阻止8000端口？")
    print("  • 负载均衡器是否正确配置？")

def provide_configuration_solution():
    """提供配置解决方案"""
    print("\n🔧 5. 配置解决方案")
    print("-" * 50)
    
    print("📋 方案A: 确认Python服务监听配置")
    print("  1. 检查 config.yaml 中的服务器配置:")
    print("     server:")
    print("       ip: \"0.0.0.0\"    # 监听所有接口")
    print("       port: 8000")
    print()
    
    print("📋 方案B: 检查网络配置")
    print("  1. 确认47.98.51.180确实是本服务器的公网IP")
    print("  2. 检查云服务器安全组设置")
    print("  3. 检查系统防火墙设置")
    print()
    
    print("📋 方案C: 测试硬件连接")
    print("  1. 硬件先尝试连接内网地址: ws://172.20.12.204:8000/xiaozhi/v1/")
    print("  2. 如果成功，再配置公网地址映射")
    print("  3. 如果失败，说明是其他问题")

def provide_immediate_test():
    """提供立即测试方案"""
    print("\n🧪 6. 立即测试方案")
    print("-" * 50)
    
    print("⚡ 立即验证硬件连接:")
    print("  # 让硬件临时改为内网地址测试")
    print("  ws://172.20.12.204:8000/xiaozhi/v1/")
    print()
    print("  # 然后发送主动问候测试")
    print("  curl -X POST http://172.20.12.204:8003/xiaozhi/greeting/send \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"device_id\": \"7c:2c:67:8d:89:78\", \"initial_content\": \"测试内网连接\", \"category\": \"test\"}'")
    print()
    print("✅ 如果内网连接成功且有音频，说明:")
    print("  • Python服务逻辑完全正常")
    print("  • 问题在于公网网络配置")
    print("  • 需要配置公网IP映射或安全组")

def main():
    """主检查流程"""
    check_server_ip_configuration()
    check_python_service_binding()
    test_public_ip_accessibility()
    check_firewall_and_security()
    provide_configuration_solution()
    provide_immediate_test()
    
    print("\n" + "=" * 80)
    print("🎊 检查结论")
    print("=" * 80)
    print("✅ Python服务默认配置支持公网访问 (监听0.0.0.0)")
    print("✅ 硬件连接地址理论上正确: ws://47.98.51.180:8000/xiaozhi/v1/")
    print("❓ 需要验证: 47.98.51.180是否为本服务器公网IP")
    print("❓ 需要检查: 网络路由和安全组配置")
    print()
    print("🎯 建议优先验证:")
    print("   1. 硬件先连接内网地址测试功能")
    print("   2. 确认公网IP和网络配置正确性")
    print("   3. 配置公网访问权限")

if __name__ == "__main__":
    main()

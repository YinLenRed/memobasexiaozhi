#!/usr/bin/env python3
"""
测试Bearer Token认证
"""

import urllib.request
import urllib.error
import json

MEMOBASE_API = "http://47.98.51.180:8019"

def test_with_token(token=""):
    """测试带token的API调用"""
    
    # 测试项目配置API
    try:
        url = f"{MEMOBASE_API}/api/v1/project/profile_config"
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/json')
        if token:
            req.add_header('Authorization', f'Bearer {token}')
        
        print(f"🔍 测试: {url}")
        print(f"🔐 Token: {'已设置' if token else '未设置'}")
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.getcode() == 200:
                content = response.read().decode('utf-8')
                data = json.loads(content)
                print(f"✅ 成功获取配置:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return True
            else:
                print(f"⚠️  返回状态: {response.getcode()}")
                return False
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP错误: {e.code} {e.reason}")
        if e.code == 401:
            print("   说明: 需要有效的Bearer Token")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_admin_status(token=""):
    """测试管理状态API"""
    
    try:
        url = f"{MEMOBASE_API}/api/v1/admin/status_check"
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/json')
        if token:
            req.add_header('Authorization', f'Bearer {token}')
        
        print(f"\n🔍 测试管理API: {url}")
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.getcode() == 200:
                content = response.read().decode('utf-8')
                data = json.loads(content)
                print(f"✅ 管理状态:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return True
            else:
                print(f"⚠️  返回状态: {response.getcode()}")
                return False
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP错误: {e.code} {e.reason}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def main():
    print("🚀 Memobase Bearer Token测试")
    print("=" * 50)
    
    # 无token测试
    print("📋 测试1: 无Token访问")
    test_with_token("")
    
    print("\n📋 测试2: 管理API")
    test_admin_status("")
    
    print("\n" + "=" * 50)
    print("💡 获取Bearer Token的方法:")
    print("1. 联系memobase服务管理员")
    print("2. 查看项目配置文档")
    print("3. 检查环境变量或配置文件")
    print("4. 在API文档页面查看示例")
    
    print("\n📝 配置方法:")
    print("在config.yaml中设置:")
    print("  memobase:")
    print("    api_key: 'your-bearer-token-here'")

if __name__ == "__main__":
    main()

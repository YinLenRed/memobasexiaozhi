#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小智记忆快速清除脚本
提供简单的命令行方式快速清除记忆
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from 记忆管理工具 import MemoryManager


def quick_clear_device(device_id: str):
    """快速清除指定设备记忆"""
    print(f"🗑️ 准备清除设备 {device_id} 的记忆...")
    
    manager = MemoryManager()
    
    # 先显示当前记忆
    user_id = manager.find_device_user(device_id)
    if not user_id:
        print(f"❌ 未找到设备 {device_id}")
        return
    
    memories = manager.get_user_memories(user_id)
    print(f"📊 设备 {device_id} 当前有 {len(memories)} 条记忆")
    
    if len(memories) == 0:
        print("✅ 设备记忆已经是空的")
        return
    
    # 显示记忆概要
    print("\n记忆概要:")
    topics = {}
    for memory in memories:
        topic = memory['topic']
        topics[topic] = topics.get(topic, 0) + 1
    
    for topic, count in topics.items():
        print(f"  - {topic}: {count}条")
    
    # 确认删除
    confirm = input(f"\n确认清除设备 {device_id} 的所有记忆? (yes/no): ").strip().lower()
    if confirm == "yes":
        if manager.delete_device_memory(device_id, confirm=True):
            print("✅ 记忆清除成功!")
        else:
            print("❌ 记忆清除失败!")
    else:
        print("❌ 操作已取消")


def quick_clear_all():
    """快速清除所有记忆"""
    print("🗑️ 准备清除所有设备的记忆...")
    
    manager = MemoryManager()
    
    # 显示统计信息
    users = manager.list_all_users()
    print(f"📊 当前有 {len(users)} 个用户/设备")
    
    if len(users) == 0:
        print("✅ 没有找到任何记忆数据")
        return
    
    total_memories = 0
    for user in users:
        memories = manager.get_user_memories(user['id'])
        total_memories += len(memories)
        device_info = user.get('additional_fields', {})
        device_name = list(device_info.keys())[0] if device_info else user['id']
        print(f"  - 设备 {device_name}: {len(memories)}条记忆")
    
    print(f"\n总计: {total_memories} 条记忆")
    
    # 双重确认
    confirm1 = input(f"\n确认清除所有设备的记忆? (yes/no): ").strip().lower()
    if confirm1 != "yes":
        print("❌ 操作已取消")
        return
    
    confirm2 = input(f"再次确认! 此操作不可恢复! (yes/no): ").strip().lower()
    if confirm2 == "yes":
        if manager.delete_all_memories(confirm=True):
            print("✅ 所有记忆清除成功!")
        else:
            print("❌ 记忆清除失败!")
    else:
        print("❌ 操作已取消")


def show_usage():
    """显示使用说明"""
    print("🧠 小智记忆快速清除工具")
    print("=" * 40)
    print("用法:")
    print("  python 快速清除记忆.py device <设备ID>    # 清除指定设备记忆")
    print("  python 快速清除记忆.py all               # 清除所有记忆")
    print("  python 快速清除记忆.py help              # 显示帮助")
    print("\n示例:")
    print("  python 快速清除记忆.py device xiaozhi_001")
    print("  python 快速清除记忆.py all")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_usage()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "device":
            if len(sys.argv) < 3:
                print("❌ 请指定设备ID")
                print("用法: python 快速清除记忆.py device <设备ID>")
                return
            device_id = sys.argv[2]
            quick_clear_device(device_id)
        
        elif command == "all":
            quick_clear_all()
        
        elif command == "help":
            show_usage()
        
        else:
            print(f"❌ 未知命令: {command}")
            show_usage()
            
    except KeyboardInterrupt:
        print("\n👋 操作已取消")
    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")


if __name__ == "__main__":
    main()

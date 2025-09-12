#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小智记忆管理工具
提供多种方式清除和管理设备记忆
"""

import sys
import json
import time
from memobase import Memobase, ChatBlob
from typing import List, Optional, Dict
import traceback

class MemoryManager:
    """小智记忆管理器"""
    
    def __init__(self, project_url="http://47.98.51.180:8019", api_key="secret"):
        """
        初始化记忆管理器
        
        Args:
            project_url: Memobase服务地址
            api_key: API密钥
        """
        self.project_url = project_url
        self.api_key = api_key
        
        try:
            self.client = Memobase(project_url=project_url, api_key=api_key)
            print(f"✅ 成功连接到Memobase服务: {project_url}")
        except Exception as e:
            print(f"❌ 连接Memobase服务失败: {str(e)}")
            sys.exit(1)
    
    def list_all_users(self) -> List[Dict]:
        """列出所有用户"""
        try:
            users = self.client.get_all_users(
                search="", 
                order_by='updated_at', 
                order_desc=True,
                limit=100
            )
            return users
        except Exception as e:
            print(f"❌ 获取用户列表失败: {str(e)}")
            return []
    
    def find_device_user(self, device_id: str) -> Optional[str]:
        """
        根据设备ID查找对应的用户ID
        
        Args:
            device_id: 设备ID（role_id）
            
        Returns:
            用户ID或None
        """
        try:
            users = self.list_all_users()
            for user in users:
                additional_fields = user.get('additional_fields', {})
                if device_id in additional_fields:
                    return user.get('id')
            return None
        except Exception as e:
            print(f"❌ 查找设备用户失败: {str(e)}")
            return None
    
    def get_user_memories(self, user_id: str) -> List[Dict]:
        """
        获取用户的记忆列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            记忆列表
        """
        try:
            user = self.client.get_user(user_id)
            user.flush()  # 确保缓存是最新的
            profiles = user.profile()
            
            memories = []
            for profile in profiles:
                memories.append({
                    'id': profile.id,
                    'topic': profile.topic,
                    'sub_topic': profile.sub_topic,
                    'content': profile.content,
                    'describe': profile.describe,
                    'created_at': str(profile.created_at),
                    'updated_at': str(profile.updated_at)
                })
            return memories
        except Exception as e:
            print(f"❌ 获取用户记忆失败: {str(e)}")
            return []
    
    def delete_device_memory(self, device_id: str, confirm: bool = False) -> bool:
        """
        删除指定设备的所有记忆
        
        Args:
            device_id: 设备ID
            confirm: 是否确认删除
            
        Returns:
            是否成功
        """
        if not confirm:
            print("⚠️  请使用 confirm=True 确认删除操作")
            return False
        
        try:
            user_id = self.find_device_user(device_id)
            if not user_id:
                print(f"❌ 未找到设备 {device_id} 对应的用户")
                return False
            
            # 删除用户及其所有记忆
            self.client.delete_user(user_id)
            print(f"✅ 已删除设备 {device_id} 的所有记忆")
            return True
            
        except Exception as e:
            print(f"❌ 删除设备记忆失败: {str(e)}")
            print(f"详细错误: {traceback.format_exc()}")
            return False
    
    def delete_all_memories(self, confirm: bool = False) -> bool:
        """
        删除所有设备的记忆
        
        Args:
            confirm: 是否确认删除
            
        Returns:
            是否成功
        """
        if not confirm:
            print("⚠️  请使用 confirm=True 确认删除操作")
            return False
        
        try:
            users = self.list_all_users()
            deleted_count = 0
            
            for user in users:
                try:
                    self.client.delete_user(user['id'])
                    deleted_count += 1
                    print(f"✅ 已删除用户 {user['id']} 的记忆")
                except Exception as e:
                    print(f"❌ 删除用户 {user['id']} 失败: {str(e)}")
            
            print(f"✅ 总共删除了 {deleted_count} 个用户的记忆")
            return True
            
        except Exception as e:
            print(f"❌ 删除所有记忆失败: {str(e)}")
            print(f"详细错误: {traceback.format_exc()}")
            return False
    
    def delete_specific_memories(self, device_id: str, memory_ids: List[str], confirm: bool = False) -> bool:
        """
        删除指定设备的特定记忆
        
        Args:
            device_id: 设备ID
            memory_ids: 要删除的记忆ID列表
            confirm: 是否确认删除
            
        Returns:
            是否成功
        """
        if not confirm:
            print("⚠️  请使用 confirm=True 确认删除操作")
            return False
        
        try:
            user_id = self.find_device_user(device_id)
            if not user_id:
                print(f"❌ 未找到设备 {device_id} 对应的用户")
                return False
            
            user = self.client.get_user(user_id)
            deleted_count = 0
            
            for memory_id in memory_ids:
                try:
                    user.delete_profile(memory_id)
                    deleted_count += 1
                    print(f"✅ 已删除记忆 {memory_id}")
                except Exception as e:
                    print(f"❌ 删除记忆 {memory_id} 失败: {str(e)}")
            
            print(f"✅ 总共删除了 {deleted_count} 条记忆")
            return True
            
        except Exception as e:
            print(f"❌ 删除特定记忆失败: {str(e)}")
            print(f"详细错误: {traceback.format_exc()}")
            return False
    
    def clear_memory_by_topic(self, device_id: str, topics: List[str], confirm: bool = False) -> bool:
        """
        根据主题清除记忆
        
        Args:
            device_id: 设备ID
            topics: 要清除的主题列表
            confirm: 是否确认删除
            
        Returns:
            是否成功
        """
        if not confirm:
            print("⚠️  请使用 confirm=True 确认删除操作")
            return False
        
        try:
            user_id = self.find_device_user(device_id)
            if not user_id:
                print(f"❌ 未找到设备 {device_id} 对应的用户")
                return False
            
            memories = self.get_user_memories(user_id)
            to_delete = [m['id'] for m in memories if m['topic'] in topics]
            
            if not to_delete:
                print(f"❌ 未找到主题为 {topics} 的记忆")
                return False
            
            return self.delete_specific_memories(device_id, to_delete, confirm=True)
            
        except Exception as e:
            print(f"❌ 按主题清除记忆失败: {str(e)}")
            return False
    
    def show_memory_statistics(self):
        """显示记忆统计信息"""
        try:
            users = self.list_all_users()
            print(f"\n📊 记忆统计信息")
            print(f"=" * 50)
            print(f"总用户数: {len(users)}")
            
            total_memories = 0
            for user in users:
                try:
                    memories = self.get_user_memories(user['id'])
                    device_info = user.get('additional_fields', {})
                    device_name = list(device_info.keys())[0] if device_info else user['id']
                    
                    print(f"\n设备: {device_name}")
                    print(f"  用户ID: {user['id']}")
                    print(f"  记忆数: {len(memories)}")
                    print(f"  创建时间: {user.get('created_at', 'N/A')}")
                    print(f"  更新时间: {user.get('updated_at', 'N/A')}")
                    
                    if memories:
                        # 按主题分组
                        topics = {}
                        for memory in memories:
                            topic = memory['topic']
                            if topic not in topics:
                                topics[topic] = 0
                            topics[topic] += 1
                        
                        print(f"  主题分布:")
                        for topic, count in topics.items():
                            print(f"    - {topic}: {count}条")
                    
                    total_memories += len(memories)
                    
                except Exception as e:
                    print(f"  ❌ 获取记忆失败: {str(e)}")
            
            print(f"\n总记忆数: {total_memories}")
            print(f"=" * 50)
            
        except Exception as e:
            print(f"❌ 获取统计信息失败: {str(e)}")
    
    def interactive_menu(self):
        """交互式菜单"""
        while True:
            print(f"\n🧠 小智记忆管理工具")
            print(f"=" * 40)
            print(f"1. 📊 查看记忆统计")
            print(f"2. 🔍 查看指定设备记忆")
            print(f"3. 🗑️  删除指定设备记忆")
            print(f"4. 🗑️  删除所有设备记忆")
            print(f"5. 🎯 按主题删除记忆")
            print(f"6. 🚪 退出")
            print(f"=" * 40)
            
            choice = input("请选择操作 (1-6): ").strip()
            
            if choice == "1":
                self.show_memory_statistics()
            
            elif choice == "2":
                device_id = input("请输入设备ID: ").strip()
                if device_id:
                    user_id = self.find_device_user(device_id)
                    if user_id:
                        memories = self.get_user_memories(user_id)
                        print(f"\n设备 {device_id} 的记忆:")
                        print(f"-" * 50)
                        for i, memory in enumerate(memories, 1):
                            print(f"{i}. [{memory['topic']}/{memory['sub_topic']}] {memory['describe']}")
                            print(f"   内容: {memory['content'][:100]}...")
                            print(f"   ID: {memory['id']}")
                            print(f"   更新时间: {memory['updated_at']}")
                            print()
                    else:
                        print(f"❌ 未找到设备 {device_id}")
            
            elif choice == "3":
                device_id = input("请输入设备ID: ").strip()
                if device_id:
                    confirm = input(f"确认删除设备 {device_id} 的所有记忆? (yes/no): ").strip().lower()
                    if confirm == "yes":
                        self.delete_device_memory(device_id, confirm=True)
                    else:
                        print("❌ 操作已取消")
            
            elif choice == "4":
                confirm = input("确认删除所有设备的记忆? (yes/no): ").strip().lower()
                if confirm == "yes":
                    double_confirm = input("再次确认删除所有记忆? 此操作不可恢复! (yes/no): ").strip().lower()
                    if double_confirm == "yes":
                        self.delete_all_memories(confirm=True)
                    else:
                        print("❌ 操作已取消")
                else:
                    print("❌ 操作已取消")
            
            elif choice == "5":
                device_id = input("请输入设备ID: ").strip()
                if device_id:
                    topics_str = input("请输入要删除的主题（多个主题用逗号分隔）: ").strip()
                    if topics_str:
                        topics = [t.strip() for t in topics_str.split(',')]
                        confirm = input(f"确认删除设备 {device_id} 中主题为 {topics} 的记忆? (yes/no): ").strip().lower()
                        if confirm == "yes":
                            self.clear_memory_by_topic(device_id, topics, confirm=True)
                        else:
                            print("❌ 操作已取消")
            
            elif choice == "6":
                print("👋 再见!")
                break
            
            else:
                print("❌ 无效选择，请重新输入")


def main():
    """主函数"""
    print("🧠 小智记忆管理工具")
    print("=" * 40)
    
    # 可以通过命令行参数自定义连接信息
    project_url = "http://47.98.51.180:8019"
    api_key = "secret"
    
    if len(sys.argv) >= 3:
        project_url = sys.argv[1]
        api_key = sys.argv[2]
    
    try:
        manager = MemoryManager(project_url, api_key)
        
        # 如果有命令行参数，直接执行对应操作
        if len(sys.argv) > 3:
            action = sys.argv[3].lower()
            
            if action == "stats":
                manager.show_memory_statistics()
            
            elif action == "delete_device" and len(sys.argv) >= 5:
                device_id = sys.argv[4]
                confirm = len(sys.argv) > 5 and sys.argv[5].lower() == "confirm"
                manager.delete_device_memory(device_id, confirm=confirm)
            
            elif action == "delete_all":
                confirm = len(sys.argv) > 4 and sys.argv[4].lower() == "confirm"
                manager.delete_all_memories(confirm=confirm)
            
            else:
                print("❌ 无效的命令行参数")
                print("用法:")
                print("  python 记忆管理工具.py [project_url] [api_key] stats")
                print("  python 记忆管理工具.py [project_url] [api_key] delete_device <device_id> [confirm]")
                print("  python 记忆管理工具.py [project_url] [api_key] delete_all [confirm]")
        
        else:
            # 启动交互式菜单
            manager.interactive_menu()
            
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 程序出错: {str(e)}")
        print(f"详细错误: {traceback.format_exc()}")


if __name__ == "__main__":
    main()

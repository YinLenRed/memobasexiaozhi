import traceback

from ..base import MemoryProviderBase, logger
from memobase import Memobase, ChatBlob
from core.utils.util import check_model_key

TAG = __name__


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory=None):
        super().__init__(config)
        # 从配置中获取memobase连接信息
        self.project_url = config.get("project_url", "http://47.98.51.180:8019")
        self.api_key = config.get("api_key", "secret")
        self.project_id = config.get("project_id", "xiaozhi-memory")
        self.enabled = config.get("enabled", True)
        
        # 如果禁用，则不尝试连接
        if not self.enabled:
            logger.bind(tag=TAG).info("Memobase 记忆存储已禁用")
            self.client = None
            return
        
        try:
            self.client = Memobase(project_url=self.project_url, api_key=self.api_key)
            logger.bind(tag=TAG).info(f"成功连接到 memobase 服务: {self.project_url}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"连接到 memobase 服务时发生错误: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
            self.client = None

    def init_memory(
        self, role_id, llm, summary_memory=None, save_to_file=True, **kwargs
    ):
        super().init_memory(role_id, llm, **kwargs)

    async def save_memory(self, msgs):
        # 检查客户端是否可用
        if not self.client:
            logger.bind(tag=TAG).warning("Memobase客户端不可用，跳过保存记忆")
            return None
            
        print('role_id', self.role_id)
        try:
            users = self.client.get_all_users(search="", order_by='updated_at', order_desc=True)
            print('users', users)
            u_id = None
            for user in users:
                additional_fields = user.get('additional_fields')
                print('additional_fields:', additional_fields)
                if additional_fields and self.role_id in additional_fields:
                    u_id = user.get('id')
                    break
            if not u_id:
                u_id = self.client.add_user({self.role_id: self.role_id})
            u = self.client.get_user(u_id)
            messages = [
                {"role": message.role, "content": message.content}
                for message in msgs
                if message.role in ["user", "assistant"]  # 只保留有效的角色
            ]
            bid = u.insert(ChatBlob(messages=messages))
            logger.bind(tag=TAG).debug(f"Save memory result: {u.get(bid)}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"保存记忆失败: {str(e)}")
            return None

    async def query_memory(self, query: str) -> str:
        # 检查客户端是否可用
        if not self.client:
            logger.bind(tag=TAG).warning("Memobase客户端不可用，返回空记忆")
            return ""
            
        try:
            users = self.client.get_all_users(search="", order_by='updated_at', order_desc=True)
            print('users', users)
            u_id = None
            for user in users:
                additional_fields = user.get('additional_fields')
                print('additional_fields:', additional_fields)
                if additional_fields and self.role_id in additional_fields:
                    u_id = user.get('id')
                    break
            if not u_id:
                u_id = self.client.add_user({self.role_id: self.role_id})
            u = self.client.get_user(u_id)
            u.flush()
            results = u.profile()
            if not len(results):
                return ""

            # Format each memory entry with its update time up to minutes
            memories = []
            for entry in results:
                timestamp = str(entry.updated_at)
                if timestamp:
                    try:
                        # Parse and reformat the timestamp
                        dt = timestamp.split(".")[0]  # Remove milliseconds
                        # formatted_time = dt.replace("T", " ")
                        formatted_time = dt.replace("T", " ")
                    except:
                        formatted_time = timestamp
                memory = entry.content
                if timestamp and memory:
                    # Store tuple of (timestamp, formatted_string) for sorting
                    memories.append((timestamp, f"[{formatted_time}] {memory}"))

            # Sort by timestamp in descending order (newest first)
            memories.sort(key=lambda x: x[0], reverse=True)

            # Extract only the formatted strings
            memories_str = "\n".join(f"- {memory[1]}" for memory in memories)
            logger.bind(tag=TAG).debug(f"Query results: {memories_str}")
            return memories_str
        except Exception as e:
            logger.bind(tag=TAG).error(f"查询记忆失败: {str(e)}")
            return ""
    
    async def clear_memory(self) -> bool:
        """
        清除当前设备的所有记忆
        
        Returns:
            bool: 是否成功清除
        """
        if not self.client:
            logger.bind(tag=TAG).warning("Memobase客户端不可用，无法清除记忆")
            return False
        
        try:
            users = self.client.get_all_users(search="", order_by='updated_at', order_desc=True)
            u_id = None
            
            # 查找当前设备对应的用户
            for user in users:
                additional_fields = user.get('additional_fields')
                if additional_fields and self.role_id in additional_fields:
                    u_id = user.get('id')
                    break
            
            if not u_id:
                logger.bind(tag=TAG).info(f"设备 {self.role_id} 没有找到记忆数据")
                return True  # 没有记忆也算成功
            
            # 删除用户及其所有记忆
            self.client.delete_user(u_id)
            logger.bind(tag=TAG).info(f"✅ 已清除设备 {self.role_id} 的所有记忆")
            return True
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"清除记忆失败: {str(e)}")
            return False
    
    async def clear_memory_by_topic(self, topics: list) -> bool:
        """
        根据主题清除记忆
        
        Args:
            topics: 要清除的主题列表
            
        Returns:
            bool: 是否成功清除
        """
        if not self.client:
            logger.bind(tag=TAG).warning("Memobase客户端不可用，无法清除记忆")
            return False
        
        try:
            users = self.client.get_all_users(search="", order_by='updated_at', order_desc=True)
            u_id = None
            
            # 查找当前设备对应的用户
            for user in users:
                additional_fields = user.get('additional_fields')
                if additional_fields and self.role_id in additional_fields:
                    u_id = user.get('id')
                    break
            
            if not u_id:
                logger.bind(tag=TAG).info(f"设备 {self.role_id} 没有找到记忆数据")
                return True
            
            u = self.client.get_user(u_id)
            u.flush()
            profiles = u.profile()
            
            # 找到要删除的记忆
            to_delete = []
            for profile in profiles:
                if profile.topic in topics:
                    to_delete.append(profile.id)
            
            if not to_delete:
                logger.bind(tag=TAG).info(f"未找到主题为 {topics} 的记忆")
                return True
            
            # 逐个删除记忆配置文件
            deleted_count = 0
            for profile_id in to_delete:
                try:
                    u.delete_profile(profile_id)
                    deleted_count += 1
                except Exception as e:
                    logger.bind(tag=TAG).error(f"删除记忆 {profile_id} 失败: {str(e)}")
            
            logger.bind(tag=TAG).info(f"✅ 已删除设备 {self.role_id} 中 {deleted_count} 条主题为 {topics} 的记忆")
            return deleted_count > 0
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"按主题清除记忆失败: {str(e)}")
            return False

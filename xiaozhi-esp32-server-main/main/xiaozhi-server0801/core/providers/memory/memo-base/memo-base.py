import traceback

from ..base import MemoryProviderBase, logger
from memobase import Memobase, ChatBlob
from core.utils.util import check_model_key

TAG = __name__


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory=None):
        super().__init__(config)
        self.api_key = config.get("api_key", "secret")
        try:
            self.client = Memobase(project_url='http://47.98.51.180:8019', api_key='secret')
            logger.bind(tag=TAG).info("成功连接到 memobase 服务")
        except Exception as e:
            logger.bind(tag=TAG).error(f"连接到 memobase 服务时发生错误: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")

    def init_memory(
        self, role_id, llm, summary_memory=None, save_to_file=True, **kwargs
    ):
        super().init_memory(role_id, llm, **kwargs)

    async def save_memory(self, msgs):
        print('role_id', self.role_id)
        try:
            users = self.client.get_all_users(search="", order_by='updated_at', order_desc=True)
            print('users', users)
            u_id = None
            for user in users:
                print(user.get('additional_fields'))
                if self.role_id in user.get('additional_fields'):
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
        try:
            users = self.client.get_all_users(search="", order_by='updated_at', order_desc=True)
            print('users', users)
            u_id = None
            for user in users:
                print(user.get('additional_fields'))
                if self.role_id in user.get('additional_fields'):
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
                if self.role_id in user.get('additional_fields'):
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

from rich import print
from memobase import MemoBaseClient, ChatBlob

PROJECT_URL = "https://api.memobase.dev"
PROJECT_TOKEN = "sk-proj-80c742f56a1dd621-0da46a144de3fc8666500313e1ba12b7"

client = MemoBaseClient(
    project_url=PROJECT_URL,
    api_key=PROJECT_TOKEN,
)

# 使用之前创建的用户ID（你需要替换成实际的用户ID）
user_id = "94d749e4-b30c-415f-b28b-3b83e90b42f7"  # 替换为你的用户ID
u = client.get_user(user_id)

# 添加更多记忆 - 比如具体的旅行经历
new_travel_memory = [
    {
        "role": "user",
        "content": "我去过日本的冲绳，那里的海水真的很清澈，还看到了很多热带鱼。那次旅行让我更加确定了想要学潜水的想法。",
        "created_at": "2025-08-03",
    },
    {
        "role": "assistant", 
        "content": "冲绳确实是个美丽的地方！清澈的海水和丰富的海洋生物一定给你留下了深刻印象。这样的经历让你更向往潜水也很自然呢！",
        "alias": "AI助手",
    },
]

# 添加个人偏好
preference_memory = [
    {
        "role": "user",
        "content": "我比较喜欢海岛旅行，不太喜欢寒冷的地方。温暖的阳光和蓝色的海水总是能让我放松。",
        "created_at": "2025-08-03",
    },
    {
        "role": "assistant",
        "content": "海岛旅行确实很棒！温暖的气候和美丽的海景能让人完全放松下来。看来你真的很适合去瓦努阿图这样的热带天堂！",
        "alias": "AI助手",
    },
]

print("🏝️ 添加冲绳旅行回忆...")
blob_travel = ChatBlob(messages=new_travel_memory)
u.insert(blob_travel)

print("🌞 添加旅行偏好...")
blob_preference = ChatBlob(messages=preference_memory)
u.insert(blob_preference)

print("⚙️ 处理新记忆...")
u.flush(sync=True)

print("\n🧠 更新后的用户档案:")
print(u.profile(need_json=True))

print("\n📝 更新后的记忆上下文:")
print(f"```\n{u.context()}\n```")

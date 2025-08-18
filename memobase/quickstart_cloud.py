from rich import print
from memobase import MemoBaseClient, ChatBlob

# 选项1: 使用 Memobase 云服务（推荐）
# 你需要从 https://www.memobase.io/en/login 获取 API 密钥
PROJECT_URL = "https://api.memobase.dev"
PROJECT_TOKEN = "sk-proj-80c742f56a1dd621-0da46a144de3fc8666500313e1ba12b7"  # 替换为你的实际 API 密钥

# 选项2: 如果你想使用本地服务器，需要先启动服务器
# PROJECT_URL = "http://localhost:8019"
# PROJECT_TOKEN = "secret"

print("🔧 正在连接到 Memobase...")
print(f"📡 服务器地址: {PROJECT_URL}")

client = MemoBaseClient(
    project_url=PROJECT_URL,
    api_key=PROJECT_TOKEN,
)

# 测试连接
try:
    ping_result = client.ping()
    if ping_result:
        print("✅ 成功连接到 Memobase 服务器!")
    else:
        print("❌ 无法连接到 Memobase 服务器")
        exit(1)
except Exception as e:
    print(f"❌ 连接失败: {e}")
    print("\n💡 解决方案:")
    print("1. 如果使用云服务，请确保 API 密钥正确")
    print("2. 如果使用本地服务器，请先启动服务器")
    print("3. 访问 https://app.memobase.io/playground 体验在线版本")
    exit(1)

# 第一组对话 - 基本介绍
messages_1 = [
    {
        "role": "user",
        "content": "Hello, I'm 鸭鸭",
        "created_at": "2025-08-03",
    },
    {
        "role": "assistant",
        "content": "Hi, nice to meet you, 鸭鸭! That's such a cute name!",
        "alias": "AI助手",
    },
]

# 第二组对话 - 兴趣爱好
messages_2 = [
    {
        "role": "user", 
        "content": "我真的很喜欢旅行，去过很多地方，每次旅行都让我感到特别开心和充实。",
        "created_at": "2025-08-03",
    },
    {
        "role": "assistant",
        "content": "旅行确实是一件很棒的事情！能够探索不同的地方，体验不同的文化，一定给你带来了很多美好的回忆。你最喜欢的旅行目的地是哪里呢？",
        "alias": "AI助手",
    },
]

# 第三组对话 - 梦想
messages_3 = [
    {
        "role": "user",
        "content": "我最大的梦想是去瓦努阿图潜水！我听说那里的海底世界特别美，有很多珊瑚礁和热带鱼。潜水一直是我想尝试的运动。",
        "created_at": "2025-08-03", 
    },
    {
        "role": "assistant",
        "content": "瓦努阿图确实是潜水爱好者的天堂！那里有著名的蓝洞和丰富的海洋生物。你的这个梦想听起来很棒，希望你能早日实现！",
        "alias": "AI助手",
    },
]

print("\n👤 创建用户...")
uid = client.add_user()
u = client.get_user(uid)

print(f"🆔 用户 ID: {uid}")

# 插入多组对话来构建更丰富的用户画像
print("\n💬 插入第一组对话（基本介绍）...")
blob_1 = ChatBlob(messages=messages_1)
bid_1 = u.insert(blob_1)
print(f"📝 数据块 1 ID: {bid_1}")

print("\n💬 插入第二组对话（兴趣爱好）...")
blob_2 = ChatBlob(messages=messages_2) 
bid_2 = u.insert(blob_2)
print(f"📝 数据块 2 ID: {bid_2}")

print("\n💬 插入第三组对话（梦想目标）...")
blob_3 = ChatBlob(messages=messages_3)
bid_3 = u.insert(blob_3)
print(f"📝 数据块 3 ID: {bid_3}")

print("\n⚙️ 处理记忆数据...")
u.flush(sync=True)

print("\n🧠 用户档案:")
print(u.profile(need_json=True))

print("\n📅 用户事件:")
for e in u.event():
    print("📅", e.created_at.astimezone().strftime("%Y-%m-%d %H:%M:%S"))
    for i in e.event_data.profile_delta:
        print(
            "-", i.attributes["topic"], i.attributes["sub_topic"], i.content, sep="::"
        )

print("\n📝 记忆上下文:")
print(f"```\n{u.context()}\n```")

print("\n🎉 示例运行完成!")

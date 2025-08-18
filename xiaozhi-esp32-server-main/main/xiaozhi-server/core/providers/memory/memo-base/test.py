# -*-coding:utf-8-*-
# from memobase import MemoBaseClient
#
# mb = MemoBaseClient("http://47.97.185.142:8001", "secret")
# assert mb.ping()
import requests
import json
# from memobase import Memobase
# memobase = Memobase(project_url='http://47.97.185.142:8001', api_key='secret')
# print('memobase', memobase)
# users = memobase.get_all_users(search="", order_by='updated_at', order_desc=True)
# print('users', users)
# user = None
# for user in users:
#     print(user.get('additional_fields'))
#     if 'f8:89:d2:64:b0:05' in user.get('additional_fields'):
#         print(user.get('additional_fields').get('f8:89:d2:64:b0:05'))
    # print(user.get('additional_fields'))
# c7cdce5c-02dd-4dd4-8dce-c69b5911e5fa
# uid = memobase.add_user({'f8:89:d2:64:b0:05': 'f8:89:d2:64:b0:05'})
# print('uid', uid)

from memobase import Memobase, ChatBlob

mac_address = 'f8:89:d2:64:b0:05'
client = Memobase(project_url='http://47.98.51.180:8019', api_key='secret')
print('client', client)
users = client.get_all_users(search="", order_by='updated_at', order_desc=True)
print('users', users)
u_id = None
for user in users:
    print(user.get('additional_fields'))
    if mac_address in user.get('additional_fields'):
        u_id = user.get('id')
        break
if not u_id:
    u_id = client.add_user({mac_address: mac_address})
u = client.get_user(u_id)
messages = [
    {
        'role': 'user',
        'content': "我喜欢打篮球",
    },
    {
        'role': 'assistant',
        'content': "啊，你喜欢打篮球啊，好厉害!",
    }
]
# bid = u.insert(ChatBlob(messages=messages))
# print(u.get(bid))
u.flush()
print(u.profile())
a = u.profile()
print(len(a))
for i in a:
    print(i.content, i.created_at, i.updated_at, i.topic)

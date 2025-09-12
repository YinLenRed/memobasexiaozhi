#!/bin/bash
# xiaozhi项目环境快速设置（用于source）

# 激活虚拟环境
source /home/web/.venv/bin/activate

# 切换到项目目录
cd /home/web/xiaozhi-esp32-server-main/main/xiaozhi-server

echo "✅ xiaozhi环境已激活"
echo "📍 目录: $(pwd)"

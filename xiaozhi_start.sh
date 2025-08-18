#!/bin/bash

VENV_PATH="/home/web/.venv"
PROJECT_DIR="/home/web/xiaozhi-esp32-server-main/main/xiaozhi-server"

cd "$PROJECT_DIR" || exit 1
source "$VENV_PATH/bin/activate"

# 后台运行并将日志输出重定向
nohup python app.py > logs/server.log 2>&1 &

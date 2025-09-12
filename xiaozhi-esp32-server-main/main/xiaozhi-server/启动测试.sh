#!/bin/bash

# 设置颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}   🤖 小智系统全流程测试套件${NC}"
echo -e "${BLUE}====================================${NC}"
echo -e "Java后端: http://q83b6ed9.natappfree.cc"
echo -e "Python服务: http://47.98.51.180:8003"
echo -e "${BLUE}====================================${NC}"
echo ""

# 检查Python环境
echo -e "${YELLOW}🔍 检查Python环境...${NC}"
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python未安装${NC}"
    echo "请先安装Python 3.8+"
    exit 1
fi

# 确定Python命令
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo -e "${GREEN}✅ Python环境正常${NC}"

# 检查并安装依赖
echo ""
echo -e "${YELLOW}📦 检查并安装依赖包...${NC}"
$PYTHON_CMD -c "import websockets, paho.mqtt.client, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "正在安装依赖包..."
    $PYTHON_CMD -m pip install websockets paho-mqtt requests
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 依赖包安装失败${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ 依赖包已安装${NC}"

# 创建必要目录
echo ""
echo -e "${YELLOW}📁 创建必要目录...${NC}"
mkdir -p test_logs test_reports test_audio_data

echo -e "${GREEN}✅ 目录创建完成${NC}"

# 显示测试菜单
echo ""
echo -e "${YELLOW}🚀 启动测试选择菜单...${NC}"
echo ""
echo "请选择要运行的测试:"
echo "  1. Java API测试"
echo "  2. MQTT通信测试"
echo "  3. WebSocket音频测试"
echo "  4. 完整流程测试"
echo -e "  5. ${GREEN}全套测试 (推荐)${NC}"
echo "  6. 启动硬件模拟器"
echo "  0. 退出"
echo ""

read -p "请输入选择 (0-6，默认5): " choice
choice=${choice:-5}

case $choice in
    0)
        echo "👋 再见！"
        exit 0
        ;;
    1)
        echo -e "${YELLOW}🧪 运行Java API测试...${NC}"
        $PYTHON_CMD test_java_api.py --java-url http://q83b6ed9.natappfree.cc
        ;;
    2)
        echo -e "${YELLOW}🧪 运行MQTT通信测试...${NC}"
        $PYTHON_CMD test_mqtt_communication.py --device-id f0:9e:9e:04:8a:44
        ;;
    3)
        echo -e "${YELLOW}🧪 运行WebSocket音频测试...${NC}"
        $PYTHON_CMD test_websocket_audio.py --websocket-url ws://47.98.51.180:8000/xiaozhi/v1/
        ;;
    4)
        echo -e "${YELLOW}🧪 运行完整流程测试...${NC}"
        $PYTHON_CMD test_full_flow.py --device-id f0:9e:9e:04:8a:44
        ;;
    5)
        echo -e "${YELLOW}🧪 运行全套测试...${NC}"
        $PYTHON_CMD run_all_tests.py --java-url http://q83b6ed9.natappfree.cc --python-url http://47.98.51.180:8003
        ;;
    6)
        echo -e "${YELLOW}🤖 启动硬件模拟器...${NC}"
        echo "请在另一个终端窗口运行测试脚本"
        $PYTHON_CMD hardware_simulator.py f0:9e:9e:04:8a:44
        ;;
    *)
        echo -e "${RED}❌ 无效选择${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}📊 测试报告位置:${NC}"
echo "  - test_reports/ 目录下的JSON和HTML报告"
echo "  - test_logs/ 目录下的日志文件"
echo ""
echo -e "${GREEN}🕐 测试完成时间: $(date)${NC}"
echo ""

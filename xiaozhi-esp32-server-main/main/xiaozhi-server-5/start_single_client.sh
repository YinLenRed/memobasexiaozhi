#!/bin/bash

# 小智单客户端启动脚本 - 避免MQTT冲突
# 只启动app.py主服务，使用统一MQTT客户端

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数 - 同时输出到终端和日志文件
log() {
    local msg="${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
    echo -e "$msg"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> logs/server.log
}

error() {
    local msg="${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    echo -e "$msg"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >> logs/server.log
}

warn() {
    local msg="${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARN:${NC} $1"
    echo -e "$msg"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARN: $1" >> logs/server.log
}

# 检查依赖
check_dependencies() {
    log "🔍 检查环境依赖..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        error "❌ Python未安装"
        exit 1
    fi
    
    # 检查主文件
    if [ ! -f "app.py" ]; then
        error "❌ 缺少主文件: app.py"
        exit 1
    fi
    
    log "✅ 环境检查通过"
}

# 启动服务
start_service() {
    log "🚀 启动小智主服务（统一MQTT客户端）..."
    
    # 确定Python命令
    local python_cmd="python3"
    if ! command -v python3 &> /dev/null; then
        python_cmd="python"
    fi
    
    # 创建日志目录
    mkdir -p logs
    
    # 后台启动主服务
    nohup $python_cmd app.py > logs/app_unified.log 2>&1 &
    local pid=$!
    
    # 保存PID
    echo $pid > app.py.pid
    
    # 等待服务启动
    sleep 3
    
    # 检查进程是否还在运行
    if kill -0 $pid 2>/dev/null; then
        log "✅ 小智主服务启动成功 (PID: $pid)"
        log "📡 使用统一MQTT客户端 - 无连接冲突"
        return 0
    else
        error "❌ 小智主服务启动失败"
        if [ -f "logs/app_unified.log" ]; then
            error "📋 错误详情 (最近20行):"
            tail -20 logs/app_unified.log | while read line; do
                echo "    $line" >> logs/server.log
            done
        fi
        return 1
    fi
}

# 停止服务
stop_service() {
    log "🛑 停止小智主服务..."
    
    if [ -f "app.py.pid" ]; then
        local pid=$(cat "app.py.pid")
        if kill -0 $pid 2>/dev/null; then
            log "🛑 停止主服务 (PID: $pid)..."
            kill -TERM $pid
            
            # 等待优雅停止
            local count=0
            while kill -0 $pid 2>/dev/null && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # 如果还没停止，强制杀死
            if kill -0 $pid 2>/dev/null; then
                warn "⚠️ 强制停止主服务..."
                kill -KILL $pid
            fi
            
            log "✅ 小智主服务已停止"
        fi
        rm -f "app.py.pid"
    else
        warn "❌ 未找到服务进程"
    fi
}

# 检查服务状态
check_status() {
    log "🔍 检查服务状态..."
    
    if [ -f "app.py.pid" ]; then
        local pid=$(cat "app.py.pid")
        if kill -0 $pid 2>/dev/null; then
            log "✅ 小智主服务运行中 (PID: $pid)"
            log "📡 MQTT客户端: 统一管理"
            return 0
        else
            log "❌ 小智主服务已停止"
            rm -f "app.py.pid"
            return 1
        fi
    else
        log "❌ 小智主服务未启动"
        return 1
    fi
}

# 显示服务日志
show_logs() {
    log "📋 显示最近日志..."
    
    if [ -f "logs/app_unified.log" ]; then
        echo "=== 主服务日志 (最近50行) ==="
        tail -n 50 logs/app_unified.log
    else
        warn "❌ 未找到日志文件"
    fi
}

# 实时监控日志
monitor_logs() {
    log "📈 实时监控日志 (Ctrl+C 退出)..."
    
    if [ -f "logs/app_unified.log" ]; then
        tail -f logs/app_unified.log
    else
        warn "❌ 未找到日志文件"
    fi
}

# 信号处理
cleanup() {
    echo ""
    log "📡 接收到停止信号..."
    stop_service
    exit 0
}

# 注册信号处理器
trap cleanup SIGINT SIGTERM

# 主函数
main() {
    # 创建日志目录
    mkdir -p logs
    
    # 初始化日志文件
    echo "🎉 小智服务管理器启动 - $(date '+%Y-%m-%d %H:%M:%S')" > logs/server.log
    echo "================================================================" >> logs/server.log
    
    echo "================================================================"
    echo "🎉 小智统一MQTT客户端服务管理器"
    echo "================================================================"
    echo ""
    
    log "📝 脚本日志输出到: logs/server.log"
    
    # 检查依赖
    check_dependencies
    
    case "${1:-start}" in
        "start")
            # 先检查是否已经在运行
            if check_status &>/dev/null; then
                warn "⚠️ 服务已在运行"
                exit 1
            fi
            
            if start_service; then
                log "🎉 服务启动成功！"
                log "📊 服务信息:"
                log "   📡 统一MQTT客户端 - 避免连接冲突"
                log "   🌤️ 天气功能集成在主服务中"
                log "   🤖 语音对话、WebSocket、HTTP全功能"
                
                log "💡 硬件对接:"
                log "   📋 MQTT主题: xiaozhi/+"
                log "   📋 完整文档: HARDWARE_MQTT_GUIDE.md"
                
                log "🔧 管理命令:"
                log "   ./start_single_client.sh status   - 检查状态"
                log "   ./start_single_client.sh logs     - 查看日志"
                log "   ./start_single_client.sh monitor  - 实时日志"
                log "   ./start_single_client.sh stop     - 停止服务"
                
                log "📈 实时日志监控 (最近消息)..."
                sleep 2
                show_logs | tail -20
                
                log "🔄 服务现在在后台运行"
                log "💡 使用 './start_single_client.sh monitor' 查看实时日志"
            else
                error "❌ 服务启动失败"
                exit 1
            fi
            ;;
        "stop")
            stop_service
            ;;
        "restart")
            log "🔄 重启服务..."
            stop_service
            sleep 2
            if start_service; then
                log "✅ 服务重启成功"
            else
                error "❌ 服务重启失败"
                exit 1
            fi
            ;;
        "status")
            check_status
            ;;
        "logs")
            show_logs
            ;;
        "monitor")
            monitor_logs
            ;;
        *)
            echo "用法: $0 {start|stop|restart|status|logs|monitor}"
            echo ""
            echo "命令说明:"
            echo "  start   - 启动统一MQTT服务"
            echo "  stop    - 停止服务"
            echo "  restart - 重启服务"
            echo "  status  - 检查服务状态"
            echo "  logs    - 显示最近日志"
            echo "  monitor - 实时监控日志"
            echo ""
            echo "🎯 特点: 使用单一MQTT客户端，避免连接冲突"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"

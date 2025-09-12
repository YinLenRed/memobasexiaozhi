#!/bin/bash

# 环境切换便捷脚本
# 用于在本地开发环境和生产环境之间快速切换

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')] INFO:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARN:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"
}

# 检查Python环境
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        error "❌ 未找到Python环境"
        exit 1
    fi
}

# 快速修复MQTT连接问题
quick_fix_mqtt() {
    log "🔧 快速修复MQTT客户端ID冲突问题"
    
    if [ -f "fix_production_mqtt.py" ]; then
        $PYTHON_CMD fix_production_mqtt.py
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            log "✅ MQTT问题修复成功"
            return 0
        else
            error "❌ MQTT问题修复失败"
            return 1
        fi
    else
        error "❌ 修复脚本不存在: fix_production_mqtt.py"
        return 1
    fi
}

# 初始化环境配置
init_env() {
    log "🚀 初始化环境配置模板"
    
    if [ -f "env_manager.py" ]; then
        $PYTHON_CMD env_manager.py init
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            log "✅ 环境配置初始化成功"
            return 0
        else
            error "❌ 环境配置初始化失败"
            return 1
        fi
    else
        error "❌ 环境管理器不存在: env_manager.py"
        return 1
    fi
}

# 切换环境
switch_environment() {
    local target_env="$1"
    
    if [ -z "$target_env" ]; then
        error "❌ 请指定环境类型: local 或 production"
        return 1
    fi
    
    log "🔄 切换到 ${target_env^^} 环境"
    
    if [ -f "env_manager.py" ]; then
        $PYTHON_CMD env_manager.py switch "$target_env"
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            log "✅ 环境切换成功"
            
            # 询问是否重启服务
            echo ""
            read -p "🤔 是否重启服务使配置生效? (y/n): " -n 1 -r
            echo
            
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                if [ -f "start_single_client.sh" ]; then
                    log "🔄 重启服务中..."
                    ./start_single_client.sh restart
                    
                    if [ $? -eq 0 ]; then
                        log "✅ 服务重启成功"
                        log "💡 运行 './start_single_client.sh monitor' 查看日志"
                    else
                        warn "⚠️ 服务重启失败，请手动检查"
                    fi
                else
                    warn "⚠️ 启动脚本不存在，请手动重启服务"
                fi
            fi
            
            return 0
        else
            error "❌ 环境切换失败"
            return 1
        fi
    else
        error "❌ 环境管理器不存在: env_manager.py"
        return 1
    fi
}

# 显示当前状态
show_status() {
    log "📊 显示当前环境状态"
    
    if [ -f "env_manager.py" ]; then
        $PYTHON_CMD env_manager.py status
    else
        error "❌ 环境管理器不存在: env_manager.py"
        return 1
    fi
    
    # 显示服务状态
    echo ""
    if [ -f "start_single_client.sh" ]; then
        info "🔍 检查服务运行状态:"
        ./start_single_client.sh status
    fi
}

# 显示帮助信息
show_help() {
    echo "🔧 小智环境管理工具"
    echo "==================="
    echo ""
    echo "用法: $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  fix            - 🚨 快速修复MQTT客户端ID冲突问题（生产环境推荐）"
    echo "  init           - 🚀 初始化环境配置模板"
    echo "  local          - 🏠 切换到本地开发环境"
    echo "  production     - 🏭 切换到生产环境"
    echo "  status         - 📊 显示当前环境和服务状态" 
    echo "  help           - ❓ 显示此帮助信息"
    echo ""
    echo "📋 典型使用场景:"
    echo "  生产部署遇到MQTT返回码7错误:"
    echo "    $0 fix"
    echo ""
    echo "  首次设置多环境配置:"
    echo "    $0 init"
    echo "    $0 production"
    echo ""
    echo "  本地开发:"
    echo "    $0 local"
    echo ""
    echo "  检查当前状态:"
    echo "    $0 status"
}

# 主函数
main() {
    # 检查Python环境
    check_python
    
    local command="${1:-help}"
    
    case "$command" in
        "fix")
            quick_fix_mqtt
            ;;
        "init")
            init_env
            ;;
        "local")
            switch_environment "local"
            ;;
        "production"|"prod")
            switch_environment "production"
            ;;
        "status")
            show_status
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            warn "❓ 未知命令: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"

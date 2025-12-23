#!/bin/bash
set -e  # 遇到错误退出

echo "=========================================="
echo "🚗 汽车测试用例生成系统启动"
echo "=========================================="

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查Python依赖..."
    
    local missing_deps=()
    
    # 检查后端依赖
    if ! python3 -c "import fastapi" 2>/dev/null; then
        missing_deps+=("fastapi")
    fi
    
    if ! python3 -c "import uvicorn" 2>/dev/null; then
        missing_deps+=("uvicorn")
    fi
    
    if ! python3 -c "import aiohttp" 2>/dev/null; then
        missing_deps+=("aiohttp")
    fi
    
    # 检查前端依赖
    if ! python3 -c "import streamlit" 2>/dev/null; then
        missing_deps+=("streamlit")
    fi
    
    if ! python3 -c "import pandas" 2>/dev/null; then
        missing_deps+=("pandas")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_warning "缺少依赖: ${missing_deps[*]}"
        log_info "尝试安装缺少的依赖..."
        pip install "${missing_deps[@]}" || {
            log_error "依赖安装失败"
            exit 1
        }
        log_success "依赖安装完成"
    else
        log_success "所有依赖已安装"
    fi
}

# 停止已有服务
stop_existing_services() {
    log_info "停止现有服务..."
    
    # 停止后端
    if pgrep -f "uvicorn.*main_workflow" > /dev/null; then
        log_info "停止后端服务..."
        pkill -f "uvicorn.*main_workflow"
        sleep 2
    fi
    
    # 停止前端
    if pgrep -f "streamlit.*streamlit_app" > /dev/null; then
        log_info "停止前端服务..."
        pkill -f "streamlit.*streamlit_app"
        sleep 2
    fi
    
    log_success "服务停止完成"
}

# 检查端口是否可用
check_port() {
    local port=$1
    local service=$2
    
    if netstat -tulpn 2>/dev/null | grep ":$port" > /dev/null; then
        log_error "端口 $port 已被占用，$service 无法启动"
        return 1
    fi
    return 0
}

# 启动后端API服务
start_backend() {
    log_info "启动后端API服务..."
    
    # 检查端口
    check_port 8000 "后端API" || return 1
    
    # 设置环境变量
    export PYTHONPATH="/opt/TestCraft-AI:$PYTHONPATH"
    
    # 启动后端
    nohup python3 -m uvicorn src.workflow.main_workflow:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --log-level warning \
        > /tmp/testcraft_backend.log 2>&1 &
    
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/testcraft_backend.pid
    
    # 等待启动
    log_info "等待后端服务启动..."
    sleep 5
    
    # 检查是否启动成功
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        log_success "后端API服务启动成功 (PID: $BACKEND_PID)"
        return 0
    else
        log_error "后端API服务启动失败，查看日志: /tmp/testcraft_backend.log"
        tail -20 /tmp/testcraft_backend.log
        return 1
    fi
}

# 启动前端服务
start_frontend() {
    log_info "启动前端服务..."
    
    # 检查端口
    check_port 8501 "前端" || return 1
    
    # 设置环境变量
    export PYTHONPATH="/opt/TestCraft-AI:$PYTHONPATH"
    
    # 检查前端文件是否存在
    if [ ! -f "frontend/streamlit_app.py" ]; then
        log_error "前端文件 frontend/streamlit_app.py 不存在"
        return 1
    fi
    
    # 启动前端
    nohup streamlit run frontend/streamlit_app.py \
        --server.port 8501 \
        --server.address 0.0.0.0 \
        --server.headless true \
        --theme.base light \
        --server.maxUploadSize 100 \
        > /tmp/testcraft_frontend.log 2>&1 &
    
    FRONTEND_PID=$!
    echo $FRONTEND_PID > /tmp/testcraft_frontend.pid
    
    # 等待启动
    log_info "等待前端服务启动..."
    sleep 8
    
    # 检查是否启动成功
    if curl -s http://localhost:8501 > /dev/null 2>&1; then
        log_success "前端服务启动成功 (PID: $FRONTEND_PID)"
        return 0
    else
        log_warning "前端服务启动检测失败，但仍可能正在启动中"
        log_info "查看日志: /tmp/testcraft_frontend.log"
        return 0
    fi
}

# 显示服务状态
show_status() {
    echo ""
    echo "=========================================="
    echo "📊 服务状态"
    echo "=========================================="
    
    # 后端状态
    if [ -f /tmp/testcraft_backend.pid ] && kill -0 $(cat /tmp/testcraft_backend.pid) 2>/dev/null; then
        echo -e "🔧 后端API服务: ${GREEN}运行中${NC} (PID: $(cat /tmp/testcraft_backend.pid))"
        echo "   🌐 本地访问: http://localhost:8000"
        echo "   📚 API文档: http://localhost:8000/docs"
        echo "   🩺 健康检查: http://localhost:8000/api/v1/health"
    else
        echo -e "🔧 后端API服务: ${RED}未运行${NC}"
    fi
    
    # 前端状态
    if [ -f /tmp/testcraft_frontend.pid ] && kill -0 $(cat /tmp/testcraft_frontend.pid) 2>/dev/null; then
        echo -e "🖥️  前端服务: ${GREEN}运行中${NC} (PID: $(cat /tmp/testcraft_frontend.pid))"
        echo "   🌐 本地访问: http://localhost:8501"
    else
        echo -e "🖥️  前端服务: ${RED}未运行${NC}"
    fi
    
    # 公网访问信息
    echo ""
    echo "=========================================="
    echo "🌍 公网访问信息"
    echo "=========================================="
    echo "   公网IP: 8.138.92.110"
    echo "   🖥️  前端界面: http://8.138.92.110:8501"
    echo "   📚 API文档: http://8.138.92.110:8000/docs"
    echo ""
    echo "=========================================="
    echo "📋 管理命令"
    echo "=========================================="
    echo "   查看后端日志: tail -f /tmp/testcraft_backend.log"
    echo "   查看前端日志: tail -f /tmp/testcraft_frontend.log"
    echo "   停止所有服务: ./stop_system.sh"
    echo "   重启服务: ./run_system.sh"
    echo ""
}

# 停止服务函数
stop_services() {
    log_info "停止服务..."
    
    if [ -f /tmp/testcraft_backend.pid ]; then
        kill $(cat /tmp/testcraft_backend.pid) 2>/dev/null && rm -f /tmp/testcraft_backend.pid
    fi
    
    if [ -f /tmp/testcraft_frontend.pid ]; then
        kill $(cat /tmp/testcraft_frontend.pid) 2>/dev/null && rm -f /tmp/testcraft_frontend.pid
    fi
    
    # 确保进程停止
    pkill -f "uvicorn.*main_workflow" 2>/dev/null
    pkill -f "streamlit.*streamlit_app" 2>/dev/null
    
    log_success "服务已停止"
}

# 主函数
main() {
    echo ""
    log_info "开始启动系统..."
    
    # 检查依赖
    check_dependencies
    
    # 停止现有服务
    stop_existing_services
    
    # 启动后端
    if ! start_backend; then
        log_error "后端启动失败，退出"
        exit 1
    fi
    
    # 启动前端
    if ! start_frontend; then
        log_error "前端启动失败"
        # 继续显示状态，后端可能还在运行
    fi
    
    # 显示状态
    show_status
    
    # 设置退出时的清理
    trap cleanup EXIT INT TERM
}

# 清理函数
cleanup() {
    echo ""
    log_info "收到停止信号，清理资源..."
    stop_services
    exit 0
}

# 运行主函数
main

# 保持脚本运行，等待Ctrl+C
echo ""
log_info "系统启动完成，按 Ctrl+C 停止服务"
echo ""

# 等待用户中断
while true; do
    sleep 1
done
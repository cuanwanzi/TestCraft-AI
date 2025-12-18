#!/bin/bash
# scripts/start.sh

echo "🚗 启动汽车测试用例生成系统..."

# 获取当前目录
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "项目根目录: $PROJECT_ROOT"

# 设置Python路径
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 检查环境变量
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ 请设置 DEEPSEEK_API_KEY 环境变量"
    echo "   export DEEPSEEK_API_KEY=your_api_key_here"
    exit 1
fi

# 创建数据目录
mkdir -p data/knowledge_base
mkdir -p data/templates
mkdir -p data/logs
mkdir -p data/uploads

# 检查requirements.txt
if [ -f "requirements.txt" ]; then
    echo "📦 检查Python依赖..."
    pip install -r requirements.txt
fi

# 启动数据库服务（如果有docker-compose）
if [ -f "docker-compose.yml" ]; then
    echo "📊 启动数据库服务..."
    docker-compose up -d redis db qdrant
    
    # 等待数据库就绪
    echo "⏳ 等待数据库就绪..."
    sleep 10
fi

# 初始化知识库
echo "📚 初始化知识库..."
cd "$PROJECT_ROOT"
python scripts/init_knowledge_base.py

# 启动API服务
echo "🌐 启动API服务..."
cd "$PROJECT_ROOT"
python -m uvicorn src.workflow.main_workflow:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info &

API_PID=$!

# 启动前端
echo "🖥️ 启动前端界面..."
cd "$PROJECT_ROOT"
streamlit run frontend/streamlit_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 &

FRONTEND_PID=$!

# 保存PID文件
echo $API_PID > /tmp/automotive_test_api.pid
echo $FRONTEND_PID > /tmp/automotive_test_frontend.pid

echo "✅ 系统启动完成！"
echo "🌐 访问以下地址："
echo "   - API文档: http://localhost:8000/docs"
echo "   - 前端界面: http://localhost:8501"
echo "   - 向量数据库: http://localhost:6333"

echo ""
echo "📝 使用说明："
echo "   1. 在浏览器中访问 http://localhost:8501"
echo "   2. 输入测试需求，系统将自动生成测试用例"
echo "   3. 查看生成的测试用例和解释"
echo ""
echo "🛑 停止系统请按 Ctrl+C"

# 等待退出信号
trap 'echo "正在停止服务..."; kill $API_PID $FRONTEND_PID 2>/dev/null; echo "服务已停止"; exit' INT TERM
wait
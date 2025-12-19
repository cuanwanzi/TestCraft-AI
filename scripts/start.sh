#!/bin/bash
# start_simple.sh

echo "🚗 启动汽车测试用例生成系统（简单模式）..."

# 设置项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 设置Python路径
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 检查环境变量
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ 请设置 DEEPSEEK_API_KEY 环境变量"
    echo "   例如: export DEEPSEEK_API_KEY=your_key_here"
    exit 1
fi

# 检查依赖
echo "📦 检查Python依赖..."
pip install -r requirements.txt --quiet 2>/dev/null || {
    echo "安装依赖失败，尝试简单安装..."
    pip install fastapi uvicorn aiohttp pydantic sentence-transformers streamlit --quiet
}

# 创建必要目录
mkdir -p data/knowledge_base data/templates data/logs data/uploads

# 清理旧的 ChromaDB 数据（避免配置错误）
if [ -d "./data/knowledge_base" ]; then
    # 只删除 ChromaDB 相关文件，保留 SQLite 数据库
    find ./data/knowledge_base -type f -name "*.parquet" -delete
    find ./data/knowledge_base -type f -name "chroma.sqlite3" -delete
    find ./data/knowledge_base -type f -name "chroma_settings.json" -delete
    echo "✓ 清理旧的 ChromaDB 数据"
fi

# 初始化系统
echo "🔄 初始化系统..."
python scripts/init_simple.py

if [ $? -ne 0 ]; then
    echo "❌ 系统初始化失败"
    exit 1
fi

# 启动 API 服务
echo "🌐 启动 API 服务..."
python -m uvicorn src.workflow.main_workflow:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info \
    &

API_PID=$!

# 等待 API 启动
sleep 3

# 启动前端
echo "🖥️  启动前端界面..."
streamlit run frontend/streamlit_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    &

FRONTEND_PID=$!

# 保存 PID
echo $API_PID > /tmp/automotive_api.pid
echo $FRONTEND_PID > /tmp/automotive_frontend.pid

echo ""
echo "✅ 系统启动完成！"
echo "========================================="
echo "🌐 API 文档:    http://localhost:8000/docs"
echo "🖥️  前端界面:   http://localhost:8501"
echo "========================================="
echo ""
echo "📝 使用说明："
echo "   1. 在浏览器中访问 http://localhost:8501"
echo "   2. 输入测试需求"
echo "   3. 系统将自动生成测试用例"
echo ""
echo "🛑 停止系统请按 Ctrl+C"
echo ""

# 等待退出
trap 'echo "正在停止服务..."; kill $API_PID $FRONTEND_PID 2>/dev/null; echo "服务已停止"; exit' INT TERM
wait
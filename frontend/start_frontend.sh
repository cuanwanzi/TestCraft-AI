# frontend/start_frontend.sh
#!/bin/bash

echo "🖥️  启动汽车测试用例生成前端..."

# 设置Python路径
export PYTHONPATH="$(pwd)/..:$PYTHONPATH"

# 安装前端依赖
pip install streamlit plotly pandas requests --quiet

# 启动Streamlit应用
streamlit run streamlit_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --theme.base light \
    --theme.primaryColor "#1E88E5" \
    --theme.backgroundColor "#FFFFFF" \
    --theme.secondaryBackgroundColor "#F0F2F6" \
    --theme.textColor "#262730" \
    --theme.font "sans serif"

echo "✅ 前端服务已启动"
echo "🌐 访问地址: http://localhost:8501"
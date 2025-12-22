# frontend/streamlit_app.py
import streamlit as st
import requests
import json
import pandas as pd
import time
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
import os
import sys

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 页面配置
st.set_page_config(
    page_title="汽车测试用例生成系统",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #424242;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    .section-box {
        background-color: #f5f5f5;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        border-left: 5px solid #1E88E5;
    }
    .test-case-box {
        background-color: #e8f5e8;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border: 1px solid #c8e6c9;
    }
    .step-box {
        background-color: #fff3e0;
        padding: 0.8rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
        border-left: 3px solid #ff9800;
    }
    .metric-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.5rem;
    }
    .status-success {
        color: #4CAF50;
        font-weight: bold;
    }
    .status-processing {
        color: #FF9800;
        font-weight: bold;
    }
    .status-failed {
        color: #F44336;
        font-weight: bold;
    }
    .btn-generate {
        background-color: #1E88E5 !important;
        color: white !important;
        border: none !important;
        padding: 0.5rem 2rem !important;
        border-radius: 5px !important;
        font-weight: bold !important;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

class AutomotiveTestCaseGenerator:
    def __init__(self):
        self.api_base_url = st.session_state.get('api_url', 'http://localhost:8000/api/v1')
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """初始化会话状态"""
        if 'requests_history' not in st.session_state:
            st.session_state.requests_history = []
        if 'generated_cases' not in st.session_state:
            st.session_state.generated_cases = []
        if 'api_status' not in st.session_state:
            st.session_state.api_status = self.check_api_status()
    
    def check_api_status(self):
        """检查API状态"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                return "online"
        except:
            pass
        return "offline"
    
    def display_header(self):
        """显示页眉"""
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<h1 class="main-header">🚗 汽车测试用例生成系统</h1>', unsafe_allow_html=True)
        
        # 显示API状态
        status_col1, status_col2, status_col3 = st.columns([1, 1, 1])
        with status_col2:
            if st.session_state.api_status == "online":
                st.success("✅ API服务在线")
            else:
                st.error("❌ API服务离线")
                st.info("请确保后端服务已启动：`python main.py`")
        
        st.markdown("---")
    
    def display_sidebar(self):
        """显示侧边栏"""
        with st.sidebar:
            st.markdown("### ⚙️ 系统配置")
            
            # API配置
            api_url = st.text_input(
                "API地址",
                value=st.session_state.get('api_url', 'http://localhost:8000'),
                help="后端API服务的地址"
            )
            st.session_state.api_url = api_url
            self.api_base_url = f"{api_url}/api/v1"
            
            # 显示统计信息
            st.markdown("---")
            st.markdown("### 📊 统计信息")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("历史请求", len(st.session_state.requests_history))
            with col2:
                st.metric("已生成用例", len(st.session_state.generated_cases))
            
            # 系统信息
            st.markdown("---")
            st.markdown("### ℹ️ 系统信息")
            st.info("""
            **版本**: 1.0.0  
            **功能**:  
            • 智能测试用例生成  
            • 规范自动分析  
            • 模板匹配与优化  
            • 质量评估与改进建议  
            """)
            
            # 快速操作
            st.markdown("---")
            st.markdown("### ⚡ 快速操作")
            if st.button("🔄 刷新状态", use_container_width=True):
                st.session_state.api_status = self.check_api_status()
                st.rerun()
            
            if st.button("🗑️ 清除历史", use_container_width=True):
                st.session_state.requests_history = []
                st.session_state.generated_cases = []
                st.rerun()
    
    def display_input_section(self):
        """显示输入区域"""
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.markdown('<h3 class="sub-header">📝 输入测试需求</h3>', unsafe_allow_html=True)
        
        # 需求输入
        requirement = st.text_area(
            "测试需求描述",
            height=150,
            placeholder="请输入详细的测试需求，例如：\n"
                      "为VCU控制器设计HIL测试用例，验证Ready模式切换功能，需要符合ISO 26262 ASIL C安全等级要求。\n"
                      "测试应包括正常功能、边界条件和故障注入场景。",
            help="请详细描述测试目标、被测对象、测试场景和特殊要求"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 测试标准选择
            standards = st.multiselect(
                "测试标准",
                options=["ISO 26262", "ISO 21434", "GB/T 18384", "GB/T 18488", "企标", "自定义"],
                default=["ISO 26262"],
                help="选择适用的测试标准"
            )
            
            # 自定义标准输入
            custom_std = st.text_input(
                "自定义标准",
                placeholder="输入其他标准，如：ISO 16750",
                help="输入不在列表中的标准"
            )
            if custom_std:
                standards.append(custom_std)
        
        with col2:
            # 优先级选择
            priority = st.selectbox(
                "优先级",
                options=["高", "中", "低"],
                index=1,
                help="测试用例的优先级"
            )
            
            # 回调URL（可选）
            callback_url = st.text_input(
                "回调URL（可选）",
                placeholder="http://your-server/callback",
                help="测试用例生成完成后的通知地址"
            )
        
        # 上传规范文件
        st.markdown("### 📎 上传规范文档（可选）")
        uploaded_files = st.file_uploader(
            "上传需求规范、设计文档等",
            type=['pdf', 'docx', 'txt', 'xlsx', 'json'],
            accept_multiple_files=True,
            help="支持PDF、Word、Excel、TXT、JSON格式"
        )
        
        # 高级选项
        with st.expander("⚙️ 高级选项"):
            col_a, col_b = st.columns(2)
            with col_a:
                timeout = st.number_input(
                    "超时时间（秒）",
                    min_value=30,
                    max_value=600,
                    value=300,
                    help="生成过程的超时时间"
                )
            
            with col_b:
                max_steps = st.number_input(
                    "最大步骤数",
                    min_value=3,
                    max_value=50,
                    value=10,
                    help="测试用例的最大步骤数"
                )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 生成按钮
        if st.button("🚀 生成测试用例", type="primary", use_container_width=True):
            if not requirement:
                st.error("请输入测试需求！")
                return None
            
            if st.session_state.api_status != "online":
                st.error("API服务不可用，请先启动后端服务！")
                return None
            
            return {
                "requirement": requirement,
                "standards": standards,
                "priority": priority,
                "callback_url": callback_url if callback_url else None,
                "uploaded_files": uploaded_files,
                "timeout": timeout,
                "max_steps": max_steps
            }
        
        return None
    
    def submit_generation_request(self, request_data):
        """提交生成请求"""
        try:
            # 构建请求体
            request_body = {
                "requirement": request_data["requirement"],
                "standards": request_data["standards"],
                "priority": request_data["priority"],
                "callback_url": request_data["callback_url"]
            }
            
            # 显示进度
            progress_bar = st.progress(0, text="提交生成请求...")
            
            # 发送请求
            response = requests.post(
                f"{self.api_base_url}/generate",
                json=request_body,
                timeout=10
            )
            
            if response.status_code == 200:
                progress_bar.progress(30, text="请求已接受，开始处理...")
                result = response.json()
                request_id = result["request_id"]
                
                # 添加到历史记录
                history_entry = {
                    "id": request_id,
                    "requirement": request_data["requirement"][:100] + "...",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "submitted"
                }
                st.session_state.requests_history.append(history_entry)
                
                return request_id
            else:
                st.error(f"请求失败: {response.text}")
                return None
                
        except Exception as e:
            st.error(f"请求异常: {str(e)}")
            return None
    
    def poll_generation_result(self, request_id):
        """轮询生成结果"""
        try:
            max_attempts = 60  # 最多尝试60次
            attempt = 0
            
            with st.spinner("正在生成测试用例..."):
                progress_bar = st.progress(30, text="分析规范需求...")
                
                while attempt < max_attempts:
                    time.sleep(2)  # 每2秒轮询一次
                    attempt += 1
                    
                    # 更新进度
                    if attempt < 20:
                        progress = 30 + attempt * 2
                        progress_bar.progress(min(progress, 80), text=f"处理中... ({attempt}/{max_attempts})")
                    
                    # 查询结果
                    response = requests.get(f"{self.api_base_url}/result/{request_id}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        if result["status"] == "completed":
                            progress_bar.progress(100, text="生成完成！")
                            return result
                        elif result["status"] == "failed":
                            progress_bar.progress(0, text="生成失败")
                            st.error(f"生成失败: {result.get('message', '未知错误')}")
                            return result
                        # 继续轮询...
                    else:
                        st.error(f"查询结果失败: {response.text}")
                        break
            
            st.warning("生成超时，请稍后手动查询结果")
            return None
            
        except Exception as e:
            st.error(f"轮询异常: {str(e)}")
            return None
    
    def display_result(self, result):
        """显示生成结果"""
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.markdown('<h3 class="sub-header">✅ 测试用例生成完成</h3>', unsafe_allow_html=True)
        
        if not result or "result" not in result:
            st.error("结果数据不完整")
            return
        
        test_case_data = result["result"]["test_case"]
        explanations = result["result"].get("explanations", {})
        metrics = result["result"].get("metrics", {})
        
        # 保存到会话状态
        st.session_state.generated_cases.append({
            "id": test_case_data.get("id", "unknown"),
            "name": test_case_data.get("name", "未命名"),
            "timestamp": datetime.now().isoformat(),
            "data": test_case_data
        })
        
        # 创建标签页
        tab1, tab2, tab3, tab4 = st.tabs(["📋 测试用例", "📊 质量评估", "🔍 逻辑解释", "💾 导出"])
        
        with tab1:
            self.display_test_case_details(test_case_data)
        
        with tab2:
            self.display_quality_metrics(metrics)
        
        with tab3:
            self.display_explanations(explanations)
        
        with tab4:
            self.display_export_options(test_case_data, explanations, metrics)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def display_test_case_details(self, test_case):
        """显示测试用例详情"""
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 基本信息")
            info_data = {
                "用例ID": test_case.get("id", "N/A"),
                "名称": test_case.get("name", "N/A"),
                "领域": test_case.get("domain", "N/A"),
                "子系统": test_case.get("subsystem", "N/A"),
                "测试模式": ", ".join(test_case.get("test_patterns", [])),
                "适用标准": ", ".join(test_case.get("standards", [])),
                "创建时间": test_case.get("created_at", "N/A")
            }
            
            for key, value in info_data.items():
                st.info(f"**{key}:** {value}")
        
        with col2:
            st.markdown("#### 前置条件")
            preconditions = test_case.get("preconditions", [])
            if preconditions:
                for i, condition in enumerate(preconditions, 1):
                    st.markdown(f"{i}. {condition}")
            else:
                st.warning("无前置条件")
        
        # 测试步骤
        st.markdown("#### 🛠️ 测试步骤")
        test_steps = test_case.get("test_steps", [])
        if test_steps:
            for step in test_steps:
                self.display_test_step(step)
        else:
            st.warning("无测试步骤")
        
        # 预期结果和通过标准
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown("#### ✅ 预期结果")
            expected_results = test_case.get("expected_results", [])
            if expected_results:
                for i, result in enumerate(expected_results, 1):
                    st.success(f"{i}. {result}")
            else:
                st.warning("无预期结果")
        
        with col4:
            st.markdown("#### 🎯 通过标准")
            pass_criteria = test_case.get("pass_criteria", "N/A")
            st.markdown(f'<div class="test-case-box">{pass_criteria}</div>', unsafe_allow_html=True)
        
        # 测试数据
        if "test_data" in test_case and test_case["test_data"]:
            with st.expander("📊 测试数据详情"):
                st.json(test_case["test_data"])
        
        # 约束条件
        constraints = test_case.get("constraints", [])
        if constraints:
            st.markdown("#### ⚠️ 约束条件")
            for constraint in constraints[:5]:  # 显示前5个
                if isinstance(constraint, dict):
                    content = constraint.get("content", str(constraint))
                else:
                    content = str(constraint)
                st.warning(f"• {content}")
    
    def display_test_step(self, step):
        """显示单个测试步骤"""
        if isinstance(step, dict):
            step_id = step.get("id", "unknown")
            step_num = step.get("step_number", 0)
            action = step.get("action", "无动作描述")
            step_type = step.get("step_type", "unknown")
            expected = step.get("expected_result", "无预期结果")
            verification = step.get("verification_method", "通用验证")
            data = step.get("data", {})
        else:
            # 假设是TestStep对象
            step_id = step.id
            step_num = step.step_number
            action = step.action
            step_type = step.step_type
            expected = step.expected_result
            verification = step.verification_method
            data = step.data
        
        st.markdown(f'<div class="step-box">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            st.markdown(f"**步骤 {step_num}**")
            st.caption(f"类型: {step_type}")
        
        with col2:
            st.markdown(f"**操作:** {action}")
            st.markdown(f"**预期:** {expected}")
            st.markdown(f"**验证:** {verification}")
            
            if data:
                with st.expander("测试数据"):
                    st.json(data)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def display_quality_metrics(self, metrics):
        """显示质量评估指标"""
        if not metrics:
            st.info("无质量评估数据")
            return
        
        # 总体评分
        overall_score = metrics.get("quality_score", 0)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="metric-box">', unsafe_allow_html=True)
            st.markdown("**总体评分**")
            self.display_score_gauge(overall_score)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # 分项指标
        breakdown = metrics.get("breakdown", {})
        
        if breakdown:
            st.markdown("#### 📈 分项指标")
            
            metrics_cols = st.columns(min(len(breakdown), 4))
            metrics_items = list(breakdown.items())
            
            for idx, (metric_name, score) in enumerate(metrics_items):
                col_idx = idx % len(metrics_cols)
                with metrics_cols[col_idx]:
                    self.display_metric_card(metric_name, score)
            
            # 改进建议
            recommendations = metrics.get("recommendations", [])
            if recommendations:
                st.markdown("#### 💡 改进建议")
                for rec in recommendations:
                    priority_icon = {
                        "high": "🔴",
                        "medium": "🟡",
                        "low": "🟢"
                    }.get(rec.get("priority", "medium"), "⚪")
                    
                    st.info(
                        f"{priority_icon} **{rec.get('type', '建议')}**\n\n"
                        f"**建议:** {rec.get('suggestion', '')}\n\n"
                        f"**原因:** {rec.get('reason', '')}"
                    )
    
    def display_score_gauge(self, score):
        """显示评分仪表盘"""
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score * 100,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "分数"},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 60], 'color': "lightgray"},
                    {'range': [60, 80], 'color': "gray"},
                    {'range': [80, 100], 'color': "lightblue"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 80
                }
            }
        ))
        
        fig.update_layout(
            height=200,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def display_metric_card(self, name, score):
        """显示指标卡片"""
        # 翻译指标名称
        name_translation = {
            "completeness": "完整性",
            "executability": "可执行性",
            "constraint_coverage": "约束覆盖",
            "standard_compliance": "标准符合",
            "explanation_quality": "解释质量"
        }
        
        display_name = name_translation.get(name, name)
        
        # 确定颜色
        if score >= 0.8:
            color = "#4CAF50"
            emoji = "✅"
        elif score >= 0.6:
            color = "#FF9800"
            emoji = "⚠️"
        else:
            color = "#F44336"
            emoji = "❌"
        
        st.markdown(f"""
        <div style="
            background-color: {color}10;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid {color};
            margin-bottom: 1rem;
        ">
            <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.5rem;">
                {emoji} {display_name}
            </div>
            <div style="font-size: 1.5rem; font-weight: bold; color: {color};">
                {score * 100:.0f}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def display_explanations(self, explanations):
        """显示逻辑解释"""
        if not explanations:
            st.info("无逻辑解释数据")
            return
        
        explanation_types = {
            "steps": "步骤设计解释",
            "data": "数据选择依据",
            "constraints": "约束处理说明",
            "design_decisions": "设计决策"
        }
        
        for exp_type, title in explanation_types.items():
            if exp_type in explanations and explanations[exp_type]:
                st.markdown(f"#### {title}")
                st.markdown(f'<div class="test-case-box">{explanations[exp_type]}</div>', unsafe_allow_html=True)
    
    def display_export_options(self, test_case, explanations, metrics):
        """显示导出选项"""
        st.markdown("### 📤 导出测试用例")
        
        export_format = st.radio(
            "选择导出格式",
            ["JSON", "Excel", "Markdown", "Word (实验性)"],
            horizontal=True
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 导出JSON", use_container_width=True):
                self.export_json(test_case, explanations, metrics)
        
        with col2:
            if st.button("📊 导出Excel", use_container_width=True):
                self.export_excel(test_case)
        
        with col3:
            if st.button("📝 导出Markdown", use_container_width=True):
                self.export_markdown(test_case)
        
        # 预览区域
        with st.expander("👁️ 预览导出内容"):
            if export_format == "JSON":
                st.json(test_case)
            elif export_format == "Markdown":
                st.markdown(self.generate_markdown(test_case))
    
    def export_json(self, test_case, explanations, metrics):
        """导出为JSON"""
        export_data = {
            "test_case": test_case,
            "explanations": explanations,
            "metrics": metrics,
            "export_time": datetime.now().isoformat(),
            "system": "汽车测试用例生成系统 v1.0"
        }
        
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        
        # 创建下载链接
        b64 = base64.b64encode(json_str.encode()).decode()
        href = f'<a href="data:application/json;base64,{b64}" download="test_case_{test_case["id"]}.json">点击下载JSON文件</a>'
        st.markdown(href, unsafe_allow_html=True)
    
    def export_excel(self, test_case):
        """导出为Excel"""
        try:
            # 创建DataFrame
            data_frames = {}
            
            # 基本信息
            basic_info = {
                "字段": ["用例ID", "名称", "领域", "子系统", "创建时间"],
                "值": [
                    test_case.get("id", ""),
                    test_case.get("name", ""),
                    test_case.get("domain", ""),
                    test_case.get("subsystem", ""),
                    test_case.get("created_at", "")
                ]
            }
            data_frames["基本信息"] = pd.DataFrame(basic_info)
            
            # 测试步骤
            steps_data = []
            for step in test_case.get("test_steps", []):
                if isinstance(step, dict):
                    steps_data.append({
                        "步骤编号": step.get("step_number", ""),
                        "操作": step.get("action", ""),
                        "预期结果": step.get("expected_result", ""),
                        "验证方法": step.get("verification_method", "")
                    })
            
            if steps_data:
                data_frames["测试步骤"] = pd.DataFrame(steps_data)
            
            # 创建Excel写入器
            output = pd.ExcelWriter("test_case_export.xlsx", engine='openpyxl')
            
            for sheet_name, df in data_frames.items():
                df.to_excel(output, sheet_name=sheet_name, index=False)
            
            output.close()
            
            # 提供下载
            with open("test_case_export.xlsx", "rb") as file:
                st.download_button(
                    label="📥 下载Excel文件",
                    data=file,
                    file_name=f"test_case_{test_case['id']}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            # 清理临时文件
            os.remove("test_case_export.xlsx")
            
        except Exception as e:
            st.error(f"导出Excel失败: {str(e)}")
    
    def export_markdown(self, test_case):
        """导出为Markdown"""
        markdown_content = self.generate_markdown(test_case)
        
        # 创建下载链接
        b64 = base64.b64encode(markdown_content.encode()).decode()
        href = f'<a href="data:text/markdown;base64,{b64}" download="test_case_{test_case["id"]}.md">点击下载Markdown文件</a>'
        st.markdown(href, unsafe_allow_html=True)
    
    def generate_markdown(self, test_case):
        """生成Markdown内容"""
        md = f"""# 测试用例: {test_case.get('name', '未命名')}

## 基本信息
- **用例ID**: {test_case.get('id', 'N/A')}
- **领域**: {test_case.get('domain', 'N/A')}
- **子系统**: {test_case.get('subsystem', 'N/A')}
- **测试模式**: {', '.join(test_case.get('test_patterns', []))}
- **适用标准**: {', '.join(test_case.get('standards', []))}
- **创建时间**: {test_case.get('created_at', 'N/A')}

## 前置条件
"""
        
        for condition in test_case.get('preconditions', []):
            md += f"- {condition}\n"
        
        md += "\n## 测试步骤\n"
        
        for step in test_case.get('test_steps', []):
            if isinstance(step, dict):
                step_num = step.get('step_number', '')
                action = step.get('action', '')
                expected = step.get('expected_result', '')
                verification = step.get('verification_method', '')
                
                md += f"### 步骤 {step_num}: {action}\n"
                md += f"- **预期结果**: {expected}\n"
                md += f"- **验证方法**: {verification}\n\n"
        
        md += "## 预期结果\n"
        for result in test_case.get('expected_results', []):
            md += f"- {result}\n"
        
        md += f"\n## 通过标准\n{test_case.get('pass_criteria', 'N/A')}\n"
        
        constraints = test_case.get('constraints', [])
        if constraints:
            md += "\n## 约束条件\n"
            for constraint in constraints[:5]:
                if isinstance(constraint, dict):
                    content = constraint.get('content', str(constraint))
                else:
                    content = str(constraint)
                md += f"- {content}\n"
        
        md += f"\n---\n*生成自: 汽车测试用例生成系统 v1.0*\n"
        
        return md
    
    def display_history(self):
        """显示历史记录"""
        if not st.session_state.requests_history:
            return
        
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.markdown('<h3 class="sub-header">📜 生成历史</h3>', unsafe_allow_html=True)
        
        # 创建历史记录表格
        history_df = pd.DataFrame(st.session_state.requests_history)
        
        if not history_df.empty:
            # 重命名列
            history_df.columns = ['ID', '需求描述', '生成时间', '状态']
            
            # 格式化状态显示
            def format_status(status):
                if status == "submitted":
                    return '<span class="status-processing">处理中</span>'
                elif status == "completed":
                    return '<span class="status-success">已完成</span>'
                elif status == "failed":
                    return '<span class="status-failed">失败</span>'
                else:
                    return status
            
            # 显示表格
            st.markdown(history_df.to_html(escape=False), unsafe_allow_html=True)
        else:
            st.info("暂无历史记录")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def display_recent_cases(self):
        """显示最近生成的用例"""
        if not st.session_state.generated_cases:
            return
        
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.markdown('<h3 class="sub-header">📋 最近生成的用例</h3>', unsafe_allow_html=True)
        
        # 显示最近3个用例
        recent_cases = st.session_state.generated_cases[-3:]
        
        for case in recent_cases:
            with st.expander(f"📄 {case['name']} ({case['id']})"):
                if isinstance(case['data'], dict):
                    st.json(case['data'])
                else:
                    st.text(str(case['data']))
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def run(self):
        """运行主应用"""
        self.display_header()
        self.display_sidebar()
        
        # 主界面布局
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 输入区域
            input_data = self.display_input_section()
            
            if input_data:
                # 提交请求
                request_id = self.submit_generation_request(input_data)
                
                if request_id:
                    # 轮询结果
                    result = self.poll_generation_result(request_id)
                    
                    if result and result["status"] == "completed":
                        # 显示结果
                        self.display_result(result)
        
        with col2:
            # 最近生成的用例
            self.display_recent_cases()
            
            # 快速模板
            st.markdown('<div class="section-box">', unsafe_allow_html=True)
            st.markdown('<h3 class="sub-header">⚡ 快速模板</h3>', unsafe_allow_html=True)
            
            templates = [
                {
                    "name": "VCU Ready模式测试",
                    "requirement": "为VCU控制器设计HIL测试用例，验证Ready模式切换功能，符合ISO 26262 ASIL C要求"
                },
                {
                    "name": "BMS SOC精度测试",
                    "requirement": "为BMS控制器设计测试用例，验证SOC估算精度在±3%以内，包含温度补偿验证"
                },
                {
                    "name": "MCU扭矩响应测试",
                    "requirement": "为MCU控制器设计性能测试用例，验证扭矩响应时间小于50ms，包含过载保护测试"
                }
            ]
            
            for template in templates:
                if st.button(f"📋 {template['name']}", key=f"template_{template['name']}", use_container_width=True):
                    # 这里可以设置到输入框的值
                    st.session_state.last_template = template['requirement']
                    st.info(f"已选择模板: {template['name']}")
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # 历史记录（全宽）
        self.display_history()
        
        # 页脚
        st.markdown("---")
        st.markdown(
            '<div style="text-align: center; color: #666; font-size: 0.8rem;">'
            '🚗 汽车测试用例生成系统 v1.0 | '
            '© 2024 智能测试团队 | '
            '<a href="https://github.com/your-repo" target="_blank">GitHub</a>'
            '</div>',
            unsafe_allow_html=True
        )

def main():
    """主函数"""
    try:
        app = AutomotiveTestCaseGenerator()
        app.run()
    except Exception as e:
        st.error(f"应用运行错误: {str(e)}")
        st.info("请检查后端服务是否正常运行")
        st.code("python main.py", language="bash")

if __name__ == "__main__":
    main()
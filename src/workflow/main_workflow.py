import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from dataclasses import dataclass
import uuid
import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 使用相对导入
from src.api.deepseek_client import DeepSeekClient, DeepSeekConfig
from src.core.specification_analyzer import SpecificationAnalyzer
from src.core.hierarchical_classifier import HierarchicalClassifier
from src.core.knowledge_base import KnowledgeBase
from src.core.template_learner import TemplateLearner
from src.generator.template_selector import TemplateSelector
from src.generator.case_generator import TestCaseGenerator
from src.generator.constraint_integrator import ConstraintIntegrator
from src.core.logic_explainer import LogicExplainer

logger = logging.getLogger(__name__)

@dataclass
class WorkflowConfig:
    """工作流配置"""
    deepseek_api_key: str
    knowledge_base_path: str = "./data/knowledge_base"
    template_db_path: str = "./data/templates"
    max_concurrent_tasks: int = 5
    timeout_seconds: int = 300

@dataclass
class GenerationRequest:
    """生成请求"""
    id: str
    requirement: str
    spec_files: Optional[List[str]] = None
    standards: Optional[List[str]] = None
    user_context: Optional[Dict[str, Any]] = None
    priority: str = "normal"
    callback_url: Optional[str] = None

@dataclass
class GenerationResult:
    """生成结果"""
    request_id: str
    success: bool
    test_case: Optional[Dict[str, Any]] = None
    explanations: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    generated_at: Optional[datetime] = None

class TestCaseGenerationWorkflow:
    """测试用例生成工作流"""
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
        
        # 初始化所有组件
        self._init_components()
        
        # 任务队列和状态跟踪
        self.task_queue = asyncio.Queue()
        self.active_tasks = {}
        self.task_results = {}
        
        logger.info("测试用例生成工作流初始化完成")
    
    def _init_components(self):
        """初始化所有组件"""
        
        # 1. DeepSeek客户端
        deepseek_config = DeepSeekConfig(
            api_key=self.config.deepseek_api_key,
            timeout=self.config.timeout_seconds
        )
        self.deepseek_client = DeepSeekClient(deepseek_config)
        
        # 2. 知识库
        kb_config = {
            "vector_db_path": self.config.knowledge_base_path,
            "relational_db_path": f"{self.config.knowledge_base_path}/knowledge.db",
            "embedding_model": "BAAI/bge-small-zh-v1.5"
        }
        self.knowledge_base = KnowledgeBase(kb_config)
        
        # 3. 模板学习器
        self.template_learner = TemplateLearner(
            template_db=None,  # 需要实际数据库
            case_db=None,      # 需要实际数据库
            history_db=None    # 需要实际数据库
        )
        
        # 4. 规范分析器
        self.spec_analyzer = SpecificationAnalyzer(
            self.deepseek_client,
            self.knowledge_base
        )
        
        # 5. 分层分类器
        self.classifier = HierarchicalClassifier(
            self.deepseek_client,
            self.knowledge_base
        )
        
        # 6. 模板选择器
        self.template_selector = TemplateSelector(
            self.knowledge_base,
            self.template_learner
        )
        
        # 7. 约束集成器
        self.constraint_integrator = ConstraintIntegrator()
        
        # 8. 测试用例生成器
        self.case_generator = TestCaseGenerator(
            self.deepseek_client,
            self.template_selector,
            self.constraint_integrator
        )
        
        # 9. 逻辑解释器
        self.logic_explainer = LogicExplainer(self.knowledge_base)
        
        logger.info("所有组件初始化完成")
    
    async def start(self):
        """启动工作流"""
        
        logger.info("启动测试用例生成工作流")
        
        # 启动任务处理器
        task_handlers = []
        for i in range(self.config.max_concurrent_tasks):
            handler = asyncio.create_task(self._task_handler(f"handler-{i}"))
            task_handlers.append(handler)
        
        logger.info(f"启动 {len(task_handlers)} 个任务处理器")
        
        return task_handlers
    
    async def stop(self):
        """停止工作流"""
        
        logger.info("停止测试用例生成工作流")
        
        # 等待所有任务完成
        await self.task_queue.join()
        
        logger.info("所有任务处理完成")
    
    async def submit_request(self, request: GenerationRequest) -> str:
        """提交生成请求"""
        
        # 生成请求ID
        if not request.id:
            request.id = str(uuid.uuid4())
        
        # 添加到任务队列
        await self.task_queue.put(request)
        
        logger.info(f"提交生成请求: {request.id}")
        
        return request.id
    
    async def get_result(self, request_id: str) -> Optional[GenerationResult]:
        """获取生成结果"""
        
        return self.task_results.get(request_id)
    
    async def _task_handler(self, handler_id: str):
        """任务处理器"""
        
        logger.info(f"任务处理器 {handler_id} 启动")
        
        while True:
            try:
                # 获取任务
                request = await self.task_queue.get()
                
                logger.info(f"处理器 {handler_id} 开始处理请求: {request.id}")
                
                # 处理请求
                result = await self._process_request(request)
                
                # 存储结果
                self.task_results[request.id] = result
                
                # 通知回调（如果存在）
                if request.callback_url:
                    await self._notify_callback(request.callback_url, result)
                
                # 标记任务完成
                self.task_queue.task_done()
                
                logger.info(f"处理器 {handler_id} 完成请求: {request.id}")
                
            except asyncio.CancelledError:
                logger.info(f"处理器 {handler_id} 被取消")
                break
                
            except Exception as e:
                logger.error(f"处理器 {handler_id} 处理失败: {str(e)}")
                self.task_queue.task_done()
    
    async def _process_request(self, request: GenerationRequest) -> GenerationResult:
        """处理单个生成请求"""
        
        start_time = datetime.now()
        
        try:
            logger.info(f"开始处理请求 {request.id}")
            
            # 阶段1: 规范分析
            logger.info(f"请求 {request.id}: 阶段1 - 规范分析")
            spec_analysis = await self.spec_analyzer.analyze(
                requirement=request.requirement,
                spec_files=request.spec_files,
                selected_standards=request.standards
            )
            
            # 阶段2: 分层分类
            logger.info(f"请求 {request.id}: 阶段2 - 分层分类")
            classification = await self.classifier.classify(
                requirement=request.requirement,
                spec_analysis=spec_analysis
            )
            
            # 阶段3: 模板学习与选择
            logger.info(f"请求 {request.id}: 阶段3 - 模板选择")
            template, template_score, alternatives = await self.template_selector.select_template(
                requirement=request.requirement,
                classification=classification,
                spec_analysis=spec_analysis
            )
            
            # 阶段4: 测试用例生成
            logger.info(f"请求 {request.id}: 阶段4 - 用例生成")
            test_case = await self.case_generator.generate_test_case(
                requirement=request.requirement,
                classification=classification,
                spec_analysis=spec_analysis,
                template=template
            )
            
            # 阶段5: 逻辑解释生成
            logger.info(f"请求 {request.id}: 阶段5 - 逻辑解释")
            explanations = await self.logic_explainer.generate_explanations(
                test_case=test_case,
                classification=classification,
                spec_analysis=spec_analysis
            )
            
            # 阶段6: 质量评估
            logger.info(f"请求 {request.id}: 阶段6 - 质量评估")
            metrics = await self._evaluate_quality(
                test_case, explanations, classification, spec_analysis
            )
            
            # 阶段7: 模板学习更新
            logger.info(f"请求 {request.id}: 阶段7 - 模板学习")
            await self._update_template_learning(test_case, template, classification)
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 构建结果
            result = GenerationResult(
                request_id=request.id,
                success=True,
                test_case=test_case,
                explanations=explanations,
                metrics=metrics,
                execution_time=execution_time,
                generated_at=datetime.now()
            )
            
            logger.info(f"请求 {request.id} 处理成功，耗时: {execution_time:.2f}秒")
            
            return result
            
        except Exception as e:
            logger.error(f"请求 {request.id} 处理失败: {str(e)}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return GenerationResult(
                request_id=request.id,
                success=False,
                error=str(e),
                execution_time=execution_time,
                generated_at=datetime.now()
            )
    
    async def _evaluate_quality(self,
                               test_case: Dict[str, Any],
                               explanations: Dict[str, Any],
                               classification: Any,
                               spec_analysis: Any) -> Dict[str, Any]:
        """评估生成质量"""
        
        metrics = {
            "quality_score": 0.0,
            "breakdown": {},
            "recommendations": []
        }
        
        try:
            # 1. 完整性评估
            completeness_score = self._evaluate_completeness(test_case)
            metrics["breakdown"]["completeness"] = completeness_score
            
            # 2. 可执行性评估
            executability_score = self._evaluate_executability(test_case)
            metrics["breakdown"]["executability"] = executability_score
            
            # 3. 约束覆盖率
            constraint_coverage = self._evaluate_constraint_coverage(
                test_case, spec_analysis.extracted_constraints
            )
            metrics["breakdown"]["constraint_coverage"] = constraint_coverage
            
            # 4. 标准符合性
            standard_compliance = self._evaluate_standard_compliance(
                test_case, classification.standards
            )
            metrics["breakdown"]["standard_compliance"] = standard_compliance
            
            # 5. 解释质量
            explanation_quality = self._evaluate_explanation_quality(explanations)
            metrics["breakdown"]["explanation_quality"] = explanation_quality
            
            # 计算综合评分
            weights = {
                "completeness": 0.25,
                "executability": 0.25,
                "constraint_coverage": 0.20,
                "standard_compliance": 0.20,
                "explanation_quality": 0.10
            }
            
            total_score = 0.0
            for metric, score in metrics["breakdown"].items():
                total_score += score * weights.get(metric, 0.0)
            
            metrics["quality_score"] = round(total_score, 2)
            
            # 生成改进建议
            metrics["recommendations"] = self._generate_improvement_recommendations(
                metrics["breakdown"]
            )
            
        except Exception as e:
            logger.error(f"质量评估失败: {str(e)}")
            metrics["error"] = str(e)
        
        return metrics
    
    def _evaluate_completeness(self, test_case: Dict[str, Any]) -> float:
        """评估完整性"""
        
        required_sections = ["preconditions", "test_steps", "expected_results", "pass_criteria"]
        present_sections = 0
        
        for section in required_sections:
            if section in test_case and test_case[section]:
                present_sections += 1
        
        # 检查测试步骤是否具体
        steps_score = 0.0
        if "test_steps" in test_case and test_case["test_steps"]:
            steps = test_case["test_steps"]
            if len(steps) >= 3:
                steps_score = min(1.0, len(steps) / 10)  # 最多10步为满分
        
        completeness = (present_sections / len(required_sections)) * 0.7 + steps_score * 0.3
        
        return round(completeness, 2)
    
    def _evaluate_executability(self, test_case: Dict[str, Any]) -> float:
        """评估可执行性"""
        
        executability = 0.0
        
        if "test_steps" in test_case:
            steps = test_case["test_steps"]
            
            # 检查步骤是否有具体数据
            steps_with_data = 0
            for step in steps:
                if isinstance(step, dict) and step.get("data"):
                    steps_with_data += 1
                elif hasattr(step, "data") and step.data:
                    steps_with_data += 1
            
            if steps:
                executability = steps_with_data / len(steps)
        
        return round(executability, 2)
    
    def _evaluate_constraint_coverage(self,
                                     test_case: Dict[str, Any],
                                     constraints: List[Any]) -> float:
        """评估约束覆盖率"""
        
        if not constraints:
            return 1.0  # 没有约束，覆盖率为100%
        
        # 检查测试用例中是否提到了约束
        test_case_text = json.dumps(test_case, ensure_ascii=False).lower()
        
        covered_count = 0
        for constraint in constraints[:10]:  # 最多检查10个约束
            if isinstance(constraint, dict):
                constraint_text = constraint.get("content", "").lower()
            else:
                constraint_text = constraint.content.lower()
            
            # 检查约束关键词是否出现在测试用例中
            keywords = constraint_text.split()[:3]  # 取前3个关键词
            if any(keyword in test_case_text for keyword in keywords if len(keyword) > 1):
                covered_count += 1
        
        coverage = covered_count / min(len(constraints), 10)
        
        return round(coverage, 2)
    
    def _evaluate_standard_compliance(self,
                                     test_case: Dict[str, Any],
                                     standards: List[str]) -> float:
        """评估标准符合性"""
        
        if not standards:
            return 1.0  # 没有标准要求，符合性为100%
        
        test_case_text = json.dumps(test_case, ensure_ascii=False).lower()
        
        compliance_score = 0.0
        for standard in standards:
            standard_lower = standard.lower()
            
            # 检查标准是否被提及
            if standard_lower in test_case_text:
                compliance_score += 1.0 / len(standards)
            
            # 检查标准特定的关键词
            standard_keywords = {
                "iso 26262": ["安全", "asil", "故障", "安全机制"],
                "iso 21434": ["安全", "网络", "威胁", "攻击"],
                "gb/t": ["国标", "标准", "规范"]
            }
            
            if standard_lower in standard_keywords:
                keywords = standard_keywords[standard_lower]
                keyword_count = sum(1 for kw in keywords if kw in test_case_text)
                compliance_score += (keyword_count / len(keywords)) * (0.5 / len(standards))
        
        return round(min(compliance_score, 1.0), 2)
    
    def _evaluate_explanation_quality(self, explanations: Dict[str, Any]) -> float:
        """评估解释质量"""
        
        if not explanations:
            return 0.0
        
        quality_score = 0.0
        
        # 检查解释的完整性
        required_explanations = ["steps", "data", "constraints", "design_decisions"]
        present_explanations = 0
        
        for exp_type in required_explanations:
            if exp_type in explanations and explanations[exp_type]:
                present_explanations += 1
        
        quality_score = present_explanations / len(required_explanations)
        
        return round(quality_score, 2)
    
    def _generate_improvement_recommendations(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """生成改进建议"""
        
        recommendations = []
        
        if metrics.get("completeness", 0) < 0.8:
            recommendations.append({
                "type": "completeness",
                "priority": "high",
                "suggestion": "增加测试步骤或完善测试数据",
                "reason": f"完整性评分较低 ({metrics['completeness']})"
            })
        
        if metrics.get("executability", 0) < 0.7:
            recommendations.append({
                "type": "executability",
                "priority": "high",
                "suggestion": "为测试步骤添加具体数据和验证方法",
                "reason": f"可执行性评分较低 ({metrics['executability']})"
            })
        
        if metrics.get("constraint_coverage", 1.0) < 0.8:
            recommendations.append({
                "type": "constraint_coverage",
                "priority": "medium",
                "suggestion": "增加对约束条件的验证",
                "reason": f"约束覆盖不足 ({metrics['constraint_coverage']})"
            })
        
        if metrics.get("explanation_quality", 0) < 0.6:
            recommendations.append({
                "type": "explanation_quality",
                "priority": "low",
                "suggestion": "完善设计决策和逻辑解释",
                "reason": f"解释质量有待提高 ({metrics['explanation_quality']})"
            })
        
        return recommendations
    
    async def _update_template_learning(self,
                                       test_case: Dict[str, Any],
                                       template: Optional[Dict[str, Any]],
                                       classification: Any):
        """更新模板学习"""
        
        try:
            # 如果测试用例质量高，可以考虑添加到模板库
            if hasattr(test_case, "metadata") and test_case.metadata.get("quality_score", 0) > 80:
                # 这里可以调用模板学习器的更新方法
                pass
                
        except Exception as e:
            logger.error(f"模板学习更新失败: {str(e)}")
    
    async def _notify_callback(self, callback_url: str, result: GenerationResult):
        """通知回调"""
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "request_id": result.request_id,
                    "success": result.success,
                    "generated_at": result.generated_at.isoformat() if result.generated_at else None,
                    "execution_time": result.execution_time
                }
                
                if result.success:
                    payload["test_case_id"] = result.test_case.get("id") if result.test_case else None
                    payload["quality_score"] = result.metrics.get("quality_score") if result.metrics else None
                else:
                    payload["error"] = result.error
                
                async with session.post(callback_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"回调通知成功: {callback_url}")
                    else:
                        logger.warning(f"回调通知失败: {response.status}")
                        
        except Exception as e:
            logger.error(f"回调通知异常: {str(e)}")

# FastAPI集成
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="汽车测试用例生成系统", version="1.0.0")

class GenerationRequestModel(BaseModel):
    """生成请求模型"""
    requirement: str
    spec_files: Optional[List[str]] = None
    standards: Optional[List[str]] = None
    user_context: Optional[Dict[str, Any]] = None
    priority: str = "normal"
    callback_url: Optional[str] = None

class GenerationResponse(BaseModel):
    """生成响应模型"""
    request_id: str
    status: str  # submitted, processing, completed, failed
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    estimated_time: Optional[float] = None

# 全局工作流实例
workflow = None

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    global workflow
    
    # 从环境变量获取配置
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("deepseek")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY环境变量未设置")
    
    # 创建工作流配置
    config = WorkflowConfig(
        deepseek_api_key=api_key,
        knowledge_base_path="./data/knowledge_base",
        max_concurrent_tasks=5
    )
    
    # 创建工作流实例
    workflow = TestCaseGenerationWorkflow(config)
    
    # 启动工作流
    await workflow.start()
    
    logger.info("应用启动完成")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    if workflow:
        await workflow.stop()
    
    logger.info("应用关闭完成")

@app.post("/api/v1/generate", response_model=GenerationResponse)
async def generate_test_case(
    request: GenerationRequestModel,
    background_tasks: BackgroundTasks
):
    """生成测试用例API"""
    
    try:
        # 构建请求对象
        gen_request = GenerationRequest(
            id=str(uuid.uuid4()),
            requirement=request.requirement,
            spec_files=request.spec_files,
            standards=request.standards,
            user_context=request.user_context,
            priority=request.priority,
            callback_url=request.callback_url
        )
        
        # 提交请求
        request_id = await workflow.submit_request(gen_request)
        
        # 在后台处理结果获取（简化实现）
        background_tasks.add_task(_poll_result, request_id)
        
        return GenerationResponse(
            request_id=request_id,
            status="submitted",
            message="生成请求已提交",
            estimated_time=60.0  # 预估时间
        )
        
    except Exception as e:
        logger.error(f"生成请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/result/{request_id}", response_model=GenerationResponse)
async def get_generation_result(request_id: str):
    """获取生成结果"""
    
    result = await workflow.get_result(request_id)
    
    if not result:
        return GenerationResponse(
            request_id=request_id,
            status="processing",
            message="请求正在处理中"
        )
    
    if result.success:
        return GenerationResponse(
            request_id=request_id,
            status="completed",
            message="生成完成",
            result={
                "test_case": result.test_case,
                "explanations": result.explanations,
                "metrics": result.metrics,
                "execution_time": result.execution_time
            }
        )
    else:
        return GenerationResponse(
            request_id=request_id,
            status="failed",
            message=f"生成失败: {result.error}"
        )

@app.get("/api/v1/health")
async def health_check():
    """健康检查"""
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_tasks": len(workflow.active_tasks) if workflow else 0,
        "queue_size": workflow.task_queue.qsize() if workflow else 0
    }

async def _poll_result(request_id: str):
    """轮询结果（简化实现）"""
    
    # 在实际应用中，这里可以设置更复杂的轮询逻辑
    await asyncio.sleep(1)

# 使用示例
async def example_usage():
    """使用示例"""
    
    # 创建工作流
    config = WorkflowConfig(deepseek_api_key="your-api-key")
    workflow = TestCaseGenerationWorkflow(config)
    
    # 启动工作流
    handlers = await workflow.start()
    
    try:
        # 提交生成请求
        request = GenerationRequest(
            id="test-001",
            requirement="为VCU控制器设计HIL测试用例，验证Ready模式切换功能",
            standards=["ISO 26262"]
        )
        
        request_id = await workflow.submit_request(request)
        print(f"提交请求: {request_id}")
        
        # 等待结果
        await asyncio.sleep(2)
        
        # 获取结果
        result = await workflow.get_result(request_id)
        
        if result and result.success:
            print(f"生成成功！用例ID: {result.test_case.get('id')}")
            print(f"质量评分: {result.metrics.get('quality_score')}")
        else:
            print(f"生成失败: {result.error if result else 'Unknown error'}")
            
    finally:
        # 停止工作流
        await workflow.stop()
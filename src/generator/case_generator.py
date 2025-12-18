# src/generator/case_generator.py
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class TestStepType(Enum):
    """测试步骤类型"""
    SETUP = "setup"  # 设置
    STIMULUS = "stimulus"  # 激励
    VERIFICATION = "verification"  # 验证
    DELAY = "delay"  # 延迟
    RECORD = "record"  # 记录
    CLEANUP = "cleanup"  # 清理

@dataclass
class TestStep:
    """测试步骤"""
    id: str
    step_number: int
    action: str
    description: str
    step_type: TestStepType
    data: Dict[str, Any]
    expected_result: str
    verification_method: str
    timeout: Optional[int] = None
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class TestCase:
    """测试用例"""
    id: str
    name: str
    description: str
    domain: str
    subsystem: str
    test_patterns: List[str]
    preconditions: List[str]
    test_steps: List[TestStep]
    expected_results: List[str]
    pass_criteria: str
    test_data: Dict[str, Any]
    constraints: List[Dict[str, Any]]
    standards: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class TestCaseGenerator:
    """测试用例生成器"""
    
    def __init__(self, deepseek_client, template_selector, constraint_integrator):
        self.client = deepseek_client
        self.template_selector = template_selector
        self.constraint_integrator = constraint_integrator
        
        # 步骤生成模板
        self.step_templates = self._load_step_templates()
        
        # 数据生成规则
        self.data_generation_rules = self._load_data_generation_rules()
        
        logger.info("测试用例生成器初始化完成")
    
    def _load_step_templates(self) -> Dict[str, Dict[str, Any]]:
        """加载步骤模板"""
        
        return {
            "setup": {
                "description": "设置测试环境",
                "action_patterns": [
                    "设置{parameter}为{value}",
                    "初始化{system}",
                    "配置{device}参数",
                    "准备测试环境"
                ],
                "verification_methods": [
                    "环境检查",
                    "参数确认",
                    "状态验证"
                ]
            },
            "stimulus": {
                "description": "施加测试激励",
                "action_patterns": [
                    "发送{signal}信号",
                    "注入{fault}故障",
                    "模拟{scenario}场景",
                    "触发{event}事件"
                ],
                "verification_methods": [
                    "信号确认",
                    "事件触发验证",
                    "状态监控"
                ]
            },
            "verification": {
                "description": "验证系统响应",
                "action_patterns": [
                    "检查{parameter}值",
                    "验证{function}功能",
                    "监控{signal}变化",
                    "确认{state}状态"
                ],
                "verification_methods": [
                    "数据比对",
                    "逻辑验证",
                    "状态检查",
                    "时间测量"
                ]
            },
            "delay": {
                "description": "等待系统响应",
                "action_patterns": [
                    "等待{duration}时间",
                    "暂停执行",
                    "延迟响应"
                ],
                "verification_methods": [
                    "时间监控",
                    "状态检查"
                ]
            },
            "record": {
                "description": "记录测试数据",
                "action_patterns": [
                    "记录{parameter}数据",
                    "保存测试结果",
                    "存储测试日志"
                ],
                "verification_methods": [
                    "数据完整性检查",
                    "文件验证"
                ]
            },
            "cleanup": {
                "description": "清理测试环境",
                "action_patterns": [
                    "恢复{system}状态",
                    "清理测试环境",
                    "重置{device}参数"
                ],
                "verification_methods": [
                    "状态确认",
                    "环境检查"
                ]
            }
        }
    
    def _load_data_generation_rules(self) -> Dict[str, Dict[str, Any]]:
        """加载数据生成规则"""
        
        return {
            "voltage": {
                "normal_range": (9, 16),
                "boundary_values": [6, 9, 12, 16, 18],
                "unit": "V",
                "precision": 0.1
            },
            "current": {
                "normal_range": (0, 100),
                "boundary_values": [0, 50, 100, 150, 200],
                "unit": "A",
                "precision": 0.1
            },
            "temperature": {
                "normal_range": (-40, 85),
                "boundary_values": [-40, -20, 0, 25, 60, 85, 105],
                "unit": "°C",
                "precision": 1
            },
            "time": {
                "normal_range": (10, 1000),
                "boundary_values": [1, 10, 100, 500, 1000, 5000],
                "unit": "ms",
                "precision": 1
            },
            "can_id": {
                "pattern": "0x{hex:04X}",
                "range": (0x100, 0x7FF),
                "examples": [0x100, 0x200, 0x300]
            }
        }
    
    async def generate_test_case(self,
                               requirement: str,
                               classification: ClassificationResult,
                               spec_analysis: SpecificationAnalysisResult,
                               template: Optional[Dict[str, Any]] = None) -> TestCase:
        """生成测试用例"""
        
        logger.info(f"开始生成测试用例: {requirement[:50]}...")
        
        # 1. 选择或创建模板
        if template:
            selected_template = template
        else:
            selected_template = await self.template_selector.select_template(
                requirement, classification, spec_analysis
            )
        
        # 2. 生成测试步骤
        test_steps = await self._generate_test_steps(
            requirement, classification, spec_analysis, selected_template
        )
        
        # 3. 生成测试数据
        test_data = await self._generate_test_data(
            requirement, classification, test_steps
        )
        
        # 4. 生成前置条件和预期结果
        preconditions = await self._generate_preconditions(
            requirement, classification, spec_analysis
        )
        
        expected_results = await self._generate_expected_results(
            requirement, classification, test_steps
        )
        
        # 5. 生成通过标准
        pass_criteria = await self._generate_pass_criteria(
            requirement, classification, expected_results
        )
        
        # 6. 集成约束
        integrated_constraints = await self.constraint_integrator.integrate(
            test_steps, spec_analysis.extracted_constraints
        )
        
        # 7. 构建测试用例
        test_case = self._build_test_case(
            requirement=requirement,
            classification=classification,
            spec_analysis=spec_analysis,
            test_steps=test_steps,
            test_data=test_data,
            preconditions=preconditions,
            expected_results=expected_results,
            pass_criteria=pass_criteria,
            constraints=integrated_constraints,
            template=selected_template
        )
        
        logger.info(f"测试用例生成完成: {test_case.name}")
        
        return test_case
    
    async def _generate_test_steps(self,
                                  requirement: str,
                                  classification: ClassificationResult,
                                  spec_analysis: SpecificationAnalysisResult,
                                  template: Dict[str, Any]) -> List[TestStep]:
        """生成测试步骤"""
        
        steps = []
        
        # 1. 如果模板中有步骤模板，使用模板
        if template and "step_templates" in template:
            step_templates = template["step_templates"]
            
            for i, step_template in enumerate(step_templates[:10]):  # 限制最多10步
                step = await self._generate_step_from_template(
                    step_template=step_template,
                    step_number=i + 1,
                    requirement=requirement,
                    classification=classification,
                    context={"step_index": i, "total_steps": len(step_templates)}
                )
                steps.append(step)
        
        # 2. 否则使用AI生成步骤
        else:
            steps = await self._generate_steps_with_ai(
                requirement, classification, spec_analysis
            )
        
        # 3. 优化步骤顺序和依赖
        steps = self._optimize_step_sequence(steps)
        
        return steps
    
    async def _generate_step_from_template(self,
                                         step_template: Dict[str, Any],
                                         step_number: int,
                                         requirement: str,
                                         classification: ClassificationResult,
                                         context: Dict[str, Any]) -> TestStep:
        """从模板生成步骤"""
        
        # 提取模板信息
        action_template = step_template.get("action_template", "执行测试操作")
        step_type = TestStepType(step_template.get("step_type", "stimulus"))
        verification_method = step_template.get("verification_method", "通用验证")
        
        # 填充模板变量
        filled_action = await self._fill_template_variables(
            template=action_template,
            context={
                "requirement": requirement,
                "domain": classification.domain.value,
                "subsystem": classification.subsystem.value,
                "test_patterns": [p.value for p in classification.test_patterns],
                "step_number": step_number,
                **context
            }
        )
        
        # 生成步骤数据
        step_data = await self._generate_step_data(
            step_type=step_type,
            step_number=step_number,
            action=filled_action,
            classification=classification
        )
        
        # 生成预期结果
        expected_result = await self._generate_expected_result_for_step(
            step_type=step_type,
            action=filled_action,
            step_number=step_number,
            classification=classification
        )
        
        # 创建步骤
        step = TestStep(
            id=f"STEP_{step_number:03d}_{uuid.uuid4().hex[:8]}",
            step_number=step_number,
            action=filled_action,
            description=step_template.get("description", f"步骤{step_number}"),
            step_type=step_type,
            data=step_data,
            expected_result=expected_result,
            verification_method=verification_method,
            timeout=step_template.get("timeout"),
            dependencies=step_template.get("dependencies", [])
        )
        
        return step
    
    async def _fill_template_variables(self,
                                     template: str,
                                     context: Dict[str, Any]) -> str:
        """填充模板变量"""
        
        # 简单变量替换
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in template:
                if isinstance(value, list):
                    template = template.replace(placeholder, ', '.join(value))
                else:
                    template = template.replace(placeholder, str(value))
        
        # 如果还有未填充的变量，使用AI填充
        if "{" in template and "}" in template:
            filled_template = await self._fill_template_with_ai(template, context)
            return filled_template
        
        return template
    
    async def _fill_template_with_ai(self,
                                   template: str,
                                   context: Dict[str, Any]) -> str:
        """使用AI填充模板"""
        
        prompt = f"""
        请根据以下上下文信息，填充模板中的变量：

        模板：{template}

        上下文信息：
        {json.dumps(context, ensure_ascii=False, indent=2)}

        请将模板中的变量（用{{}}括起）替换为具体、合理的值。
        返回填充后的完整文本。
        """
        
        try:
            response = await self.client.chat_completion([
                {"role": "user", "content": prompt}
            ])
            
            filled_template = response["choices"][0]["message"]["content"].strip()
            return filled_template
            
        except Exception as e:
            logger.error(f"AI填充模板失败: {str(e)}")
            # 回退：移除变量
            return re.sub(r'\{.*?\}', '具体值', template)
    
    async def _generate_step_data(self,
                                step_type: TestStepType,
                                step_number: int,
                                action: str,
                                classification: ClassificationResult) -> Dict[str, Any]:
        """生成步骤数据"""
        
        data = {}
        
        # 基于步骤类型生成数据
        if step_type == TestStepType.SETUP:
            data = {
                "environment": {
                    "temperature": self._generate_value("temperature", "normal"),
                    "voltage": self._generate_value("voltage", "normal")
                },
                "initial_state": "准备就绪"
            }
        
        elif step_type == TestStepType.STIMULUS:
            # 分析动作中的信号类型
            if "信号" in action or "发送" in action:
                data = {
                    "signal_type": self._infer_signal_type(action),
                    "signal_value": self._generate_value("voltage", "boundary"),
                    "duration": self._generate_value("time", "normal")
                }
            elif "故障" in action or "注入" in action:
                data = {
                    "fault_type": self._infer_fault_type(action),
                    "injection_method": "软件注入",
                    "duration": self._generate_value("time", "normal")
                }
        
        elif step_type == TestStepType.VERIFICATION:
            data = {
                "monitoring_points": self._generate_monitoring_points(action),
                "sampling_rate": 100,  # Hz
                "duration": self._generate_value("time", "normal")
            }
        
        elif step_type == TestStepType.DELAY:
            data = {
                "duration": self._generate_value("time", "normal"),
                "reason": "等待系统稳定"
            }
        
        elif step_type == TestStepType.RECORD:
            data = {
                "data_points": ["响应时间", "状态值", "错误码"],
                "storage_format": "CSV",
                "sample_count": 100
            }
        
        return data
    
    def _generate_value(self,
                       data_type: str,
                       value_type: str = "normal") -> Any:
        """生成数据值"""
        
        if data_type in self.data_generation_rules:
            rules = self.data_generation_rules[data_type]
            
            if value_type == "normal" and "normal_range" in rules:
                min_val, max_val = rules["normal_range"]
                return round((min_val + max_val) / 2, rules.get("precision", 1))
            
            elif value_type == "boundary" and "boundary_values" in rules:
                import random
                return random.choice(rules["boundary_values"])
        
        # 默认值
        defaults = {
            "voltage": 12.5,
            "current": 10.0,
            "temperature": 25.0,
            "time": 100,
            "can_id": 0x100
        }
        
        return defaults.get(data_type, 0)
    
    def _infer_signal_type(self, action: str) -> str:
        """推断信号类型"""
        
        action_lower = action.lower()
        
        if any(word in action_lower for word in ["can", "总线", "通信"]):
            return "CAN信号"
        elif any(word in action_lower for word in ["电压", "电源"]):
            return "电压信号"
        elif any(word in action_lower for word in ["电流"]):
            return "电流信号"
        elif any(word in action_lower for word in ["温度"]):
            return "温度信号"
        else:
            return "控制信号"
    
    def _infer_fault_type(self, action: str) -> str:
        """推断故障类型"""
        
        action_lower = action.lower()
        
        if any(word in action_lower for word in ["短路"]):
            return "短路故障"
        elif any(word in action_lower for word in ["开路", "断线"]):
            return "开路故障"
        elif any(word in action_lower for word in ["接地"]):
            return "接地故障"
        elif any(word in action_lower for word in ["通信", "can"]):
            return "通信故障"
        else:
            return "通用故障"
    
    def _generate_monitoring_points(self, action: str) -> List[str]:
        """生成监控点"""
        
        monitoring_points = []
        
        # 通用监控点
        monitoring_points.extend([
            "系统状态",
            "错误代码",
            "响应时间"
        ])
        
        # 基于动作的监控点
        action_lower = action.lower()
        
        if any(word in action_lower for word in ["电压", "电源"]):
            monitoring_points.extend(["电源电压", "工作电流"])
        
        if any(word in action_lower for word in ["温度"]):
            monitoring_points.extend(["环境温度", "芯片温度"])
        
        if any(word in action_lower for word in ["can", "通信"]):
            monitoring_points.extend(["CAN通信状态", "报文频率"])
        
        return monitoring_points
    
    async def _generate_expected_result_for_step(self,
                                               step_type: TestStepType,
                                               action: str,
                                               step_number: int,
                                               classification: ClassificationResult) -> str:
        """生成步骤的预期结果"""
        
        # 基于步骤类型的预期结果模板
        templates = {
            TestStepType.SETUP: "测试环境准备就绪，{subsystem}处于初始状态",
            TestStepType.STIMULUS: "成功{action}，系统接收到激励信号",
            TestStepType.VERIFICATION: "系统响应符合预期，{parameter}在允许范围内",
            TestStepType.DELAY: "等待时间结束，系统达到稳定状态",
            TestStepType.RECORD: "测试数据完整记录，数据格式正确",
            TestStepType.CLEANUP: "测试环境恢复完成，系统状态正常"
        }
        
        template = templates.get(step_type, "步骤执行成功")
        
        # 填充变量
        expected_result = template.format(
            subsystem=classification.subsystem.value,
            action=action,
            parameter="性能指标"  # 可以根据实际情况具体化
        )
        
        return expected_result
    
    async def _generate_steps_with_ai(self,
                                     requirement: str,
                                     classification: ClassificationResult,
                                     spec_analysis: SpecificationAnalysisResult) -> List[TestStep]:
        """使用AI生成测试步骤"""
        
        prompt = f"""
        请为以下测试需求生成详细的测试步骤序列：

        测试需求：{requirement}

        测试上下文：
        - 测试领域：{classification.domain.value}
        - 目标系统：{classification.subsystem.value}
        - 测试模式：{', '.join([p.value for p in classification.test_patterns])}
        - 相关标准：{', '.join(classification.standards[:5])}
        - 约束条件：{', '.join(classification.constraints[:5])}

        请生成6-10个具体的测试步骤，每个步骤应包含：
        1. 步骤编号
        2. 具体操作（可执行）
        3. 步骤类型（setup/stimulus/verification/delay/record/cleanup）
        4. 测试数据（如有）
        5. 预期结果
        6. 验证方法

        以JSON数组格式返回，每个元素为：
        {{
            "step_number": 1,
            "action": "具体操作描述",
            "step_type": "步骤类型",
            "data": {{"key": "value"}},
            "expected_result": "预期结果",
            "verification_method": "验证方法",
            "timeout": 1000
        }}
        """
        
        try:
            response = await self.client.chat_completion([
                {"role": "user", "content": prompt}
            ])
            
            steps_data = json.loads(response["choices"][0]["message"]["content"])
            
            steps = []
            for step_data in steps_data:
                step = TestStep(
                    id=f"STEP_{step_data['step_number']:03d}_{uuid.uuid4().hex[:8]}",
                    step_number=step_data["step_number"],
                    action=step_data["action"],
                    description=f"步骤{step_data['step_number']}",
                    step_type=TestStepType(step_data["step_type"]),
                    data=step_data.get("data", {}),
                    expected_result=step_data["expected_result"],
                    verification_method=step_data["verification_method"],
                    timeout=step_data.get("timeout")
                )
                steps.append(step)
            
            return steps
            
        except Exception as e:
            logger.error(f"AI生成步骤失败: {str(e)}")
            # 返回默认步骤
            return self._generate_default_steps(classification)
    
    def _generate_default_steps(self, classification: ClassificationResult) -> List[TestStep]:
        """生成默认步骤"""
        
        steps = []
        
        # 基本步骤序列
        default_sequence = [
            (TestStepType.SETUP, "设置测试环境", {}),
            (TestStepType.STIMULUS, "发送测试激励", {"signal": "测试信号"}),
            (TestStepType.VERIFICATION, "验证系统响应", {"parameter": "响应时间"}),
            (TestStepType.VERIFICATION, "检查功能正确性", {}),
            (TestStepType.RECORD, "记录测试数据", {}),
            (TestStepType.CLEANUP, "恢复测试环境", {})
        ]
        
        for i, (step_type, action, data) in enumerate(default_sequence, 1):
            step = TestStep(
                id=f"STEP_{i:03d}_DEFAULT",
                step_number=i,
                action=action,
                description=f"步骤{i}",
                step_type=step_type,
                data=data,
                expected_result=f"步骤{i}执行成功",
                verification_method="通用验证",
                timeout=1000
            )
            steps.append(step)
        
        return steps
    
    def _optimize_step_sequence(self, steps: List[TestStep]) -> List[TestStep]:
        """优化步骤顺序"""
        
        if not steps:
            return steps
        
        # 1. 确保设置步骤在前
        setup_steps = [s for s in steps if s.step_type == TestStepType.SETUP]
        other_steps = [s for s in steps if s.step_type != TestStepType.SETUP]
        
        # 2. 确保清理步骤在最后
        cleanup_steps = [s for s in other_steps if s.step_type == TestStepType.CLEANUP]
        other_steps = [s for s in other_steps if s.step_type != TestStepType.CLEANUP]
        
        # 3. 重新排序
        optimized_steps = []
        
        # 添加设置步骤
        for i, step in enumerate(setup_steps):
            step.step_number = i + 1
            optimized_steps.append(step)
        
        # 添加其他步骤
        start_idx = len(optimized_steps) + 1
        for i, step in enumerate(other_steps):
            step.step_number = start_idx + i
            optimized_steps.append(step)
        
        # 添加清理步骤
        cleanup_start_idx = len(optimized_steps) + 1
        for i, step in enumerate(cleanup_steps):
            step.step_number = cleanup_start_idx + i
            optimized_steps.append(step)
        
        return optimized_steps
    
    async def _generate_test_data(self,
                                requirement: str,
                                classification: ClassificationResult,
                                test_steps: List[TestStep]) -> Dict[str, Any]:
        """生成测试数据"""
        
        test_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "requirement": requirement[:100],
                "domain": classification.domain.value,
                "subsystem": classification.subsystem.value
            },
            "input_data": {},
            "boundary_values": {},
            "expected_results": {}
        }
        
        # 生成边界值数据
        for data_type, rules in self.data_generation_rules.items():
            if "boundary_values" in rules:
                test_data["boundary_values"][data_type] = {
                    "values": rules["boundary_values"],
                    "unit": rules.get("unit", ""),
                    "description": f"{data_type}边界值"
                }
        
        # 分析步骤中的数据需求
        for step in test_steps:
            if step.data:
                step_key = f"step_{step.step_number}"
                test_data["input_data"][step_key] = step.data
        
        return test_data
    
    async def _generate_preconditions(self,
                                    requirement: str,
                                    classification: ClassificationResult,
                                    spec_analysis: SpecificationAnalysisResult) -> List[str]:
        """生成前置条件"""
        
        preconditions = []
        
        # 1. 基础前置条件
        preconditions.extend([
            f"测试环境准备就绪",
            f"{classification.subsystem.value}处于初始状态",
            f"测试设备连接正常",
            f"测试软件版本正确"
        ])
        
        # 2. 基于领域的特殊前置条件
        if classification.domain == TestDomain.HIL_TESTING:
            preconditions.extend([
                "HIL测试平台已启动",
                "仿真模型加载完成",
                "实时系统运行正常"
            ])
        elif classification.domain == TestDomain.VEHICLE_EE_TESTING:
            preconditions.extend([
                "实车电源接通",
                "测试仪器校准完成",
                "环境条件符合要求"
            ])
        
        # 3. 基于约束的前置条件
        for constraint in classification.constraints[:3]:
            if "环境" in constraint or "温度" in constraint:
                preconditions.append("环境温度符合测试要求")
            elif "电源" in constraint or "电压" in constraint:
                preconditions.append("电源系统稳定可靠")
        
        return list(set(preconditions))  # 去重
    
    async def _generate_expected_results(self,
                                       requirement: str,
                                       classification: ClassificationResult,
                                       test_steps: List[TestStep]) -> List[str]:
        """生成预期结果"""
        
        expected_results = []
        
        # 1. 功能验证结果
        expected_results.append(f"{classification.subsystem.value}功能正常")
        
        # 2. 性能验证结果
        if any(p.value in ["性能测试", "响应测试"] for p in classification.test_patterns):
            expected_results.extend([
                "响应时间符合要求",
                "系统性能满足规格"
            ])
        
        # 3. 安全验证结果
        if any(p.value in ["安全测试", "故障注入测试"] for p in classification.test_patterns):
            expected_results.extend([
                "安全机制正确触发",
                "故障处理符合预期",
                "系统状态安全可控"
            ])
        
        # 4. 从步骤中提取预期结果
        for step in test_steps:
            if step.expected_result and step.expected_result not in expected_results:
                expected_results.append(step.expected_result)
        
        return expected_results[:10]  # 限制数量
    
    async def _generate_pass_criteria(self,
                                     requirement: str,
                                     classification: ClassificationResult,
                                     expected_results: List[str]) -> str:
        """生成通过标准"""
        
        pass_criteria_parts = []
        
        # 基本通过标准
        pass_criteria_parts.append("所有测试步骤执行完成")
        
        # 预期结果满足
        if expected_results:
            pass_criteria_parts.append("所有预期结果均满足")
        
        # 基于标准的要求
        for standard in classification.standards[:2]:
            if standard == "ISO 26262":
                pass_criteria_parts.append("符合ISO 26262相关条款要求")
            elif standard == "ISO 21434":
                pass_criteria_parts.append("符合ISO 21434安全要求")
        
        # 基于约束的要求
        for constraint in classification.constraints[:3]:
            if "时间" in constraint or "响应" in constraint:
                pass_criteria_parts.append("时间性能满足约束要求")
                break
        
        pass_criteria = "；".join(pass_criteria_parts)
        
        return pass_criteria
    
    def _build_test_case(self,
                        requirement: str,
                        classification: ClassificationResult,
                        spec_analysis: SpecificationAnalysisResult,
                        test_steps: List[TestStep],
                        test_data: Dict[str, Any],
                        preconditions: List[str],
                        expected_results: List[str],
                        pass_criteria: str,
                        constraints: List[Dict[str, Any]],
                        template: Optional[Dict[str, Any]]) -> TestCase:
        """构建测试用例"""
        
        # 生成用例ID和名称
        case_id = f"TC_{classification.subsystem.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        case_name = f"{classification.subsystem.value} {classification.test_patterns[0].value}测试"
        
        # 构建约束信息
        constraint_info = []
        for constraint in constraints:
            if isinstance(constraint, dict):
                constraint_info.append(constraint)
            else:
                constraint_info.append(asdict(constraint))
        
        # 构建元数据
        metadata = {
            "generation_method": "template_based" if template else "ai_generated",
            "template_used": template.get("id") if template else None,
            "classification_confidence": classification.confidence,
            "spec_analysis_quality": spec_analysis.quality_score,
            "step_count": len(test_steps),
            "constraint_count": len(constraint_info)
        }
        
        test_case = TestCase(
            id=case_id,
            name=case_name,
            description=requirement,
            domain=classification.domain.value,
            subsystem=classification.subsystem.value,
            test_patterns=[p.value for p in classification.test_patterns],
            preconditions=preconditions,
            test_steps=test_steps,
            expected_results=expected_results,
            pass_criteria=pass_criteria,
            test_data=test_data,
            constraints=constraint_info,
            standards=classification.standards,
            metadata=metadata,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        return test_case

# 使用示例
async def main():
    from deepseek_client import DeepSeekClient, DeepSeekConfig
    from template_selector import TemplateSelector
    from constraint_integrator import ConstraintIntegrator
    
    # 初始化
    config = DeepSeekConfig(api_key="your-api-key")
    client = DeepSeekClient(config)
    
    # 创建依赖组件
    template_selector = TemplateSelector(knowledge_base=None)  # 需要知识库
    constraint_integrator = ConstraintIntegrator()
    
    # 创建生成器
    generator = TestCaseGenerator(client, template_selector, constraint_integrator)
    
    # 模拟分类结果
    from hierarchical_classifier import ClassificationResult, TestDomain, TestSubsystem, TestPattern
    
    classification = ClassificationResult(
        domain=TestDomain.HIL_TESTING,
        subsystem=TestSubsystem.VCU,
        test_patterns=[TestPattern.FUNCTIONAL_TEST, TestPattern.FAULT_INJECTION],
        confidence=0.85,
        reasoning="匹配VCU和HIL测试关键词",
        constraints=["响应时间<100ms", "符合ISO 26262 ASIL C"],
        standards=["ISO 26262"],
        metadata={}
    )
    
    # 模拟规范分析结果
    from specification_analyzer import SpecificationAnalysisResult, Constraint
    
    spec_analysis = SpecificationAnalysisResult(
        requirement="测试需求",
        extracted_constraints=[
            Constraint(id="C001", content="电压范围9-16V", source="spec", type="performance", priority="high", verification_method="测试"),
            Constraint(id="C002", content="温度范围-40~85°C", source="spec", type="environmental", priority="medium", verification_method="测试")
        ],
        identified_standards=["ISO 26262"],
        specification_details={},
        test_requirements=[],
        compliance_checklist=[],
        risk_assessment={},
        quality_score=0.8
    )
    
    # 生成测试用例
    requirement = "为VCU控制器设计HIL测试，验证Ready模式切换功能"
    
    test_case = await generator.generate_test_case(
        requirement=requirement,
        classification=classification,
        spec_analysis=spec_analysis
    )
    
    print(f"生成的测试用例: {test_case.name}")
    print(f"步骤数量: {len(test_case.test_steps)}")
    print(f"前置条件: {len(test_case.preconditions)}")
    print(f"预期结果: {len(test_case.expected_results)}")
    
    # 打印前几个步骤
    for step in test_case.test_steps[:3]:
        print(f"步骤{step.step_number}: {step.action}")
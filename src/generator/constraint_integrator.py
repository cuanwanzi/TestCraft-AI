# src/generator/constraint_integrator.py
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)

@dataclass
class ConstraintIntegrationResult:
    """约束集成结果"""
    integrated_steps: List[Dict[str, Any]]
    constraint_coverage: Dict[str, float]
    verification_points: List[Dict[str, Any]]
    integration_quality: float

class ConstraintIntegrator:
    """约束集成器"""
    
    def __init__(self):
        # 约束映射规则
        self.constraint_mapping_rules = self._load_mapping_rules()
        
        # 验证点生成规则
        self.verification_rules = self._load_verification_rules()
        
        logger.info("约束集成器初始化完成")
    
    def _load_mapping_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载约束映射规则"""
        return {
            "performance": [
                {
                    "pattern": r"响应时间.*?([<=≥].*?\d+.*?(ms|s))",
                    "action": "添加时间测量步骤",
                    "verification": "时间测量"
                },
                {
                    "pattern": r"吞吐量.*?([>=≤].*?\d+)",
                    "action": "添加吞吐量测试步骤",
                    "verification": "数据量统计"
                }
            ],
            "safety": [
                {
                    "pattern": r"安全.*?要求",
                    "action": "添加安全机制验证",
                    "verification": "安全状态检查"
                },
                {
                    "pattern": r"故障.*?检测",
                    "action": "添加故障注入步骤",
                    "verification": "故障响应验证"
                }
            ],
            "reliability": [
                {
                    "pattern": r"MTBF.*?([>=≤].*?\d+)",
                    "action": "添加耐久性测试循环",
                    "verification": "失效统计"
                }
            ],
            "environmental": [
                {
                    "pattern": r"温度.*?([-~].*?\d+.*?[°度]C)",
                    "action": "添加温度变化测试",
                    "verification": "温度监控"
                },
                {
                    "pattern": r"防护等级.*?(IP\d+)",
                    "action": "添加防护性能测试",
                    "verification": "防护等级检查"
                }
            ]
        }
    
    def _load_verification_rules(self) -> Dict[str, Dict[str, Any]]:
        """加载验证点生成规则"""
        return {
            "performance": {
                "verification_type": "数值验证",
                "methods": ["范围检查", "阈值比较", "趋势分析"],
                "tools": ["示波器", "数据采集卡", "分析软件"]
            },
            "safety": {
                "verification_type": "状态验证",
                "methods": ["状态机检查", "故障码读取", "安全状态确认"],
                "tools": ["诊断仪", "安全分析工具", "监控软件"]
            },
            "reliability": {
                "verification_type": "统计验证",
                "methods": ["MTBF计算", "失效率统计", "寿命分析"],
                "tools": ["可靠性分析软件", "数据记录仪", "统计分析工具"]
            }
        }
    
    async def integrate(self,
                       test_steps: List[Dict[str, Any]],
                       constraints: List[Any]) -> List[Dict[str, Any]]:
        """集成约束到测试步骤"""
        
        logger.info(f"开始集成约束，步骤数: {len(test_steps)}, 约束数: {len(constraints)}")
        
        if not constraints:
            logger.info("无约束条件，返回原始步骤")
            return test_steps
        
        # 复制步骤列表
        integrated_steps = [step.copy() if isinstance(step, dict) else step for step in test_steps]
        
        # 分析约束类型分布
        constraint_types = self._analyze_constraint_types(constraints)
        
        # 为每种约束类型集成验证点
        for constraint_type, type_constraints in constraint_types.items():
            if type_constraints:
                integrated_steps = self._integrate_constraint_type(
                    integrated_steps, constraint_type, type_constraints
                )
        
        logger.info(f"约束集成完成，最终步骤数: {len(integrated_steps)}")
        
        return integrated_steps
    
    def _analyze_constraint_types(self, constraints: List[Any]) -> Dict[str, List[Any]]:
        """分析约束类型分布"""
        constraint_types = {}
        
        for constraint in constraints:
            if isinstance(constraint, dict):
                constraint_type = constraint.get("type", "other")
                constraint_content = constraint.get("content", "")
            else:
                # 假设是Constraint对象
                constraint_type = getattr(constraint, "type", "other")
                constraint_content = getattr(constraint, "content", "")
            
            if constraint_type not in constraint_types:
                constraint_types[constraint_type] = []
            
            constraint_types[constraint_type].append({
                "type": constraint_type,
                "content": constraint_content,
                "priority": constraint.get("priority") if isinstance(constraint, dict) else getattr(constraint, "priority", "medium")
            })
        
        return constraint_types
    
    def _integrate_constraint_type(self,
                                  test_steps: List[Dict[str, Any]],
                                  constraint_type: str,
                                  constraints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """集成特定类型的约束"""
        
        if constraint_type not in self.constraint_mapping_rules:
            logger.warning(f"未知约束类型: {constraint_type}")
            return test_steps
        
        mapping_rules = self.constraint_mapping_rules[constraint_type]
        
        # 为每个约束寻找匹配的规则
        for constraint in constraints:
            constraint_content = constraint["content"]
            
            for rule in mapping_rules:
                pattern = rule["pattern"]
                if re.search(pattern, constraint_content, re.IGNORECASE):
                    # 找到匹配规则，集成约束
                    test_steps = self._apply_mapping_rule(
                        test_steps, constraint, rule
                    )
                    break  # 每个约束只应用一个规则
        
        return test_steps
    
    def _apply_mapping_rule(self,
                           test_steps: List[Dict[str, Any]],
                           constraint: Dict[str, Any],
                           rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """应用映射规则"""
        
        constraint_content = constraint["content"]
        action_template = rule["action"]
        verification_method = rule["verification"]
        
        # 寻找合适的插入位置
        insertion_index = self._find_insertion_index(test_steps, constraint["type"])
        
        # 创建新的验证步骤
        verification_step = self._create_verification_step(
            constraint_content=constraint_content,
            action_template=action_template,
            verification_method=verification_method,
            constraint_type=constraint["type"],
            step_number=insertion_index + 1
        )
        
        # 插入步骤
        test_steps.insert(insertion_index, verification_step)
        
        # 重新编号步骤
        for i, step in enumerate(test_steps):
            if isinstance(step, dict):
                step["step_number"] = i + 1
        
        logger.info(f"为约束添加验证步骤: {constraint_content[:50]}...")
        
        return test_steps
    
    def _find_insertion_index(self, test_steps: List[Dict[str, Any]], constraint_type: str) -> int:
        """寻找插入位置"""
        # 默认在最后一个验证步骤之后插入
        last_verification_index = -1
        
        for i, step in enumerate(test_steps):
            if isinstance(step, dict):
                step_type = step.get("step_type", "")
                if step_type == "verification":
                    last_verification_index = i
        
        if last_verification_index >= 0:
            return last_verification_index + 1
        else:
            # 如果没有验证步骤，在刺激步骤之后插入
            for i, step in enumerate(test_steps):
                if isinstance(step, dict):
                    step_type = step.get("step_type", "")
                    if step_type == "stimulus":
                        return i + 1
        
        # 默认在步骤列表末尾插入
        return len(test_steps)
    
    def _create_verification_step(self,
                                 constraint_content: str,
                                 action_template: str,
                                 verification_method: str,
                                 constraint_type: str,
                                 step_number: int) -> Dict[str, Any]:
        """创建验证步骤"""
        
        import uuid
        
        # 从约束内容提取关键信息
        extracted_info = self._extract_constraint_info(constraint_content, constraint_type)
        
        # 填充动作模板
        action = action_template
        if "{constraint}" in action:
            action = action.replace("{constraint}", constraint_content[:50])
        if extracted_info:
            for key, value in extracted_info.items():
                placeholder = f"{{{key}}}"
                if placeholder in action:
                    action = action.replace(placeholder, str(value))
        
        # 构建步骤数据
        step_data = {
            "constraint_source": constraint_content,
            "constraint_type": constraint_type,
            "verification_details": self.verification_rules.get(constraint_type, {}),
            "extracted_info": extracted_info
        }
        
        # 创建步骤
        step = {
            "id": f"VERIFY_{step_number:03d}_{uuid.uuid4().hex[:8]}",
            "step_number": step_number,
            "action": action,
            "description": f"验证约束: {constraint_content[:30]}...",
            "step_type": "verification",
            "data": step_data,
            "expected_result": f"满足约束条件: {constraint_content[:50]}",
            "verification_method": verification_method,
            "timeout": 5000  # 默认5秒超时
        }
        
        return step
    
    def _extract_constraint_info(self, constraint_content: str, constraint_type: str) -> Dict[str, Any]:
        """从约束内容提取信息"""
        extracted_info = {}
        
        # 性能约束提取数值
        if constraint_type == "performance":
            # 提取数值和单位
            number_pattern = r'(\d+(?:\.\d+)?)'
            unit_pattern = r'(ms|s|m/s|Hz|%)'
            
            numbers = re.findall(number_pattern, constraint_content)
            units = re.findall(unit_pattern, constraint_content, re.IGNORECASE)
            
            if numbers:
                extracted_info["value"] = numbers[0]
                if len(numbers) > 1:
                    extracted_info["threshold"] = numbers[1]
            
            if units:
                extracted_info["unit"] = units[0]
        
        # 环境约束提取范围
        elif constraint_type == "environmental":
            range_pattern = r'(-?\d+(?:\.\d+)?)\s*[~-]\s*(-?\d+(?:\.\d+)?)'
            match = re.search(range_pattern, constraint_content)
            if match:
                extracted_info["min_value"] = match.group(1)
                extracted_info["max_value"] = match.group(2)
        
        # 安全约束提取ASIL等级
        elif constraint_type == "safety":
            asil_pattern = r'ASIL-[ABCD]'
            match = re.search(asil_pattern, constraint_content, re.IGNORECASE)
            if match:
                extracted_info["asil_level"] = match.group()
        
        return extracted_info
    
    def calculate_constraint_coverage(self,
                                    test_steps: List[Dict[str, Any]],
                                    constraints: List[Any]) -> Dict[str, float]:
        """计算约束覆盖率"""
        
        if not constraints:
            return {"total_coverage": 1.0, "by_type": {}}
        
        # 统计约束总数
        total_constraints = len(constraints)
        
        # 统计已覆盖约束
        covered_count = 0
        coverage_by_type = {}
        
        # 分析约束类型分布
        constraint_types = self._analyze_constraint_types(constraints)
        
        # 检查测试步骤中的约束引用
        test_steps_text = str(test_steps).lower()
        
        for constraint_type, type_constraints in constraint_types.items():
            type_covered = 0
            
            for constraint in type_constraints:
                constraint_content = constraint["content"].lower()
                
                # 检查约束关键词是否出现在测试步骤中
                keywords = constraint_content.split()[:3]  # 取前3个关键词
                if any(keyword in test_steps_text for keyword in keywords if len(keyword) > 2):
                    type_covered += 1
                    covered_count += 1
            
            # 计算类型覆盖率
            if type_constraints:
                coverage_by_type[constraint_type] = type_covered / len(type_constraints)
        
        # 计算总覆盖率
        total_coverage = covered_count / total_constraints if total_constraints > 0 else 1.0
        
        return {
            "total_coverage": total_coverage,
            "by_type": coverage_by_type
        }
    
    def generate_verification_summary(self,
                                     test_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成验证点摘要"""
        
        verification_points = []
        
        for step in test_steps:
            if isinstance(step, dict):
                step_type = step.get("step_type", "")
                
                if step_type == "verification":
                    verification_point = {
                        "step_number": step.get("step_number"),
                        "description": step.get("description", ""),
                        "verification_method": step.get("verification_method", ""),
                        "constraint_reference": step.get("data", {}).get("constraint_source", ""),
                        "expected_result": step.get("expected_result", "")
                    }
                    verification_points.append(verification_point)
        
        return verification_points

# 使用示例
async def main():
    """使用示例"""
    integrator = ConstraintIntegrator()
    
    # 模拟测试步骤
    test_steps = [
        {
            "id": "STEP_001",
            "step_number": 1,
            "action": "设置测试环境",
            "step_type": "setup",
            "expected_result": "环境准备就绪"
        },
        {
            "id": "STEP_002",
            "step_number": 2,
            "action": "发送CAN信号",
            "step_type": "stimulus",
            "expected_result": "信号发送成功"
        },
        {
            "id": "STEP_003",
            "step_number": 3,
            "action": "验证响应",
            "step_type": "verification",
            "expected_result": "响应正确"
        }
    ]
    
    # 模拟约束
    constraints = [
        {"type": "performance", "content": "响应时间小于100ms", "priority": "high"},
        {"type": "safety", "content": "符合ISO 26262 ASIL C要求", "priority": "high"},
        {"type": "environmental", "content": "温度范围-40~85°C", "priority": "medium"}
    ]
    
    # 集成约束
    integrated_steps = await integrator.integrate(test_steps, constraints)
    
    print(f"原始步骤数: {len(test_steps)}")
    print(f"集成后步骤数: {len(integrated_steps)}")
    
    # 计算覆盖率
    coverage = integrator.calculate_constraint_coverage(integrated_steps, constraints)
    print(f"约束覆盖率: {coverage['total_coverage']:.2f}")
    
    # 生成验证点摘要
    verification_summary = integrator.generate_verification_summary(integrated_steps)
    print(f"验证点数量: {len(verification_summary)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
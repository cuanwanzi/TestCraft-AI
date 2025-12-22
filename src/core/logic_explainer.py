# src/core/logic_explainer.py
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class ExplanationResult:
    """解释结果"""
    steps_explanation: str
    data_explanation: str
    constraints_explanation: str
    design_decisions: str
    recommendations: List[str]
    confidence: float

class LogicExplainer:
    """逻辑解释器"""
    
    def __init__(self, knowledge_base):
        self.knowledge_base = knowledge_base
        
        # 解释模板
        self.explanation_templates = self._load_explanation_templates()
        
        # 设计决策库
        self.design_decisions_db = self._load_design_decisions()
        
        logger.info("逻辑解释器初始化完成")
    
    def _load_explanation_templates(self) -> Dict[str, Dict[str, str]]:
        """加载解释模板"""
        return {
            "steps": {
                "setup": "设置步骤确保测试环境满足{preconditions}，为后续测试提供可靠基础。",
                "stimulus": "激励步骤模拟{scenario}场景，触发被测系统的{function}功能。",
                "verification": "验证步骤检查系统对激励的响应，确保{expected_result}。",
                "sequence": "步骤顺序遵循{pattern}测试模式，确保测试的逻辑性和完整性。"
            },
            "data": {
                "boundary_values": "选择边界值{values}进行测试，覆盖{parameter}的正常和异常范围。",
                "normal_values": "使用正常值{value}验证系统在典型工况下的表现。",
                "special_values": "特殊值{value}用于测试{scenario}场景。"
            },
            "constraints": {
                "performance": "性能约束{constraint}通过{verification_method}进行验证。",
                "safety": "安全约束{constraint}确保系统符合{safety_standard}要求。",
                "compliance": "合规约束{constraint}保证测试满足{standard}标准。"
            }
        }
    
    def _load_design_decisions(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载设计决策库"""
        return {
            "test_sequence_design": [
                {
                    "decision": "先设置后激励",
                    "reason": "确保测试环境稳定后再施加激励",
                    "applicability": ["功能测试", "性能测试"],
                    "confidence": 0.9
                },
                {
                    "decision": "激励后立即验证",
                    "reason": "及时捕捉系统响应，避免状态变化",
                    "applicability": ["响应测试", "实时测试"],
                    "confidence": 0.85
                }
            ],
            "data_selection": [
                {
                    "decision": "包含边界值",
                    "reason": "覆盖系统能力的极限情况",
                    "applicability": ["边界测试", "鲁棒性测试"],
                    "confidence": 0.95
                },
                {
                    "decision": "使用典型值",
                    "reason": "验证系统在正常工况下的表现",
                    "applicability": ["功能测试", "验收测试"],
                    "confidence": 0.8
                }
            ],
            "constraint_handling": [
                {
                    "decision": "高优先级约束优先验证",
                    "reason": "确保关键要求得到满足",
                    "applicability": ["安全测试", "合规测试"],
                    "confidence": 0.9
                }
            ]
        }
    
    async def generate_explanations(self,
                                  test_case: Dict[str, Any],
                                  classification: Any,
                                  spec_analysis: Any) -> Dict[str, Any]:
        """生成逻辑解释"""
        
        logger.info(f"开始生成逻辑解释: {test_case.get('name', '未命名')}")
        
        explanations = {}
        
        try:
            # 1. 步骤设计解释
            steps_explanation = await self._explain_test_steps(
                test_case.get("test_steps", []),
                classification,
                test_case.get("preconditions", [])
            )
            explanations["steps"] = steps_explanation
            
            # 2. 数据选择解释
            data_explanation = await self._explain_test_data(
                test_case.get("test_data", {}),
                classification,
                test_case.get("test_patterns", [])
            )
            explanations["data"] = data_explanation
            
            # 3. 约束处理解释
            constraints_explanation = await self._explain_constraints(
                test_case.get("constraints", []),
                test_case.get("test_steps", []),
                spec_analysis
            )
            explanations["constraints"] = constraints_explanation
            
            # 4. 设计决策说明
            design_decisions = await self._explain_design_decisions(
                test_case,
                classification,
                spec_analysis
            )
            explanations["design_decisions"] = design_decisions
            
            # 5. 生成改进建议
            recommendations = await self._generate_recommendations(
                test_case,
                explanations
            )
            explanations["recommendations"] = recommendations
            
            # 6. 计算置信度
            confidence = self._calculate_explanation_confidence(explanations)
            explanations["confidence"] = confidence
            
            logger.info(f"逻辑解释生成完成，置信度: {confidence:.2f}")
            
        except Exception as e:
            logger.error(f"生成逻辑解释失败: {str(e)}")
            explanations["error"] = str(e)
        
        return explanations
    
    async def _explain_test_steps(self,
                                 test_steps: List[Dict[str, Any]],
                                 classification: Any,
                                 preconditions: List[str]) -> str:
        """解释测试步骤设计"""
        
        if not test_steps:
            return "无测试步骤需要解释。"
        
        explanation_parts = []
        
        # 解释步骤类型分布
        step_types = {}
        for step in test_steps:
            if isinstance(step, dict):
                step_type = step.get("step_type", "unknown")
                if step_type not in step_types:
                    step_types[step_type] = 0
                step_types[step_type] += 1
        
        if step_types:
            step_types_desc = "，".join([f"{count}个{stype}步骤" for stype, count in step_types.items()])
            explanation_parts.append(f"测试包含{step_types_desc}。")
        
        # 解释步骤顺序
        if len(test_steps) >= 3:
            first_steps = []
            for step in test_steps[:3]:
                if isinstance(step, dict):
                    step_type = step.get("step_type", "unknown")
                    first_steps.append(step_type)
            
            sequence_pattern = "->".join(first_steps)
            explanation_parts.append(f"步骤顺序遵循 {sequence_pattern} 模式，确保测试的完整性。")
        
        # 解释关键步骤
        key_steps = []
        for step in test_steps:
            if isinstance(step, dict):
                step_type = step.get("step_type", "")
                action = step.get("action", "")
                
                if step_type == "stimulus" and action:
                    key_steps.append(f"激励步骤 '{action[:30]}...'")
                elif step_type == "verification" and "约束" in str(step.get("data", {})):
                    key_steps.append("约束验证步骤")
        
        if key_steps:
            explanation_parts.append(f"关键步骤包括: {', '.join(key_steps)}。")
        
        # 结合前置条件解释
        if preconditions:
            precond_summary = ", ".join([p[:20] for p in preconditions[:2]])
            explanation_parts.append(f"基于前置条件 '{precond_summary}...' 设计测试步骤。")
        
        return " ".join(explanation_parts)
    
    async def _explain_test_data(self,
                                test_data: Dict[str, Any],
                                classification: Any,
                                test_patterns: List[str]) -> str:
        """解释测试数据选择"""
        
        if not test_data:
            return "无特定测试数据需要解释。"
        
        explanation_parts = []
        
        # 解释边界值数据
        if "boundary_values" in test_data:
            boundary_data = test_data["boundary_values"]
            if isinstance(boundary_data, dict):
                for data_type, values_info in boundary_data.items():
                    if isinstance(values_info, dict) and "values" in values_info:
                        values = values_info["values"]
                        if isinstance(values, list) and values:
                            explanation_parts.append(
                                f"{data_type}边界值选择 {values}，覆盖正常和极限工况。"
                            )
        
        # 解释输入数据
        if "input_data" in test_data:
            input_data = test_data["input_data"]
            if isinstance(input_data, dict) and input_data:
                data_steps = list(input_data.keys())
                explanation_parts.append(
                    f"测试数据分布在 {len(data_steps)} 个步骤中，确保每个关键操作都有数据支持。"
                )
        
        # 解释基于测试模式的数据选择
        if "边界测试" in test_patterns or "Boundary" in str(test_patterns):
            explanation_parts.append("采用边界值分析法，选择参数的上下限进行测试。")
        
        if "故障注入测试" in test_patterns or "Fault" in str(test_patterns):
            explanation_parts.append("包含故障模式数据，验证系统的容错能力。")
        
        # 如果没有具体解释，提供通用说明
        if not explanation_parts:
            explanation_parts.append(
                "测试数据基于被测系统的规格和典型使用场景选择，确保测试的代表性和有效性。"
            )
        
        return " ".join(explanation_parts)
    
    async def _explain_constraints(self,
                                  constraints: List[Any],
                                  test_steps: List[Dict[str, Any]],
                                  spec_analysis: Any) -> str:
        """解释约束处理"""
        
        if not constraints:
            return "无特定约束需要处理。"
        
        explanation_parts = []
        
        # 分析约束类型
        constraint_types = {}
        for constraint in constraints:
            if isinstance(constraint, dict):
                const_type = constraint.get("type", "unknown")
            else:
                const_type = getattr(constraint, "type", "unknown")
            
            if const_type not in constraint_types:
                constraint_types[const_type] = 0
            constraint_types[const_type] += 1
        
        # 解释约束分布
        if constraint_types:
            type_desc = "，".join([f"{count}个{ctype}约束" for ctype, count in constraint_types.items()])
            explanation_parts.append(f"测试需要处理 {type_desc}。")
        
        # 检查约束验证步骤
        verification_steps = []
        for step in test_steps:
            if isinstance(step, dict):
                step_type = step.get("step_type", "")
                data = step.get("data", {})
                
                if step_type == "verification" and isinstance(data, dict):
                    if "constraint_source" in data or "constraint_type" in data:
                        verification_steps.append(step.get("step_number", 0))
        
        if verification_steps:
            verification_desc = "、".join([f"步骤{num}" for num in verification_steps[:3]])
            explanation_parts.append(f"通过 {verification_desc} 等步骤验证关键约束。")
        
        # 解释高优先级约束
        high_priority_constraints = []
        for constraint in constraints:
            if isinstance(constraint, dict):
                priority = constraint.get("priority", "medium")
                content = constraint.get("content", "")[:50]
            else:
                priority = getattr(constraint, "priority", "medium")
                content = getattr(constraint, "content", "")[:50]
            
            if priority == "high" and content:
                high_priority_constraints.append(f"'{content}...'")
        
        if high_priority_constraints:
            explanation_parts.append(
                f"高优先级约束 {', '.join(high_priority_constraints)} 得到重点验证。"
            )
        
        return " ".join(explanation_parts)
    
    async def _explain_design_decisions(self,
                                       test_case: Dict[str, Any],
                                       classification: Any,
                                       spec_analysis: Any) -> str:
        """解释设计决策"""
        
        decisions = []
        
        # 基于测试步骤的设计决策
        test_steps = test_case.get("test_steps", [])
        if test_steps:
            step_types = []
            for step in test_steps[:3]:  # 只看前3个步骤
                if isinstance(step, dict):
                    step_type = step.get("step_type", "")
                    step_types.append(step_type)
            
            if len(step_types) >= 3 and step_types[0] == "setup":
                decisions.append("采用先设置环境、再施加激励、最后验证响应的标准测试流程。")
        
        # 基于测试数据的设计决策
        test_data = test_case.get("test_data", {})
        if "boundary_values" in test_data:
            decisions.append("包含边界值测试数据，确保系统在极限条件下的可靠性。")
        
        # 基于分类结果的设计决策
        classification_dict = self._classification_to_dict(classification)
        if classification_dict.get("domain") == "HIL测试":
            decisions.append("针对HIL测试环境，设计实时性验证和故障注入场景。")
        
        if classification_dict.get("subsystem") == "VCU控制器":
            decisions.append("针对VCU控制器的模式管理特性，设计状态转换测试。")
        
        # 基于标准的设计决策
        standards = test_case.get("standards", [])
        if "ISO 26262" in standards:
            decisions.append("遵循ISO 26262安全标准，设计故障注入和安全机制验证。")
        
        if not decisions:
            decisions.append("基于最佳实践和经验设计测试用例，确保测试的有效性和可重复性。")
        
        return " ".join(decisions)
    
    def _classification_to_dict(self, classification: Any) -> Dict[str, Any]:
        """将分类对象转换为字典"""
        if hasattr(classification, "__dict__"):
            result = classification.__dict__.copy()
            for key, value in result.items():
                if hasattr(value, "value"):
                    result[key] = value.value
                elif isinstance(value, list):
                    result[key] = [item.value if hasattr(item, "value") else item 
                                 for item in value]
        elif isinstance(classification, dict):
            result = classification.copy()
        else:
            result = {}
        return result
    
    async def _generate_recommendations(self,
                                      test_case: Dict[str, Any],
                                      explanations: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        
        recommendations = []
        
        # 检查步骤完整性
        test_steps = test_case.get("test_steps", [])
        if len(test_steps) < 5:
            recommendations.append("建议增加测试步骤，覆盖更多测试场景。")
        
        # 检查数据完整性
        test_data = test_case.get("test_data", {})
        if not test_data.get("boundary_values") and not test_data.get("input_data"):
            recommendations.append("建议补充测试数据，特别是边界值和异常数据。")
        
        # 检查约束覆盖
        constraints = test_case.get("constraints", [])
        if constraints and len(constraints) > 5:
            # 如果约束很多，建议分组验证
            recommendations.append("约束数量较多，建议分组验证以提高测试效率。")
        
        # 基于解释质量
        if explanations.get("steps", "") and len(explanations["steps"]) < 100:
            recommendations.append("步骤解释可以更详细，说明每个步骤的设计意图。")
        
        return recommendations[:3]  # 返回前3个建议
    
    def _calculate_explanation_confidence(self, explanations: Dict[str, Any]) -> float:
        """计算解释置信度"""
        
        required_explanations = ["steps", "data", "constraints", "design_decisions"]
        present_explanations = 0
        
        for exp_type in required_explanations:
            if exp_type in explanations and explanations[exp_type]:
                # 检查解释长度
                if len(str(explanations[exp_type])) > 20:
                    present_explanations += 1
        
        # 基础分数
        base_score = present_explanations / len(required_explanations)
        
        # 质量加分
        quality_bonus = 0.0
        
        # 检查是否有详细建议
        if explanations.get("recommendations"):
            quality_bonus += 0.1
        
        # 检查解释的详细程度
        total_length = sum(len(str(exp)) for exp in explanations.values() if exp)
        if total_length > 500:
            quality_bonus += 0.1
        
        return min(base_score + quality_bonus, 1.0)
    
    def format_explanations_for_display(self, explanations: Dict[str, Any]) -> Dict[str, str]:
        """格式化解释用于显示"""
        
        formatted = {}
        
        # 格式化各个部分
        section_names = {
            "steps": "测试步骤设计解释",
            "data": "测试数据选择依据",
            "constraints": "约束条件处理说明",
            "design_decisions": "设计决策说明",
            "recommendations": "改进建议"
        }
        
        for key, display_name in section_names.items():
            if key in explanations:
                content = explanations[key]
                if isinstance(content, list):
                    formatted[display_name] = "\n".join([f"• {item}" for item in content])
                else:
                    formatted[display_name] = str(content)
        
        # 添加置信度
        if "confidence" in explanations:
            confidence = explanations["confidence"]
            confidence_level = "高" if confidence > 0.8 else "中" if confidence > 0.6 else "低"
            formatted["解释置信度"] = f"{confidence:.1%} ({confidence_level})"
        
        return formatted

# 使用示例
async def main():
    """使用示例"""
    from knowledge_base import KnowledgeBase
    
    # 初始化知识库
    knowledge_base = KnowledgeBase({
        "vector_db_path": "./data/knowledge_base",
        "relational_db_path": "./data/knowledge_base/knowledge.db"
    })
    
    # 创建解释器
    explainer = LogicExplainer(knowledge_base)
    
    # 模拟测试用例
    test_case = {
        "name": "VCU Ready模式测试",
        "test_steps": [
            {
                "step_number": 1,
                "step_type": "setup",
                "action": "设置HIL测试环境，初始化VCU控制器",
                "expected_result": "环境准备就绪"
            },
            {
                "step_number": 2,
                "step_type": "stimulus",
                "action": "发送模式切换CAN信号",
                "expected_result": "信号发送成功"
            },
            {
                "step_number": 3,
                "step_type": "verification",
                "action": "验证VCU进入Ready模式",
                "expected_result": "模式切换成功",
                "data": {
                    "constraint_source": "响应时间小于100ms"
                }
            }
        ],
        "test_data": {
            "boundary_values": {
                "voltage": {"values": [9, 12, 16]}
            }
        },
        "constraints": [
            {"type": "performance", "content": "响应时间小于100ms", "priority": "high"}
        ],
        "standards": ["ISO 26262"],
        "preconditions": ["HIL平台运行正常", "VCU软件版本正确"]
    }
    
    # 模拟分类结果
    class MockClassification:
        domain = "HIL测试"
        subsystem = "VCU控制器"
        test_patterns = ["功能测试"]
    
    classification = MockClassification()
    
    # 模拟规范分析
    spec_analysis = {
        "extracted_constraints": [
            {"type": "performance", "content": "响应时间小于100ms"}
        ]
    }
    
    # 生成解释
    explanations = await explainer.generate_explanations(
        test_case=test_case,
        classification=classification,
        spec_analysis=spec_analysis
    )
    
    print(f"解释生成完成，置信度: {explanations.get('confidence', 0):.2f}")
    
    # 格式化显示
    formatted = explainer.format_explanations_for_display(explanations)
    for section, content in formatted.items():
        print(f"\n{section}:\n{content}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
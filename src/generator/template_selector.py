# src/generator/template_selector.py
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class TemplateSelectionResult:
    """模板选择结果"""
    template: Optional[Dict[str, Any]]
    score: float
    alternatives: List[Dict[str, Any]]
    reasoning: str

class TemplateSelector:
    """模板选择器"""
    
    def __init__(self, knowledge_base, template_learner):
        self.knowledge_base = knowledge_base
        self.template_learner = template_learner
        
        # 模板库
        self.templates = self._load_templates()
        
        logger.info("模板选择器初始化完成")
    
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """加载模板库"""
        # 简化实现，实际应该从数据库或文件加载
        return {
            "hil_functional_test": {
                "id": "hil_functional_test",
                "name": "HIL功能测试模板",
                "description": "用于HIL环境下的基础功能测试",
                "domain": "HIL测试",
                "applicable_subsystems": ["VCU", "BMS", "MCU"],
                "test_patterns": ["功能测试"],
                "step_templates": [
                    {
                        "step_number": 1,
                        "step_type": "setup",
                        "action_template": "设置测试环境，初始化{controller}控制器",
                        "verification_method": "环境检查"
                    },
                    {
                        "step_number": 2,
                        "step_type": "stimulus",
                        "action_template": "发送{signal}信号到{controller}",
                        "verification_method": "信号确认"
                    },
                    {
                        "step_number": 3,
                        "step_type": "verification",
                        "action_template": "验证{controller}响应",
                        "verification_method": "数据比对"
                    }
                ],
                "default_data": {
                    "voltage": {"normal": 12.0, "boundary": [9, 16]},
                    "response_time": {"max": 100}  # ms
                }
            },
            "fault_injection_test": {
                "id": "fault_injection_test",
                "name": "故障注入测试模板",
                "description": "用于安全相关的故障注入测试",
                "domain": "HIL测试",
                "applicable_subsystems": ["VCU", "BMS", "MCU"],
                "test_patterns": ["故障注入测试", "安全测试"],
                "step_templates": [
                    {
                        "step_number": 1,
                        "step_type": "setup",
                        "action_template": "设置正常工况环境",
                        "verification_method": "状态确认"
                    },
                    {
                        "step_number": 2,
                        "step_type": "stimulus",
                        "action_template": "注入{fault_type}故障",
                        "verification_method": "故障确认"
                    },
                    {
                        "step_number": 3,
                        "step_type": "verification",
                        "action_template": "验证安全机制响应",
                        "verification_method": "安全状态检查"
                    }
                ],
                "default_data": {
                    "fault_types": ["短路", "开路", "通信故障"]
                }
            }
        }
    
    async def select_template(self,
                            requirement: str,
                            classification: Any,
                            spec_analysis: Any) -> Tuple[Optional[Dict[str, Any]], float, List[Dict[str, Any]]]:
        """选择模板"""
        
        logger.info(f"开始选择模板: {requirement[:50]}...")
        
        # 1. 基于分类结果筛选模板
        candidate_templates = self._filter_templates_by_classification(classification)
        
        # 2. 计算匹配分数
        scored_templates = []
        for template_id, template in candidate_templates.items():
            score = self._calculate_template_score(template, requirement, classification, spec_analysis)
            scored_templates.append((template, score))
        
        # 3. 排序并选择
        scored_templates.sort(key=lambda x: x[1], reverse=True)
        
        if scored_templates:
            best_template, best_score = scored_templates[0]
            alternatives = [t for t, s in scored_templates[1:4]]  # 取前3个备选
            
            logger.info(f"选择模板: {best_template['name']}, 分数: {best_score:.2f}")
            
            return best_template, best_score, alternatives
        else:
            logger.warning("未找到合适模板，返回None")
            return None, 0.0, []
    
    def _filter_templates_by_classification(self, classification: Any) -> Dict[str, Dict[str, Any]]:
        """基于分类结果筛选模板"""
        filtered_templates = {}
        
        classification_dict = self._classification_to_dict(classification)
        
        for template_id, template in self.templates.items():
            # 检查领域匹配
            if template.get("domain") == classification_dict.get("domain"):
                filtered_templates[template_id] = template
            # 检查子系统匹配
            elif classification_dict.get("subsystem") in template.get("applicable_subsystems", []):
                filtered_templates[template_id] = template
            # 检查测试模式匹配
            elif any(pattern in template.get("test_patterns", []) 
                    for pattern in classification_dict.get("test_patterns", [])):
                filtered_templates[template_id] = template
        
        # 如果没有匹配的，返回所有模板
        if not filtered_templates:
            return self.templates.copy()
        
        return filtered_templates
    
    def _classification_to_dict(self, classification: Any) -> Dict[str, Any]:
        """将分类对象转换为字典"""
        if hasattr(classification, "__dict__"):
            # 如果是dataclass对象
            result = classification.__dict__.copy()
            # 处理枚举值
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
    
    def _calculate_template_score(self,
                                 template: Dict[str, Any],
                                 requirement: str,
                                 classification: Any,
                                 spec_analysis: Any) -> float:
        """计算模板匹配分数"""
        score = 0.0
        weights = {
            "domain_match": 0.3,
            "subsystem_match": 0.3,
            "pattern_match": 0.2,
            "requirement_similarity": 0.2
        }
        
        classification_dict = self._classification_to_dict(classification)
        
        # 1. 领域匹配
        if template.get("domain") == classification_dict.get("domain"):
            score += weights["domain_match"]
        
        # 2. 子系统匹配
        if classification_dict.get("subsystem") in template.get("applicable_subsystems", []):
            score += weights["subsystem_match"]
        
        # 3. 测试模式匹配
        template_patterns = set(template.get("test_patterns", []))
        classification_patterns = set(classification_dict.get("test_patterns", []))
        if template_patterns.intersection(classification_patterns):
            score += weights["pattern_match"]
        
        # 4. 需求相似度
        requirement_lower = requirement.lower()
        template_name_lower = template.get("name", "").lower()
        template_desc_lower = template.get("description", "").lower()
        
        # 简单关键词匹配
        keywords = ["测试", "验证", "功能", "性能", "安全"]
        matched_keywords = sum(1 for kw in keywords if kw in requirement_lower and kw in template_desc_lower)
        similarity = min(1.0, matched_keywords / 3)
        score += similarity * weights["requirement_similarity"]
        
        return min(score, 1.0)
    
    def get_template_alternatives(self, 
                                 selected_template: Dict[str, Any],
                                 classification: Any) -> List[Dict[str, Any]]:
        """获取备选模板"""
        alternatives = []
        
        classification_dict = self._classification_to_dict(classification)
        
        for template_id, template in self.templates.items():
            if template_id == selected_template.get("id"):
                continue
            
            # 计算相似度
            similarity = self._calculate_template_similarity(selected_template, template)
            
            if similarity > 0.5:  # 相似度阈值
                alternatives.append({
                    "template": template,
                    "similarity": similarity,
                    "reason": self._get_alternative_reason(template, classification_dict)
                })
        
        # 按相似度排序
        alternatives.sort(key=lambda x: x["similarity"], reverse=True)
        
        return alternatives[:3]  # 返回前3个
    
    def _calculate_template_similarity(self, 
                                      template1: Dict[str, Any], 
                                      template2: Dict[str, Any]) -> float:
        """计算模板相似度"""
        similarity = 0.0
        
        # 1. 领域相似度
        if template1.get("domain") == template2.get("domain"):
            similarity += 0.3
        
        # 2. 子系统交集
        subsystems1 = set(template1.get("applicable_subsystems", []))
        subsystems2 = set(template2.get("applicable_subsystems", []))
        if subsystems1.intersection(subsystems2):
            similarity += 0.3
        
        # 3. 测试模式交集
        patterns1 = set(template1.get("test_patterns", []))
        patterns2 = set(template2.get("test_patterns", []))
        if patterns1.intersection(patterns2):
            similarity += 0.2
        
        # 4. 步骤结构相似度
        steps1 = template1.get("step_templates", [])
        steps2 = template2.get("step_templates", [])
        if steps1 and steps2:
            step_types1 = [step.get("step_type") for step in steps1[:3]]
            step_types2 = [step.get("step_type") for step in steps2[:3]]
            if step_types1 == step_types2:
                similarity += 0.2
        
        return min(similarity, 1.0)
    
    def _get_alternative_reason(self, 
                               template: Dict[str, Any], 
                               classification: Dict[str, Any]) -> str:
        """获取备选模板理由"""
        reasons = []
        
        if template.get("domain") == classification.get("domain"):
            reasons.append("相同测试领域")
        
        if classification.get("subsystem") in template.get("applicable_subsystems", []):
            reasons.append("支持相同子系统")
        
        classification_patterns = set(classification.get("test_patterns", []))
        template_patterns = set(template.get("test_patterns", []))
        if classification_patterns.intersection(template_patterns):
            reasons.append("包含相同测试模式")
        
        if reasons:
            return "；".join(reasons)
        else:
            return "通用备选模板"

# 使用示例
async def main():
    """使用示例"""
    selector = TemplateSelector(knowledge_base=None, template_learner=None)
    
    # 模拟分类结果
    class MockClassification:
        domain = "HIL测试"
        subsystem = "VCU控制器"
        test_patterns = ["功能测试", "性能测试"]
    
    classification = MockClassification()
    
    # 模拟规范分析
    spec_analysis = {
        "extracted_constraints": [
            {"type": "performance", "content": "响应时间<100ms"}
        ]
    }
    
    # 选择模板
    requirement = "为VCU控制器设计HIL测试，验证Ready模式切换功能"
    
    template, score, alternatives = await selector.select_template(
        requirement=requirement,
        classification=classification,
        spec_analysis=spec_analysis
    )
    
    if template:
        print(f"选择模板: {template['name']}, 分数: {score:.2f}")
        print(f"备选模板数量: {len(alternatives)}")
    else:
        print("未找到合适模板")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
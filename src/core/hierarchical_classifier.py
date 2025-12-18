# src/core/hierarchical_classifier.py
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging
from dataclasses import dataclass
from datetime import datetime
logger = logging.getLogger(__name__)

class TestDomain(Enum):
    """测试领域枚举"""
    HIL_TESTING = "HIL测试"
    VEHICLE_EE_TESTING = "实车电子电器测试"
    ENERGY_TESTING = "能耗测试"
    BENCH_TESTING = "台架测试"
    ENVIRONMENTAL_TESTING = "环境测试"
    SAFETY_TESTING = "安全测试"

class TestSubsystem(Enum):
    """测试子系统枚举"""
    VCU = "VCU控制器"
    BMS = "BMS控制器"
    MCU = "MCU控制器"
    ESP = "ESP控制器"
    ADAS = "ADAS控制器"
    GATEWAY = "网关控制器"
    POWER_SYSTEM = "电源系统"
    NETWORK_SYSTEM = "网络系统"
    SENSOR = "传感器系统"
    ACTUATOR = "执行器系统"

class TestPattern(Enum):
    """测试模式枚举"""
    FUNCTIONAL_TEST = "功能测试"
    PERFORMANCE_TEST = "性能测试"
    SAFETY_TEST = "安全测试"
    RELIABILITY_TEST = "可靠性测试"
    ENVIRONMENTAL_TEST = "环境测试"
    COMPATIBILITY_TEST = "兼容性测试"
    FAULT_INJECTION = "故障注入测试"
    BOUNDARY_TEST = "边界测试"
    DIAGNOSTIC_TEST = "诊断测试"

@dataclass
class ClassificationResult:
    """分类结果数据类"""
    domain: TestDomain
    subsystem: TestSubsystem
    test_patterns: List[TestPattern]
    confidence: float
    reasoning: str
    constraints: List[str]
    standards: List[str]
    metadata: Dict[str, Any]

class HierarchicalClassifier:
    """分层分类器"""
    
    def __init__(self, deepseek_client, knowledge_base):
        self.client = deepseek_client
        self.knowledge_base = knowledge_base
        
        # 关键词映射
        self.keyword_mappings = self._load_keyword_mappings()
        
        # 规则库
        self.rules = self._load_classification_rules()
        
        logger.info("分层分类器初始化完成")
    
    def _load_keyword_mappings(self) -> Dict[str, Dict[str, List[str]]]:
        """加载关键词映射"""
        
        return {
            "domains": {
                "HIL测试": ["hil", "硬件在环", "故障注入", "信号模拟", "实时仿真"],
                "实车电子电器测试": ["实车", "电子电器", "emc", "电源", "网络", "总线"],
                "能耗测试": ["能耗", "续航", "电耗", "wltp", "cltc", "充电"],
                "台架测试": ["台架", "耐久", "nvh", "性能", "振动", "盐雾"],
                "环境测试": ["环境", "温度", "湿度", "振动", "防护", "ip等级"],
                "安全测试": ["安全", "iso26262", "asil", "防护", "故障安全"]
            },
            "subsystems": {
                "VCU控制器": ["vcu", "整车控制", "模式管理", "扭矩分配"],
                "BMS控制器": ["bms", "电池管理", "soc", "均衡", "热管理"],
                "MCU控制器": ["mcu", "电机控制", "扭矩", "转速", "效率"],
                "ESP控制器": ["esp", "车身稳定", "abs", "tcs", "esc"],
                "ADAS控制器": ["adas", "驾驶辅助", "aeb", "acc", "lka"],
                "网关控制器": ["网关", "路由", "can", "通信", "网络"],
                "电源系统": ["电源", "电压", "电流", "配电", "保险"],
                "网络系统": ["网络", "can", "lin", "以太网", "通信"],
                "传感器系统": ["传感器", "温度", "压力", "位置", "转速"],
                "执行器系统": ["执行器", "电机", "电磁阀", "继电器", "泵"]
            },
            "patterns": {
                "功能测试": ["功能", "正常", "基本", "操作", "切换"],
                "性能测试": ["性能", "响应", "时间", "效率", "吞吐"],
                "安全测试": ["安全", "故障", "保护", "防护", "失效"],
                "可靠性测试": ["可靠", "耐久", "寿命", "mtbf", "失效"],
                "环境测试": ["环境", "温度", "湿度", "振动", "盐雾"],
                "兼容性测试": ["兼容", "互操作", "接口", "协议", "版本"],
                "故障注入测试": ["故障", "注入", "模拟", "错误", "异常"],
                "边界测试": ["边界", "极限", "最大", "最小", "范围"],
                "诊断测试": ["诊断", "dtc", "故障码", "扫描", "读取"]
            }
        }
    
    def _load_classification_rules(self) -> Dict[str, Any]:
        """加载分类规则"""
        
        rules_path = Path(__file__).parent.parent / "config" / "classification_rules.json"
        
        if rules_path.exists():
            with open(rules_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 默认规则
        return {
            "domain_rules": {
                "如果包含'HIL'或'硬件在环'，则分类为HIL测试": {
                    "condition": ["hil", "硬件在环"],
                    "action": "HIL测试",
                    "confidence": 0.9
                },
                "如果包含'实车'或'电子电器'，则分类为实车电子电器测试": {
                    "condition": ["实车", "电子电器"],
                    "action": "实车电子电器测试",
                    "confidence": 0.8
                }
            },
            "subsystem_rules": {
                "如果包含'VCU'或'整车控制'，则分类为VCU控制器": {
                    "condition": ["vcu", "整车控制"],
                    "action": "VCU控制器",
                    "confidence": 0.9
                },
                "如果包含'BMS'或'电池管理'，则分类为BMS控制器": {
                    "condition": ["bms", "电池管理"],
                    "action": "BMS控制器",
                    "confidence": 0.9
                }
            }
        }
    
    async def classify(self,
                      requirement: str,
                      spec_analysis: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """执行分层分类"""
        
        logger.info(f"开始分类需求: {requirement[:50]}...")
        
        # 1. 基于规则的基础分类
        base_classification = self._rule_based_classification(requirement)
        
        # 2. 基于AI的增强分类
        enhanced_classification = await self._ai_enhanced_classification(
            requirement, base_classification, spec_analysis
        )
        
        # 3. 知识库验证
        validated_classification = await self._validate_with_knowledge_base(
            enhanced_classification, requirement
        )
        
        # 4. 构建最终结果
        result = self._build_classification_result(
            validated_classification, requirement, spec_analysis
        )
        
        logger.info(f"分类完成: {result.domain.value} - {result.subsystem.value}")
        
        return result
    
    def _rule_based_classification(self, requirement: str) -> Dict[str, Any]:
        """基于规则的分类"""
        
        requirement_lower = requirement.lower()
        
        # 初始化分类结果
        classification = {
            "domain": None,
            "subsystem": None,
            "test_patterns": [],
            "confidence": 0.0,
            "keywords": []
        }
        
        # 领域分类
        domain_scores = {}
        for domain, keywords in self.keyword_mappings["domains"].items():
            score = sum(1 for kw in keywords if kw in requirement_lower)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            best_domain = max(domain_scores.items(), key=lambda x: x[1])[0]
            classification["domain"] = TestDomain(best_domain)
            classification["confidence"] = min(1.0, domain_scores[best_domain] / 3)
        
        # 子系统分类
        subsystem_scores = {}
        for subsystem, keywords in self.keyword_mappings["subsystems"].items():
            score = sum(1 for kw in keywords if kw in requirement_lower)
            if score > 0:
                subsystem_scores[subsystem] = score
        
        if subsystem_scores:
            best_subsystem = max(subsystem_scores.items(), key=lambda x: x[1])[0]
            classification["subsystem"] = TestSubsystem(best_subsystem)
            classification["confidence"] = (
                classification["confidence"] * 0.6 + 
                min(1.0, subsystem_scores[best_subsystem] / 2) * 0.4
            )
        
        # 测试模式分类
        pattern_scores = {}
        for pattern, keywords in self.keyword_mappings["patterns"].items():
            score = sum(1 for kw in keywords if kw in requirement_lower)
            if score > 0:
                pattern_scores[pattern] = score
        
        # 选择得分最高的前3个模式
        sorted_patterns = sorted(pattern_scores.items(), key=lambda x: x[1], reverse=True)
        for pattern_name, score in sorted_patterns[:3]:
            if score > 0:
                classification["test_patterns"].append(TestPattern(pattern_name))
        
        return classification
    
    async def _ai_enhanced_classification(self,
                                         requirement: str,
                                         base_classification: Dict[str, Any],
                                         spec_analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """基于AI的增强分类"""
        
        # 如果基础分类置信度足够高，直接返回
        if base_classification["confidence"] > 0.8:
            return base_classification
        
        prompt = f"""
        作为汽车测试专家，请分析以下测试需求，确定其所属的测试领域、子系统和测试模式：

        测试需求：{requirement}

        可选的测试领域：{', '.join([d.value for d in TestDomain])}
        可选的子系统：{', '.join([s.value for s in TestSubsystem])}
        可选的测试模式：{', '.join([p.value for p in TestPattern])}

        请基于以下规则进行分析：
        1. 首先确定测试领域（主要测试类型）
        2. 然后确定子系统（被测试的具体对象）
        3. 最后确定适用的测试模式（测试方法）
        4. 考虑测试的完整性和有效性

        以JSON格式返回：
        {{
            "domain": "领域名称",
            "subsystem": "子系统名称",
            "test_patterns": ["模式1", "模式2", "模式3"],
            "confidence": 0.95,
            "reasoning": "分类理由",
            "constraints": ["约束1", "约束2"],
            "standards": ["标准1", "标准2"]
        }}
        """
        
        try:
            response = await self.client.chat_completion([
                {"role": "user", "content": prompt}
            ])
            
            ai_result = json.loads(response["choices"][0]["message"]["content"])
            
            # 合并AI分类结果
            enhanced = base_classification.copy()
            
            if ai_result.get("domain"):
                try:
                    enhanced["domain"] = TestDomain(ai_result["domain"])
                except ValueError:
                    pass
            
            if ai_result.get("subsystem"):
                try:
                    enhanced["subsystem"] = TestSubsystem(ai_result["subsystem"])
                except ValueError:
                    pass
            
            if ai_result.get("test_patterns"):
                patterns = []
                for pattern_name in ai_result["test_patterns"][:3]:
                    try:
                        patterns.append(TestPattern(pattern_name))
                    except ValueError:
                        continue
                enhanced["test_patterns"] = patterns
            
            enhanced["confidence"] = max(
                enhanced["confidence"],
                ai_result.get("confidence", 0.0)
            )
            
            enhanced["ai_reasoning"] = ai_result.get("reasoning", "")
            enhanced["ai_constraints"] = ai_result.get("constraints", [])
            enhanced["ai_standards"] = ai_result.get("standards", [])
            
            return enhanced
            
        except Exception as e:
            logger.error(f"AI分类失败: {str(e)}")
            return base_classification
    
    async def _validate_with_knowledge_base(self,
                                          classification: Dict[str, Any],
                                          requirement: str) -> Dict[str, Any]:
        """使用知识库验证分类结果"""
        
        validated = classification.copy()
        
        # 如果领域或子系统未确定，尝试从知识库推断
        if not validated["domain"] or not validated["subsystem"]:
            # 搜索相关知识
            knowledge_items = self.knowledge_base.search_knowledge(
                query=requirement,
                top_k=5
            )
            
            if knowledge_items:
                # 分析知识项的领域和子系统分布
                domain_counts = {}
                subsystem_counts = {}
                
                for item in knowledge_items:
                    domain = item.domain
                    if domain not in domain_counts:
                        domain_counts[domain] = 0
                    domain_counts[domain] += 1
                    
                    # 从标签推断子系统
                    for tag in item.tags:
                        for subsystem_name in self.keyword_mappings["subsystems"].keys():
                            if subsystem_name in tag:
                                if subsystem_name not in subsystem_counts:
                                    subsystem_counts[subsystem_name] = 0
                                subsystem_counts[subsystem_name] += 1
                
                # 选择最常见的领域和子系统
                if not validated["domain"] and domain_counts:
                    most_common_domain = max(domain_counts.items(), key=lambda x: x[1])[0]
                    try:
                        validated["domain"] = TestDomain(most_common_domain)
                    except ValueError:
                        pass
                
                if not validated["subsystem"] and subsystem_counts:
                    most_common_subsystem = max(subsystem_counts.items(), key=lambda x: x[1])[0]
                    try:
                        validated["subsystem"] = TestSubsystem(most_common_subsystem)
                    except ValueError:
                        pass
        
        return validated
    
    def _build_classification_result(self,
                                   classification: Dict[str, Any],
                                   requirement: str,
                                   spec_analysis: Optional[Dict[str, Any]]) -> ClassificationResult:
        """构建分类结果"""
        
        # 确定领域和子系统
        domain = classification.get("domain")
        subsystem = classification.get("subsystem")
        
        # 如果仍未确定，使用默认值
        if not domain:
            domain = TestDomain.HIL_TESTING
        
        if not subsystem:
            subsystem = TestSubsystem.VCU
        
        # 构建测试模式列表
        test_patterns = classification.get("test_patterns", [])
        if not test_patterns:
            test_patterns = [TestPattern.FUNCTIONAL_TEST]
        
        # 构建推理说明
        reasoning_parts = []
        
        if classification.get("ai_reasoning"):
            reasoning_parts.append(classification["ai_reasoning"])
        
        # 添加关键词匹配说明
        requirement_lower = requirement.lower()
        matched_keywords = []
        
        # 检查领域关键词
        domain_keywords = self.keyword_mappings["domains"].get(domain.value, [])
        matched = [kw for kw in domain_keywords if kw in requirement_lower]
        if matched:
            reasoning_parts.append(f"匹配领域关键词: {', '.join(matched[:3])}")
        
        # 检查子系统关键词
        subsystem_keywords = self.keyword_mappings["subsystems"].get(subsystem.value, [])
        matched = [kw for kw in subsystem_keywords if kw in requirement_lower]
        if matched:
            reasoning_parts.append(f"匹配子系统关键词: {', '.join(matched[:3])}")
        
        reasoning = "；".join(reasoning_parts) if reasoning_parts else "基于综合分析和历史经验"
        
        # 收集约束
        constraints = classification.get("ai_constraints", [])
        if spec_analysis and "extracted_constraints" in spec_analysis:
            constraints.extend([c.content for c in spec_analysis["extracted_constraints"][:5]])
        
        # 收集标准
        standards = classification.get("ai_standards", [])
        if spec_analysis and "identified_standards" in spec_analysis:
            standards.extend(spec_analysis["identified_standards"])
        
        # 构建元数据
        metadata = {
            "classification_method": "ai_enhanced" if classification.get("ai_reasoning") else "rule_based",
            "confidence_breakdown": {
                "rule_based": classification.get("confidence", 0.0),
                "ai_enhanced": classification.get("ai_confidence", 0.0)
            },
            "matched_keywords": {
                "domain": domain_keywords,
                "subsystem": subsystem_keywords
            }
        }
        
        return ClassificationResult(
            domain=domain,
            subsystem=subsystem,
            test_patterns=test_patterns,
            confidence=classification.get("confidence", 0.7),
            reasoning=reasoning,
            constraints=list(set(constraints)),
            standards=list(set(standards)),
            metadata=metadata
        )
    
    def get_recommended_test_types(self,
                                  classification: ClassificationResult) -> List[Dict[str, Any]]:
        """获取推荐的测试类型"""
        
        recommendations = []
        
        # 基于领域推荐
        domain_recommendations = {
            TestDomain.HIL_TESTING: [
                {"type": "功能测试", "priority": "高", "reason": "验证基本功能正确性"},
                {"type": "故障注入测试", "priority": "高", "reason": "验证安全机制"},
                {"type": "边界测试", "priority": "中", "reason": "验证边界条件处理"}
            ],
            TestDomain.VEHICLE_EE_TESTING: [
                {"type": "EMC测试", "priority": "高", "reason": "验证电磁兼容性"},
                {"type": "电源测试", "priority": "高", "reason": "验证电源系统可靠性"},
                {"type": "网络测试", "priority": "中", "reason": "验证通信可靠性"}
            ],
            TestDomain.ENERGY_TESTING: [
                {"type": "续航测试", "priority": "高", "reason": "验证能量消耗"},
                {"type": "充电测试", "priority": "高", "reason": "验证充电性能"},
                {"type": "热管理测试", "priority": "中", "reason": "验证热管理系统"}
            ]
        }
        
        # 添加领域推荐
        if classification.domain in domain_recommendations:
            recommendations.extend(domain_recommendations[classification.domain])
        
        # 基于子系统推荐
        subsystem_recommendations = {
            TestSubsystem.VCU: [
                {"type": "模式切换测试", "priority": "高", "reason": "验证整车模式管理"},
                {"type": "扭矩控制测试", "priority": "高", "reason": "验证扭矩分配逻辑"}
            ],
            TestSubsystem.BMS: [
                {"type": "SOC估算测试", "priority": "高", "reason": "验证电池状态估算精度"},
                {"type": "均衡控制测试", "priority": "中", "reason": "验证电池均衡功能"}
            ],
            TestSubsystem.MCU: [
                {"type": "扭矩响应测试", "priority": "高", "reason": "验证电机响应性能"},
                {"type": "效率测试", "priority": "中", "reason": "验证电机效率"}
            ]
        }
        
        # 添加子系统推荐
        if classification.subsystem in subsystem_recommendations:
            recommendations.extend(subsystem_recommendations[classification.subsystem])
        
        # 基于标准推荐
        for standard in classification.standards:
            if standard == "ISO 26262":
                recommendations.append({
                    "type": "安全机制验证测试",
                    "priority": "高",
                    "reason": "ISO 26262要求的安全机制验证"
                })
            elif standard == "ISO 21434":
                recommendations.append({
                    "type": "网络安全测试",
                    "priority": "高",
                    "reason": "ISO 21434要求的网络安全验证"
                })
        
        # 去重
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            key = (rec["type"], rec["reason"])
            if key not in seen:
                seen.add(key)
                unique_recommendations.append(rec)
        
        return unique_recommendations

# 使用示例
async def main():
    from deepseek_client import DeepSeekClient, DeepSeekConfig
    from knowledge_base import KnowledgeBase
    
    # 初始化
    config = DeepSeekConfig(api_key="your-api-key")
    client = DeepSeekClient(config)
    knowledge_base = KnowledgeBase({
        "vector_db_path": "./data/knowledge_base",
        "relational_db_path": "./data/knowledge_base/knowledge.db"
    })
    
    # 创建分类器
    classifier = HierarchicalClassifier(client, knowledge_base)
    
    # 测试分类
    requirement = "为VCU控制器设计HIL测试用例，验证Ready模式切换功能，需要符合ISO 26262 ASIL C要求"
    
    result = await classifier.classify(requirement)
    
    print(f"分类结果:")
    print(f"- 领域: {result.domain.value}")
    print(f"- 子系统: {result.subsystem.value}")
    print(f"- 测试模式: {[p.value for p in result.test_patterns]}")
    print(f"- 置信度: {result.confidence:.2f}")
    print(f"- 理由: {result.reasoning}")
    
    # 获取推荐测试类型
    recommendations = classifier.get_recommended_test_types(result)
    print(f"\n推荐测试类型:")
    for rec in recommendations:
        print(f"- {rec['type']} ({rec['priority']}): {rec['reason']}")
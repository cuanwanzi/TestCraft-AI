# src/core/template_learner.py
import json
import logging
import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class TemplateLearningResult:
    """模板学习结果"""
    success: bool
    learned_patterns: List[Dict[str, Any]]
    updated_templates: List[str]
    confidence_score: float
    recommendations: List[str]

@dataclass
class TemplateUsageRecord:
    """模板使用记录"""
    template_id: str
    requirement: str
    classification: Dict[str, Any]
    test_case: Dict[str, Any]
    quality_score: float
    user_feedback: Optional[float] = None
    generated_at: Optional[datetime] = None

class TemplateLearner:
    """模板学习器"""
    
    def __init__(self, template_db, case_db, history_db):
        self.template_db = template_db
        self.case_db = case_db
        self.history_db = history_db
        
        # 学习参数
        self.learning_rate = 0.1
        self.min_usage_count = 3
        self.quality_threshold = 0.7
        
        # 模式提取规则
        self.pattern_rules = self._load_pattern_rules()
        
        logger.info("模板学习器初始化完成")
    
    def _load_pattern_rules(self) -> Dict[str, Any]:
        """加载模式提取规则"""
        return {
            "step_patterns": {
                "min_similarity": 0.8,
                "min_occurrence": 2,
                "extraction_methods": ["sequence", "structure", "content"]
            },
            "data_patterns": {
                "min_similarity": 0.85,
                "min_occurrence": 2,
                "extraction_methods": ["type", "range", "distribution"]
            },
            "constraint_patterns": {
                "min_similarity": 0.9,
                "min_occurrence": 2,
                "extraction_methods": ["source", "type", "priority"]
            }
        }
    
    def record_template_usage(self, record: TemplateUsageRecord):
        """记录模板使用情况"""
        try:
            if not record.generated_at:
                record.generated_at = datetime.now()
            
            # 这里应该保存到数据库
            # 简化实现：打印日志
            logger.info(f"记录模板使用: {record.template_id}, 质量: {record.quality_score}")
            
            # 检查是否需要学习
            if record.quality_score >= self.quality_threshold:
                self._learn_from_successful_case(record)
            
            return True
            
        except Exception as e:
            logger.error(f"记录模板使用失败: {str(e)}")
            return False
    
    def _learn_from_successful_case(self, record: TemplateUsageRecord):
        """从成功案例中学习"""
        try:
            test_case = record.test_case
            
            # 1. 学习步骤模式
            step_patterns = self._extract_step_patterns(test_case.get("test_steps", []))
            
            # 2. 学习数据模式
            data_patterns = self._extract_data_patterns(test_case.get("test_data", {}))
            
            # 3. 学习约束模式
            constraint_patterns = self._extract_constraint_patterns(test_case.get("constraints", []))
            
            # 4. 合并模式
            learned_patterns = {
                "step_patterns": step_patterns,
                "data_patterns": data_patterns,
                "constraint_patterns": constraint_patterns,
                "metadata": {
                    "source_template": record.template_id,
                    "quality_score": record.quality_score,
                    "classification": record.classification,
                    "learned_at": datetime.now().isoformat()
                }
            }
            
            # 5. 应用学习结果
            self._apply_learned_patterns(learned_patterns, record)
            
            logger.info(f"从案例学习完成，提取模式: {len(step_patterns)} 个步骤模式")
            
        except Exception as e:
            logger.error(f"从案例学习失败: {str(e)}")
    
    def _extract_step_patterns(self, test_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取步骤模式"""
        patterns = []
        
        if not test_steps:
            return patterns
        
        # 分析步骤序列
        step_types = []
        step_actions = []
        
        for step in test_steps:
            if isinstance(step, dict):
                step_types.append(step.get("step_type", "unknown"))
                step_actions.append(step.get("action", ""))
        
        # 检测常见的步骤类型序列
        if len(step_types) >= 3:
            # 检查是否有 "setup -> stimulus -> verification" 模式
            for i in range(len(step_types) - 2):
                seq = step_types[i:i+3]
                if seq == ["setup", "stimulus", "verification"]:
                    patterns.append({
                        "pattern_type": "step_sequence",
                        "sequence": seq,
                        "description": "标准测试序列：设置->激励->验证",
                        "confidence": 0.9
                    })
        
        # 分析步骤内容模式
        action_keywords = {}
        for action in step_actions:
            words = action.split()
            for word in words:
                if len(word) > 2:  # 忽略太短的词
                    if word not in action_keywords:
                        action_keywords[word] = 0
                    action_keywords[word] += 1
        
        # 提取高频关键词
        frequent_keywords = [(word, count) for word, count in action_keywords.items() 
                            if count >= self.pattern_rules["step_patterns"]["min_occurrence"]]
        
        if frequent_keywords:
            patterns.append({
                "pattern_type": "action_keywords",
                "keywords": [word for word, _ in frequent_keywords],
                "description": "高频动作关键词",
                "confidence": min(1.0, len(frequent_keywords) / 5)
            })
        
        return patterns
    
    def _extract_data_patterns(self, test_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取数据模式"""
        patterns = []
        
        if not test_data:
            return patterns
        
        # 分析数据范围
        if "boundary_values" in test_data:
            boundary_data = test_data["boundary_values"]
            
            for data_type, values in boundary_data.items():
                if isinstance(values, dict) and "values" in values:
                    value_list = values["values"]
                    if isinstance(value_list, list) and len(value_list) >= 2:
                        patterns.append({
                            "pattern_type": "boundary_values",
                            "data_type": data_type,
                            "values": value_list,
                            "description": f"{data_type}边界值集合",
                            "confidence": 0.8
                        })
        
        # 分析输入数据
        if "input_data" in test_data:
            input_data = test_data["input_data"]
            
            step_data_patterns = []
            for step_key, step_info in input_data.items():
                if isinstance(step_info, dict):
                    data_keys = list(step_info.keys())
                    if data_keys:
                        step_data_patterns.append({
                            "step": step_key,
                            "data_keys": data_keys
                        })
            
            if len(step_data_patterns) >= self.pattern_rules["data_patterns"]["min_occurrence"]:
                # 查找共同的数据键
                common_keys = set()
                for pattern in step_data_patterns:
                    if not common_keys:
                        common_keys = set(pattern["data_keys"])
                    else:
                        common_keys = common_keys.intersection(set(pattern["data_keys"]))
                
                if common_keys:
                    patterns.append({
                        "pattern_type": "common_data_fields",
                        "fields": list(common_keys),
                        "description": "跨步骤通用数据字段",
                        "confidence": len(common_keys) / 10  # 基于字段数量
                    })
        
        return patterns
    
    def _extract_constraint_patterns(self, constraints: List[Any]) -> List[Dict[str, Any]]:
        """提取约束模式"""
        patterns = []
        
        if not constraints:
            return patterns
        
        constraint_types = {}
        constraint_sources = {}
        constraint_priorities = {}
        
        for constraint in constraints:
            if isinstance(constraint, dict):
                constraint_type = constraint.get("type", "unknown")
                source = constraint.get("source", "unknown")
                priority = constraint.get("priority", "medium")
            else:
                # 假设是Constraint对象
                constraint_type = getattr(constraint, "type", "unknown")
                source = getattr(constraint, "source", "unknown")
                priority = getattr(constraint, "priority", "medium")
            
            # 统计类型
            if constraint_type not in constraint_types:
                constraint_types[constraint_type] = 0
            constraint_types[constraint_type] += 1
            
            # 统计来源
            if source not in constraint_sources:
                constraint_sources[source] = 0
            constraint_sources[source] += 1
            
            # 统计优先级
            if priority not in constraint_priorities:
                constraint_priorities[priority] = 0
            constraint_priorities[priority] += 1
        
        # 提取高频类型
        for const_type, count in constraint_types.items():
            if count >= self.pattern_rules["constraint_patterns"]["min_occurrence"]:
                patterns.append({
                    "pattern_type": "frequent_constraint_type",
                    "type": const_type,
                    "count": count,
                    "description": f"高频约束类型: {const_type}",
                    "confidence": min(1.0, count / 5)
                })
        
        # 提取主要来源
        for source, count in constraint_sources.items():
            if count >= self.pattern_rules["constraint_patterns"]["min_occurrence"]:
                patterns.append({
                    "pattern_type": "main_constraint_source",
                    "source": source,
                    "count": count,
                    "description": f"主要约束来源: {source}",
                    "confidence": min(1.0, count / 5)
                })
        
        return patterns
    
    def _apply_learned_patterns(self, patterns: Dict[str, Any], record: TemplateUsageRecord):
        """应用学习到的模式"""
        try:
            # 这里应该更新模板库
            # 简化实现：记录学习结果
            
            logger.info(f"应用学习模式: {len(patterns.get('step_patterns', []))} 个步骤模式")
            
            # 可以根据学习结果优化模板
            if patterns.get("step_patterns"):
                self._optimize_template_steps(record.template_id, patterns["step_patterns"])
            
            if patterns.get("data_patterns"):
                self._optimize_template_data(record.template_id, patterns["data_patterns"])
            
            return True
            
        except Exception as e:
            logger.error(f"应用学习模式失败: {str(e)}")
            return False
    
    def _optimize_template_steps(self, template_id: str, step_patterns: List[Dict[str, Any]]):
        """优化模板步骤"""
        # 这里应该更新数据库中的模板
        # 简化实现：记录优化建议
        for pattern in step_patterns:
            if pattern["pattern_type"] == "step_sequence":
                logger.info(f"模板 {template_id} 可以优化步骤序列")
            elif pattern["pattern_type"] == "action_keywords":
                logger.info(f"模板 {template_id} 可以使用高频关键词: {pattern['keywords']}")
    
    def _optimize_template_data(self, template_id: str, data_patterns: List[Dict[str, Any]]):
        """优化模板数据"""
        # 这里应该更新数据库中的模板数据
        # 简化实现：记录优化建议
        for pattern in data_patterns:
            if pattern["pattern_type"] == "boundary_values":
                logger.info(f"模板 {template_id} 可以添加边界值: {pattern['data_type']}")
            elif pattern["pattern_type"] == "common_data_fields":
                logger.info(f"模板 {template_id} 可以标准化数据字段: {pattern['fields']}")
    
    def get_template_recommendations(self, 
                                   requirement: str, 
                                   classification: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取模板推荐"""
        recommendations = []
        
        try:
            # 基于历史使用记录推荐
            # 简化实现：返回基础推荐
            
            recommendations.append({
                "template_type": "基础功能测试",
                "reason": "适用于大多数功能验证场景",
                "confidence": 0.7,
                "suggested_adaptations": ["调整激励参数", "添加边界条件"]
            })
            
            # 基于分类结果推荐
            if classification.get("domain") == "HIL测试":
                recommendations.append({
                    "template_type": "HIL故障注入测试",
                    "reason": "HIL测试需要验证安全机制",
                    "confidence": 0.8,
                    "suggested_adaptations": ["添加故障注入点", "验证安全状态"]
                })
            
            if classification.get("subsystem") == "VCU控制器":
                recommendations.append({
                    "template_type": "VCU模式切换测试",
                    "reason": "VCU主要功能是模式管理",
                    "confidence": 0.85,
                    "suggested_adaptations": ["验证模式转换条件", "检查状态同步"]
                })
            
        except Exception as e:
            logger.error(f"获取模板推荐失败: {str(e)}")
        
        return recommendations
    
    def analyze_template_effectiveness(self, 
                                     template_id: str, 
                                     time_period_days: int = 30) -> Dict[str, Any]:
        """分析模板有效性"""
        try:
            # 这里应该查询数据库获取使用统计
            # 简化实现：返回模拟数据
            
            return {
                "template_id": template_id,
                "usage_count": 15,
                "average_quality": 0.78,
                "success_rate": 0.85,
                "common_applications": ["功能测试", "边界测试"],
                "recommended_improvements": ["增加数据验证步骤", "优化步骤顺序"],
                "effectiveness_score": 0.82
            }
            
        except Exception as e:
            logger.error(f"分析模板有效性失败: {str(e)}")
            return {
                "template_id": template_id,
                "error": str(e)
            }

# 使用示例
def main():
    """使用示例"""
    learner = TemplateLearner(template_db=None, case_db=None, history_db=None)
    
    # 模拟使用记录
    record = TemplateUsageRecord(
        template_id="TEMPLATE_001",
        requirement="VCU Ready模式测试",
        classification={
            "domain": "HIL测试",
            "subsystem": "VCU控制器",
            "test_patterns": ["功能测试", "故障注入测试"]
        },
        test_case={
            "test_steps": [
                {"step_number": 1, "step_type": "setup", "action": "设置测试环境"},
                {"step_number": 2, "step_type": "stimulus", "action": "发送CAN信号"},
                {"step_number": 3, "step_type": "verification", "action": "验证响应时间"}
            ],
            "test_data": {
                "boundary_values": {
                    "voltage": {"values": [9, 12, 16]},
                    "temperature": {"values": [-40, 25, 85]}
                }
            },
            "constraints": [
                {"type": "performance", "source": "spec", "priority": "high"},
                {"type": "safety", "source": "ISO 26262", "priority": "high"}
            ]
        },
        quality_score=0.85
    )
    
    # 记录使用并学习
    learner.record_template_usage(record)
    
    # 获取推荐
    recommendations = learner.get_template_recommendations(
        "测试需求",
        {"domain": "HIL测试", "subsystem": "VCU控制器"}
    )
    
    print(f"模板推荐: {len(recommendations)} 条")

if __name__ == "__main__":
    main()
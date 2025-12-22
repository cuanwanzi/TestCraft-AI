# src/core/specification_analyzer.py
import os
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import PyPDF2
from docx import Document
import pandas as pd
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class Constraint:
    """约束条件数据类"""
    id: str
    content: str
    source: str
    type: str  # performance, safety, reliability, environmental, compliance
    priority: str  # high, medium, low
    verification_method: str
    standard_reference: Optional[str] = None

@dataclass
class SpecificationAnalysisResult:
    """规范分析结果数据类"""
    requirement: str
    extracted_constraints: List[Constraint]
    identified_standards: List[str]
    specification_details: Dict[str, Any]
    test_requirements: List[str]
    compliance_checklist: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    quality_score: float = 0.0

class SpecificationAnalyzer:
    """规范输入分析器"""
    
    def __init__(self, deepseek_client, knowledge_base):
        self.client = deepseek_client
        self.knowledge_base = knowledge_base
        
        # 支持的文档格式
        self.supported_formats = {
            '.pdf': self._parse_pdf,
            '.docx': self._parse_docx,
            '.doc': self._parse_doc,
            '.xlsx': self._parse_excel,
            '.xls': self._parse_excel,
            '.txt': self._parse_text,
            '.json': self._parse_json
        }
        
        # 标准模板库
        self.standard_templates = self._load_standard_templates()
        
        # 约束模式识别规则
        self.constraint_patterns = {
            'performance': [
                r'响应时间.*?[<=≥].*?\d+.*?(ms|s)',
                r'吞吐量.*?[>=≤].*?\d+',
                r'效率.*?[>=≤].*?\d+%',
                r'精度.*?[<=≥].*?\d+'
            ],
            'safety': [
                r'安全.*?要求',
                r'防护.*?等级',
                r'故障.*?检测',
                r'保护.*?机制',
                r'ASIL-[ABCD]'
            ],
            'reliability': [
                r'MTBF.*?[>=≤].*?\d+',
                r'寿命.*?[>=≤].*?\d+',
                r'可靠性.*?[>=≤].*?\d+%'
            ],
            'environmental': [
                r'温度.*?[-~].*?\d+.*?[°度]C',
                r'湿度.*?[<=≥].*?\d+%',
                r'振动.*?[<=≥].*?\d+',
                r'防护等级.*?IP\d+'
            ],
            'compliance': [
                r'符合.*?(ISO|GB|企标|标准)',
                r'遵循.*?规范',
                r'满足.*?要求',
                r'应.*?符合'
            ]
        }
    
    def _load_standard_templates(self) -> Dict[str, Dict]:
        """加载标准模板库"""
        standards_path = Path(__file__).parent.parent / "config" / "standards.json"
        
        if standards_path.exists():
            with open(standards_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 默认标准模板
        return {
            "ISO 26262": {
                "name": "道路车辆功能安全",
                "sections": ["安全管理", "概念阶段", "产品开发", "生产运维"],
                "test_requirements": [
                    "故障注入测试",
                    "安全机制验证",
                    "安全状态转换测试",
                    "诊断覆盖率验证"
                ],
                "asil_requirements": {
                    "A": {"fault_injection": "推荐", "verification": "基础"},
                    "B": {"fault_injection": "推荐", "verification": "扩展"},
                    "C": {"fault_injection": "必需", "verification": "详细"},
                    "D": {"fault_injection": "必需", "verification": "全面"}
                }
            },
            "ISO 21434": {
                "name": "道路车辆网络安全",
                "sections": ["组织网络安全管理", "项目相关网络安全管理"],
                "test_requirements": [
                    "威胁分析与风险评估",
                    "安全控制措施验证",
                    "漏洞扫描与渗透测试",
                    "安全事件响应测试"
                ]
            },
            "GB/T 18384": {
                "name": "电动汽车安全要求",
                "sections": ["电气安全", "功能安全", "防护安全"],
                "test_requirements": [
                    "绝缘电阻测试",
                    "电位均衡测试",
                    "触电防护测试",
                    "过流保护测试"
                ]
            }
        }
    
    async def analyze(self,
                     requirement: str,
                     spec_files: Optional[List[str]] = None,
                     selected_standards: Optional[List[str]] = None) -> SpecificationAnalysisResult:
        """执行规范分析"""
        
        logger.info("开始规范分析")
        
        # 1. 分析用户需求
        requirement_analysis = await self._analyze_requirement(requirement)
        
        # 2. 解析规范文档
        spec_details = {}
        if spec_files:
            spec_details = await self._parse_specification_files(spec_files)
        
        # 3. 处理选择的标准
        standard_details = {}
        if selected_standards:
            standard_details = await self._process_selected_standards(selected_standards)
        
        # 4. 提取约束条件
        all_constraints = await self._extract_constraints(
            requirement, requirement_analysis, spec_details, standard_details
        )
        
        # 5. 生成测试要求
        test_requirements = await self._generate_test_requirements(
            requirement_analysis, all_constraints, standard_details
        )
        
        # 6. 生成合规检查清单
        compliance_checklist = await self._generate_compliance_checklist(
            all_constraints, standard_details
        )
        
        # 7. 风险评估
        risk_assessment = await self._assess_risks(all_constraints, test_requirements)
        
        # 8. 质量评分
        quality_score = await self._calculate_quality_score(
            all_constraints, compliance_checklist, risk_assessment
        )
        
        # 构建结果
        result = SpecificationAnalysisResult(
            requirement=requirement,
            extracted_constraints=all_constraints,
            identified_standards=list(set(
                requirement_analysis.get("implicit_standards", []) +
                list(standard_details.keys())
            )),
            specification_details={**spec_details, **standard_details},
            test_requirements=test_requirements,
            compliance_checklist=compliance_checklist,
            risk_assessment=risk_assessment,
            quality_score=quality_score
        )
        
        logger.info(f"规范分析完成，提取约束: {len(all_constraints)}条")
        
        return result
    
    async def _analyze_requirement(self, requirement: str) -> Dict[str, Any]:
        """分析用户需求"""
        
        prompt = f"""
        请分析以下汽车测试需求，提取关键信息：

        需求：{requirement}

        请提取：
        1. 隐含引用的标准（如ISO 26262、GB/T等）
        2. 质量属性要求（可靠性、安全性、性能等）
        3. 技术约束条件
        4. 测试重点领域

        以JSON格式返回：
        {{
            "implicit_standards": ["标准1", "标准2"],
            "quality_attributes": ["属性1", "属性2"],
            "technical_constraints": ["约束1", "约束2"],
            "focus_areas": ["领域1", "领域2"]
        }}
        """
        
        try:
            response = await self.client.chat_completion([
                {"role": "user", "content": prompt}
            ])
            
            result = json.loads(response["choices"][0]["message"]["content"])
            return result
            
        except Exception as e:
            logger.error(f"需求分析失败: {str(e)}")
            return {
                "implicit_standards": [],
                "quality_attributes": [],
                "technical_constraints": [],
                "focus_areas": []
            }
    
    async def _parse_specification_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """解析规范文档"""
        
        spec_details = {}
        
        for file_path in file_paths:
            try:
                file_path_obj = Path(file_path)
                file_ext = file_path_obj.suffix.lower()
                
                if file_ext in self.supported_formats:
                    parser = self.supported_formats[file_ext]
                    content = parser(file_path)
                    
                    # 分析文档内容
                    analysis = await self._analyze_document_content(content)
                    
                    spec_details[file_path_obj.name] = {
                        "format": file_ext,
                        "content_preview": content[:500],  # 预览前500字符
                        "analysis": analysis,
                        "file_size": os.path.getsize(file_path)
                    }
                    
            except Exception as e:
                logger.error(f"解析文件失败 {file_path}: {str(e)}")
                spec_details[Path(file_path).name] = {
                    "format": file_ext,
                    "error": str(e)
                }
        
        return spec_details
    
    def _parse_pdf(self, file_path: str) -> str:
        """解析PDF文档"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- 第 {page_num + 1} 页 ---\n{page_text}"
        return text
    
    def _parse_docx(self, file_path: str) -> str:
        """解析DOCX文档"""
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    
    def _parse_doc(self, file_path: str) -> str:
        """解析DOC文档（备用方法）"""
        try:
            # 尝试使用 docx 解析器
            return self._parse_docx(file_path)
        except:
            # 如果失败，返回简单信息
            return f"无法解析 .doc 文件，请转换为 .docx 格式: {file_path}"
    
    def _parse_excel(self, file_path: str) -> str:
        """解析Excel文档"""
        excel_data = {}
        try:
            xls = pd.ExcelFile(file_path)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                # 转换为JSON格式字符串
                excel_data[sheet_name] = {
                    "columns": df.columns.tolist(),
                    "sample_data": df.head().to_dict('records')
                }
            return json.dumps(excel_data, ensure_ascii=False)
        except Exception as e:
            return f"Excel解析错误: {str(e)}"
    
    def _parse_text(self, file_path: str) -> str:
        """解析文本文件"""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    def _parse_json(self, file_path: str) -> str:
        """解析JSON文件"""
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return json.dumps(data, ensure_ascii=False, indent=2)
    
    async def _analyze_document_content(self, content: str) -> Dict[str, Any]:
        """分析文档内容"""
        
        # 如果内容太长，截取前5000字符进行分析
        if len(content) > 5000:
            content_preview = content[:5000] + "...[内容已截断]"
        else:
            content_preview = content
        
        prompt = f"""
        分析以下规范文档内容，提取关键信息：

        文档内容：
        {content_preview}

        请提取：
        1. 引用的标准和规范
        2. 具体的技术要求
        3. 测试相关的规定
        4. 约束条件
        5. 验收标准

        以JSON格式返回：
        {{
            "referenced_standards": ["标准1", "标准2"],
            "technical_requirements": ["要求1", "要求2"],
            "test_provisions": ["规定1", "规定2"],
            "constraints": ["约束1", "约束2"],
            "acceptance_criteria": ["标准1", "标准2"]
        }}
        """
        
        try:
            response = await self.client.chat_completion([
                {"role": "user", "content": prompt}
            ])
            
            result = json.loads(response["choices"][0]["message"]["content"])
            return result
            
        except Exception as e:
            logger.error(f"文档分析失败: {str(e)}")
            return self._basic_content_analysis(content)
    
    def _basic_content_analysis(self, content: str) -> Dict[str, Any]:
        """基础内容分析（回退方法）"""
        
        analysis = {
            "referenced_standards": [],
            "technical_requirements": [],
            "test_provisions": [],
            "constraints": [],
            "acceptance_criteria": []
        }
        
        # 简单正则匹配
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # 检测标准引用
            std_patterns = [
                r'ISO\s*\d+',
                r'GB/[T]?\s*\d+',
                r'企标.*?\d+',
                r'标准.*?\d+'
            ]
            
            for pattern in std_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    analysis["referenced_standards"].extend(matches)
            
            # 检测要求
            if re.search(r'应[^。]*[。]', line) or re.search(r'必须[^。]*[。]', line):
                analysis["technical_requirements"].append(line[:200])
            
            # 检测约束
            if re.search(r'不得[^。]*[。]', line) or re.search(r'禁止[^。]*[。]', line):
                analysis["constraints"].append(line[:200])
            
            # 检测验收标准
            if '验收' in line or '通过标准' in line:
                analysis["acceptance_criteria"].append(line[:200])
        
        # 去重
        for key in analysis:
            analysis[key] = list(set(analysis[key]))
        
        return analysis
    
    async def _process_selected_standards(self, standards: List[str]) -> Dict[str, Any]:
        """处理选择的标准"""
        
        standard_details = {}
        
        for std in standards:
            if std in self.standard_templates:
                template = self.standard_templates[std]
                
                # 获取标准的测试要求
                test_requirements = template.get("test_requirements", [])
                
                # 获取ASIL等级要求（如果适用）
                asil_requirements = {}
                if "asil_requirements" in template:
                    asil_requirements = template["asil_requirements"]
                
                standard_details[std] = {
                    "name": template.get("name", std),
                    "sections": template.get("sections", []),
                    "test_requirements": test_requirements,
                    "asil_requirements": asil_requirements,
                    "test_implications": self._get_standard_test_implications(std)
                }
        
        return standard_details
    
    def _get_standard_test_implications(self, standard: str) -> List[str]:
        """获取标准的测试要求"""
        implications = {
            "ISO 26262": [
                "必须进行故障注入测试",
                "需要验证安全机制的有效性",
                "需进行ASIL等级对应的测试",
                "需要覆盖率分析报告",
                "必须验证安全状态转换"
            ],
            "ISO 21434": [
                "必须进行威胁分析和风险评估",
                "需要验证安全控制措施",
                "需进行渗透测试",
                "需要安全测试报告",
                "必须验证安全事件响应"
            ],
            "GB/T 18384": [
                "必须进行绝缘电阻测试",
                "需要验证电位均衡",
                "需进行触电防护测试",
                "需要过流保护验证",
                "必须进行防护等级测试"
            ]
        }
        
        return implications.get(standard, [])
    
    async def _extract_constraints(self,
                                  requirement: str,
                                  requirement_analysis: Dict[str, Any],
                                  spec_details: Dict[str, Any],
                                  standard_details: Dict[str, Any]) -> List[Constraint]:
        """提取约束条件"""
        
        constraints = []
        constraint_id = 1
        
        # 1. 从需求分析中提取约束
        for tech_constraint in requirement_analysis.get("technical_constraints", []):
            constraint_type = self._classify_constraint_type(tech_constraint)
            
            constraint = Constraint(
                id=f"C{constraint_id:03d}",
                content=tech_constraint,
                source="用户需求",
                type=constraint_type,
                priority=self._determine_constraint_priority(tech_constraint),
                verification_method=self._determine_verification_method(tech_constraint)
            )
            constraints.append(constraint)
            constraint_id += 1
        
        # 2. 从规范文档中提取约束
        for file_name, file_info in spec_details.items():
            if "analysis" in file_info:
                analysis = file_info["analysis"]
                
                for constraint_text in analysis.get("constraints", []):
                    constraint_type = self._classify_constraint_type(constraint_text)
                    
                    constraint = Constraint(
                        id=f"C{constraint_id:03d}",
                        content=constraint_text,
                        source=f"规范文档: {file_name}",
                        type=constraint_type,
                        priority="high",  # 规范文档中的约束通常优先级高
                        verification_method=self._determine_verification_method(constraint_text),
                        standard_reference=self._find_standard_reference(constraint_text)
                    )
                    constraints.append(constraint)
                    constraint_id += 1
        
        # 3. 从标准中提取约束
        for std, std_info in standard_details.items():
            for implication in std_info.get("test_implications", []):
                constraint = Constraint(
                    id=f"C{constraint_id:03d}",
                    content=implication,
                    source=f"标准: {std}",
                    type="compliance",
                    priority="high",
                    verification_method="测试验证",
                    standard_reference=std
                )
                constraints.append(constraint)
                constraint_id += 1
        
        # 4. 使用AI进行深度约束提取
        ai_constraints = await self._extract_constraints_with_ai(
            requirement, constraints, spec_details
        )
        constraints.extend(ai_constraints)
        
        return constraints
    
    def _classify_constraint_type(self, constraint_text: str) -> str:
        """分类约束类型"""
        constraint_text_lower = constraint_text.lower()
        
        for constraint_type, patterns in self.constraint_patterns.items():
            for pattern in patterns:
                if re.search(pattern, constraint_text_lower):
                    return constraint_type
        
        return "other"
    
    def _determine_constraint_priority(self, constraint_text: str) -> str:
        """确定约束优先级"""
        high_priority_keywords = ['必须', '强制', '禁止', '不得', '务必']
        medium_priority_keywords = ['应', '宜', '需要', '建议']
        
        constraint_text_lower = constraint_text.lower()
        
        for keyword in high_priority_keywords:
            if keyword in constraint_text_lower:
                return "high"
        
        for keyword in medium_priority_keywords:
            if keyword in constraint_text_lower:
                return "medium"
        
        return "low"
    
    def _determine_verification_method(self, constraint_text: str) -> str:
        """确定验证方法"""
        constraint_text_lower = constraint_text.lower()
        
        if any(word in constraint_text_lower for word in ['测试', '试验', '验证']):
            return "测试验证"
        elif any(word in constraint_text_lower for word in ['检查', '审核', '评审']):
            return "文档评审"
        elif any(word in constraint_text_lower for word in ['分析', '评估', '计算']):
            return "分析验证"
        else:
            return "通用验证"
    
    def _find_standard_reference(self, constraint_text: str) -> Optional[str]:
        """查找标准引用"""
        for std in self.standard_templates.keys():
            if std.lower() in constraint_text.lower():
                return std
        return None
    
    async def _extract_constraints_with_ai(self,
                                          requirement: str,
                                          existing_constraints: List[Constraint],
                                          spec_details: Dict[str, Any]) -> List[Constraint]:
        """使用AI进行深度约束提取"""
        
        # 构建已有的约束文本
        existing_constraint_texts = [c.content for c in existing_constraints]
        
        prompt = f"""
        基于以下信息，请提取可能遗漏的约束条件：

        1. 测试需求：{requirement}
        
        2. 已提取的约束：
        {chr(10).join(f'- {c}' for c in existing_constraint_texts[:10])}
        
        3. 规范文档摘要：
        {json.dumps(spec_details, ensure_ascii=False, indent=2)[:2000]}

        请从以下角度补充可能的约束：
        1. 性能约束（响应时间、吞吐量、效率等）
        2. 安全约束（防护等级、故障处理、安全机制等）
        3. 可靠性约束（MTBF、寿命、失效模式等）
        4. 环境约束（温度、湿度、振动、防护等级等）
        5. 合规约束（标准符合性、法规要求等）

        以JSON数组格式返回，每个元素包含：
        {{
            "content": "约束内容",
            "type": "约束类型",
            "priority": "优先级",
            "reason": "提取理由"
        }}
        """
        
        try:
            response = await self.client.chat_completion([
                {"role": "user", "content": prompt}
            ])
            
            result = json.loads(response["choices"][0]["message"]["content"])
            
            ai_constraints = []
            constraint_id = len(existing_constraints) + 1
            
            for item in result:
                constraint = Constraint(
                    id=f"C{constraint_id:03d}",
                    content=item["content"],
                    source="AI分析",
                    type=item["type"],
                    priority=item.get("priority", "medium"),
                    verification_method=self._determine_verification_method(item["content"])
                )
                ai_constraints.append(constraint)
                constraint_id += 1
            
            return ai_constraints
            
        except Exception as e:
            logger.error(f"AI约束提取失败: {str(e)}")
            return []
    
    async def _generate_test_requirements(self,
                                         requirement_analysis: Dict[str, Any],
                                         constraints: List[Constraint],
                                         standard_details: Dict[str, Any]) -> List[str]:
        """生成测试要求"""
        
        test_requirements = []
        
        # 1. 从质量属性生成测试要求
        for quality_attribute in requirement_analysis.get("quality_attributes", []):
            if quality_attribute == "可靠性":
                test_requirements.extend([
                    "进行MTBF验证测试",
                    "执行失效模式分析",
                    "验证寿命指标"
                ])
            elif quality_attribute == "安全性":
                test_requirements.extend([
                    "进行故障注入测试",
                    "验证安全状态转换",
                    "检查安全机制有效性"
                ])
            elif quality_attribute == "性能":
                test_requirements.extend([
                    "验证响应时间",
                    "测试吞吐量指标",
                    "检查效率参数"
                ])
        
        # 2. 从约束生成测试要求
        for constraint in constraints:
            if constraint.type == "performance":
                test_requirements.append(f"验证{constraint.content}")
            elif constraint.type == "safety":
                test_requirements.append(f"安全测试：{constraint.content}")
            elif constraint.type == "reliability":
                test_requirements.append(f"可靠性测试：{constraint.content}")
        
        # 3. 从标准生成测试要求
        for std, std_info in standard_details.items():
            test_requirements.extend(std_info.get("test_requirements", []))
        
        # 去重
        test_requirements = list(set(test_requirements))
        
        return test_requirements
    
    async def _generate_compliance_checklist(self,
                                            constraints: List[Constraint],
                                            standard_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成合规检查清单"""
        
        checklist = []
        item_id = 1
        
        # 1. 从约束生成检查项
        for constraint in constraints:
            if constraint.type == "compliance" or constraint.standard_reference:
                checklist.append({
                    "id": f"CL{item_id:03d}",
                    "description": constraint.content,
                    "source": constraint.source,
                    "standard": constraint.standard_reference or "通用要求",
                    "verification_method": constraint.verification_method,
                    "priority": constraint.priority,
                    "status": "待验证"
                })
                item_id += 1
        
        # 2. 从标准生成检查项
        for std, std_info in standard_details.items():
            for requirement in std_info.get("test_requirements", []):
                checklist.append({
                    "id": f"CL{item_id:03d}",
                    "description": requirement,
                    "source": f"标准: {std}",
                    "standard": std,
                    "verification_method": "测试验证",
                    "priority": "high",
                    "status": "待验证"
                })
                item_id += 1
        
        return checklist
    
    async def _assess_risks(self,
                           constraints: List[Constraint],
                           test_requirements: List[str]) -> Dict[str, Any]:
        """风险评估"""
        
        prompt = f"""
        基于以下信息进行风险评估：

        约束条件：
        {chr(10).join(f'- {c.content} (类型: {c.type}, 优先级: {c.priority})' for c in constraints[:15])}

        测试要求：
        {chr(10).join(f'- {req}' for req in test_requirements[:10])}

        请评估：
        1. 高风险领域（哪些约束可能难以满足）
        2. 测试复杂性（哪些测试要求执行困难）
        3. 合规风险（哪些标准要求可能不符合）
        4. 建议的缓解措施

        以JSON格式返回：
        {{
            "high_risk_areas": ["领域1", "领域2"],
            "test_complexity": {"复杂测试": "原因", "中等测试": "原因"},
            "compliance_risks": ["风险1", "风险2"],
            "mitigation_measures": ["措施1", "措施2"],
            "overall_risk_level": "high/medium/low"
        }}
        """
        
        try:
            response = await self.client.chat_completion([
                {"role": "user", "content": prompt}
            ])
            
            return json.loads(response["choices"][0]["message"]["content"])
            
        except Exception as e:
            logger.error(f"风险评估失败: {str(e)}")
            return {
                "high_risk_areas": [],
                "test_complexity": {},
                "compliance_risks": [],
                "mitigation_measures": [],
                "overall_risk_level": "medium"
            }
    
    async def _calculate_quality_score(self,
                                      constraints: List[Constraint],
                                      compliance_checklist: List[Dict[str, Any]],
                                      risk_assessment: Dict[str, Any]) -> float:
        """计算质量评分"""
        
        scores = []
        
        # 1. 约束覆盖评分（基于约束数量和优先级）
        if constraints:
            high_priority_count = sum(1 for c in constraints if c.priority == "high")
            constraint_score = min(100, len(constraints) * 5 + high_priority_count * 10)
            scores.append(constraint_score)
        
        # 2. 合规检查清单评分
        if compliance_checklist:
            compliance_score = min(100, len(compliance_checklist) * 3)
            scores.append(compliance_score)
        
        # 3. 风险评估评分
        risk_level = risk_assessment.get("overall_risk_level", "medium")
        risk_scores = {"high": 60, "medium": 80, "low": 95}
        scores.append(risk_scores.get(risk_level, 80))
        
        # 计算平均分
        if scores:
            return sum(scores) / len(scores)
        else:
            return 70.0  # 默认分数

# 使用示例
async def main():
    from deepseek_client import DeepSeekClient, DeepSeekConfig
    from knowledge_base import KnowledgeBase
    
    # 初始化客户端和知识库
    config = DeepSeekConfig(api_key="your-api-key")
    client = DeepSeekClient(config)
    knowledge_base = KnowledgeBase()
    
    # 创建分析器
    analyzer = SpecificationAnalyzer(client, knowledge_base)
    
    # 执行分析
    requirement = "为VCU控制器设计HIL测试用例，验证Ready模式切换功能，符合ISO 26262 ASIL C要求"
    
    result = await analyzer.analyze(
        requirement=requirement,
        spec_files=["specs/test_requirements.pdf"],
        selected_standards=["ISO 26262", "GB/T 18384"]
    )
    
    print(f"分析完成，提取约束: {len(result.extracted_constraints)}条")
    print(f"识别标准: {result.identified_standards}")
    print(f"质量评分: {result.quality_score}")
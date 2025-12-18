# src/core/knowledge_base.py
import os
import json
import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import logging
import pickle
from dataclasses import dataclass, asdict
from enum import Enum

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from sqlalchemy import create_engine, Column, String, Integer, Float, JSON, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()

class KnowledgeType(Enum):
    """知识类型"""
    STANDARD = "standard"
    BEST_PRACTICE = "best_practice"
    TEST_PATTERN = "test_pattern"
    CASE_TEMPLATE = "case_template"
    EQUIPMENT = "equipment"
    CONTROLLER = "controller"

@dataclass
class KnowledgeItem:
    """知识项"""
    id: str
    content: str
    type: KnowledgeType
    domain: str
    tags: List[str]
    source: str
    confidence: float
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class KnowledgeRecord(Base):
    """知识记录数据库模型"""
    __tablename__ = 'knowledge_records'
    
    id = Column(String, primary_key=True)
    content = Column(Text, nullable=False)
    type = Column(String, nullable=False)  # KnowledgeType value
    domain = Column(String, nullable=False)
    tags = Column(JSON, default=[])  # List of strings
    source = Column(String, nullable=False)
    confidence = Column(Float, default=1.0)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

class KnowledgeBase:
    """知识库管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 初始化向量数据库
        self.vector_db = self._init_vector_db()
        
        # 初始化关系数据库
        self.relational_db = self._init_relational_db()
        
        # 初始化嵌入模型
        self.embedder = self._init_embedder()
        
        # 加载初始知识
        self._load_initial_knowledge()
        
        logger.info("知识库初始化完成")
    
    def _init_vector_db(self) -> chromadb.Client:
        """初始化向量数据库"""
        persist_path = Path(self.config.get("vector_db_path", "./data/knowledge_base"))
        persist_path.mkdir(parents=True, exist_ok=True)
        
        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(persist_path),
            anonymized_telemetry=False
        )
        
        client = chromadb.Client(settings)
        
        # 创建或获取集合
        collections = {
            "standards": "标准规范知识",
            "best_practices": "最佳实践知识",
            "test_patterns": "测试模式知识",
            "case_templates": "用例模板知识",
            "controllers": "控制器知识"
        }
        
        for collection_name, description in collections.items():
            try:
                client.create_collection(
                    name=collection_name,
                    metadata={"description": description}
                )
                logger.info(f"创建集合: {collection_name}")
            except Exception as e:
                # 集合已存在
                pass
        
        return client
    
    def _init_relational_db(self) -> Any:
        """初始化关系数据库"""
        db_path = self.config.get("relational_db_path", "./data/knowledge_base/knowledge.db")
        db_url = f"sqlite:///{db_path}"
        
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        return session
    
    def _init_embedder(self) -> SentenceTransformer:
        """初始化嵌入模型"""
        model_name = self.config.get("embedding_model", "BAAI/bge-small-zh-v1.5")
        
        try:
            embedder = SentenceTransformer(model_name)
            logger.info(f"加载嵌入模型: {model_name}")
            return embedder
        except Exception as e:
            logger.warning(f"无法加载模型 {model_name}: {str(e)}，使用备用模型")
            return SentenceTransformer('all-MiniLM-L6-v2')
    
    def _load_initial_knowledge(self):
        """加载初始知识"""
        initial_data_path = Path(__file__).parent.parent / "config" / "initial_knowledge.json"
        
        if initial_data_path.exists():
            with open(initial_data_path, 'r', encoding='utf-8') as f:
                initial_knowledge = json.load(f)
                
            for item in initial_knowledge:
                self.add_knowledge_item(
                    content=item["content"],
                    type=KnowledgeType(item["type"]),
                    domain=item["domain"],
                    tags=item.get("tags", []),
                    source=item["source"],
                    metadata=item.get("metadata", {})
                )
            
            logger.info(f"加载初始知识: {len(initial_knowledge)} 项")
    
    def add_knowledge_item(self,
                          content: str,
                          type: KnowledgeType,
                          domain: str,
                          tags: List[str],
                          source: str,
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """添加知识项"""
        
        # 生成唯一ID
        item_id = f"{type.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(content) % 10000:04d}"
        
        # 创建知识项
        knowledge_item = KnowledgeItem(
            id=item_id,
            content=content,
            type=type,
            domain=domain,
            tags=tags,
            source=source,
            confidence=1.0,
            metadata=metadata or {},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 保存到关系数据库
        record = KnowledgeRecord(
            id=item_id,
            content=content,
            type=type.value,
            domain=domain,
            tags=tags,
            source=source,
            metadata=metadata or {},
            confidence=1.0
        )
        
        self.relational_db.add(record)
        self.relational_db.commit()
        
        # 保存到向量数据库
        collection_name = self._get_collection_name(type)
        collection = self.vector_db.get_collection(collection_name)
        
        embedding = self.embedder.encode(content).tolist()
        
        collection.add(
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "id": item_id,
                "type": type.value,
                "domain": domain,
                "tags": json.dumps(tags, ensure_ascii=False),
                "source": source
            }],
            ids=[item_id]
        )
        
        logger.info(f"添加知识项: {item_id} ({type.value})")
        
        return item_id
    
    def _get_collection_name(self, knowledge_type: KnowledgeType) -> str:
        """获取集合名称"""
        mapping = {
            KnowledgeType.STANDARD: "standards",
            KnowledgeType.BEST_PRACTICE: "best_practices",
            KnowledgeType.TEST_PATTERN: "test_patterns",
            KnowledgeType.CASE_TEMPLATE: "case_templates",
            KnowledgeType.CONTROLLER: "controllers",
            KnowledgeType.EQUIPMENT: "equipment"
        }
        
        return mapping.get(knowledge_type, "general")
    
    def search_knowledge(self,
                        query: str,
                        knowledge_types: Optional[List[KnowledgeType]] = None,
                        domains: Optional[List[str]] = None,
                        tags: Optional[List[str]] = None,
                        top_k: int = 5) -> List[KnowledgeItem]:
        """搜索知识"""
        
        results = []
        
        # 确定要搜索的集合
        if knowledge_types:
            collection_names = [self._get_collection_name(t) for t in knowledge_types]
        else:
            collection_names = list(self.vector_db.list_collections())
        
        # 生成查询嵌入
        query_embedding = self.embedder.encode(query).tolist()
        
        for collection_name in collection_names:
            try:
                collection = self.vector_db.get_collection(collection_name)
                
                # 构建过滤器
                where_filter = {}
                if domains:
                    where_filter["domain"] = {"$in": domains}
                if tags:
                    where_filter["tags"] = {"$contains": tags}
                
                # 执行查询
                query_results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where=where_filter if where_filter else None,
                    include=["documents", "metadatas", "distances"]
                )
                
                # 处理结果
                if query_results["documents"]:
                    for i in range(len(query_results["documents"][0])):
                        metadata = query_results["metadatas"][0][i]
                        
                        knowledge_item = KnowledgeItem(
                            id=metadata.get("id", f"unknown_{i}"),
                            content=query_results["documents"][0][i],
                            type=KnowledgeType(metadata.get("type", "general")),
                            domain=metadata.get("domain", ""),
                            tags=json.loads(metadata.get("tags", "[]")),
                            source=metadata.get("source", ""),
                            confidence=1.0 - query_results["distances"][0][i],
                            metadata={},
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        
                        results.append(knowledge_item)
                        
            except Exception as e:
                logger.error(f"搜索集合 {collection_name} 失败: {str(e)}")
                continue
        
        # 按置信度排序
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        # 限制返回数量
        return results[:top_k]
    
    def get_controller_knowledge(self, controller_name: str) -> Dict[str, Any]:
        """获取控制器知识"""
        
        # 从关系数据库查询
        records = self.relational_db.query(KnowledgeRecord).filter(
            KnowledgeRecord.type == KnowledgeType.CONTROLLER.value,
            KnowledgeRecord.domain.contains(controller_name)
        ).all()
        
        controller_knowledge = {
            "functions": [],
            "interfaces": [],
            "test_points": [],
            "common_issues": [],
            "best_practices": []
        }
        
        for record in records:
            metadata = record.metadata or {}
            
            if "function" in metadata.get("category", ""):
                controller_knowledge["functions"].append({
                    "name": metadata.get("name", ""),
                    "description": record.content,
                    "parameters": metadata.get("parameters", [])
                })
            elif "interface" in metadata.get("category", ""):
                controller_knowledge["interfaces"].append({
                    "type": metadata.get("interface_type", ""),
                    "protocol": metadata.get("protocol", ""),
                    "description": record.content
                })
            elif "test" in metadata.get("category", ""):
                controller_knowledge["test_points"].append({
                    "test_type": metadata.get("test_type", ""),
                    "description": record.content,
                    "expected_result": metadata.get("expected_result", "")
                })
        
        return controller_knowledge
    
    def get_test_patterns(self, test_type: str, domain: str) -> List[Dict[str, Any]]:
        """获取测试模式"""
        
        patterns = []
        
        # 从向量数据库搜索
        query = f"{test_type}测试模式 {domain}"
        knowledge_items = self.search_knowledge(
            query=query,
            knowledge_types=[KnowledgeType.TEST_PATTERN],
            domains=[domain],
            top_k=10
        )
        
        for item in knowledge_items:
            pattern = {
                "name": item.metadata.get("name", f"模式_{item.id}"),
                "description": item.content,
                "steps": item.metadata.get("steps", []),
                "applicable_scenarios": item.metadata.get("applicable_scenarios", []),
                "success_rate": item.metadata.get("success_rate", 0.0),
                "usage_count": item.metadata.get("usage_count", 0)
            }
            patterns.append(pattern)
        
        return patterns
    
    def record_usage(self, knowledge_id: str, success: bool):
        """记录知识使用情况"""
        
        try:
            # 更新关系数据库
            record = self.relational_db.query(KnowledgeRecord).filter_by(id=knowledge_id).first()
            
            if record:
                record.usage_count += 1
                
                if success:
                    current_success_rate = record.success_rate or 0.0
                    usage_count = record.usage_count or 1
                    new_success_rate = ((current_success_rate * (usage_count - 1)) + 1) / usage_count
                    record.success_rate = new_success_rate
                else:
                    current_success_rate = record.success_rate or 0.0
                    usage_count = record.usage_count or 1
                    new_success_rate = (current_success_rate * (usage_count - 1)) / usage_count
                    record.success_rate = new_success_rate
                
                record.updated_at = datetime.now()
                self.relational_db.commit()
                
                logger.info(f"记录知识使用: {knowledge_id}, 成功: {success}")
        
        except Exception as e:
            logger.error(f"记录知识使用失败: {str(e)}")
    
    def export_knowledge(self, export_path: str):
        """导出知识库"""
        
        export_data = {
            "metadata": {
                "export_time": datetime.now().isoformat(),
                "total_items": 0,
                "knowledge_types": {}
            },
            "knowledge_items": []
        }
        
        # 从关系数据库导出所有记录
        records = self.relational_db.query(KnowledgeRecord).all()
        
        for record in records:
            knowledge_item = {
                "id": record.id,
                "content": record.content,
                "type": record.type,
                "domain": record.domain,
                "tags": record.tags,
                "source": record.source,
                "confidence": record.confidence,
                "metadata": record.metadata,
                "usage_count": record.usage_count,
                "success_rate": record.success_rate,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None
            }
            
            export_data["knowledge_items"].append(knowledge_item)
            
            # 更新统计信息
            export_data["metadata"]["total_items"] += 1
            knowledge_type = record.type
            if knowledge_type not in export_data["metadata"]["knowledge_types"]:
                export_data["metadata"]["knowledge_types"][knowledge_type] = 0
            export_data["metadata"]["knowledge_types"][knowledge_type] += 1
        
        # 保存到文件
        export_path_obj = Path(export_path)
        export_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(export_path_obj, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"知识库导出完成: {export_path}")
        
        return export_data["metadata"]["total_items"]
    
    def import_knowledge(self, import_path: str):
        """导入知识库"""
        
        import_path_obj = Path(import_path)
        
        if not import_path_obj.exists():
            logger.error(f"导入文件不存在: {import_path}")
            return 0
        
        with open(import_path_obj, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        imported_count = 0
        
        for item_data in import_data.get("knowledge_items", []):
            try:
                # 检查是否已存在
                existing = self.relational_db.query(KnowledgeRecord).filter_by(id=item_data["id"]).first()
                
                if existing:
                    # 更新现有记录
                    existing.content = item_data["content"]
                    existing.tags = item_data.get("tags", [])
                    existing.metadata = item_data.get("metadata", {})
                    existing.updated_at = datetime.now()
                else:
                    # 创建新记录
                    knowledge_type = item_data.get("type", "general")
                    
                    record = KnowledgeRecord(
                        id=item_data["id"],
                        content=item_data["content"],
                        type=knowledge_type,
                        domain=item_data.get("domain", "general"),
                        tags=item_data.get("tags", []),
                        source=item_data.get("source", "import"),
                        metadata=item_data.get("metadata", {}),
                        confidence=item_data.get("confidence", 1.0),
                        usage_count=item_data.get("usage_count", 0),
                        success_rate=item_data.get("success_rate", 0.0)
                    )
                    
                    self.relational_db.add(record)
                    
                    # 添加到向量数据库
                    collection_name = self._get_collection_name(KnowledgeType(knowledge_type))
                    collection = self.vector_db.get_collection(collection_name)
                    
                    embedding = self.embedder.encode(item_data["content"]).tolist()
                    
                    collection.add(
                        embeddings=[embedding],
                        documents=[item_data["content"]],
                        metadatas=[{
                            "id": item_data["id"],
                            "type": knowledge_type,
                            "domain": item_data.get("domain", "general"),
                            "tags": json.dumps(item_data.get("tags", []), ensure_ascii=False),
                            "source": item_data.get("source", "import")
                        }],
                        ids=[item_data["id"]]
                    )
                
                imported_count += 1
                
            except Exception as e:
                logger.error(f"导入知识项失败 {item_data.get('id')}: {str(e)}")
                continue
        
        self.relational_db.commit()
        
        logger.info(f"知识库导入完成: {imported_count} 项")
        
        return imported_count

# 初始知识数据示例
INITIAL_KNOWLEDGE = [
    {
        "content": "HIL测试硬件在环测试是通过实时仿真器模拟车辆环境，验证控制器软件的正确性。",
        "type": "best_practice",
        "domain": "HIL测试",
        "tags": ["基础概念", "测试方法"],
        "source": "行业最佳实践",
        "metadata": {
            "category": "concept",
            "complexity": "low"
        }
    },
    {
        "content": "VCU整车控制器主要负责整车模式管理、扭矩分配、能量回收控制、热管理控制等功能。",
        "type": "controller",
        "domain": "VCU",
        "tags": ["功能说明", "控制器"],
        "source": "技术文档",
        "metadata": {
            "category": "function",
            "name": "VCU基本功能"
        }
    },
    {
        "content": "故障注入测试步骤：1.设置正常工况 2.注入故障信号 3.监控系统响应 4.验证安全机制 5.恢复系统状态",
        "type": "test_pattern",
        "domain": "安全测试",
        "tags": ["测试模式", "故障注入"],
        "source": "测试经验",
        "metadata": {
            "name": "故障注入测试模式",
            "steps": ["设置", "注入", "监控", "验证", "恢复"],
            "success_rate": 0.95
        }
    }
]

# 使用示例
def create_initial_knowledge():
    """创建初始知识库文件"""
    
    config = {
        "vector_db_path": "./data/knowledge_base",
        "relational_db_path": "./data/knowledge_base/knowledge.db",
        "embedding_model": "BAAI/bge-small-zh-v1.5"
    }
    
    # 创建知识库
    knowledge_base = KnowledgeBase(config)
    
    # 添加初始知识
    for item in INITIAL_KNOWLEDGE:
        knowledge_base.add_knowledge_item(
            content=item["content"],
            type=KnowledgeType(item["type"]),
            domain=item["domain"],
            tags=item["tags"],
            source=item["source"],
            metadata=item.get("metadata", {})
        )
    
    print("初始知识库创建完成")
    
    # 测试搜索
    results = knowledge_base.search_knowledge(
        query="HIL测试方法",
        knowledge_types=[KnowledgeType.BEST_PRACTICE],
        top_k=3
    )
    
    print(f"搜索到 {len(results)} 条结果")
    for result in results:
        print(f"- {result.content[:50]}... (置信度: {result.confidence:.2f})")
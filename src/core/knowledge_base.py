# src/core/knowledge_base.py
import os
import json
import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import logging
from dataclasses import dataclass
from enum import Enum

# ChromaDB 新版本导入
import chromadb
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
    meta_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class KnowledgeRecord(Base):
    """知识记录数据库模型"""
    __tablename__ = 'knowledge_records'
    
    id = Column(String, primary_key=True)
    content = Column(Text, nullable=False)
    type = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    tags = Column(JSON, default=[])
    source = Column(String, nullable=False)
    confidence = Column(Float, default=1.0)
    meta_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

class KnowledgeBase:
    """知识库管理器（兼容新版 ChromaDB）"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 初始化向量数据库
        self.vector_db = self._init_vector_db()
        
        # 初始化关系数据库
        self.relational_db = self._init_relational_db()
        
        # 初始化嵌入模型
        self.embedder = self._init_embedder()
        
        logger.info("知识库初始化完成")
    
    def _init_vector_db(self):
        """初始化向量数据库 - 新版 ChromaDB API"""
        persist_path = Path(self.config.get("vector_db_path", "./data/knowledge_base"))
        persist_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"初始化 ChromaDB，路径: {persist_path}")
        
        try:
            # 新版 ChromaDB 使用 PersistentClient
            client = chromadb.PersistentClient(path=str(persist_path))
            logger.info("ChromaDB 客户端创建成功")
            return client
        except Exception as e:
            logger.error(f"创建 ChromaDB 客户端失败: {str(e)}")
            # 回退到内存模式
            logger.warning("使用内存模式 ChromaDB")
            return chromadb.Client()
    
    def _init_relational_db(self):
        """初始化关系数据库"""
        db_path = self.config.get("relational_db_path", "./data/knowledge_base/knowledge.db")
        db_url = f"sqlite:///{db_path}"
        
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        return session
    
    def _init_embedder(self):
        """初始化嵌入模型"""
        model_name = self.config.get("embedding_model", "all-MiniLM-L6-v2")
        
        try:
            # 尝试加载模型
            cache_dir = Path("./data/models")
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            embedder = SentenceTransformer(model_name, cache_folder=str(cache_dir))
            logger.info(f"加载嵌入模型: {model_name}")
            return embedder
        except Exception as e:
            logger.warning(f"无法加载模型 {model_name}: {str(e)}")
            # 返回简单的嵌入器
            return SimpleEmbedder()
    
    def add_knowledge_item(self,
                          content: str,
                          type: KnowledgeType,
                          domain: str,
                          tags: List[str],
                          source: str,
                          meta_data: Optional[Dict[str, Any]] = None) -> str:
        """添加知识项"""
        
        # 生成唯一ID
        item_id = f"{type.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(content) % 10000:04d}"
        
        # 保存到关系数据库
        record = KnowledgeRecord(
            id=item_id,
            content=content,
            type=type.value,
            domain=domain,
            tags=tags,
            source=source,
            meta_data=meta_data or {},
            confidence=1.0
        )
        
        try:
            self.relational_db.add(record)
            self.relational_db.commit()
        except Exception as e:
            logger.error(f"保存到关系数据库失败: {str(e)}")
            self.relational_db.rollback()
            raise
        
        # 保存到向量数据库
        collection_name = self._get_collection_name(type)
        try:
            # 获取或创建集合
            try:
                collection = self.vector_db.get_collection(name=collection_name)
            except:
                # 集合不存在，创建它
                collection = self.vector_db.create_collection(
                    name=collection_name,
                    metadata={"description": f"{type.value} 知识"}
                )
            
            # 生成嵌入向量
            embedding = self.embedder.encode(content).tolist()
            
            # 准备元数据
            vector_metadata = {
                "type": type.value,
                "domain": domain,
                "tags": json.dumps(tags, ensure_ascii=False),
                "source": source,
                "created_at": datetime.now().isoformat()
            }
            
            # 添加额外的元数据
            if meta_data:
                for key, value in meta_data.items():
                    if isinstance(value, (str, int, float, bool)):
                        vector_metadata[key] = value
            
            # 添加到集合
            collection.add(
                documents=[content],
                metadatas=[vector_metadata],
                ids=[item_id],
                embeddings=[embedding]
            )
            
        except Exception as e:
            logger.error(f"保存到向量数据库失败: {str(e)}")
            # 回滚关系数据库
            try:
                self.relational_db.delete(record)
                self.relational_db.commit()
            except:
                pass
            raise
        
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
        
        # 生成查询嵌入
        try:
            query_embedding = self.embedder.encode(query).tolist()
        except Exception as e:
            logger.error(f"生成查询嵌入失败: {str(e)}")
            return self._simple_text_search(query, top_k)
        
        results = []
        
        # 确定要搜索的集合
        if knowledge_types:
            collection_names = [self._get_collection_name(t) for t in knowledge_types]
        else:
            # 搜索所有集合
            collection_names = []
            try:
                collections = self.vector_db.list_collections()
                for collection in collections:
                    collection_names.append(collection.name)
            except:
                # 如果无法获取集合列表，使用默认集合
                collection_names = ["standards", "best_practices", "test_patterns"]
        
        for collection_name in collection_names:
            try:
                collection = self.vector_db.get_collection(name=collection_name)
                
                # 构建查询过滤器
                where_filter = None
                if domains:
                    where_filter = {"domain": {"$in": domains}}
                
                # 执行查询
                query_results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where=where_filter
                )
                
                # 处理结果
                if query_results.get('documents') and query_results['documents'][0]:
                    for i in range(len(query_results['documents'][0])):
                        metadata = query_results['metadatas'][0][i] if query_results.get('metadatas') else {}
                        document = query_results['documents'][0][i]
                        distance = query_results['distances'][0][i] if query_results.get('distances') else 0
                        
                        # 解析 tags
                        tags_list = []
                        if metadata.get('tags'):
                            try:
                                tags_list = json.loads(metadata['tags'])
                            except:
                                tags_list = [metadata['tags']]
                        
                        knowledge_item = KnowledgeItem(
                            id=query_results['ids'][0][i] if query_results.get('ids') else f"unknown_{i}",
                            content=document,
                            type=KnowledgeType(metadata.get("type", "general")),
                            domain=metadata.get("domain", ""),
                            tags=tags_list,
                            source=metadata.get("source", ""),
                            confidence=1.0 - distance,
                            meta_data=metadata,
                            created_at=datetime.fromisoformat(metadata.get("created_at")) if metadata.get("created_at") else datetime.now(),
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
    
    def _simple_text_search(self, query: str, top_k: int = 5) -> List[KnowledgeItem]:
        """简单文本搜索（备用）"""
        results = []
        
        try:
            query_lower = query.lower()
            records = self.relational_db.query(KnowledgeRecord).all()
            
            for record in records:
                content_lower = record.content.lower()
                if query_lower in content_lower:
                    # 简单评分：关键词出现次数
                    score = content_lower.count(query_lower) / max(1, len(query_lower.split()))
                    
                    knowledge_item = KnowledgeItem(
                        id=record.id,
                        content=record.content,
                        type=KnowledgeType(record.type),
                        domain=record.domain,
                        tags=record.tags if record.tags else [],
                        source=record.source,
                        confidence=min(score, 1.0),
                        meta_data=record.meta_data if record.meta_data else {},
                        created_at=record.created_at or datetime.now(),
                        updated_at=record.updated_at or datetime.now()
                    )
                    
                    results.append(knowledge_item)
            
            results.sort(key=lambda x: x.confidence, reverse=True)
            
        except Exception as e:
            logger.error(f"简单文本搜索失败: {str(e)}")
        
        return results[:top_k]
    
    def get_all_collections(self):
        """获取所有集合"""
        try:
            return self.vector_db.list_collections()
        except:
            return []

class SimpleEmbedder:
    """简单的嵌入器，用于备用"""
    def __init__(self, dimension=384):
        self.dimension = dimension
    
    def encode(self, text: str):
        """生成简单的嵌入向量"""
        import hashlib
        import random
        
        # 使用哈希生成确定性随机向量
        hash_obj = hashlib.md5(text.encode())
        seed = int(hash_obj.hexdigest()[:8], 16)
        random.seed(seed)
        
        # 生成随机向量
        vector = [random.uniform(-1, 1) for _ in range(self.dimension)]
        
        # 归一化
        norm = sum(v*v for v in vector) ** 0.5
        if norm > 0:
            vector = [v/norm for v in vector]
        
        return vector

# 使用示例
def create_initial_knowledge():
    """创建初始知识库"""
    config = {
        "vector_db_path": "./data/knowledge_base",
        "relational_db_path": "./data/knowledge_base/knowledge.db",
        "embedding_model": "all-MiniLM-L6-v2"
    }
    
    try:
        # 确保数据目录存在
        os.makedirs("./data/knowledge_base", exist_ok=True)
        
        print("正在初始化知识库...")
        
        # 创建知识库
        knowledge_base = KnowledgeBase(config)
        
        # 添加初始知识
        initial_data = [
            {
                "content": "HIL测试（硬件在环测试）是通过实时仿真器模拟车辆环境，验证控制器软件的正确性。",
                "type": KnowledgeType.BEST_PRACTICE,
                "domain": "HIL测试",
                "tags": ["基础概念", "测试方法", "硬件在环"],
                "source": "行业最佳实践",
                "meta_data": {"category": "concept", "complexity": "low"}
            },
            {
                "content": "VCU（整车控制器）主要负责整车模式管理、扭矩分配、能量回收控制、热管理控制等功能。",
                "type": KnowledgeType.CONTROLLER,
                "domain": "VCU",
                "tags": ["功能说明", "控制器", "整车控制"],
                "source": "技术文档",
                "meta_data": {"category": "function", "name": "VCU基本功能"}
            },
            {
                "content": "故障注入测试步骤：1.设置正常工况 2.注入故障信号 3.监控系统响应 4.验证安全机制 5.恢复系统状态。",
                "type": KnowledgeType.TEST_PATTERN,
                "domain": "安全测试",
                "tags": ["测试模式", "故障注入", "安全测试"],
                "source": "测试经验",
                "meta_data": {"name": "故障注入测试模式", "steps": 5, "success_rate": 0.95}
            }
        ]
        
        for item in initial_data:
            knowledge_base.add_knowledge_item(
                content=item["content"],
                type=item["type"],
                domain=item["domain"],
                tags=item["tags"],
                source=item["source"],
                meta_data=item["meta_data"]
            )
            print(f"✓ 添加: {item['domain']} - {item['content'][:30]}...")
        
        # 测试搜索
        results = knowledge_base.search_knowledge(query="测试", top_k=3)
        
        print(f"\n✅ 知识库初始化完成！")
        print(f"搜索测试结果: {len(results)} 条")
        
        for i, result in enumerate(results[:2], 1):
            print(f"{i}. {result.content[:50]}... (置信度: {result.confidence:.2f})")
        
        return knowledge_base
            
    except Exception as e:
        print(f"❌ 知识库初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    create_initial_knowledge()
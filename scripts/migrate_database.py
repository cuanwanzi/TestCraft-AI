# scripts/migrate_database.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import json

def migrate_database():
    """迁移数据库，将 metadata 列重命名为 meta_data"""
    
    db_path = "./data/knowledge_base/knowledge.db"
    db_url = f"sqlite:///{db_path}"
    
    if not os.path.exists(db_path):
        print("数据库文件不存在，无需迁移")
        return
    
    engine = create_engine(db_url)
    
    # 检查表结构
    inspector = inspect(engine)
    columns = inspector.get_columns('knowledge_records')
    
    # 检查是否有 metadata 列
    has_metadata = any(col['name'] == 'metadata' for col in columns)
    has_meta_data = any(col['name'] == 'meta_data' for col in columns)
    
    if has_metadata and not has_meta_data:
        print("发现旧的 metadata 列，开始迁移...")
        
        # 重命名列
        with engine.begin() as conn:
            # 备份数据
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS knowledge_records_backup AS 
                SELECT * FROM knowledge_records
            """))
            
            # 重命名列
            conn.execute(text("""
                CREATE TABLE knowledge_records_new (
                    id VARCHAR NOT NULL, 
                    content TEXT NOT NULL, 
                    type VARCHAR NOT NULL, 
                    domain VARCHAR NOT NULL, 
                    tags JSON, 
                    source VARCHAR NOT NULL, 
                    confidence FLOAT, 
                    meta_data JSON, 
                    created_at DATETIME, 
                    updated_at DATETIME, 
                    usage_count INTEGER, 
                    success_rate FLOAT, 
                    PRIMARY KEY (id)
                )
            """))
            
            # 复制数据
            conn.execute(text("""
                INSERT INTO knowledge_records_new 
                SELECT id, content, type, domain, tags, source, confidence, 
                       metadata, created_at, updated_at, usage_count, success_rate 
                FROM knowledge_records
            """))
            
            # 删除旧表，重命名新表
            conn.execute(text("DROP TABLE knowledge_records"))
            conn.execute(text("ALTER TABLE knowledge_records_new RENAME TO knowledge_records"))
            
            print("✅ 数据库迁移完成：metadata -> meta_data")
    
    elif has_meta_data:
        print("✅ 数据库已经是新版本（使用 meta_data 列）")
    else:
        print("⚠️  数据库表结构异常，可能需要重新创建")

if __name__ == "__main__":
    migrate_database()
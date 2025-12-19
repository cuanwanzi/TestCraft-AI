# scripts/init_simple.py
#!/usr/bin/env python3
import sys
import os
import traceback

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """简单初始化"""
    print("🚀 开始初始化系统...")
    
    try:
        # 创建目录
        dirs = [
            "./data",
            "./data/knowledge_base", 
            "./data/templates",
            "./data/logs",
            "./data/uploads",
            "./data/models"
        ]
        
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
            print(f"✓ 创建目录: {dir_path}")
        
        # 检查 ChromaDB 是否可用
        try:
            import chromadb
            print("✓ ChromaDB 已安装")
            
            # 测试新版 API
            test_client = chromadb.PersistentClient(path="./test_chroma")
            test_collection = test_client.create_collection(name="test")
            test_client.delete_collection("test")
            import shutil
            if os.path.exists("./test_chroma"):
                shutil.rmtree("./test_chroma")
            print("✓ ChromaDB 新版 API 工作正常")
            
        except Exception as e:
            print(f"⚠️  ChromaDB 测试失败: {str(e)}")
            print("将使用简单模式")
        
        # 初始化知识库
        print("\n📚 初始化知识库...")
        from src.core.knowledge_base import create_initial_knowledge
        
        kb = create_initial_knowledge()
        
        print("\n✅ 系统初始化完成！")
        
        return kb
        
    except Exception as e:
        print(f"\n❌ 初始化失败: {str(e)}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()
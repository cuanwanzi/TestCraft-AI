import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.knowledge_base import create_initial_knowledge
import logging

logging.basicConfig(level=logging.INFO)

def main():
    """初始化知识库"""
    print("📚 开始初始化知识库...")
    
    try:
        # 确保数据目录存在
        os.makedirs("./data/knowledge_base", exist_ok=True)
        
        # 创建初始知识库
        create_initial_knowledge()
        
        print("✅ 知识库初始化完成！")
        
    except Exception as e:
        print(f"❌ 知识库初始化失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
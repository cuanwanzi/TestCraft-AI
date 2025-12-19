# scripts/init_knowledge_base.py
#!/usr/bin/env python3
import sys
import os
import traceback

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

def main():
    """初始化知识库"""
    print("📚 开始初始化知识库...")
    
    try:
        # 确保数据目录存在
        data_dirs = [
            "./data",
            "./data/knowledge_base",
            "./data/templates",
            "./data/logs",
            "./data/uploads",
            "./data/models"
        ]
        
        for dir_path in data_dirs:
            os.makedirs(dir_path, exist_ok=True)
            print(f"✓ 创建目录: {dir_path}")
        
        # 导入知识库模块
        from src.core.knowledge_base import create_initial_knowledge
        
        # 创建初始知识库
        create_initial_knowledge()
        
        print("✅ 知识库初始化成功完成！")
        
    except Exception as e:
        print(f"❌ 知识库初始化失败: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
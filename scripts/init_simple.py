# scripts/init_fixed.py
#!/usr/bin/env python3
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """修复后的初始化"""
    print("🔧 使用修复版本初始化...")
    
    try:
        # 设置环境变量避免网络请求
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        os.environ['HF_HUB_OFFLINE'] = '1'
        
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
        
        # 导入并初始化
        from src.core.knowledge_base import create_initial_knowledge
        
        kb = create_initial_knowledge()
        
        print("\n✅ 初始化成功完成！")
        
        return kb
        
    except Exception as e:
        print(f"\n❌ 初始化失败: {str(e)}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()
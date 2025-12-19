# test_embedder.py
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 测试嵌入器
from src.core.knowledge_base import SimpleEmbedder, UniversalEmbedder

def test_embedder():
    print("测试嵌入器...")
    
    # 测试 SimpleEmbedder
    simple = SimpleEmbedder()
    result = simple.encode("测试文本")
    
    print(f"SimpleEmbedder 返回类型: {type(result)}")
    print(f"长度: {len(result)}")
    print(f"是否列表: {isinstance(result, list)}")
    
    # 测试 UniversalEmbedder 包装
    universal = UniversalEmbedder(simple)
    result2 = universal.encode("测试文本")
    
    print(f"\nUniversalEmbedder 返回类型: {type(result2)}")
    print(f"长度: {len(result2)}")
    print(f"是否列表: {isinstance(result2, list)}")
    
    # 测试是否能调用 tolist（不应该）
    try:
        result2.tolist()
        print("❌ 错误: 列表不应该有 tolist 方法")
    except AttributeError:
        print("✓ 正确: 列表没有 tolist 方法")
    
    print("\n✅ 嵌入器测试通过")

if __name__ == "__main__":
    test_embedder()
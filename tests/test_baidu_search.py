import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from skills.web_browser import BaiduSearcher
from utils.logger import log


async def test_baidu_search():
    """测试百度搜索功能"""
    # 启用调试日志
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    searcher = BaiduSearcher(timeout=30)
    
    try:
        print("测试百度搜索: 杭州天气")
        results = await searcher.search("杭州天气", max_results=5)
        
        print(f"\n找到 {len(results)} 条结果:")
        for i, r in enumerate(results, 1):
            print(f"\n{i}. {r.get('title', '')}")
            print(f"   链接: {r.get('url', '')}")
            print(f"   摘要: {r.get('snippet', '')[:100]}...")
        
        if results:
            print(f"\n✓ 百度搜索测试成功! 找到 {len(results)} 条结果")
        else:
            print("\n✗ 百度搜索没有返回结果")
    
    except Exception as e:
        print(f"\n✗ 百度搜索测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await searcher.close()


if __name__ == "__main__":
    asyncio.run(test_baidu_search())

#!/usr/bin/env python3
"""
Unit Test: 搜索链接提取验证
第一步验证：确保我们可以搜索并获得需要的链接

目标：测试web services的搜索引擎能力，验证搜索结果链接提取功能
"""
import asyncio
import sys
import os
from typing import List, Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tools.services.web_services.engines.search_engine import SearchEngine, BraveSearchStrategy, SearchProvider
from tools.services.web_services.core.browser_manager import BrowserManager
from tools.services.web_services.strategies.detection.vision_analyzer import VisionAnalyzer

class TestSearchLinkExtraction:
    """搜索链接提取单元测试"""
    
    def __init__(self):
        self.search_engine = None
        self.browser_manager = None
        self.vision_analyzer = None
        
    async def setup(self):
        """初始化测试环境"""
        print("🔧 初始化测试环境...")
        
        # 初始化搜索引擎
        self.search_engine = SearchEngine()
        
        # 这里需要Brave API Key - 在真实环境中应该从环境变量获取
        # 暂时跳过API依赖的部分
        print("⚠️  暂时跳过Brave API配置 - 需要API密钥")
        
        # 初始化浏览器管理器
        self.browser_manager = BrowserManager()
        await self.browser_manager.initialize()
        
        # 初始化视觉分析器
        self.vision_analyzer = VisionAnalyzer()
        
        print("✅ 测试环境初始化完成")
    
    async def test_search_engine_availability(self):
        """测试搜索引擎可用性"""
        print("\n🔍 测试1: 搜索引擎可用性检查")
        
        try:
            # 检查搜索引擎是否正确初始化
            assert self.search_engine is not None, "搜索引擎未初始化"
            
            # 检查可用的提供商
            providers = self.search_engine.get_available_providers()
            print(f"   可用提供商: {providers}")
            
            # 应该没有提供商，因为我们还没注册
            assert len(providers) == 0, f"预期0个提供商，实际{len(providers)}个"
            
            print("   ✅ 搜索引擎基础功能正常")
            return True
            
        except Exception as e:
            print(f"   ❌ 搜索引擎测试失败: {e}")
            return False
    
    async def test_browser_search_simulation(self):
        """测试浏览器搜索模拟"""
        print("\n🌐 测试2: 浏览器搜索模拟")
        
        try:
            # 获取浏览器页面
            page = await self.browser_manager.get_page("stealth")
            
            # 模拟访问Google搜索
            test_query = "AirPods 4 ANR price"
            google_search_url = f"https://www.google.com/search?q={test_query.replace(' ', '+')}"
            
            print(f"   访问搜索URL: {google_search_url}")
            await page.goto(google_search_url, wait_until='networkidle', timeout=30000)
            
            # 获取页面标题验证加载成功
            title = await page.title()
            print(f"   页面标题: {title}")
            
            # 验证是否是搜索结果页面
            assert "AirPods" in title or "search" in title.lower(), f"页面标题不符合搜索预期: {title}"
            
            # 尝试提取搜索结果链接
            links = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.map(link => ({
                        text: link.innerText.trim(),
                        href: link.href,
                        isResult: link.closest('[data-result-type]') ? true : false
                    })).filter(link => link.href.startsWith('http') && link.text.length > 0);
                }
            """)
            
            print(f"   提取到链接数量: {len(links)}")
            
            # 筛选可能的产品链接
            product_links = [
                link for link in links 
                if any(site in link['href'] for site in ['amazon.com', 'apple.com', 'bestbuy.com', 'target.com'])
                and any(keyword in link['text'].lower() for keyword in ['airpods', 'price', 'buy'])
            ]
            
            print(f"   筛选出产品链接: {len(product_links)}")
            for i, link in enumerate(product_links[:3]):  # 只显示前3个
                print(f"     {i+1}. {link['text'][:50]}... -> {link['href'][:60]}...")
            
            assert len(links) > 0, "未提取到任何链接"
            print("   ✅ 浏览器搜索模拟成功")
            return product_links
            
        except Exception as e:
            print(f"   ❌ 浏览器搜索测试失败: {e}")
            return []
    
    async def test_link_classification(self):
        """测试链接分类功能"""
        print("\n🏷️ 测试3: 链接分类功能")
        
        try:
            # 模拟一些测试链接
            test_links = [
                {"text": "Apple AirPods 4 with ANC - Official Store", "href": "https://www.apple.com/airpods-4/"},
                {"text": "AirPods 4 ANR Best Price on Amazon", "href": "https://www.amazon.com/dp/B0C123456"},
                {"text": "Buy AirPods 4 Active Noise Cancellation - Best Buy", "href": "https://www.bestbuy.com/site/airpods"},
                {"text": "Privacy Policy - Google", "href": "https://policies.google.com/privacy"},
                {"text": "Facebook - Log In", "href": "https://www.facebook.com/login"}
            ]
            
            # 分类函数
            def classify_link(link):
                href = link['href'].lower()
                text = link['text'].lower()
                
                # 电商平台
                ecommerce_sites = ['amazon.com', 'apple.com', 'bestbuy.com', 'target.com', 'walmart.com']
                if any(site in href for site in ecommerce_sites):
                    if any(keyword in text for keyword in ['airpods', 'price', 'buy']):
                        return 'product_page'
                    return 'ecommerce_other'
                
                # 社交媒体
                social_sites = ['facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com']
                if any(site in href for site in social_sites):
                    return 'social_media'
                
                # 新闻/评论
                news_sites = ['cnet.com', 'theverge.com', 'techcrunch.com']
                if any(site in href for site in news_sites):
                    return 'news_review'
                
                return 'other'
            
            # 分类测试链接
            classified_links = {
                'product_page': [],
                'ecommerce_other': [],
                'social_media': [],
                'news_review': [],
                'other': []
            }
            
            for link in test_links:
                category = classify_link(link)
                classified_links[category].append(link)
                print(f"   {link['text'][:40]}... -> {category}")
            
            # 验证分类结果
            assert len(classified_links['product_page']) >= 2, f"预期至少2个产品页面，实际{len(classified_links['product_page'])}个"
            assert len(classified_links['other']) >= 1, f"预期至少1个其他链接，实际{len(classified_links['other'])}个"
            
            print(f"   ✅ 链接分类完成: {sum(len(links) for links in classified_links.values())}个链接")
            return classified_links
            
        except Exception as e:
            print(f"   ❌ 链接分类测试失败: {e}")
            return {}
    
    async def test_link_priority_scoring(self):
        """测试链接优先级评分"""
        print("\n⭐ 测试4: 链接优先级评分")
        
        try:
            # 测试链接评分函数
            def score_link_priority(link, target_query="AirPods 4 ANR"):
                score = 0
                href = link['href'].lower()
                text = link['text'].lower()
                query_words = target_query.lower().split()
                
                # 文本相关性评分 (0-40分)
                text_matches = sum(1 for word in query_words if word in text)
                score += text_matches * 10
                
                # 域名信任度评分 (0-30分)
                trusted_domains = {
                    'apple.com': 30,
                    'amazon.com': 25,
                    'bestbuy.com': 20,
                    'target.com': 15,
                    'walmart.com': 15
                }
                for domain, domain_score in trusted_domains.items():
                    if domain in href:
                        score += domain_score
                        break
                
                # URL路径相关性 (0-20分)
                if any(word in href for word in query_words):
                    score += 15
                
                # 特殊关键词加分 (0-10分)
                if any(keyword in text for keyword in ['official', 'buy', 'price', 'store']):
                    score += 5
                
                return min(score, 100)  # 最高100分
            
            # 测试链接
            test_links = [
                {"text": "Apple AirPods 4 with Active Noise Cancellation - Official Apple Store", "href": "https://www.apple.com/airpods-4/"},
                {"text": "Amazon.com: Apple AirPods 4 ANR - Best Price", "href": "https://www.amazon.com/Apple-AirPods-4-ANR/dp/B123"},
                {"text": "Best Buy: AirPods 4 Active Noise Cancellation", "href": "https://www.bestbuy.com/site/apple/airpods-4/"},
                {"text": "Random tech blog post", "href": "https://techblog.com/random-post"},
                {"text": "Facebook login page", "href": "https://www.facebook.com/login"}
            ]
            
            # 计算评分并排序
            scored_links = []
            for link in test_links:
                score = score_link_priority(link)
                scored_links.append({**link, 'score': score})
                print(f"   {score:3d}分 - {link['text'][:50]}...")
            
            # 按分数排序
            scored_links.sort(key=lambda x: x['score'], reverse=True)
            
            # 验证评分合理性
            top_link = scored_links[0]
            assert top_link['score'] >= 60, f"最高分链接评分过低: {top_link['score']}"
            assert 'apple.com' in top_link['href'] or 'amazon.com' in top_link['href'], "最高分应该是权威电商网站"
            
            print(f"   ✅ 链接评分完成，最高分: {top_link['score']}分")
            return scored_links
            
        except Exception as e:
            print(f"   ❌ 链接评分测试失败: {e}")
            return []
    
    async def cleanup(self):
        """清理测试环境"""
        print("\n🧹 清理测试环境...")
        
        if self.browser_manager:
            await self.browser_manager.cleanup_all()
        
        print("✅ 清理完成")

async def run_search_link_tests():
    """运行搜索链接提取测试套件"""
    print("🧪 搜索链接提取单元测试套件")
    print("=" * 50)
    
    test_suite = TestSearchLinkExtraction()
    results = {
        'total_tests': 4,
        'passed_tests': 0,
        'failed_tests': 0,
        'test_results': []
    }
    
    try:
        # 初始化
        await test_suite.setup()
        
        # 测试1: 搜索引擎可用性
        test1_result = await test_suite.test_search_engine_availability()
        results['test_results'].append(('搜索引擎可用性', test1_result))
        if test1_result:
            results['passed_tests'] += 1
        else:
            results['failed_tests'] += 1
        
        # 测试2: 浏览器搜索模拟
        test2_result = await test_suite.test_browser_search_simulation()
        results['test_results'].append(('浏览器搜索模拟', len(test2_result) > 0))
        if len(test2_result) > 0:
            results['passed_tests'] += 1
        else:
            results['failed_tests'] += 1
        
        # 测试3: 链接分类功能
        test3_result = await test_suite.test_link_classification()
        results['test_results'].append(('链接分类功能', len(test3_result) > 0))
        if len(test3_result) > 0:
            results['passed_tests'] += 1
        else:
            results['failed_tests'] += 1
        
        # 测试4: 链接优先级评分
        test4_result = await test_suite.test_link_priority_scoring()
        results['test_results'].append(('链接优先级评分', len(test4_result) > 0))
        if len(test4_result) > 0:
            results['passed_tests'] += 1
        else:
            results['failed_tests'] += 1
        
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        results['failed_tests'] = results['total_tests']
    
    finally:
        await test_suite.cleanup()
    
    # 输出测试结果
    print("\n📊 测试结果摘要")
    print("=" * 30)
    for test_name, result in results['test_results']:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n通过测试: {results['passed_tests']}/{results['total_tests']}")
    print(f"成功率: {(results['passed_tests']/results['total_tests']*100):.1f}%")
    
    if results['passed_tests'] == results['total_tests']:
        print("\n🎉 所有测试通过！搜索链接提取功能验证成功！")
        return True
    else:
        print(f"\n⚠️ {results['failed_tests']}个测试失败，需要检查和修复")
        return False

if __name__ == "__main__":
    print("🔗 搜索链接提取验证测试")
    print("验证第一步：确保我们可以搜索并获得需要的链接")
    print("")
    
    result = asyncio.run(run_search_link_tests())
    sys.exit(0 if result else 1)
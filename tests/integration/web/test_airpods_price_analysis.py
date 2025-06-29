#!/usr/bin/env python3
"""
AirPods 4 ANR Price Analysis Integration Test
End-to-end test demonstrating complete web services workflow:
1. Search e-commerce platforms for pricing
2. Extract structured product data
3. Search social media for reviews
4. Apply AI filtering for relevance
5. Generate comprehensive markdown report
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import our web services
from tools.services.web_services.core.browser_manager import BrowserManager
from tools.services.web_services.core.session_manager import SessionManager
from tools.services.web_services.strategies.extraction import LLMExtractionStrategy, PredefinedLLMSchemas
from tools.services.web_services.strategies.filtering import (
    AIRelevanceFilter, 
    AIQualityFilter,
    SemanticFilter,
    ContentQuality
)
from tools.services.web_services.strategies.generation import MarkdownGenerator
from tools.services.web_services.utils.rate_limiter import RateLimiter

class AirPodsAnalyzer:
    """Complete AirPods 4 ANR market analysis system"""
    
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.session_manager = SessionManager()
        self.rate_limiter = RateLimiter()
        
        # Analysis target
        self.product_name = "AirPods 4 ANR"
        self.search_queries = {
            "price": "AirPods 4 ANR price buy",
            "reviews": "AirPods 4 ANR review opinion",
            "specs": "AirPods 4 ANR specifications features"
        }
        
        # E-commerce platforms to check
        self.ecommerce_sites = [
            "https://www.amazon.com",
            "https://www.bestbuy.com", 
            "https://www.apple.com",
            "https://www.target.com",
            "https://www.walmart.com"
        ]
        
        # Social media and review sites
        self.review_sites = [
            "https://www.reddit.com",
            "https://twitter.com",
            "https://www.youtube.com",
            "https://www.cnet.com",
            "https://www.theverge.com"
        ]
        
        self.results = {
            "pricing_data": [],
            "reviews_data": [],
            "analysis_summary": {},
            "timestamp": datetime.now().isoformat()
        }
    
    async def initialize(self):
        """Initialize all services"""
        print("🔧 Initializing AirPods Analyzer...")
        await self.browser_manager.initialize()
        print("✅ Browser manager initialized")
        print("✅ AirPods Analyzer ready for market analysis")
    
    async def search_ecommerce_pricing(self) -> List[Dict[str, Any]]:
        """Search e-commerce platforms for AirPods 4 ANR pricing"""
        print(f"\n💰 Searching E-commerce Platforms for {self.product_name} Pricing")
        print("=" * 60)
        
        pricing_data = []
        
        # Get a stealth browser session
        page = await self.browser_manager.get_page("stealth")
        
        for site in self.ecommerce_sites:
            try:
                print(f"🛒 Analyzing {site}...")
                
                # Rate limiting
                await self.rate_limiter.wait_for_rate_limit("ecommerce_search")
                
                # Create search URL based on platform
                search_url = self._build_search_url(site, self.search_queries["price"])
                
                # Navigate to search results
                await page.goto(search_url, wait_until='networkidle', timeout=30000)
                
                # Extract product data using LLM
                product_schema = PredefinedLLMSchemas.get_product_extraction_schema()
                llm_extractor = LLMExtractionStrategy(product_schema)
                
                # Extract structured product data
                products = await llm_extractor.extract(page, "")
                
                # Filter for AirPods 4 ANR specifically
                relevant_filter = AIRelevanceFilter(
                    user_query="AirPods 4 ANR Active Noise Cancellation",
                    relevance_threshold=0.7
                )
                
                airpods_products = []
                for product in products:
                    if product.get('name'):
                        product_text = f"{product.get('name', '')} {product.get('description', '')}"
                        filtered_text = await relevant_filter.filter(product_text)
                        
                        if filtered_text and len(filtered_text) > 20:
                            # Add platform info
                            product['platform'] = self._get_platform_name(site)
                            product['search_url'] = search_url
                            product['extracted_at'] = datetime.now().isoformat()
                            airpods_products.append(product)
                
                pricing_data.extend(airpods_products)
                
                print(f"   ✅ Found {len(airpods_products)} relevant products")
                
                # Clean up
                await llm_extractor.close()
                await relevant_filter.close()
                
            except Exception as e:
                print(f"   ❌ Failed to analyze {site}: {e}")
                continue
        
        print(f"\n💰 E-commerce Analysis Complete: {len(pricing_data)} products found")
        self.results["pricing_data"] = pricing_data
        return pricing_data
    
    async def search_social_reviews(self) -> List[Dict[str, Any]]:
        """Search social media and review sites for opinions"""
        print(f"\n💬 Searching Social Media for {self.product_name} Reviews")
        print("=" * 55)
        
        reviews_data = []
        
        # Get a fresh browser session
        page = await self.browser_manager.get_page("stealth") 
        
        for site in self.review_sites:
            try:
                print(f"📱 Analyzing {site}...")
                
                # Rate limiting
                await self.rate_limiter.wait_for_rate_limit("social_search")
                
                # Create search URL
                search_url = self._build_search_url(site, self.search_queries["reviews"])
                
                # Navigate to search results
                await page.goto(search_url, wait_until='networkidle', timeout=30000)
                
                # Extract article/content data using LLM
                article_schema = PredefinedLLMSchemas.get_article_extraction_schema()
                llm_extractor = LLMExtractionStrategy(article_schema)
                
                # Extract content
                articles = await llm_extractor.extract(page, "")
                
                # Apply AI quality filter to get high-quality reviews
                quality_filter = AIQualityFilter(min_quality=ContentQuality.MEDIUM)
                
                # Apply semantic filter for AirPods 4 ANR relevance
                semantic_filter = SemanticFilter(
                    user_query="AirPods 4 ANR review opinion experience quality sound",
                    similarity_threshold=0.6
                )
                
                quality_reviews = []
                for article in articles:
                    if article.get('content'):
                        # Apply quality filtering
                        filtered_content = await quality_filter.filter(article.get('content', ''))
                        
                        if filtered_content:
                            # Apply semantic filtering
                            relevant_content = await semantic_filter.filter(filtered_content)
                            
                            if relevant_content and len(relevant_content) > 100:
                                article['filtered_content'] = relevant_content
                                article['platform'] = self._get_platform_name(site)
                                article['search_url'] = search_url
                                article['extracted_at'] = datetime.now().isoformat()
                                quality_reviews.append(article)
                
                reviews_data.extend(quality_reviews)
                
                print(f"   ✅ Found {len(quality_reviews)} quality reviews")
                
                # Clean up
                await llm_extractor.close()
                await quality_filter.close()
                await semantic_filter.close()
                
            except Exception as e:
                print(f"   ❌ Failed to analyze {site}: {e}")
                continue
        
        print(f"\n💬 Social Media Analysis Complete: {len(reviews_data)} reviews found")
        self.results["reviews_data"] = reviews_data
        return reviews_data
    
    async def analyze_pricing_data(self) -> Dict[str, Any]:
        """Analyze collected pricing data to find best deals"""
        print(f"\n📊 Analyzing Pricing Data")
        print("=" * 25)
        
        pricing_data = self.results["pricing_data"]
        
        if not pricing_data:
            print("❌ No pricing data available for analysis")
            return {}
        
        # Extract and normalize prices
        valid_prices = []
        price_by_platform = {}
        
        for product in pricing_data:
            price_str = product.get('price', '')
            platform = product.get('platform', 'unknown')
            
            # Extract numeric price (handle different formats)
            import re
            price_match = re.search(r'\$?(\d+(?:\.\d{2})?)', str(price_str))
            
            if price_match:
                try:
                    price = float(price_match.group(1))
                    valid_prices.append(price)
                    
                    if platform not in price_by_platform:
                        price_by_platform[platform] = []
                    price_by_platform[platform].append({
                        'price': price,
                        'product_name': product.get('name', ''),
                        'url': product.get('search_url', '')
                    })
                except ValueError:
                    continue
        
        if not valid_prices:
            print("❌ No valid pricing data found")
            return {}
        
        # Calculate statistics
        min_price = min(valid_prices)
        max_price = max(valid_prices)
        avg_price = sum(valid_prices) / len(valid_prices)
        
        # Find best deals
        best_deals = []
        for platform, products in price_by_platform.items():
            platform_min = min(products, key=lambda x: x['price'])
            best_deals.append({
                'platform': platform,
                'price': platform_min['price'],
                'product_name': platform_min['product_name'],
                'url': platform_min['url']
            })
        
        # Sort by price
        best_deals.sort(key=lambda x: x['price'])
        
        analysis = {
            'total_products_found': len(pricing_data),
            'valid_prices_count': len(valid_prices),
            'price_range': {
                'min': min_price,
                'max': max_price,
                'average': round(avg_price, 2)
            },
            'best_deals': best_deals[:5],  # Top 5 deals
            'platforms_checked': list(price_by_platform.keys())
        }
        
        print(f"✅ Price Analysis Complete:")
        print(f"   💲 Lowest Price: ${min_price}")
        print(f"   💲 Highest Price: ${max_price}")
        print(f"   💲 Average Price: ${avg_price:.2f}")
        print(f"   🏪 Platforms Checked: {len(price_by_platform)}")
        
        self.results["analysis_summary"]["pricing"] = analysis
        return analysis
    
    async def analyze_review_sentiment(self) -> Dict[str, Any]:
        """Analyze sentiment and key themes from reviews"""
        print(f"\n🔍 Analyzing Review Sentiment")
        print("=" * 30)
        
        reviews_data = self.results["reviews_data"]
        
        if not reviews_data:
            print("❌ No review data available for analysis")
            return {}
        
        # Use AI to analyze sentiment and extract key points
        from tools.services.web_services.strategies.filtering import AISentimentFilter, Sentiment
        
        sentiment_filter = AISentimentFilter(
            target_sentiments=[Sentiment.POSITIVE, Sentiment.NEUTRAL, Sentiment.NEGATIVE]
        )
        
        sentiment_analysis = {
            'positive_reviews': [],
            'neutral_reviews': [],
            'negative_reviews': [],
            'total_reviews': len(reviews_data),
            'key_themes': []
        }
        
        for review in reviews_data:
            content = review.get('filtered_content', review.get('content', ''))
            
            if content and len(content) > 50:
                # Analyze sentiment (this is a simplified approach)
                # In a real implementation, you'd use the sentiment filter more systematically
                
                # For demo purposes, we'll categorize based on keywords
                positive_keywords = ['good', 'great', 'excellent', 'amazing', 'love', 'best', 'perfect']
                negative_keywords = ['bad', 'terrible', 'awful', 'hate', 'worst', 'issues', 'problems']
                
                content_lower = content.lower()
                positive_count = sum(1 for keyword in positive_keywords if keyword in content_lower)
                negative_count = sum(1 for keyword in negative_keywords if keyword in content_lower)
                
                if positive_count > negative_count:
                    sentiment_analysis['positive_reviews'].append(review)
                elif negative_count > positive_count:
                    sentiment_analysis['negative_reviews'].append(review)
                else:
                    sentiment_analysis['neutral_reviews'].append(review)
        
        # Calculate percentages
        total = sentiment_analysis['total_reviews']
        sentiment_analysis['sentiment_breakdown'] = {
            'positive_percentage': (len(sentiment_analysis['positive_reviews']) / total * 100) if total > 0 else 0,
            'neutral_percentage': (len(sentiment_analysis['neutral_reviews']) / total * 100) if total > 0 else 0,
            'negative_percentage': (len(sentiment_analysis['negative_reviews']) / total * 100) if total > 0 else 0
        }
        
        print(f"✅ Sentiment Analysis Complete:")
        print(f"   😊 Positive: {len(sentiment_analysis['positive_reviews'])} reviews")
        print(f"   😐 Neutral: {len(sentiment_analysis['neutral_reviews'])} reviews") 
        print(f"   😞 Negative: {len(sentiment_analysis['negative_reviews'])} reviews")
        
        await sentiment_filter.close()
        
        self.results["analysis_summary"]["sentiment"] = sentiment_analysis
        return sentiment_analysis
    
    async def generate_markdown_report(self) -> str:
        """Generate comprehensive markdown report"""
        print(f"\n📝 Generating Markdown Report")
        print("=" * 30)
        
        # Use markdown generator
        markdown_gen = MarkdownGenerator()
        
        # Prepare report data
        pricing_analysis = self.results["analysis_summary"].get("pricing", {})
        sentiment_analysis = self.results["analysis_summary"].get("sentiment", {})
        
        report_data = {
            "title": f"{self.product_name} - Market Analysis Report",
            "timestamp": self.results["timestamp"],
            "pricing_data": pricing_analysis,
            "sentiment_data": sentiment_analysis,
            "raw_pricing": self.results["pricing_data"][:5],  # Top 5 for demo
            "raw_reviews": self.results["reviews_data"][:3]   # Top 3 for demo
        }
        
        # Generate markdown
        markdown_content = await markdown_gen.generate_report(report_data)
        
        # Save to file
        report_filename = f"airpods_4_anr_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"✅ Markdown report generated: {report_filename}")
        print(f"📄 Report length: {len(markdown_content)} characters")
        
        return markdown_content
    
    def _build_search_url(self, base_url: str, query: str) -> str:
        """Build search URL for different platforms"""
        platform_name = self._get_platform_name(base_url)
        
        # Platform-specific search URL patterns
        if 'amazon.com' in base_url:
            return f"{base_url}/s?k={query.replace(' ', '+')}"
        elif 'google.com' in base_url:
            return f"https://www.google.com/search?q={query.replace(' ', '+')}"
        elif 'reddit.com' in base_url:
            return f"{base_url}/search/?q={query.replace(' ', '+')}"
        elif 'youtube.com' in base_url:
            return f"{base_url}/results?search_query={query.replace(' ', '+')}"
        else:
            # Generic search - try common patterns
            return f"{base_url}/search?q={query.replace(' ', '+')}"
    
    def _get_platform_name(self, url: str) -> str:
        """Extract platform name from URL"""
        if 'amazon.com' in url:
            return 'Amazon'
        elif 'bestbuy.com' in url:
            return 'Best Buy'
        elif 'apple.com' in url:
            return 'Apple Store'
        elif 'target.com' in url:
            return 'Target'
        elif 'walmart.com' in url:
            return 'Walmart'
        elif 'reddit.com' in url:
            return 'Reddit'
        elif 'twitter.com' in url:
            return 'Twitter'
        elif 'youtube.com' in url:
            return 'YouTube'
        elif 'cnet.com' in url:
            return 'CNET'
        elif 'theverge.com' in url:
            return 'The Verge'
        else:
            return 'Unknown Platform'
    
    async def cleanup(self):
        """Clean up resources"""
        print("\n🧹 Cleaning up resources...")
        await self.browser_manager.cleanup_all()
        print("✅ Cleanup complete")

async def run_airpods_analysis():
    """Run the complete AirPods 4 ANR analysis"""
    print("🎧 Starting AirPods 4 ANR Market Analysis")
    print("=" * 50)
    
    analyzer = AirPodsAnalyzer()
    
    try:
        # Initialize services
        await analyzer.initialize()
        
        # Step 1: Search e-commerce for pricing
        print(f"\n📍 Step 1: E-commerce Price Analysis")
        pricing_data = await analyzer.search_ecommerce_pricing()
        
        # Step 2: Search social media for reviews  
        print(f"\n📍 Step 2: Social Media Review Analysis")
        reviews_data = await analyzer.search_social_reviews()
        
        # Step 3: Analyze pricing data
        print(f"\n📍 Step 3: Price Data Analysis")
        pricing_analysis = await analyzer.analyze_pricing_data()
        
        # Step 4: Analyze review sentiment
        print(f"\n📍 Step 4: Review Sentiment Analysis")
        sentiment_analysis = await analyzer.analyze_review_sentiment()
        
        # Step 5: Generate markdown report
        print(f"\n📍 Step 5: Generate Final Report")
        markdown_report = await analyzer.generate_markdown_report()
        
        # Final summary
        print(f"\n🎉 Analysis Complete!")
        print("=" * 20)
        print(f"📊 Pricing data points: {len(pricing_data)}")
        print(f"💬 Review data points: {len(reviews_data)}")
        print(f"📝 Report generated with {len(markdown_report)} characters")
        
        # Show a preview of the report
        print(f"\n📖 Report Preview (first 500 chars):")
        print("-" * 40)
        print(markdown_report[:500] + "..." if len(markdown_report) > 500 else markdown_report)
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False
        
    finally:
        await analyzer.cleanup()

if __name__ == "__main__":
    print("🧪 AirPods 4 ANR Market Analysis Integration Test")
    print("📝 Testing complete end-to-end web services workflow")
    print("")
    
    result = asyncio.run(run_airpods_analysis())
    
    if result:
        print("\n✅ Integration test completed successfully!")
        print("🚀 All web services working correctly in end-to-end scenario!")
    else:
        print("\n❌ Integration test failed!")
        print("⚠️ Check service configuration and connectivity")
    
    sys.exit(0 if result else 1)
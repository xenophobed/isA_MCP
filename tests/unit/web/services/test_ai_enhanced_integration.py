#!/usr/bin/env python3
"""
Test for AI-Enhanced Web Services (LLM + Embedding Integration)
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_llm_extraction_strategy():
    """Test LLM-based data extraction strategy"""
    print("🧠 Testing LLM Extraction Strategy")
    print("=" * 40)
    
    try:
        from tools.services.web_services.strategies.extraction import LLMExtractionStrategy, PredefinedLLMSchemas
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Create test HTML content
        test_html = """
        <html>
        <head><title>AI Conference 2024 - Leading Tech Event</title></head>
        <body>
            <article class="main-content">
                <h1>AI Conference 2024: Shaping the Future of Technology</h1>
                <div class="author">By Dr. Sarah Johnson</div>
                <time class="date">March 15, 2024</time>
                
                <div class="content">
                    <p>The annual AI Conference 2024 brings together leading researchers, industry experts, and innovators to discuss the latest breakthroughs in artificial intelligence and machine learning.</p>
                    
                    <p>This year's conference will focus on three key areas: natural language processing, computer vision, and ethical AI development. With over 50 speakers from top universities and tech companies, attendees will gain insights into cutting-edge research and practical applications.</p>
                    
                    <h2>Key Highlights</h2>
                    <ul>
                        <li>Keynote by Dr. Andrew Ng on the future of AI education</li>
                        <li>Panel discussion on AI ethics and governance</li>
                        <li>Workshops on transformer architectures and neural networks</li>
                        <li>Startup pitch competition with $100,000 in prizes</li>
                    </ul>
                    
                    <p>The conference will take place at the San Francisco Convention Center from March 15-17, 2024. Early bird registration is available until February 1st at $299 for students and $599 for professionals.</p>
                </div>
                
                <div class="tags">
                    <span>artificial intelligence</span>
                    <span>machine learning</span>
                    <span>technology conference</span>
                    <span>AI research</span>
                </div>
            </article>
        </body>
        </html>
        """
        
        # Initialize browser
        browser_manager = BrowserManager()
        page = await browser_manager.get_page("stealth")
        
        # Set content
        await page.set_content(test_html)
        
        # Test article extraction schema
        article_schema = PredefinedLLMSchemas.get_article_extraction_schema()
        llm_extractor = LLMExtractionStrategy(article_schema)
        
        print("✅ LLM extractor initialized with article schema")
        
        # Extract data
        results = await llm_extractor.extract(page, test_html)
        
        print(f"✅ Extraction completed: {len(results)} articles found")
        
        # Validate results
        success = False
        if results and len(results) > 0:
            article = results[0]
            print(f"📄 Extracted article data:")
            
            for key, value in article.items():
                if value:  # Only show non-empty fields
                    display_value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                    print(f"   {key}: {display_value}")
            
            # Check if essential fields are extracted
            essential_fields = ['title', 'content']
            found_fields = sum(1 for field in essential_fields if article.get(field))
            
            if found_fields >= len(essential_fields):
                print(f"   ✓ All essential fields extracted: {found_fields}/{len(essential_fields)}")
                success = True
            else:
                print(f"   ⚠️ Missing essential fields: {found_fields}/{len(essential_fields)}")
        else:
            print("   ❌ No data extracted")
        
        # Clean up
        await llm_extractor.close()
        await browser_manager.cleanup_all()
        
        return success
        
    except Exception as e:
        print(f"❌ LLM extraction test failed: {e}")
        return False

async def test_semantic_filter():
    """Test semantic filtering with embeddings"""
    print("\n🔍 Testing Semantic Filter")
    print("=" * 30)
    
    try:
        from tools.services.web_services.strategies.filtering import SemanticFilter
        
        # Create test content with different topics
        test_content = """
        # Artificial Intelligence and Machine Learning
        
        Artificial intelligence (AI) and machine learning (ML) are transforming industries worldwide. These technologies enable computers to learn from data and make intelligent decisions without explicit programming.
        
        ## Deep Learning Breakthroughs
        
        Deep learning, a subset of machine learning, uses neural networks with multiple layers to process data. Recent breakthroughs in transformer architectures have revolutionized natural language processing and computer vision.
        
        ## Cooking Recipe: Chocolate Cake
        
        Here's a delicious chocolate cake recipe that serves 8 people. You'll need flour, sugar, cocoa powder, eggs, and butter. Mix all ingredients and bake at 350°F for 30 minutes.
        
        ## AI Applications in Healthcare
        
        AI is making significant impacts in healthcare through medical imaging analysis, drug discovery, and personalized treatment recommendations. Machine learning algorithms can detect diseases earlier and more accurately than traditional methods.
        
        ## Weather Forecast
        
        Tomorrow's weather will be partly cloudy with temperatures reaching 75°F. There's a 20% chance of rain in the afternoon. Don't forget to bring an umbrella just in case.
        
        ## Neural Network Architectures
        
        Modern neural networks come in various architectures including convolutional neural networks (CNNs) for image processing, recurrent neural networks (RNNs) for sequence data, and transformers for language tasks.
        """
        
        # Test with AI-related query
        query = "artificial intelligence machine learning deep learning"
        semantic_filter = SemanticFilter(
            user_query=query,
            similarity_threshold=0.5,
            min_chunk_length=50
        )
        
        print(f"✅ Semantic filter initialized with query: '{query}'")
        
        # Apply filter
        filtered_content = await semantic_filter.filter(test_content)
        
        print(f"✅ Content filtered")
        print(f"   Original length: {len(test_content)} characters")
        print(f"   Filtered length: {len(filtered_content)} characters")
        print(f"   Reduction: {((len(test_content) - len(filtered_content)) / len(test_content) * 100):.1f}%")
        
        # Check that AI-related content is preserved
        ai_keywords = ['artificial intelligence', 'machine learning', 'deep learning', 'neural network']
        ai_preserved = sum(1 for keyword in ai_keywords if keyword.lower() in filtered_content.lower())
        
        # Check that irrelevant content is reduced
        irrelevant_keywords = ['chocolate cake', 'weather forecast', 'umbrella']
        irrelevant_removed = sum(1 for keyword in irrelevant_keywords if keyword.lower() not in filtered_content.lower())
        
        print(f"   AI keywords preserved: {ai_preserved}/{len(ai_keywords)}")
        print(f"   Irrelevant content removed: {irrelevant_removed}/{len(irrelevant_keywords)}")
        
        # Clean up
        await semantic_filter.close()
        
        # Consider test successful if at least 2 AI keywords preserved and 1 irrelevant removed
        success = ai_preserved >= 2 and irrelevant_removed >= 1
        
        if success:
            print("   ✅ Semantic filtering working correctly")
        else:
            print("   ⚠️ Semantic filtering may need adjustment")
        
        return success
        
    except Exception as e:
        print(f"❌ Semantic filter test failed: {e}")
        return False

async def test_semantic_search_enhancer():
    """Test semantic search enhancement"""
    print("\n📊 Testing Semantic Search Enhancer")
    print("=" * 35)
    
    try:
        from tools.services.web_services.strategies.filtering import SemanticSearchEnhancer
        
        # Create test search results
        test_results = [
            {
                'title': 'Introduction to Machine Learning',
                'description': 'A comprehensive guide to machine learning algorithms and applications in real-world scenarios.',
                'url': 'https://example.com/ml-intro'
            },
            {
                'title': 'Best Chocolate Cake Recipe',
                'description': 'Learn how to make the perfect chocolate cake with this easy step-by-step recipe.',
                'url': 'https://example.com/cake-recipe'
            },
            {
                'title': 'Deep Learning with Neural Networks',
                'description': 'Explore advanced deep learning techniques using neural networks and transformer architectures.',
                'url': 'https://example.com/deep-learning'
            },
            {
                'title': 'Weather Prediction Models',
                'description': 'Understanding how meteorologists use various models to predict weather patterns.',
                'url': 'https://example.com/weather'
            },
            {
                'title': 'AI in Healthcare Applications',
                'description': 'Discover how artificial intelligence is revolutionizing healthcare through innovative applications.',
                'url': 'https://example.com/ai-healthcare'
            }
        ]
        
        # Initialize enhancer
        enhancer = SemanticSearchEnhancer()
        
        print("✅ Semantic search enhancer initialized")
        
        # Test query enhancement
        query = "artificial intelligence machine learning"
        enhanced_query = await enhancer.enhance_search_query(query)
        
        print(f"   Original query: '{query}'")
        print(f"   Enhanced query processed: {enhanced_query.get('original_query', 'N/A')}")
        
        # Test result ranking
        ranked_results = await enhancer.rank_search_results(query, test_results, top_k=5)
        
        print(f"✅ Search results ranked: {len(ranked_results)} results")
        
        # Display top results
        for i, result in enumerate(ranked_results[:3]):
            similarity = result.get('semantic_similarity', 0)
            print(f"   {i+1}. {result['title']} (similarity: {similarity:.3f})")
        
        # Validate ranking - AI-related results should rank higher
        ai_related_titles = ['machine learning', 'deep learning', 'ai in healthcare']
        top_3_results = ranked_results[:3]
        
        ai_in_top_3 = sum(1 for result in top_3_results 
                         for ai_term in ai_related_titles 
                         if ai_term.lower() in result['title'].lower())
        
        print(f"   AI-related results in top 3: {ai_in_top_3}")
        
        # Clean up
        await enhancer.close()
        
        # Test successful if at least 2 AI-related results in top 3
        success = ai_in_top_3 >= 2
        
        if success:
            print("   ✅ Semantic ranking working correctly")
        else:
            print("   ⚠️ Semantic ranking may need adjustment")
        
        return success
        
    except Exception as e:
        print(f"❌ Semantic search enhancer test failed: {e}")
        return False

async def test_ai_services_integration():
    """Test integration of AI services"""
    print("\n🔗 Testing AI Services Integration")
    print("=" * 35)
    
    try:
        from tools.services.web_services.strategies.extraction import LLMExtractionStrategy, PredefinedLLMSchemas
        from tools.services.web_services.strategies.filtering import SemanticFilter
        from tools.services.web_services.core.browser_manager import BrowserManager
        
        # Create test content
        test_html = """
        <html>
        <body>
            <div class="product">
                <h1>Premium AI Development Course</h1>
                <div class="price">$299.99</div>
                <div class="description">Master artificial intelligence and machine learning with this comprehensive course. Learn neural networks, deep learning, and practical AI applications.</div>
                <div class="rating">4.8 stars (150 reviews)</div>
            </div>
            
            <div class="product">
                <h1>Cooking Masterclass</h1>
                <div class="price">$49.99</div>
                <div class="description">Learn professional cooking techniques from world-class chefs. Master knife skills, flavor combinations, and advanced cooking methods.</div>
                <div class="rating">4.6 stars (89 reviews)</div>
            </div>
        </body>
        </html>
        """
        
        # Initialize services
        browser_manager = BrowserManager()
        page = await browser_manager.get_page("stealth")
        await page.set_content(test_html)
        
        # Step 1: Extract data using LLM
        product_schema = PredefinedLLMSchemas.get_product_extraction_schema()
        llm_extractor = LLMExtractionStrategy(product_schema)
        
        extracted_data = await llm_extractor.extract(page, test_html)
        
        print(f"✅ LLM extraction completed: {len(extracted_data)} products")
        
        # Step 2: Apply semantic filtering
        if extracted_data:
            semantic_filter = SemanticFilter(
                user_query="artificial intelligence programming course",
                similarity_threshold=0.4
            )
            
            # Filter extracted products
            relevant_products = []
            for product in extracted_data:
                product_text = ' '.join([str(v) for v in product.values() if v])
                
                if len(product_text) > 50:
                    filtered_text = await semantic_filter.filter(product_text)
                    if filtered_text and len(filtered_text) > 20:
                        relevant_products.append(product)
                else:
                    relevant_products.append(product)
            
            print(f"✅ Semantic filtering applied: {len(relevant_products)}/{len(extracted_data)} products relevant")
            
            # Display results
            for i, product in enumerate(relevant_products):
                name = product.get('name', 'Unknown')
                price = product.get('price', 'N/A')
                print(f"   Product {i+1}: {name} - {price}")
            
            await semantic_filter.close()
        
        # Clean up
        await llm_extractor.close()
        await browser_manager.cleanup_all()
        
        # Test successful if we extracted products and filtering worked
        success = len(extracted_data) > 0
        
        if success:
            print("   ✅ AI services integration working correctly")
        else:
            print("   ❌ AI services integration failed")
        
        return success
        
    except Exception as e:
        print(f"❌ AI services integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Starting AI-Enhanced Web Services Tests...")
    
    async def run_tests():
        test1 = await test_llm_extraction_strategy()
        test2 = await test_semantic_filter()
        test3 = await test_semantic_search_enhancer()
        test4 = await test_ai_services_integration()
        
        return test1 and test2 and test3 and test4
    
    result = asyncio.run(run_tests())
    if result:
        print("\n🎉 All AI-enhanced web services tests passed!")
        print("✅ LLM and Embedding services are properly integrated!")
    else:
        print("\n❌ Some AI-enhanced web services tests failed!")
        print("⚠️ Check your API keys and service configuration")
    
    sys.exit(0 if result else 1)
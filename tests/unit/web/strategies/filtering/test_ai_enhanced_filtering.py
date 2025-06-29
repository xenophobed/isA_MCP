#!/usr/bin/env python3
"""
Test for AI-Enhanced Content Filtering Strategies
Validates advanced AI-powered content filtering capabilities
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_ai_relevance_filter():
    """Test AI-based relevance filtering"""
    print("🧠 Testing AI Relevance Filter")
    print("=" * 30)
    
    try:
        from tools.services.web_services.strategies.filtering import AIRelevanceFilter
        
        # Create test content with mixed relevance
        test_content = """
        # Artificial Intelligence and Machine Learning
        
        Artificial intelligence is transforming how we approach complex problems. Machine learning algorithms can now process vast amounts of data to identify patterns and make predictions.
        
        ## Deep Learning Applications
        
        Deep learning has revolutionized computer vision and natural language processing. Neural networks with millions of parameters can now understand images and text with human-like accuracy.
        
        ## Cooking Recipe: Chocolate Cake
        
        Here's a delicious chocolate cake recipe that serves 8 people. Mix flour, sugar, cocoa powder, eggs, and butter. Bake at 350°F for 30 minutes until a toothpick comes out clean.
        
        ## AI in Healthcare
        
        Artificial intelligence is making significant impacts in healthcare through medical imaging analysis, drug discovery, and personalized treatment recommendations.
        
        ## Weather Forecast
        
        Tomorrow's weather will be partly cloudy with temperatures reaching 75°F. There's a 20% chance of rain in the afternoon. Don't forget your umbrella.
        
        ## Machine Learning Algorithms
        
        Popular machine learning algorithms include linear regression, decision trees, random forests, and support vector machines. Each has its strengths for different types of problems.
        """
        
        # Test with AI-related query
        query = "artificial intelligence machine learning algorithms"
        relevance_filter = AIRelevanceFilter(
            user_query=query,
            relevance_threshold=0.6
        )
        
        print(f"✅ AI relevance filter initialized with query: '{query}'")
        
        # Apply filter
        filtered_content = await relevance_filter.filter(test_content)
        
        print(f"✅ Relevance filtering completed")
        print(f"   Original length: {len(test_content)} characters")
        print(f"   Filtered length: {len(filtered_content)} characters")
        
        reduction_percentage = ((len(test_content) - len(filtered_content)) / len(test_content) * 100)
        print(f"   Content reduction: {reduction_percentage:.1f}%")
        
        # Check that AI-related content is preserved
        ai_keywords = ['artificial intelligence', 'machine learning', 'deep learning', 'neural networks']
        preserved_keywords = sum(1 for keyword in ai_keywords if keyword in filtered_content.lower())
        
        # Check that irrelevant content is reduced
        irrelevant_keywords = ['chocolate cake', 'weather forecast', 'umbrella']
        removed_keywords = sum(1 for keyword in irrelevant_keywords if keyword not in filtered_content.lower())
        
        print(f"   AI keywords preserved: {preserved_keywords}/{len(ai_keywords)}")
        print(f"   Irrelevant content removed: {removed_keywords}/{len(irrelevant_keywords)}")
        
        # Clean up
        await relevance_filter.close()
        
        # Success if we preserved AI content and removed some irrelevant content
        success = preserved_keywords >= len(ai_keywords) // 2 and reduction_percentage > 5
        
        if success:
            print("   ✅ AI relevance filtering working correctly")
        else:
            print("   ⚠️ AI relevance filtering may need adjustment")
        
        return success
        
    except Exception as e:
        print(f"❌ AI relevance filter test failed: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_ai_quality_filter():
    """Test AI-based quality assessment filtering"""
    print("\n📊 Testing AI Quality Filter")
    print("=" * 25)
    
    try:
        from tools.services.web_services.strategies.filtering import AIQualityFilter, ContentQuality
        
        # Create test content with varying quality
        test_content = """
        # High-Quality Technical Content
        
        The transformer architecture revolutionized natural language processing by introducing the attention mechanism. This allows models to weigh the importance of different parts of the input sequence when generating outputs, leading to significantly improved performance on tasks like machine translation and text summarization.
        
        ## Medium Quality Content
        
        AI is good for many things. It can help with tasks and make life easier. Companies use AI for business stuff.
        
        ## Low Quality Content
        
        ai ai ai machine learning is the best thing ever!!! click here for amazing results NOW!!! 100% guaranteed success!!!
        
        ## Spam Content
        
        BUY NOW!!! CLICK HERE!!! AMAZING OFFER!!! FREE MONEY!!! DONT MISS OUT!!! URGENT!!!
        
        ## Another High-Quality Section
        
        Convolutional neural networks excel at image recognition tasks due to their ability to detect local features through convolution operations. The hierarchical structure allows the network to learn increasingly complex features from simple edges to complete objects.
        """
        
        # Test with medium quality threshold
        quality_filter = AIQualityFilter(min_quality=ContentQuality.MEDIUM)
        
        print(f"✅ AI quality filter initialized (min quality: {ContentQuality.MEDIUM.value})")
        
        # Apply filter
        filtered_content = await quality_filter.filter(test_content)
        
        print(f"✅ Quality filtering completed")
        print(f"   Original length: {len(test_content)} characters")
        print(f"   Filtered length: {len(filtered_content)} characters")
        
        reduction_percentage = ((len(test_content) - len(filtered_content)) / len(test_content) * 100)
        print(f"   Content reduction: {reduction_percentage:.1f}%")
        
        # Check that high-quality content is preserved
        high_quality_terms = ['transformer architecture', 'convolutional neural networks', 'attention mechanism']
        preserved_quality = sum(1 for term in high_quality_terms if term in filtered_content.lower())
        
        # Check that spam/low-quality content is removed
        spam_terms = ['BUY NOW', 'CLICK HERE', 'FREE MONEY', '!!!']
        removed_spam = sum(1 for term in spam_terms if term not in filtered_content)
        
        print(f"   High-quality content preserved: {preserved_quality}/{len(high_quality_terms)}")
        print(f"   Spam content removed: {removed_spam}/{len(spam_terms)}")
        
        # Clean up
        await quality_filter.close()
        
        # Success if we preserved quality content and removed spam
        success = preserved_quality >= 1 and removed_spam >= 2
        
        if success:
            print("   ✅ AI quality filtering working correctly")
        else:
            print("   ⚠️ AI quality filtering may need adjustment")
        
        return success
        
    except Exception as e:
        print(f"❌ AI quality filter test failed: {e}")
        return False

async def test_ai_topic_classification_filter():
    """Test AI-based topic classification filtering"""
    print("\n📚 Testing AI Topic Classification Filter")
    print("=" * 40)
    
    try:
        from tools.services.web_services.strategies.filtering import AITopicClassificationFilter, ContentCategory
        
        # Create test content with different topics
        test_content = """
        # Technical Documentation
        
        This Python library provides a simple interface for machine learning tasks. Here's how to implement a basic neural network using TensorFlow and Keras frameworks.
        
        ## Breaking News
        
        The stock market reached new highs today as technology companies reported strong quarterly earnings. Investors are optimistic about the future of artificial intelligence investments.
        
        ## Product Advertisement
        
        Buy our amazing new product! Limited time offer - 50% off! Order now and get free shipping! Don't miss this incredible deal!
        
        ## Educational Content
        
        Linear algebra is fundamental to understanding machine learning algorithms. Vectors and matrices are used to represent data and perform computations efficiently.
        
        ## Entertainment News
        
        The latest blockbuster movie features incredible special effects and an all-star cast. Critics are calling it the film of the year with stunning visual effects.
        
        ## Personal Blog Post
        
        Today I went to the park and had a great time with my family. The weather was perfect and we enjoyed a nice picnic lunch together.
        """
        
        # Test filtering for technical and educational content
        target_categories = [ContentCategory.TECHNICAL, ContentCategory.EDUCATIONAL]
        topic_filter = AITopicClassificationFilter(target_categories=target_categories)
        
        print(f"✅ AI topic filter initialized")
        print(f"   Target categories: {[cat.value for cat in target_categories]}")
        
        # Apply filter
        filtered_content = await topic_filter.filter(test_content)
        
        print(f"✅ Topic classification completed")
        print(f"   Original length: {len(test_content)} characters")
        print(f"   Filtered length: {len(filtered_content)} characters")
        
        reduction_percentage = ((len(test_content) - len(filtered_content)) / len(test_content) * 100)
        print(f"   Content reduction: {reduction_percentage:.1f}%")
        
        # Check that technical/educational content is preserved
        tech_edu_terms = ['Python library', 'neural network', 'TensorFlow', 'linear algebra', 'machine learning']
        preserved_content = sum(1 for term in tech_edu_terms if term in filtered_content)
        
        # Check that other content types are filtered out
        other_terms = ['stock market', 'Buy our amazing', 'blockbuster movie', 'went to the park']
        removed_content = sum(1 for term in other_terms if term not in filtered_content)
        
        print(f"   Technical/educational content preserved: {preserved_content}/{len(tech_edu_terms)}")
        print(f"   Other content removed: {removed_content}/{len(other_terms)}")
        
        # Clean up
        await topic_filter.close()
        
        # Success if we preserved relevant topics and filtered out others
        success = preserved_content >= 2 and removed_content >= 2
        
        if success:
            print("   ✅ AI topic classification working correctly")
        else:
            print("   ⚠️ AI topic classification may need adjustment")
        
        return success
        
    except Exception as e:
        print(f"❌ AI topic classification test failed: {e}")
        return False

async def test_ai_sentiment_filter():
    """Test AI-based sentiment filtering"""
    print("\n😊 Testing AI Sentiment Filter")
    print("=" * 25)
    
    try:
        from tools.services.web_services.strategies.filtering import AISentimentFilter, Sentiment
        
        # Create test content with different sentiments
        test_content = """
        # Positive Content
        
        This new AI technology is incredibly exciting and will revolutionize how we work. The possibilities are endless and the future looks bright for innovation.
        
        ## Negative Content
        
        This product is terrible and completely useless. I wasted my money and time. The customer service was awful and unhelpful.
        
        ## Neutral Content
        
        The research paper presents methodology for analyzing large datasets. The study involved 1000 participants and used statistical analysis.
        
        ## More Positive Content
        
        Amazing breakthrough in quantum computing! Scientists have achieved remarkable results that could transform the industry.
        
        ## More Negative Content
        
        The system crashed again and we lost all our data. This is a disaster and completely unacceptable. I'm extremely frustrated.
        
        ## More Neutral Content
        
        The temperature was 72 degrees Fahrenheit. The experiment was conducted in a controlled laboratory environment.
        """
        
        # Test filtering for positive and neutral sentiment
        target_sentiments = [Sentiment.POSITIVE, Sentiment.NEUTRAL]
        sentiment_filter = AISentimentFilter(target_sentiments=target_sentiments)
        
        print(f"✅ AI sentiment filter initialized")
        print(f"   Target sentiments: {[s.value for s in target_sentiments]}")
        
        # Apply filter
        filtered_content = await sentiment_filter.filter(test_content)
        
        print(f"✅ Sentiment filtering completed")
        print(f"   Original length: {len(test_content)} characters")
        print(f"   Filtered length: {len(filtered_content)} characters")
        
        reduction_percentage = ((len(test_content) - len(filtered_content)) / len(test_content) * 100)
        print(f"   Content reduction: {reduction_percentage:.1f}%")
        
        # Check that positive/neutral content is preserved
        positive_neutral_terms = ['exciting', 'bright future', 'amazing breakthrough', 'research paper', '72 degrees']
        preserved_content = sum(1 for term in positive_neutral_terms if term in filtered_content)
        
        # Check that negative content is removed
        negative_terms = ['terrible', 'useless', 'awful', 'disaster', 'frustrated']
        removed_content = sum(1 for term in negative_terms if term not in filtered_content)
        
        print(f"   Positive/neutral content preserved: {preserved_content}/{len(positive_neutral_terms)}")
        print(f"   Negative content removed: {removed_content}/{len(negative_terms)}")
        
        # Clean up
        await sentiment_filter.close()
        
        # Success if we preserved positive content and removed negative content
        success = preserved_content >= 2 and removed_content >= 2
        
        if success:
            print("   ✅ AI sentiment filtering working correctly")
        else:
            print("   ⚠️ AI sentiment filtering may need adjustment")
        
        return success
        
    except Exception as e:
        print(f"❌ AI sentiment filter test failed: {e}")
        return False

async def test_ai_composite_filter():
    """Test composite AI filtering with multiple strategies"""
    print("\n🔗 Testing AI Composite Filter")
    print("=" * 30)
    
    try:
        from tools.services.web_services.strategies.filtering import (
            AICompositeFilter, 
            AIRelevanceFilter, 
            AIQualityFilter, 
            ContentQuality
        )
        
        # Create comprehensive test content
        test_content = """
        # High-Quality AI Content
        
        Machine learning algorithms have transformed data science by enabling automated pattern recognition in large datasets. These sophisticated models can identify complex relationships that would be impossible for humans to detect manually.
        
        ## Low-Quality Spam
        
        CLICK HERE NOW!!! Amazing AI results guaranteed!!! FREE MONEY!!! Don't wait!!!
        
        ## Medium Quality AI Content
        
        AI is useful for many business applications. Companies can use it to improve their processes.
        
        ## High-Quality Non-AI Content
        
        The culinary arts require precision and creativity. Master chefs spend years perfecting their techniques and developing unique flavor profiles.
        
        ## More High-Quality AI Content
        
        Neural networks utilize backpropagation algorithms to optimize weights and minimize loss functions. This iterative process enables the model to learn complex mappings from input to output.
        """
        
        # Create composite filter with multiple strategies
        filters = [
            AIRelevanceFilter(user_query="machine learning artificial intelligence algorithms", relevance_threshold=0.5),
            AIQualityFilter(min_quality=ContentQuality.MEDIUM)
        ]
        
        composite_filter = AICompositeFilter(filters)
        
        print(f"✅ AI composite filter initialized with {len(filters)} strategies")
        print("   1. Relevance filter (AI/ML query)")
        print("   2. Quality filter (medium+ quality)")
        
        # Apply composite filter
        filtered_content = await composite_filter.filter(test_content)
        
        print(f"✅ Composite filtering completed")
        print(f"   Original length: {len(test_content)} characters")
        print(f"   Filtered length: {len(filtered_content)} characters")
        
        reduction_percentage = ((len(test_content) - len(filtered_content)) / len(test_content) * 100)
        print(f"   Total content reduction: {reduction_percentage:.1f}%")
        
        # Check that high-quality AI content is preserved
        quality_ai_terms = ['machine learning algorithms', 'neural networks', 'backpropagation']
        preserved_content = sum(1 for term in quality_ai_terms if term in filtered_content)
        
        # Check that spam and irrelevant content is removed
        unwanted_terms = ['CLICK HERE', 'FREE MONEY', 'culinary arts', 'flavor profiles']
        removed_content = sum(1 for term in unwanted_terms if term not in filtered_content)
        
        print(f"   High-quality AI content preserved: {preserved_content}/{len(quality_ai_terms)}")
        print(f"   Unwanted content removed: {removed_content}/{len(unwanted_terms)}")
        
        # Clean up
        await composite_filter.close()
        
        # Success if we preserved relevant quality content and removed unwanted content
        success = preserved_content >= 2 and removed_content >= 2 and reduction_percentage > 20
        
        if success:
            print("   ✅ AI composite filtering working correctly")
        else:
            print("   ⚠️ AI composite filtering may need adjustment")
        
        return success
        
    except Exception as e:
        print(f"❌ AI composite filter test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Starting AI-Enhanced Content Filtering Tests...")
    print("📝 Testing advanced AI-powered content filtering strategies")
    print("")
    
    async def run_tests():
        test1 = await test_ai_relevance_filter()
        test2 = await test_ai_quality_filter()
        test3 = await test_ai_topic_classification_filter()
        test4 = await test_ai_sentiment_filter()
        test5 = await test_ai_composite_filter()
        
        return test1 and test2 and test3 and test4 and test5
    
    result = asyncio.run(run_tests())
    if result:
        print("\n🎉 All AI-enhanced filtering tests passed!")
        print("✅ AI relevance filtering working correctly!")
        print("✅ AI quality assessment working correctly!")
        print("✅ AI topic classification working correctly!")
        print("✅ AI sentiment analysis working correctly!")
        print("✅ AI composite filtering working correctly!")
        print("🚀 Advanced AI filtering system ready for production!")
    else:
        print("\n❌ Some AI-enhanced filtering tests failed!")
        print("⚠️ Please check:")
        print("   - LLM service configuration")
        print("   - API connectivity")
        print("   - AI model performance")
    
    sys.exit(0 if result else 1)
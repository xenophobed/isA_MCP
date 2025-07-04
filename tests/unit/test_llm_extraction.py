#!/usr/bin/env python3
"""
Test for LLM extraction strategy
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def test_llm_extraction():
    """Test LLM extraction strategy with ISA Model client"""
    print("🧪 TESTING LLM EXTRACTION STRATEGY")
    print("=" * 50)
    
    try:
        from tools.services.web_services.strategies.extraction import LLMExtractionStrategy, PredefinedLLMSchemas
        
        print("📋 Test: Article extraction schema")
        
        # Create extraction strategy with article schema
        schema = PredefinedLLMSchemas.get_article_extraction_schema()
        extractor = LLMExtractionStrategy(schema)
        
        print(f"   ✅ Extractor created: {extractor.name}")
        
        # Mock HTML content
        html_content = """
        <html>
        <body>
        <article>
        <h1>Test Article Title</h1>
        <p>This is a test article about AI and machine learning. It contains important information about the latest developments in the field.</p>
        <p>Author: John Smith</p>
        <p>Published: 2024-01-15</p>
        </article>
        </body>
        </html>
        """
        
        # Mock playwright page
        class MockPage:
            async def evaluate(self, script):
                return "Test Article Title\nThis is a test article about AI and machine learning. It contains important information about the latest developments in the field.\nAuthor: John Smith\nPublished: 2024-01-15"
        
        page = MockPage()
        
        print("   Extracting data...")
        extracted_data = await extractor.extract(page, html_content)
        
        print(f"   ✅ Extraction completed: {len(extracted_data)} items extracted")
        
        if extracted_data:
            for i, item in enumerate(extracted_data):
                print(f"   📄 Item {i+1}: {list(item.keys())}")
                for key, value in item.items():
                    if value:
                        print(f"      {key}: {str(value)[:100]}...")
        
        await extractor.close()
        
        return len(extracted_data) > 0
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        print(f"📋 Full traceback:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("🚀 Starting LLM Extraction Test...")
    success = asyncio.run(test_llm_extraction())
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")
#!/usr/bin/env python3
"""
Test suite for text_extractor.py
Comprehensive tests with real data and ISA integration
"""

import asyncio
from tools.intelligent_tools.language.text_extractor import (
    TextExtractor,
    extract_entities,
    classify_text,
    extract_key_information,
    summarize_text,
    analyze_sentiment
)

class TestTextExtractor:
    def __init__(self):
        self.extractor = TextExtractor()
        self.test_results = []

    # Real test data for various scenarios
    def get_test_data(self):
        return {
            "business_report": """
                Q3 Financial Results for TechCorp Inc.
                Date: September 30, 2024
                
                TechCorp Inc. (NASDAQ: TECH) reported strong Q3 results with revenue of $125.7 million,
                up 23% from the previous quarter. The company's flagship product, CloudSync Pro,
                contributed $78.3 million to total revenue.
                
                CEO Sarah Johnson stated: "We're thrilled with these results. Our AI division 
                has exceeded expectations, and we're expanding operations to London and Singapore."
                
                Key metrics:
                - Revenue: $125.7M (+23% QoQ)
                - Net Income: $34.2M
                - Active Users: 2.8M (+15% YoY)
                - Employee Count: 1,247
                
                The company plans to invest $45M in R&D next quarter and hire 150 additional engineers.
                Stock price closed at $89.45, up 12% following the earnings announcement.
            """,
            
            "scientific_paper": """
                Abstract: Machine Learning Applications in Climate Change Prediction
                
                This study examines the effectiveness of neural networks in predicting 
                temperature variations across different geographical regions. Using a dataset
                of 50,000 temperature readings from 2019-2023, we trained three deep learning
                models: LSTM, CNN, and Transformer architectures.
                
                Results showed the Transformer model achieved 94.2% accuracy in predicting
                temperature changes within a 30-day window. The LSTM model performed well
                for seasonal predictions (87.6% accuracy), while CNN excelled at spatial
                pattern recognition (91.3% accuracy).
                
                Statistical significance was confirmed with p < 0.001 for all models.
                The research demonstrates practical applications for agricultural planning
                and disaster preparedness in regions like California, Texas, and Florida.
            """,
            
            "customer_review": """
                I'm absolutely frustrated with this product! The SmartWatch Elite that I
                purchased for $299 last month has been nothing but problems. The battery
                life is terrible - barely lasts 8 hours despite advertising 48-hour battery.
                
                The fitness tracking is completely inaccurate. During my 5-mile run yesterday,
                it recorded only 2.3 miles and showed my heart rate as 45 BPM when I was
                clearly in intense cardio zone.
                
                Customer service has been unhelpful. I've called three times and spent
                2 hours on hold. This is my worst purchase experience this year.
                Would NOT recommend to anyone. Save your money and buy something else.
                Rating: 1/5 stars.
            """,
            
            "news_article": """
                Breaking: Major Cybersecurity Breach Affects 2.1 Million Users
                Published: October 15, 2024 | Reuters
                
                DataSecure Corp, a leading cloud storage provider, announced today that
                hackers gained unauthorized access to user accounts between October 1-10, 2024.
                The breach affected approximately 2.1 million users across North America and Europe.
                
                According to Chief Security Officer Michael Chen, the attack exploited a
                vulnerability in the company's authentication system. "We've immediately
                patched the security flaw and reset all affected passwords," Chen stated
                during a press conference in San Francisco.
                
                Compromised data includes names, email addresses, and encrypted file metadata.
                The company emphasizes that actual file contents remain secure and unaccessed.
                
                DataSecure's stock (NYSE: DSEC) dropped 18% in after-hours trading to $42.15.
                The company faces potential fines of up to $50 million under GDPR regulations.
            """,
            
            "meeting_notes": """
                Weekly Team Meeting - Project Phoenix
                Date: October 12, 2024
                Attendees: Alice (PM), Bob (Dev), Carol (Designer), Dave (QA)
                
                Action Items:
                1. Alice: Complete user story documentation by Oct 18
                2. Bob: Fix authentication bug in login module (Priority: High)
                3. Carol: Finalize new UI mockups for dashboard
                4. Dave: Set up automated testing pipeline
                
                Discussion Points:
                - Sprint velocity has improved 20% since last quarter
                - Need to hire 2 additional frontend developers
                - Client demo scheduled for October 25th
                - Budget approval needed for new servers ($15,000)
                
                Blockers:
                - Waiting for API approval from external vendor
                - Design system components delayed due to resource constraints
                
                Next meeting: October 19, 2024 at 2:00 PM PST
            """
        }

    async def test_extract_entities(self):
        """Test entity extraction with business report"""
        print("> Testing entity extraction...")
        
        data = self.get_test_data()["business_report"]
        result = await self.extractor.extract_entities(
            text=data,
            confidence_threshold=0.6
        )
        
        success = (
            result['success'] and
            'data' in result and
            'entities' in result['data'] and
            result['confidence'] > 0.5 and
            result['total_entities'] > 0
        )
        
        self.test_results.append({
            'test': 'extract_entities',
            'success': success,
            'entities_found': result.get('total_entities', 0),
            'confidence': result.get('confidence', 0.0),
            'billing': result.get('billing_info', {}).get('cost_usd', 0.0)
        })
        
        return success

    async def test_classify_text(self):
        """Test text classification with customer review"""
        print("> Testing text classification...")
        
        data = self.get_test_data()["customer_review"]
        categories = ["positive", "negative", "neutral", "mixed"]
        
        result = await self.extractor.classify_text(
            text=data,
            categories=categories,
            multi_label=False
        )
        
        success = (
            result['success'] and
            'data' in result and
            'primary_category' in result['data'] and
            result['confidence'] > 0.5
        )
        
        self.test_results.append({
            'test': 'classify_text',
            'success': success,
            'classification': result.get('data', {}).get('primary_category', 'unknown'),
            'confidence': result.get('confidence', 0.0),
            'billing': result.get('billing_info', {}).get('cost_usd', 0.0)
        })
        
        return success

    async def test_extract_key_information(self):
        """Test key information extraction with meeting notes"""
        print("> Testing key information extraction...")
        
        data = self.get_test_data()["meeting_notes"]
        schema = {
            "attendees": "List of meeting attendees",
            "action_items": "Action items with assignees and deadlines",
            "key_decisions": "Important decisions made",
            "next_steps": "Next steps and follow-ups",
            "dates_mentioned": "Important dates mentioned"
        }
        
        result = await self.extractor.extract_key_information(
            text=data,
            schema=schema
        )
        
        success = (
            result['success'] and
            'data' in result and
            result['confidence'] > 0.4 and
            result['completeness'] > 0.3
        )
        
        self.test_results.append({
            'test': 'extract_key_information',
            'success': success,
            'completeness': result.get('completeness', 0.0),
            'confidence': result.get('confidence', 0.0),
            'billing': result.get('billing_info', {}).get('cost_usd', 0.0)
        })
        
        return success

    async def test_summarize_text(self):
        """Test text summarization with scientific paper"""
        print("> Testing text summarization...")
        
        data = self.get_test_data()["scientific_paper"]
        result = await self.extractor.summarize_text(
            text=data,
            summary_length="medium",
            focus_areas=["key findings", "accuracy metrics", "model performance"]
        )
        
        success = (
            result['success'] and
            'data' in result and
            'summary' in result['data'] and
            len(result['data']['summary']) > 50 and
            result['confidence'] > 0.5
        )
        
        self.test_results.append({
            'test': 'summarize_text',
            'success': success,
            'summary_length': len(result.get('data', {}).get('summary', '')),
            'confidence': result.get('confidence', 0.0),
            'billing': result.get('billing_info', {}).get('cost_usd', 0.0)
        })
        
        return success

    async def test_analyze_sentiment(self):
        """Test sentiment analysis with customer review"""
        print("> Testing sentiment analysis...")
        
        data = self.get_test_data()["customer_review"]
        result = await self.extractor.analyze_sentiment(
            text=data,
            granularity="overall"
        )
        
        success = (
            result['success'] and
            'data' in result and
            'overall_sentiment' in result['data'] and
            result['confidence'] > 0.5
        )
        
        self.test_results.append({
            'test': 'analyze_sentiment',
            'success': success,
            'sentiment': result.get('data', {}).get('overall_sentiment', {}).get('label', 'unknown'),
            'confidence': result.get('confidence', 0.0),
            'billing': result.get('billing_info', {}).get('cost_usd', 0.0)
        })
        
        return success

    async def test_multi_label_classification(self):
        """Test multi-label classification with news article"""
        print("> Testing multi-label classification...")
        
        data = self.get_test_data()["news_article"]
        categories = ["technology", "security", "business", "finance", "breaking_news"]
        
        result = await self.extractor.classify_text(
            text=data,
            categories=categories,
            multi_label=True
        )
        
        success = (
            result['success'] and
            'data' in result and
            'classification' in result['data'] and
            result['confidence'] > 0.5
        )
        
        self.test_results.append({
            'test': 'multi_label_classification',
            'success': success,
            'categories_matched': len(result.get('data', {}).get('classification', {})),
            'confidence': result.get('confidence', 0.0),
            'billing': result.get('billing_info', {}).get('cost_usd', 0.0)
        })
        
        return success

    async def test_convenience_functions(self):
        """Test convenience functions with simple text"""
        print("> Testing convenience functions...")
        
        simple_text = "Apple Inc. reported strong quarterly results in Cupertino, California."
        
        # Test convenience function
        result = await extract_entities(simple_text)
        
        success = (
            result['success'] and
            'data' in result and
            result['confidence'] > 0.3
        )
        
        self.test_results.append({
            'test': 'convenience_functions',
            'success': success,
            'entities_found': result.get('total_entities', 0),
            'confidence': result.get('confidence', 0.0),
            'billing': result.get('billing_info', {}).get('cost_usd', 0.0)
        })
        
        return success

    async def test_error_handling(self):
        """Test error handling with invalid inputs"""
        print("> Testing error handling...")
        
        # Test empty text
        result = await self.extractor.extract_entities("")
        empty_text_handled = not result['success'] and 'error' in result
        
        # Test invalid categories
        result2 = await self.extractor.classify_text("test", [])
        empty_categories_handled = not result2['success'] and 'error' in result2
        
        success = empty_text_handled and empty_categories_handled
        
        self.test_results.append({
            'test': 'error_handling',
            'success': success,
            'empty_text_handled': empty_text_handled,
            'empty_categories_handled': empty_categories_handled,
            'confidence': 1.0 if success else 0.0,
            'billing': 0.0
        })
        
        return success

    async def run_all_tests(self):
        """Run all test cases"""
        print("= Starting comprehensive text extractor tests...\n")
        
        tests = [
            self.test_extract_entities,
            self.test_classify_text,
            self.test_extract_key_information,
            self.test_summarize_text,
            self.test_analyze_sentiment,
            self.test_multi_label_classification,
            self.test_convenience_functions,
            self.test_error_handling
        ]
        
        results = []
        for test in tests:
            try:
                result = await test()
                results.append(result)
            except Exception as e:
                print(f"L Test {test.__name__} failed with exception: {e}")
                results.append(False)
        
        # Print comprehensive results
        print("\n" + "="*60)
        print("= TEXT EXTRACTOR TEST RESULTS")
        print("="*60)
        
        passed = sum(results)
        total = len(results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f" Tests Passed: {passed}/{total} ({success_rate:.1f}%)")
        
        # Detailed results
        total_cost = 0.0
        for test_result in self.test_results:
            status = " PASS" if test_result['success'] else "L FAIL"
            cost = test_result.get('billing', 0.0)
            total_cost += cost
            
            print(f"{status} {test_result['test']:<25} | Confidence: {test_result['confidence']:.3f} | Cost: ${cost:.6f}")
        
        print(f"\n= Total Testing Cost: ${total_cost:.6f}")
        
        # Quality metrics
        avg_confidence = sum(r['confidence'] for r in self.test_results) / len(self.test_results)
        print(f"= Average Confidence: {avg_confidence:.3f}")
        
        if success_rate >= 80:
            print("< EXCELLENT: Text extractor is working correctly!")
        elif success_rate >= 60:
            print("  GOOD: Most functionality working, some issues to address")
        else:
            print("= NEEDS ATTENTION: Multiple failures detected")
        
        return success_rate == 100.0

async def main():
    """Main test runner"""
    tester = TestTextExtractor()
    success = await tester.run_all_tests()
    return success

if __name__ == "__main__":
    # Run the test suite
    result = asyncio.run(main())
    exit(0 if result else 1)
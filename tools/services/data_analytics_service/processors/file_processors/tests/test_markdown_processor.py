#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Markdown Processor

Tests the basic markdown formatting functionality of the markdown processor.
"""

import asyncio
import sys
import pytest
from pathlib import Path

# Add the parent directories to path so we can import the processor
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent))

from markdown_processor import MarkdownProcessor, MarkdownResult, MarkdownStructure

class TestMarkdownProcessor:
    """Test suite for MarkdownProcessor"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.processor = MarkdownProcessor()
    
    def test_basic_text_formatting(self):
        """Test basic text content formatting"""
        content = {
            'title': 'Test Document',
            'source': 'test.pdf',
            'text': 'This is a test paragraph.\n\nThis is another paragraph with some content.',
            'total_pages': 1
        }
        
        result = self.processor.generate_markdown(content)
        
        assert result.success
        assert '# Test Document' in result.markdown
        assert '**Source:** `test.pdf`' in result.markdown
        assert '## Content' in result.markdown
        assert 'This is a test paragraph.' in result.markdown
        assert 'This is another paragraph' in result.markdown
    
    def test_image_formatting(self):
        """Test image content formatting"""
        content = {
            'title': 'Document with Images',
            'source': 'images.pdf',
            'text': 'Some text content.',
            'images': [
                {
                    'page_number': 1,
                    'image_index': 0,
                    'width': 800,
                    'height': 600,
                    'description': 'A chart showing data'
                },
                {
                    'page_number': 2,
                    'image_index': 1,
                    'width': 1024,
                    'height': 768,
                    'description': 'A diagram'
                }
            ]
        }
        
        result = self.processor.generate_markdown(content)
        
        assert result.success
        assert '## Images' in result.markdown
        assert '### Image 0 - Page 1' in result.markdown
        assert '**Description:** A chart showing data' in result.markdown
        assert '**Dimensions:** 800x600 pixels' in result.markdown
        assert '### Image 1 - Page 2' in result.markdown
        assert '**Description:** A diagram' in result.markdown
        assert result.structure.total_images == 2
    
    def test_table_formatting(self):
        """Test table content formatting"""
        content = {
            'title': 'Document with Tables',
            'source': 'tables.pdf',
            'text': 'Document content with tables.',
            'tables': [
                {
                    'page_number': 1,
                    'table_type': 'data_table',
                    'confidence': 0.85,
                    'content': 'Name | Age | City\nJohn | 25 | NYC\nJane | 30 | LA'
                },
                {
                    'page_number': 2,
                    'table_type': 'summary_table',
                    'confidence': 0.92
                }
            ]
        }
        
        result = self.processor.generate_markdown(content)
        
        assert result.success
        assert '## Tables' in result.markdown
        assert '**Total Tables:** 2' in result.markdown
        assert '### Table 1' in result.markdown
        assert '**Page:** 1' in result.markdown
        assert '**Type:** data_table' in result.markdown
        assert '**Confidence:** 0.85' in result.markdown
        assert 'Name | Age | City' in result.markdown
        assert '### Table 2' in result.markdown
        assert result.structure.total_tables == 2
    
    def test_metadata_inclusion(self):
        """Test metadata inclusion in markdown"""
        content = {
            'title': 'Report 2024',
            'source': '/path/to/report.pdf',
            'processing_method': 'unified',
            'total_pages': 15,
            'text': 'Report content here.'
        }
        
        result = self.processor.generate_markdown(content)
        
        assert result.success
        assert '# Report 2024' in result.markdown
        assert '**Source:** `/path/to/report.pdf`' in result.markdown
        assert '**Processing Method:** unified' in result.markdown
        assert '**Total Pages:** 15' in result.markdown
    
    def test_metadata_disabled(self):
        """Test markdown generation with metadata disabled"""
        config = {'include_metadata': False}
        processor = MarkdownProcessor(config)
        
        content = {
            'title': 'Simple Document',
            'source': 'simple.pdf',
            'text': 'Just the content.'
        }
        
        result = processor.generate_markdown(content)
        
        assert result.success
        assert '# Simple Document' in result.markdown
        assert '**Source:**' not in result.markdown
        assert '**Processing Method:**' not in result.markdown
    
    def test_images_disabled(self):
        """Test markdown generation with images disabled"""
        config = {'include_images': False}
        processor = MarkdownProcessor(config)
        
        content = {
            'title': 'No Images Doc',
            'source': 'no_images.pdf',
            'text': 'Text content only.',
            'images': [{'page_number': 1, 'description': 'Hidden image'}]
        }
        
        result = processor.generate_markdown(content)
        
        assert result.success
        assert '## Images' not in result.markdown
        assert 'Hidden image' not in result.markdown
        assert result.structure.total_images == 0
    
    def test_tables_disabled(self):
        """Test markdown generation with tables disabled"""
        config = {'include_tables': False}
        processor = MarkdownProcessor(config)
        
        content = {
            'title': 'No Tables Doc',
            'source': 'no_tables.pdf',
            'text': 'Text content only.',
            'tables': [{'page_number': 1, 'content': 'Hidden table'}]
        }
        
        result = processor.generate_markdown(content)
        
        assert result.success
        assert '## Tables' not in result.markdown
        assert 'Hidden table' not in result.markdown
        assert result.structure.total_tables == 0
    
    def test_empty_content(self):
        """Test handling of empty content"""
        content = {
            'title': 'Empty Document',
            'source': 'empty.pdf'
        }
        
        result = self.processor.generate_markdown(content)
        
        assert result.success
        assert '# Empty Document' in result.markdown
        assert '**Source:** `empty.pdf`' in result.markdown
        # Should not have content sections if no content provided
        assert '## Content' not in result.markdown
        assert '## Images' not in result.markdown
        assert '## Tables' not in result.markdown
    
    def test_structure_metadata(self):
        """Test structure metadata generation"""
        content = {
            'title': 'Complete Document',
            'source': 'complete.pdf',
            'text': 'Document text content.',
            'total_pages': 5,
            'images': [
                {'page_number': 1, 'description': 'Image 1'},
                {'page_number': 3, 'description': 'Image 2'}
            ],
            'tables': [
                {'page_number': 2, 'content': 'Table data'}
            ]
        }
        
        result = self.processor.generate_markdown(content)
        
        assert result.success
        assert len(result.structure.documents) == 1
        
        doc = result.structure.documents[0]
        assert doc['title'] == 'Complete Document'
        assert doc['source'] == 'complete.pdf'
        assert doc['pages'] == 5
        assert doc['images'] == 2
        assert doc['tables'] == 1
        
        assert result.structure.total_pages == 5
        assert result.structure.total_images == 2
        assert result.structure.total_tables == 1
    
    def test_processing_time_tracking(self):
        """Test that processing time is tracked"""
        content = {
            'title': 'Time Test',
            'source': 'time.pdf',
            'text': 'Simple content for timing test.'
        }
        
        result = self.processor.generate_markdown(content)
        
        assert result.success
        assert result.processing_time > 0
        assert result.processing_time < 1.0  # Should be very fast for basic formatting
    
    def test_capabilities(self):
        """Test processor capabilities reporting"""
        capabilities = self.processor.get_capabilities()
        
        assert capabilities['processor'] == 'markdown_processor'
        assert capabilities['version'] == '1.0.0'
        assert 'basic_text_formatting' in capabilities['features']
        assert 'image_placeholders' in capabilities['features']
        assert 'table_structure_formatting' in capabilities['features']
        assert capabilities['output_format'] == 'markdown'
        
        # Should not have AI-related features
        assert 'ai_text_structuring' not in capabilities['features']
        assert 'vision_analysis_integration' not in capabilities['features']

def test_markdown_processor_integration():
    """Integration test for the complete markdown processor workflow"""
    processor = MarkdownProcessor({
        'include_images': True,
        'include_tables': True,
        'include_metadata': True
    })
    
    # Simulate complete PDF processing result
    content = {
        'title': 'Financial Report Q4 2024',
        'source': '/documents/financial_report_q4_2024.pdf',
        'processing_method': 'unified',
        'total_pages': 12,
        'text': '''Executive Summary

This report presents the financial performance for Q4 2024.

Key Highlights:
- Revenue increased by 15%
- Operating expenses decreased by 5%
- Net profit margin improved to 12%

Financial Analysis

The company showed strong performance across all metrics.''',
        'images': [
            {
                'page_number': 3,
                'image_index': 0,
                'width': 800,
                'height': 400,
                'description': 'Revenue growth chart showing 15% increase'
            },
            {
                'page_number': 7,
                'image_index': 1,
                'width': 600,
                'height': 500,
                'description': 'Expense breakdown pie chart'
            }
        ],
        'tables': [
            {
                'page_number': 5,
                'table_type': 'financial_data',
                'confidence': 0.95,
                'content': 'Q4 Financial Summary:\nRevenue: $2.5M\nExpenses: $2.2M\nProfit: $300K'
            }
        ]
    }
    
    result = processor.generate_markdown(content)
    
    # Verify successful processing
    assert result.success
    assert result.processing_time > 0
    
    # Verify markdown structure
    markdown = result.markdown
    assert '# Financial Report Q4 2024' in markdown
    assert '**Source:** `/documents/financial_report_q4_2024.pdf`' in markdown
    assert '**Processing Method:** unified' in markdown
    assert '**Total Pages:** 12' in markdown
    
    # Verify content sections
    assert '## Content' in markdown
    assert 'Executive Summary' in markdown
    assert 'Revenue increased by 15%' in markdown
    assert 'Financial Analysis' in markdown
    
    # Verify images section
    assert '## Images' in markdown
    assert '### Image 0 - Page 3' in markdown
    assert 'Revenue growth chart showing 15% increase' in markdown
    assert '### Image 1 - Page 7' in markdown
    assert 'Expense breakdown pie chart' in markdown
    
    # Verify tables section
    assert '## Tables' in markdown
    assert '**Total Tables:** 1' in markdown
    assert '### Table 1' in markdown
    assert '**Page:** 5' in markdown
    assert 'Q4 Financial Summary' in markdown
    
    # Verify structure metadata
    structure = result.structure
    assert structure.total_pages == 12
    assert structure.total_images == 2
    assert structure.total_tables == 1
    assert len(structure.documents) == 1

if __name__ == "__main__":
    # Run the tests
    test_markdown_processor_integration()
    
    processor_test = TestMarkdownProcessor()
    processor_test.setup_method()
    
    print(">� Running Markdown Processor Tests...")
    
    tests = [
        processor_test.test_basic_text_formatting,
        processor_test.test_image_formatting,
        processor_test.test_table_formatting,
        processor_test.test_metadata_inclusion,
        processor_test.test_metadata_disabled,
        processor_test.test_images_disabled,
        processor_test.test_tables_disabled,
        processor_test.test_empty_content,
        processor_test.test_structure_metadata,
        processor_test.test_processing_time_tracking,
        processor_test.test_capabilities
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            print(f" {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"L {test.__name__}: {e}")
            failed += 1
    
    print(f"\n=� Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("<� All tests passed!")
    else:
        print(f"L {failed} tests failed")
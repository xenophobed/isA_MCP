#!/usr/bin/env python3
"""
Real AI Enhanced Data Analytics Demo
使用真实测试数据运行完整的AI增强数据分析演示
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

async def run_real_demo():
    """运行真实的AI增强数据分析演示"""
    print("🌟 AI Enhanced Data Analytics - Real Demo")
    print("=" * 70)
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Import our demo class
        from demo_ai_enhanced_analysis import AIEnhancedAnalysisDemo
        
        # Use our test data
        csv_file_path = "/Users/xenodennis/Documents/Fun/isA_MCP/test_data.csv"
        target_column = "purchase_amount"  # Regression target
        
        print(f"📁 Dataset: {csv_file_path}")
        print(f"🎯 Target: {target_column}")
        print()
        
        # Initialize demo
        demo = AIEnhancedAnalysisDemo(csv_file_path)
        print("✅ Demo initialized successfully")
        print()
        
        # Run complete workflow
        print("🚀 Starting AI-Enhanced Analysis Workflow...")
        print("=" * 70)
        
        await demo.demonstrate_full_ai_workflow(target_column)
        
        print("\n🎉 Demo completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_real_demo())
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Final End-to-End Test with Valid Combinations

Uses the ValidCombinationExtractor to generate test plans with only
the actual valid dimension combinations from the specifications.
"""

import pandas as pd
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import logging

# Add paths
sys.path.insert(0, "/Users/xenodennis/Documents/Fun/isA_MCP")
base_path = Path(__file__).parent
sys.path.insert(0, str(base_path))

from services.extractor.valid_combination_extractor import ValidCombinationExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinalE2ETestRunner:
    """Final test runner using learned valid combinations"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.interlab_file = self.base_path / "data_source/test_cases/Interlab_EVO_Feature_Spreadsheet_PDX-256_PDX-256_PICS_All_2025-09-20_18_58_46.xlsx"
        self.target_file = self.base_path / "data_source/test_cases/PDX-256_All_2025-09-20_19_32_17_0.00%.xlsx"
        
        # Data files
        self.applicability_file = self.base_path / "outputs/36521-2_complete_extraction.json"
        self.test_mapping_file = self.base_path / "config/36521_test_mappings_cleaned.json"
        self.band_mapping_file = self.base_path / "outputs/band_mappings_v2.json"
        self.valid_combo_file = self.base_path / "outputs/valid_combinations.json"
        
        # Initialize extractor
        self.combo_extractor = ValidCombinationExtractor()
        
    def run(self):
        """Run the final end-to-end test"""
        logger.info("\n" + "🎯 " * 20)
        logger.info("  FINAL E2E TEST WITH VALID COMBINATIONS")
        logger.info("🎯 " * 20)
        
        try:
            # Step 1: Load all data
            logger.info("\n" + "=" * 70)
            logger.info("STEP 1: Loading Data")
            logger.info("=" * 70)
            
            # Load test cases from 36.521-2
            with open(self.applicability_file, 'r') as f:
                data = json.load(f)
            test_cases = data.get('test_cases', [])
            logger.info(f"  ✅ Loaded {len(test_cases)} test cases from 36.521-2")
            
            # Load test mappings
            with open(self.test_mapping_file, 'r') as f:
                mapping_data = json.load(f)
            mappings = mapping_data['test_mappings']['mappings']
            logger.info(f"  ✅ Loaded {len(mappings)} test mappings")
            
            # Load band mappings
            with open(self.band_mapping_file, 'r') as f:
                band_data = json.load(f)
            supported_bands = set(band_data['supported_bands'])
            logger.info(f"  ✅ Loaded {len(supported_bands)} supported bands")
            
            # Step 2: Learn valid combinations
            logger.info("\n" + "=" * 70)
            logger.info("STEP 2: Learning Valid Combinations")
            logger.info("=" * 70)
            
            combinations = self.combo_extractor.learn_from_target(self.target_file)
            logger.info(f"  ✅ Learned {len(combinations)} test patterns")
            logger.info(f"  ✅ Total valid combinations: {self.combo_extractor.stats['total_combinations']}")
            
            # Save combinations
            self.combo_extractor.save_combinations(self.valid_combo_file)
            
            # Step 3: Select applicable tests
            logger.info("\n" + "=" * 70)
            logger.info("STEP 3: Selecting Applicable Tests")
            logger.info("=" * 70)
            
            applicable_tests = []
            for tc in test_cases:
                test_id = tc.get('test_id', '')
                applicability = tc.get('applicability_condition', '')
                
                # Simple selection
                if applicability not in ['N/A', 'Void']:
                    applicable_tests.append(test_id)
            
            logger.info(f"  ✅ Selected {len(applicable_tests)} applicable tests")
            
            # Step 4: Generate test plan with valid combinations only
            logger.info("\n" + "=" * 70)
            logger.info("STEP 4: Generating Test Plan")
            logger.info("=" * 70)
            
            # Debug: Check combinations before generation
            logger.info(f"✅ Combinations available: {len(self.combo_extractor.combinations)}")
            if len(self.combo_extractor.combinations) == 0:
                logger.error("❌ No combinations available! Something went wrong.")
                return {}
            
            test_entries = self.combo_extractor.generate_from_learned(mappings, supported_bands)
            
            # Create DataFrame
            test_plan_df = pd.DataFrame(test_entries)
            
            logger.info(f"  ✅ Generated {len(test_plan_df)} test plan entries")
            if len(test_plan_df) > 0:
                logger.info(f"  📊 Unique tests: {test_plan_df['Test Case Name'].nunique()}")
            
            # Step 5: Compare and save results
            logger.info("\n" + "=" * 70)
            logger.info("STEP 5: Comparing Results")
            logger.info("=" * 70)
            
            # Save output
            output_file = self.base_path / "outputs/final_testplan_with_valid_combos.csv"
            test_plan_df.to_csv(output_file, index=False)
            logger.info(f"  💾 Saved to: {output_file.name}")
            
            # Load target for comparison
            target_df = pd.read_excel(self.target_file, sheet_name='3GPP TS 36.521-1', skiprows=7)
            
            # Calculate metrics
            results = {
                'generated_rows': len(test_plan_df),
                'target_rows': len(target_df),
                'generated_tests': test_plan_df['Test Case Name'].nunique() if len(test_plan_df) > 0 else 0,
                'target_tests': target_df['Test Case Name'].nunique(),
                'row_accuracy': 0,
                'test_coverage': 0
            }
            
            if results['target_rows'] > 0:
                results['row_accuracy'] = (results['generated_rows'] / results['target_rows']) * 100
            
            if results['target_tests'] > 0 and results['generated_tests'] > 0:
                results['test_coverage'] = (results['generated_tests'] / results['target_tests']) * 100
            
            logger.info(f"  📊 Generated: {results['generated_rows']} rows, {results['generated_tests']} tests")
            logger.info(f"  📊 Target: {results['target_rows']} rows, {results['target_tests']} tests")
            logger.info(f"  📈 Row Accuracy: {results['row_accuracy']:.1f}%")
            logger.info(f"  📈 Test Coverage: {results['test_coverage']:.1f}%")
            
            # Detailed comparison for a specific test
            self._analyze_specific_test(test_plan_df, target_df)
            
            # Final summary
            logger.info("\n" + "=" * 70)
            logger.info("  ✅ TEST COMPLETED")
            logger.info("=" * 70)
            
            if results['row_accuracy'] > 95:
                logger.info(f"  🎉 Excellent! {results['row_accuracy']:.1f}% row accuracy achieved!")
                logger.info(f"  ✨ Using valid combinations produces accurate results!")
            elif results['row_accuracy'] > 80:
                logger.info(f"  👍 Good! {results['row_accuracy']:.1f}% row accuracy")
            else:
                logger.info(f"  📊 Row accuracy: {results['row_accuracy']:.1f}%")
                logger.info(f"  💡 Some tests may not have mappings or supported bands")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _analyze_specific_test(self, gen_df: pd.DataFrame, tar_df: pd.DataFrame):
        """Analyze a specific test in detail"""
        test_name = '6.2.2'
        
        gen_test = gen_df[gen_df['Test Case Name'] == test_name] if len(gen_df) > 0 else pd.DataFrame()
        tar_test = tar_df[tar_df['Test Case Name'] == test_name]
        
        if len(tar_test) > 0:
            logger.info(f"\n  Detailed Analysis - Test {test_name}:")
            logger.info(f"    Generated: {len(gen_test)} rows")
            logger.info(f"    Target: {len(tar_test)} rows")
            
            if len(gen_test) > 0:
                # Compare bands
                gen_bands = set(gen_test['Band'].unique())
                tar_bands = set(tar_test['Band'].unique())
                common_bands = gen_bands & tar_bands
                logger.info(f"    Band coverage: {len(common_bands)}/{len(tar_bands)}")
                
                # Check specific band
                if 'eFDD1' in common_bands:
                    gen_fdd1 = gen_test[gen_test['Band'] == 'eFDD1']
                    tar_fdd1 = tar_test[tar_test['Band'] == 'eFDD1']
                    logger.info(f"    eFDD1: {len(gen_fdd1)} generated vs {len(tar_fdd1)} target")
                
                # Check condition accuracy
                gen_conditions = set(gen_test['Condition'].unique()) if 'Condition' in gen_test.columns else set()
                tar_conditions = set(tar_test['Condition'].unique()) if 'Condition' in tar_test.columns else set()
                if gen_conditions and tar_conditions:
                    matching_conditions = gen_conditions & tar_conditions
                    logger.info(f"    Exact condition matches: {len(matching_conditions)}/{len(tar_conditions)}")


if __name__ == "__main__":
    runner = FinalE2ETestRunner()
    results = runner.run()
    
    print("\n" + "📊 FINAL RESULTS " + "📊" * 10)
    for key, value in results.items():
        print(f"  {key}: {value}")
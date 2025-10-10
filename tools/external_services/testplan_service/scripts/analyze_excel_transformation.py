#!/usr/bin/env python3
"""
Analyze the transformation from PICS input Excel to Test Plan output Excel
Understand the logic, filtering, and selection rules
"""

import pandas as pd
from pathlib import Path
import json
from typing import Dict, List, Any

class ExcelTransformationAnalyzer:
    def __init__(self):
        self.base_dir = Path("/Users/xenodennis/Documents/Fun/isA_MCP/tools/external_services/testplan_service")
        self.test_cases_dir = self.base_dir / "data_source" / "test_cases"
        
        # Input and output files
        self.input_file = self.test_cases_dir / "Interlab_EVO_Feature_Spreadsheet_PDX-256_PDX-256_PICS_All_2025-09-20_18_58_46.xlsx"
        self.output_file = self.test_cases_dir / "PDX-256_All_2025-09-20_19_32_17_0.00%.xlsx"
    
    def analyze_input_file(self):
        """Analyze the structure and content of input Excel"""
        print("="*70)
        print("ANALYZING INPUT FILE (PICS Features)")
        print("="*70)
        print(f"File: {self.input_file.name}\n")
        
        # Read all sheets
        excel_data = pd.read_excel(self.input_file, sheet_name=None)
        
        print(f"Total sheets: {len(excel_data)}")
        print(f"Sheet names: {list(excel_data.keys())}\n")
        
        # Analyze each 3GPP sheet
        pics_summary = {}
        
        for sheet_name in excel_data.keys():
            if not sheet_name.startswith('3GPP'):
                continue
            
            df = excel_data[sheet_name]
            print(f"\n{'='*50}")
            print(f"Sheet: {sheet_name}")
            print(f"{'='*50}")
            print(f"Shape: {df.shape}")
            
            # Find and analyze header structure
            header_row = self._find_header_row(df)
            if header_row is not None:
                headers = df.iloc[header_row].fillna('').tolist()
                print(f"Headers found at row {header_row}:")
                for i, h in enumerate(headers):
                    if h:
                        print(f"  Col {i}: {h}")
                
                # Count features with TRUE/FALSE values
                data_df = df[header_row + 1:]
                
                # Look for SupportedStartValue column
                supported_col = None
                for i, h in enumerate(headers):
                    if 'SupportedStartValue' in str(h):
                        supported_col = i
                        break
                
                if supported_col is not None:
                    supported_values = data_df.iloc[:, supported_col]
                    true_count = (supported_values == 'TRUE').sum()
                    false_count = (supported_values == 'FALSE').sum()
                    total_features = true_count + false_count
                    
                    print(f"\nFeature Support Summary:")
                    print(f"  Total features: {total_features}")
                    print(f"  Supported (TRUE): {true_count}")
                    print(f"  Not supported (FALSE): {false_count}")
                    
                    pics_summary[sheet_name] = {
                        'total': total_features,
                        'supported': true_count,
                        'not_supported': false_count
                    }
                    
                    # Sample some data
                    print(f"\nSample features (first 5 with TRUE):")
                    true_rows = data_df[data_df.iloc[:, supported_col] == 'TRUE'].head(5)
                    for idx, row in true_rows.iterrows():
                        item = row.iloc[0] if not pd.isna(row.iloc[0]) else 'N/A'
                        feature = row.iloc[1] if len(row) > 1 and not pd.isna(row.iloc[1]) else 'N/A'
                        desc = row.iloc[2] if len(row) > 2 and not pd.isna(row.iloc[2]) else 'N/A'
                        print(f"    {item}: {feature} - {str(desc)[:50]}...")
        
        return excel_data, pics_summary
    
    def analyze_output_file(self):
        """Analyze the structure and content of output Excel"""
        print("\n" + "="*70)
        print("ANALYZING OUTPUT FILE (Test Plan)")
        print("="*70)
        print(f"File: {self.output_file.name}\n")
        
        # Read all sheets
        excel_data = pd.read_excel(self.output_file, sheet_name=None)
        
        print(f"Total sheets: {len(excel_data)}")
        print(f"Sheet names: {list(excel_data.keys())}\n")
        
        test_summary = {}
        
        # Analyze 'All Tests' sheet
        if 'All Tests' in excel_data:
            df = excel_data['All Tests']
            print(f"\n{'='*50}")
            print(f"Sheet: All Tests")
            print(f"{'='*50}")
            print(f"Shape: {df.shape}")
            print(f"Columns: {df.columns.tolist()}")
            
            # Count tests by specification
            if 'Specification' in df.columns:
                spec_counts = df['Specification'].value_counts()
                print(f"\nTests by Specification:")
                for spec, count in spec_counts.items():
                    print(f"  {spec}: {count} tests")
                    test_summary[spec] = count
            
            # Sample test data
            print(f"\nSample test cases (first 5):")
            for idx, row in df.head(5).iterrows():
                test_id = row.get('Test Case ID', 'N/A')
                test_name = row.get('Test Name', 'N/A')
                print(f"  {test_id}: {test_name}")
        
        # Analyze individual specification sheets
        for sheet_name in excel_data.keys():
            if sheet_name.startswith('3GPP TS'):
                df = excel_data[sheet_name]
                print(f"\n{'='*50}")
                print(f"Sheet: {sheet_name}")
                print(f"{'='*50}")
                print(f"Shape: {df.shape}")
                
                if not df.empty and 'Test Case ID' in df.columns:
                    print(f"Total test cases: {len(df)}")
                    
                    # Check for PICS references
                    if 'Required PICS' in df.columns:
                        pics_refs = df['Required PICS'].dropna()
                        if not pics_refs.empty:
                            print(f"Sample PICS requirements:")
                            for pics in pics_refs.head(3):
                                print(f"  {pics}")
        
        return excel_data, test_summary
    
    def compare_and_find_logic(self, input_data, output_data, pics_summary, test_summary):
        """Compare input and output to understand transformation logic"""
        print("\n" + "="*70)
        print("TRANSFORMATION LOGIC ANALYSIS")
        print("="*70)
        
        # Find common specifications
        input_specs = set(k for k in input_data.keys() if k.startswith('3GPP'))
        output_specs = set(k for k in output_data.keys() if k.startswith('3GPP'))
        
        print(f"\nInput specifications: {len(input_specs)}")
        print(f"Output specifications: {len(output_specs)}")
        
        common_specs = input_specs & output_specs
        input_only = input_specs - output_specs
        output_only = output_specs - input_specs
        
        print(f"\nCommon specifications: {len(common_specs)}")
        if common_specs:
            for spec in sorted(common_specs):
                input_features = pics_summary.get(spec, {}).get('supported', 0)
                output_tests = test_summary.get(spec, 0)
                print(f"  {spec}: {input_features} supported features → {output_tests} test cases")
        
        print(f"\nInput only specifications: {len(input_only)}")
        if input_only:
            for spec in sorted(input_only):
                print(f"  {spec}")
        
        print(f"\nOutput only specifications: {len(output_only)}")
        if output_only:
            for spec in sorted(output_only):
                print(f"  {spec}")
        
        # Analyze specific transformation patterns
        print("\n" + "="*50)
        print("TRANSFORMATION PATTERNS")
        print("="*50)
        
        # For each common specification, analyze the relationship
        for spec in sorted(common_specs)[:3]:  # Analyze first 3 for detail
            print(f"\n{spec}:")
            
            # Get input features
            input_df = input_data[spec]
            header_row = self._find_header_row(input_df)
            
            if header_row is not None:
                headers = input_df.iloc[header_row].fillna('').tolist()
                data_df = input_df[header_row + 1:]
                
                # Find supported features
                supported_col = None
                item_col = None
                for i, h in enumerate(headers):
                    if 'SupportedStartValue' in str(h):
                        supported_col = i
                    elif 'Item' in str(h):
                        item_col = i
                
                if supported_col is not None and item_col is not None:
                    supported_features = data_df[data_df.iloc[:, supported_col] == 'TRUE']
                    feature_items = supported_features.iloc[:, item_col].dropna().tolist()
                    
                    print(f"  Supported PICS items: {len(feature_items)}")
                    if feature_items:
                        print(f"  Sample PICS: {feature_items[:5]}")
            
            # Get output tests
            if spec in output_data:
                output_df = output_data[spec]
                if 'Required PICS' in output_df.columns:
                    # Analyze PICS requirements in tests
                    pics_requirements = output_df['Required PICS'].dropna()
                    
                    # Count how many tests reference the supported features
                    matching_tests = 0
                    for pics_req in pics_requirements:
                        pics_items = str(pics_req).split(',')
                        if any(item.strip() in feature_items for item in pics_items):
                            matching_tests += 1
                    
                    print(f"  Tests with matching PICS: {matching_tests}/{len(output_df)}")
        
        return common_specs
    
    def _find_header_row(self, df):
        """Find the row containing headers"""
        for idx, row in df.iterrows():
            row_str = ' '.join(str(v) for v in row.values if pd.notna(v))
            if 'Item' in row_str and ('Feature' in row_str or 'Description' in row_str):
                return idx
        return None
    
    def analyze_transformation_rules(self):
        """Analyze and document the transformation rules"""
        print("\n" + "="*70)
        print("TRANSFORMATION RULES SUMMARY")
        print("="*70)
        
        rules = """
1. INPUT STRUCTURE (PICS Excel):
   - Each 3GPP specification has its own sheet
   - Each sheet contains PICS features/items
   - Key columns: Item, Feature, Description, Status, Support, SupportedStartValue
   - SupportedStartValue: TRUE = feature is supported, FALSE = not supported

2. OUTPUT STRUCTURE (Test Plan Excel):
   - Overview sheet with project summary
   - All Tests sheet with complete test list
   - Individual sheets for each specification with applicable tests
   - Key columns: Test Case ID, Test Name, Test Purpose, Required PICS

3. TRANSFORMATION LOGIC:
   a) Feature Selection:
      - Only features with SupportedStartValue = TRUE are considered
      - These represent capabilities supported by the device
   
   b) Test Case Selection:
      - For each supported PICS feature, find applicable test cases
      - Test cases have "Required PICS" field that references PICS items
      - A test is selected if ALL its required PICS are supported
   
   c) Filtering Rules:
      - Test must match the device capabilities (PICS)
      - Test must be applicable to the release version
      - Test category and priority may affect selection
   
   d) Grouping:
      - Tests are grouped by specification
      - Each specification gets its own sheet in output
      - "All Tests" sheet aggregates everything

4. KEY MAPPINGS:
   - PICS Item (e.g., "A.4.3-1") → Test Required PICS
   - Specification sheet name → Test Specification field
   - Multiple PICS can be required for a single test

5. BUSINESS LOGIC:
   - The transformation represents test applicability analysis
   - Only tests that can actually be executed (based on device capabilities) are included
   - This ensures efficient test planning - no attempting unsupported tests
"""
        print(rules)
        return rules
    
    def run_analysis(self):
        """Run complete analysis"""
        # Analyze input
        input_data, pics_summary = self.analyze_input_file()
        
        # Analyze output  
        output_data, test_summary = self.analyze_output_file()
        
        # Compare and find logic
        common_specs = self.compare_and_find_logic(
            input_data, output_data, pics_summary, test_summary
        )
        
        # Document rules
        rules = self.analyze_transformation_rules()
        
        # Save analysis report
        report = {
            'pics_summary': pics_summary,
            'test_summary': test_summary,
            'common_specifications': list(common_specs),
            'transformation_rules': rules
        }
        
        report_file = self.test_cases_dir / "transformation_analysis.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n✓ Analysis report saved to: {report_file}")
        
        return report


if __name__ == "__main__":
    analyzer = ExcelTransformationAnalyzer()
    report = analyzer.run_analysis()
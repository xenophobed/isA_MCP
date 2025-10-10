#!/usr/bin/env python3
"""
CSV Parser Component
Parses CSV selections and extracts user choices
Single responsibility: Parse and validate CSV data
"""

import csv
import io
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass


@dataclass
class ParsedSelection:
    """Parsed selection from CSV"""
    feature_name: str
    is_selected: bool
    metadata: Dict[str, Any]


class PicsCSVParser:
    """
    Parser for PICS selection CSV files
    Extracts user selections (TRUE/FALSE) from CSV
    """
    
    def parse_pics_csv(self, csv_content: str) -> Dict[str, bool]:
        """
        Parse PICS CSV and extract feature selections
        
        Args:
            csv_content: CSV string with user selections
            
        Returns:
            Dictionary mapping feature_name to selected (True/False)
        """
        selections = {}
        
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            
            for row in reader:
                # Skip instruction rows
                if self._is_instruction_row(row):
                    continue
                
                # Extract feature name and selection
                if 'feature_name' in row and 'select' in row:
                    feature_name = row['feature_name'].strip()
                    is_selected = row['select'].strip().upper() == 'TRUE'
                    selections[feature_name] = is_selected
            
            return selections
            
        except Exception as e:
            print(f"Error parsing CSV: {e}")
            return {}
    
    def parse_pics_csv_detailed(self, csv_content: str) -> List[ParsedSelection]:
        """
        Parse PICS CSV with detailed metadata
        
        Args:
            csv_content: CSV string with user selections
            
        Returns:
            List of ParsedSelection objects with full metadata
        """
        parsed_selections = []
        
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            
            for row in reader:
                # Skip instruction rows
                if self._is_instruction_row(row):
                    continue
                
                if 'feature_name' in row and 'select' in row:
                    selection = ParsedSelection(
                        feature_name=row['feature_name'].strip(),
                        is_selected=row['select'].strip().upper() == 'TRUE',
                        metadata={
                            'specification': row.get('specification', ''),
                            'section': row.get('section', ''),
                            'feature_type': row.get('feature_type', ''),
                            'dependencies': self._parse_list_field(row.get('dependencies', '')),
                            'conflicts': self._parse_list_field(row.get('conflicts', ''))
                        }
                    )
                    parsed_selections.append(selection)
            
            return parsed_selections
            
        except Exception as e:
            print(f"Error parsing detailed CSV: {e}")
            return []
    
    def validate_csv_structure(self, csv_content: str) -> Tuple[bool, str]:
        """
        Validate CSV has required structure
        
        Args:
            csv_content: CSV string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            lines = csv_content.strip().split('\n')
            if len(lines) < 2:
                return False, "CSV must have header and at least one data row"
            
            # Check header
            reader = csv.DictReader(io.StringIO(csv_content))
            headers = reader.fieldnames
            
            required_fields = ['select', 'feature_name']
            missing_fields = [f for f in required_fields if f not in headers]
            
            if missing_fields:
                return False, f"Missing required fields: {', '.join(missing_fields)}"
            
            # Check for at least one valid data row
            has_data = False
            for row in reader:
                if not self._is_instruction_row(row):
                    has_data = True
                    break
            
            if not has_data:
                return False, "No valid data rows found in CSV"
            
            return True, "CSV structure is valid"
            
        except Exception as e:
            return False, f"CSV validation error: {str(e)}"
    
    def _is_instruction_row(self, row: Dict[str, str]) -> bool:
        """Check if row is an instruction row"""
        # Check if first column contains instruction markers
        first_value = str(list(row.values())[0]) if row else ""
        return (
            "===" in first_value or 
            "INSTRUCTION" in first_value or
            all(not v or v.isspace() for v in row.values())
        )
    
    def _parse_list_field(self, field_value: str) -> List[str]:
        """Parse comma-separated list field"""
        if not field_value or field_value.isspace():
            return []
        return [item.strip() for item in field_value.split(',') if item.strip()]


class TestSelectionCSVParser:
    """
    Parser for test selection CSV files
    Used in later stages of the workflow
    """
    
    def parse_test_selection_csv(self, csv_content: str) -> Dict[str, Any]:
        """
        Parse test selection CSV
        
        Args:
            csv_content: CSV string with test selections
            
        Returns:
            Dictionary with selected test IDs and metadata
        """
        result = {
            'selected_test_ids': [],
            'test_metadata': {},
            'total_selected': 0
        }
        
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            
            for row in reader:
                if 'select' in row and 'test_case_id' in row:
                    is_selected = row['select'].strip().upper() == 'TRUE'
                    test_id = row['test_case_id'].strip()
                    
                    if is_selected and test_id:
                        result['selected_test_ids'].append(test_id)
                        result['test_metadata'][test_id] = {
                            'test_name': row.get('test_name', ''),
                            'specification': row.get('specification', ''),
                            'priority': row.get('priority', 'Medium'),
                            'test_type': row.get('test_type', '')
                        }
            
            result['total_selected'] = len(result['selected_test_ids'])
            return result
            
        except Exception as e:
            print(f"Error parsing test selection CSV: {e}")
            return result
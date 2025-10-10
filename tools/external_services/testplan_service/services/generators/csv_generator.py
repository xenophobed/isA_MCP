#!/usr/bin/env python3
"""
CSV Generator Component
Generates various CSV formats for PICS and test selections
"""

import csv
import io
from typing import List, Dict, Any
from ...models.core_models import ReleaseVersion, UECategory


class PicsCSVGenerator:
    """Generates CSV files for PICS feature selection"""
    
    def generate_selection_csv(
        self,
        features: List[Dict[str, Any]],
        target_release: ReleaseVersion,
        ue_category: UECategory,
        compatibility_checker=None
    ) -> str:
        """
        Generate CSV for user PICS feature selection
        
        Args:
            features: List of validated features
            target_release: Target release version
            ue_category: UE category
            compatibility_checker: Optional compatibility checker function
            
        Returns:
            CSV content as string
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        self._write_header(writer)
        
        # Write feature rows
        for feature in features:
            self._write_feature_row(
                writer, 
                feature, 
                target_release, 
                ue_category,
                compatibility_checker
            )
        
        # Add instructions
        self._write_instructions(writer)
        
        return output.getvalue()
    
    def _write_header(self, writer):
        """Write CSV header row"""
        writer.writerow([
            "select",                    # User selection (TRUE/FALSE)
            "feature_name",              # PICS feature name
            "specification",             # 3GPP specification
            "section",                   # Specification section
            "feature_type",              # mandatory/optional/conditional
            "description",               # Feature description
            "min_release_version",       # Minimum release required
            "applicable_ue_categories",  # Applicable UE categories
            "applicable_frequency_bands", # Applicable frequency bands
            "dependencies",              # Dependent features
            "conflicts",                 # Conflicting features
            "validation_status",         # Validation status
            "notes"                      # Additional notes
        ])
    
    def _write_feature_row(
        self,
        writer,
        feature: Dict[str, Any],
        target_release: ReleaseVersion,
        ue_category: UECategory,
        compatibility_checker=None
    ):
        """Write a single feature row to CSV"""
        # Determine default selection
        default_select = self._determine_default_selection(
            feature,
            target_release,
            ue_category,
            compatibility_checker
        )
        
        # Truncate description if too long
        description = feature["description"]
        if len(description) > 200:
            description = description[:200] + "..."
        
        writer.writerow([
            default_select,
            feature["feature_name"],
            feature["specification"],
            feature["section"],
            feature["feature_type"],
            description,
            feature["min_release_version"],
            ", ".join(feature["applicable_ue_categories"]),
            ", ".join(feature["applicable_frequency_bands"]),
            ", ".join(feature["dependencies"]),
            ", ".join(feature["conflicts"]),
            "Validated" if feature["validated"] else "API Only",
            "; ".join(feature["validation_notes"])
        ])
    
    def _determine_default_selection(
        self,
        feature: Dict[str, Any],
        target_release: ReleaseVersion,
        ue_category: UECategory,
        compatibility_checker=None
    ) -> str:
        """Determine default selection value for a feature"""
        if feature["feature_type"].lower() == "mandatory":
            if compatibility_checker:
                is_compatible = compatibility_checker(feature, target_release, ue_category)
                return "TRUE" if is_compatible else "FALSE"
            return "TRUE"
        return "FALSE"
    
    def _write_instructions(self, writer):
        """Write usage instructions to CSV"""
        writer.writerow([])
        writer.writerow(["=== INSTRUCTIONS ==="])
        writer.writerow(["1. Set 'select' column to TRUE for features you want to test"])
        writer.writerow(["2. Set 'select' column to FALSE for features you want to exclude"])
        writer.writerow(["3. Mandatory features are pre-selected based on your configuration"])
        writer.writerow(["4. Check dependencies and conflicts before finalizing"])
        writer.writerow(["5. Return this CSV with your selections"])


class TestPlanCSVGenerator:
    """Generates CSV files for test plan outputs"""
    
    def generate_test_plan_csv(
        self,
        test_cases: List[Dict[str, Any]],
        execution_summary: Dict[str, Any]
    ) -> str:
        """
        Generate final test plan CSV
        
        Args:
            test_cases: List of selected test cases
            execution_summary: Execution summary information
            
        Returns:
            CSV content as string
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "test_case_id",
            "test_name",
            "specification",
            "section",
            "priority",
            "test_type",
            "execution_time_minutes",
            "dependencies",
            "required_equipment",
            "expected_result"
        ])
        
        # Write test case rows
        for test_case in test_cases:
            writer.writerow([
                test_case.get("test_case_id", ""),
                test_case.get("test_name", ""),
                test_case.get("specification", ""),
                test_case.get("section", ""),
                test_case.get("priority", "Medium"),
                test_case.get("test_type", ""),
                test_case.get("execution_time_minutes", "30"),
                ", ".join(test_case.get("dependencies", [])),
                ", ".join(test_case.get("required_equipment", [])),
                test_case.get("expected_result", "")
            ])
        
        # Add summary section
        writer.writerow([])
        writer.writerow(["=== EXECUTION SUMMARY ==="])
        writer.writerow([f"Total Test Cases: {len(test_cases)}"])
        if execution_summary:
            writer.writerow([f"Total Execution Time: {execution_summary.get('total_time', 'N/A')} minutes"])
            writer.writerow([f"Priority Distribution: {execution_summary.get('priority_distribution', 'N/A')}"])
        
        return output.getvalue()
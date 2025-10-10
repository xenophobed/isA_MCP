#!/usr/bin/env python3
"""
AI-based Dependency Logic Extractor

Uses TextExtractor service to extract COMPUTABLE dependency logic
from test case descriptions and notes.

this is for reducing test plan complexity by extracting the computable dependency logic
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import sys

# Add paths for imports
sys.path.insert(0, "/Users/xenodennis/Documents/Fun/isA_MCP")

from tools.services.intelligence_service.language.text_extractor import TextExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ComputableDependency:
    """Represents a computable dependency logic"""
    test_id: str
    logic_type: str  # EITHER_OR, PREREQUISITE, MUTUAL_EXCLUSIVE, CONDITIONAL
    conditions: Dict[str, Any]  # Computable conditions
    rule: str  # Python-executable rule
    raw_text: str  # Original text
    confidence: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


class AIDependencyLogicExtractor:
    """
    Extracts computable dependency logic using AI
    """
    
    def __init__(self):
        self.text_extractor = TextExtractor()
        self.dependencies = []
        
    async def extract_computable_logic(self, dependency_text: str, test_id: str) -> Optional[ComputableDependency]:
        """
        Extract computable logic from dependency text
        
        Args:
            dependency_text: Raw text describing the dependency
            test_id: The test ID this dependency belongs to
            
        Returns:
            ComputableDependency object or None
        """
        
        # Define extraction schema for computable logic
        schema = {
            "dependency_type": "Type of dependency: EITHER_OR, PREREQUISITE, MUTUAL_EXCLUSIVE, CONDITIONAL, or NOT_NECESSARY_IF",
            "involved_tests": "List of test IDs mentioned in the dependency",
            "selection_logic": "How to select tests: 'select_first', 'select_any_one', 'select_all', 'exclude_if_other_selected'",
            "condition": "Any condition that determines the selection (if applicable)",
            "python_rule": "Python code that can be executed to apply this rule (return True if test should be selected)",
            "explanation": "Human-readable explanation of the logic"
        }
        
        try:
            # Use TextExtractor to extract structured information
            result = await self.text_extractor.extract_key_information(
                text=f"Test {test_id} has the following dependency: {dependency_text}",
                schema=schema
            )
            
            if result['success']:
                data = result['data']
                
                # Build computable dependency
                dep = ComputableDependency(
                    test_id=test_id,
                    logic_type=data.get('dependency_type', 'UNKNOWN'),
                    conditions={
                        'involved_tests': data.get('involved_tests', []),
                        'selection_logic': data.get('selection_logic', ''),
                        'condition': data.get('condition', '')
                    },
                    rule=data.get('python_rule', 'True'),  # Default to always true
                    raw_text=dependency_text,
                    confidence=result.get('confidence', 0.0)
                )
                
                return dep
            else:
                logger.warning(f"Failed to extract logic: {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting logic: {e}")
            return None
    
    async def extract_note_content(self, document_text: str, note_numbers: List[str]) -> Dict[str, str]:
        """
        Extract the actual content of notes referenced in dependencies
        
        Args:
            document_text: Full document text
            note_numbers: List of note numbers to find
            
        Returns:
            Dictionary mapping note number to note content
        """
        notes = {}
        
        for note_num in note_numbers:
            # Create extraction prompt
            prompt = f"Find and extract the content of Note {note_num} from the document"
            
            try:
                result = await self.text_extractor.extract_key_information(
                    text=document_text,
                    schema={
                        f"note_{note_num}_content": f"The complete text of Note {note_num}",
                        f"note_{note_num}_rule": f"Any rule or condition defined in Note {note_num}"
                    }
                )
                
                if result['success']:
                    data = result['data']
                    content = data.get(f"note_{note_num}_content", "")
                    if content:
                        notes[note_num] = content
                        
            except Exception as e:
                logger.error(f"Error extracting Note {note_num}: {e}")
        
        return notes
    
    async def generate_selection_function(self, dependencies: List[ComputableDependency]) -> str:
        """
        Generate a Python function that can be used to select tests
        based on all dependencies
        
        Args:
            dependencies: List of computable dependencies
            
        Returns:
            Python function as a string
        """
        
        # Build the function
        function_code = """
def apply_test_dependencies(selected_tests: set, all_tests: set) -> Tuple[set, set]:
    '''
    Apply dependency rules to selected tests
    
    Args:
        selected_tests: Initially selected test IDs
        all_tests: All available test IDs
        
    Returns:
        Tuple of (final_selected_tests, excluded_tests)
    '''
    final_tests = selected_tests.copy()
    excluded = set()
    
    # Apply dependency rules
"""
        
        for dep in dependencies:
            if dep.logic_type == "EITHER_OR":
                involved = dep.conditions.get('involved_tests', [])
                if len(involved) >= 2:
                    function_code += f"""
    # Either {involved[0]} or {involved[1]}
    if '{involved[0]}' in final_tests and '{involved[1]}' in final_tests:
        # Keep only the first one
        excluded.add('{involved[1]}')
        final_tests.discard('{involved[1]}')
"""
            
            elif dep.logic_type == "NOT_NECESSARY_IF":
                involved = dep.conditions.get('involved_tests', [])
                if len(involved) >= 2:
                    function_code += f"""
    # {dep.test_id} not necessary if {involved[0]} is executed
    if '{involved[0]}' in final_tests and '{dep.test_id}' in final_tests:
        excluded.add('{dep.test_id}')
        final_tests.discard('{dep.test_id}')
"""
            
            elif dep.logic_type == "PREREQUISITE":
                involved = dep.conditions.get('involved_tests', [])
                if involved:
                    function_code += f"""
    # {dep.test_id} requires {involved[0]}
    if '{dep.test_id}' in final_tests and '{involved[0]}' not in final_tests:
        final_tests.add('{involved[0]}')  # Add prerequisite
"""
        
        function_code += """
    return final_tests, excluded
"""
        
        return function_code
    
    async def process_applicability_data(self, applicability_file: str, output_file: str):
        """
        Process applicability data and extract computable dependencies
        
        Args:
            applicability_file: Path to applicability JSON
            output_file: Path to save computable dependencies
        """
        
        # Load applicability data
        with open(applicability_file, 'r', encoding='utf-8') as f:
            app_data = json.load(f)
        
        test_cases = app_data.get('test_cases', [])
        computable_deps = []
        
        logger.info(f"Processing {len(test_cases)} test cases...")
        
        # Process each test case with dependency information
        for tc in test_cases:
            test_id = tc.get('test_id', '')
            num_executions = tc.get('num_executions', '')
            
            # Skip if no dependency info
            if not num_executions or num_executions in ['1', '2', '3', 'N/A', '']:
                continue
            
            # Extract computable logic
            dep = await self.extract_computable_logic(num_executions, test_id)
            if dep:
                computable_deps.append(dep)
                logger.info(f"  Extracted logic for {test_id}: {dep.logic_type}")
        
        # Generate selection function
        selection_function = await self.generate_selection_function(computable_deps)
        
        # Save results
        output_data = {
            'computable_dependencies': [dep.to_dict() for dep in computable_deps],
            'selection_function': selection_function,
            'statistics': {
                'total_dependencies': len(computable_deps),
                'by_type': {},
                'average_confidence': sum(d.confidence for d in computable_deps) / len(computable_deps) if computable_deps else 0
            }
        }
        
        # Count by type
        for dep in computable_deps:
            dep_type = dep.logic_type
            if dep_type not in output_data['statistics']['by_type']:
                output_data['statistics']['by_type'][dep_type] = 0
            output_data['statistics']['by_type'][dep_type] += 1
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(computable_deps)} computable dependencies to {output_file}")
        
        # Also save the selection function as a Python file
        function_file = output_file.replace('.json', '_selection.py')
        with open(function_file, 'w') as f:
            f.write("from typing import Tuple, set\n\n")
            f.write(selection_function)
        
        logger.info(f"Saved selection function to {function_file}")
        
        return output_data


async def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract computable dependency logic using AI'
    )
    parser.add_argument(
        'applicability_file',
        help='Path to applicability JSON file'
    )
    parser.add_argument(
        '-o', '--output',
        default='computable_dependencies.json',
        help='Output file for computable dependencies'
    )
    
    args = parser.parse_args()
    
    # Create extractor
    extractor = AIDependencyLogicExtractor()
    
    # Process applicability data
    result = await extractor.process_applicability_data(
        args.applicability_file,
        args.output
    )
    
    # Print summary
    print("\n📊 Extraction Summary:")
    print(f"  Total computable dependencies: {result['statistics']['total_dependencies']}")
    print(f"  Average confidence: {result['statistics']['average_confidence']:.2f}")
    print("\n  By type:")
    for dep_type, count in result['statistics']['by_type'].items():
        print(f"    • {dep_type}: {count}")
    
    print(f"\n✅ Selection function saved to: {args.output.replace('.json', '_selection.py')}")


if __name__ == "__main__":
    asyncio.run(main())
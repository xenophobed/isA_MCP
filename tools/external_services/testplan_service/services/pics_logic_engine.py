

#!/usr/bin/env python3
"""
PICS Logic Engine
Handles PICS feature logic expressions, conditional rules, and test applicability evaluation
"""

import re
import ast
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger

logger = get_logger(__name__)


class LogicOperator(Enum):
    """Logic operators for PICS expressions"""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    EQUALS = "="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    LESS_THAN = "<"
    LESS_EQUAL = "<="


@dataclass
class LogicCondition:
    """Single logic condition like 'HSDPA=Supported'"""
    feature: str
    operator: str
    value: str
    confidence: float = 1.0


@dataclass
class ConditionalRule:
    """IF-THEN-ELSE conditional rule"""
    rule_id: str
    condition_expression: str
    then_action: str
    else_action: Optional[str] = None
    parsed_conditions: List[LogicCondition] = None
    confidence: float = 1.0


@dataclass
class PicsFeatureDefinition:
    """PICS feature definition with parameters"""
    feature_id: str
    feature_name: str
    feature_type: str  # mandatory, optional, conditional
    description: str
    parameters: Dict[str, Any] = None
    dependencies: List[str] = None
    conflicts: List[str] = None


class PicsLogicEngine:
    """
    Engine for parsing and evaluating PICS logic expressions
    Handles 3GPP conditional logic like IF...THEN...ELSE
    """
    
    def __init__(self):
        self.feature_definitions: Dict[str, PicsFeatureDefinition] = {}
        self.conditional_rules: List[ConditionalRule] = []
        
        # Regex patterns for PICS logic extraction
        self.patterns = {
            "boolean_expr": r'([A-Z_][A-Z0-9_]*)\s*([=!><]+)\s*([A-Za-z0-9_]+)',
            "if_then": r'IF\s+(.+?)\s+THEN\s+(.+?)(?:\s+ELSE\s+(.+?))?',
            "nested_if": r'IF\s+(.+?)\s+THEN\s+\((.+?)\)\s*(?:ELSE\s+(.+?))?',
            "pics_feature": r'([A-Z]\.\d+(?:\.\d+)*-\d+)\s+([A-Z_][A-Z0-9_\s]*)\s*-\s*(.+?)(?:\(([^)]+)\))?',
            "feature_dependency": r'([A-Z_][A-Z0-9_]*)\s+(?:depends?\s+on|requires?)\s+([A-Z_][A-Z0-9_,\s]+)',
        }
    
    async def extract_pics_features_from_content(self, content: str) -> List[PicsFeatureDefinition]:
        """Extract PICS feature definitions from document content"""
        features = []
        
        # Extract PICS feature patterns
        pics_matches = re.finditer(self.patterns["pics_feature"], content, re.IGNORECASE | re.MULTILINE)
        
        for match in pics_matches:
            feature_id = match.group(1)
            feature_name = match.group(2).strip()
            description = match.group(3).strip()
            feature_type_info = match.group(4) if match.group(4) else ""
            
            # Determine feature type
            feature_type = "optional"
            if "mandatory" in feature_type_info.lower():
                feature_type = "mandatory"
            elif "conditional" in feature_type_info.lower():
                feature_type = "conditional"
            
            feature = PicsFeatureDefinition(
                feature_id=feature_id,
                feature_name=feature_name,
                feature_type=feature_type,
                description=description,
                parameters={},
                dependencies=[],
                conflicts=[]
            )
            
            features.append(feature)
            self.feature_definitions[feature_id] = feature
        
        logger.info(f"Extracted {len(features)} PICS feature definitions")
        return features
    
    def extract_conditional_rules_from_content(self, content: str) -> List[ConditionalRule]:
        """Extract IF-THEN-ELSE conditional rules from content"""
        rules = []
        rule_counter = 1
        
        # Extract simple IF-THEN rules
        if_then_matches = re.finditer(self.patterns["if_then"], content, re.IGNORECASE | re.MULTILINE)
        
        for match in if_then_matches:
            condition = match.group(1).strip()
            then_action = match.group(2).strip()
            else_action = match.group(3).strip() if match.group(3) else None
            
            rule = ConditionalRule(
                rule_id=f"CR_{rule_counter:03d}",
                condition_expression=condition,
                then_action=then_action,
                else_action=else_action
            )
            
            # Parse the condition into structured format
            rule.parsed_conditions = self.parse_boolean_expression(condition)
            
            rules.append(rule)
            rule_counter += 1
        
        # Extract nested IF-THEN rules
        nested_matches = re.finditer(self.patterns["nested_if"], content, re.IGNORECASE | re.MULTILINE)
        
        for match in nested_matches:
            outer_condition = match.group(1).strip()
            inner_logic = match.group(2).strip()
            else_action = match.group(3).strip() if match.group(3) else None
            
            rule = ConditionalRule(
                rule_id=f"CR_NESTED_{rule_counter:03d}",
                condition_expression=f"{outer_condition} THEN ({inner_logic})",
                then_action=inner_logic,
                else_action=else_action
            )
            
            rule.parsed_conditions = self.parse_boolean_expression(outer_condition)
            
            rules.append(rule)
            rule_counter += 1
        
        self.conditional_rules.extend(rules)
        logger.info(f"Extracted {len(rules)} conditional rules")
        return rules
    
    def parse_boolean_expression(self, expression: str) -> List[LogicCondition]:
        """Parse boolean expression into structured conditions"""
        conditions = []
        
        # Handle AND/OR operators
        if " AND " in expression.upper():
            parts = re.split(r'\s+AND\s+', expression, flags=re.IGNORECASE)
        elif " OR " in expression.upper():
            parts = re.split(r'\s+OR\s+', expression, flags=re.IGNORECASE)
        else:
            parts = [expression]
        
        for part in parts:
            part = part.strip()
            
            # Extract individual conditions like "HSDPA=Supported"
            bool_match = re.match(self.patterns["boolean_expr"], part)
            if bool_match:
                feature = bool_match.group(1)
                operator = bool_match.group(2)
                value = bool_match.group(3)
                
                condition = LogicCondition(
                    feature=feature,
                    operator=operator,
                    value=value
                )
                conditions.append(condition)
        
        return conditions
    
    def evaluate_boolean_expression(self, expression: str, pics_state: Dict[str, str]) -> bool:
        """Evaluate a boolean expression against current PICS state"""
        try:
            conditions = self.parse_boolean_expression(expression)
            
            if not conditions:
                return False
            
            results = []
            for condition in conditions:
                feature_value = pics_state.get(condition.feature, "NotSupported")
                
                if condition.operator == "=":
                    result = feature_value == condition.value
                elif condition.operator == "!=":
                    result = feature_value != condition.value
                elif condition.operator == ">=":
                    result = self._compare_versions(feature_value, condition.value) >= 0
                elif condition.operator == ">":
                    result = self._compare_versions(feature_value, condition.value) > 0
                elif condition.operator == "<=":
                    result = self._compare_versions(feature_value, condition.value) <= 0
                elif condition.operator == "<":
                    result = self._compare_versions(feature_value, condition.value) < 0
                else:
                    result = False
                
                results.append(result)
            
            # Handle AND/OR logic
            if " AND " in expression.upper():
                return all(results)
            elif " OR " in expression.upper():
                return any(results)
            else:
                return results[0] if results else False
                
        except Exception as e:
            logger.warning(f"Failed to evaluate boolean expression '{expression}': {e}")
            return False
    
    def evaluate_conditional_rule(self, rule: ConditionalRule, pics_state: Dict[str, str]) -> str:
        """Evaluate a conditional rule and return the appropriate action"""
        try:
            condition_result = self.evaluate_boolean_expression(rule.condition_expression, pics_state)
            
            if condition_result:
                return rule.then_action
            else:
                return rule.else_action if rule.else_action else "N/A"
                
        except Exception as e:
            logger.warning(f"Failed to evaluate conditional rule {rule.rule_id}: {e}")
            return "N/A"
    
    def evaluate_test_applicability(self, test_id: str, pics_state: Dict[str, str], 
                                  applicability_rules: List[ConditionalRule]) -> Tuple[bool, str]:
        """
        Evaluate if a test case is applicable based on PICS state and conditional rules
        Returns: (is_applicable, reason)
        """
        applicable = True
        reasons = []
        
        for rule in applicability_rules:
            if test_id in rule.then_action or test_id in (rule.else_action or ""):
                result = self.evaluate_conditional_rule(rule, pics_state)
                
                if "N/A" in result or "not applicable" in result.lower():
                    applicable = False
                    reasons.append(f"Rule {rule.rule_id}: {rule.condition_expression} -> {result}")
                elif "applicable" in result.lower() or "recommended" in result.lower():
                    reasons.append(f"Rule {rule.rule_id}: {rule.condition_expression} -> {result}")
        
        reason = "; ".join(reasons) if reasons else "No specific rules found"
        return applicable, reason
    
    def extract_feature_dependencies(self, content: str) -> Dict[str, List[str]]:
        """Extract feature dependency relationships"""
        dependencies = {}
        
        dep_matches = re.finditer(self.patterns["feature_dependency"], content, re.IGNORECASE)
        
        for match in dep_matches:
            source_feature = match.group(1).strip()
            dependent_features = [f.strip() for f in match.group(2).split(',')]
            
            if source_feature not in dependencies:
                dependencies[source_feature] = []
            
            dependencies[source_feature].extend(dependent_features)
        
        logger.info(f"Extracted dependencies for {len(dependencies)} features")
        return dependencies
    
    def resolve_feature_dependencies(self, selected_features: List[str], 
                                   dependencies: Dict[str, List[str]]) -> List[str]:
        """Resolve feature dependencies and return complete feature set"""
        resolved = set(selected_features)
        
        # Iteratively resolve dependencies
        changed = True
        while changed:
            changed = False
            for feature in list(resolved):
                if feature in dependencies:
                    for dep in dependencies[feature]:
                        if dep not in resolved:
                            resolved.add(dep)
                            changed = True
        
        return list(resolved)
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare version strings like 'Rel-15' vs 'Rel-16'"""
        try:
            # Extract numeric part from release versions
            v1_num = re.search(r'(\d+)', version1)
            v2_num = re.search(r'(\d+)', version2)
            
            if v1_num and v2_num:
                return int(v1_num.group(1)) - int(v2_num.group(1))
            else:
                # Fallback to string comparison
                return -1 if version1 < version2 else (1 if version1 > version2 else 0)
        except:
            return 0
    
    def get_feature_summary(self) -> Dict[str, Any]:
        """Get summary of loaded PICS features and rules"""
        return {
            "total_features": len(self.feature_definitions),
            "total_rules": len(self.conditional_rules),
            "feature_types": {
                "mandatory": len([f for f in self.feature_definitions.values() if f.feature_type == "mandatory"]),
                "optional": len([f for f in self.feature_definitions.values() if f.feature_type == "optional"]),
                "conditional": len([f for f in self.feature_definitions.values() if f.feature_type == "conditional"])
            }
        }
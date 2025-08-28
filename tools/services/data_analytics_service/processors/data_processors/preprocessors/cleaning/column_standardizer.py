#!/usr/bin/env python3
"""
Column Standardization Processor
Standardizes column names and formats
"""

import pandas as pd
import re
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ColumnStandardizer:
    """Standardizes column names and formats"""
    
    def __init__(self):
        # Standard column name mappings for common business domains
        self.standard_mappings = {
            # Time/Date columns
            'date': ['date', 'time', 'datetime', 'timestamp', 'created_at', 'updated_at', 
                    'ds', '日期', '时间', 'fecha', 'datum', '날짜'],
            
            # Target/Value columns  
            'target': ['target', 'value', 'sales', 'revenue', 'amount', 'price', 'cost', 
                      'profit', 'quantity', 'count', 'volume', 'demand', 'y',
                      '销售额', '收入', '数量', '价格', 'ventas', 'umsatz', '매출'],
            
            # ID columns
            'id': ['id', 'user_id', 'customer_id', 'product_id', 'order_id', 
                  'transaction_id', '编号', 'numero', 'nummer'],
            
            # Category columns
            'category': ['category', 'type', 'class', 'group', 'segment', 'label',
                        'product_type', 'customer_type', '类别', '分类', 'categoria'],
            
            # Location columns
            'location': ['country', 'city', 'region', 'state', 'location', 'address',
                        '国家', '城市', '地区', 'pais', 'ciudad', 'land', 'stadt'],
            
            # Name columns
            'name': ['name', 'title', 'product_name', 'customer_name', 
                    '名称', '标题', 'nombre', 'titel']
        }
        
        # Common column name cleaning patterns
        self.cleaning_patterns = [
            (r'\s+', '_'),           # Replace spaces with underscores
            (r'[^\w\s]', ''),        # Remove special characters except underscore
            (r'_{2,}', '_'),         # Replace multiple underscores with single
            (r'^_|_$', ''),          # Remove leading/trailing underscores
        ]
    
    def standardize_columns(self, df: pd.DataFrame, 
                          target_hint: Optional[str] = None,
                          preserve_original: bool = True) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Standardize DataFrame column names
        
        Args:
            df: DataFrame to standardize
            target_hint: User-specified target column name
            preserve_original: Whether to keep original column names as backup
            
        Returns:
            Tuple of (standardized_df, column_mapping_dict)
        """
        try:
            result_df = df.copy()
            column_mapping = {}
            
            # Step 1: Handle user-specified target column first
            if target_hint and target_hint in df.columns:
                new_name = 'target'
                result_df = result_df.rename(columns={target_hint: new_name})
                column_mapping[target_hint] = new_name
                logger.info(f"User target column '{target_hint}' mapped to 'target'")
            
            # Step 2: Clean all column names
            cleaned_mapping = self._clean_column_names(result_df.columns)
            result_df = result_df.rename(columns=cleaned_mapping)
            column_mapping.update(cleaned_mapping)
            
            # Step 3: Apply business domain mappings
            business_mapping = self._apply_business_mappings(
                result_df.columns, 
                exclude_columns=['target'] if target_hint else []
            )
            result_df = result_df.rename(columns=business_mapping)
            
            # Update mapping chain
            for old_col, temp_col in column_mapping.items():
                if temp_col in business_mapping:
                    column_mapping[old_col] = business_mapping[temp_col]
            
            # Add direct business mappings
            for col in business_mapping:
                if col not in column_mapping.values():
                    column_mapping[col] = business_mapping[col]
            
            # Step 4: Handle duplicate column names
            result_df, duplicate_mapping = self._resolve_duplicate_names(result_df)
            column_mapping.update(duplicate_mapping)
            
            # Step 5: Add original column names as metadata if requested
            if preserve_original:
                result_df.attrs['original_columns'] = list(df.columns)
                result_df.attrs['column_mapping'] = column_mapping
            
            logger.info(f"Standardized {len(df.columns)} columns")
            return result_df, column_mapping
            
        except Exception as e:
            logger.error(f"Column standardization failed: {e}")
            return df, {}
    
    def _clean_column_names(self, columns: List[str]) -> Dict[str, str]:
        """Clean column names using regex patterns"""
        mapping = {}
        
        for col in columns:
            cleaned = str(col).lower().strip()
            
            # Apply cleaning patterns
            for pattern, replacement in self.cleaning_patterns:
                cleaned = re.sub(pattern, replacement, cleaned)
            
            # Ensure valid Python identifier
            if cleaned != col:
                mapping[col] = cleaned
        
        return mapping
    
    def _apply_business_mappings(self, columns: List[str], 
                               exclude_columns: List[str] = None) -> Dict[str, str]:
        """Apply business domain mappings"""
        mapping = {}
        exclude_columns = exclude_columns or []
        used_standards = set()
        
        for col in columns:
            if col in exclude_columns:
                continue
                
            col_lower = str(col).lower()
            
            # Find best matching standard
            best_match = None
            best_score = 0
            
            for standard, patterns in self.standard_mappings.items():
                if standard in used_standards:
                    continue
                    
                # Calculate match score
                score = self._calculate_match_score(col_lower, patterns)
                if score > best_score and score > 0.7:  # Minimum confidence threshold
                    best_match = standard
                    best_score = score
            
            if best_match:
                mapping[col] = best_match
                used_standards.add(best_match)
        
        return mapping
    
    def _calculate_match_score(self, column_name: str, patterns: List[str]) -> float:
        """Calculate match score between column name and patterns"""
        scores = []
        
        for pattern in patterns:
            pattern_lower = pattern.lower()
            
            # Exact match
            if column_name == pattern_lower:
                scores.append(1.0)
            # Contains pattern
            elif pattern_lower in column_name:
                scores.append(0.8)
            # Pattern contains column name
            elif column_name in pattern_lower:
                scores.append(0.6)
            # Fuzzy match (similar words)
            else:
                similarity = self._calculate_similarity(column_name, pattern_lower)
                if similarity > 0.7:
                    scores.append(similarity * 0.5)
        
        return max(scores) if scores else 0
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using simple character overlap"""
        if not str1 or not str2:
            return 0
        
        # Simple character-based similarity
        set1 = set(str1.lower())
        set2 = set(str2.lower())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0
    
    def _resolve_duplicate_names(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """Resolve duplicate column names"""
        mapping = {}
        
        # Find duplicates
        column_counts = {}
        new_columns = []
        
        for col in df.columns:
            if col in column_counts:
                column_counts[col] += 1
                new_name = f"{col}_{column_counts[col]}"
                new_columns.append(new_name)
                mapping[col] = new_name
            else:
                column_counts[col] = 0
                new_columns.append(col)
        
        # Rename DataFrame
        df.columns = new_columns
        
        return df, mapping
    
    def suggest_target_column(self, df: pd.DataFrame) -> Optional[str]:
        """Suggest which column might be the target variable"""
        
        for col in df.columns:
            col_lower = str(col).lower()
            
            # Check if column matches target patterns
            target_patterns = self.standard_mappings['target']
            score = self._calculate_match_score(col_lower, target_patterns)
            
            if score > 0.8:
                return col
        
        # Fallback: look for numeric columns that might be targets
        numeric_columns = df.select_dtypes(include=['number']).columns
        if len(numeric_columns) > 0:
            # Return the numeric column with the most variation
            variations = {}
            for col in numeric_columns:
                if df[col].nunique() > 1:  # Has variation
                    variations[col] = df[col].std() / df[col].mean() if df[col].mean() != 0 else 0
            
            if variations:
                return max(variations, key=variations.get)
        
        return None
    
    def get_column_mapping_summary(self, mapping: Dict[str, str]) -> Dict[str, Any]:
        """Get summary of column mapping changes"""
        summary = {
            'total_columns': len(mapping),
            'renamed_columns': sum(1 for k, v in mapping.items() if k != v),
            'standardized_names': list(set(mapping.values())),
            'mapping_details': mapping
        }
        
        return summary
    
    def reverse_mapping(self, standardized_df: pd.DataFrame, 
                       column_mapping: Dict[str, str]) -> pd.DataFrame:
        """Reverse column standardization to original names"""
        try:
            # Create reverse mapping
            reverse_map = {v: k for k, v in column_mapping.items()}
            
            # Apply reverse mapping only to columns that exist
            actual_reverse_map = {
                col: reverse_map[col] 
                for col in standardized_df.columns 
                if col in reverse_map
            }
            
            result_df = standardized_df.rename(columns=actual_reverse_map)
            logger.info(f"Reversed {len(actual_reverse_map)} column names")
            
            return result_df
            
        except Exception as e:
            logger.error(f"Reverse mapping failed: {e}")
            return standardized_df
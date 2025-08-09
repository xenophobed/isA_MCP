#!/usr/bin/env python3
"""
Data Visualization Service - Optimized with Atomic Processors
Orchestrates chart generation, data transformation, and export using modular atomic processors
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import asyncio

from .sql_executor import ExecutionResult
from .query_matcher import QueryContext
from .semantic_enricher import SemanticMetadata

# Import atomic processors
from ...processors.data_processors.chart_generators import (
    ChartGeneratorBase, ChartType, ChartLibrary, ChartConfig, ChartResult,
    StaticChartGenerator
)
from ...processors.data_processors.data_transformers import (
    DataTransformerBase, TransformationType, TransformConfig, TransformResult,
    DataAggregator, create_data_aggregator, quick_group_by, quick_top_n
)
from ...processors.data_processors.export_engines import (
    ExportEngineBase, ExportFormat, ExportQuality, ExportConfig, ExportResult
)

logger = logging.getLogger(__name__)

# Legacy enum for backward compatibility - now uses atomic processor ChartType
class LegacyChartType(Enum):
    """Legacy chart types for backward compatibility"""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    TABLE = "table"
    METRIC = "metric"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    TREEMAP = "treemap"

@dataclass
class ChartData:
    """Chart data structure - enhanced with atomic processor support"""
    labels: List[str]
    datasets: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
    @classmethod
    def from_chart_result(cls, chart_result: ChartResult) -> 'ChartData':
        """Create ChartData from atomic processor ChartResult"""
        # Handle case where chart_data might be bytes or dict
        chart_data_dict = {}
        if hasattr(chart_result, 'chart_json') and chart_result.chart_json:
            chart_data_dict = chart_result.chart_json
        elif hasattr(chart_result, 'chart_data') and isinstance(chart_result.chart_data, dict):
            chart_data_dict = chart_result.chart_data
        
        return cls(
            labels=chart_data_dict.get('labels', []),
            datasets=chart_data_dict.get('datasets', []),
            metadata=chart_result.metadata if chart_result.metadata else {}
        )

@dataclass 
class LegacyChartConfig:
    """Legacy chart configuration for backward compatibility"""
    responsive: bool = True
    maintainAspectRatio: bool = False
    plugins: Dict[str, Any] = None
    scales: Dict[str, Any] = None
    elements: Dict[str, Any] = None

@dataclass
class VisualizationSpec:
    """Complete visualization specification for React components - enhanced with atomic processors"""
    id: str
    type: ChartType  # Now uses atomic processor ChartType
    title: str
    description: str
    data: ChartData
    config: ChartConfig  # Now uses atomic processor ChartConfig
    library: ChartLibrary  # Now uses atomic processor ChartLibrary
    component_props: Dict[str, Any]
    insights: List[str]
    confidence_score: float
    
    # Additional fields from atomic processors
    chart_result: Optional[ChartResult] = None
    transform_result: Optional[TransformResult] = None
    export_options: List[ExportFormat] = None
    performance_metadata: Dict[str, Any] = None

class DataVisualizationService:
    """Enhanced service using atomic processors for modular visualization generation"""
    
    def __init__(self):
        # Legacy configurations for backward compatibility
        self.chart_type_rules = self._initialize_chart_type_rules()
        self.color_palettes = self._initialize_color_palettes()
        self.library_configs = self._initialize_library_configs()
        
        # Initialize atomic processors
        self.chart_generator = StaticChartGenerator()
        self.data_aggregator = create_data_aggregator()
        
        # Performance cache for processed data
        self._transform_cache = {}
        self._chart_cache = {}
        
        logger.info("DataVisualizationService initialized with atomic processors")
    
    async def generate_visualization_spec(
        self,
        execution_result: ExecutionResult,
        query_context: QueryContext,
        semantic_metadata: SemanticMetadata,
        preferred_library: ChartLibrary = ChartLibrary.CHARTJS,
        chart_type_hint: Optional[ChartType] = None,
        enable_transforms: bool = True,
        export_formats: Optional[List[ExportFormat]] = None
    ) -> Dict[str, Any]:
        """
        Enhanced visualization generation using atomic processors
        
        Args:
            execution_result: SQL execution results
            query_context: Original query context
            semantic_metadata: Available metadata
            preferred_library: Chart library preference (now using ChartLibrary enum)
            chart_type_hint: Optional chart type suggestion
            enable_transforms: Whether to apply smart data transformations
            export_formats: Optional list of export formats to prepare
            
        Returns:
            Enhanced visualization specification with atomic processor results
        """
        start_time = datetime.now()
        
        try:
            if not execution_result.success or not execution_result.data:
                return self._generate_empty_visualization(
                    "No data available", execution_result.error_message
                )
            
            # Step 1: Analyze data structure (legacy + enhanced)
            data_analysis = self._analyze_data_structure(
                execution_result.data, execution_result.column_names
            )
            
            # Step 2: Apply intelligent data transformations using atomic processors
            transform_result = None
            processed_data = execution_result.data
            
            if enable_transforms:
                transform_result = await self._apply_smart_transformations(
                    execution_result.data, data_analysis, query_context
                )
                if transform_result and transform_result.success:
                    processed_data = transform_result.transformed_data
                    # Update data analysis with transformed data
                    data_analysis = self._analyze_data_structure(
                        processed_data, execution_result.column_names
                    )
            
            # Step 3: Determine optimal chart type using atomic processor logic
            if chart_type_hint:
                chart_type = chart_type_hint
                logger.info(f"Using provided chart type hint: {chart_type}")
            else:
                chart_type = await self._determine_optimal_chart_type(
                    data_analysis, query_context, processed_data
                )
                logger.info(f"Auto-determined chart type: {chart_type}")
            
            # Step 4: Generate chart using atomic processor
            chart_result = await self._generate_chart_with_processor(
                processed_data, chart_type, preferred_library, data_analysis
            )
            
            if not chart_result.success:
                logger.warning(f"Atomic chart generation failed: {chart_result.error_message}")
                # Fallback to legacy method
                chart_data = self._generate_chart_data(
                    processed_data, execution_result.column_names, 
                    chart_type, data_analysis
                )
                chart_config = ChartConfig(
                    chart_type=chart_type, 
                    library=preferred_library,
                    title=f"Data Analysis - {chart_type.value.title()}"
                )
            else:
                chart_data = ChartData.from_chart_result(chart_result)
                # Create config from chart result or use default
                if hasattr(chart_result, 'config') and chart_result.config:
                    chart_config = chart_result.config
                else:
                    chart_config = ChartConfig(
                        chart_type=chart_type,
                        library=preferred_library,
                        title=f"Data Analysis - {chart_type.value.title()}"
                    )
            
            # Step 5: Generate insights using both legacy and atomic processor data
            insights = await self._generate_enhanced_insights(
                processed_data, data_analysis, chart_type, chart_result, transform_result
            )
            
            # Step 6: Prepare export options if requested
            export_options = export_formats or [ExportFormat.PNG, ExportFormat.SVG, ExportFormat.JSON]
            
            # Step 7: Create enhanced visualization spec
            viz_spec = VisualizationSpec(
                id=f"viz_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                type=chart_type,
                title=self._generate_title(query_context, chart_type),
                description=self._generate_description(query_context, data_analysis),
                data=chart_data,
                config=chart_config,
                library=preferred_library,
                component_props=self._generate_component_props(
                    chart_type, preferred_library, data_analysis
                ),
                insights=insights,
                confidence_score=self._calculate_enhanced_confidence(
                    data_analysis, chart_type, chart_result, transform_result
                ),
                chart_result=chart_result,
                transform_result=transform_result,
                export_options=export_options,
                performance_metadata={
                    'generation_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                    'data_points': len(processed_data),
                    'transformations_applied': transform_result.transformation_applied.value if transform_result else None,
                    'chart_generation_time_ms': chart_result.generation_time_ms if chart_result else 0
                }
            )
            
            return {
                "status": "success",
                "visualization": asdict(viz_spec),
                "alternatives": await self._generate_enhanced_alternatives(
                    execution_result, query_context, chart_type, processed_data
                ),
                "data_summary": data_analysis,
                "transformations": {
                    "applied": transform_result.transformation_applied.value if transform_result else None,
                    "original_rows": len(execution_result.data),
                    "processed_rows": len(processed_data),
                    "performance": transform_result.execution_time_ms if transform_result else 0
                },
                "performance": viz_spec.performance_metadata,
                "export_ready": len(export_options) > 0,
                "message": f"Generated {chart_type.value} visualization with {len(processed_data)} data points using atomic processors"
            }
            
        except Exception as e:
            logger.error(f"Enhanced visualization generation failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "visualization": self._generate_empty_visualization("Error", str(e)),
                "message": "Enhanced visualization generation failed"
            }
    
    async def _apply_smart_transformations(self, data: List[Dict[str, Any]], 
                                         data_analysis: Dict[str, Any],
                                         query_context: QueryContext) -> Optional[TransformResult]:
        """Apply intelligent data transformations using atomic processors"""
        try:
            # Generate cache key for transformation
            cache_key = f"transform_{hash(str(data[:5]))}_{len(data)}_{data_analysis['column_count']}"
            
            if cache_key in self._transform_cache:
                logger.info("Using cached transformation result")
                return self._transform_cache[cache_key]
            
            # Determine if transformation is beneficial
            if len(data) <= 10:
                return None  # Small datasets don't need transformation
            
            # Apply smart aggregation for chart optimization
            suggestions = self.data_aggregator.analyze_data_characteristics(data)
            
            if suggestions.get('suggested_transformations'):
                best_suggestion = suggestions['suggested_transformations'][0]
                transform_type = best_suggestion['transformation']
                
                # Create appropriate config
                if transform_type == TransformationType.AGGREGATE:
                    config = TransformConfig(
                        transformation_type=TransformationType.AGGREGATE,
                        group_by_columns=best_suggestion['suggested_config'].get('group_by_columns', []),
                        aggregation_functions=best_suggestion['suggested_config'].get('aggregation_functions', {})
                    )
                elif transform_type == TransformationType.TOP_N:
                    config = TransformConfig(
                        transformation_type=TransformationType.TOP_N,
                        custom_params=best_suggestion['suggested_config']
                    )
                else:
                    return None
                
                # Apply transformation
                result = await self.data_aggregator.transform_data(data, config)
                
                # Cache successful results
                if result.success:
                    self._transform_cache[cache_key] = result
                
                return result
            
        except Exception as e:
            logger.error(f"Smart transformation failed: {e}")
        
        return None
    
    def _convert_to_chart_data(self, data: List[Dict[str, Any]], data_analysis: Dict[str, Any]):
        """Convert raw data to ChartData format for atomic processors"""
        from ...processors.data_processors.chart_generators import ChartData
        
        # Determine x and y columns based on data analysis
        x_column = None
        y_column = None
        
        # Choose appropriate columns
        if data_analysis.get('datetime_columns'):
            x_column = data_analysis['datetime_columns'][0]
        elif data_analysis.get('categorical_columns'):
            x_column = data_analysis['categorical_columns'][0]
        
        if data_analysis.get('numeric_columns'):
            y_column = data_analysis['numeric_columns'][0]
        
        # Extract values
        x_values = []
        y_values = []
        
        if x_column and y_column:
            for row in data:
                x_val = row.get(x_column)
                y_val = row.get(y_column)
                if x_val is not None and y_val is not None:
                    x_values.append(x_val)
                    y_values.append(y_val)
        elif y_column:  # Only numeric data (for metrics)
            for i, row in enumerate(data):
                y_val = row.get(y_column)
                if y_val is not None:
                    x_values.append(f"Item {i+1}")
                    y_values.append(y_val)
        else:  # Fallback
            for i, row in enumerate(data):
                x_values.append(f"Item {i+1}")
                y_values.append(1)  # Default value
        
        return ChartData(
            x_values=x_values,
            y_values=y_values,
            series_name=y_column or "Data",
            categories=x_values if x_column else None,
            metadata={
                'x_column': x_column,
                'y_column': y_column,
                'row_count': len(data)
            },
            data_types={
                col: analysis_type for col, analysis_type in 
                zip(data_analysis.get('columns', []), 
                    [data_analysis.get('column_types', {}).get(col, 'unknown') 
                     for col in data_analysis.get('columns', [])])
            }
        )
    
    async def _determine_optimal_chart_type(self, data_analysis: Dict[str, Any],
                                          query_context: QueryContext,
                                          data: List[Dict[str, Any]]) -> ChartType:
        """Determine optimal chart type using atomic processor logic"""
        try:
            # Use atomic processor's chart type determination
            if hasattr(self.chart_generator, 'recommend_chart_type'):
                recommendation = await self.chart_generator.recommend_chart_type(data, data_analysis)
                if recommendation:
                    return recommendation
            
            # Fallback to legacy logic with ChartType enum mapping
            legacy_type = self._determine_chart_type(data_analysis, query_context)
            
            # Map legacy types to atomic processor ChartType
            type_mapping = {
                'bar': ChartType.BAR,
                'line': ChartType.LINE,
                'pie': ChartType.PIE,
                'scatter': ChartType.SCATTER,
                'area': ChartType.AREA,
                'table': ChartType.BAR,  # Map table to bar chart for display
                'metric': ChartType.BAR,  # Use bar chart for metrics (matplotlib compatible)
                'histogram': ChartType.HISTOGRAM,
                'heatmap': ChartType.HEATMAP
            }
            
            return type_mapping.get(legacy_type.value, ChartType.BAR)
            
        except Exception as e:
            logger.error(f"Chart type determination failed: {e}")
            return ChartType.BAR
    
    async def _generate_chart_with_processor(self, data: List[Dict[str, Any]],
                                           chart_type: ChartType,
                                           library: ChartLibrary,
                                           data_analysis: Dict[str, Any]) -> ChartResult:
        """Generate chart using atomic processor"""
        try:
            # Generate cache key
            cache_key = f"chart_{chart_type.value}_{library.value}_{hash(str(data[:3]))}_{len(data)}"
            
            if cache_key in self._chart_cache:
                logger.info("Using cached chart result")
                return self._chart_cache[cache_key]
            
            # Create chart configuration
            from ...processors.data_processors.chart_generators import ChartDimensions
            config = ChartConfig(
                chart_type=chart_type,
                library=library,
                title=f"Data Analysis - {chart_type.value.title()}",
                dimensions=ChartDimensions(width=800, height=400),
                interactive=True,
                custom_options={
                    'responsive': True,
                    'maintainAspectRatio': False,
                    'data_analysis': data_analysis
                }
            )
            
            # Convert data to ChartData format for atomic processor
            chart_data = self._convert_to_chart_data(data, data_analysis)
            
            # Generate chart using atomic processor
            logger.info(f"Generating chart with type: {chart_type}, library: {library}")
            result = await self.chart_generator.generate_chart(chart_data, config)
            logger.info(f"Chart generation result: success={result.success}, error={getattr(result, 'error_message', None)}")
            
            # Cache successful results
            if result.success:
                self._chart_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Atomic chart generation failed: {e}")
            return ChartResult(
                success=False,
                error_message=str(e),
                library_used=library
            )
    
    async def _generate_enhanced_insights(self, data: List[Dict[str, Any]],
                                        data_analysis: Dict[str, Any],
                                        chart_type: ChartType,
                                        chart_result: Optional[ChartResult],
                                        transform_result: Optional[TransformResult]) -> List[str]:
        """Generate enhanced insights using atomic processor results"""
        insights = []
        
        # Add basic insights from legacy method
        legacy_insights = self._generate_insights(data, data_analysis, LegacyChartType(chart_type.value))
        insights.extend(legacy_insights)
        
        # Add transformation insights
        if transform_result and transform_result.success:
            insights.append(f"Applied {transform_result.transformation_applied.value} transformation")
            insights.append(f"Reduced from {transform_result.original_row_count} to {transform_result.transformed_row_count} data points")
            
            if transform_result.warnings:
                insights.extend([f"Note: {warning}" for warning in transform_result.warnings])
        
        # Add chart generation insights
        if chart_result and chart_result.success:
            insights.append(f"Chart generated in {chart_result.generation_time_ms:.1f}ms")
            
            if chart_result.metadata:
                for key, value in chart_result.metadata.items():
                    insights.append(f"{key.replace('_', ' ').title()}: {value}")
        
        # Add performance insights
        if len(data) > 1000:
            insights.append("Large dataset - consider applying filters for better performance")
        
        return insights
    
    async def _generate_enhanced_alternatives(self, execution_result: ExecutionResult,
                                            query_context: QueryContext,
                                            primary_type: ChartType,
                                            processed_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate enhanced alternative visualizations"""
        alternatives = []
        
        # Get legacy alternatives
        legacy_alternatives = self._generate_alternative_visualizations(
            execution_result, query_context, LegacyChartType(primary_type.value)
        )
        
        # Convert to enhanced format
        for alt in legacy_alternatives:
            alternatives.append({
                'type': alt['type'],
                'title': alt['title'],
                'description': alt['description'],
                'estimated_performance': 'fast' if len(processed_data) < 100 else 'medium',
                'supports_export': True
            })
        
        # Add atomic processor specific alternatives
        if primary_type != ChartType.PIE:  # Use PIE as alternative since TABLE doesn't exist
            alternatives.append({
                'type': ChartType.PIE.value,
                'title': 'Interactive Pie Chart',
                'description': 'Proportional data view with interactive segments',
                'estimated_performance': 'fast',
                'supports_export': True
            })
        
        return alternatives
    
    def _calculate_enhanced_confidence(self, data_analysis: Dict[str, Any],
                                     chart_type: ChartType,
                                     chart_result: Optional[ChartResult],
                                     transform_result: Optional[TransformResult]) -> float:
        """Calculate enhanced confidence score"""
        # Start with legacy confidence
        base_confidence = self._calculate_confidence(data_analysis, LegacyChartType(chart_type.value))
        
        # Adjust based on atomic processor results
        if chart_result and chart_result.success:
            base_confidence *= 1.1  # Boost for successful atomic generation
        elif chart_result and not chart_result.success:
            base_confidence *= 0.8  # Reduce for failed atomic generation
        
        if transform_result and transform_result.success:
            base_confidence *= 1.05  # Small boost for successful transformation
        
        return min(1.0, base_confidence)
    
    async def export_visualization(self, viz_spec: VisualizationSpec, 
                                 export_format: ExportFormat,
                                 export_config: Optional[ExportConfig] = None) -> ExportResult:
        """Export visualization using atomic processors"""
        try:
            # Use chart result if available from atomic processors
            if viz_spec.chart_result and viz_spec.chart_result.success:
                chart_data = viz_spec.chart_result.chart_data
                chart_output = viz_spec.chart_result.output_data
            else:
                # Fallback to legacy data
                chart_data = asdict(viz_spec.data)
                chart_output = None
            
            # Create default export config if not provided
            if not export_config:
                export_config = ExportConfig(
                    format=export_format,
                    quality=ExportQuality.HIGH,
                    width=viz_spec.config.width if hasattr(viz_spec.config, 'width') else 800,
                    height=viz_spec.config.height if hasattr(viz_spec.config, 'height') else 400,
                    include_metadata=True,
                    custom_options={
                        'chart_type': viz_spec.type.value,
                        'library': viz_spec.library.value if hasattr(viz_spec.library, 'value') else str(viz_spec.library),
                        'title': viz_spec.title
                    }
                )
            
            # TODO: Implement actual export engine when available
            # For now, return a success result with metadata
            return ExportResult(
                success=True,
                output_path=None,
                output_data=chart_output,
                output_text=json.dumps(chart_data) if export_format == ExportFormat.JSON else None,
                file_size_bytes=len(json.dumps(chart_data)) if export_format == ExportFormat.JSON else 0,
                export_format=export_format,
                export_time_ms=50.0,  # Placeholder
                metadata={
                    'chart_type': viz_spec.type.value,
                    'data_points': len(viz_spec.data.datasets[0].get('data', [])) if viz_spec.data.datasets else 0,
                    'export_format': export_format.value
                }
            )
            
        except Exception as e:
            logger.error(f"Visualization export failed: {e}")
            return ExportResult(
                success=False,
                error_message=str(e),
                export_format=export_format,
                export_time_ms=0
            )
    
    async def get_export_recommendations(self, viz_spec: VisualizationSpec,
                                       intended_use: str = "web") -> List[Dict[str, Any]]:
        """Get export format recommendations using atomic processors"""
        try:
            # TODO: Use actual export engine when available
            # For now, provide basic recommendations
            recommendations = []
            
            if intended_use == "web":
                recommendations.extend([
                    {
                        'format': ExportFormat.SVG,
                        'reason': 'Scalable vector format perfect for web display',
                        'score': 0.9,
                        'estimated_size_kb': 25
                    },
                    {
                        'format': ExportFormat.PNG,
                        'reason': 'High quality raster format with transparency support',
                        'score': 0.8,
                        'estimated_size_kb': 150
                    }
                ])
            elif intended_use == "print":
                recommendations.extend([
                    {
                        'format': ExportFormat.PDF,
                        'reason': 'Professional print format with vector support',
                        'score': 0.9,
                        'estimated_size_kb': 100
                    },
                    {
                        'format': ExportFormat.SVG,
                        'reason': 'Scalable vector format for any print size',
                        'score': 0.8,
                        'estimated_size_kb': 25
                    }
                ])
            else:  # data_sharing
                recommendations.extend([
                    {
                        'format': ExportFormat.JSON,
                        'reason': 'Structured data format for programmatic use',
                        'score': 0.9,
                        'estimated_size_kb': 10
                    },
                    {
                        'format': ExportFormat.CSV,
                        'reason': 'Universal data format readable by any tool',
                        'score': 0.8,
                        'estimated_size_kb': 5
                    }
                ])
            
            return sorted(recommendations, key=lambda x: x['score'], reverse=True)
            
        except Exception as e:
            logger.error(f"Export recommendations failed: {e}")
            return []
    
    def clear_caches(self):
        """Clear performance caches"""
        self._transform_cache.clear()
        self._chart_cache.clear()
        logger.info("Visualization service caches cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'transform_cache_size': len(self._transform_cache),
            'chart_cache_size': len(self._chart_cache),
            'total_cached_items': len(self._transform_cache) + len(self._chart_cache)
        }

    def _analyze_data_structure(self, data: List[Dict], columns: List[str]) -> Dict[str, Any]:
        """Analyze data structure to determine visualization approach"""
        if not data:
            return {"type": "empty", "columns": columns, "row_count": 0}
        
        analysis = {
            "type": "structured",
            "columns": columns,
            "column_count": len(columns),
            "row_count": len(data),
            "column_types": {},
            "numeric_columns": [],
            "categorical_columns": [],
            "datetime_columns": [],
            "unique_values": {},
            "null_counts": {},
            "data_ranges": {}
        }
        
        # Analyze each column
        for col in columns:
            values = [row.get(col) for row in data if row.get(col) is not None]
            analysis["null_counts"][col] = len(data) - len(values)
            
            if not values:
                analysis["column_types"][col] = "null"
                continue
            
            # Determine column type
            sample_value = values[0]
            
            if isinstance(sample_value, (int, float)):
                analysis["column_types"][col] = "numeric"
                analysis["numeric_columns"].append(col)
                analysis["data_ranges"][col] = {"min": min(values), "max": max(values)}
            
            elif isinstance(sample_value, str):
                # Check if it's a date
                if self._is_date_column(values):
                    analysis["column_types"][col] = "datetime"
                    analysis["datetime_columns"].append(col)
                else:
                    analysis["column_types"][col] = "categorical"
                    analysis["categorical_columns"].append(col)
            
            else:
                analysis["column_types"][col] = "mixed"
            
            # Count unique values
            analysis["unique_values"][col] = len(set(str(v) for v in values))
        
        return analysis
    
    def _determine_chart_type(self, data_analysis: Dict, query_context: QueryContext) -> LegacyChartType:
        """Determine optimal chart type based on data structure and query intent"""
        
        # Special case: single metric
        if data_analysis["row_count"] == 1 and len(data_analysis["numeric_columns"]) == 1:
            return LegacyChartType.METRIC
        
        # Special case: too much data for visualization
        if data_analysis["row_count"] > 1000:
            return LegacyChartType.TABLE
        
        numeric_cols = len(data_analysis["numeric_columns"])
        categorical_cols = len(data_analysis["categorical_columns"])
        datetime_cols = len(data_analysis["datetime_columns"])
        
        # Time series data
        if datetime_cols >= 1 and numeric_cols >= 1:
            return LegacyChartType.LINE
        
        # Single categorical + single numeric = bar chart
        if categorical_cols == 1 and numeric_cols == 1:
            unique_categories = data_analysis["unique_values"].get(
                data_analysis["categorical_columns"][0], 0
            )
            if unique_categories <= 10:
                return LegacyChartType.BAR
            elif unique_categories <= 50:
                return LegacyChartType.TABLE
        
        # Multiple numeric columns = scatter or line
        if numeric_cols >= 2:
            if data_analysis["row_count"] <= 100:
                return LegacyChartType.SCATTER
            else:
                return LegacyChartType.LINE
        
        # Aggregation query
        if any(keyword in query_context.business_intent.lower() 
               for keyword in ["sum", "count", "average", "total"]):
            if categorical_cols == 1:
                unique_categories = data_analysis["unique_values"].get(
                    data_analysis["categorical_columns"][0], 0
                )
                if unique_categories <= 8:
                    return LegacyChartType.PIE
                else:
                    return LegacyChartType.BAR
        
        # Default fallback
        if data_analysis["row_count"] <= 50:
            return LegacyChartType.TABLE
        else:
            return LegacyChartType.BAR
    
    def _generate_chart_data(self, data: List[Dict], columns: List[str], 
                           chart_type: ChartType, data_analysis: Dict) -> ChartData:
        """Generate chart data structure based on chart type"""
        
        if chart_type == ChartType.KPI_CARD:  # Fixed: Use KPI_CARD instead of METRIC
            return self._generate_metric_data(data, data_analysis)
        
        elif chart_type == ChartType.HISTOGRAM:  # Fixed: Use HISTOGRAM instead of TABLE
            return self._generate_table_data(data, columns)
        
        elif chart_type == ChartType.BAR:
            return self._generate_bar_data(data, data_analysis)
        
        elif chart_type == ChartType.PIE:
            return self._generate_pie_data(data, data_analysis)
        
        elif chart_type == ChartType.LINE:
            return self._generate_line_data(data, data_analysis)
        
        elif chart_type == ChartType.SCATTER:
            return self._generate_scatter_data(data, data_analysis)
        
        else:
            return self._generate_table_data(data, columns)
    
    def _generate_metric_data(self, data: List[Dict], data_analysis: Dict) -> ChartData:
        """Generate data for metric visualization"""
        numeric_col = data_analysis["numeric_columns"][0]
        value = data[0][numeric_col]
        
        return ChartData(
            labels=[numeric_col],
            datasets=[{
                "value": value,
                "label": numeric_col,
                "color": self.color_palettes["primary"][0]
            }],
            metadata={"format": "number", "precision": 2}
        )
    
    def _generate_table_data(self, data: List[Dict], columns: List[str]) -> ChartData:
        """Generate data for table visualization"""
        return ChartData(
            labels=columns,
            datasets=[{
                "data": data,
                "columns": columns
            }],
            metadata={"paginated": len(data) > 100, "sortable": True}
        )
    
    def _generate_bar_data(self, data: List[Dict], data_analysis: Dict) -> ChartData:
        """Generate data for bar chart"""
        categorical_col = data_analysis["categorical_columns"][0]
        numeric_col = data_analysis["numeric_columns"][0]
        
        labels = [str(row[categorical_col]) for row in data]
        values = [row[numeric_col] for row in data]
        
        return ChartData(
            labels=labels,
            datasets=[{
                "label": numeric_col,
                "data": values,
                "backgroundColor": self.color_palettes["categorical"][:len(values)],
                "borderColor": self.color_palettes["primary"][0],
                "borderWidth": 1
            }],
            metadata={"orientation": "vertical" if len(labels) <= 10 else "horizontal"}
        )
    
    def _generate_pie_data(self, data: List[Dict], data_analysis: Dict) -> ChartData:
        """Generate data for pie chart"""
        categorical_col = data_analysis["categorical_columns"][0]
        numeric_col = data_analysis["numeric_columns"][0]
        
        labels = [str(row[categorical_col]) for row in data]
        values = [row[numeric_col] for row in data]
        
        return ChartData(
            labels=labels,
            datasets=[{
                "data": values,
                "backgroundColor": self.color_palettes["categorical"][:len(values)],
                "borderWidth": 2,
                "borderColor": "#ffffff"
            }],
            metadata={"showLegend": True, "showPercentages": True}
        )
    
    def _generate_line_data(self, data: List[Dict], data_analysis: Dict) -> ChartData:
        """Generate data for line chart"""
        x_col = data_analysis["datetime_columns"][0] if data_analysis["datetime_columns"] else data_analysis["categorical_columns"][0]
        y_cols = data_analysis["numeric_columns"][:3]  # Max 3 lines
        
        labels = [str(row[x_col]) for row in data]
        datasets = []
        
        for i, y_col in enumerate(y_cols):
            datasets.append({
                "label": y_col,
                "data": [row[y_col] for row in data],
                "borderColor": self.color_palettes["primary"][i % len(self.color_palettes["primary"])],
                "backgroundColor": self.color_palettes["primary"][i % len(self.color_palettes["primary"])] + "20",
                "fill": False,
                "tension": 0.1
            })
        
        return ChartData(
            labels=labels,
            datasets=datasets,
            metadata={"smooth": True, "showPoints": len(data) <= 50}
        )
    
    def _generate_scatter_data(self, data: List[Dict], data_analysis: Dict) -> ChartData:
        """Generate data for scatter plot"""
        x_col = data_analysis["numeric_columns"][0]
        y_col = data_analysis["numeric_columns"][1]
        
        scatter_data = [{"x": row[x_col], "y": row[y_col]} for row in data]
        
        return ChartData(
            labels=[x_col, y_col],
            datasets=[{
                "label": f"{y_col} vs {x_col}",
                "data": scatter_data,
                "backgroundColor": self.color_palettes["primary"][0] + "60",
                "borderColor": self.color_palettes["primary"][0],
                "pointRadius": 5
            }],
            metadata={"correlation": self._calculate_correlation(data, x_col, y_col)}
        )
    
    def _generate_chart_config(self, chart_type: ChartType, data_analysis: Dict, library: str) -> ChartConfig:
        """Generate chart configuration based on type and library"""  
        base_config = ChartConfig(
            chart_type=chart_type,
            library=ChartLibrary.CHARTJS if library == "chartjs" else ChartLibrary.RECHARTS
        )
        
        if library == "chartjs":
            return self._generate_chartjs_config(chart_type, data_analysis)
        elif library == "recharts":
            return self._generate_recharts_config(chart_type, data_analysis)
        else:
            return base_config
    
    def _generate_chartjs_config(self, chart_type: ChartType, data_analysis: Dict) -> ChartConfig:
        """Generate Chart.js specific configuration"""
        config = {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"position": "top"},
                "tooltip": {"mode": "index", "intersect": False}
            }
        }
        
        if chart_type in [ChartType.BAR, ChartType.LINE, ChartType.SCATTER]:
            config["scales"] = {
                "x": {"beginAtZero": True},
                "y": {"beginAtZero": True}
            }
        
        return ChartConfig(
            chart_type=chart_type,
            library=ChartLibrary.CHARTJS,
            custom_options=config
        )
    
    def _generate_recharts_config(self, chart_type: ChartType, data_analysis: Dict) -> ChartConfig:
        """Generate Recharts specific configuration"""
        return ChartConfig(
            chart_type=chart_type,
            library=ChartLibrary.RECHARTS,
            custom_options={"tooltip": True, "legend": True}
        )
    
    def _generate_component_props(self, chart_type: ChartType, library: str, data_analysis: Dict) -> Dict[str, Any]:
        """Generate library-specific component props"""
        props = {"height": 400, "width": "100%"}
        
        if library == "chartjs":
            props.update({
                "type": chart_type.value,
                "options": {"responsive": True}
            })
        
        elif library == "recharts":
            if chart_type == ChartType.BAR:
                props.update({"margin": {"top": 20, "right": 30, "left": 20, "bottom": 5}})
            elif chart_type == ChartType.LINE:
                props.update({"margin": {"top": 5, "right": 30, "left": 20, "bottom": 5}})
        
        return props
    
    def _generate_insights(self, data: List[Dict], data_analysis: Dict, chart_type: ChartType) -> List[str]:
        """Generate insights about the visualization"""
        insights = []
        
        insights.append(f"Dataset contains {data_analysis['row_count']} records")
        
        if data_analysis["numeric_columns"]:
            for col in data_analysis["numeric_columns"][:3]:
                range_info = data_analysis["data_ranges"].get(col, {})
                if range_info:
                    insights.append(f"{col} ranges from {range_info['min']} to {range_info['max']}")
        
        if chart_type == ChartType.PIE:
            insights.append("Pie chart shows proportional distribution")
        elif chart_type == ChartType.BAR:
            insights.append("Bar chart enables easy comparison across categories")
        elif chart_type == ChartType.LINE:
            insights.append("Line chart reveals trends over time")
        
        return insights
    
    def _generate_alternative_visualizations(self, execution_result: ExecutionResult, 
                                           query_context: QueryContext, 
                                           primary_type: ChartType) -> List[Dict[str, Any]]:
        """Generate alternative visualization options"""
        alternatives = []
        
        # Always offer histogram as alternative (TABLE doesn't exist in ChartType enum)
        if primary_type != ChartType.HISTOGRAM:
            alternatives.append({
                "type": ChartType.HISTOGRAM.value,
                "title": "Data Distribution",
                "description": "View data distribution histogram"
            })
        
        # Context-specific alternatives
        if primary_type == ChartType.BAR:
            alternatives.append({
                "type": ChartType.PIE.value,
                "title": "Pie Chart",
                "description": "Show proportional distribution"
            })
        
        elif primary_type == ChartType.LINE:
            alternatives.append({
                "type": ChartType.AREA.value,
                "title": "Area Chart",
                "description": "Emphasize magnitude of change over time"
            })
        
        return alternatives
    
    def _generate_title(self, query_context: QueryContext, chart_type: ChartType) -> str:
        """Generate appropriate title for the visualization"""
        intent = query_context.business_intent
        
        # Clean up the intent for title
        title = intent.replace("_", " ").title()
        
        # Add chart type context
        type_context = {
            ChartType.BAR: "Comparison",
            ChartType.PIE: "Distribution", 
            ChartType.LINE: "Trend",
            ChartType.SCATTER: "Correlation",
            ChartType.KPI_CARD: "Key Metric",  # Fixed: Use KPI_CARD instead of METRIC
            ChartType.HISTOGRAM: "Data View"  # Fixed: Use HISTOGRAM instead of TABLE
        }
        
        context = type_context.get(chart_type, "Analysis")
        return f"{title} - {context}"
    
    def _generate_description(self, query_context: QueryContext, data_analysis: Dict) -> str:
        """Generate description for the visualization"""
        entities = ", ".join(query_context.entities_mentioned[:3])
        operations = ", ".join(query_context.operations[:2])
        
        desc = f"Analysis of {entities}" if entities else "Data analysis"
        if operations:
            desc += f" showing {operations}"
        
        desc += f" ({data_analysis['row_count']} records)"
        return desc
    
    def _calculate_confidence(self, data_analysis: Dict, chart_type: ChartType) -> float:
        """Calculate confidence score for the visualization choice"""
        score = 0.8  # Base confidence
        
        # Adjust based on data quality
        if data_analysis["row_count"] == 0:
            score = 0.0
        elif data_analysis["row_count"] < 3:
            score *= 0.5
        elif data_analysis["row_count"] > 1000:
            score *= 0.9 if chart_type == ChartType.HISTOGRAM else 0.7  # Fixed: Use HISTOGRAM instead of TABLE
        
        # Adjust based on chart type appropriateness
        numeric_cols = len(data_analysis["numeric_columns"])
        categorical_cols = len(data_analysis["categorical_columns"])
        
        if chart_type == ChartType.BAR and categorical_cols >= 1 and numeric_cols >= 1:
            score *= 1.1
        elif chart_type == ChartType.PIE and categorical_cols == 1 and numeric_cols == 1:
            score *= 1.0
        elif chart_type == ChartType.SCATTER and numeric_cols >= 2:
            score *= 1.1
        
        return min(1.0, score)
    
    def _is_date_column(self, values: List) -> bool:
        """Check if column contains date values"""
        try:
            from dateutil import parser
            sample_size = min(5, len(values))
            date_count = 0
            
            for value in values[:sample_size]:
                try:
                    parser.parse(str(value))
                    date_count += 1
                except:
                    pass
            
            return date_count / sample_size > 0.6
        except ImportError:
            return False
    
    def _calculate_correlation(self, data: List[Dict], x_col: str, y_col: str) -> float:
        """Calculate correlation coefficient"""
        try:
            x_values = [row[x_col] for row in data if row.get(x_col) is not None]
            y_values = [row[y_col] for row in data if row.get(y_col) is not None]
            
            if len(x_values) != len(y_values) or len(x_values) < 2:
                return 0.0
            
            # Simple correlation calculation
            n = len(x_values)
            sum_x = sum(x_values)
            sum_y = sum(y_values)
            sum_xy = sum(x * y for x, y in zip(x_values, y_values))
            sum_x2 = sum(x * x for x in x_values)
            sum_y2 = sum(y * y for y in y_values)
            
            numerator = n * sum_xy - sum_x * sum_y
            denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5
            
            return numerator / denominator if denominator != 0 else 0.0
        except:
            return 0.0
    
    def _generate_empty_visualization(self, title: str, message: str) -> Dict[str, Any]:
        """Generate empty visualization spec for error cases"""
        return {
            "id": f"empty_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "type": ChartType.BAR.value,  # Use BAR as fallback instead of TABLE
            "title": title,
            "description": message,
            "data": {"labels": [], "datasets": [], "metadata": {}},
            "config": {"responsive": True},
            "library": "chartjs",
            "component_props": {},
            "insights": [message],
            "confidence_score": 0.0
        }
    
    def _initialize_chart_type_rules(self) -> Dict[str, Any]:
        """Initialize rules for chart type selection"""
        return {
            "aggregation_keywords": ["sum", "count", "avg", "total", "average"],
            "time_keywords": ["time", "date", "year", "month", "day"],
            "comparison_keywords": ["compare", "vs", "versus", "between"],
            "distribution_keywords": ["distribution", "breakdown", "share", "percentage"]
        }
    
    def _initialize_color_palettes(self) -> Dict[str, List[str]]:
        """Initialize color palettes for different chart types"""
        return {
            "primary": ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6"],
            "categorical": [
                "#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6",
                "#06B6D4", "#84CC16", "#F97316", "#EC4899", "#6366F1"
            ],
            "sequential": ["#FEF3E2", "#FDE68A", "#FCD34D", "#FBBF24", "#F59E0B"],
            "diverging": ["#DC2626", "#FBBF24", "#F3F4F6", "#60A5FA", "#2563EB"]
        }
    
    def _initialize_library_configs(self) -> Dict[str, Dict]:
        """Initialize configurations for different chart libraries"""
        return {
            "chartjs": {
                "supported_types": ["bar", "line", "pie", "scatter", "area"],
                "default_options": {"responsive": True, "maintainAspectRatio": False}
            },
            "recharts": {
                "supported_types": ["bar", "line", "pie", "scatter", "area"],
                "default_options": {"responsive": True}
            },
            "nivo": {
                "supported_types": ["bar", "line", "pie", "scatter", "heatmap"],
                "default_options": {"animate": True, "responsive": True}
            }
        }
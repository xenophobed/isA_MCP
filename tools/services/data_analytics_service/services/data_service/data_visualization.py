#!/usr/bin/env python3
"""
Data Visualization Service - Step 7: Generate visualization specifications from query results
Returns JSON specifications that can be consumed by React charting libraries
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from .sql_executor import ExecutionResult
from .query_matcher import QueryContext
from .semantic_enricher import SemanticMetadata

logger = logging.getLogger(__name__)

class ChartType(Enum):
    """Supported chart types"""
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
    """Chart data structure"""
    labels: List[str]
    datasets: List[Dict[str, Any]]
    metadata: Dict[str, Any]

@dataclass
class ChartConfig:
    """Chart configuration options"""
    responsive: bool = True
    maintainAspectRatio: bool = False
    plugins: Dict[str, Any] = None
    scales: Dict[str, Any] = None
    elements: Dict[str, Any] = None

@dataclass
class VisualizationSpec:
    """Complete visualization specification for React components"""
    id: str
    type: ChartType
    title: str
    description: str
    data: ChartData
    config: ChartConfig
    library: str  # 'chartjs', 'recharts', 'nivo', etc.
    component_props: Dict[str, Any]
    insights: List[str]
    confidence_score: float

class DataVisualizationService:
    """Service to generate visualization specifications from query results"""
    
    def __init__(self):
        self.chart_type_rules = self._initialize_chart_type_rules()
        self.color_palettes = self._initialize_color_palettes()
        self.library_configs = self._initialize_library_configs()
    
    async def generate_visualization_spec(
        self,
        execution_result: ExecutionResult,
        query_context: QueryContext,
        semantic_metadata: SemanticMetadata,
        preferred_library: str = "chartjs",
        chart_type_hint: Optional[ChartType] = None
    ) -> Dict[str, Any]:
        """
        Generate visualization specification from query results
        
        Args:
            execution_result: SQL execution results
            query_context: Original query context
            semantic_metadata: Available metadata
            preferred_library: React chart library preference
            chart_type_hint: Optional chart type suggestion
            
        Returns:
            Visualization specification dictionary
        """
        try:
            if not execution_result.success or not execution_result.data:
                return self._generate_empty_visualization(
                    "No data available", execution_result.error_message
                )
            
            # Analyze data structure
            data_analysis = self._analyze_data_structure(
                execution_result.data, execution_result.column_names
            )
            
            # Determine optimal chart type
            chart_type = chart_type_hint or self._determine_chart_type(
                data_analysis, query_context
            )
            
            # Generate chart data
            chart_data = self._generate_chart_data(
                execution_result.data, execution_result.column_names, 
                chart_type, data_analysis
            )
            
            # Generate configuration
            chart_config = self._generate_chart_config(
                chart_type, data_analysis, preferred_library
            )
            
            # Generate insights
            insights = self._generate_insights(
                execution_result.data, data_analysis, chart_type
            )
            
            # Create visualization spec
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
                confidence_score=self._calculate_confidence(data_analysis, chart_type)
            )
            
            return {
                "status": "success",
                "visualization": asdict(viz_spec),
                "alternatives": self._generate_alternative_visualizations(
                    execution_result, query_context, chart_type
                ),
                "data_summary": data_analysis,
                "message": f"Generated {chart_type.value} visualization with {len(execution_result.data)} data points"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate visualization: {e}")
            return {
                "status": "error",
                "error": str(e),
                "visualization": self._generate_empty_visualization("Error", str(e)),
                "message": "Visualization generation failed"
            }
    
    def _analyze_data_structure(self, data: List[Dict], columns: List[str]) -> Dict[str, Any]:
        """Analyze data structure to determine visualization approach"""
        if not data:
            return {"type": "empty", "columns": columns, "row_count": 0}
        
        analysis = {
            "type": "structured",
            "columns": columns,
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
    
    def _determine_chart_type(self, data_analysis: Dict, query_context: QueryContext) -> ChartType:
        """Determine optimal chart type based on data structure and query intent"""
        
        # Special case: single metric
        if data_analysis["row_count"] == 1 and len(data_analysis["numeric_columns"]) == 1:
            return ChartType.METRIC
        
        # Special case: too much data for visualization
        if data_analysis["row_count"] > 1000:
            return ChartType.TABLE
        
        numeric_cols = len(data_analysis["numeric_columns"])
        categorical_cols = len(data_analysis["categorical_columns"])
        datetime_cols = len(data_analysis["datetime_columns"])
        
        # Time series data
        if datetime_cols >= 1 and numeric_cols >= 1:
            return ChartType.LINE
        
        # Single categorical + single numeric = bar chart
        if categorical_cols == 1 and numeric_cols == 1:
            unique_categories = data_analysis["unique_values"].get(
                data_analysis["categorical_columns"][0], 0
            )
            if unique_categories <= 10:
                return ChartType.BAR
            elif unique_categories <= 50:
                return ChartType.TABLE
        
        # Multiple numeric columns = scatter or line
        if numeric_cols >= 2:
            if data_analysis["row_count"] <= 100:
                return ChartType.SCATTER
            else:
                return ChartType.LINE
        
        # Aggregation query
        if any(keyword in query_context.business_intent.lower() 
               for keyword in ["sum", "count", "average", "total"]):
            if categorical_cols == 1:
                unique_categories = data_analysis["unique_values"].get(
                    data_analysis["categorical_columns"][0], 0
                )
                if unique_categories <= 8:
                    return ChartType.PIE
                else:
                    return ChartType.BAR
        
        # Default fallback
        if data_analysis["row_count"] <= 50:
            return ChartType.TABLE
        else:
            return ChartType.BAR
    
    def _generate_chart_data(self, data: List[Dict], columns: List[str], 
                           chart_type: ChartType, data_analysis: Dict) -> ChartData:
        """Generate chart data structure based on chart type"""
        
        if chart_type == ChartType.METRIC:
            return self._generate_metric_data(data, data_analysis)
        
        elif chart_type == ChartType.TABLE:
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
        base_config = ChartConfig(responsive=True, maintainAspectRatio=False)
        
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
        
        return ChartConfig(**config)
    
    def _generate_recharts_config(self, chart_type: ChartType, data_analysis: Dict) -> ChartConfig:
        """Generate Recharts specific configuration"""
        return ChartConfig(
            responsive=True,
            maintainAspectRatio=False,
            plugins={"tooltip": True, "legend": True}
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
        
        # Always offer table as alternative
        if primary_type != ChartType.TABLE:
            alternatives.append({
                "type": ChartType.TABLE.value,
                "title": "Data Table",
                "description": "View raw data in tabular format"
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
            ChartType.METRIC: "Key Metric",
            ChartType.TABLE: "Data View"
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
            score *= 0.9 if chart_type == ChartType.TABLE else 0.7
        
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
            "type": ChartType.TABLE.value,
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
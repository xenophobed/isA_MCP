#!/usr/bin/env python3
"""
Chart Generator Base Class
Abstract base class for all chart generators providing common interface and functionality
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ChartType(Enum):
    """Supported chart types"""
    # Basic Charts
    BAR = "bar"
    COLUMN = "column"
    LINE = "line"
    SCATTER = "scatter"
    PIE = "pie"
    AREA = "area"
    
    # Statistical Charts
    HISTOGRAM = "histogram"
    BOX_PLOT = "box_plot"
    VIOLIN_PLOT = "violin_plot"
    HEATMAP = "heatmap"
    
    # Time Series
    TIME_SERIES = "time_series"
    CANDLESTICK = "candlestick"
    
    # Advanced Charts
    SANKEY = "sankey"
    TREEMAP = "treemap"
    SUNBURST = "sunburst"
    NETWORK = "network"
    
    # Geospatial
    MAP_CHOROPLETH = "map_choropleth"
    MAP_SCATTER = "map_scatter"
    
    # Business Intelligence
    KPI_CARD = "kpi_card"
    GAUGE = "gauge"
    FUNNEL = "funnel"
    WATERFALL = "waterfall"


class ChartLibrary(Enum):
    """Supported chart libraries"""
    MATPLOTLIB = "matplotlib"
    SEABORN = "seaborn"
    PLOTLY = "plotly"
    BOKEH = "bokeh"
    D3JS = "d3js"
    CHARTJS = "chartjs"


class OutputFormat(Enum):
    """Chart output formats"""
    PNG = "png"
    SVG = "svg"
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    PLOTLY_JSON = "plotly_json"
    BASE64 = "base64"


@dataclass
class ChartDimensions:
    """Chart dimensions configuration"""
    width: int = 800
    height: int = 600
    dpi: int = 100
    aspect_ratio: Optional[float] = None
    responsive: bool = True


@dataclass
class ChartStyling:
    """Chart styling configuration"""
    theme: str = "default"
    color_palette: List[str] = field(default_factory=lambda: ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"])
    background_color: str = "white"
    grid: bool = True
    legend: bool = True
    title_font_size: int = 16
    axis_font_size: int = 12
    custom_css: Optional[str] = None


@dataclass
class ChartConfig:
    """Complete chart configuration"""
    chart_type: ChartType
    library: ChartLibrary
    dimensions: ChartDimensions = field(default_factory=ChartDimensions)
    styling: ChartStyling = field(default_factory=ChartStyling)
    title: Optional[str] = None
    subtitle: Optional[str] = None
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None
    output_format: OutputFormat = OutputFormat.PNG
    interactive: bool = False
    custom_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChartData:
    """Standardized chart data structure"""
    x_values: List[Any]
    y_values: List[Any]
    series_name: Optional[str] = None
    categories: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    data_types: Dict[str, str] = field(default_factory=dict)  # column_name -> data_type


@dataclass
class ChartResult:
    """Chart generation result"""
    success: bool
    chart_object: Optional[Any] = None
    chart_data: Optional[bytes] = None
    chart_html: Optional[str] = None
    chart_json: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    generation_time_ms: float = 0
    library_used: Optional[ChartLibrary] = None
    dimensions: Optional[ChartDimensions] = None


class ChartGeneratorBase(ABC):
    """Abstract base class for chart generators"""
    
    def __init__(self, library: ChartLibrary):
        self.library = library
        self.supported_chart_types = self._get_supported_chart_types()
        self.default_styling = ChartStyling()
        self.cache_enabled = True
        
    @abstractmethod
    def _get_supported_chart_types(self) -> List[ChartType]:
        """Return list of chart types supported by this generator"""
        pass
    
    @abstractmethod
    async def generate_chart(self, data: ChartData, config: ChartConfig) -> ChartResult:
        """Generate a chart from data and configuration"""
        pass
    
    def supports_chart_type(self, chart_type: ChartType) -> bool:
        """Check if this generator supports the given chart type"""
        return chart_type in self.supported_chart_types
    
    def supports_output_format(self, output_format: OutputFormat) -> bool:
        """Check if this generator supports the given output format"""
        # Override in subclasses for library-specific format support
        return output_format in [OutputFormat.PNG, OutputFormat.SVG, OutputFormat.PDF]
    
    async def validate_data(self, data: ChartData, config: ChartConfig) -> Dict[str, Any]:
        """Validate input data for chart generation"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'recommendations': []
        }
        
        try:
            # Basic data validation
            if not data.x_values:
                validation_result['errors'].append("X values cannot be empty")
                validation_result['is_valid'] = False
            
            if not data.y_values:
                validation_result['errors'].append("Y values cannot be empty")
                validation_result['is_valid'] = False
            
            # Length consistency
            if len(data.x_values) != len(data.y_values):
                validation_result['errors'].append("X and Y values must have the same length")
                validation_result['is_valid'] = False
            
            # Chart type support
            if not self.supports_chart_type(config.chart_type):
                validation_result['errors'].append(f"Chart type {config.chart_type.value} not supported by {self.library.value}")
                validation_result['is_valid'] = False
            
            # Output format support
            if not self.supports_output_format(config.output_format):
                validation_result['warnings'].append(f"Output format {config.output_format.value} may not be fully supported")
            
            # Data quality recommendations
            if len(data.x_values) > 10000:
                validation_result['recommendations'].append("Large dataset detected - consider data sampling or aggregation")
            
            # Missing values check
            x_none_count = sum(1 for x in data.x_values if x is None)
            y_none_count = sum(1 for y in data.y_values if y is None)
            
            if x_none_count > 0:
                validation_result['warnings'].append(f"{x_none_count} missing values in X data")
            
            if y_none_count > 0:
                validation_result['warnings'].append(f"{y_none_count} missing values in Y data")
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def create_default_config(self, chart_type: ChartType) -> ChartConfig:
        """Create a default configuration for the given chart type"""
        return ChartConfig(
            chart_type=chart_type,
            library=self.library,
            dimensions=ChartDimensions(),
            styling=self.default_styling
        )
    
    def prepare_data(self, raw_data: List[Dict[str, Any]], x_column: str, y_column: str, 
                    series_column: Optional[str] = None) -> ChartData:
        """Convert raw data to ChartData format"""
        try:
            x_values = [row.get(x_column) for row in raw_data]
            y_values = [row.get(y_column) for row in raw_data]
            
            # Handle series data if specified
            series_name = None
            if series_column:
                series_values = [row.get(series_column) for row in raw_data]
                # For now, just use the first series value as the name
                series_name = str(series_values[0]) if series_values else None
            
            # Extract data types
            data_types = {}
            if raw_data:
                sample_row = raw_data[0]
                for key, value in sample_row.items():
                    if value is not None:
                        data_types[key] = type(value).__name__
            
            return ChartData(
                x_values=x_values,
                y_values=y_values,
                series_name=series_name,
                data_types=data_types,
                metadata={
                    'x_column': x_column,
                    'y_column': y_column,
                    'series_column': series_column,
                    'row_count': len(raw_data)
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to prepare chart data: {e}")
            return ChartData(x_values=[], y_values=[], metadata={'error': str(e)})
    
    def get_chart_recommendations(self, data: ChartData) -> List[Dict[str, Any]]:
        """Get chart type recommendations based on data characteristics"""
        recommendations = []
        
        try:
            x_count = len(data.x_values)
            y_count = len(data.y_values)
            
            # Analyze data types
            x_is_numeric = all(isinstance(x, (int, float)) for x in data.x_values if x is not None)
            y_is_numeric = all(isinstance(y, (int, float)) for y in data.y_values if y is not None)
            x_is_categorical = not x_is_numeric
            x_unique_count = len(set(data.x_values))
            
            # Generate recommendations
            if x_is_categorical and y_is_numeric:
                recommendations.append({
                    'chart_type': ChartType.BAR,
                    'confidence': 0.9,
                    'reason': 'Categorical X values with numeric Y values - perfect for bar chart'
                })
                
                if x_unique_count <= 10:
                    recommendations.append({
                        'chart_type': ChartType.PIE,
                        'confidence': 0.7,
                        'reason': 'Small number of categories suitable for pie chart'
                    })
            
            elif x_is_numeric and y_is_numeric:
                recommendations.append({
                    'chart_type': ChartType.SCATTER,
                    'confidence': 0.8,
                    'reason': 'Both X and Y are numeric - good for scatter plot to show correlation'
                })
                
                # Check if X values could be time-based
                x_is_sequential = all(data.x_values[i] <= data.x_values[i+1] for i in range(len(data.x_values)-1))
                if x_is_sequential:
                    recommendations.append({
                        'chart_type': ChartType.LINE,
                        'confidence': 0.8,
                        'reason': 'Sequential numeric X values suggest time series or ordered data'
                    })
            
            # Large dataset recommendations
            if x_count > 1000:
                recommendations.append({
                    'chart_type': ChartType.HISTOGRAM,
                    'confidence': 0.6,
                    'reason': 'Large dataset - consider histogram to show distribution'
                })
            
        except Exception as e:
            logger.error(f"Failed to generate chart recommendations: {e}")
        
        return sorted(recommendations, key=lambda x: x['confidence'], reverse=True)
    
    async def estimate_generation_time(self, data: ChartData, config: ChartConfig) -> float:
        """Estimate chart generation time in milliseconds"""
        # Basic estimation based on data size and chart complexity
        base_time = 100  # Base time in ms
        data_factor = len(data.x_values) * 0.01  # 0.01ms per data point
        
        complexity_factors = {
            ChartType.BAR: 1.0,
            ChartType.LINE: 1.2,
            ChartType.SCATTER: 1.5,
            ChartType.HEATMAP: 2.0,
            ChartType.SANKEY: 3.0,
            ChartType.NETWORK: 4.0
        }
        
        complexity_factor = complexity_factors.get(config.chart_type, 1.0)
        
        return base_time + data_factor * complexity_factor
    
    def _create_error_result(self, error_message: str, 
                           generation_time_ms: float = 0) -> ChartResult:
        """Create a ChartResult for error cases"""
        return ChartResult(
            success=False,
            error_message=error_message,
            generation_time_ms=generation_time_ms,
            library_used=self.library
        )
    
    def _create_success_result(self, chart_object: Any = None, 
                             chart_data: bytes = None,
                             chart_html: str = None,
                             chart_json: Dict[str, Any] = None,
                             file_path: str = None,
                             generation_time_ms: float = 0,
                             dimensions: ChartDimensions = None,
                             metadata: Dict[str, Any] = None) -> ChartResult:
        """Create a successful ChartResult"""
        return ChartResult(
            success=True,
            chart_object=chart_object,
            chart_data=chart_data,
            chart_html=chart_html,
            chart_json=chart_json,
            file_path=file_path,
            generation_time_ms=generation_time_ms,
            library_used=self.library,
            dimensions=dimensions,
            metadata=metadata or {}
        )
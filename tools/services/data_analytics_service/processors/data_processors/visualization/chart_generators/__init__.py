"""
Chart Generators Package
Atomic processors for generating various types of charts and visualizations

Provides:
- Base chart generator interface
- Static chart generators (matplotlib, seaborn)
- Interactive chart generators (plotly, bokeh)
- Custom D3.js chart generators
"""

from .chart_base import (
    ChartGeneratorBase,
    ChartType,
    ChartLibrary,
    OutputFormat,
    ChartData,
    ChartConfig,
    ChartResult,
    ChartDimensions,
    ChartStyling
)

from .static_chart_generator import (
    StaticChartGenerator,
    create_static_chart_generator,
    generate_quick_chart
)

__all__ = [
    'ChartGeneratorBase',
    'ChartType',
    'ChartLibrary', 
    'OutputFormat',
    'ChartData',
    'ChartConfig',
    'ChartResult',
    'ChartDimensions',
    'ChartStyling',
    'StaticChartGenerator',
    'create_static_chart_generator',
    'generate_quick_chart'
]
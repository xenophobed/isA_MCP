#!/usr/bin/env python3
"""
Static Chart Generator
Generates high-quality static charts using matplotlib and seaborn
"""

import io
import base64
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from .chart_base import (
    ChartGeneratorBase, ChartType, ChartLibrary, OutputFormat,
    ChartData, ChartConfig, ChartResult, ChartDimensions
)

# Optional imports with fallbacks
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-GUI backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_pdf import PdfPages
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

logger = logging.getLogger(__name__)


class StaticChartGenerator(ChartGeneratorBase):
    """Static chart generator using matplotlib and seaborn"""
    
    def __init__(self, use_seaborn: bool = True):
        self.use_seaborn = use_seaborn and SEABORN_AVAILABLE
        super().__init__(ChartLibrary.SEABORN if self.use_seaborn else ChartLibrary.MATPLOTLIB)
        
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib is required for StaticChartGenerator")
        
        # Configure matplotlib defaults
        plt.style.use('default')
        if self.use_seaborn:
            sns.set_style("whitegrid")
        
        logger.info(f"StaticChartGenerator initialized with {self.library.value}")
    
    def _get_supported_chart_types(self) -> List[ChartType]:
        """Return supported chart types for matplotlib/seaborn"""
        base_types = [
            ChartType.BAR,
            ChartType.COLUMN,
            ChartType.LINE,
            ChartType.SCATTER,
            ChartType.PIE,
            ChartType.AREA,
            ChartType.HISTOGRAM
        ]
        
        if self.use_seaborn:
            base_types.extend([
                ChartType.BOX_PLOT,
                ChartType.VIOLIN_PLOT,
                ChartType.HEATMAP
            ])
        
        return base_types
    
    def supports_output_format(self, output_format: OutputFormat) -> bool:
        """Check supported output formats"""
        return output_format in [
            OutputFormat.PNG, 
            OutputFormat.SVG, 
            OutputFormat.PDF, 
            OutputFormat.BASE64
        ]
    
    async def generate_chart(self, data: ChartData, config: ChartConfig) -> ChartResult:
        """Generate static chart using matplotlib/seaborn"""
        start_time = datetime.now()
        
        try:
            # Validate inputs
            validation = await self.validate_data(data, config)
            if not validation['is_valid']:
                return self._create_error_result(
                    f"Validation failed: {', '.join(validation['errors'])}"
                )
            
            # Create figure and axis
            fig, ax = plt.subplots(
                figsize=(config.dimensions.width/100, config.dimensions.height/100),
                dpi=config.dimensions.dpi
            )
            
            # Apply styling
            self._apply_styling(fig, ax, config)
            
            # Generate chart based on type
            chart_generated = await self._generate_chart_by_type(fig, ax, data, config)
            
            if not chart_generated:
                plt.close(fig)
                return self._create_error_result(f"Unsupported chart type: {config.chart_type.value}")
            
            # Add title and labels
            if config.title:
                ax.set_title(config.title, fontsize=config.styling.title_font_size, pad=20)
            
            if config.x_axis_label:
                ax.set_xlabel(config.x_axis_label, fontsize=config.styling.axis_font_size)
            
            if config.y_axis_label:
                ax.set_ylabel(config.y_axis_label, fontsize=config.styling.axis_font_size)
            
            # Adjust layout
            plt.tight_layout()
            
            # Generate output based on format
            result = await self._generate_output(fig, config)
            
            plt.close(fig)  # Always close to free memory
            
            # Calculate generation time
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            result.generation_time_ms = generation_time
            
            return result
            
        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            return self._create_error_result(str(e), generation_time)
    
    async def _generate_chart_by_type(self, fig, ax, data: ChartData, config: ChartConfig) -> bool:
        """Generate specific chart type"""
        try:
            if config.chart_type == ChartType.BAR:
                return self._create_bar_chart(ax, data, config)
            
            elif config.chart_type == ChartType.COLUMN:
                return self._create_column_chart(ax, data, config)
            
            elif config.chart_type == ChartType.LINE:
                return self._create_line_chart(ax, data, config)
            
            elif config.chart_type == ChartType.SCATTER:
                return self._create_scatter_chart(ax, data, config)
            
            elif config.chart_type == ChartType.PIE:
                return self._create_pie_chart(ax, data, config)
            
            elif config.chart_type == ChartType.AREA:
                return self._create_area_chart(ax, data, config)
            
            elif config.chart_type == ChartType.HISTOGRAM:
                return self._create_histogram(ax, data, config)
            
            elif config.chart_type == ChartType.BOX_PLOT and self.use_seaborn:
                return self._create_box_plot(ax, data, config)
            
            elif config.chart_type == ChartType.VIOLIN_PLOT and self.use_seaborn:
                return self._create_violin_plot(ax, data, config)
            
            elif config.chart_type == ChartType.HEATMAP and self.use_seaborn:
                return self._create_heatmap(ax, data, config)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to create {config.chart_type.value} chart: {e}")
            return False
    
    def _create_bar_chart(self, ax, data: ChartData, config: ChartConfig) -> bool:
        """Create horizontal bar chart"""
        try:
            bars = ax.barh(data.x_values, data.y_values, color=config.styling.color_palette[0])
            
            # Add value labels on bars if not too many
            if len(data.x_values) <= 20:
                for bar in bars:
                    width = bar.get_width()
                    ax.text(width, bar.get_y() + bar.get_height()/2, 
                           f'{width:.1f}', ha='left', va='center')
            
            return True
        except Exception as e:
            logger.error(f"Bar chart creation failed: {e}")
            return False
    
    def _create_column_chart(self, ax, data: ChartData, config: ChartConfig) -> bool:
        """Create vertical column chart"""
        try:
            bars = ax.bar(data.x_values, data.y_values, color=config.styling.color_palette[0])
            
            # Rotate x labels if too many categories
            if len(data.x_values) > 10:
                plt.xticks(rotation=45, ha='right')
            
            # Add value labels on bars if not too many
            if len(data.x_values) <= 15:
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2, height,
                           f'{height:.1f}', ha='center', va='bottom')
            
            return True
        except Exception as e:
            logger.error(f"Column chart creation failed: {e}")
            return False
    
    def _create_line_chart(self, ax, data: ChartData, config: ChartConfig) -> bool:
        """Create line chart"""
        try:
            ax.plot(data.x_values, data.y_values, 
                   color=config.styling.color_palette[0],
                   linewidth=2, marker='o', markersize=4)
            
            # Format x-axis if dates
            if data.data_types.get(data.metadata.get('x_column')) == 'datetime':
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                plt.xticks(rotation=45)
            
            return True
        except Exception as e:
            logger.error(f"Line chart creation failed: {e}")
            return False
    
    def _create_scatter_chart(self, ax, data: ChartData, config: ChartConfig) -> bool:
        """Create scatter plot"""
        try:
            ax.scatter(data.x_values, data.y_values,
                      color=config.styling.color_palette[0],
                      alpha=0.6, s=50)
            
            # Add trend line if both axes are numeric
            if NUMPY_AVAILABLE:
                try:
                    x_numeric = [float(x) for x in data.x_values if x is not None]
                    y_numeric = [float(y) for y in data.y_values if y is not None]
                    
                    if len(x_numeric) == len(y_numeric) and len(x_numeric) > 1:
                        z = np.polyfit(x_numeric, y_numeric, 1)
                        p = np.poly1d(z)
                        ax.plot(x_numeric, p(x_numeric), "--", alpha=0.7, 
                               color=config.styling.color_palette[1] if len(config.styling.color_palette) > 1 
                               else 'red')
                except (ValueError, TypeError):
                    pass  # Skip trend line if data isn't suitable
            
            return True
        except Exception as e:
            logger.error(f"Scatter chart creation failed: {e}")
            return False
    
    def _create_pie_chart(self, ax, data: ChartData, config: ChartConfig) -> bool:
        """Create pie chart"""
        try:
            # Filter out zero or negative values
            filtered_data = [(x, y) for x, y in zip(data.x_values, data.y_values) 
                           if y is not None and y > 0]
            
            if not filtered_data:
                return False
            
            labels, values = zip(*filtered_data)
            
            wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%',
                                            colors=config.styling.color_palette)
            
            # Improve text readability
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_weight('bold')
            
            ax.axis('equal')  # Equal aspect ratio ensures circular pie
            
            return True
        except Exception as e:
            logger.error(f"Pie chart creation failed: {e}")
            return False
    
    def _create_area_chart(self, ax, data: ChartData, config: ChartConfig) -> bool:
        """Create area chart"""
        try:
            ax.fill_between(data.x_values, data.y_values,
                           color=config.styling.color_palette[0],
                           alpha=0.6)
            
            # Add line on top
            ax.plot(data.x_values, data.y_values,
                   color=config.styling.color_palette[0],
                   linewidth=2)
            
            return True
        except Exception as e:
            logger.error(f"Area chart creation failed: {e}")
            return False
    
    def _create_histogram(self, ax, data: ChartData, config: ChartConfig) -> bool:
        """Create histogram"""
        try:
            # Use y_values for histogram data
            numeric_values = [y for y in data.y_values if y is not None and isinstance(y, (int, float))]
            
            if not numeric_values:
                return False
            
            ax.hist(numeric_values, bins=min(30, len(numeric_values)//10 + 1),
                   color=config.styling.color_palette[0], alpha=0.7,
                   edgecolor='black', linewidth=0.5)
            
            return True
        except Exception as e:
            logger.error(f"Histogram creation failed: {e}")
            return False
    
    def _create_box_plot(self, ax, data: ChartData, config: ChartConfig) -> bool:
        """Create box plot using seaborn"""
        try:
            if not PANDAS_AVAILABLE:
                return False
            
            # Convert to DataFrame for seaborn
            df = pd.DataFrame({
                'category': data.x_values,
                'value': data.y_values
            })
            
            sns.boxplot(data=df, x='category', y='value', ax=ax,
                       palette=config.styling.color_palette)
            
            if len(data.x_values) > 10:
                plt.xticks(rotation=45, ha='right')
            
            return True
        except Exception as e:
            logger.error(f"Box plot creation failed: {e}")
            return False
    
    def _create_violin_plot(self, ax, data: ChartData, config: ChartConfig) -> bool:
        """Create violin plot using seaborn"""
        try:
            if not PANDAS_AVAILABLE:
                return False
            
            # Convert to DataFrame for seaborn
            df = pd.DataFrame({
                'category': data.x_values,
                'value': data.y_values
            })
            
            sns.violinplot(data=df, x='category', y='value', ax=ax,
                          palette=config.styling.color_palette)
            
            if len(data.x_values) > 10:
                plt.xticks(rotation=45, ha='right')
            
            return True
        except Exception as e:
            logger.error(f"Violin plot creation failed: {e}")
            return False
    
    def _create_heatmap(self, ax, data: ChartData, config: ChartConfig) -> bool:
        """Create heatmap using seaborn"""
        try:
            if not PANDAS_AVAILABLE or not NUMPY_AVAILABLE:
                return False
            
            # This requires special data structure - skip for now
            # Would need matrix-like data
            logger.warning("Heatmap requires matrix data structure - not implemented")
            return False
            
        except Exception as e:
            logger.error(f"Heatmap creation failed: {e}")
            return False
    
    def _apply_styling(self, fig, ax, config: ChartConfig):
        """Apply styling configuration"""
        try:
            # Background color
            fig.patch.set_facecolor(config.styling.background_color)
            ax.set_facecolor(config.styling.background_color)
            
            # Grid
            ax.grid(config.styling.grid, alpha=0.3)
            
            # Theme-specific styling
            if config.styling.theme == "dark":
                plt.style.use('dark_background')
            elif config.styling.theme == "minimal":
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
            
        except Exception as e:
            logger.warning(f"Styling application failed: {e}")
    
    async def _generate_output(self, fig, config: ChartConfig) -> ChartResult:
        """Generate output in the requested format"""
        try:
            if config.output_format == OutputFormat.PNG:
                buffer = io.BytesIO()
                fig.savefig(buffer, format='png', bbox_inches='tight', 
                           dpi=config.dimensions.dpi, facecolor=config.styling.background_color)
                buffer.seek(0)
                
                return self._create_success_result(
                    chart_object=fig,
                    chart_data=buffer.getvalue(),
                    dimensions=config.dimensions
                )
            
            elif config.output_format == OutputFormat.SVG:
                buffer = io.BytesIO()
                fig.savefig(buffer, format='svg', bbox_inches='tight',
                           facecolor=config.styling.background_color)
                buffer.seek(0)
                
                return self._create_success_result(
                    chart_object=fig,
                    chart_data=buffer.getvalue(),
                    dimensions=config.dimensions
                )
            
            elif config.output_format == OutputFormat.PDF:
                buffer = io.BytesIO()
                fig.savefig(buffer, format='pdf', bbox_inches='tight',
                           facecolor=config.styling.background_color)
                buffer.seek(0)
                
                return self._create_success_result(
                    chart_object=fig,
                    chart_data=buffer.getvalue(),
                    dimensions=config.dimensions
                )
            
            elif config.output_format == OutputFormat.BASE64:
                buffer = io.BytesIO()
                fig.savefig(buffer, format='png', bbox_inches='tight',
                           dpi=config.dimensions.dpi, facecolor=config.styling.background_color)
                buffer.seek(0)
                
                encoded_string = base64.b64encode(buffer.getvalue()).decode()
                
                return self._create_success_result(
                    chart_object=fig,
                    chart_data=buffer.getvalue(),
                    chart_html=f"data:image/png;base64,{encoded_string}",
                    dimensions=config.dimensions
                )
            
            else:
                return self._create_error_result(f"Unsupported output format: {config.output_format.value}")
        
        except Exception as e:
            logger.error(f"Output generation failed: {e}")
            return self._create_error_result(f"Output generation failed: {str(e)}")


# Convenience functions
def create_static_chart_generator(use_seaborn: bool = True) -> StaticChartGenerator:
    """Create a static chart generator instance"""
    return StaticChartGenerator(use_seaborn=use_seaborn)


async def generate_quick_chart(data: List[Dict[str, Any]], 
                             x_column: str, 
                             y_column: str,
                             chart_type: ChartType = ChartType.BAR,
                             title: Optional[str] = None) -> ChartResult:
    """Quick chart generation with minimal configuration"""
    try:
        generator = create_static_chart_generator()
        
        # Prepare data
        chart_data = generator.prepare_data(data, x_column, y_column)
        
        # Create config
        config = generator.create_default_config(chart_type)
        if title:
            config.title = title
        config.x_axis_label = x_column
        config.y_axis_label = y_column
        
        # Generate chart
        return await generator.generate_chart(chart_data, config)
        
    except Exception as e:
        logger.error(f"Quick chart generation failed: {e}")
        return ChartResult(success=False, error_message=str(e))
#!/usr/bin/env python3
"""
Export Engine Base Class
Abstract base class for chart and data export processors
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Export formats"""
    # Images
    PNG = "png"
    JPG = "jpg"
    SVG = "svg"
    PDF = "pdf"
    
    # Web formats
    HTML = "html"
    JSON = "json"
    
    # Data formats
    CSV = "csv"
    EXCEL = "xlsx"
    PARQUET = "parquet"
    
    # Archive formats
    ZIP = "zip"
    
    # Base64 encoded
    BASE64_PNG = "base64_png"
    BASE64_SVG = "base64_svg"


class ExportQuality(Enum):
    """Export quality settings"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


@dataclass
class ExportConfig:
    """Configuration for export operations"""
    format: ExportFormat
    output_path: Optional[str] = None
    quality: ExportQuality = ExportQuality.HIGH
    
    # Image-specific settings
    width: Optional[int] = None
    height: Optional[int] = None
    dpi: int = 300
    compression: int = 6  # For PNG compression
    
    # Web export settings
    include_interactive: bool = True
    embed_data: bool = False
    include_styles: bool = True
    
    # Data export settings
    include_metadata: bool = True
    date_format: str = "%Y-%m-%d"
    float_precision: int = 2
    
    # Archive settings
    compress: bool = True
    password: Optional[str] = None
    
    # Custom options
    custom_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportResult:
    """Result of export operation"""
    success: bool
    output_path: Optional[str] = None
    output_data: Optional[bytes] = None
    output_text: Optional[str] = None  # For HTML/JSON exports
    file_size_bytes: int = 0
    export_format: Optional[ExportFormat] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    export_time_ms: float = 0
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class ExportEngineBase(ABC):
    """Abstract base class for export engines"""
    
    def __init__(self):
        self.supported_formats = self._get_supported_formats()
        self.temp_dir = Path("/tmp/data_viz_exports")
        self.temp_dir.mkdir(exist_ok=True)
        
    @abstractmethod
    def _get_supported_formats(self) -> List[ExportFormat]:
        """Return list of export formats supported by this engine"""
        pass
    
    @abstractmethod
    async def export(self, data: Any, config: ExportConfig) -> ExportResult:
        """Export data in the specified format"""
        pass
    
    def supports_format(self, export_format: ExportFormat) -> bool:
        """Check if this engine supports the given export format"""
        return export_format in self.supported_formats
    
    async def validate_config(self, config: ExportConfig) -> Dict[str, Any]:
        """Validate export configuration"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'recommendations': []
        }
        
        try:
            # Check format support
            if not self.supports_format(config.format):
                validation_result['errors'].append(
                    f"Export format {config.format.value} not supported"
                )
                validation_result['is_valid'] = False
            
            # Validate output path
            if config.output_path:
                output_path = Path(config.output_path)
                
                # Check if directory exists
                if not output_path.parent.exists():
                    validation_result['errors'].append(
                        f"Output directory does not exist: {output_path.parent}"
                    )
                    validation_result['is_valid'] = False
                
                # Check file extension matches format
                expected_ext = f".{config.format.value}"
                if not output_path.suffix.lower() == expected_ext:
                    validation_result['warnings'].append(
                        f"File extension {output_path.suffix} doesn't match format {expected_ext}"
                    )
            
            # Validate dimensions
            if config.width and config.width <= 0:
                validation_result['errors'].append("Width must be positive")
                validation_result['is_valid'] = False
            
            if config.height and config.height <= 0:
                validation_result['errors'].append("Height must be positive")
                validation_result['is_valid'] = False
            
            # Validate DPI
            if config.dpi <= 0:
                validation_result['errors'].append("DPI must be positive")
                validation_result['is_valid'] = False
            
            # Performance warnings
            if config.dpi > 600:
                validation_result['warnings'].append(
                    "Very high DPI may result in large file sizes and slow export"
                )
            
            if config.width and config.height and config.width * config.height > 16000000:  # 4000x4000
                validation_result['warnings'].append(
                    "Very large dimensions may result in memory issues"
                )
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def generate_filename(self, config: ExportConfig, prefix: str = "export") -> str:
        """Generate a filename for export"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = config.format.value
            
            # Handle special cases
            if config.format == ExportFormat.BASE64_PNG:
                extension = "png"
            elif config.format == ExportFormat.BASE64_SVG:
                extension = "svg"
            
            return f"{prefix}_{timestamp}.{extension}"
            
        except Exception as e:
            logger.error(f"Filename generation failed: {e}")
            return f"export.{config.format.value}"
    
    def get_quality_settings(self, quality: ExportQuality) -> Dict[str, Any]:
        """Get quality-specific settings"""
        quality_settings = {
            ExportQuality.LOW: {
                'dpi': 72,
                'compression': 9,
                'jpeg_quality': 60
            },
            ExportQuality.MEDIUM: {
                'dpi': 150,
                'compression': 6,
                'jpeg_quality': 80
            },
            ExportQuality.HIGH: {
                'dpi': 300,
                'compression': 3,
                'jpeg_quality': 95
            },
            ExportQuality.ULTRA: {
                'dpi': 600,
                'compression': 1,
                'jpeg_quality': 100
            }
        }
        
        return quality_settings.get(quality, quality_settings[ExportQuality.HIGH])
    
    def estimate_file_size(self, config: ExportConfig, 
                          data_complexity: str = "medium") -> int:
        """Estimate output file size in bytes"""
        try:
            base_sizes = {
                ExportFormat.PNG: 500000,  # 500KB base
                ExportFormat.JPG: 200000,  # 200KB base
                ExportFormat.SVG: 50000,   # 50KB base
                ExportFormat.PDF: 100000,  # 100KB base
                ExportFormat.HTML: 20000,  # 20KB base
                ExportFormat.JSON: 10000,  # 10KB base
                ExportFormat.CSV: 5000,    # 5KB base
                ExportFormat.EXCEL: 15000, # 15KB base
            }
            
            base_size = base_sizes.get(config.format, 50000)
            
            # Adjust for quality
            quality_multipliers = {
                ExportQuality.LOW: 0.3,
                ExportQuality.MEDIUM: 0.7,
                ExportQuality.HIGH: 1.0,
                ExportQuality.ULTRA: 2.5
            }
            
            quality_multiplier = quality_multipliers.get(config.quality, 1.0)
            
            # Adjust for dimensions
            dimension_multiplier = 1.0
            if config.width and config.height:
                # Base calculation on 800x600
                dimension_multiplier = (config.width * config.height) / (800 * 600)
            
            # Adjust for complexity
            complexity_multipliers = {
                "simple": 0.5,
                "medium": 1.0,
                "complex": 2.0
            }
            
            complexity_multiplier = complexity_multipliers.get(data_complexity, 1.0)
            
            estimated_size = int(base_size * quality_multiplier * dimension_multiplier * complexity_multiplier)
            
            return max(estimated_size, 1000)  # Minimum 1KB
            
        except Exception as e:
            logger.error(f"File size estimation failed: {e}")
            return 50000  # Default 50KB
    
    def _create_error_result(self, error_message: str, 
                           export_time_ms: float = 0,
                           export_format: ExportFormat = None) -> ExportResult:
        """Create error result"""
        return ExportResult(
            success=False,
            error_message=error_message,
            export_time_ms=export_time_ms,
            export_format=export_format
        )
    
    def _create_success_result(self, output_path: str = None,
                             output_data: bytes = None,
                             output_text: str = None,
                             export_format: ExportFormat = None,
                             export_time_ms: float = 0,
                             metadata: Dict[str, Any] = None,
                             warnings: List[str] = None) -> ExportResult:
        """Create success result"""
        file_size = 0
        if output_data:
            file_size = len(output_data)
        elif output_text:
            file_size = len(output_text.encode('utf-8'))
        elif output_path and Path(output_path).exists():
            file_size = Path(output_path).stat().st_size
        
        return ExportResult(
            success=True,
            output_path=output_path,
            output_data=output_data,
            output_text=output_text,
            file_size_bytes=file_size,
            export_format=export_format,
            export_time_ms=export_time_ms,
            metadata=metadata or {},
            warnings=warnings or []
        )
    
    async def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up temporary export files"""
        try:
            current_time = datetime.now()
            
            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file():
                    # Get file modification time
                    mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    age_hours = (current_time - mod_time).total_seconds() / 3600
                    
                    if age_hours > max_age_hours:
                        file_path.unlink()
                        logger.info(f"Cleaned up temp file: {file_path}")
                        
        except Exception as e:
            logger.error(f"Temp file cleanup failed: {e}")
    
    def get_export_recommendations(self, data_type: str, 
                                 intended_use: str) -> List[Dict[str, Any]]:
        """Get export format recommendations based on data and use case"""
        recommendations = []
        
        try:
            if intended_use == "web":
                recommendations.extend([
                    {
                        'format': ExportFormat.SVG,
                        'reason': 'Scalable vector format perfect for web display',
                        'score': 0.9
                    },
                    {
                        'format': ExportFormat.PNG,
                        'reason': 'High quality raster format with transparency support',
                        'score': 0.8
                    },
                    {
                        'format': ExportFormat.HTML,
                        'reason': 'Interactive format that can be embedded directly',
                        'score': 0.7
                    }
                ])
            
            elif intended_use == "print":
                recommendations.extend([
                    {
                        'format': ExportFormat.PDF,
                        'reason': 'Professional print format with vector support',
                        'score': 0.9
                    },
                    {
                        'format': ExportFormat.SVG,
                        'reason': 'Scalable vector format for any print size',
                        'score': 0.8
                    }
                ])
            
            elif intended_use == "presentation":
                recommendations.extend([
                    {
                        'format': ExportFormat.PNG,
                        'reason': 'Universal raster format for presentations',
                        'score': 0.9
                    },
                    {
                        'format': ExportFormat.SVG,
                        'reason': 'Scalable format that looks good at any size',
                        'score': 0.8
                    }
                ])
            
            elif intended_use == "data_sharing":
                recommendations.extend([
                    {
                        'format': ExportFormat.CSV,
                        'reason': 'Universal data format readable by any tool',
                        'score': 0.9
                    },
                    {
                        'format': ExportFormat.EXCEL,
                        'reason': 'Rich format with formatting and multiple sheets',
                        'score': 0.8
                    },
                    {
                        'format': ExportFormat.JSON,
                        'reason': 'Structured data format for programmatic use',
                        'score': 0.7
                    }
                ])
            
            # Sort by score
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            
        except Exception as e:
            logger.error(f"Export recommendations failed: {e}")
        
        return recommendations
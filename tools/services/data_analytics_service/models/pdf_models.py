#!/usr/bin/env python3
"""
PDF Service Data Models

PDF服务专用的数据模型
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from .base_models import ProcessingRequest, ProcessingResult, AssetType

@dataclass
class PDFProcessingRequest(ProcessingRequest):
    """PDF处理请求"""
    # 继承基础请求，添加PDF特定选项
    extract_text: bool = True
    extract_images: bool = True
    extract_tables: bool = True
    analyze_layout: bool = True
    generate_summary: bool = True
    
    def __post_init__(self):
        # 确保asset_type是PDF类型
        if self.asset_type not in [AssetType.PDF_NATIVE, AssetType.PDF_SCANNED]:
            raise ValueError(f"Invalid asset_type for PDF service: {self.asset_type}")

@dataclass
class PDFMetadata:
    """PDF元数据"""
    page_count: int
    file_size: int
    pdf_version: str
    title: str = ""
    author: str = ""
    subject: str = ""
    creator: str = ""
    producer: str = ""
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    is_encrypted: bool = False
    is_scanned: bool = False

@dataclass
class PDFPageInfo:
    """PDF页面信息"""
    page_number: int
    width: float
    height: float
    rotation: int = 0
    has_text: bool = False
    has_images: bool = False
    has_tables: bool = False
    text_blocks_count: int = 0
    images_count: int = 0

@dataclass
class PDFTextExtraction:
    """PDF文本提取结果"""
    full_text: str
    page_texts: List[str]
    text_blocks: List[Dict[str, Any]] = field(default_factory=list)
    extraction_method: str = "native"  # "native", "ocr", "hybrid"
    confidence: float = 1.0
    language: str = "unknown"

@dataclass
class PDFImageExtraction:
    """PDF图像提取结果"""
    total_images: int
    extracted_images: List[Dict[str, Any]] = field(default_factory=list)
    image_analysis: List[Dict[str, Any]] = field(default_factory=list)
    extraction_method: str = "native"

@dataclass
class PDFTableExtraction:
    """PDF表格提取结果"""
    total_tables: int
    extracted_tables: List[Dict[str, Any]] = field(default_factory=list)
    table_analysis: List[Dict[str, Any]] = field(default_factory=list)
    extraction_method: str = "native"  # "native", "transformer", "ocr"

@dataclass
class PDFLayoutAnalysis:
    """PDF布局分析结果"""
    layout_type: str  # "single_column", "multi_column", "complex"
    reading_order: List[Dict[str, Any]] = field(default_factory=list)
    regions: List[Dict[str, Any]] = field(default_factory=list)
    complexity_score: float = 0.0
    processing_recommendations: List[str] = field(default_factory=list)

@dataclass
class PDFSummary:
    """PDF摘要"""
    executive_summary: str
    key_points: List[str]
    main_topics: List[str]
    entities: List[Dict[str, Any]] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)
    confidence: float = 0.0

@dataclass
class PDFProcessingResult(ProcessingResult):
    """PDF处理结果"""
    # 继承基础结果，添加PDF特定数据
    pdf_metadata: Optional[PDFMetadata] = None
    page_info: List[PDFPageInfo] = field(default_factory=list)
    text_extraction: Optional[PDFTextExtraction] = None
    image_extraction: Optional[PDFImageExtraction] = None
    table_extraction: Optional[PDFTableExtraction] = None
    layout_analysis: Optional[PDFLayoutAnalysis] = None
    summary: Optional[PDFSummary] = None
    
    # 三层处理结果
    preprocessing_result: Optional[Dict[str, Any]] = None
    processing_result: Optional[Dict[str, Any]] = None
    extraction_result: Optional[Dict[str, Any]] = None

@dataclass
class PDFServiceOptions:
    """PDF服务选项"""
    # Layer 1 选项
    detect_pdf_type: bool = True
    analyze_quality: bool = True
    
    # Layer 2 选项
    ocr_language: str = "auto"
    table_detection_model: str = "default"
    image_analysis_model: str = "gpt-4.1-nano"
    
    # Layer 3 选项
    summary_type: str = "executive"  # "executive", "detailed", "technical"
    summary_length: str = "medium"   # "brief", "medium", "detailed"
    extract_entities: bool = True
    extract_themes: bool = True
    
    # 性能选项
    max_pages_to_process: Optional[int] = None
    enable_parallel_processing: bool = True
    cache_results: bool = True
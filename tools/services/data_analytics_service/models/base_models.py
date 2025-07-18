#!/usr/bin/env python3
"""
Base Data Models for Digital Analytics Service

定义数字分析服务的基础数据模型
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class AssetType(Enum):
    """数字资产类型"""
    PDF_NATIVE = "pdf_native"
    PDF_SCANNED = "pdf_scanned"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    POWERPOINT = "powerpoint"
    UNKNOWN = "unknown"

class ProcessingStatus(Enum):
    """处理状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ServiceType(Enum):
    """服务类型"""
    PDF_SERVICE = "pdf_service"
    IMAGE_SERVICE = "image_service"
    AUDIO_SERVICE = "audio_service"
    VIDEO_SERVICE = "video_service"
    DOCUMENT_SERVICE = "document_service"

@dataclass
class ProcessingRequest:
    """处理请求模型"""
    asset_path: str
    asset_type: AssetType
    service_type: ServiceType
    options: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(datetime.now().timestamp()))
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ProcessingResult:
    """处理结果模型"""
    request_id: str
    success: bool
    status: ProcessingStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

@dataclass
class LayerResult:
    """单层处理结果"""
    layer_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ServiceCapabilities:
    """服务能力描述"""
    service_name: str
    version: str
    supported_asset_types: List[AssetType]
    supported_operations: List[str]
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ServiceHealth:
    """服务健康状态"""
    service_name: str
    status: str  # "healthy", "degraded", "unhealthy"
    last_check: datetime
    dependencies_status: Dict[str, str] = field(default_factory=dict)
    error_message: Optional[str] = None
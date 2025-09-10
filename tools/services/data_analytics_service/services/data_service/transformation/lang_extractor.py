#!/usr/bin/env python3
"""
Language Data Extractor Service
基于Google LangExtract架构设计，充分复用现有intelligence_service的统一非结构化数据提取服务

实际可用服务:
- text_extractor.py (714行) - 实体提取、关键信息、分类、情感分析
- text_summarizer.py (496行) - 专业摘要服务  
- embedding_generator.py (1534行) - 文本分块 + 向量化
- text_generator.py (124行) - 基础文本生成

设计特点:
- 复用现有服务，避免重复实现
- 统一的提取接口
- 可插拔的提取器架构
- 智能文档分块和并行处理
- 精确的源位置追踪
"""

import asyncio
from typing import Dict, List, Any, Optional, Union, Type
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum
import logging

# 导入现有的AI服务
from tools.services.intelligence_service.language.text_extractor import TextExtractor
from tools.services.intelligence_service.language.text_summarizer import TextSummarizer
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator
from tools.services.intelligence_service.language.text_generator import TextGenerator

logger = logging.getLogger(__name__)

class ExtractionType(Enum):
    """提取类型枚举"""
    ENTITIES = "entities"                    # 命名实体识别
    CLASSIFICATION = "classification"        # 文本分类
    KEY_INFORMATION = "key_information"      # 关键信息提取
    SUMMARY = "summary"                      # 文本摘要
    SENTIMENT = "sentiment"                  # 情感分析
    TOPICS = "topics"                        # 主题提取
    CHUNKS = "chunks"                        # 文本分块
    GENERATION = "generation"                # 文本生成

@dataclass
class SourceLocation:
    """源文档位置信息"""
    start_char: int
    end_char: int
    line_number: Optional[int] = None
    chunk_id: Optional[str] = None
    source_text: Optional[str] = None

@dataclass
class ExtractionResult:
    """统一的提取结果格式"""
    success: bool
    data: Dict[str, Any]
    confidence: float
    source_locations: List[SourceLocation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    extraction_type: str = ""
    error_message: Optional[str] = None
    
@dataclass 
class ExtractionConfig:
    """提取配置"""
    extraction_type: ExtractionType
    schema: Optional[Dict[str, Any]] = None
    chunk_size: int = 3000
    chunk_overlap: int = 200
    max_workers: int = 5
    confidence_threshold: float = 0.7
    enable_source_grounding: bool = True
    custom_instructions: Optional[str] = None

class BaseServiceProvider(ABC):
    """基础服务提供者抽象类"""
    
    @abstractmethod
    def supports_extraction_type(self, extraction_type: ExtractionType) -> bool:
        """检查是否支持特定提取类型"""
        pass
    
    @abstractmethod
    async def extract(self, text: str, config: ExtractionConfig) -> ExtractionResult:
        """执行提取操作"""
        pass

class TextExtractorProvider(BaseServiceProvider):
    """基于现有TextExtractor的服务提供者"""
    
    def __init__(self):
        self.service = TextExtractor()
        self.supported_types = {
            ExtractionType.ENTITIES,
            ExtractionType.CLASSIFICATION, 
            ExtractionType.KEY_INFORMATION,
            ExtractionType.SENTIMENT
        }
    
    def supports_extraction_type(self, extraction_type: ExtractionType) -> bool:
        return extraction_type in self.supported_types
    
    async def extract(self, text: str, config: ExtractionConfig) -> ExtractionResult:
        """使用TextExtractor执行提取"""
        start_time = datetime.utcnow()
        
        try:
            if config.extraction_type == ExtractionType.ENTITIES:
                result = await self.service.extract_entities(
                    text=text,
                    confidence_threshold=config.confidence_threshold
                )
            elif config.extraction_type == ExtractionType.CLASSIFICATION:
                if not config.schema or 'categories' not in config.schema:
                    raise ValueError("Classification requires 'categories' in schema")
                result = await self.service.classify_text(
                    text=text,
                    categories=config.schema['categories'],
                    multi_label=config.schema.get('multi_label', False)
                )
            elif config.extraction_type == ExtractionType.KEY_INFORMATION:
                result = await self.service.extract_key_information(
                    text=text,
                    schema=config.schema
                )
            elif config.extraction_type == ExtractionType.SENTIMENT:
                result = await self.service.analyze_sentiment(
                    text=text,
                    granularity=config.schema.get('granularity', 'overall') if config.schema else 'overall'
                )
            else:
                raise ValueError(f"Unsupported extraction type: {config.extraction_type}")
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ExtractionResult(
                success=result.get('success', True),
                data=result.get('data', {}),
                confidence=result.get('confidence', 0.0),
                source_locations=self._generate_source_locations(text) if config.enable_source_grounding else [],
                metadata={
                    'provider': 'TextExtractorProvider',
                    'billing_info': result.get('billing_info', {}),
                    'service_used': 'text_extractor'
                },
                processing_time_ms=processing_time,
                extraction_type=config.extraction_type.value,
                error_message=result.get('error') if not result.get('success', True) else None
            )
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"TextExtractor提取失败: {e}")
            return ExtractionResult(
                success=False,
                data={},
                confidence=0.0,
                metadata={'provider': 'TextExtractorProvider', 'service_used': 'text_extractor'},
                processing_time_ms=processing_time,
                extraction_type=config.extraction_type.value,
                error_message=str(e)
            )
    
    def _generate_source_locations(self, text: str) -> List[SourceLocation]:
        """生成源位置信息"""
        return [SourceLocation(
            start_char=0,
            end_char=len(text),
            line_number=1,
            source_text=text[:100] + "..." if len(text) > 100 else text
        )]

class TextSummarizerProvider(BaseServiceProvider):
    """基于现有TextSummarizer的服务提供者"""
    
    def __init__(self):
        self.service = TextSummarizer()
        self.supported_types = {ExtractionType.SUMMARY, ExtractionType.TOPICS}
    
    def supports_extraction_type(self, extraction_type: ExtractionType) -> bool:
        return extraction_type in self.supported_types
    
    async def extract(self, text: str, config: ExtractionConfig) -> ExtractionResult:
        """使用TextSummarizer执行提取"""
        start_time = datetime.utcnow()
        
        try:
            if config.extraction_type == ExtractionType.SUMMARY:
                # 使用text_summarizer的summarize方法
                length = config.schema.get('length', 'medium') if config.schema else 'medium'
                style = config.schema.get('style', 'detailed') if config.schema else 'detailed'
                focus_areas = config.schema.get('focus_areas') if config.schema else None
                
                result = await self.service.summarize(
                    text=text,
                    style=style,
                    length=length,
                    focus_areas=focus_areas
                )
            elif config.extraction_type == ExtractionType.TOPICS:
                # 使用extract_key_points来提取主题
                max_points = config.schema.get('max_topics', 10) if config.schema else 10
                result = await self.service.extract_key_points(
                    text=text,
                    max_points=max_points
                )
            else:
                raise ValueError(f"Unsupported extraction type: {config.extraction_type}")
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ExtractionResult(
                success=result.get('success', True),
                data=result.get('data', {}),
                confidence=result.get('confidence', 0.8),
                source_locations=self._generate_source_locations(text) if config.enable_source_grounding else [],
                metadata={
                    'provider': 'TextSummarizerProvider',
                    'billing_info': result.get('billing_info', {}),
                    'service_used': 'text_summarizer'
                },
                processing_time_ms=processing_time,
                extraction_type=config.extraction_type.value,
                error_message=result.get('error') if not result.get('success', True) else None
            )
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"TextSummarizer提取失败: {e}")
            return ExtractionResult(
                success=False,
                data={},
                confidence=0.0,
                metadata={'provider': 'TextSummarizerProvider', 'service_used': 'text_summarizer'},
                processing_time_ms=processing_time,
                extraction_type=config.extraction_type.value,
                error_message=str(e)
            )
    
    def _generate_source_locations(self, text: str) -> List[SourceLocation]:
        """生成源位置信息"""
        return [SourceLocation(
            start_char=0,
            end_char=len(text),
            line_number=1,
            source_text=text[:100] + "..." if len(text) > 100 else text
        )]

class EmbeddingGeneratorProvider(BaseServiceProvider):
    """基于现有EmbeddingGenerator的服务提供者 - 主要用于分块"""
    
    def __init__(self):
        self.service = EmbeddingGenerator()
        self.supported_types = {ExtractionType.CHUNKS}
    
    def supports_extraction_type(self, extraction_type: ExtractionType) -> bool:
        return extraction_type in self.supported_types
    
    async def extract(self, text: str, config: ExtractionConfig) -> ExtractionResult:
        """使用EmbeddingGenerator执行分块"""
        start_time = datetime.utcnow()
        
        try:
            if config.extraction_type == ExtractionType.CHUNKS:
                # 使用embedding_generator的chunk_text方法
                chunks = await self.service.chunk_text(
                    text=text,
                    chunk_size=config.chunk_size,
                    overlap=config.chunk_overlap,
                    metadata=config.schema.get('metadata') if config.schema else None
                )
                
                result = {
                    'success': True,
                    'data': {'chunks': chunks},
                    'confidence': 1.0  # 分块是确定性操作
                }
            else:
                raise ValueError(f"Unsupported extraction type: {config.extraction_type}")
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ExtractionResult(
                success=result.get('success', True),
                data=result.get('data', {}),
                confidence=result.get('confidence', 1.0),
                source_locations=self._generate_chunk_locations(chunks) if config.enable_source_grounding else [],
                metadata={
                    'provider': 'EmbeddingGeneratorProvider',
                    'service_used': 'embedding_generator',
                    'chunks_count': len(chunks)
                },
                processing_time_ms=processing_time,
                extraction_type=config.extraction_type.value
            )
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"EmbeddingGenerator分块失败: {e}")
            return ExtractionResult(
                success=False,
                data={},
                confidence=0.0,
                metadata={'provider': 'EmbeddingGeneratorProvider', 'service_used': 'embedding_generator'},
                processing_time_ms=processing_time,
                extraction_type=config.extraction_type.value,
                error_message=str(e)
            )
    
    def _generate_chunk_locations(self, chunks: List[Dict]) -> List[SourceLocation]:
        """为分块生成源位置信息"""
        locations = []
        for i, chunk in enumerate(chunks):
            if isinstance(chunk, dict):
                locations.append(SourceLocation(
                    start_char=chunk.get('start_char', 0),
                    end_char=chunk.get('end_char', 0),
                    chunk_id=f"chunk_{i}",
                    source_text=chunk.get('text', '')[:50] + "..." if len(chunk.get('text', '')) > 50 else chunk.get('text', '')
                ))
        return locations

class TextGeneratorProvider(BaseServiceProvider):
    """基于现有TextGenerator的服务提供者"""
    
    def __init__(self):
        self.service = TextGenerator()
        self.supported_types = {ExtractionType.GENERATION}
    
    def supports_extraction_type(self, extraction_type: ExtractionType) -> bool:
        return extraction_type in self.supported_types
    
    async def extract(self, text: str, config: ExtractionConfig) -> ExtractionResult:
        """使用TextGenerator执行生成"""
        start_time = datetime.utcnow()
        
        try:
            if config.extraction_type == ExtractionType.GENERATION:
                # 构建生成提示
                if config.custom_instructions:
                    prompt = f"{config.custom_instructions}\n\nText: {text}"
                else:
                    prompt = text
                
                generated_text = await self.service.generate(
                    prompt=prompt,
                    temperature=config.schema.get('temperature', 0.7) if config.schema else 0.7,
                    max_tokens=config.schema.get('max_tokens') if config.schema else None
                )
                
                result = {
                    'success': True,
                    'data': {'generated_text': generated_text},
                    'confidence': 0.8
                }
            else:
                raise ValueError(f"Unsupported extraction type: {config.extraction_type}")
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ExtractionResult(
                success=result.get('success', True),
                data=result.get('data', {}),
                confidence=result.get('confidence', 0.8),
                source_locations=[],  # 生成的内容没有源位置
                metadata={
                    'provider': 'TextGeneratorProvider',
                    'service_used': 'text_generator'
                },
                processing_time_ms=processing_time,
                extraction_type=config.extraction_type.value
            )
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"TextGenerator生成失败: {e}")
            return ExtractionResult(
                success=False,
                data={},
                confidence=0.0,
                metadata={'provider': 'TextGeneratorProvider', 'service_used': 'text_generator'},
                processing_time_ms=processing_time,
                extraction_type=config.extraction_type.value,
                error_message=str(e)
            )

class ServiceRegistry:
    """服务注册中心 - 管理所有可用的服务提供者"""
    
    def __init__(self):
        self._providers: Dict[str, BaseServiceProvider] = {}
        self._type_mappings: Dict[ExtractionType, List[str]] = {}
        
        # 注册所有可用的服务
        self._register_default_providers()
    
    def _register_default_providers(self):
        """注册默认的服务提供者"""
        # TextExtractor: 实体、分类、关键信息、情感分析
        text_extractor = TextExtractorProvider()
        self.register("text_extractor", text_extractor)
        
        # TextSummarizer: 摘要、主题提取
        text_summarizer = TextSummarizerProvider()
        self.register("text_summarizer", text_summarizer)
        
        # EmbeddingGenerator: 文本分块
        embedding_generator = EmbeddingGeneratorProvider()
        self.register("embedding_generator", embedding_generator)
        
        # TextGenerator: 文本生成
        text_generator = TextGeneratorProvider()
        self.register("text_generator", text_generator)
        
        logger.info("已注册所有默认服务提供者")
    
    def register(self, name: str, provider: BaseServiceProvider):
        """注册新的服务提供者"""
        self._providers[name] = provider
        
        # 更新类型映射
        for extraction_type in ExtractionType:
            if provider.supports_extraction_type(extraction_type):
                if extraction_type not in self._type_mappings:
                    self._type_mappings[extraction_type] = []
                self._type_mappings[extraction_type].append(name)
        
        logger.info(f"注册服务提供者: {name}")
    
    def get_provider(self, name: str) -> BaseServiceProvider:
        """获取指定的服务提供者"""
        if name not in self._providers:
            raise ValueError(f"未知的服务提供者: {name}")
        return self._providers[name]
    
    def get_suitable_provider(self, extraction_type: ExtractionType) -> BaseServiceProvider:
        """获取适合指定提取类型的服务提供者"""
        if extraction_type not in self._type_mappings:
            raise ValueError(f"没有服务提供者支持提取类型: {extraction_type}")
        
        # 返回第一个支持的提供者
        provider_name = self._type_mappings[extraction_type][0]
        return self._providers[provider_name]
    
    def list_providers(self) -> List[str]:
        """列出所有可用的服务提供者"""
        return list(self._providers.keys())
    
    def list_supported_types(self) -> Dict[str, List[str]]:
        """列出每个提供者支持的提取类型"""
        result = {}
        for name, provider in self._providers.items():
            supported = []
            for extraction_type in ExtractionType:
                if provider.supports_extraction_type(extraction_type):
                    supported.append(extraction_type.value)
            result[name] = supported
        return result

class LangExtractor:
    """
    主要的语言提取服务类 - 基于Google LangExtract架构，充分复用现有intelligence服务
    
    特点:
    - 复用现有TextExtractor、TextSummarizer、EmbeddingGenerator、TextGenerator服务
    - 统一的提取接口
    - 可插拔的服务架构
    - 智能文档处理
    - 并行处理支持
    """
    
    def __init__(self):
        self.registry = ServiceRegistry()
    
    async def extract(
        self,
        text: str,
        extraction_type: Union[ExtractionType, str],
        schema: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        """
        主要的提取方法
        
        Args:
            text: 要提取的文本
            extraction_type: 提取类型
            schema: 提取模式定义
            provider: 指定服务提供者
            **kwargs: 其他配置参数
            
        Returns:
            提取结果
        """
        # 规范化提取类型
        if isinstance(extraction_type, str):
            try:
                extraction_type = ExtractionType(extraction_type)
            except ValueError:
                raise ValueError(f"不支持的提取类型: {extraction_type}")
        
        # 创建配置
        config = ExtractionConfig(
            extraction_type=extraction_type,
            schema=schema or {},
            **{k: v for k, v in kwargs.items() if k in ExtractionConfig.__dataclass_fields__}
        )
        
        # 获取适合的服务提供者
        if provider:
            service_provider = self.registry.get_provider(provider)
        else:
            service_provider = self.registry.get_suitable_provider(extraction_type)
        
        # 执行提取
        if len(text) > config.chunk_size and extraction_type != ExtractionType.CHUNKS:
            return await self._extract_from_chunks(text, config, service_provider)
        else:
            return await service_provider.extract(text, config)
    
    # 便利方法
    async def extract_entities(self, text: str, **kwargs) -> ExtractionResult:
        """提取命名实体"""
        return await self.extract(text, ExtractionType.ENTITIES, **kwargs)
    
    async def classify_text(self, text: str, categories: List[str], **kwargs) -> ExtractionResult:
        """文本分类"""
        schema = {'categories': categories, 'multi_label': kwargs.pop('multi_label', False)}
        return await self.extract(text, ExtractionType.CLASSIFICATION, schema=schema, **kwargs)
    
    async def extract_key_information(self, text: str, schema: Dict[str, Any], **kwargs) -> ExtractionResult:
        """提取关键信息"""
        return await self.extract(text, ExtractionType.KEY_INFORMATION, schema=schema, **kwargs)
    
    async def summarize(self, text: str, length: str = "medium", style: str = "detailed", focus_areas: Optional[List[str]] = None, **kwargs) -> ExtractionResult:
        """文本摘要"""
        schema = {'length': length, 'style': style, 'focus_areas': focus_areas}
        return await self.extract(text, ExtractionType.SUMMARY, schema=schema, **kwargs)
    
    async def analyze_sentiment(self, text: str, granularity: str = "overall", **kwargs) -> ExtractionResult:
        """情感分析"""
        schema = {'granularity': granularity}
        return await self.extract(text, ExtractionType.SENTIMENT, schema=schema, **kwargs)
    
    async def extract_topics(self, text: str, max_topics: int = 10, **kwargs) -> ExtractionResult:
        """提取主题"""
        schema = {'max_topics': max_topics}
        return await self.extract(text, ExtractionType.TOPICS, schema=schema, **kwargs)
    
    async def chunk_text(self, text: str, chunk_size: int = 3000, overlap: int = 200, **kwargs) -> ExtractionResult:
        """文本分块"""
        return await self.extract(text, ExtractionType.CHUNKS, chunk_size=chunk_size, chunk_overlap=overlap, **kwargs)
    
    async def generate_text(self, text: str, instructions: str, temperature: float = 0.7, **kwargs) -> ExtractionResult:
        """文本生成"""
        schema = {'temperature': temperature}
        return await self.extract(text, ExtractionType.GENERATION, schema=schema, custom_instructions=instructions, **kwargs)
    
    async def batch_extract(
        self,
        texts: List[str],
        extraction_type: Union[ExtractionType, str],
        schema: Optional[Dict[str, Any]] = None,
        max_workers: int = 5,
        **kwargs
    ) -> List[ExtractionResult]:
        """批量提取"""
        semaphore = asyncio.Semaphore(max_workers)
        
        async def extract_single(text: str) -> ExtractionResult:
            async with semaphore:
                return await self.extract(text, extraction_type, schema, **kwargs)
        
        tasks = [extract_single(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ExtractionResult(
                    success=False,
                    data={},
                    confidence=0.0,
                    extraction_type=str(extraction_type),
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def register_provider(self, name: str, provider: BaseServiceProvider):
        """注册自定义服务提供者"""
        self.registry.register(name, provider)
    
    def get_available_services(self) -> Dict[str, Any]:
        """获取所有可用服务信息"""
        return {
            'providers': self.registry.list_providers(),
            'supported_types': self.registry.list_supported_types(),
            'extraction_types': [t.value for t in ExtractionType]
        }
    
    async def _extract_from_chunks(
        self,
        text: str,
        config: ExtractionConfig,
        provider: BaseServiceProvider
    ) -> ExtractionResult:
        """从分块文本中提取信息 - 使用EmbeddingGenerator进行分块"""
        # 使用embedding_generator进行分块
        chunker = EmbeddingGeneratorProvider()
        chunk_config = ExtractionConfig(
            extraction_type=ExtractionType.CHUNKS,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )
        
        chunk_result = await chunker.extract(text, chunk_config)
        if not chunk_result.success:
            return chunk_result
        
        chunks = chunk_result.data.get('chunks', [])
        
        # 并行处理多个块
        semaphore = asyncio.Semaphore(config.max_workers)
        
        async def extract_chunk(chunk: Dict[str, Any]) -> ExtractionResult:
            async with semaphore:
                chunk_text = chunk.get('text', '')
                result = await provider.extract(chunk_text, config)
                # 调整源位置信息
                if result.source_locations and 'start_char' in chunk:
                    for location in result.source_locations:
                        location.start_char += chunk.get('start_char', 0)
                        location.end_char += chunk.get('start_char', 0)
                        location.chunk_id = chunk.get('id', f"chunk_{chunk}")
                return result
        
        tasks = [extract_chunk(chunk) for chunk in chunks]
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        return self._merge_chunk_results(chunk_results, config)
    
    def _merge_chunk_results(self, chunk_results: List[ExtractionResult], config: ExtractionConfig) -> ExtractionResult:
        """合并块提取结果"""
        valid_results = [r for r in chunk_results if isinstance(r, ExtractionResult) and r.success]
        
        if not valid_results:
            return ExtractionResult(
                success=False,
                data={},
                confidence=0.0,
                extraction_type=config.extraction_type.value,
                error_message="All chunks failed to process"
            )
        
        # 合并策略根据提取类型调整
        merged_data = {}
        all_source_locations = []
        total_processing_time = 0.0
        confidences = []
        
        for result in valid_results:
            confidences.append(result.confidence)
            all_source_locations.extend(result.source_locations)
            total_processing_time += result.processing_time_ms
            
            # 根据类型合并数据
            if config.extraction_type == ExtractionType.ENTITIES:
                entities = result.data.get('entities', {})
                for entity_type, entity_list in entities.items():
                    if entity_type not in merged_data:
                        merged_data[entity_type] = []
                    merged_data[entity_type].extend(entity_list)
            elif config.extraction_type == ExtractionType.SUMMARY:
                # 摘要类型：连接所有摘要
                if 'summary' not in merged_data:
                    merged_data['summaries'] = []
                merged_data['summaries'].append(result.data.get('summary', ''))
            else:
                # 其他类型简单合并
                for key, value in result.data.items():
                    if key not in merged_data:
                        merged_data[key] = []
                    if isinstance(value, list):
                        merged_data[key].extend(value)
                    else:
                        merged_data[key].append(value)
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return ExtractionResult(
            success=True,
            data=merged_data,
            confidence=avg_confidence,
            source_locations=all_source_locations,
            metadata={
                'chunks_processed': len(valid_results),
                'merge_strategy': f'{config.extraction_type.value}_merge',
                'total_chunks': len(chunk_results)
            },
            processing_time_ms=total_processing_time,
            extraction_type=config.extraction_type.value
        )

# 全局实例
lang_extractor = LangExtractor()

# 便利函数
async def extract_entities(text: str, **kwargs) -> ExtractionResult:
    """提取命名实体"""
    return await lang_extractor.extract_entities(text, **kwargs)

async def classify_text(text: str, categories: List[str], **kwargs) -> ExtractionResult:
    """文本分类"""
    return await lang_extractor.classify_text(text, categories, **kwargs)

async def extract_key_information(text: str, schema: Dict[str, Any], **kwargs) -> ExtractionResult:
    """提取关键信息"""
    return await lang_extractor.extract_key_information(text, schema, **kwargs)

async def summarize(text: str, **kwargs) -> ExtractionResult:
    """文本摘要"""
    return await lang_extractor.summarize(text, **kwargs)

async def analyze_sentiment(text: str, **kwargs) -> ExtractionResult:
    """情感分析"""
    return await lang_extractor.analyze_sentiment(text, **kwargs)

async def extract_topics(text: str, **kwargs) -> ExtractionResult:
    """提取主题"""
    return await lang_extractor.extract_topics(text, **kwargs)

async def chunk_text(text: str, **kwargs) -> ExtractionResult:
    """文本分块"""
    return await lang_extractor.chunk_text(text, **kwargs)

async def batch_extract(texts: List[str], extraction_type: str, schema: Optional[Dict[str, Any]] = None, **kwargs) -> List[ExtractionResult]:
    """批量提取"""
    return await lang_extractor.batch_extract(texts, extraction_type, schema, **kwargs)

def get_available_services() -> Dict[str, Any]:
    """获取可用服务信息"""
    return lang_extractor.get_available_services()
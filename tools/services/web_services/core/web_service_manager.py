#!/usr/bin/env python
"""
Web Service Manager for Web Services
Centralized management of all web services with proper lifecycle management
"""
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.logging import get_logger
from core.config import get_settings

# Core services
from .browser_manager import BrowserManager
from .session_manager import SessionManager
from .stealth_manager import StealthManager

# Engines
from ..engines.search_engine import SearchEngine, SearchProvider, BraveSearchStrategy
from ..engines.extraction_engine import ExtractionEngine

# Strategies
from ..strategies.extraction import LLMExtractionStrategy, PredefinedLLMSchemas
from ..strategies.filtering import SemanticFilter

# Utils
from ..utils.rate_limiter import RateLimiter
from ..utils.human_behavior import HumanBehavior

# Optional advanced components
try:
    from ..strategies.detection.intelligent_element_detector import IntelligentElementDetector
    from ..strategies.filtering import AICompositeFilter as AIEnhancedFilter, BM25Filter
except ImportError as e:
    logger.warning(f"Could not import advanced components: {e}")
    IntelligentElementDetector = None
    AIEnhancedFilter = None
    BM25Filter = None

logger = get_logger(__name__)

class WebServiceManager:
    """Centralized manager for all web services"""
    
    def __init__(self):
        self.initialized = False
        self.services: Dict[str, Any] = {}
        self.initialization_order = [
            'rate_limiter',
            'human_behavior', 
            'browser_manager',
            'session_manager',
            'stealth_manager',
            'search_engine',
            'extraction_engine',
            'shared_llm_extractor',
            'element_detector',
            'ai_filter',
            'bm25_filter'
        ]
        
    async def initialize(self):
        """Initialize all services in proper order"""
        if self.initialized:
            return
            
        logger.info("🔧 Initializing Web Service Manager...")
        
        try:
            # Initialize core services
            await self._initialize_core_services()
            
            # Initialize engines
            await self._initialize_engines()
            
            # Initialize strategies
            await self._initialize_strategies()
            
            # Initialize advanced components
            await self._initialize_advanced_components()
            
            self.initialized = True
            logger.info("✅ Web Service Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Web Service Manager: {e}")
            raise
    
    async def _initialize_core_services(self):
        """Initialize core services"""
        logger.info("🔧 Initializing core services...")
        
        # Rate limiter
        self.services['rate_limiter'] = RateLimiter()
        logger.info("✅ Rate Limiter initialized")
        
        # Human behavior simulator
        self.services['human_behavior'] = HumanBehavior()
        logger.info("✅ Human Behavior simulator initialized")
        
        # Browser manager
        self.services['browser_manager'] = BrowserManager()
        logger.info("✅ Browser Manager initialized")
        
        # Session manager
        self.services['session_manager'] = SessionManager(self.services['browser_manager'])
        logger.info("✅ Session Manager initialized")
        
        # Stealth manager
        self.services['stealth_manager'] = StealthManager()
        logger.info("✅ Stealth Manager initialized")
    
    async def _initialize_engines(self):
        """Initialize engine services"""
        logger.info("🔧 Initializing engines...")
        
        # Search engine
        self.services['search_engine'] = SearchEngine()
        
        # Configure search strategies
        settings = get_settings()
        brave_api_key = settings.brave_api_key
        if brave_api_key:
            brave_strategy = BraveSearchStrategy(brave_api_key)
            self.services['search_engine'].register_strategy(SearchProvider.BRAVE, brave_strategy)
            logger.info(f"✅ Brave search strategy registered")
        else:
            logger.warning("⚠️ BRAVE_TOKEN not found in configuration")
        
        # Extraction engine
        self.services['extraction_engine'] = ExtractionEngine()
        logger.info("✅ Extraction Engine initialized")
    
    async def _initialize_strategies(self):
        """Initialize strategy services"""
        logger.info("🔧 Initializing strategies...")
        
        # Shared LLM extractor
        article_schema = PredefinedLLMSchemas.get_article_extraction_schema()
        self.services['shared_llm_extractor'] = LLMExtractionStrategy(article_schema)
        logger.info("✅ Shared LLM Extractor initialized")
        
        # Semantic filter
        self.services['semantic_filter'] = SemanticFilter()
        logger.info("✅ Semantic Filter initialized")
    
    async def _initialize_advanced_components(self):
        """Initialize advanced automation components"""
        logger.info("🔧 Initializing advanced components...")
        
        # Intelligent element detector
        if IntelligentElementDetector:
            self.services['element_detector'] = IntelligentElementDetector()
            logger.info("✅ Intelligent Element Detector initialized")
        else:
            logger.warning("⚠️ IntelligentElementDetector not available")
        
        # AI enhanced filter (skip for now due to initialization complexity)
        # if AIEnhancedFilter:
        #     self.services['ai_filter'] = AIEnhancedFilter()
        #     logger.info("✅ AI Enhanced Filter initialized")
        
        # BM25 filter
        if BM25Filter:
            self.services['bm25_filter'] = BM25Filter()
            logger.info("✅ BM25 Filter initialized")
    
    def get_service(self, service_name: str) -> Any:
        """Get a service by name"""
        if not self.initialized:
            raise RuntimeError("WebServiceManager not initialized")
            
        if service_name not in self.services:
            raise ValueError(f"Service '{service_name}' not found")
            
        return self.services[service_name]
    
    def get_search_engine(self) -> SearchEngine:
        """Get the search engine service"""
        return self.get_service('search_engine')
    
    def get_browser_manager(self) -> BrowserManager:
        """Get the browser manager service"""
        return self.get_service('browser_manager')
    
    def get_session_manager(self) -> SessionManager:
        """Get the session manager service"""
        return self.get_service('session_manager')
    
    def get_stealth_manager(self) -> StealthManager:
        """Get the stealth manager service"""
        return self.get_service('stealth_manager')
    
    def get_extraction_engine(self) -> ExtractionEngine:
        """Get the extraction engine service"""
        return self.get_service('extraction_engine')
    
    def get_shared_llm_extractor(self) -> LLMExtractionStrategy:
        """Get the shared LLM extractor"""
        return self.get_service('shared_llm_extractor')
    
    def get_rate_limiter(self) -> RateLimiter:
        """Get the rate limiter service"""
        return self.get_service('rate_limiter')
    
    def get_human_behavior(self) -> HumanBehavior:
        """Get the human behavior service"""
        return self.get_service('human_behavior')
    
    def get_element_detector(self) -> Optional[Any]:
        """Get the element detector service if available"""
        return self.services.get('element_detector')
    
    def get_ai_filter(self) -> Optional[Any]:
        """Get the AI filter service if available"""
        return self.services.get('ai_filter')
    
    def get_bm25_filter(self) -> Optional[Any]:
        """Get the BM25 filter service if available"""
        return self.services.get('bm25_filter')
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all services"""
        status = {
            'initialized': self.initialized,
            'services': {},
            'total_services': len(self.services),
            'timestamp': datetime.now().isoformat()
        }
        
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'get_status'):
                    service_status = await service.get_status()
                    status['services'][service_name] = {
                        'status': 'healthy',
                        'details': service_status
                    }
                else:
                    status['services'][service_name] = {
                        'status': 'healthy',
                        'details': {'initialized': True}
                    }
            except Exception as e:
                status['services'][service_name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
        
        return status
    
    async def cleanup(self):
        """Cleanup all services"""
        logger.info("🧹 Cleaning up Web Service Manager...")
        
        cleanup_tasks = []
        
        # Cleanup services in reverse order
        for service_name in reversed(self.initialization_order):
            if service_name in self.services:
                service = self.services[service_name]
                
                # Cleanup methods can be: cleanup, close, cleanup_all
                if hasattr(service, 'cleanup_all'):
                    cleanup_tasks.append(service.cleanup_all())
                elif hasattr(service, 'cleanup'):
                    cleanup_tasks.append(service.cleanup())
                elif hasattr(service, 'close'):
                    cleanup_tasks.append(service.close())
        
        # Execute cleanup tasks
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.services.clear()
        self.initialized = False
        logger.info("✅ Web Service Manager cleanup completed")
    
    def is_initialized(self) -> bool:
        """Check if manager is initialized"""
        return self.initialized
    
    def get_service_names(self) -> List[str]:
        """Get list of all service names"""
        return list(self.services.keys())

# Global instance
_web_service_manager: Optional[WebServiceManager] = None

async def get_web_service_manager() -> WebServiceManager:
    """Get the global web service manager instance"""
    global _web_service_manager
    
    if _web_service_manager is None:
        _web_service_manager = WebServiceManager()
        await _web_service_manager.initialize()
    
    return _web_service_manager

async def cleanup_web_service_manager():
    """Cleanup the global web service manager"""
    global _web_service_manager
    
    if _web_service_manager:
        await _web_service_manager.cleanup()
        _web_service_manager = None
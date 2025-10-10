"""
Shared Dask Manager for Knowledge Analytics Services

Provides centralized Dask client management for all extractors and services.
Allows any service to leverage parallel processing capabilities.
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DaskManager:
    """
    Centralized Dask Client Manager
    
    Provides shared Dask client for all knowledge extraction services.
    Manages client lifecycle and provides utility methods for parallel processing.
    """
    
    _instance = None
    _dask_client = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def is_available(self) -> bool:
        """Check if Dask client is available and ready"""
        return self._dask_client is not None and not self._dask_client.status == 'closed'
    
    @property
    def client(self):
        """Get the current Dask client"""
        return self._dask_client
    
    async def initialize(self, 
                        workers: int = 4, 
                        threads_per_worker: int = 2,
                        memory_limit: str = "2GB",
                        timeout: int = 30) -> bool:
        """
        Initialize Dask client for parallel processing
        
        Args:
            workers: Number of worker processes
            threads_per_worker: Threads per worker
            memory_limit: Memory limit per worker
            timeout: Connection timeout
            
        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized and self.is_available:
            logger.info("Dask client already initialized and available")
            return True
        
        try:
            from dask.distributed import Client
            
            self._dask_client = Client(
                processes=True,
                n_workers=workers,
                threads_per_worker=threads_per_worker,
                memory_limit=memory_limit,
                silence_logs=False,
                timeout=timeout
            )
            
            self._initialized = True
            logger.info(f"✅ Dask client initialized: {workers} workers, {threads_per_worker} threads each")
            logger.info(f"📊 Dask dashboard: {self._dask_client.dashboard_link}")
            return True
            
        except Exception as e:
            logger.warning(f"❌ Dask initialization failed: {e}")
            self._dask_client = None
            self._initialized = False
            return False
    
    def close(self):
        """Close Dask client and cleanup"""
        if self._dask_client:
            try:
                self._dask_client.close()
                logger.info("🔄 Dask client closed")
            except Exception as e:
                logger.warning(f"Dask close error: {e}")
            finally:
                self._dask_client = None
                self._initialized = False
    
    async def process_in_parallel(self,
                                items: List[Any],
                                process_func: Callable,
                                max_workers: int = None,
                                **kwargs) -> List[Any]:
        """
        Process items in parallel using Dask or asyncio fallback
        
        Args:
            items: List of items to process
            process_func: Function to process each item
            max_workers: Maximum workers (if None, uses all available)
            **kwargs: Additional arguments for process_func
            
        Returns:
            List of processed results
        """
        if not items:
            return []
        
        if len(items) == 1:
            # Single item, process directly
            return [await process_func(items[0], **kwargs)]
        
        if self.is_available:
            return await self._process_with_dask(items, process_func, **kwargs)
        else:
            return await self._process_with_asyncio(items, process_func, max_workers or 4, **kwargs)
    
    async def _process_with_dask(self,
                               items: List[Any],
                               process_func: Callable,
                               **kwargs) -> List[Any]:
        """Process items using Dask distributed computing"""
        try:
            from dask import delayed
            import dask
            
            @delayed
            def delayed_process(item):
                """Dask delayed wrapper for processing function"""
                import asyncio
                
                # Create new event loop for Dask worker
                async def _run():
                    return await process_func(item, **kwargs)
                
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(_run())
                finally:
                    loop.close()
            
            # Create delayed tasks
            tasks = [delayed_process(item) for item in items]
            
            # Execute in parallel
            logger.info(f"🚀 Processing {len(items)} items with Dask...")
            start_time = time.time()
            results = dask.compute(*tasks)
            processing_time = time.time() - start_time
            
            logger.info(f"✅ Dask processing completed in {processing_time:.2f}s")
            return list(results)
            
        except Exception as e:
            logger.warning(f"Dask processing failed: {e}, falling back to asyncio")
            return await self._process_with_asyncio(items, process_func, 4, **kwargs)
    
    async def _process_with_asyncio(self,
                                  items: List[Any],
                                  process_func: Callable,
                                  max_workers: int,
                                  **kwargs) -> List[Any]:
        """Process items using asyncio (fallback)"""
        try:
            semaphore = asyncio.Semaphore(max_workers)
            
            async def process_with_semaphore(item):
                async with semaphore:
                    return await process_func(item, **kwargs)
            
            logger.info(f"🔄 Processing {len(items)} items with asyncio (max {max_workers} concurrent)...")
            start_time = time.time()
            
            tasks = [process_with_semaphore(item) for item in items]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            processing_time = time.time() - start_time
            logger.info(f"✅ Asyncio processing completed in {processing_time:.2f}s")
            
            # Handle exceptions in results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Item {i} processing failed: {result}")
                    processed_results.append(None)  # or handle as needed
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Asyncio processing failed: {e}")
            return [None] * len(items)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current Dask status information"""
        if not self.is_available:
            return {
                "status": "not_available",
                "client": None,
                "workers": 0,
                "dashboard": None
            }
        
        try:
            return {
                "status": "available", 
                "client": str(self._dask_client),
                "workers": len(self._dask_client.scheduler_info()['workers']),
                "dashboard": self._dask_client.dashboard_link,
                "scheduler": self._dask_client.scheduler_info()['address']
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# Global instance
dask_manager = DaskManager()


# Convenience functions
async def initialize_dask(**kwargs) -> bool:
    """Initialize global Dask manager"""
    return await dask_manager.initialize(**kwargs)


def close_dask():
    """Close global Dask manager"""
    dask_manager.close()


async def process_parallel(items: List[Any], process_func: Callable, **kwargs) -> List[Any]:
    """Process items in parallel using global Dask manager"""
    return await dask_manager.process_in_parallel(items, process_func, **kwargs)


def is_dask_available() -> bool:
    """Check if Dask is available for use"""
    return dask_manager.is_available


def get_dask_status() -> Dict[str, Any]:
    """Get Dask status information"""
    return dask_manager.get_status()
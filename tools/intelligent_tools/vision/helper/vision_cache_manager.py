#!/usr/bin/env python
"""
Vision Analysis Cache Manager
Provides caching and pre-configured element detection to reduce omniparser dependency
"""
import json
import hashlib
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from urllib.parse import urlparse

from core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class CachedDetectionResult:
    """Cached detection result with metadata"""
    elements: Dict[str, Any]
    detection_type: str  # 'login', 'search', 'ui_analysis'
    confidence: float
    timestamp: str
    url_pattern: str
    page_hash: str
    expires_at: str
    hit_count: int = 0

@dataclass
class PreConfiguredSite:
    """Pre-configured site element definitions"""
    domain: str
    site_name: str
    login_elements: Dict[str, Any]
    search_elements: Dict[str, Any]
    special_selectors: Dict[str, Any]
    confidence: float = 0.95
    last_verified: str = ""
    notes: str = ""

class VisionCacheManager:
    """Manager for caching vision analysis results and pre-configured sites"""
    
    def __init__(self, cache_dir: str = "cache/vision", preconfig_dir: str = "config/sites"):
        self.cache_dir = Path(cache_dir)
        self.preconfig_dir = Path(preconfig_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.preconfig_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache settings
        self.default_cache_duration = timedelta(hours=24)
        self.max_cache_entries = 1000
        self.min_confidence_threshold = 0.7
        
        # Pre-configured sites registry
        self.preconfig_sites: Dict[str, PreConfiguredSite] = {}
        self._load_preconfig_sites()
        
        logger.debug(f"Vision Cache Manager initialized: cache={self.cache_dir}, preconfig_sites={len(self.preconfig_sites)}")
    
    def _generate_cache_key(self, url: str, detection_type: str, 
                          additional_context: Dict[str, Any] = None) -> str:
        """Generate unique cache key for detection request"""
        # Normalize URL (remove query params, fragments)
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        # Create key components
        key_data = {
            'url': base_url,
            'type': detection_type,
            'context': additional_context or {}
        }
        
        # Generate hash
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def _generate_page_hash(self, page_content: str) -> str:
        """Generate hash of page content for cache validation"""
        # Use first 2000 chars to avoid huge content
        content_sample = page_content[:2000] if page_content else ""
        return hashlib.md5(content_sample.encode()).hexdigest()[:12]
    
    async def get_cached_detection(self, url: str, detection_type: str,
                                 page_content: str = "",
                                 additional_context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Retrieve cached detection result if available and valid"""
        try:
            cache_key = self._generate_cache_key(url, detection_type, additional_context)
            cache_file = self.cache_dir / f"{cache_key}.json"
            
            if not cache_file.exists():
                logger.debug(f"🔍 No cache entry for key: {cache_key}")
                return None
            
            # Load cached result
            with cache_file.open('r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            cached_result = CachedDetectionResult(**cached_data)
            
            # Check if cache is expired
            expires_at = datetime.fromisoformat(cached_result.expires_at)
            if datetime.now() > expires_at:
                logger.info(f"⏰ Cache expired for {url} ({detection_type})")
                cache_file.unlink()  # Remove expired cache
                return None
            
            # Validate page content if provided
            if page_content:
                current_hash = self._generate_page_hash(page_content)
                if current_hash != cached_result.page_hash:
                    logger.info(f"📄 Page content changed for {url}, cache invalid")
                    return None
            
            # Update hit count
            cached_result.hit_count += 1
            await self._save_cache_entry(cache_key, cached_result)
            
            logger.info(f"✅ Cache hit for {url} ({detection_type}) - hits: {cached_result.hit_count}")
            return cached_result.elements
            
        except Exception as e:
            logger.error(f"❌ Cache retrieval error: {e}")
            return None
    
    async def save_detection_result(self, url: str, detection_type: str,
                                  elements: Dict[str, Any], confidence: float,
                                  page_content: str = "",
                                  additional_context: Dict[str, Any] = None):
        """Save detection result to cache"""
        try:
            # Only cache high-confidence results
            if confidence < self.min_confidence_threshold:
                logger.debug(f"❌ Confidence too low to cache: {confidence:.2f}")
                return
            
            cache_key = self._generate_cache_key(url, detection_type, additional_context)
            
            # Create cache entry
            cached_result = CachedDetectionResult(
                elements=elements,
                detection_type=detection_type,
                confidence=confidence,
                timestamp=datetime.now().isoformat(),
                url_pattern=self._extract_url_pattern(url),
                page_hash=self._generate_page_hash(page_content),
                expires_at=(datetime.now() + self.default_cache_duration).isoformat(),
                hit_count=0
            )
            
            await self._save_cache_entry(cache_key, cached_result)
            logger.info(f"💾 Cached detection result for {url} ({detection_type})")
            
        except Exception as e:
            logger.error(f"❌ Cache save error: {e}")
    
    async def _save_cache_entry(self, cache_key: str, cached_result: CachedDetectionResult):
        """Save cache entry to file"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        with cache_file.open('w', encoding='utf-8') as f:
            json.dump(asdict(cached_result), f, indent=2, ensure_ascii=False)
    
    def _extract_url_pattern(self, url: str) -> str:
        """Extract URL pattern for classification"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove common prefixes
        domain = domain.replace('www.', '').replace('m.', '')
        
        return domain
    
    async def get_preconfig_detection(self, url: str, detection_type: str) -> Optional[Dict[str, Any]]:
        """Get pre-configured detection result for known sites"""
        try:
            domain = self._extract_url_pattern(url)
            
            # Check if we have pre-config for this domain
            if domain not in self.preconfig_sites:
                logger.debug(f"🔍 No pre-config for domain: {domain}")
                return None
            
            site_config = self.preconfig_sites[domain]
            
            # Get appropriate elements based on detection type
            if detection_type == 'login' and site_config.login_elements:
                logger.info(f"🎯 Using pre-configured login elements for {domain}")
                return site_config.login_elements
            elif detection_type == 'search' and site_config.search_elements:
                logger.info(f"🔍 Using pre-configured search elements for {domain}")
                return site_config.search_elements
            elif detection_type == 'ui_analysis' and site_config.special_selectors:
                logger.info(f"🎨 Using pre-configured special selectors for {domain}")
                return site_config.special_selectors
            
            logger.debug(f"❌ No pre-config available for {detection_type} on {domain}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Pre-config retrieval error: {e}")
            return None
    
    def _load_preconfig_sites(self):
        """Load pre-configured site definitions"""
        try:
            # Load all JSON files in preconfig directory
            for config_file in self.preconfig_dir.glob("*.json"):
                try:
                    with config_file.open('r', encoding='utf-8') as f:
                        site_data = json.load(f)
                    
                    site_config = PreConfiguredSite(**site_data)
                    self.preconfig_sites[site_config.domain] = site_config
                    logger.debug(f"Loaded pre-config for {site_config.site_name} ({site_config.domain})")

                except Exception as e:
                    logger.warning(f"⚠️ Failed to load config {config_file}: {e}")

            logger.debug(f"Loaded {len(self.preconfig_sites)} pre-configured sites")
            
        except Exception as e:
            logger.error(f"❌ Failed to load pre-configs: {e}")
    
    async def add_preconfig_site(self, domain: str, site_name: str,
                               login_elements: Dict[str, Any] = None,
                               search_elements: Dict[str, Any] = None,
                               special_selectors: Dict[str, Any] = None,
                               notes: str = ""):
        """Add new pre-configured site"""
        try:
            site_config = PreConfiguredSite(
                domain=domain,
                site_name=site_name,
                login_elements=login_elements or {},
                search_elements=search_elements or {},
                special_selectors=special_selectors or {},
                confidence=0.95,
                last_verified=datetime.now().isoformat(),
                notes=notes
            )
            
            # Save to file
            config_file = self.preconfig_dir / f"{domain.replace('.', '_')}.json"
            with config_file.open('w', encoding='utf-8') as f:
                json.dump(asdict(site_config), f, indent=2, ensure_ascii=False)
            
            # Add to registry
            self.preconfig_sites[domain] = site_config
            
            logger.info(f"✅ Added pre-config for {site_name} ({domain})")
            
        except Exception as e:
            logger.error(f"❌ Failed to add pre-config: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_entries = len(cache_files)
            
            # Calculate cache size
            total_size = sum(f.stat().st_size for f in cache_files)
            
            # Count by detection type
            type_counts = {}
            hit_counts = []
            
            for cache_file in cache_files:
                try:
                    with cache_file.open('r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    detection_type = data.get('detection_type', 'unknown')
                    type_counts[detection_type] = type_counts.get(detection_type, 0) + 1
                    hit_counts.append(data.get('hit_count', 0))
                    
                except:
                    continue
            
            avg_hits = sum(hit_counts) / len(hit_counts) if hit_counts else 0
            
            return {
                'total_entries': total_entries,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'by_type': type_counts,
                'average_hits': round(avg_hits, 1),
                'preconfig_sites': len(self.preconfig_sites),
                'cache_directory': str(self.cache_dir),
                'preconfig_directory': str(self.preconfig_dir)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get cache stats: {e}")
            return {}
    
    async def cleanup_expired_cache(self):
        """Remove expired cache entries"""
        try:
            removed_count = 0
            cache_files = list(self.cache_dir.glob("*.json"))
            
            for cache_file in cache_files:
                try:
                    with cache_file.open('r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    expires_at = datetime.fromisoformat(data['expires_at'])
                    if datetime.now() > expires_at:
                        cache_file.unlink()
                        removed_count += 1
                        
                except:
                    continue
            
            logger.info(f"🧹 Cleaned up {removed_count} expired cache entries")
            return removed_count
            
        except Exception as e:
            logger.error(f"❌ Cache cleanup error: {e}")
            return 0
    
    async def clear_cache(self, detection_type: str = None):
        """Clear cache entries (optionally filtered by type)"""
        try:
            removed_count = 0
            cache_files = list(self.cache_dir.glob("*.json"))
            
            for cache_file in cache_files:
                should_remove = True
                
                if detection_type:
                    try:
                        with cache_file.open('r', encoding='utf-8') as f:
                            data = json.load(f)
                        should_remove = data.get('detection_type') == detection_type
                    except:
                        should_remove = False
                
                if should_remove:
                    cache_file.unlink()
                    removed_count += 1
            
            logger.info(f"🧹 Cleared {removed_count} cache entries" + 
                       (f" for type '{detection_type}'" if detection_type else ""))
            return removed_count
            
        except Exception as e:
            logger.error(f"❌ Cache clear error: {e}")
            return 0

# Global cache manager instance
_cache_manager = None

def get_vision_cache_manager() -> VisionCacheManager:
    """Get global vision cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = VisionCacheManager()
    return _cache_manager
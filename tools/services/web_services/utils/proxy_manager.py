#!/usr/bin/env python
"""
Proxy Manager for Web Services
Manages proxy rotation and connection handling
"""
import random
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class ProxyConfig:
    """Proxy configuration"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: str = "http"  # http, https, socks4, socks5
    
    def to_url(self) -> str:
        """Convert to proxy URL"""
        if self.username and self.password:
            return f"{self.proxy_type}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.proxy_type}://{self.host}:{self.port}"

class ProxyManager:
    """Manages proxy rotation and health checking"""
    
    def __init__(self):
        self.proxies: List[ProxyConfig] = []
        self.active_proxies: List[ProxyConfig] = []
        self.failed_proxies: List[ProxyConfig] = []
        self.current_proxy_index = 0
        self.health_check_interval = 300  # 5 minutes
        self.max_failures = 3
        self.proxy_failures: Dict[str, int] = {}
    
    def add_proxy(self, host: str, port: int, username: str = None, password: str = None, proxy_type: str = "http"):
        """Add a proxy to the pool"""
        proxy = ProxyConfig(
            host=host,
            port=port,
            username=username,
            password=password,
            proxy_type=proxy_type
        )
        
        self.proxies.append(proxy)
        self.active_proxies.append(proxy)
        logger.info(f"Added proxy: {proxy.host}:{proxy.port}")
    
    def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get next proxy in rotation"""
        if not self.active_proxies:
            logger.warning("No active proxies available")
            return None
        
        # Round-robin selection
        proxy = self.active_proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.active_proxies)
        
        logger.debug(f"Selected proxy: {proxy.host}:{proxy.port}")
        return proxy
    
    def get_random_proxy(self) -> Optional[ProxyConfig]:
        """Get random proxy from active pool"""
        if not self.active_proxies:
            logger.warning("No active proxies available")
            return None
        
        proxy = random.choice(self.active_proxies)
        logger.debug(f"Selected random proxy: {proxy.host}:{proxy.port}")
        return proxy
    
    def get_status(self) -> Dict[str, Any]:
        """Get proxy manager status"""
        return {
            "total_proxies": len(self.proxies),
            "active_proxies": len(self.active_proxies),
            "failed_proxies": len(self.failed_proxies),
            "current_proxy_index": self.current_proxy_index,
            "health_check_interval": self.health_check_interval
        }
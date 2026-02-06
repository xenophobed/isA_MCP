#!/usr/bin/env python3
"""
Web Tools Package
MCP tools for web search and automation via web microservice
"""

from .web_tools import register_web_tools
from .web_client import get_web_client, WebServiceClient, WebServiceConfig

__all__ = [
    'register_web_tools',
    'get_web_client',
    'WebServiceClient',
    'WebServiceConfig'
]

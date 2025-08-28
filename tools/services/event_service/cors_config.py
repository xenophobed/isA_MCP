#!/usr/bin/env python
"""
CORS Configuration for Event Service
Centralized CORS settings for easy management
"""

import os
from typing import List

# Default CORS origins for development
DEFAULT_ORIGINS = [
    "http://localhost:5173",  # Vite default port
    "http://localhost:3000",  # React default port
    "http://127.0.0.1:5173", # Alternative localhost format
    "http://127.0.0.1:3000", # Alternative localhost format
]

# Production origins (can be overridden by environment variables)
PRODUCTION_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]

def get_cors_origins() -> List[str]:
    """
    Get CORS origins from environment variables or use defaults
    
    Environment Variables:
    - CORS_ORIGINS: Comma-separated list of allowed origins
    - ENV: Set to 'production' to use production origins
    
    Returns:
        List of allowed CORS origins
    """
    # Check for custom CORS origins in environment
    custom_origins = os.getenv('CORS_ORIGINS')
    if custom_origins:
        return [origin.strip() for origin in custom_origins.split(',')]
    
    # Use production origins if in production environment
    if os.getenv('ENV', 'development').lower() == 'production':
        return PRODUCTION_ORIGINS
    
    # Default to development origins
    return DEFAULT_ORIGINS

def get_cors_config():
    """
    Get complete CORS configuration
    
    Returns:
        Dictionary with CORS middleware configuration
    """
    return {
        "allow_origins": get_cors_origins(),
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["*"],
    }

# Example usage:
# from fastapi.middleware.cors import CORSMiddleware
# from cors_config import get_cors_config
# 
# app.add_middleware(CORSMiddleware, **get_cors_config())

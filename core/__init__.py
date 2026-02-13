#!/usr/bin/env python3
"""
Core Module - isA MCP System

PROJECT DESCRIPTION:
    Core module providing fundamental services and utilities for the isA MCP (Model Context Protocol) system.
    This module contains the foundational components including configuration management, security services,
    authentication, monitoring, database connections, and utility functions.

INPUTS:
    - Environment variables for configuration
    - Authentication tokens and API keys
    - Database connection parameters
    - Security policies and settings

OUTPUTS:
    - Configured service instances
    - Authentication and authorization results
    - Database connections and schema management
    - Monitoring and logging infrastructure

FUNCTIONALITY:
    - Central configuration management with environment-based settings
    - Production-grade authentication (JWT, API keys) and authorization
    - Security management with rate limiting and access controls
    - Database schema management and migration handling
    - Structured logging and monitoring systems
    - Auto-discovery system for tools, prompts, and resources
    - Unified search service across all MCP capabilities

DEPENDENCIES:
    - python-dotenv: Environment variable management
    - PyJWT: JSON Web Token handling
    - asyncpg: PostgreSQL database client
    - FastAPI/Starlette: Web framework components
    - logging: Standard logging infrastructure

OPTIMIZATION POINTS:
    - Implement connection pooling for database operations
    - Add caching layers for frequently accessed configurations
    - Optimize security token validation with caching
    - Enhance monitoring with metrics aggregation
    - Add configuration validation and error handling
    - Implement graceful degradation for external services
    - Add health check endpoints for all core services
    - Optimize auto-discovery performance with indexing

ARCHITECTURE:
    This core module follows a layered architecture pattern:
    - Configuration Layer: Environment-based settings management
    - Security Layer: Authentication, authorization, and access control
    - Data Layer: Database connections and schema management
    - Service Layer: Core business logic and utilities
    - Monitoring Layer: Logging, metrics, and health checks

USAGE:
    from core import config, auth, logging, database
    from core.auto_discovery import AutoDiscoverySystem
    # Search service moved to services/search_service/
    from services.search_service.search_service import SearchService
"""

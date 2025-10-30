#!/usr/bin/env python3
"""
User-Agent Configuration
Transparent and ethical user-agent strings for web scraping

Based on MCP Fetch Server pattern for identifying AI/autonomous access
"""

import os

# Base project info
PROJECT_NAME = "isA_MCP"
PROJECT_VERSION = "1.0.0"
PROJECT_URL = "https://github.com/yourusername/isA_MCP"  # Update with actual repo URL

# Autonomous User-Agent (for tool/automated requests)
USER_AGENT_AUTONOMOUS = (
    f"{PROJECT_NAME}/{PROJECT_VERSION} "
    f"(Autonomous; AI Agent; +{PROJECT_URL})"
)

# Manual/User-Directed User-Agent (for user-requested fetches)
USER_AGENT_MANUAL = (
    f"{PROJECT_NAME}/{PROJECT_VERSION} "
    f"(User-Directed; +{PROJECT_URL})"
)

# Browser-like User-Agent (for sites that block automated access)
USER_AGENT_BROWSER_LIKE = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 "
    f"({PROJECT_NAME}/{PROJECT_VERSION}; +{PROJECT_URL})"
)

# Custom User-Agent from Environment
USER_AGENT_CUSTOM = os.getenv("WEB_USER_AGENT")


def get_user_agent(
    autonomous: bool = True,
    custom_ua: str = None,
    browser_like: bool = False
) -> str:
    """Get appropriate user-agent string"""
    if custom_ua:
        return custom_ua
    if USER_AGENT_CUSTOM:
        return USER_AGENT_CUSTOM
    if browser_like:
        return USER_AGENT_BROWSER_LIKE
    return USER_AGENT_AUTONOMOUS if autonomous else USER_AGENT_MANUAL

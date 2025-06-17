#!/usr/bin/env python
"""
Main entry point for the Enhanced Secure MCP Server
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from servers.secure_server import main

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Digital Service Test Suite
Comprehensive testing framework for all digital service functionality
"""

from .functionality import *
from .performance import *
from .integration import *
from .patterns import *
from .benchmarks import *

__version__ = "1.0.0"
__all__ = [
    "functionality",
    "performance", 
    "integration",
    "patterns",
    "benchmarks"
]
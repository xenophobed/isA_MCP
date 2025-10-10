#!/usr/bin/env python3
"""
Main entry point for TestPlan Generation Service
"""

import uvicorn
from services.api.testplan_api import app

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8105,
        reload=True,
        log_level="info"
    )
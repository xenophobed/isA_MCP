"""Web Services Context Module"""

from .search_progress_context import WebSearchProgressReporter, SearchOperationDetector
from .automation_progress_context import WebAutomationProgressReporter, AutomationOperationDetector

__all__ = [
    "WebSearchProgressReporter", 
    "SearchOperationDetector",
    "WebAutomationProgressReporter",
    "AutomationOperationDetector"
]

"""Web Services Tools Package"""

from .context import (
    WebSearchProgressReporter, 
    SearchOperationDetector,
    WebAutomationProgressReporter,
    AutomationOperationDetector
)

__all__ = [
    "WebSearchProgressReporter", 
    "SearchOperationDetector",
    "WebAutomationProgressReporter",
    "AutomationOperationDetector"
]

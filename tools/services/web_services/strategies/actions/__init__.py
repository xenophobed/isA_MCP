"""
Action Strategies for Web Automation
Enhanced browser action capabilities
"""

from .click_action import ClickActionStrategy
from .type_action import TypeActionStrategy
from .select_action import SelectActionStrategy
from .scroll_action import ScrollActionStrategy
from .hover_action import HoverActionStrategy
from .wait_action import WaitActionStrategy
from .navigate_action import NavigateActionStrategy
from .checkbox_action import CheckboxActionStrategy
from .iframe_action import IFrameActionStrategy
from .upload_action import UploadActionStrategy
from .download_action import DownloadActionStrategy
from .drag_action import DragActionStrategy

__all__ = [
    'ClickActionStrategy',
    'TypeActionStrategy',
    'SelectActionStrategy',
    'ScrollActionStrategy',
    'HoverActionStrategy',
    'WaitActionStrategy',
    'NavigateActionStrategy',
    'CheckboxActionStrategy',
    'IFrameActionStrategy',
    'UploadActionStrategy',
    'DownloadActionStrategy',
    'DragActionStrategy'
]
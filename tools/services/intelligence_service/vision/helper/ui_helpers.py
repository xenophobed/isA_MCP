#!/usr/bin/env python
"""
UI Helper Functions

Utility functions for UI element processing and interaction text extraction.
"""

import re
from typing import List, Dict, Any


def draw_bounding_boxes(image_path: str, ui_elements: List[Dict]) -> str:
    """
    Draw numbered bounding boxes on screenshot for VLM analysis
    
    Args:
        image_path: Path to image file
        ui_elements: List of UI elements with bbox information
        
    Returns:
        Path to annotated image
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Open image
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        
        # Try to load font
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # Draw boxes with numbers
        for i, elem in enumerate(ui_elements):
            bbox = elem.get('bbox', [])
            if len(bbox) == 4:
                x1, y1, x2, y2 = bbox
                
                # Draw red bounding box
                draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
                
                # Draw number label
                label = str(i)
                
                # Label background
                label_bbox = draw.textbbox((0, 0), label, font=font)
                label_width = label_bbox[2] - label_bbox[0]
                label_height = label_bbox[3] - label_bbox[1]
                
                label_x = x1
                label_y = max(0, y1 - label_height - 5)
                
                draw.rectangle([label_x, label_y, label_x + label_width + 8, label_y + label_height + 4], 
                             fill="red", outline="red")
                draw.text((label_x + 4, label_y + 2), label, fill="white", font=font)
        
        # Save annotated image
        annotated_path = image_path.replace('.png', '_annotated.png')
        image.save(annotated_path)
        
        return annotated_path
        
    except Exception as e:
        print(f"❌ Failed to draw bounding boxes: {e}")
        return image_path  # Return original if failed


def extract_input_text(task: str) -> str:
    """
    Extract text input needed for any task
    
    Args:
        task: Task description
        
    Returns:
        Extracted text for input
    """
    # Look for content in quotes
    match = re.search(r"[''\"](.*?)[''\"']", task)
    if match:
        return match.group(1)
    
    # Look for content after common action words
    action_patterns = [
        r"search\s+(.+)",
        r"find\s+(.+)", 
        r"look\s+for\s+(.+)",
        r"type\s+(.+)",
        r"enter\s+(.+)"
    ]
    
    for pattern in action_patterns:
        match = re.search(pattern, task, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Extract last word as fallback
    words = task.strip().split()
    return words[-1] if words else "search"


def analyze_task_requirements(task: str) -> Dict[str, Any]:
    """
    Analyze task description to determine required interactions and elements
    
    Args:
        task: Task description
        
    Returns:
        Task analysis with type, interactions, and fallback elements
    """
    task_lower = task.lower()
    
    # Search patterns
    search_patterns = ['search', 'find', 'look for', 'query']
    if any(pattern in task_lower for pattern in search_patterns):
        return {
            'task_type': 'search',
            'interactions': ['input_text', 'submit'],
            'fallback_elements': [
                {
                    "element_name": "search_input",
                    "element_purpose": "text input for search query",
                    "location_description": "main search area",
                    "visual_description": "input field or search box",
                    "interaction_type": "click_and_type"
                },
                {
                    "element_name": "search_submit",
                    "element_purpose": "submit search query",
                    "location_description": "near search input",
                    "visual_description": "button or submit element",
                    "interaction_type": "click"
                }
            ]
        }
    
    # Click patterns
    click_patterns = ['click', 'press', 'tap', 'select']
    if any(pattern in task_lower for pattern in click_patterns):
        return {
            'task_type': 'click',
            'interactions': ['click'],
            'fallback_elements': [
                {
                    "element_name": "target_element",
                    "element_purpose": "element to click",
                    "location_description": "as described in task",
                    "visual_description": "clickable element",
                    "interaction_type": "click"
                }
            ]
        }
    
    # Form patterns
    form_patterns = ['fill', 'enter', 'input', 'type', 'submit']
    if any(pattern in task_lower for pattern in form_patterns):
        return {
            'task_type': 'form',
            'interactions': ['input_text', 'submit'],
            'fallback_elements': [
                {
                    "element_name": "form_input",
                    "element_purpose": "form field to fill",
                    "location_description": "form area",
                    "visual_description": "input field",
                    "interaction_type": "click_and_type"
                }
            ]
        }
    
    # Navigation patterns
    nav_patterns = ['go to', 'navigate', 'visit', 'open']
    if any(pattern in task_lower for pattern in nav_patterns):
        return {
            'task_type': 'navigation',
            'interactions': ['click'],
            'fallback_elements': [
                {
                    "element_name": "navigation_link",
                    "element_purpose": "link or button for navigation",
                    "location_description": "navigation area",
                    "visual_description": "link or button",
                    "interaction_type": "click"
                }
            ]
        }
    
    # Generic fallback
    return {
        'task_type': 'generic',
        'interactions': ['click'],
        'fallback_elements': [
            {
                "element_name": "target_element",
                "element_purpose": "element to interact with",
                "location_description": "page content area",
                "visual_description": "interactive element",
                "interaction_type": "click"
            }
        ]
    }
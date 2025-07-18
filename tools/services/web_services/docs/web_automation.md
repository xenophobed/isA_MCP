# Web Automation Tool

## Description
Automate web browser interactions using 5-step atomic workflow with VLM-powered intelligence. Performs complex tasks like form filling, navigation, and content interaction through a structured atomic approach.

## Architecture: 5-Step Atomic Workflow
1. **Playwright Screenshot** - Capture initial page state
2. **image_analyzer** - Screen understanding and task analysis  
3. **ui_detector** - UI element detection with precise coordinates
4. **text_generator** - Action reasoning and Playwright command generation
5. **Playwright Execution + Analysis** - Execute actions and analyze results

## Input Parameters
- `url` (string, required): Target web page URL
- `task` (string, required): Task description (e.g., "search for airpods", "fill out contact form")

## Output Format
```json
{
  "status": "success|error",
  "action": "web_automation", 
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "success": true,
    "initial_url": "https://www.google.com",
    "final_url": "https://www.google.com/search?q=airpods",
    "task": "search airpods",
    "workflow_results": {
      "step1_screenshot": "/tmp/screenshot_path.png",
      "step2_analysis": {
        "page_suitable": true,
        "page_type": "search_page", 
        "required_elements": [
          {
            "element_name": "search_input",
            "element_purpose": "search query input",
            "visual_description": "white input field",
            "interaction_type": "click_and_type"
          }
        ],
        "confidence": 0.9
      },
      "step3_ui_detection": 1,
      "step4_actions": [
        {
          "action": "click",
          "element": "search_input",
          "x": 691,
          "y": 404
        },
        {
          "action": "type", 
          "element": "search_input",
          "x": 691,
          "y": 404,
          "text": "airpods"
        }
      ],
      "step5_execution": {
        "actions_executed": 2,
        "execution_log": [
          "Clicked at (691, 404)",
          "Typed 'airpods' at (691, 404)"
        ],
        "task_completed": true,
        "summary": "Executed 2 actions - Success"
      }
    },
    "result_description": "Successfully searched for 'airpods' on Google..."
  }
}
```

## Error Response
```json
{
  "status": "error",
  "action": "web_automation",
  "timestamp": "2024-01-01T12:00:00Z", 
  "error_message": "Error description (e.g., invalid URL, task failed, timeout)"
}
```

## Example Usage
```python
# Google search automation
result = await client.call_tool("web_automation", {
    "url": "https://www.google.com",
    "task": "search latest nba news"
})

# Form filling automation  
result = await client.call_tool("web_automation", {
    "url": "https://example.com/contact",
    "task": "fill out contact form with name 'John Doe' and email 'john@example.com'"
})

# E-commerce automation
result = await client.call_tool("web_automation", {
    "url": "https://store.example.com", 
    "task": "search for wireless headphones and add first result to cart"
})
```

## Atomic Functions Used
- **image_analyzer.py** - Generic VLM wrapper for screen understanding and result analysis
- **ui_detector.py** - 3-step UI detection: OmniParser → Annotation → VLM matching  
- **text_generator.py** - LLM-based Playwright action reasoning

## Notes
- Uses 5-step atomic workflow for systematic, reliable automation
- Each step is independently testable and reusable
- Processing time: typically 30-90 seconds for complete workflow
- Captures screenshots at each step for debugging and analysis
- Handles dynamic content and JavaScript-heavy sites through VLM analysis
- Supports complex multi-step workflows with precise coordinate targeting
- Atomic functions ensure clean separation of concerns and maintainability
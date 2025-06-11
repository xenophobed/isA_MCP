from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
import yaml
import json
import logging
from app.config.config_manager import config_manager

logger = config_manager.get_logger(__name__)

@tool
async def analyze_intention(input_text: str) -> Dict[str, Any]:
    """
    Analyzes user input to determine their intention, required capabilities,
    and the complexity of their request.
    
    Args:
        input_text: The user's input text to analyze
        
    Returns:
        A dictionary containing the analysis results:
        - primary_intent: The main intention of the user
        - sub_intents: Additional sub-intentions identified
        - complexity: Low, Medium, or High assessment of request complexity
        - capabilities_required: List of capabilities needed to fulfill the request
        - domains: Knowledge domains related to the request
    """
    try:
        # This is a mock implementation. In a real system, this would use
        # a more sophisticated approach with a specialized model or service.
        
        # Simple keywords-based analysis for demo purposes
        weather_keywords = ["weather", "temperature", "forecast", "rain", "humidity", "celsius", "fahrenheit"]
        research_keywords = ["research", "search", "find information", "look up", "article", "paper"]
        writing_keywords = ["write", "draft", "article", "essay", "summary", "summarize", "create content"]
        editing_keywords = ["edit", "revise", "proofread", "correct", "improve", "rewrite"]
        
        # Check for intents
        primary_intent = "general_query"
        sub_intents = []
        complexity = "low"
        capabilities_required = []
        domains = []
        
        # Check for weather intent
        if any(keyword in input_text.lower() for keyword in weather_keywords):
            primary_intent = "weather_query"
            capabilities_required.append("weather_api")
            domains.append("weather")
        
        # Check for research intent
        if any(keyword in input_text.lower() for keyword in research_keywords):
            if primary_intent == "general_query":
                primary_intent = "research"
            else:
                sub_intents.append("research")
            capabilities_required.append("web_search")
            domains.append("information_retrieval")
            complexity = "medium"
        
        # Check for writing intent
        if any(keyword in input_text.lower() for keyword in writing_keywords):
            if primary_intent == "general_query":
                primary_intent = "content_creation"
            else:
                sub_intents.append("content_creation")
            capabilities_required.append("text_generation")
            complexity = "medium"
        
        # Check for editing intent
        if any(keyword in input_text.lower() for keyword in editing_keywords):
            if primary_intent == "general_query":
                primary_intent = "content_editing"
            else:
                sub_intents.append("content_editing")
            capabilities_required.append("text_editing")
            complexity = "medium"
        
        # Assess complexity based on number of different intents
        if len(sub_intents) >= 2:
            complexity = "high"
        
        # Return analysis results
        return {
            "primary_intent": primary_intent,
            "sub_intents": sub_intents,
            "complexity": complexity,
            "capabilities_required": capabilities_required,
            "domains": domains
        }
    except Exception as e:
        logger.error(f"Error analyzing intention: {str(e)}")
        return {
            "error": str(e),
            "primary_intent": "unknown",
            "sub_intents": [],
            "complexity": "unknown",
            "capabilities_required": [],
            "domains": []
        }

@tool
async def generate_execution_graph(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates an execution graph configuration based on requirements.
    
    Args:
        requirements: A dictionary containing:
            - primary_intent: The main intention of the user
            - capabilities_required: List of capabilities needed
            - complexity: Complexity assessment (low, medium, high)
            - reasoning_steps: Optional list of reasoning steps to incorporate
            - recommended_actions: Optional list of recommended actions 
            
    Returns:
        A dictionary containing:
            - graph_yaml: YAML representation of the execution graph
            - graph_config: Parsed dictionary of the graph configuration
    """
    try:
        primary_intent = requirements.get("primary_intent", "unknown")
        capabilities = requirements.get("capabilities_required", [])
        complexity = requirements.get("complexity", "low")
        reasoning_steps = requirements.get("reasoning_steps", [])
        recommended_actions = requirements.get("recommended_actions", [])
        
        # Select appropriate template based on the primary intent and reasoning
        graph_yaml = ""
        
        # Weather query template - ENHANCED VERSION
        if primary_intent == "weather_query" or "weather_api" in capabilities:
            graph_yaml = """
graph_name: Enhanced_WeatherQueryGraph
description: Enhanced graph for weather information with location extraction and formatting

graph_state:
  raw_input: str  # Original user query
  location: str   # Extracted location
  weather_data: dict  # Weather API response
  response: str   # Formatted response
  error: str      # Any error information

nodes:
  - name: extract_location
    node_pattern_type: "execute_llm_call_pattern"
    description: Extracts location from user query with detailed analysis
    parameters:
      prompt_template: |
        Extract the location the user is asking about from the following weather query.
        If multiple locations are mentioned, identify the primary one the user wants weather for.
        If no specific location is mentioned, determine the most likely location from context.
        
        User query: {query}
        
        Output the location name only, with no additional text or explanation.
      input_mappings: {"query": "raw_input"}
      output_mappings: {"extracted_location": "location"}
      llm_invocation_params:
        temperature: 0.1
  
  - name: get_weather
    node_pattern_type: "execute_tool_call_pattern"
    description: Gets comprehensive weather data for the location
    parameters:
      tool_id: "get_weather"
      input_mappings: {"location": "location"}
      output_mappings: {"result": "weather_data"}
      error_mapping: {"error": "error"}
  
  - name: format_response
    node_pattern_type: "execute_llm_call_pattern"
    description: Formats the weather data into a natural and helpful response
    parameters:
      prompt_template: |
        Format this weather data for {location} into a natural, conversational response.
        Include temperature in both Celsius and Fahrenheit, current conditions, and any other relevant details.
        Keep the response concise but informative and friendly.
        
        Weather data: {weather_data}
      input_mappings: {"location": "location", "weather_data": "weather_data"}
      output_mappings: {"llm_output": "response"}
      llm_invocation_params:
        temperature: 0.7

edges:
  - from: extract_location
    to: get_weather
    condition: "not error"
  - from: get_weather
    to: format_response
    condition: "not error"

entry_point: extract_location
end_node: format_response
error_node: format_response  # Will still attempt to format with error info
"""
        
        # Research and content creation - ENHANCED VERSION
        elif primary_intent in ["research", "content_creation"] or "web_search" in capabilities:
            graph_yaml = """
graph_name: Enhanced_ResearchAndWriteGraph
description: Comprehensive graph for researching a topic, writing, and editing content

graph_state:
  raw_input: str     # Original user query
  topic: str         # Extracted research topic
  search_query: str  # Refined search query
  research_data: List[Dict]  # Search results
  outline: str       # Content outline
  draft_content: str # Initial draft
  edited_content: str # Edited content
  final_content: str # Final polished content
  error: str         # Error tracking

nodes:
  - name: extract_topic
    node_pattern_type: "execute_llm_call_pattern"
    description: Analyzes user request to extract clear research topic and parameters
    parameters:
      prompt_template: |
        Analyze the following request for content creation:
        
        "{query}"
        
        Extract:
        1. The main topic to research
        2. Any specific aspects to focus on
        3. The type of content to be created (article, report, summary, etc.)
        4. Any style preferences indicated
        
        Format your response as a JSON object with these fields.
      input_mappings: {"query": "raw_input"}
      output_mappings: {"extracted_topic": "topic"}
      llm_invocation_params:
        temperature: 0.2
  
  - name: generate_search_query
    node_pattern_type: "execute_llm_call_pattern"
    description: Generates optimal search queries for the research topic
    parameters:
      prompt_template: |
        Create an effective search query for researching this topic:
        
        Topic: {topic}
        
        Create a concise, focused search query that will yield high-quality, relevant information.
        Consider using advanced search operators if appropriate.
        Output the query only, with no additional text or explanation.
      input_mappings: {"topic": "topic"}
      output_mappings: {"query": "search_query"}
  
  - name: research_topic
    node_pattern_type: "execute_tool_call_pattern"
    description: Performs comprehensive research using search tools
    parameters:
      tool_id: "web_search"
      input_mappings: {"query": "search_query"}
      output_mappings: {"results": "research_data"}
      error_mapping: {"error": "error"}
  
  - name: create_outline
    node_pattern_type: "execute_llm_call_pattern"
    description: Creates structured content outline based on research
    parameters:
      prompt_template: |
        Create a detailed outline for content about {topic} based on this research:
        
        Research data:
        {research_data}
        
        The outline should include:
        1. Introduction section
        2. Main sections with clear headings
        3. Key points to address in each section
        4. Conclusion section
        
        Format as a structured outline.
      input_mappings: {"topic": "topic", "research_data": "research_data"}
      output_mappings: {"outline": "outline"}
  
  - name: generate_draft
    node_pattern_type: "execute_llm_call_pattern"
    description: Generates full content draft following the outline
    parameters:
      prompt_template: |
        Write a comprehensive draft following this outline:
        
        Topic: {topic}
        Outline: {outline}
        Research data: {research_data}
        
        Create engaging, factual content with clear structure following the outline.
        Include a compelling introduction and meaningful conclusion.
      input_mappings: {"topic": "topic", "outline": "outline", "research_data": "research_data"}
      output_mappings: {"draft": "draft_content"}
      llm_invocation_params:
        temperature: 0.6
        max_tokens: 1500
  
  - name: edit_content
    node_pattern_type: "execute_llm_call_pattern"
    description: Edits and improves the draft with professional editing
    parameters:
      prompt_template: |
        Edit and improve this content for clarity, coherence, and impact:
        
        {draft}
        
        Your edits should:
        1. Improve sentence structure and flow
        2. Enhance clarity and readability
        3. Fix any grammatical or factual errors
        4. Ensure compelling introduction and conclusion
        5. Optimize paragraph structure
        
        Return the complete edited version.
      input_mappings: {"draft": "draft_content"}
      output_mappings: {"edited_content": "edited_content"}
  
  - name: finalize_content
    node_pattern_type: "execute_llm_call_pattern"
    description: Performs final polish and quality check
    parameters:
      prompt_template: |
        Perform a final review and polish of this content:
        
        {content}
        
        Check for:
        - Professional tone and language
        - Consistent formatting and style
        - Logical flow and transitions
        - Compelling opening and conclusion
        - Any remaining errors or unclear passages
        
        Return the finalized version.
      input_mappings: {"content": "edited_content"}
      output_mappings: {"final_content": "final_content"}

edges:
  - from: extract_topic
    to: generate_search_query
    condition: "not error"
  - from: generate_search_query
    to: research_topic
    condition: "not error"
  - from: research_topic
    to: create_outline
    condition: "not error"
  - from: create_outline
    to: generate_draft
    condition: "not error"
  - from: generate_draft
    to: edit_content
    condition: "not error"
  - from: edit_content
    to: finalize_content
    condition: "not error"

entry_point: extract_topic
end_node: finalize_content
error_nodes: [generate_draft, finalize_content]  # Can fallback to these nodes with partial completion
"""
        
        # Default simple response template - ENHANCED VERSION
        else:
            graph_yaml = """
graph_name: EnhancedResponseGraph
description: Improved response graph with context integration

graph_state:
  raw_input: str    # Original user query
  context: dict     # Available context information
  response: str     # Generated response
  error: str        # Error information

nodes:
  - name: fetch_context
    node_pattern_type: "context_retrieval_pattern"
    description: Retrieves relevant context for the response
    parameters:
      context_providers: ["conversation_history", "user_profile", "knowledge_base"]
      query_mappings: {"query": "raw_input"}
      output_mappings: {"retrieved_context": "context"}
  
  - name: generate_response
    node_pattern_type: "execute_llm_call_pattern"
    description: Generates a contextually informed response
    parameters:
      prompt_template: |
        Generate a helpful, informative response to this query:
        
        Query: {query}
        
        Available Context:
        {context}
        
        Your response should be:
        - Directly addressing the user's query
        - Incorporating relevant context appropriately
        - Helpful and friendly in tone
        - Concise yet complete
      input_mappings: {"query": "raw_input", "context": "context"}
      output_mappings: {"llm_output": "response"}
      llm_invocation_params:
        temperature: 0.7

edges:
  - from: fetch_context
    to: generate_response

entry_point: fetch_context
end_node: generate_response
"""
        
        # Parse the YAML
        graph_config = yaml.safe_load(graph_yaml)
        
        return {
            "graph_yaml": graph_yaml,
            "graph_config": graph_config
        }
        
    except Exception as e:
        logger.error(f"Error generating execution graph: {str(e)}")
        return {
            "error": str(e),
            "graph_yaml": "",
            "graph_config": {}
        }

@tool
async def assess_capabilities(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assesses available capabilities against requirements and suggests
    the best components to use.
    
    Args:
        requirements: A dictionary containing capability requirements
        
    Returns:
        Dictionary with capability assessment and recommendations
    """
    try:
        required_capabilities = requirements.get("capabilities_required", [])
        complexity = requirements.get("complexity", "low")
        
        # Mock capability assessment
        available_capabilities = {
            "weather_api": {
                "available": True,
                "components": ["get_weather", "get_forecast"],
                "confidence": 0.95
            },
            "web_search": {
                "available": True,
                "components": ["web_search", "get_search_results"],
                "confidence": 0.9
            },
            "text_generation": {
                "available": True,
                "components": ["generate_text", "draft_content"],
                "confidence": 0.85
            },
            "text_editing": {
                "available": True,
                "components": ["edit_text", "improve_content"],
                "confidence": 0.8
            }
        }
        
        # Assess each required capability
        assessment = {}
        overall_confidence = 1.0
        missing_capabilities = []
        
        for capability in required_capabilities:
            if capability in available_capabilities:
                assessment[capability] = available_capabilities[capability]
                overall_confidence *= available_capabilities[capability]["confidence"]
            else:
                missing_capabilities.append(capability)
                assessment[capability] = {
                    "available": False,
                    "components": [],
                    "confidence": 0.0
                }
                overall_confidence *= 0.1  # Penalize for missing capability
        
        # Calculate number of steps needed based on complexity
        if complexity == "low":
            estimated_steps = 1
        elif complexity == "medium":
            estimated_steps = 3
        else:  # high
            estimated_steps = 5
        
        # Return assessment
        return {
            "assessment": assessment,
            "missing_capabilities": missing_capabilities,
            "overall_confidence": overall_confidence,
            "estimated_steps": estimated_steps,
            "recommendation": "proceed" if not missing_capabilities else "fallback"
        }
        
    except Exception as e:
        logger.error(f"Error assessing capabilities: {str(e)}")
        return {
            "error": str(e),
            "assessment": {},
            "missing_capabilities": [],
            "overall_confidence": 0.0,
            "estimated_steps": 0,
            "recommendation": "error"
        }

@tool
async def reason_step_by_step(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs step-by-step reasoning about a user request, breaking down
    analysis into multiple steps with clear chain of thought.
    
    Args:
        input_data: Dictionary containing:
            - query: The user's request to reason about
            - intent_analysis: Optional intent analysis results to incorporate
            - focus: Optional focus areas for reasoning (e.g., "workflow", "capabilities")
            
    Returns:
        Dictionary containing detailed reasoning steps and conclusions:
        - reasoning_steps: List of reasoning steps
        - key_insights: List of important insights from reasoning
        - reasoning_summary: Summary of the reasoning process
        - recommended_actions: List of recommended next steps
        - dependencies: Required dependencies identified
    """
    try:
        query = input_data.get("query", "")
        intent_analysis = input_data.get("intent_analysis", {})
        focus = input_data.get("focus", "general")
        
        # This would ideally use a specialized LLM call for chain-of-thought 
        # But for our demo purposes, we'll mock the step-by-step reasoning
        
        # Identify the key aspects of the query
        primary_intent = intent_analysis.get("primary_intent", "general_query")
        complexity = intent_analysis.get("complexity", "low")
        
        # Mock reasoning steps based on intent and complexity
        reasoning_steps = []
        key_insights = []
        dependencies = []
        
        # Step 1: Analyze the query nature
        reasoning_steps.append(f"Step 1: Analyzing query nature - This appears to be a {complexity}-complexity {primary_intent} request.")
        if "weather" in query.lower():
            reasoning_steps.append("Step 2: Identified specific entities - The user is asking about weather information for a specific location.")
            key_insights.append("Weather information for a specific location is needed")
            dependencies.append("weather_api")
            reasoning_steps.append("Step 3: Determining execution path - This requires a simple API call to a weather service.")
            reasoning_steps.append("Step 4: Check for additional context - No additional context or follow-up seems required.")
            recommended_actions = ["Extract location entity", "Query weather API", "Format response"]
            reasoning_summary = "This is a straightforward weather query that can be handled by a simple weather lookup workflow."
            
        elif "research" in query.lower() and "article" in query.lower():
            reasoning_steps.append("Step 2: Identified multi-step task - The user wants to perform research and create content.")
            key_insights.append("Multiple sequential tasks requiring different tools")
            dependencies.extend(["web_search", "content_generation", "editing_capability"])
            reasoning_steps.append("Step 3: Determining execution path - This requires a multi-node execution graph with research, writing, and editing stages.")
            reasoning_steps.append("Step 4: Consider dependencies - Each step depends on the previous step's output.")
            recommended_actions = ["Perform web research", "Generate draft content", "Edit and refine content", "Deliver final result"]
            reasoning_summary = "This is a complex content creation task requiring multiple sequential processing steps and tools."
            
        else:
            reasoning_steps.append("Step 2: Analyzing requirements - This appears to be a general query or command.")
            key_insights.append("General request that may require conversation")
            dependencies.append("conversation_capability")
            reasoning_steps.append("Step 3: Determining execution path - A simple response using available information should suffice.")
            recommended_actions = ["Generate appropriate response"]
            reasoning_summary = "This is a general request that can be handled with a simple response node."
        
        return {
            "reasoning_steps": reasoning_steps,
            "key_insights": key_insights,
            "dependencies": dependencies,
            "recommended_actions": recommended_actions,
            "reasoning_summary": reasoning_summary
        }
    except Exception as e:
        logger.error(f"Error in step-by-step reasoning: {str(e)}")
        return {
            "error": str(e),
            "reasoning_steps": ["Error occurred during reasoning"],
            "reasoning_summary": f"Error: {str(e)}"
        } 
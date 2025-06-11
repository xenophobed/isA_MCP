from typing import Dict, Any, Optional, List
from datetime import datetime
from app.services.ai.tools.tools_manager import tools_manager
from app.services.agent.agent_manager import AgentManager
from app.services.agent.agent_factory import AgentFactory
from app.models.chat.graph_messages import (
    SemanticData,
    Entity,
    AspectSentiment
)
from app.config.config_manager import config_manager
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import logging
import json
import asyncio

logger = logging.getLogger(__name__)

REQUIRED_TRAVEL_INFO = [
    "destination",
    "travel_dates",
    "duration",
    "travelers",
    "budget",
    "preferences"
]

def intention_error_handler(state):
    """Handle intention analysis errors"""
    error = state.get("error")
    return {
        "messages": [{
            "content": f"Intention analysis error: {error}. Please try again later.",
            "type": "error"
        }]
    }

def validate_travel_info(result_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Validate travel information and update human interaction needs."""
    # Initialize current state
    current_state = {}
    
    # Extract information from entities
    for entity in result_dict.get('entities', []):
        if entity['type'] == 'DESTINATION':
            current_state['destination'] = entity['value']
        elif entity['type'] == 'TIME':
            current_state['travel_dates'] = entity['value']
        elif entity['type'] == 'DURATION':
            current_state['duration'] = entity['value']
        elif entity['type'] == 'BUDGET':
            current_state['budget'] = entity['value']
        elif entity['type'] == 'TRAVELERS':
            current_state['travelers'] = entity['value']
        elif entity['type'] == 'PREFERENCES':
            if 'preferences' not in current_state:
                current_state['preferences'] = []
            if isinstance(entity['value'], list):
                current_state['preferences'].extend(entity['value'])
            else:
                current_state['preferences'].append(entity['value'])
    
    # Update with user input if available
    user_input = result_dict.get('user_input', {})
    if user_input:
        # Validate user input
        if not user_input:
            logger.warning("Empty user input provided")
            result_dict['error'] = "Empty user input provided"
            current_state = {}  # Reset current state to force re-asking questions
        else:
            # Validate each field format
            if 'duration' in user_input and not any(c.isdigit() for c in user_input['duration']):
                logger.warning(f"Invalid duration format: {user_input['duration']}")
                del user_input['duration']
            if 'budget' in user_input and not any(c.isdigit() for c in user_input['budget']):
                logger.warning(f"Invalid budget format: {user_input['budget']}")
                del user_input['budget']
            if 'travelers' in user_input and not any(c.isdigit() for c in user_input['travelers']):
                logger.warning(f"Invalid travelers format: {user_input['travelers']}")
                del user_input['travelers']
            
            current_state.update(user_input)
    
    # Check for missing required information
    missing_info = []
    questions = []
    required_fields = ['destination', 'travel_dates', 'duration', 'travelers', 'budget', 'preferences']
    
    for field in required_fields:
        if field not in current_state or not current_state[field]:
            missing_info.append(field)
            questions.append(f"Could you please provide {field} for your travel plan?")
    
    # Update human interaction needs
    result_dict['human_interaction'] = {
        'needs_human_input': bool(missing_info),
        'missing_info': missing_info,
        'questions': questions,
        'current_state': current_state
    }
    
    # Create tool message if human input is needed
    if missing_info:
        result_dict['tool_message'] = ToolMessage(
            content=json.dumps({
                'type': 'human_interaction_needed',
                'questions': questions,
                'missing_info': missing_info,
                'current_state': current_state
            }),
            name='human_interaction',
            tool_call_id='human_interaction'
        )
    
    return result_dict

@tools_manager.register_tool(error_handler=intention_error_handler)
async def analyze_intention(
    message: str, 
    context: Optional[str] = None,
    user_input: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = 30  # Default timeout in seconds
) -> Dict[str, Any]:
    """Analyze user intention from message with human interaction support.
    
    @semantic:
        concept: intention-analysis
        domain: nlp-service
        type: real-time
    
    @functional:
        operation: analyze
        input: message:string, context:string(optional), user_input:dict(optional), timeout:int(optional)
        output: semantic_data:dict
    
    @context:
        usage: message-analysis
        prereq: valid_message
        constraint: llm_dependent
    """
    try:
        # Get AgentManager instance
        agent_manager = AgentManager()
        
        # Configure intention agent
        agent_config = {
            "model": {
                "model_name": "gpt-4o-mini",
                "provider": "yyds",
            },
            "prompt": {
                "template_path": "app/services/ai/prompt/templates",
                "prompt_name": "proxy/intention_node"
            }
        }
        
        # Create or get agent
        agent_id = "intention_analysis_agent"
        try:
            agent = await agent_manager.get_agent(agent_id)
        except ValueError:
            # Agent doesn't exist, create it
            agent = await agent_manager.create_agent(
                agent_type="customer_intent",
                name="意图分析助手",
                description="一个分析用户意图的代理",
                config=agent_config,
                agent_id=agent_id,
                persist=False
            )
        
        # Prepare input with user feedback if available
        input_data = {
            "question": message,
            "previous_messages": context or "",
            "user_input": user_input or {}
        }
        
        # Execute agent with timeout
        try:
            result = await asyncio.wait_for(
                agent_manager.execute_agent(agent_id, input_data),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Agent execution timed out after {timeout} seconds")
            return {
                "error": f"Request timed out after {timeout} seconds",
                "human_interaction": {
                    "needs_human_input": True,
                    "missing_info": ["timeout"],
                    "questions": ["The request timed out. Please try again."],
                    "current_state": {}
                }
            }
        
        # Convert to dict format
        if isinstance(result, SemanticData):
            result_dict = {
                "intents": result.intents,
                "entities": [
                    {
                        "type": e.type,
                        "value": e.value,
                        "confidence": 1.0
                    }
                    for e in result.entities
                ],
                "sentiments": [
                    {
                        "aspect": "overall",
                        "sentiment": result.sentiments[0].sentiment if result.sentiments else "NEUTRAL",
                        "confidence": 1.0
                    }
                ],
                "topics": result.topics,
            }
        else:
            result_dict = result

        # Add user input to result dict
        result_dict["user_input"] = user_input

        # Validate travel information and update human interaction needs
        result_dict = validate_travel_info(result_dict)

        # Log results
        logger.info(f"Intention analysis results: {result_dict}")
        
        return result_dict

    except Exception as e:
        logger.error(f"Error in intention analysis: {e}", exc_info=True)
        raise

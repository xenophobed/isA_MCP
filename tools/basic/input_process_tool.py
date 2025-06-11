import asyncio
import httpx
from typing import Dict, Any, Optional, Type
from app.services.agent.tools.tools_manager import tools_manager
from app.services.ai.models.ai_factory import AIFactory
from app.services.ai.models.base_provider import ModelType
from app.config.config_manager import config_manager
from langchain_core.tools import tool
from pydantic import BaseModel

logger = config_manager.get_logger(__name__)

class ImageInput(BaseModel):
    """Input schema for image processing"""
    image_url: str

class AudioInput(BaseModel):
    """Input schema for audio processing"""
    audio_url: str

def download_file(url: str) -> bytes:
    """Download file from URL"""
    try:
        with httpx.Client() as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content
    except Exception as e:
        logger.error(f"Error downloading file from {url}: {e}")
        raise

def input_error_handler(state):
    """Handle input processing tool errors"""
    error = state.get("error")
    return {
        "messages": [{
            "content": f"Input processing error: {error}. Please try again later.",
            "type": "error"
        }]
    }

@tools_manager.register_tool(error_handler=input_error_handler)
def process_image(image_url: str) -> str:
    """Process and analyze an image from a URL.
    
    @semantic:
        concept: image-analysis
        domain: vision-service
        type: real-time
    
    @functional:
        operation: analyze
        input: image_url:string
        output: analysis_result:string
    
    @context:
        usage: image-understanding
        prereq: valid_url,active_service
        constraint: api_dependent,url_required
    """
    try:
        # Download image data
        image_data = download_file(image_url)
        
        # Create vision service
        vision_service = AIFactory.get_instance().create_service(
            provider_name="yyds",
            model_type=ModelType.VISION,
            model_name="gpt-4-vision-preview"
        )
        
        # Create event loop for async operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run async operation in sync context
        result = loop.run_until_complete(vision_service.analyze_image(image_data, "What's in this image?"))
        
        # Clean up
        loop.close()
        
        return f"Image analysis result: {result}"
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise

@tools_manager.register_tool(error_handler=input_error_handler)
def process_audio(audio_url: str) -> str:
    """Process and transcribe audio from a URL.
    
    @semantic:
        concept: audio-transcription
        domain: audio-service
        type: real-time
    
    @functional:
        operation: transcribe
        input: audio_url:string
        output: transcription_result:string
    
    @context:
        usage: speech-to-text
        prereq: valid_url,active_service
        constraint: api_dependent,url_required
    """
    try:
        # Download audio data
        audio_data = download_file(audio_url)
        
        # Create audio service
        audio_service = AIFactory.get_instance().create_service(
            provider_name="yyds",
            model_type=ModelType.AUDIO,
            model_name="whisper-1"
        )
        
        # Create event loop for async operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run async operation in sync context
        result = loop.run_until_complete(audio_service.transcribe(audio_data))
        
        # Clean up
        loop.close()
        
        return f"Audio transcription: {result['text']}"
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        raise
    
    

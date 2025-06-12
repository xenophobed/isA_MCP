from typing import Optional, List, Dict
from .tools_manager import tools_manager
from app.config.config_manager import config_manager
from app.services.ai.models.ai_factory import AIFactory
import replicate
import logging
import aiohttp
from datetime import datetime
import io
import uuid
import json
import asyncio

logger = logging.getLogger(__name__)

def image_gen_error_handler(state):
    """Handle image generation tool errors"""
    error = state.get("error")
    return {
        "messages": [{
            "content": f"Image generation error: {error}. Please try again later.",
            "type": "error"
        }]
    }

async def _save_image_to_minio(image_url: str, bucket_name: str = "generated-images") -> str:
    """Save image to MinIO and return the storage path"""
    try:
        # Get MinIO client
        minio_client = await config_manager.get_storage_client()
        
        # Create bucket if it doesn't exist
        try:
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)
                # Set bucket policy to public read if needed
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                        }
                    ]
                }
                minio_client.set_bucket_policy(bucket_name, json.dumps(policy))
        except Exception as e:
            logger.error(f"Error creating bucket: {e}")
            raise
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{unique_id}.png"
        storage_path = f"images/generated/{filename}"
        
        # Download image from URL
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download image: {response.status}")
                image_data = await response.read()
        
        # Upload to MinIO
        minio_client.put_object(
            bucket_name,
            storage_path,
            io.BytesIO(image_data),
            len(image_data),
            content_type="image/png"
        )
        
        # Get the URL for the uploaded image
        # Assuming MinIO is configured with a public endpoint
        minio_config = config_manager.get_config('minio')
        endpoint = minio_config.ENDPOINT
        secure = minio_config.SECURE
        protocol = "https" if secure else "http"
        
        return f"{protocol}://{endpoint}/{bucket_name}/{storage_path}"
        
    except Exception as e:
        logger.error(f"Failed to save image to MinIO: {e}")
        raise

async def _generate_image_async(
    prompt: str,
    aspect_ratio: str = "1:1",
    num_outputs: int = 1,
    go_fast: bool = True
) -> List[str]:
    """Async implementation of image generation"""
    try:
        # Get LLM config and create Replicate service
        llm_config = config_manager.get_config('llm')
        replicate_service = await LLMFactory._create_replicate_service(llm_config)
        
        # Generate images using service
        image_outputs = await replicate_service.generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            num_outputs=num_outputs,
            go_fast=go_fast
        )
        
        # Save each image to MinIO and get URLs
        minio_urls = []
        for image_output in image_outputs:
            # Get the URL from the FileOutput object
            image_url = str(image_output)
            # Save to MinIO and get public URL
            minio_url = await _save_image_to_minio(image_url)
            minio_urls.append(minio_url)
            
        return minio_urls

    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        raise

@tools_manager.register_tool(error_handler=image_gen_error_handler)
def generate_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    num_outputs: int = 1,
    go_fast: bool = True
) -> List[str]:
    """Generate product images using Flux model.
    
    @semantic:
        concept: image-generation
        domain: product-visualization
        type: generative
    
    @functional:
        operation: create
        input: prompt:string,aspect_ratio:string,num_outputs:int
        output: image_urls:list
    
    @context:
        usage: marketing-content
        prereq: valid_prompt,replicate_access
        constraint: api_dependent,quality_dependent
    """
    # Create event loop if it doesn't exist
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_generate_image_async(
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        num_outputs=num_outputs,
        go_fast=go_fast
    ))

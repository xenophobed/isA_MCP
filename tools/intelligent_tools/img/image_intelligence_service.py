#!/usr/bin/env python3
"""
Atomic Image Intelligence Service
Specialized image processing capabilities using ISA Model
"""

import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ImageTask:
    """Image processing task configuration"""

    task_type: str
    model: str
    parameters: Dict[str, Any]
    input_data: Any
    cost_estimate: float = 0.0


class AtomicImageIntelligence:
    """Atomic Image Intelligence Service with specialized capabilities"""

    def __init__(self):
        self.service_name = "atomic_image_intelligence"
        self._client = None

        # Task type configurations
        self.task_configs = {
            "text_to_image": {
                "model": "flux-schnell",
                "provider": "replicate",
                "task": "generate",
                "cost_per_1000": 3.0,
            },
            "image_to_image": {
                "model": "flux-kontext-pro",
                "provider": "replicate",
                "task": "img2img",
                "cost_per_image": 0.04,
            },
            "style_transfer": {
                "model": "flux-kontext-pro",
                "provider": "replicate",
                "task": "img2img",
                "cost_per_image": 0.04,
            },
            "sticker_generation": {
                "model": "sticker-maker",
                "provider": "replicate",
                "task": "generate",
                "cost_per_image": 0.0024,
            },
            "face_swap": {
                "model": "face-swap",
                "provider": "replicate",
                "task": "face_swap",
                "cost_per_image": 0.04,
            },
            "professional_headshot": {
                "model": "flux-kontext-pro",
                "provider": "replicate",
                "task": "img2img",
                "cost_per_image": 0.04,
            },
            "photo_inpainting": {
                "model": "flux-kontext-pro",
                "provider": "replicate",
                "task": "img2img",
                "cost_per_image": 0.04,
            },
            "photo_outpainting": {
                "model": "flux-kontext-pro",
                "provider": "replicate",
                "task": "img2img",
                "cost_per_image": 0.04,
            },
            "emoji_generation": {
                "model": "sticker-maker",
                "provider": "replicate",
                "task": "generate",
                "cost_per_image": 0.0024,
            },
        }

    async def _get_client(self):
        """Lazy load ISA client"""
        if self._client is None:
            from core.clients.model_client import get_isa_client

            self._client = await get_isa_client()
        return self._client

    def _validate_task_type(self, task_type: str) -> bool:
        """Validate if task type is supported"""
        return task_type in self.task_configs

    def _estimate_cost(self, task_type: str, count: int = 1) -> float:
        """Estimate cost for task"""
        config = self.task_configs.get(task_type, {})

        if "cost_per_1000" in config:
            return (config["cost_per_1000"] / 1000) * count
        elif "cost_per_image" in config:
            return config["cost_per_image"] * count

        return 0.0

    async def _execute_image_task(self, task: ImageTask) -> Dict[str, Any]:
        """Execute a single image task"""
        try:
            config = self.task_configs[task.task_type]

            # Call ISA client using new images API
            client = await self._get_client()

            # Use OpenAI-compatible images.generate() interface
            image_response = await client.images.generate(
                prompt=task.input_data,
                model=config["model"],
                provider=config["provider"],
                **task.parameters,
            )

            # Extract URLs from response
            image_urls = [item.url for item in image_response.data]
            if isinstance(image_urls, str):
                image_urls = [image_urls]
            elif not image_urls and "url" in result_data:
                image_urls = [result_data["url"]]

            if not image_urls:
                raise Exception("No image URLs returned from ISA Model")

            # Get billing info and cost
            cost = result_data.get("cost_usd", 0.0)
            billing_info = response.get("metadata", {}).get("billing", {})

            return {
                "success": True,
                "urls": image_urls,
                "cost": cost,
                "metadata": {
                    "task_type": task.task_type,
                    "model": config["model"],
                    "billing": billing_info,
                },
            }

        except Exception as e:
            logger.error(f"Image task execution failed ({task.task_type}): {e}")
            return {"success": False, "error": str(e), "task_type": task.task_type}

    async def generate_text_to_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        num_images: int = 1,
        steps: int = 3,
    ) -> Dict[str, Any]:
        """Generate images from text prompt using FLUX Schnell"""
        task = ImageTask(
            task_type="text_to_image",
            model="flux-schnell",
            parameters={
                "width": width,
                "height": height,
                "num_inference_steps": steps,
                "num_images": num_images,
            },
            input_data=prompt,
        )

        return await self._execute_image_task(task)

    async def transform_image(
        self,
        prompt: str,
        init_image_url: str,
        strength: float = 0.8,
        width: int = 1024,
        height: int = 1024,
    ) -> Dict[str, Any]:
        """Transform existing image with new prompt"""
        task = ImageTask(
            task_type="image_to_image",
            model="flux-kontext-pro",
            parameters={
                "init_image": init_image_url,
                "strength": strength,
                "width": width,
                "height": height,
            },
            input_data=prompt,
        )

        return await self._execute_image_task(task)

    async def transfer_style(
        self, content_image_url: str, style_prompt: str, strength: float = 0.7
    ) -> Dict[str, Any]:
        """Transfer style to existing image"""
        task = ImageTask(
            task_type="style_transfer",
            model="flux-kontext-pro",
            parameters={"init_image": content_image_url, "strength": strength},
            input_data=f"Apply this style: {style_prompt}",
        )

        return await self._execute_image_task(task)

    async def generate_sticker(
        self,
        prompt: str,
        width: int = 1152,
        height: int = 1152,
        steps: int = 4,
        output_format: str = "webp",
    ) -> Dict[str, Any]:
        """Generate cute sticker design"""
        task = ImageTask(
            task_type="sticker_generation",
            model="sticker-maker",
            parameters={
                "width": width,
                "height": height,
                "num_inference_steps": steps,
                "output_format": output_format,
                "output_quality": 100,
            },
            input_data=f"cute {prompt} sticker design",
        )

        return await self._execute_image_task(task)

    async def swap_faces(
        self,
        source_face_url: str,
        target_image_url: str,
        hair_source: str = "target",
        user_gender: str = "default",
    ) -> Dict[str, Any]:
        """Swap faces between images"""
        task = ImageTask(
            task_type="face_swap",
            model="face-swap",
            parameters={
                "target_image": target_image_url,
                "hair_source": hair_source,
                "user_gender": user_gender,
            },
            input_data=source_face_url,
        )

        return await self._execute_image_task(task)

    async def create_professional_headshot(
        self,
        input_image_url: str,
        style: str = "professional business headshot",
        strength: float = 0.6,
    ) -> Dict[str, Any]:
        """Create professional headshot from casual photo"""
        task = ImageTask(
            task_type="professional_headshot",
            model="flux-kontext-pro",
            parameters={"init_image": input_image_url, "strength": strength},
            input_data=f"Transform into {style}, high quality, professional lighting",
        )

        return await self._execute_image_task(task)

    async def inpaint_photo(
        self, image_url: str, inpaint_prompt: str, strength: float = 0.8
    ) -> Dict[str, Any]:
        """Fill or modify specific areas of an image"""
        task = ImageTask(
            task_type="photo_inpainting",
            model="flux-kontext-pro",
            parameters={"init_image": image_url, "strength": strength},
            input_data=f"Inpaint: {inpaint_prompt}",
        )

        return await self._execute_image_task(task)

    async def outpaint_photo(
        self, image_url: str, expand_prompt: str, strength: float = 0.7
    ) -> Dict[str, Any]:
        """Expand image beyond original boundaries"""
        task = ImageTask(
            task_type="photo_outpainting",
            model="flux-kontext-pro",
            parameters={"init_image": image_url, "strength": strength},
            input_data=f"Expand image: {expand_prompt}",
        )

        return await self._execute_image_task(task)

    async def generate_emoji(self, description: str, style: str = "cute emoji") -> Dict[str, Any]:
        """Generate custom emoji"""
        task = ImageTask(
            task_type="emoji_generation",
            model="sticker-maker",
            parameters={
                "width": 512,
                "height": 512,
                "num_inference_steps": 4,
                "output_format": "png",
                "output_quality": 100,
            },
            input_data=f"{style} of {description}",
        )

        return await self._execute_image_task(task)

    async def batch_process(
        self, tasks: List[ImageTask], max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """Process multiple image tasks concurrently"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_task(task):
            async with semaphore:
                return await self._execute_image_task(task)

        results = await asyncio.gather(
            *[process_task(task) for task in tasks], return_exceptions=True
        )

        # Convert exceptions to error dictionaries
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {"success": False, "error": str(result), "task_type": tasks[i].task_type}
                )
            else:
                processed_results.append(result)

        return processed_results

    def get_cost_estimate(self, task_type: str, count: int = 1) -> float:
        """Get cost estimate for task"""
        if not self._validate_task_type(task_type):
            return 0.0

        return self._estimate_cost(task_type, count)

    def list_capabilities(self) -> List[str]:
        """List all available image processing capabilities"""
        return list(self.task_configs.keys())

    def get_task_info(self, task_type: str) -> Dict[str, Any]:
        """Get detailed information about a task type"""
        if not self._validate_task_type(task_type):
            return {}

        config = self.task_configs[task_type]
        return {
            "task_type": task_type,
            "model": config["model"],
            "provider": config["provider"],
            "estimated_cost": self._estimate_cost(task_type, 1),
            "description": self._get_task_description(task_type),
        }

    def _get_task_description(self, task_type: str) -> str:
        """Get human-readable description of task type"""
        descriptions = {
            "text_to_image": "Generate images from text descriptions",
            "image_to_image": "Transform existing images with new prompts",
            "style_transfer": "Apply artistic styles to existing images",
            "sticker_generation": "Create cute sticker designs",
            "face_swap": "Swap faces between different images",
            "professional_headshot": "Convert casual photos to professional headshots",
            "photo_inpainting": "Fill or modify specific areas within images",
            "photo_outpainting": "Expand images beyond original boundaries",
            "emoji_generation": "Create custom emoji designs",
        }
        return descriptions.get(task_type, "Unknown task type")


# Global service instance
_image_intelligence = AtomicImageIntelligence()

logger.debug("Atomic Image Intelligence Service initialized")

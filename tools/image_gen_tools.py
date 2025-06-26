#!/usr/bin/env python
"""
Image Generation Tools for MCP Server
Handles image generation operations using isa_model framework
"""
import json
import sqlite3
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import os

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from core.monitoring import monitor_manager

# Import isa_model
from isa_model.inference import AIFactory

logger = get_logger(__name__)

def register_image_gen_tools(mcp):
    """Register all image generation tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def generate_image(
        prompt: str, 
        image_type: str = "t2i",
        width: int = 1024, 
        height: int = 1024,
        save_to_memory: bool = True,
        user_id: str = "default"
    ) -> str:
        """Generate image from text prompt using isa_model
        
        This tool creates images from text descriptions using AI models,
        supporting various image types and customizable dimensions.
        
        Keywords: image, generate, ai, picture, art, creation, text-to-image
        Category: image
        """
        
        try:
            # Create image generation service
            img = AIFactory().get_img(type=image_type)
            
            # Generate image
            result = await img.generate_image(
                prompt=prompt,
                width=width,
                height=height
            )
            
            # Close the service
            await img.close()
            
            # Save generation record to database if requested
            generation_data = {
                "prompt": prompt,
                "image_type": image_type,
                "width": width,
                "height": height,
                "cost_usd": result.get('cost_usd', 0.0),
                "urls": result.get('urls', []),
                "generated_at": datetime.now().isoformat(),
                "user_id": user_id
            }
            
            if save_to_memory:
                await _save_generation_record(generation_data)
            
            # Prepare response
            response = {
                "status": "success",
                "action": "generate_image",
                "data": {
                    "prompt": prompt,
                    "image_type": image_type,
                    "dimensions": f"{width}x{height}",
                    "image_urls": result.get('urls', []),
                    "cost_usd": result.get('cost_usd', 0.0),
                    "generated_by": user_id
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Image generated: '{prompt}' by {user_id}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {
                "status": "error",
                "action": "generate_image",
                "data": {
                    "prompt": prompt,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error(f"Image generation failed: {e}")
            return json.dumps(error_response)

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def generate_image_to_file(
        prompt: str,
        output_path: str,
        image_type: str = "t2i",
        width: int = 1024,
        height: int = 1024,
        user_id: str = "default"
    ) -> str:
        """Generate image and save directly to file
        
        This tool generates images from text prompts and saves them
        directly to a specified file path on the local filesystem.
        
        Keywords: image, generate, file, save, path, export, creation
        Category: image
        """
        
        try:
            # Create image generation service
            img = AIFactory().get_img(type=image_type)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Generate and save image
            result = await img.generate_image_to_file(
                prompt=prompt,
                output_path=output_path,
                width=width,
                height=height
            )
            
            # Close the service
            await img.close()
            
            # Save generation record
            generation_data = {
                "prompt": prompt,
                "image_type": image_type,
                "width": width,
                "height": height,
                "cost_usd": result.get('cost_usd', 0.0),
                "file_path": result.get('file_path', output_path),
                "generated_at": datetime.now().isoformat(),
                "user_id": user_id
            }
            
            await _save_generation_record(generation_data)
            
            response = {
                "status": "success",
                "action": "generate_image_to_file",
                "data": {
                    "prompt": prompt,
                    "file_path": result.get('file_path', output_path),
                    "cost_usd": result.get('cost_usd', 0.0),
                    "generated_by": user_id
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Image saved to file: {output_path} by {user_id}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {
                "status": "error",
                "action": "generate_image_to_file",
                "data": {
                    "prompt": prompt,
                    "output_path": output_path,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error(f"Image generation to file failed: {e}")
            return json.dumps(error_response)

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def image_to_image(
        prompt: str,
        init_image_path: str,
        strength: float = 0.8,
        save_to_memory: bool = True,
        user_id: str = "default"
    ) -> str:
        """Transform existing image using I2I model
        
        This tool modifies existing images based on text prompts,
        allowing for image editing and style transformation.
        
        Keywords: image, transform, edit, modify, i2i, style, change
        Category: image
        """
        
        try:
            # Create I2I service
            img = AIFactory().get_img(type="i2i")
            
            # Transform image
            result = await img.image_to_image(
                prompt=prompt,
                init_image=init_image_path,
                strength=strength
            )
            
            # Close the service
            await img.close()
            
            # Save generation record
            generation_data = {
                "prompt": prompt,
                "image_type": "i2i",
                "init_image_path": init_image_path,
                "strength": strength,
                "cost_usd": result.get('cost_usd', 0.0),
                "urls": result.get('urls', []),
                "generated_at": datetime.now().isoformat(),
                "user_id": user_id
            }
            
            if save_to_memory:
                await _save_generation_record(generation_data)
            
            response = {
                "status": "success",
                "action": "image_to_image",
                "data": {
                    "prompt": prompt,
                    "init_image": init_image_path,
                    "strength": strength,
                    "image_urls": result.get('urls', []),
                    "cost_usd": result.get('cost_usd', 0.0),
                    "generated_by": user_id
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"I2I transformation: '{prompt}' by {user_id}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {
                "status": "error",
                "action": "image_to_image",
                "data": {
                    "prompt": prompt,
                    "init_image": init_image_path,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error(f"I2I transformation failed: {e}")
            return json.dumps(error_response)

    @mcp.tool()
    @security_manager.security_check
    async def search_image_generations(
        query: str = "",
        user_id: str = "default",
        limit: int = 10
    ) -> str:
        """Search through image generation history
        
        This tool searches through previously generated images
        and their metadata to find specific creations.
        
        Keywords: search, image, history, find, query, generations, lookup
        Category: image
        """
        
        try:
            conn = sqlite3.connect("memory.db")
            
            if query:
                sql = """
                    SELECT prompt, image_type, cost_usd, file_path, urls, generated_at, user_id
                    FROM image_generations 
                    WHERE (prompt LIKE ? OR image_type LIKE ?) AND user_id = ?
                    ORDER BY generated_at DESC LIMIT ?
                """
                params = [f"%{query}%", f"%{query}%", user_id, limit]
            else:
                sql = """
                    SELECT prompt, image_type, cost_usd, file_path, urls, generated_at, user_id
                    FROM image_generations 
                    WHERE user_id = ?
                    ORDER BY generated_at DESC LIMIT ?
                """
                params = [user_id, limit]
            
            cursor = conn.execute(sql, params)
            results = cursor.fetchall()
            
            generations = []
            for prompt, image_type, cost_usd, file_path, urls, generated_at, uid in results:
                generations.append({
                    "prompt": prompt,
                    "image_type": image_type,
                    "cost_usd": cost_usd,
                    "file_path": file_path,
                    "urls": json.loads(urls) if urls else [],
                    "generated_at": generated_at,
                    "user_id": uid
                })
            
            conn.close()
            
            response = {
                "status": "success",
                "action": "search_image_generations",
                "data": {
                    "query": query,
                    "results": generations,
                    "count": len(generations)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Image generation search: '{query}' found {len(generations)} results")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {
                "status": "error",
                "action": "search_image_generations",
                "data": {
                    "query": query,
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error(f"Image generation search failed: {e}")
            return json.dumps(error_response)

async def _save_generation_record(generation_data: Dict[str, Any]):
    """Save image generation record to database"""
    
    try:
        conn = sqlite3.connect("memory.db")
        
        # Create table if not exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS image_generations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                image_type TEXT NOT NULL,
                width INTEGER,
                height INTEGER,
                cost_usd REAL,
                file_path TEXT,
                urls TEXT,
                init_image_path TEXT,
                strength REAL,
                generated_at TEXT NOT NULL,
                user_id TEXT NOT NULL
            )
        """)
        
        # Insert generation record
        conn.execute("""
            INSERT INTO image_generations 
            (prompt, image_type, width, height, cost_usd, file_path, urls, init_image_path, strength, generated_at, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            generation_data.get('prompt'),
            generation_data.get('image_type'),
            generation_data.get('width'),
            generation_data.get('height'),
            generation_data.get('cost_usd', 0.0),
            generation_data.get('file_path'),
            json.dumps(generation_data.get('urls', [])),
            generation_data.get('init_image_path'),
            generation_data.get('strength'),
            generation_data.get('generated_at'),
            generation_data.get('user_id')
        ))
        
        conn.commit()
        conn.close()
        
        logger.info("Image generation record saved to database")
        
    except Exception as e:
        logger.error(f"Failed to save generation record: {e}")

def initialize_image_generation_db():
    """Initialize image generation database tables"""
    
    try:
        conn = sqlite3.connect("memory.db")
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS image_generations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                image_type TEXT NOT NULL,
                width INTEGER,
                height INTEGER,
                cost_usd REAL,
                file_path TEXT,
                urls TEXT,
                init_image_path TEXT,
                strength REAL,
                generated_at TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Image generation database tables initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize image generation database: {e}")

logger.info("Image generation tools registered successfully")
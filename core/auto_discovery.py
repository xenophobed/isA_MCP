#!/usr/bin/env python3
"""
Automatic Discovery System for MCP Tools, Prompts, and Resources
Automatically discovers, extracts docstrings, embeds, and registers everything
"""

import os
import ast
import inspect
import importlib.util
from typing import Dict, List, Any, Callable, Optional
from pathlib import Path
import asyncio
from mcp.server.fastmcp import FastMCP

from core.logging import get_logger

logger = get_logger(__name__)

class AutoDiscoverySystem:
    """Automatically discover and register tools, prompts, and resources"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir).resolve()
        self.tools_dir = self.base_dir / "tools"
        self.prompts_dir = self.base_dir / "prompts" 
        self.resources_dir = self.base_dir / "resources"
        
        self.discovered_tools: Dict[str, Dict[str, Any]] = {}
        self.discovered_prompts: Dict[str, Dict[str, Any]] = {}
        self.discovered_resources: Dict[str, Dict[str, Any]] = {}

    def extract_docstring_metadata(self, docstring: str) -> Dict[str, Any]:
        """Extract metadata from function docstring"""
        if not docstring:
            return {"description": "", "keywords": [], "usage": ""}
        
        lines = [line.strip() for line in docstring.strip().split('\n') if line.strip()]
        
        # First non-empty line is description
        description = lines[0] if lines else ""
        
        keywords = []
        usage = ""
        
        for line in lines:
            if line.startswith("Keywords:"):
                keywords_text = line.replace("Keywords:", "").strip()
                keywords = [kw.strip() for kw in keywords_text.split(',')]
            elif line.startswith("Usage:"):
                usage = line.replace("Usage:", "").strip()
        
        # Auto-extract keywords from description if not explicitly provided
        if not keywords and description:
            # Simple keyword extraction from description
            words = description.lower().split()
            common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might', 'must', 'this', 'that', 'these', 'those'}
            keywords = [word for word in words if len(word) > 3 and word not in common_words][:5]
        
        return {
            "description": description,
            "keywords": keywords,
            "usage": usage
        }

    def discover_functions_in_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Discover functions with @mcp.tool() decorator in a Python file"""
        functions = []
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Use ast.walk to find ALL function definitions (including nested ones)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if function has @mcp.tool() decorator
                    has_mcp_decorator = False
                    for decorator in node.decorator_list:
                        if (isinstance(decorator, ast.Call) and 
                            isinstance(decorator.func, ast.Attribute) and
                            decorator.func.attr == 'tool'):
                            has_mcp_decorator = True
                            break
                        elif (isinstance(decorator, ast.Attribute) and 
                              decorator.attr == 'tool'):
                            has_mcp_decorator = True
                            break
                    
                    if has_mcp_decorator:
                        # Extract docstring
                        docstring = ""
                        if (node.body and isinstance(node.body[0], ast.Expr) and 
                            isinstance(node.body[0].value, ast.Constant)):
                            docstring = node.body[0].value.value
                        
                        # Extract metadata
                        metadata = self.extract_docstring_metadata(docstring)
                        
                        functions.append({
                            "name": node.name,
                            "file": str(file_path),
                            "docstring": docstring,
                            "description": metadata["description"],
                            "keywords": metadata["keywords"],
                            "usage": metadata["usage"],
                            "type": "tool"
                        })
        
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
        
        return functions


    


    def discover_tools(self) -> Dict[str, Dict[str, Any]]:
        """Auto-discover all tools in tools directory using multiple approaches"""
        logger.info(f"🔍 Discovering tools in {self.tools_dir}")
        
        tools = {}
        
        if not self.tools_dir.exists():
            logger.warning(f"Tools directory {self.tools_dir} does not exist")
            return tools
        
        # Approach 1: Try AST-based discovery for top-level tools
        logger.info(f"🔍 Using AST discovery for top-level tools...")
        for python_file in self.tools_dir.rglob("*.py"):
            if python_file.name.startswith("__"):
                continue
            
            # CRITICAL: Skip ML models to prevent mutex lock issues
            if any(ml_path in str(python_file) for ml_path in ["ml_models", "deep_learning", "sota_models", "real_sota"]):
                logger.warning(f"⚠️ Skipping ML module {python_file.name} to prevent mutex lock")
                continue
                
            # logger.info(f"  📄 Scanning {python_file.name}")  # 减少冷余日志
            functions = self.discover_functions_in_file(python_file)
            
            for func_info in functions:
                tool_name = func_info["name"]
                tools[tool_name] = func_info
                # logger.info(f"    🔧 Found tool: {tool_name}")  # 减少冷余日志
        
        logger.info(f"✅ Discovered {len(tools)} tools total")
        
        self.discovered_tools = tools
        return tools

    def discover_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Auto-discover all prompts in prompts directory"""
        logger.info(f"🔍 Discovering prompts in {self.prompts_dir}")
        
        prompts = {}
        
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory {self.prompts_dir} does not exist")
            return prompts
        
        # Walk through all Python files in prompts directory
        for python_file in self.prompts_dir.rglob("*.py"):
            if python_file.name.startswith("__"):
                continue
                
            # logger.info(f"  📄 Scanning {python_file.name}")  # 减少冷余日志
            
            try:
                # Import module to get prompt variables
                spec = importlib.util.spec_from_file_location("prompt_module", python_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find all prompt variables (strings ending with _prompt)
                    for attr_name in dir(module):
                        if attr_name.endswith("_prompt") and not attr_name.startswith("_"):
                            prompt_content = getattr(module, attr_name)
                            if isinstance(prompt_content, str):
                                # Extract keywords from prompt name and content
                                keywords = attr_name.replace("_prompt", "").split("_")
                                # Add keywords from content (first 50 words)
                                content_words = prompt_content.lower().split()[:50]
                                keywords.extend([w for w in content_words if len(w) > 4])
                                keywords = list(set(keywords))  # Remove duplicates
                                
                                prompts[attr_name] = {
                                    "name": attr_name,
                                    "file": str(python_file),
                                    "content": prompt_content,
                                    "description": f"Prompt for {attr_name.replace('_', ' ')}",
                                    "keywords": keywords[:10],  # Limit to 10 keywords
                                    "type": "prompt"
                                }
                                logger.info(f"    📝 Found prompt: {attr_name}")
            
            except Exception as e:
                logger.error(f"Error processing prompts file {python_file}: {e}")
        
        logger.info(f"✅ Discovered {len(prompts)} prompts")
        self.discovered_prompts = prompts
        return prompts

    def discover_resources(self) -> Dict[str, Dict[str, Any]]:
        """Auto-discover all resources in resources directory"""
        logger.info(f"🔍 Discovering resources in {self.resources_dir}")
        
        resources = {}
        
        if not self.resources_dir.exists():
            logger.warning(f"Resources directory {self.resources_dir} does not exist")
            return resources
        
        # Walk through all Python files in resources directory
        for python_file in self.resources_dir.rglob("*.py"):
            if python_file.name.startswith("__"):
                continue
                
            # logger.info(f"  📄 Scanning {python_file.name}")  # 减少冷余日志
            functions = self.discover_functions_in_file(python_file)
            
            # Also look for resource variables or classes
            try:
                spec = importlib.util.spec_from_file_location("resource_module", python_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find resource functions or variables
                    for attr_name in dir(module):
                        if not attr_name.startswith("_"):
                            attr_value = getattr(module, attr_name)
                            if callable(attr_value) and hasattr(attr_value, '__doc__'):
                                metadata = self.extract_docstring_metadata(attr_value.__doc__ or "")
                                resources[attr_name] = {
                                    "name": attr_name,
                                    "file": str(python_file),
                                    "description": metadata["description"] or f"Resource: {attr_name}",
                                    "keywords": metadata["keywords"] or attr_name.split("_"),
                                    "type": "resource"
                                }
                                # logger.info(f"    📊 Found resource: {attr_name}")  # 减少冷余日志
            
            except Exception as e:
                logger.error(f"Error processing resources file {python_file}: {e}")
        
        logger.info(f"✅ Discovered {len(resources)} resources")
        self.discovered_resources = resources
        return resources

    async def auto_register_with_mcp(self, mcp: FastMCP, config: Optional[Dict[str, Any]] = None):
        """Automatically register all discovered items with MCP server"""
        config = config or {}
        
        logger.info("🚀 Auto-registering all discovered items with MCP server")
        
        # Register tools from tool modules
        registered_count = 0
        tool_files_processed = set()
        
        # Get all Python files in tools directory
        for python_file in self.tools_dir.rglob("*.py"):
            if python_file.name.startswith("__"):
                continue
                
            # Skip service files, utility files, and disabled directories, BUT include *_tools.py files
            if any(skip in str(python_file) for skip in ["__pycache__", "disabled"]):
                continue
            # Skip services directory UNLESS it's a *_tools.py file
            if "services" in str(python_file) and not python_file.name.endswith("_tools.py"):
                continue
            
            # CRITICAL: Skip ML models to prevent mutex lock issues
            if any(ml_path in str(python_file) for ml_path in ["ml_models", "deep_learning", "sota_models", "real_sota"]):
                logger.warning(f"⚠️ Skipping ML module {python_file.name} to prevent mutex lock")
                continue
            # Skip client folder but not client_interaction_tools.py
            if "/client" in str(python_file) and "client_interaction_tools.py" not in str(python_file):
                continue
                
            try:
                module_name = python_file.stem
                register_func_name = f"register_{module_name}"
                
                # Dynamic import
                spec = importlib.util.spec_from_file_location(module_name, python_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Try to find and call register function
                    if hasattr(module, register_func_name):
                        register_func = getattr(module, register_func_name)
                        
                        # Call the register function with MCP instance
                        register_func(mcp)
                        registered_count += 1
                        tool_files_processed.add(python_file.name)
                        logger.info(f"  ✅ Registered tools from {module_name}")
                    else:
                        # Check if file has any @mcp.tool decorated functions
                        has_tools = self._check_for_mcp_tools(python_file)
                        if has_tools:
                            logger.warning(f"  ⚠️ {module_name} has tools but no register function")
                        else:
                            logger.debug(f"  ⏭️ Skipping {module_name} (no tools found)")
            
            except Exception as e:
                logger.error(f"  ❌ Failed to register tools from {python_file.name}: {e}")
        
        # Register prompts from prompt modules
        prompt_files_processed = set()
        for python_file in self.prompts_dir.rglob("*.py"):
            if python_file.name.startswith("__"):
                continue
                
            try:
                module_name = python_file.stem
                register_func_name = f"register_{module_name}"
                
                # Dynamic import
                spec = importlib.util.spec_from_file_location(module_name, python_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Try to find and call register function
                    if hasattr(module, register_func_name):
                        register_func = getattr(module, register_func_name)
                        
                        # Call the register function with MCP instance
                        register_func(mcp)
                        prompt_files_processed.add(python_file.name)
                        logger.info(f"  ✅ Registered prompts from {module_name}")
            
            except Exception as e:
                logger.error(f"  ❌ Failed to register prompts from {python_file.name}: {e}")
        
        # Register resources from resource modules
        resource_files_processed = set()
        for python_file in self.resources_dir.rglob("*.py"):
            if python_file.name.startswith("__"):
                continue
                
            try:
                module_name = python_file.stem
                register_func_name = f"register_{module_name}"
                
                # Dynamic import
                spec = importlib.util.spec_from_file_location(module_name, python_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Try to find and call register function
                    if hasattr(module, register_func_name):
                        register_func = getattr(module, register_func_name)
                        
                        # Call the register function with MCP instance
                        # Handle both sync and async functions
                        if asyncio.iscoroutinefunction(register_func):
                            # If it's an async function, await it
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    # We're in an async context, create a task
                                    asyncio.create_task(register_func(mcp))
                                else:
                                    # Run it in the loop
                                    loop.run_until_complete(register_func(mcp))
                            except:
                                # Fallback: run in new event loop
                                asyncio.run(register_func(mcp))
                        else:
                            # Sync function, call directly
                            register_func(mcp)
                        
                        resource_files_processed.add(python_file.name)
                        logger.info(f"  ✅ Registered resources from {module_name}")
            
            except Exception as e:
                logger.error(f"  ❌ Failed to register resources from {python_file.name}: {e}")
        
        # Register Composio Bridge if available
        composio_tools_metadata = {}
        try:
            logger.info("🌉 Attempting to register Composio Bridge...")
            from tools.services.composio_service.composio_mcp_bridge import register_composio_bridge
            composio_tools_metadata = register_composio_bridge(mcp)
            
            # 将 Composio 工具元数据加入索引
            if composio_tools_metadata:
                logger.info(f"  📊 Indexing {len(composio_tools_metadata)} Composio tools for search...")
                for tool_name, tool_meta in composio_tools_metadata.items():
                    self.discovered_tools[tool_name] = {
                        "name": tool_name,
                        "description": tool_meta.get("description", ""),
                        "category": tool_meta.get("category", "integration"),
                        "keywords": tool_meta.get("keywords", []),
                        "source": "composio_dynamic",
                        "docstring": tool_meta.get("description", "")
                    }
                logger.info(f"  ✅ Indexed {len(composio_tools_metadata)} Composio tools for search")
            
            logger.info("  ✅ Composio Bridge integration registered")
        except ImportError as e:
            logger.info("  ⚠️ Composio Bridge not available (this is normal if not configured)")
        except Exception as e:
            logger.error(f"  ❌ Failed to register Composio Bridge: {e}")
        
        # Also discover for metadata purposes
        self.discover_tools()
        self.discover_prompts() 
        self.discover_resources()
        
        logger.info(f"🎉 Auto-registration complete:")
        logger.info(f"  🔧 Tool modules: {registered_count}")
        logger.info(f"  📝 Prompt modules: {len(prompt_files_processed)}")
        logger.info(f"  📊 Resource modules: {len(resource_files_processed)}")
        logger.info(f"📁 Files processed:")
        logger.info(f"  Tools: {list(tool_files_processed)}")
        logger.info(f"  Prompts: {list(prompt_files_processed)}")
        logger.info(f"  Resources: {list(resource_files_processed)}")
        logger.info(f"📊 Discovery summary:")
        logger.info(f"  🔧 Tools discovered: {len(self.discovered_tools)}")
        logger.info(f"  📝 Prompts: {len(self.discovered_prompts)}")
        logger.info(f"  📊 Resources: {len(self.discovered_resources)}")
    
    def _check_for_mcp_tools(self, file_path: Path) -> bool:
        """Check if a file contains @mcp.tool decorated functions"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple text search for @mcp.tool
            return "@mcp.tool" in content
        except:
            return False

    def get_all_metadata(self) -> Dict[str, Any]:
        """Get all discovered metadata for embedding and similarity matching"""
        return {
            "tools": self.discovered_tools,
            "prompts": self.discovered_prompts,
            "resources": self.discovered_resources
        }
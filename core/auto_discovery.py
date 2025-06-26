#!/usr/bin/env python3
"""
Automatic Discovery System for MCP Tools, Prompts, and Resources
Automatically discovers, extracts docstrings, embeds, and registers everything
"""

import os
import ast
import inspect
import importlib.util
from typing import Dict, List, Any, Callable
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

    def discover_tools_from_registered_modules(self) -> Dict[str, Dict[str, Any]]:
        """Alternative approach: Extract tool metadata from registered modules by importing them"""
        tools = {}
        
        logger.info(f"🔍 Discovering tools from registered modules")
        
        # Get all Python files in tools directory
        for python_file in self.tools_dir.rglob("*.py"):
            if python_file.name.startswith("__"):
                continue
                
            # Skip service files and utility files
            if any(skip in str(python_file) for skip in ["services", "client", "__pycache__"]):
                continue
                
            try:
                module_name = python_file.stem
                register_func_name = f"register_{module_name}"
                
                # Dynamic import
                spec = importlib.util.spec_from_file_location(module_name, python_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # If module has register function, try to extract tool metadata from it
                    if hasattr(module, register_func_name):
                        logger.info(f"  📄 Extracting tools from {module_name}")
                        
                        # Parse the file content to find nested tool functions
                        with open(python_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Look for function definitions inside register function
                        lines = content.split('\n')
                        in_register_function = False
                        found_mcp_tool_decorator = False
                        current_function_name = None
                        current_docstring = ""
                        collecting_docstring = False
                        
                        for i, line in enumerate(lines):
                            stripped = line.strip()
                            
                            # Check if we're entering the register function
                            if f"def {register_func_name}" in line:
                                in_register_function = True
                                continue
                            
                            if in_register_function:
                                # Check for end of register function (function at same or lower indent level)
                                if line and not line.startswith('    ') and line.strip() and not line.strip().startswith('#'):
                                    in_register_function = False
                                    continue
                                
                                # Look for @mcp.tool() decorator
                                if "@mcp.tool()" in stripped:
                                    found_mcp_tool_decorator = True
                                    continue
                                
                                # Look for function definition after @mcp.tool() (may have other decorators in between)
                                if found_mcp_tool_decorator and ("async def " in stripped or "def " in stripped) and ":" in stripped:
                                    func_line = stripped
                                    if "async def " in func_line:
                                        func_name = func_line.split("async def ")[1].split("(")[0]
                                    elif "def " in func_line:
                                        func_name = func_line.split("def ")[1].split("(")[0]
                                    else:
                                        continue
                                    
                                    current_function_name = func_name
                                    current_docstring = ""
                                    collecting_docstring = True
                                    found_mcp_tool_decorator = False  # Reset for next tool
                                    
                                    # Look for docstring after function definition (handle multi-line signatures)
                                    # First, find the end of the function signature (look for ") -> " or "):")
                                    signature_complete = False
                                    search_start = i + 1
                                    
                                    for j in range(i+1, min(i+30, len(lines))):
                                        sig_line = lines[j].strip()
                                        if ') -> ' in sig_line or sig_line.endswith('):'):
                                            signature_complete = True
                                            search_start = j + 1
                                            break
                                    
                                    # Now look for docstring after the complete function signature
                                    for j in range(search_start, min(search_start+10, len(lines))):
                                        doc_line = lines[j].strip()
                                        if '"""' in doc_line:
                                            # Start collecting docstring
                                            docstring_content = doc_line.replace('"""', "")
                                            
                                            # Check if it's a single line docstring
                                            if doc_line.count('"""') == 2:
                                                current_docstring = docstring_content
                                                break
                                            else:
                                                # Multi-line docstring, collect until closing """
                                                current_docstring = docstring_content
                                                for k in range(j+1, min(j+30, len(lines))):
                                                    next_doc_line = lines[k].strip()
                                                    if '"""' in next_doc_line:
                                                        current_docstring += " " + next_doc_line.replace('"""', "")
                                                        break
                                                    else:
                                                        current_docstring += " " + next_doc_line
                                                break
                                        elif doc_line and not doc_line.startswith('"""') and doc_line != '':
                                            # Hit some other code, no docstring found
                                            break
                                    
                                    # Process the discovered tool
                                    self._process_discovered_tool(current_function_name, current_docstring, str(python_file), tools)
                                    current_function_name = None
                                    current_docstring = ""
                                    collecting_docstring = False
                                    continue
            
            except Exception as e:
                logger.error(f"Error processing {python_file.name}: {e}")
        
        logger.info(f"✅ Discovered {len(tools)} tools from registered modules")
        return tools
    
    def _process_discovered_tool(self, tool_name: str, docstring: str, file_path: str, tools_dict: Dict):
        """Process a discovered tool and add it to the tools dictionary"""
        metadata = self.extract_docstring_metadata(docstring)
        
        tools_dict[tool_name] = {
            "name": tool_name,
            "file": file_path,
            "docstring": docstring,
            "description": metadata["description"],
            "keywords": metadata["keywords"],
            "usage": metadata["usage"],
            "type": "tool"
        }
        logger.info(f"    🔧 Found tool: {tool_name}")
        if metadata["description"]:
            logger.info(f"      Description: {metadata['description'][:60]}...")
        if metadata["keywords"]:
            logger.info(f"      Keywords: {metadata['keywords'][:5]}")

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
                
            logger.info(f"  📄 Scanning {python_file.name}")
            functions = self.discover_functions_in_file(python_file)
            
            for func_info in functions:
                tool_name = func_info["name"]
                tools[tool_name] = func_info
                logger.info(f"    🔧 Found tool: {tool_name}")
        
        # Approach 2: Use the new method for nested tools in register functions
        logger.info(f"🔍 Using register function discovery for nested tools...")
        nested_tools = self.discover_tools_from_registered_modules()
        
        # Merge both approaches (nested tools take precedence if there are conflicts)
        for tool_name, tool_info in nested_tools.items():
            if tool_name not in tools:
                tools[tool_name] = tool_info
            else:
                # Update with more complete information from nested discovery
                tools[tool_name].update(tool_info)
        
        logger.info(f"✅ Discovered {len(tools)} tools total")
        logger.info(f"    AST discovery: {len(tools) - len(nested_tools)} tools")
        logger.info(f"    Register function discovery: {len(nested_tools)} tools")
        
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
                
            logger.info(f"  📄 Scanning {python_file.name}")
            
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
                
            logger.info(f"  📄 Scanning {python_file.name}")
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
                                logger.info(f"    📊 Found resource: {attr_name}")
            
            except Exception as e:
                logger.error(f"Error processing resources file {python_file}: {e}")
        
        logger.info(f"✅ Discovered {len(resources)} resources")
        self.discovered_resources = resources
        return resources

    async def auto_register_with_mcp(self, mcp: FastMCP, config: Dict[str, Any] = None):
        """Automatically register all discovered items with MCP server"""
        config = config or {}
        
        logger.info("🚀 Auto-registering all discovered items with MCP server")
        
        # Instead of discovering individual tools, register entire tool modules
        # This handles both nested and top-level tool patterns
        
        registered_count = 0
        tool_files_processed = set()
        
        # Get all Python files in tools directory
        for python_file in self.tools_dir.rglob("*.py"):
            if python_file.name.startswith("__"):
                continue
                
            # Skip service files and utility files
            if any(skip in str(python_file) for skip in ["services", "client", "__pycache__"]):
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
        
        # Also discover for metadata purposes
        self.discover_tools()
        self.discover_prompts() 
        self.discover_resources()
        
        logger.info(f"🎉 Auto-registration complete: {registered_count} tool modules registered")
        logger.info(f"📁 Tool files processed: {list(tool_files_processed)}")
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
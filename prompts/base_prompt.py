#!/usr/bin/env python
"""
Base Prompt Class for ISA MCP Prompts
Unified handling for prompt registration, formatting, and organization.
Mirrors BaseResource patterns for consistency.
"""

import sys
from typing import Dict, Any, Optional, List, Callable
from core.logging import get_logger

logger = get_logger(__name__)


class BasePrompt:
    """Base prompt class providing unified registration and formatting"""

    def __init__(self):
        self.registered_prompts: List[Dict[str, Any]] = []
        self.default_category: Optional[str] = "default"

    def register_prompt(
        self,
        mcp,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Register a prompt to MCP server with metadata tracking.

        Args:
            mcp: MCP server instance
            func: Prompt function
            name: Custom prompt name (defaults to function name)
            description: Prompt description (defaults to docstring)
            category: Category for organization
            tags: Tags for searchability
            **kwargs: Additional kwargs passed to @mcp.prompt()
        """
        prompt_name = name or func.__name__
        prompt_description = description or func.__doc__ or ""
        prompt_category = category or getattr(func, '_prompt_category', self.default_category)
        prompt_tags = tags or getattr(func, '_prompt_tags', [])

        # Register with MCP
        if name:
            kwargs['name'] = name
        decorated_func = mcp.prompt(**kwargs)(func)

        # Track registration
        self.registered_prompts.append({
            'name': prompt_name,
            'function': func.__name__,
            'description': prompt_description,
            'category': prompt_category,
            'tags': prompt_tags
        })

        logger.info(f"Registered prompt: {prompt_name}")
        return decorated_func

    def register_all_prompts(self, mcp):
        """
        Template method for registering all prompts.
        Subclasses should override this to register their prompts.
        """
        pass

    def format_prompt_output(
        self,
        content: Optional[str] = None,
        sections: Optional[Dict[str, str]] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format prompt output with optional sections and variable substitution.

        Args:
            content: Base content string
            sections: Dict of section_name -> section_content
            variables: Variables to substitute in content

        Returns:
            Formatted prompt string
        """
        result = content or ""

        # Apply variable substitution
        if variables and result:
            result = result.format(**variables)

        # Format sections
        if sections:
            section_parts = []
            for section_name, section_content in sections.items():
                section_parts.append(f"## {section_name}\n{section_content}")
            result = "\n\n".join(section_parts)

        return result

    def create_system_prompt(
        self,
        role: str,
        capabilities: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None
    ) -> str:
        """
        Create a structured system prompt.

        Args:
            role: Role description
            capabilities: List of capabilities
            constraints: List of constraints/guidelines

        Returns:
            Formatted system prompt
        """
        parts = [role]

        if capabilities:
            parts.append("\n\nCapabilities:")
            for cap in capabilities:
                parts.append(f"- {cap}")

        if constraints:
            parts.append("\n\nGuidelines:")
            for con in constraints:
                parts.append(f"- {con}")

        return "\n".join(parts)

    def get_registered_prompts(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get registered prompts with optional filtering.

        Args:
            category: Filter by category
            tags: Filter by tags (any match)

        Returns:
            List of matching prompt metadata
        """
        result = self.registered_prompts

        if category:
            result = [p for p in result if p.get('category') == category]

        if tags:
            result = [p for p in result if any(t in p.get('tags', []) for t in tags)]

        return result


def simple_prompt(
    category: str = "default",
    tags: Optional[List[str]] = None
):
    """
    Decorator for quick prompt definition with metadata.

    Usage:
        @simple_prompt(category="reasoning", tags=["analysis"])
        def my_prompt(message: str = "") -> str:
            return f"Analyze: {message}"
    """
    def decorator(func: Callable) -> Callable:
        func._prompt_category = category
        func._prompt_tags = tags or []
        return func
    return decorator


def create_simple_prompt_registration(register_func_name: str = "register_prompts"):
    """
    Create a simple prompt registration function decorator.

    Args:
        register_func_name: Name for the generated registration function

    Returns:
        Class decorator
    """
    def decorator(prompt_class):
        def register_function(mcp):
            try:
                instance = prompt_class()
                instance.register_all_prompts(mcp)
                logger.debug(f"{prompt_class.__name__} prompts registered successfully")
            except Exception as e:
                logger.error(f"Failed to register {prompt_class.__name__}: {e}")
                raise

        # Add to caller's globals
        caller_frame = sys._getframe(1)
        caller_globals = caller_frame.f_globals
        caller_globals[register_func_name] = register_function

        return prompt_class

    return decorator

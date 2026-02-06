"""
Random data generators for test fixtures.

Provides functions to generate random test data without Factory Boy.
"""
import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def generate_random_string(length: int = 10, prefix: str = "") -> str:
    """Generate a random string."""
    chars = string.ascii_lowercase + string.digits
    return prefix + ''.join(random.choices(chars, k=length))


def generate_random_id(prefix: str = "") -> str:
    """Generate a random UUID-based ID."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def generate_random_email(domain: str = "example.com") -> str:
    """Generate a random email address."""
    name = generate_random_string(8)
    return f"{name}@{domain}"


def generate_random_timestamp(days_back: int = 30) -> datetime:
    """Generate a random timestamp within the past N days."""
    offset = random.randint(0, days_back * 24 * 3600)
    return datetime.utcnow() - timedelta(seconds=offset)


# ═══════════════════════════════════════════════════════════════
# Domain-Specific Generators
# ═══════════════════════════════════════════════════════════════

def generate_random_tool(
    name: str = None,
    category: str = None,
    **overrides
) -> Dict[str, Any]:
    """Generate a random tool definition."""
    categories = ["intelligence", "utility", "web", "data", "user"]
    descriptions = [
        "Processes input data and returns results",
        "Analyzes content for insights",
        "Generates output based on parameters",
        "Transforms data between formats",
        "Executes operations on resources",
    ]

    tool = {
        "name": name or generate_random_string(8, "tool_"),
        "description": random.choice(descriptions),
        "category": category or random.choice(categories),
        "input_schema": {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "The input to process"
                }
            },
            "required": ["input"]
        },
        "is_active": True,
        "created_at": generate_random_timestamp(),
        "updated_at": datetime.utcnow(),
    }

    tool.update(overrides)
    return tool


def generate_random_prompt(
    name: str = None,
    **overrides
) -> Dict[str, Any]:
    """Generate a random prompt definition."""
    templates = [
        "You are a helpful assistant. Task: {{task}}",
        "Please {{action}} the following: {{content}}",
        "As an expert in {{domain}}, help with: {{request}}",
        "Analyze the following {{type}}: {{input}}",
    ]

    prompt = {
        "name": name or generate_random_string(8, "prompt_"),
        "description": f"A prompt for {random.choice(['writing', 'analysis', 'coding', 'research'])}",
        "template": random.choice(templates),
        "arguments": [
            {
                "name": "input",
                "description": "The main input",
                "required": True
            }
        ],
        "created_at": generate_random_timestamp(),
        "updated_at": datetime.utcnow(),
    }

    prompt.update(overrides)
    return prompt


def generate_random_resource(
    uri: str = None,
    **overrides
) -> Dict[str, Any]:
    """Generate a random resource definition."""
    resource_types = ["data", "config", "template", "schema"]
    mime_types = ["application/json", "text/plain", "application/yaml", "text/markdown"]

    resource = {
        "uri": uri or f"resource://{random.choice(resource_types)}/{generate_random_id()}",
        "name": generate_random_string(8, "resource_"),
        "description": f"A {random.choice(resource_types)} resource",
        "mime_type": random.choice(mime_types),
        "created_at": generate_random_timestamp(),
    }

    resource.update(overrides)
    return resource


def generate_random_user(
    tier: str = None,
    **overrides
) -> Dict[str, Any]:
    """Generate a random user."""
    tiers = ["free", "pro", "enterprise"]

    user = {
        "user_id": generate_random_id("usr_"),
        "email": generate_random_email(),
        "api_key": generate_random_id("mcp_"),
        "subscription_tier": tier or random.choice(tiers),
        "is_active": True,
        "created_at": generate_random_timestamp(),
    }

    user.update(overrides)
    return user


def generate_random_embedding(
    dimension: int = 1536,
    **overrides
) -> Dict[str, Any]:
    """Generate a random embedding."""
    embedding = {
        "id": generate_random_id(),
        "vector": [random.uniform(-1, 1) for _ in range(dimension)],
        "text": f"Sample text {generate_random_string(20)}",
        "model": "text-embedding-3-small",
        "created_at": datetime.utcnow(),
    }

    embedding.update(overrides)
    return embedding


def generate_random_search_results(
    count: int = 10,
    category: str = None,
    min_score: float = 0.3,
    max_score: float = 1.0
) -> List[Dict[str, Any]]:
    """Generate random search results with descending scores."""
    categories = ["tool", "prompt", "resource"]
    results = []

    for i in range(count):
        # Generate descending scores
        score = max_score - (i * (max_score - min_score) / count)

        result = {
            "id": generate_random_id(),
            "name": generate_random_string(10),
            "description": f"Search result {i + 1}",
            "score": round(score, 4),
            "category": category or random.choice(categories),
        }
        results.append(result)

    return results


# ═══════════════════════════════════════════════════════════════
# Batch Generators
# ═══════════════════════════════════════════════════════════════

def generate_tool_batch(count: int = 5, **common_attrs) -> List[Dict[str, Any]]:
    """Generate multiple tools."""
    return [generate_random_tool(**common_attrs) for _ in range(count)]


def generate_prompt_batch(count: int = 5, **common_attrs) -> List[Dict[str, Any]]:
    """Generate multiple prompts."""
    return [generate_random_prompt(**common_attrs) for _ in range(count)]


def generate_resource_batch(count: int = 5, **common_attrs) -> List[Dict[str, Any]]:
    """Generate multiple resources."""
    return [generate_random_resource(**common_attrs) for _ in range(count)]


def generate_user_batch(count: int = 5, **common_attrs) -> List[Dict[str, Any]]:
    """Generate multiple users."""
    return [generate_random_user(**common_attrs) for _ in range(count)]


# ═══════════════════════════════════════════════════════════════
# Schema Generators
# ═══════════════════════════════════════════════════════════════

def generate_json_schema(
    properties: Dict[str, str] = None,
    required: List[str] = None
) -> Dict[str, Any]:
    """Generate a JSON schema."""
    if properties is None:
        properties = {
            "input": "string",
            "count": "integer",
            "enabled": "boolean"
        }

    schema_properties = {}
    for name, type_name in properties.items():
        schema_properties[name] = {
            "type": type_name,
            "description": f"The {name} parameter"
        }

    return {
        "type": "object",
        "properties": schema_properties,
        "required": required or list(properties.keys())[:1]
    }


def generate_tool_input_schema(
    args: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate a tool input schema from argument definitions."""
    if args is None:
        args = [
            {"name": "input", "type": "string", "required": True},
            {"name": "options", "type": "object", "required": False}
        ]

    properties = {}
    required = []

    for arg in args:
        properties[arg["name"]] = {
            "type": arg.get("type", "string"),
            "description": arg.get("description", f"The {arg['name']} parameter")
        }
        if arg.get("default") is not None:
            properties[arg["name"]]["default"] = arg["default"]
        if arg.get("required", False):
            required.append(arg["name"])

    return {
        "type": "object",
        "properties": properties,
        "required": required
    }

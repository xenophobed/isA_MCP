"""
Factory Boy factories for generating test data.

Provides factories for all major domain objects in isA_MCP.
"""
try:
    import factory
    from factory import fuzzy
    FACTORY_AVAILABLE = True
except ImportError:
    FACTORY_AVAILABLE = False
    # Create mock factory class for when factory_boy isn't installed
    class MockFactory:
        class Meta:
            model = dict
    factory = None

from datetime import datetime, timedelta
import uuid
import random
import string


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def generate_name(prefix: str = "item") -> str:
    """Generate a random name."""
    suffix = ''.join(random.choices(string.ascii_lowercase, k=6))
    return f"{prefix}_{suffix}"


def random_choice(choices: list):
    """Return a random choice from list."""
    return random.choice(choices)


# ═══════════════════════════════════════════════════════════════
# Tool Factories
# ═══════════════════════════════════════════════════════════════

if FACTORY_AVAILABLE:
    class ToolFactory(factory.Factory):
        """Factory for creating tool test data."""

        class Meta:
            model = dict

        name = factory.LazyFunction(lambda: generate_name("tool"))
        description = factory.LazyFunction(
            lambda: f"A tool that {random_choice(['processes', 'analyzes', 'generates', 'transforms'])} data"
        )
        category = factory.LazyFunction(
            lambda: random_choice(["intelligence", "utility", "web", "data", "user"])
        )
        input_schema = factory.LazyAttribute(lambda _: {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "The input to process"
                }
            },
            "required": ["input"]
        })
        is_active = True
        created_at = factory.LazyFunction(datetime.utcnow)
        updated_at = factory.LazyFunction(datetime.utcnow)

        class Params:
            """Factory parameters for customization."""
            with_optional_args = factory.Trait(
                input_schema={
                    "type": "object",
                    "properties": {
                        "input": {"type": "string", "description": "Required input"},
                        "max_length": {"type": "integer", "default": 100},
                        "format": {"type": "string", "enum": ["text", "json", "xml"]}
                    },
                    "required": ["input"]
                }
            )

            intelligence = factory.Trait(
                category="intelligence",
                description="An AI-powered tool for intelligent processing"
            )

            web = factory.Trait(
                category="web",
                description="A web automation tool"
            )


    class PromptFactory(factory.Factory):
        """Factory for creating prompt test data."""

        class Meta:
            model = dict

        name = factory.LazyFunction(lambda: generate_name("prompt"))
        description = factory.LazyFunction(
            lambda: f"A prompt for {random_choice(['writing', 'analyzing', 'coding', 'summarizing'])}"
        )
        template = factory.LazyAttribute(
            lambda obj: f"You are an assistant. {{{{task}}}}"
        )
        arguments = factory.LazyAttribute(lambda _: [
            {
                "name": "task",
                "description": "The task to perform",
                "required": True
            }
        ])
        created_at = factory.LazyFunction(datetime.utcnow)
        updated_at = factory.LazyFunction(datetime.utcnow)

        class Params:
            """Factory parameters."""
            with_context = factory.Trait(
                arguments=[
                    {"name": "task", "description": "The task", "required": True},
                    {"name": "context", "description": "Additional context", "required": False}
                ],
                template="You are an assistant. Context: {{context}}\n\nTask: {{task}}"
            )


    class ResourceFactory(factory.Factory):
        """Factory for creating resource test data."""

        class Meta:
            model = dict

        uri = factory.LazyFunction(
            lambda: f"resource://{random_choice(['data', 'config', 'template'])}/{generate_id()}"
        )
        name = factory.LazyFunction(lambda: generate_name("resource"))
        description = factory.LazyFunction(
            lambda: f"A resource containing {random_choice(['data', 'configuration', 'templates'])}"
        )
        mime_type = factory.LazyFunction(
            lambda: random_choice(["application/json", "text/plain", "application/yaml"])
        )
        created_at = factory.LazyFunction(datetime.utcnow)


    class UserFactory(factory.Factory):
        """Factory for creating user test data."""

        class Meta:
            model = dict

        user_id = factory.LazyFunction(lambda: generate_id("usr_"))
        email = factory.LazyFunction(
            lambda: f"{generate_name('user')}@example.com"
        )
        api_key = factory.LazyFunction(lambda: generate_id("mcp_"))
        subscription_tier = factory.LazyFunction(
            lambda: random_choice(["free", "pro", "enterprise"])
        )
        is_active = True
        created_at = factory.LazyFunction(datetime.utcnow)

        class Params:
            """Factory parameters."""
            admin = factory.Trait(
                subscription_tier="enterprise",
                is_admin=True
            )


    class SearchResultFactory(factory.Factory):
        """Factory for creating search result test data."""

        class Meta:
            model = dict

        id = factory.LazyFunction(lambda: generate_id())
        name = factory.LazyFunction(lambda: generate_name("item"))
        description = factory.LazyFunction(lambda: "A matching result")
        score = factory.LazyFunction(lambda: round(random.uniform(0.5, 1.0), 4))
        category = factory.LazyFunction(
            lambda: random_choice(["tool", "prompt", "resource"])
        )

        class Params:
            """Factory parameters."""
            high_relevance = factory.Trait(
                score=factory.LazyFunction(lambda: round(random.uniform(0.85, 1.0), 4))
            )

            low_relevance = factory.Trait(
                score=factory.LazyFunction(lambda: round(random.uniform(0.3, 0.5), 4))
            )


    class EmbeddingFactory(factory.Factory):
        """Factory for creating embedding test data."""

        class Meta:
            model = dict

        id = factory.LazyFunction(lambda: generate_id())
        vector = factory.LazyFunction(lambda: [random.uniform(-1, 1) for _ in range(1536)])
        text = factory.LazyFunction(lambda: f"Sample text for embedding {generate_id()}")
        model = "text-embedding-3-small"
        created_at = factory.LazyFunction(datetime.utcnow)

        class Params:
            """Factory parameters."""
            small_dimension = factory.Trait(
                vector=factory.LazyFunction(lambda: [random.uniform(-1, 1) for _ in range(384)])
            )

else:
    # Fallback implementations when factory_boy is not installed
    class ToolFactory:
        @staticmethod
        def build(**kwargs):
            default = {
                "name": generate_name("tool"),
                "description": "A test tool",
                "category": "utility",
                "input_schema": {"type": "object", "properties": {}, "required": []},
                "is_active": True,
                "created_at": datetime.utcnow(),
            }
            default.update(kwargs)
            return default

        @staticmethod
        def build_batch(size: int, **kwargs):
            return [ToolFactory.build(**kwargs) for _ in range(size)]

    class PromptFactory:
        @staticmethod
        def build(**kwargs):
            default = {
                "name": generate_name("prompt"),
                "description": "A test prompt",
                "template": "Template: {{input}}",
                "arguments": [{"name": "input", "required": True}],
                "created_at": datetime.utcnow(),
            }
            default.update(kwargs)
            return default

        @staticmethod
        def build_batch(size: int, **kwargs):
            return [PromptFactory.build(**kwargs) for _ in range(size)]

    class ResourceFactory:
        @staticmethod
        def build(**kwargs):
            default = {
                "uri": f"resource://test/{generate_id()}",
                "name": generate_name("resource"),
                "description": "A test resource",
                "mime_type": "application/json",
                "created_at": datetime.utcnow(),
            }
            default.update(kwargs)
            return default

        @staticmethod
        def build_batch(size: int, **kwargs):
            return [ResourceFactory.build(**kwargs) for _ in range(size)]

    class UserFactory:
        @staticmethod
        def build(**kwargs):
            default = {
                "user_id": generate_id("usr_"),
                "email": f"{generate_name('user')}@example.com",
                "api_key": generate_id("mcp_"),
                "subscription_tier": "free",
                "is_active": True,
                "created_at": datetime.utcnow(),
            }
            default.update(kwargs)
            return default

        @staticmethod
        def build_batch(size: int, **kwargs):
            return [UserFactory.build(**kwargs) for _ in range(size)]

    class SearchResultFactory:
        @staticmethod
        def build(**kwargs):
            default = {
                "id": generate_id(),
                "name": generate_name("item"),
                "description": "A search result",
                "score": round(random.uniform(0.5, 1.0), 4),
                "category": "tool",
            }
            default.update(kwargs)
            return default

        @staticmethod
        def build_batch(size: int, **kwargs):
            return [SearchResultFactory.build(**kwargs) for _ in range(size)]

    class EmbeddingFactory:
        @staticmethod
        def build(**kwargs):
            default = {
                "id": generate_id(),
                "vector": [random.uniform(-1, 1) for _ in range(1536)],
                "text": f"Sample text {generate_id()}",
                "model": "text-embedding-3-small",
                "created_at": datetime.utcnow(),
            }
            default.update(kwargs)
            return default

        @staticmethod
        def build_batch(size: int, **kwargs):
            return [EmbeddingFactory.build(**kwargs) for _ in range(size)]


# ═══════════════════════════════════════════════════════════════
# Batch Creation Helpers
# ═══════════════════════════════════════════════════════════════

def create_tool_batch(count: int = 5, **common_attrs) -> list:
    """Create multiple tools."""
    if FACTORY_AVAILABLE:
        return ToolFactory.build_batch(count, **common_attrs)
    return [ToolFactory.build(**common_attrs) for _ in range(count)]


def create_prompt_batch(count: int = 5, **common_attrs) -> list:
    """Create multiple prompts."""
    if FACTORY_AVAILABLE:
        return PromptFactory.build_batch(count, **common_attrs)
    return [PromptFactory.build(**common_attrs) for _ in range(count)]


def create_search_results(count: int = 10, category: str = None) -> list:
    """Create search results with decreasing scores."""
    results = []
    for i in range(count):
        score = round(1.0 - (i * 0.05), 4)
        result = SearchResultFactory.build(score=score) if FACTORY_AVAILABLE else SearchResultFactory.build(score=score)
        if category:
            result["category"] = category
        results.append(result)
    return results

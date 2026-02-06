# Prompts

Create and register custom prompts with the ISA MCP platform.

## Overview

The platform includes 50+ built-in prompts for reasoning, RAG, and specialized workflows.

## Prompt Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `default` | Reasoning prompts | `default_reason_prompt`, `rag_reason_prompt` |
| `autonomous` | Autonomous agent prompts | Planning, execution |
| `rag` | RAG-specific prompts | Document analysis |
| `system` | System-level prompts | Error handling, feedback |
| `apps` | Application-specific | Shopify, custom apps |

## Creating Custom Prompts

### Simple Function Pattern

```python
# prompts/my_prompts.py
from mcp.server.fastmcp import FastMCP

def register_my_prompts(mcp: FastMCP):
    """Register custom prompts."""

    @mcp.prompt()
    def analysis_prompt(
        topic: str = "",
        context: str = "",
        depth: str = "standard"
    ) -> str:
        """
        Structured analysis prompt for deep thinking.

        Guides the model through systematic analysis of any topic.

        Keywords: analysis, thinking, reasoning, deep-dive
        Category: reasoning
        """
        depth_instructions = {
            "quick": "Provide a brief 2-3 sentence analysis.",
            "standard": "Provide a thorough paragraph analysis.",
            "deep": "Provide comprehensive multi-paragraph analysis with examples."
        }

        return f"""Analyze the following topic systematically.

## Topic
{topic}

## Context
{context if context else "No additional context provided."}

## Instructions
{depth_instructions.get(depth, depth_instructions["standard"])}

## Analysis Framework
1. **Key Concepts** - Identify main ideas
2. **Relationships** - How concepts connect
3. **Implications** - What this means
4. **Conclusions** - Summary and insights
"""

    print("Custom prompts registered")
```

### Using BasePrompt Class

For advanced prompts with metadata tracking:

```python
from prompts.base_prompt import BasePrompt, simple_prompt

class ReasoningPrompts(BasePrompt):
    def __init__(self):
        super().__init__()
        self.default_category = "reasoning"

    def register_all_prompts(self, mcp):
        self.register_prompt(
            mcp,
            self.chain_of_thought,
            name="chain_of_thought",
            description="Step-by-step reasoning prompt",
            category="reasoning",
            tags=["thinking", "analysis", "step-by-step"]
        )

    def chain_of_thought(
        self,
        problem: str = "",
        constraints: str = ""
    ) -> str:
        return self.format_prompt_output(
            sections={
                "Problem": problem,
                "Constraints": constraints if constraints else "None specified",
                "Instructions": """Think through this step by step:
1. Understand the problem
2. Identify key factors
3. Consider approaches
4. Evaluate trade-offs
5. Provide solution"""
            }
        )

def register_reasoning_prompts(mcp):
    prompts = ReasoningPrompts()
    prompts.register_all_prompts(mcp)
```

## File Naming Convention

1. **Filename**: Any `.py` file in `prompts/`
2. **Register function**: `register_{name}_prompts(mcp)`

## BasePrompt Features

### format_prompt_output

```python
# Format with sections
output = self.format_prompt_output(
    sections={
        "Context": "...",
        "Instructions": "...",
        "Output Format": "..."
    }
)

# Format with variables
output = self.format_prompt_output(
    content="Analyze {topic} for {user}",
    variables={"topic": "AI", "user": "John"}
)
```

### create_system_prompt

```python
system = self.create_system_prompt(
    role="You are an expert analyst.",
    capabilities=[
        "Deep analytical thinking",
        "Pattern recognition",
        "Clear explanation"
    ],
    constraints=[
        "Be concise",
        "Cite sources when possible",
        "Acknowledge uncertainty"
    ]
)
```

## Decorator Pattern

Quick prompt definition with metadata:

```python
from prompts.base_prompt import simple_prompt

@simple_prompt(category="reasoning", tags=["analysis"])
def quick_analysis(message: str = "") -> str:
    """Quick analysis prompt."""
    return f"Briefly analyze: {message}"
```

## Prompt Parameters

| Type | Example | Description |
|------|---------|-------------|
| `str` | `topic: str = ""` | Text input |
| `int` | `depth: int = 1` | Numeric input |
| `bool` | `verbose: bool = False` | Boolean flag |
| `List[str]` | `tags: List[str] = []` | Multiple values |

## Best Practices

1. **Default values** - Always provide defaults for optional params
2. **Docstrings** - Include keywords for semantic search
3. **Categories** - Organize prompts by use case
4. **Tags** - Add searchable tags
5. **Clear structure** - Use markdown sections in output
6. **Flexible depth** - Support different detail levels

## Built-in Prompts

### default_reason_prompt
Primary reasoning prompt for intelligent assistant interactions.

```python
result = await client.get_prompt("default_reason_prompt", {
    "user_message": "Explain quantum computing",
    "memory": "User prefers simple explanations",
    "tools": "search_web, calculate",
    "skills": "research_skill loaded"
})
```

### rag_reason_prompt
RAG-optimized prompt for document-based reasoning.

```python
result = await client.get_prompt("rag_reason_prompt", {
    "user_message": "Summarize these documents",
    "file_context": "...",
    "file_count": 3
})
```

## Next Steps

- [Tools](./tools) - Create custom tools
- [Resources](./resources) - Create custom resources
- [Skills](./skills) - Skill-based workflows

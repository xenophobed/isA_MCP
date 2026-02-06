# Skills

ISA MCP has two distinct skill systems with different purposes.

## Overview

| Skill Type | Purpose | Storage | Access Method |
|------------|---------|---------|---------------|
| Tool Classification | Categorize tools for search | PostgreSQL + Qdrant | SkillService API |
| Agent Skills | Workflow definitions for agents | File system | MCP Resources (`skill://`) |

---

## Part 1: Tool Classification Skills

Tool classification skills categorize tools for hierarchical search and discovery.

### Purpose

- Organize tools into semantic categories
- Enable two-stage hierarchical search
- LLM-based automatic classification with confidence scores

### Creating Classification Skills

```python
from services.skill_service import SkillService

skill_service = SkillService()

# Create a new tool classification category
await skill_service.create_skill_category({
    "id": "data_visualization",        # Lowercase, alphanumeric + underscore
    "name": "Data Visualization",
    "description": "Tools for creating charts, graphs, and visual representations of data",
    "keywords": ["chart", "graph", "plot", "visualization", "dashboard"],
    "parent_domain": "data"            # Optional parent category
})
```

### Classification Schema

```python
{
    "id": str,              # Unique ID (lowercase, alphanumeric + underscore)
    "name": str,            # Display name
    "description": str,     # What this category covers (min 10 chars)
    "keywords": List[str],  # Search keywords (auto-lowercased)
    "parent_domain": str,   # Optional parent for hierarchy
    "is_active": bool,      # Whether category is active
    "metadata": dict        # Additional metadata
}
```

### Automatic Tool Classification

When tools are registered, the SkillService:

1. Analyzes tool name and description with LLM
2. Assigns up to 3 skill categories with confidence scores
3. Stores assignments for search routing

```python
# Classify a tool
result = await skill_service.classify_tool({
    "name": "create_bar_chart",
    "description": "Create a bar chart from data"
})

# Returns:
# {
#   "tool": "create_bar_chart",
#   "assignments": [
#     {"skill": "data_visualization", "confidence": 0.95},
#     {"skill": "data_analysis", "confidence": 0.72}
#   ]
# }
```

### Classification API

| Operation | Method |
|-----------|--------|
| Create category | `skill_service.create_skill_category(data)` |
| List categories | `skill_service.list_skills()` |
| Get category | `skill_service.get_skill(skill_id)` |
| Update category | `skill_service.update_skill_category(id, updates)` |
| Classify tool | `skill_service.classify_tool(tool_data)` |

### Hierarchical Search

Classification skills enable two-stage search:

```
Query: "create a pie chart"
        │
        ▼
┌─────────────────────────────────┐
│  Stage 1: Match Category        │
│  Result: data_visualization     │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│  Stage 2: Search within Category│
│  Result: create_pie_chart       │
└─────────────────────────────────┘
```

---

## Part 2: Agent Skills (MCP Resources)

Agent skills are workflow definitions that AI agents load and follow. They are **MCP resources** accessed via URIs.

### Skill Types

| Type | Location | URI Pattern |
|------|----------|-------------|
| Vibe Skills | `resources/skills/vibe/` | `skill://vibe/{name}` |
| External Skills | `resources/skills/external/` | `skill://external/{name}` |
| Legacy | - | `vibe://skill/{name}` (backward compat) |

### Current Vibe Skills

| Skill | Description |
|-------|-------------|
| `cdd` | Contract-Driven Development |
| `tdd` | Test-Driven Development |
| `agile` | Agile development workflow |
| `deployment` | Deployment workflow |
| `operations` | Operations workflow |
| `init` | Project initialization |

### Resource URIs

```python
# List all agent skills
skill://list

# List vibe skills only
skill://vibe/list

# Get specific vibe skill
skill://vibe/tdd

# Get skill guides (Level 3)
skill://vibe/tdd/guides
skill://vibe/tdd/guides/python.md

# Get skill templates (Level 3)
skill://vibe/tdd/templates
skill://vibe/tdd/templates/python/unit/

# Search skills
skill://search/{query}

# External skills
skill://external/list
skill://external/{name}
```

### Skill Structure

```
resources/skills/vibe/tdd/
├── SKILL.md              # Main skill definition (Level 2)
├── guides/               # Level 3 resources
│   ├── python.md
│   ├── react.md
│   └── data_product.md
├── templates/            # Level 3 resources
│   ├── python/
│   ├── react/
│   └── data_product/
└── scripts/              # Level 3 resources
```

### Creating Agent Skills

#### 1. Create Skill Directory

```bash
mkdir -p resources/skills/vibe/my_skill/{guides,templates,scripts}
```

#### 2. Create SKILL.md

```markdown
---
name: my_skill
description: Description of what this skill does
version: 1.0.0
author: Your Name
---

# My Skill

## Overview

What this skill helps agents accomplish.

## Workflow

### Step 1: First Step
Instructions for step 1.

### Step 2: Second Step
Instructions for step 2.

## Available Resources

### Guides (Level 3)
- `guides/getting_started.md` - Getting started guide
- `guides/advanced.md` - Advanced usage

### Templates (Level 3)
- `templates/basic/` - Basic templates

## Quick Reference

How to use this skill.
```

#### 3. Add Level 3 Resources

```markdown
<!-- guides/getting_started.md -->
# Getting Started

Detailed guide content...
```

### Progressive Disclosure (Level 1-3)

| Level | Content | When Loaded |
|-------|---------|-------------|
| Level 1 | Metadata (name, description) | Always (via list) |
| Level 2 | SKILL.md content | When skill is requested |
| Level 3 | Guides, templates, scripts | On demand |

### Using Agent Skills

```python
# Read skill content
content = await client.read_resource("skill://vibe/tdd")

# Read specific guide
guide = await client.read_resource("skill://vibe/tdd/guides/python.md")

# Search for skills
results = await client.read_resource("skill://search/testing")
```

### Installing External Skills

External skills can be installed from npm, GitHub, or other registries:

```python
# Via skill installer service
await skill_installer.install_from_npm("@example/my-skill")
await skill_installer.install_from_github("user/repo")
```

---

## Best Practices

### Tool Classification
1. Use descriptive category names
2. Add relevant keywords for matching
3. Use parent domains for hierarchy
4. Review automatic classifications

### Agent Skills
1. Clear SKILL.md with workflow steps
2. Use Level 3 resources for details
3. Include templates for common patterns
4. Add YAML frontmatter for metadata

## Next Steps

- [Tools](./tools) - Create custom tools
- [Resources](./resources) - MCP resources
- [Search & Discovery](./search) - Skill-based search

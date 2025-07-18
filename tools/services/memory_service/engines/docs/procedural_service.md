# Procedural Memory Service

## Overview

The Procedural Memory Service provides intelligent storage and retrieval of procedural knowledge by automatically extracting step-by-step instructions, workflows, and how-to procedures from raw human-AI dialog content. This service transforms conversational explanations into structured, searchable procedural memories using advanced text analysis.

## Features

- **Intelligent Procedure Extraction**: Automatically extracts step-by-step procedures from dialog
- **Multi-step Processing**: Handles complex procedures with detailed step breakdowns
- **Skill Classification**: Categorizes procedures by skill type and domain
- **Difficulty Assessment**: Automatically determines procedure complexity level
- **Comprehensive Search**: Multiple search dimensions for procedure retrieval
- **Success Tracking**: Monitors procedure effectiveness through usage metrics

## Core Method: `store_procedural_memory()`

### Input

```python
async def store_procedural_memory(
    user_id: str,
    dialog_content: str,
    importance_score: float = 0.5
) -> MemoryOperationResult
```

**Parameters:**
- `user_id` (str): User identifier for memory ownership
- `dialog_content` (str): Raw dialog between human and AI containing procedural information
- `importance_score` (float): Manual importance override (0.0-1.0, defaults to 0.5)

### Output

Returns `MemoryOperationResult` with:
- `success` (bool): Whether the operation succeeded
- `memory_id` (str): Unique identifier for the stored procedure
- `operation` (str): Operation type ("store_procedural_memory")
- `message` (str): Status message with extraction details

### Extracted Information

The service automatically extracts:

1. **Skill Type**: Category of procedure (e.g., 'programming', 'deployment', 'analysis')
2. **Steps**: Structured list of procedural steps with:
   - `step_number`: Sequential order
   - `description`: What to do in this step
   - `importance`: Critical/important/optional
   - `estimated_time`: How long the step takes
   - `tools_needed`: Required tools or resources
3. **Prerequisites**: Required skills or knowledge before attempting
4. **Difficulty Level**: Beginner, intermediate, advanced, or expert
5. **Domain**: Knowledge category (technology, business, creative, etc.)
6. **Tools Required**: Complete list of needed tools/software
7. **Success Indicators**: How to verify successful completion
8. **Common Mistakes**: Pitfalls to avoid

## Usage Examples

### Web Deployment Procedure

```python
from tools.services.memory_service.engines.procedural_engine import ProceduralMemoryEngine

engine = ProceduralMemoryEngine()

# Docker deployment tutorial
deployment_dialog = """
Human: Can you help me understand how to deploy a web application using Docker?

AI: I'll walk you through the process step by step:

First, you need to create a Dockerfile in your project root. This file defines how to build your application container. Start with a base image like node:16 for Node.js apps.

Next, copy your application files into the container and install dependencies using npm install or similar commands.

Then build the Docker image using 'docker build -t myapp .' command in your terminal.

After that, run the container with 'docker run -p 3000:3000 myapp' to expose port 3000.

Finally, test your application by visiting localhost:3000 in your browser.

This process requires Docker installed on your machine and basic knowledge of command line operations.
"""

result = await engine.store_procedural_memory(
    user_id="user123",
    dialog_content=deployment_dialog
)

# Result will extract:
# - skill_type: "web_deployment"
# - 5 detailed steps with tools and timing
# - prerequisites: ["Docker installed", "command line knowledge", "web application source code"]
# - difficulty_level: "intermediate"
# - domain: "technology"
```

### CI/CD Pipeline Setup

```python
# Complex multi-step procedure
cicd_dialog = """
Human: How do I set up a complete CI/CD pipeline for my React application?

AI: Here's a comprehensive guide:

1. First, set up your Git repository with proper branching strategy
2. Configure GitHub Actions workflow file in .github/workflows/
3. Set up testing pipeline with Jest and React Testing Library
4. Configure build process with webpack optimization
5. Set up staging environment deployment
6. Configure production deployment with proper secrets
7. Add monitoring and rollback capabilities

You'll need Docker, AWS CLI, and knowledge of YAML configuration files.
"""

result = await engine.store_procedural_memory(
    user_id="user123",
    dialog_content=cicd_dialog
)

# Result extracts advanced procedure with:
# - skill_type: "cicd_setup"
# - 7 structured steps with detailed breakdown
# - prerequisites: ["Git knowledge", "Docker basics", "AWS CLI", "YAML configuration"]
# - difficulty_level: "advanced"
# - tools_required: ["Docker", "AWS CLI", "Git", "GitHub Actions"]
```

### Troubleshooting Procedure

```python
# Problem-solving workflow
troubleshoot_dialog = """
Human: My application keeps crashing. How should I debug this?

AI: Let me guide you through systematic debugging:

Start by checking the application logs for error messages. Look for stack traces or specific error codes.

Next, verify that all dependencies are properly installed and up to date.

Then check your configuration files for any syntax errors or missing values.

If the issue persists, try running the application in debug mode to get more detailed output.

Finally, consider rolling back to the last known working version while you investigate.

This requires access to logs, version control, and understanding of your application architecture.
"""

result = await engine.store_procedural_memory(
    user_id="user123",
    dialog_content=troubleshoot_dialog
)

# Extracts systematic debugging procedure
```

## Search Methods

The Procedural Memory Service provides comprehensive search capabilities:

### 1. Domain Search

```python
procedures = await engine.search_procedures_by_domain(
    user_id="user123",
    domain="technology",
    limit=10
)
```

**Use Cases:**
- Find all procedures in a specific knowledge area
- Partial matching support (e.g., "tech" matches "technology")
- Results ordered by success rate

### 2. Skill Type Search

```python
procedures = await engine.search_procedures_by_skill_type(
    user_id="user123",
    skill_type="deployment",
    limit=10
)
```

**Available Skill Types:**
- `programming`: Code development procedures
- `deployment`: Application deployment workflows
- `troubleshooting`: Problem-solving procedures
- `analysis`: Data analysis and research methods
- `management`: Project and team management processes

### 3. Difficulty Level Search

```python
procedures = await engine.search_procedures_by_difficulty(
    user_id="user123",
    difficulty_level="intermediate",
    limit=10
)
```

**Difficulty Levels:**
- `beginner`: Simple procedures with minimal prerequisites
- `intermediate`: Moderate complexity requiring some experience
- `advanced`: Complex procedures for experienced users
- `expert`: Highly complex procedures requiring deep expertise

### 4. Success Rate Search

```python
# Find proven, high-success procedures
reliable_procedures = await engine.search_procedures_by_success_rate(
    user_id="user123",
    min_success_rate=0.8,
    limit=10
)
```

**Use Cases:**
- Find procedures with high success rates
- Identify reliable workflows
- Discover well-tested processes
- Results ordered by success rate and usage count

### 5. Prerequisites Search

```python
procedures = await engine.search_procedures_by_prerequisites(
    user_id="user123",
    prerequisite="Docker",
    limit=10
)
```

**Use Cases:**
- Find procedures requiring specific skills or tools
- Plan learning pathways based on current knowledge
- Identify procedures you're ready to attempt

### 6. Vector Similarity Search (Inherited)

```python
from tools.services.memory_service.models import MemorySearchQuery

# Semantic similarity search
query = MemorySearchQuery(
    query="web application deployment automation",
    user_id="user123",
    top_k=5,
    similarity_threshold=0.7
)

procedures = await engine.search_memories(query)
```

## Advanced Features

### Success Rate Tracking

The service tracks procedure effectiveness through usage:

```python
# Update success rate after attempting a procedure
await engine.update_success_rate(
    memory_id="procedure_id",
    success=True  # True for successful execution, False for failure
)
```

**Success Rate Calculation:**
- Weighted average of all attempts
- Higher success rates indicate more reliable procedures
- Used for ranking search results

### Step-by-Step Structure

Each procedure includes detailed steps:

```json
{
  "step_number": 1,
  "description": "Create a Dockerfile in your project root",
  "importance": "critical",
  "estimated_time": "5 minutes",
  "tools_needed": ["text editor", "project files"]
}
```

### Prerequisites Management

Procedures track required knowledge and tools:

```python
# Example prerequisites
prerequisites = [
    "Docker installed",
    "Command line knowledge", 
    "Web application source code",
    "Basic networking understanding"
]
```

### Context and Metadata

Additional extracted information:

- **Tools Required**: Complete toolkit needed
- **Success Indicators**: How to verify completion
- **Common Mistakes**: Known pitfalls and how to avoid them

## Search Method Characteristics

### Performance
- **Domain, Skill Type**: Database queries with indexing and partial matching
- **Difficulty, Prerequisites**: Direct categorical filtering with participant matching
- **Success Rate**: Numeric filtering ordered by reliability metrics
- **Vector Similarity**: Embedding-based semantic search

### Result Ordering
- **Domain**: By success rate (highest first)
- **Skill Type**: By success rate, then importance
- **Difficulty**: By success rate, then importance score
- **Success Rate**: By success rate, then usage count
- **Prerequisites**: By difficulty level (easier first)

### Error Handling
All search methods return empty lists on errors and log warnings for debugging.

## Integration with Base Memory Engine

The procedural engine extends the base memory engine, inheriting:

- **Vector Embeddings**: Automatic embedding generation for semantic search
- **Database Storage**: Supabase integration with JSON field handling
- **Access Tracking**: Usage statistics and cognitive decay modeling
- **Success Monitoring**: Automatic effectiveness tracking

## Best Practices

### Storage
1. **Dialog Quality**: Include complete procedure explanations with context
2. **Step Detail**: Ensure procedures have clear, actionable steps
3. **Tool Specification**: List all required tools and dependencies
4. **Success Criteria**: Define clear completion indicators

### Search
5. **Search Strategy**: Use specific searches (domain, skill type) before semantic similarity
6. **Difficulty Filtering**: Match procedures to user skill level
7. **Success Rate Filtering**: Prefer procedures with proven track records
8. **Prerequisite Checking**: Verify you have required knowledge/tools

### Usage
9. **Success Tracking**: Update success rates after attempting procedures
10. **Iterative Improvement**: Refine procedures based on success data
11. **Knowledge Building**: Use prerequisites to plan learning sequences

## Testing

The service includes comprehensive test coverage:

```bash
# Run all tests
python -m pytest tools/services/memory_service/engines/tests/test_procedural_service.py -v

# Test results: ✅ 12 passed, 0 failed
```

**Test Coverage:**
- ✅ Intelligent dialog processing with complex step extraction
- ✅ All 5 search methods with realistic procedure scenarios
- ✅ Success rate tracking and updates
- ✅ Data validation and error handling
- ✅ Difficulty level classification
- ✅ Prerequisites and tools extraction

## Error Handling

The service gracefully handles:

- **Extraction Failures**: Falls back to basic step identification
- **Invalid Input**: Applies defaults and validation
- **Database Errors**: Returns detailed error messages
- **Complex Procedures**: Handles multi-step workflows efficiently
- **Network Issues**: Logs errors and returns failure status

## Performance Considerations

- **Step Processing**: Efficiently handles procedures with many steps (limited to 10)
- **Prerequisite Management**: Optimized storage and retrieval of requirement lists
- **Success Tracking**: Lightweight updates to procedure effectiveness metrics
- **Async Operations**: All operations are non-blocking
- **Memory Efficient**: Processes complex procedures without memory issues
- **Query Optimization**: Database searches use appropriate indexing strategies

## Comparison with Other Memory Types

| Feature | Episodic | Factual | Procedural |
|---------|----------|---------|------------|
| **Content Type** | Events & experiences | Facts & statements | Procedures & workflows |
| **Structure** | Temporal narrative | Subject-predicate-object | Step-by-step instructions |
| **Key Fields** | participants, location, emotional_valence | subject, predicate, object_value | steps, prerequisites, difficulty_level |
| **Search Focus** | When, where, who | What, confidence, verification | How, success_rate, tools_needed |
| **Use Cases** | Personal history, context | Knowledge base, assertions | Task execution, learning |

The Procedural Memory Service excels at capturing and organizing "how-to" knowledge, making it ideal for:

- **Technical Documentation**: Software procedures and workflows
- **Learning Materials**: Step-by-step tutorials and guides  
- **Process Management**: Business and operational procedures
- **Troubleshooting**: Systematic problem-solving approaches
- **Skill Development**: Progressive learning sequences
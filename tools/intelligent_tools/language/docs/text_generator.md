# Text Generator Documentation

## Overview

The `text_generator.py` provides a simple wrapper around the ISA client for text generation. It handles all the streaming complexities and just returns the final generated text.

## Usage

### Simple Generation

```python
from tools.services.intelligence_service.language.text_generator import generate

# Basic usage
result = await generate("What are the benefits of renewable energy?")
print(result)
```

### With Parameters

```python
# Control creativity with temperature
creative_text = await generate(
    "Write a short story about a robot",
    temperature=0.9,  # More creative
    max_tokens=200
)

conservative_text = await generate(
    "Explain quantum computing",
    temperature=0.1   # More deterministic
)
```

### Using the Class

```python
from tools.services.intelligence_service.language.text_generator import text_generator

result = await text_generator.generate("Your prompt here", temperature=0.5)
```

## API Reference

### `generate(prompt, **kwargs)`

Convenience function for text generation.

**Parameters:**
- `prompt` (str): The input prompt
- `temperature` (float, optional): Controls randomness (0.0-1.0, default: 0.7)
- `max_tokens` (int, optional): Maximum tokens to generate
- `**kwargs`: Additional parameters passed to ISA client

**Returns:**
- `str`: Generated text

### `TextGenerator.generate(prompt, **kwargs)`

Main generation method.

**Parameters:**
Same as convenience function.

**Returns:**
- `str`: Generated text

## Parameters

### Temperature
- **0.0-0.3**: Very deterministic, consistent outputs
- **0.4-0.7**: Balanced creativity and consistency (default: 0.7)
- **0.8-1.0**: More creative and varied outputs

### Max Tokens
- Limits the length of generated text
- If not specified, uses model defaults
- Useful for controlling response length

## Examples

### Chat Response
```python
response = await generate(
    "User: What's the weather like today?\nAssistant:",
    temperature=0.1  # Low for consistent responses
)
```

### Creative Writing
```python
story = await generate(
    "Write a science fiction story about time travel:",
    temperature=0.8,  # High for creativity
    max_tokens=500
)
```

### Code Generation
```python
code = await generate(
    "Write a Python function to calculate fibonacci numbers:",
    temperature=0.2,  # Low for accurate code
    max_tokens=300
)
```

### Summarization
```python
summary = await generate(
    f"Summarize the following text in 2 sentences:\n\n{long_text}",
    temperature=0.1
)
```

## Error Handling

The generator handles ISA client streaming automatically and logs costs. If generation fails, it will raise an exception with a descriptive error message.

```python
try:
    result = await generate("Your prompt")
    print(result)
except Exception as e:
    print(f"Generation failed: {e}")
```

## Performance Notes

- **Cost**: Each generation consumes tokens, typically $0.001-0.020 per request
- **Speed**: Generation typically takes 1-5 seconds depending on length
- **Streaming**: All streaming complexity is handled internally
- **Logging**: Costs are automatically logged for monitoring

## Integration

### In MCP Tools
```python
from tools.services.intelligence_service.language.text_generator import generate

class MyTool(BaseTool):
    async def process_request(self, user_input):
        response = await generate(f"Process this request: {user_input}")
        return response
```

### In Services
```python
from tools.services.intelligence_service.language.text_generator import text_generator

class AnalysisService:
    async def analyze_data(self, data):
        prompt = f"Analyze this data and provide insights: {data}"
        analysis = await text_generator.generate(prompt, temperature=0.3)
        return analysis
```

## Testing

Run the test suite:
```bash
python tools/services/intelligence_service/language/tests/test_text_generator.py
```

The tests cover:
- Basic text generation
- Parameter variations (temperature, max_tokens)
- Direct class usage
- Error handling scenarios

## Summary

The text generator provides a simple, clean interface to ISA's text generation capabilities:
- **Simple**: Just call `generate(prompt)` and get text back
- **Flexible**: Control creativity and length with parameters  
- **Robust**: Handles streaming and errors automatically
- **Efficient**: Logs costs and performance metrics
- **Easy Integration**: Works seamlessly with existing tools and services

Perfect for any application that needs AI text generation without the complexity of handling streaming responses.
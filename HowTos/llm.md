# LLM Service Documentation

LLM Service provides comprehensive text generation capabilities using various language models.

## 🚀 新的统一任务架构

我们引入了新的统一客户端设计，简化了API调用：

- **统一客户端**: 使用 `ISAModelClient` 进行所有服务调用
- **任务参数化**: 支持多种LLM任务类型
- **向后兼容**: 所有旧的使用方式仍然支持
- **统一响应**: 所有任务返回一致的响应格式

## Default Configuration

- **Provider**: `openai` 
- **Default Model**: `gpt-4.1-nano`
- **Alternative Models**: `gpt-4.1-mini`, `gpt-4o-mini`, `gpt-4o`

## Client Usage

### Basic Usage

```python
from isa_model.client import ISAModelClient

# Create client
client = ISAModelClient()


# Basic text generation (uses default openai/gpt-4.1-nano)
result = await client.invoke(
    input_data="Hello, what is 2+2?",   # Text prompt
    task="generate",                    # Core task
    service_type="text"                 # Service type
)

print(result["result"])                # "Hello! 2 + 2 equals 4."
```

### Supported Tasks

```python
# 🎯 核心任务 (推荐使用新的统一设计)
result = await client.invoke("Explain quantum computing", "chat", "text")     # 主要任务类型
result = await client.invoke("Summarize this text", "chat", "text")          # 使用 chat 进行摘要
result = await client.invoke("Translate to French", "chat", "text")          # 使用 chat 进行翻译
result = await client.invoke("What is the topic?", "chat", "text")           # 使用 chat 进行分类
result = await client.invoke("Have a conversation", "chat", "text")          # 对话任务
result = await client.invoke("Analyze this text", "chat", "text")            # 使用 chat 进行分析
result = await client.invoke("Extract information", "chat", "text")          # 使用 chat 进行提取
result = await client.invoke("Complete this text", "chat", "text")           # 使用 chat 进行补全

# 注意：OpenAI 服务主要支持 chat 任务，其他任务类型可能需要使用不同的提示词
```

### Custom Model Selection

```python
# Use specific OpenAI model
result = await client.invoke(
    "Explain machine learning", 
    "chat", 
    "text",
    model="gpt-4o-mini",              # Specify model
    provider="openai"                 # Specify provider
)

# Use premium model for complex tasks
result = await client.invoke(
    "Write a detailed analysis", 
    "chat",                           # Use chat task
    "text",
    model="gpt-4o",                   # Premium model
    max_tokens=2000
)
```

### Advanced Parameters

```python
# Text generation with custom parameters
result = await client.invoke(
    "Write a creative story", 
    "chat",                           # Use chat task (generate not supported)
    "text",
    temperature=0.9,
    max_tokens=1000,
    stream=True                       # Use 'stream' not 'streaming'
)

# Conversation with message history
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is machine learning?"}
]
result = await client.invoke(
    messages,
    "chat",                          # Chat task
    "text",
    temperature=0.7
)
```

## Response Format

```python
{
    "success": True,
    "result": "Hello! 2 + 2 equals 4.",
    "metadata": {
        "model_used": "gpt-4.1-nano",
        "provider": "openai", 
        "task": "generate",
        "service_type": "text",
        "selection_reason": "Default selection",
        "billing": {
            "cost_usd": 0.0001,
            "input_tokens": 10,
            "output_tokens": 15,
            "total_tokens": 25,
            "currency": "USD"
        }
    }
}
```

## Streaming Support

```python
# Enable streaming for real-time output (default for chat tasks)
result = await client.invoke(
    "Write a story about AI",
    "chat",                           # Use chat task
    "text"
)

# Access streamed content
if "stream" in result:
    async for chunk in result["stream"]:
        print(chunk, end="", flush=True)

# Disable streaming for immediate complete response
result = await client.invoke(
    "Write a story about AI",
    "chat",
    "text",
    stream=False                      # Disable streaming
)
print(result["result"].content)       # Get complete response immediately
```

## Direct Service Usage

```python
from isa_model.inference.ai_factory import AIFactory

# Get LLM service directly
factory = AIFactory()
llm_service = factory.get_llm(provider="openai")

# Use service methods directly
response = await llm_service.ainvoke("What is machine learning?")

# Streaming output
async for token in llm_service.astream("Write a poem"):
    print(token, end="", flush=True)

# Function calling
tools = [get_weather, calculate]
llm_with_tools = llm_service.bind_tools(tools)
response = await llm_with_tools.ainvoke("What's the weather in Paris?")
```

## Available Models

### gpt-4.1-nano (Default)
- **Use Case**: Basic text generation, simple tasks
- **Max Tokens**: 64,000
- **Cost**: Most economical option
- **Capabilities**: text_generation, completion, chat

### gpt-4.1-mini  
- **Use Case**: Standard tasks, balanced performance
- **Max Tokens**: 128,000
- **Cost**: Balanced cost/performance
- **Capabilities**: text_generation, completion, chat, summarization

### gpt-4o-mini
- **Use Case**: Complex reasoning, analysis tasks
- **Max Tokens**: 128,000  
- **Cost**: Premium option
- **Capabilities**: text_generation, completion, chat, analysis, translation

### gpt-4o
- **Use Case**: Most complex tasks, professional use
- **Max Tokens**: 200,000  
- **Cost**: Highest performance
- **Capabilities**: All features, advanced reasoning

## Task-Specific Examples

### Text Generation
```python
# 🎯 新的统一任务设计
result = await client.invoke(
    "Write a creative story about robots",
    "chat",                           # Use chat task
    "text",
    temperature=0.8,
    max_tokens=500
)
```

### Text Summarization
```python
# 🎯 新的统一任务设计
result = await client.invoke(
    "Summarize this long article: [article text]",
    "chat",                           # Use chat task
    "text",
    max_tokens=200
)
```

### Text Translation
```python
# 🎯 新的统一任务设计
result = await client.invoke(
    "Translate to French: Hello world",
    "chat",                           # Use chat task
    "text"
)
```

### Question Answering
```python
# 🎯 新的统一任务设计 - 使用 chat 进行问答
result = await client.invoke(
    "What is the capital of France?",
    "chat",                           # 使用 chat 任务进行问答
    "text"
)
```

## Error Handling

```python
try:
    # 推荐使用新的统一任务设计
    result = await client.invoke("Generate text", "chat", "text")
    if result["success"]:
        text = result["result"]
    else:
        print(f"Error: {result['error']}")
except Exception as e:
    print(f"Failed to generate text: {e}")
```

## Best Practices

1. **Model Selection**: Use `gpt-4.1-nano` for simple tasks, `gpt-4o` for complex analysis
2. **Task Design**: Use `chat` task for most text generation needs - it's the most stable and supported
3. **Streaming Control**: 
   - Use `stream=True` (default for chat) for real-time interactive responses
   - Use `stream=False` for batch processing or when you need complete response at once
4. **Cost Optimization**: Choose the minimum model that meets your needs
5. **Error Handling**: Always check the `success` field in responses
6. **Token Management**: Monitor token usage to control costs

## Streaming vs Non-Streaming

### When to Use Streaming (`stream=True`)
- Real-time chat applications
- Interactive user interfaces
- Long text generation where users want to see progress
- When you want to process tokens as they arrive

### When to Use Non-Streaming (`stream=False`)
- Batch processing
- When you need the complete response before proceeding
- API integrations where streaming adds complexity
- Short responses where streaming overhead isn't worth it

```python
# Streaming example (default for chat)
result = await client.invoke("Write a long story", "chat", "text")
if "stream" in result:
    async for chunk in result["stream"]:
        print(chunk, end="", flush=True)

# Non-streaming example  
result = await client.invoke("Write a long story", "chat", "text", stream=False)
complete_story = result["result"].content
print(complete_story)
```

## JSON Output Support

### Pure JSON Output (No Markdown)

The LLM service supports outputting pure JSON without markdown code blocks by using the `response_format` parameter:

```python
# Get pure JSON output
result = await client.invoke(
    "Extract data as JSON: name=John, age=30, city=NYC",
    "chat",
    "text",
    stream=False,  # Recommended for JSON output
    response_format={"type": "json_object"}  # Enable JSON mode
)

# The result will be valid JSON that can be parsed directly
data = json.loads(result["result"].content)
```

### Examples

#### Simple JSON Extraction
```python
result = await client.invoke(
    "Extract user data as JSON: name=Alice, email=alice@example.com",
    "chat",
    "text",
    stream=False,
    response_format={"type": "json_object"}
)
# Output: {"name": "Alice", "email": "alice@example.com"}
```

#### Complex Nested Structures
```python
result = await client.invoke(
    '''Create a product catalog entry:
    - product: {id: 1, name: "Laptop", price: 999}
    - inventory: {stock: 50, warehouse: "A1"}
    Return as JSON.''',
    "chat",
    "text", 
    stream=False,
    response_format={"type": "json_object"}
)
# Output: {"product": {"id": 1, "name": "Laptop", "price": 999}, "inventory": {"stock": 50, "warehouse": "A1"}}
```

### Important Notes

1. **Use `stream=False`** - For JSON output, disable streaming to get the complete response
2. **Add `response_format`** - Include `response_format={"type": "json_object"}` to enable JSON mode
3. **Clear Instructions** - Always specify in your prompt that you want JSON output
4. **Direct Parsing** - The output can be parsed directly with `json.loads()` without cleaning

## Configuration

OpenAI API key configuration is handled by the centralized ConfigManager. Ensure your OpenAI API key is properly configured in your environment or configuration files.

```bash
export OPENAI_API_KEY="your-api-key"
```

Or in your configuration:
```yaml
providers:
  openai:
    api_key: "your-api-key"
    organization: "your-org-id"  # optional
```

## Legacy Direct Service Usage (Still Supported)

```python
import asyncio
from isa_model.inference import AIFactory

async def legacy_example():
    # Create LLM service directly
    llm = AIFactory().get_llm()
    
    # Simple text generation
    response = await llm.ainvoke("Explain quantum computing in one sentence")
    print(response)
    
    # Using message lists
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is machine learning?"}
    ]
    response = await llm.ainvoke(messages)
    print(response)
    
    # Streaming output
    async for token in llm.astream("Write a short poem about coding"):
        print(token, end="", flush=True)
    
    await llm.close()

asyncio.run(legacy_example())
```

## Pricing Information

- **gpt-4.1-nano**: $0.1/$0.4 per 1M tokens (input/output)
- **gpt-4.1-mini**: $0.4/$1.6 per 1M tokens
- **gpt-4o-mini**: $0.15/$0.6 per 1M tokens
- **gpt-4o**: $5/$15 per 1M tokens

## Troubleshooting

### Common Issues

1. **API Key Error**
   ```
   Ensure OPENAI_API_KEY is properly configured in environment or config files
   ```

2. **Model Not Found**
   ```python
   # Check available models
   result = await client.invoke("test", "chat", "text", model="gpt-4.1-nano")
   ```

3. **Streaming Issues**
   ```python
   # Enable streaming properly
   result = await client.invoke("test", "chat", "text", stream=True)
   ```

4. **Network Timeout**
   ```python
   # Increase timeout
   result = await client.invoke("test", "chat", "text", timeout=60)
   ```

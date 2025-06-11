MEMORY_STORE = {}

@tool
async def store_memory(key: str, value: str, tool_call_id: Annotated[str, InjectedToolCallId], config: RunnableConfig) -> Command:
    """存储长期记忆"""
    MEMORY_STORE[key] = value
    return Command(update={"memory": MEMORY_STORE}, messages=[ToolMessage(content=f"Stored {key}: {value}", tool_call_id=tool_call_id)])

@tool
async def retrieve_memory(key: str, tool_call_id: Annotated[str, InjectedToolCallId], config: RunnableConfig) -> Command:
    """检索长期记忆"""
    value = MEMORY_STORE.get(key, "")
    return Command(update={"memory": MEMORY_STORE}, messages=[ToolMessage(content=f"Retrieved {key}: {value}", tool_call_id=tool_call_id)])
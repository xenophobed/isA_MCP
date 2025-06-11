@tool
async def assess_capability(task_name: str, tool_call_id: Annotated[str, InjectedToolCallId], config: RunnableConfig) -> Command:
    """评估能力"""
    # 模拟能力清单，实际可以动态评估
    capability_map = {
        "fetch_data": True,
        "automate_task": True,
        "complex_analysis": False  # 假设系统无法处理复杂分析
    }
    can_handle = capability_map.get(task_name, False)
    return Command(update={"capabilities": {task_name: can_handle}}, messages=[ToolMessage(content=f"Can handle {task_name}: {can_handle}", tool_call_id=tool_call_id)])
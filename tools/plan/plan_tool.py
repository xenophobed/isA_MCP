@tool
async def plan_tasks(input_data: str, memory: Dict[str, Any], capabilities: Dict[str, bool], tool_call_id: Annotated[str, InjectedToolCallId], config: RunnableConfig) -> Command:
    """动态规划任务，利用记忆和能力"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""
根据输入、记忆和能力生成任务计划：
- 输入: {input_data}
- 记忆: {memory}
- 能力: {capabilities}
格式：[{{"task_name": "...", "strategy": "...", "input": {{"key": "value"}}}}]
只生成系统有能力执行的任务，否则设置 needs_human=True
"""),
        ("human", input_data)
    ])
    response = await llm.ainvoke(prompt)
    tasks = json.loads(response.content)
    needs_human = any(not capabilities.get(t["task_name"], False) for t in tasks)
    return Command(
        update={"tasks": tasks, "needs_human": needs_human},
        messages=[ToolMessage(content=f"Planned: {tasks}, Needs human: {needs_human}", tool_call_id=tool_call_id)]
    )
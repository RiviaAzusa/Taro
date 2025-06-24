from typing import Optional, Callable

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph.graph import CompiledGraph




async def invoke_lark(
    agent: CompiledGraph,
    query: str,
    thread_id: Optional[str] = None,
    interrupt: Optional[Callable] = None,
    chunk_size: int = 30,
    recursion_limit: Optional[int] = 25,
):
    config = {}
    if thread_id:
        config = {"configurable": {"thread_id": thread_id}}

    invoked_state = {
        "messages": [HumanMessage(content=query)],
    }

    if recursion_limit:
        config["recursion_limit"] = recursion_limit

    with_subgraphs = True
    events = agent.astream(
        invoked_state,
        stream_mode="messages",
        config=config,
        subgraphs=with_subgraphs,
    )

    accumulated_content = ""

    async for event in events:
        if interrupt and interrupt():
            return

        if with_subgraphs:
            node_meta_data, (msg, metadata) = event
        else:
            msg, metadata = event

        yields = []
        if isinstance(msg, AIMessage):
            if msg.content:
                accumulated_content += msg.content
                if len(accumulated_content) >= chunk_size:
                    yields.append({"type": "text", "text": accumulated_content})
                    accumulated_content = ""
            elif msg.additional_kwargs.get("reasoning_content"):
                accumulated_content += msg.additional_kwargs.get("reasoning_content")
                if len(accumulated_content) >= chunk_size:
                    yields.append({"type": "text", "text": accumulated_content})
                    accumulated_content = ""

            elif msg.tool_calls:
                if accumulated_content:
                    yields.append({"type": "text", "text": accumulated_content})
                    accumulated_content = ""

                for tool_call in msg.tool_calls:
                    if tool_call["name"]:
                        yields.append({"type": "tool_call", "text": tool_call["name"]})
        elif isinstance(msg, ToolMessage):
            if accumulated_content:
                yields.append({"type": "text", "text": accumulated_content})
                accumulated_content = ""
            # Not yield tool message.

        else:
            pass

        if yields:
            yield yields

    if accumulated_content:
        yield [{"type": "text", "text": accumulated_content}]

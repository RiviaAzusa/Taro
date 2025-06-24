import asyncio

import pytest


from langchain_qwq import ChatQwen
from src.agents.agent import TaroAgent
from src.runner import TaroLarkRunner


@pytest.mark.asyncio
async def test_invoke_agent():
    runner = TaroLarkRunner(config="dev")
    agent = runner.build_agent(ChatQwen(model="qwen-turbo-latest"))

    res = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "搜索当前有哪些知识库？",
                }
            ]
        }
    )
    print(res)

import os
import pytest

from easylark.conn.larkapi import EasyLarkAPI

from src.core.lark_sync import LarkSynchronizer
from src.core.db_client import DatabaseClient
from src.core.rag import LarkRAGManager
from src.agents.toolkits import LarkToolkit, ListKBsTool, SearchDocsTool, WebSearchTool


@pytest.fixture
def larkAPI():
    return EasyLarkAPI(
        app_id=os.getenv("LARK_APP_ID"), app_secret=os.getenv("LARK_APP_SECRET")
    )


@pytest.fixture
def db_api():
    return DatabaseClient("resources/db/dev.db")


@pytest.fixture
def larkSynchronizer(larkAPI, db_api):
    return LarkSynchronizer(larkAPI, db_api)


@pytest.fixture
def rag_manager(
    larkSynchronizer,
):
    return LarkRAGManager(larkSynchronizer)


@pytest.mark.asyncio
async def test_toolkits(rag_manager):
    toolkits = LarkToolkit(rag_manager=rag_manager)
    list_kbs = ListKBsTool(rag_manager=rag_manager)
    # res = await list_kbs.ainvoke(input="你好，这是一个测试")
    # print(res)

    # "list[(space_id, desc)]: [('7098202022889160705', '# 7x One知识库\\n公司产研知识库')]"

    query_kb = SearchDocsTool(rag_manager=rag_manager)
    res = await query_kb.ainvoke(input={"query": "7xOne 有哪些产品"})
    print(res)

    # web_search_tool = WebSearchTool()
    # res = await web_search_tool.ainvoke(
    #     input={"query": "dpi是干什么的？", "engine": "serpapi", "max_results": 5}
    # )
    # print(res)

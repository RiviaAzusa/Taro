import os
import pytest

from easylark.conn.larkapi import EasyLarkAPI

from src.core.lark_sync import LarkSynchronizer
from src.core.db_client import DatabaseClient
from src.core.rag import RAGManager, KnowledgeBase


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
def wiki_setting_link():
    # return "7098202022889160705"
    return "7098202022889160705"


@pytest.fixture
def wiki_docx_link():
    return "JAYYdzytco7Y2nxTBe3chBD1n7f"


@pytest.mark.asyncio
async def test_fetch_wikis(larkSynchronizer, wiki_setting_link):
    items = await larkSynchronizer.fetch_all_wiki_nodes(wiki_setting_link)
    assert len(items) > 0


@pytest.mark.asyncio
async def test_get_docs_raw_content(larkAPI, wiki_docx_link):
    content = await larkAPI.do_get_doc_raw_content(file_token=wiki_docx_link)
    assert isinstance(content, str)


@pytest.mark.asyncio
async def test_save_all_wikis(larkSynchronizer, wiki_setting_link):
    items = await larkSynchronizer.fetch_all_wiki_nodes(wiki_setting_link)
    await larkSynchronizer.save_wiki_nodes(items)


@pytest.mark.asyncio
async def test_get_wiki_nodes_content(larkSynchronizer, wiki_setting_link):
    """
    get all wiki nodes content from database.
    """
    # Extract space_id from the test data (using the one we found in the database)

    # Call the function
    results = await larkSynchronizer.get_wiki_nodes_content(wiki_setting_link)
    # results: list[tuple[str, str, str]] (title, link, content)

    # Verify results
    assert isinstance(results, list)

    if results:  # If there are results
        for title, link, content in results:
            assert isinstance(title, str)
            assert isinstance(link, str)
            assert isinstance(content, str)
            assert link.startswith("https://")
            assert "/wiki/" in link
            print(f"Title: {title}")
            print(f"Link: {link}")
            print(f"Content length: {len(content)}")
            print("---")

    print(f"Total documents found: {len(results)}")


# Test RAG
@pytest.mark.asyncio
async def test_build_knowledge_base(larkSynchronizer, wiki_setting_link):
    """Test RAG system with different chunking configurations."""

    chunk_size = 500
    chunk_overlap = 50

    print(f"Chunk size: {chunk_size}, Overlap: {chunk_overlap}")

    # Initialize RAG with specific chunking parameters
    rag = RAGManager(
        lark_sync=larkSynchronizer,
    )

    await rag.build_knowledge_base(wiki_setting_link)


@pytest.mark.asyncio
async def test_load_query_db(larkSynchronizer, wiki_setting_link):
    kb = KnowledgeBase(wiki_setting_link, larkSynchronizer)
    kb.load()

    res = await kb.query("dpi流量分析")
    assert len(res) > 0
    for doc in res:
        print(doc)


@pytest.mark.asyncio
async def test_rag_manager(larkSynchronizer, wiki_setting_link):
    rag = RAGManager(
        lark_sync=larkSynchronizer,
    )
    kb = rag.load_knowledge_base(wiki_setting_link)

    kbs = rag.list_knowledge_bases()
    print(kbs)

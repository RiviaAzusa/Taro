import os
import pytest

from easylark.conn.larkapi import EasyLarkAPI

from src.core.lark_sync import LarkSynchronizer
from src.core.db_client import DatabaseClient

from src.core.lark_sync import LarkSynchronizer

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
    return "7511700730315653148"


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

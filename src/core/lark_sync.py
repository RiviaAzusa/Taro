import os
from easylark.conn.larkapi import EasyLarkAPI
from .db_client import DatabaseClient

from lark_oapi.api.wiki.v2.model import Node

"""
Taro
"""


class LarkSynchronizer:
    def __init__(self, lark_api: EasyLarkAPI, db_api: DatabaseClient):
        self.lark_api = lark_api
        self.db_api = db_api

    async def get_wiki_nodes_content(self, space_id: str) -> list[tuple[str, str, str]]:
        """
        use wiki space_id to get all contents from database.
        return: list[tuple[str, str, str]] (title, link, content)
        """
        if not self.db_api.connection:
            await self.db_api.connect()

        # Get tenant name from environment variable
        tenant_name = os.getenv("TENANT_NAME", "ucnc29ltq5gu")  # fallback to example

        # Query to get all documents in the space with their content
        query = """
        SELECT m.title, m.node_token, c.raw_content
        FROM docs_metadata m
        LEFT JOIN docs_content c ON m.obj_token = c.obj_token
        WHERE m.space_id = ? AND c.raw_content IS NOT NULL
        ORDER BY m.title
        """

        async with self.db_api.connection.cursor() as cursor:
            await cursor.execute(query, (space_id,))
            rows = await cursor.fetchall()

        results = []
        for row in rows:
            title, node_token, raw_content = row
            # Build the wiki link
            wiki_link = f"https://{tenant_name}.feishu.cn/wiki/{node_token}"
            results.append((title, wiki_link, raw_content))

        return results

    async def fetch_all_wiki_nodes(
        self, space_id: str, parent_node_token: str = None, page_size: int = 20
    ) -> list[Node]:
        """
        递归获取整个wiki空间下所有节点，包含所有子节点。
        :param api: EasyLarkAPI 实例
        :param space_id: 空间ID
        :param parent_node_token: 父节点token，根节点为None
        :param page_size: 每页大小
        :return: 所有item的list
        """
        all_items = []

        page_token = None
        while True:
            res = await self.lark_api.do_get_wiki_list(
                space_id=space_id,
                page_size=page_size,
                page_token=page_token,
                parent_node_token=parent_node_token,
            )
            if not res or not hasattr(res, "items") or not res.items:
                break

            for item in res.items:
                all_items.append(item)
                # 如果该节点有子节点，递归获取
                if getattr(item, "has_child", False):
                    # origin_node_token 作为 parent_node_token 递归
                    child_items = await self.fetch_all_wiki_nodes(
                        space_id,
                        parent_node_token=getattr(item, "origin_node_token", None),
                        page_size=page_size,
                    )
                    all_items.extend(child_items)

            # 是否还有下一页
            if getattr(res, "has_more", False):
                page_token = getattr(res, "page_token", None)
                if not page_token:
                    break
            else:
                break

        return all_items

    async def save_wiki_nodes(self, items: list[Node]):
        if not self.db_api.connection:  # Ensure connection is established
            await self.db_api.connect()

        await self.db_api.create_docs_metadata_table()
        await self.db_api.create_docs_content_table()

        for node in items:
            if node.obj_type != "docx":
                continue

            node_data = {}
            for field_name in Node._types.keys():
                if hasattr(node, field_name):
                    node_data[field_name] = getattr(node, field_name)

            # Ensure critical fields are present
            if not node.node_token or not node.obj_token or node.obj_edit_time is None:
                # print(f"Skipping node due to missing critical fields: {node.title}")
                continue

            existing_doc_meta = await self.db_api.get_doc_metadata(node.node_token)

            needs_update = True
            if existing_doc_meta:
                # existing_doc_meta is a tuple (obj_edit_time,)
                stored_obj_edit_time = existing_doc_meta[0]
                if stored_obj_edit_time is not None and int(node.obj_edit_time) <= int(
                    stored_obj_edit_time
                ):
                    needs_update = False
                    # print(f"Node {node.title} is up to date. DB: {stored_obj_edit_time}, Node: {node.obj_edit_time}")

            if needs_update:
                # print(f"Updating node: {node.title}")
                # Upsert metadata
                # Ensure all fields are correctly typed for the DB, e.g., bool to int
                # The upsert_doc_metadata method already handles bool for has_child
                await self.db_api.upsert_doc_metadata(node_data)

                # print(f"Downloading content for obj_token: {node.obj_token}")
                # Download raw content
                try:
                    raw_content = await self.lark_api.do_get_doc_raw_content(
                        file_token=node.obj_token
                    )
                    if raw_content is not None:  # Ensure content was fetched
                        await self.db_api.upsert_doc_content(
                            obj_token=node.obj_token, raw_content=raw_content
                        )
                        # print(f"Successfully saved content for {node.title}")
                    # else:
                    # print(f"Failed to download content for {node.title} (obj_token: {node.obj_token}), content was None.")
                except Exception as e:
                    # print(f"Error downloading/saving content for {node.title} (obj_token: {node.obj_token}): {e}")
                    # Consider how to handle errors: log, retry, skip?
                    pass  # For now, just pass
            # else:
            # print(f"Skipping update for node: {node.title}, no changes detected.")

    async def download_docs(self, items: list[Node]): ...

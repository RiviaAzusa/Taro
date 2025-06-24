import aiosqlite


class DatabaseClient:
    def __init__(self, db_file: str = "resources/db/dev.db"):
        self.db_file = db_file
        self.connection = None

    async def connect(self):
        self.connection = await aiosqlite.connect(self.db_file)
        # Ensure foreign key support is enabled if using them later (optional for now)
        # await self.connection.execute("PRAGMA foreign_keys = ON")

    async def close(self):
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def execute(self, query: str, params: tuple = ()):
        # It's generally better to use the connection provided by the context manager
        # for individual executions rather than relying on self.connection being always open.
        # However, for simplicity with the existing structure, we'll assume connect() is called.
        if not self.connection:
            await self.connect()  # Ensure connection exists
        # The original execute method was problematic as it opened a new connection for each execute.
        # Reverting to a simpler model, assuming self.connection is managed outside.
        # For multiple operations, it's better to pass the connection around or ensure it's managed.
        # For now, let's assume self.connection is valid.
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, params)
            await self.connection.commit()  # Ensure changes are committed

    async def fetchone(self, query: str, params: tuple = ()):
        if not self.connection:
            await self.connect()
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, params)
            return await cursor.fetchone()

    async def create_user_db_table(self, user_id: str): ...

    async def create_docs_metadata_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS docs_metadata (
            node_token TEXT PRIMARY KEY,
            space_id TEXT,
            obj_token TEXT,
            obj_type TEXT,
            parent_node_token TEXT,
            node_type TEXT,
            origin_node_token TEXT,
            origin_space_id TEXT,
            has_child INTEGER, -- SQLite uses INTEGER for boolean
            title TEXT,
            obj_create_time INTEGER,
            obj_edit_time INTEGER,
            node_create_time INTEGER,
            creator TEXT,
            owner TEXT,
            node_creator TEXT
        )
        """
        await self.execute(query)

    async def create_docs_content_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS docs_content (
            obj_token TEXT PRIMARY KEY,
            raw_content TEXT
        )
        """
        await self.execute(query)

    async def get_doc_metadata(self, node_token: str):
        query = "SELECT obj_edit_time FROM docs_metadata WHERE node_token = ?"
        row = await self.fetchone(query, (node_token,))
        return row if row else None

    async def upsert_doc_metadata(self, node_data: dict):
        # Ensure has_child is converted to integer for SQLite
        node_data["has_child"] = 1 if node_data.get("has_child") else 0

        columns = ", ".join(node_data.keys())
        placeholders = ", ".join(["?"] * len(node_data))
        values = tuple(node_data.values())

        query = f"""
        INSERT INTO docs_metadata ({columns})
        VALUES ({placeholders})
        ON CONFLICT(node_token) DO UPDATE SET
        """
        update_assignments = [
            f"{key} = excluded.{key}" for key in node_data.keys() if key != "node_token"
        ]
        query += ", ".join(update_assignments)

        await self.execute(query, values)

    async def upsert_doc_content(self, obj_token: str, raw_content: str):
        query = """
        INSERT INTO docs_content (obj_token, raw_content)
        VALUES (?, ?)
        ON CONFLICT(obj_token) DO UPDATE SET
        raw_content = excluded.raw_content
        """
        await self.execute(query, (obj_token, raw_content))

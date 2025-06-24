import os
import asyncio
import aiosqlite

from typing import Optional, Callable, AsyncGenerator

from loguru import logger
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ..utlis.config import Config, get_config
from ..utlis.lark_utils import invoke_lark
from ..core.rag import LarkRAGManager
from ..core.db_client import DatabaseClient
from ..core.lark_sync import LarkSynchronizer
from .prompt import agent_prompt


class State(AgentState):
    open_id: str


class Agent:
    def __init__(self, config: str | Config = "dev", lark_api=None):
        if isinstance(config, str):
            self.config = get_config(config)
        else:
            self.config = config

        if lark_api is None:
            from easylark.conn import EasyLarkAPI

            lark_api = EasyLarkAPI(
                app_id=os.getenv("LARK_APP_ID"), app_secret=os.getenv("LARK_APP_SECRET")
            )

        # 初始化数据组件
        self.db_api = DatabaseClient(self.config.db_file)
        self.lark_synchronizer = LarkSynchronizer(lark_api, self.db_api)
        self.rag_manager = LarkRAGManager(self.lark_synchronizer, self.config.kb_folder)

        # Agent相关
        self.agent: Optional[CompiledGraph] = None
        self.checkpointer = None

    def build_agent(self, model) -> CompiledGraph:
        """构建LangGraph agent

        Args:
            model: LLM模型实例

        Returns:
            CompiledGraph: 编译后的 agent
        """
        tools = self._create_tools()
        self.checkpointer = MemorySaver()

        # self.build_checkpointer()

        # 创建react agent
        self.agent = create_react_agent(
            model=model,
            tools=tools,
            prompt=agent_prompt,
            state_schema=State,
            checkpointer=self.checkpointer,
        )
        return self.agent

    async def invoke2lark(
        self,
        query: str,
        thread_id: Optional[str] = None,
        interrupt: Optional[Callable] = None,
        chunk_size: int = 30,
        recursion_limit: Optional[int] = 25,
    ) -> AsyncGenerator[dict, None]:
        """主要接口：通过invoke_lark运行agent并生成流式响应

        这是Agent与LarkRunner交互的唯一接口

        Args:
            query: 用户查询
            thread_id: 线程ID
            interrupt: 中断检查函数
            chunk_size: 文本块大小
            recursion_limit: 递归限制

        Yields:
            dict: 包含type和text的字典
        """
        if not self.agent:
            raise ValueError("请先调用build_agent()来创建agent")

        async for chunks in invoke_lark(
            agent=self.agent,
            query=query,
            thread_id=thread_id,
            interrupt=interrupt,
            chunk_size=chunk_size,
            recursion_limit=recursion_limit,
        ):
            for chunk in chunks:
                yield chunk

    def _create_tools(self):
        """创建工具列表"""
        from .toolkits import LarkToolkit

        toolkit = LarkToolkit(rag_manager=self.rag_manager)
        return toolkit.get_tools()

    # async def build_checkpointer(self):
    #     self.conn = await aiosqlite.connect(self.config.db_file)
    #     self.checkpointer = AsyncSqliteSaver(self.conn)

    # async def close_conn(self):
    #     await self.conn.close()

    # def __del__(self):
    #     self.conn.close()
    #     logger.info("Checkpointer closed")

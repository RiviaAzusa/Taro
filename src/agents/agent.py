import os
import asyncio
from typing import Optional, Callable

from langchain_core.tools import tool
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from ..utlis.config import Config
from ..core.rag import LarkRAGManager

from .prompt import agent_prompt


class TaroAgent:
    """Taro LangGraph Agent"""

    def __init__(self, rag_manager: LarkRAGManager, config: Config):
        self.rag_manager = rag_manager
        self.config = config
        self.agent = None
        self.checkpointer = MemorySaver()

    def build_agent(self, model) -> CompiledGraph:
        """构建LangGraph agent

        Args:
            model: LLM模型实例

        Returns:
            CompiledGraph: 编译后的 agent
        """
        tools = self._create_tools()

        # 创建react agent
        self.agent = create_react_agent(
            model=model,
            tools=tools,
            prompt=agent_prompt,
            # checkpointer=self.checkpointer,
        )
        return self.agent

    async def invoke_agent(
        self,
        query: str,
        thread_id: Optional[str] = None,
        interrupt: Optional[Callable] = None,
        chunk_size: int = 30,
        recursion_limit: Optional[int] = 25,
    ):
        """运行agent并生成流式响应

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

        from ..utlis.invoke_lark import invoke_lark

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

        @tool
        def search_docs(query: str, space_id: str = None) -> str:
            """搜索文档内容。如果指定space_id则搜索特定知识库，否则搜索所有可用知识库。

            Args:
                query: 搜索查询
                space_id: 可选，知识库ID

            Returns:
                搜索结果文本
            """
            try:
                if space_id:
                    # 搜索特定知识库
                    results = asyncio.run(
                        self.rag_manager.query(space_id, query, top_k=3)
                    )
                    content = "\n\n".join([doc.page_content for doc in results])
                    return f"知识库 {space_id} 中的搜索结果:\n{content}"
                else:
                    # 搜索所有可用知识库
                    available_kbs = self.rag_manager.list_knowledge_bases()
                    if not available_kbs:
                        return "暂无可用的知识库"

                    all_results = []
                    for kb_id in available_kbs[:3]:  # 限制搜索数量
                        try:
                            results = asyncio.run(
                                self.rag_manager.query(kb_id, query, top_k=2)
                            )
                            for doc in results:
                                all_results.append(
                                    f"[知识库: {kb_id}] {doc.page_content}"
                                )
                        except Exception as e:
                            continue

                    return "\n\n".join(all_results) if all_results else "未找到相关内容"
            except Exception as e:
                return f"搜索出错: {str(e)}"

        @tool
        def list_kbs() -> str:
            """列出所有可用的知识库。

            Returns:
                知识库列表文本
            """
            try:
                available_kbs: list[(str, str)] = (
                    self.rag_manager.list_knowledge_bases()
                )  # space_id, desc

                if not available_kbs:
                    return "暂无可用的知识库"
                return f"list[(space_id, desc)]: {str(available_kbs)}"

            except Exception as e:
                return f"获取知识库列表出错: {str(e)}"

        return [search_docs, list_kbs]

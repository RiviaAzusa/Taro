import asyncio
from typing import Type, Optional
from pydantic import BaseModel, Field, ConfigDict
from loguru import logger

from langchain_core.tools import BaseTool
from langchain_core.tools.base import BaseToolkit

from ..core.rag import LarkRAGManager


class SearchDocsTool(BaseTool):
    """Tool for searching document content in knowledge bases"""

    name: str = "search_docs"
    description: str = (
        "搜索文档内容。如果space_id则搜索特定知识库，否则搜索所有可用知识库。"
    )

    rag_manager: LarkRAGManager = Field(exclude=True)

    class Input(BaseModel):
        space_id: Optional[str] = Field(None, description="知识库ID")
        query: str = Field(..., description="")

    args_schema: Type[BaseModel] = Input

    def _run(self, *args, **kwargs):
        raise NotImplementedError(
            "This tool only supports async execution. Please use _arun() instead."
        )

    async def _arun(
        self,
        query: str,
        space_id: Optional[str] = None,
    ) -> str:
        """Execute document search"""
        try:
            if space_id:
                # 搜索特定知识库
                results = await self.rag_manager.query(space_id, query, top_k=3)
                content = "\n\n".join([doc.page_content for doc in results])
                return f"知识库 {space_id} 中的搜索结果:\n{content}"
            else:
                # 搜索所有可用知识库
                available_kbs = self.rag_manager.list_knowledge_bases()
                if not available_kbs:
                    return "暂无可用的知识库"

                all_results = []
                for kb_id, kb_name in available_kbs[:3]:  # 限制搜索数量
                    try:
                        results = await self.rag_manager.query(kb_id, query, top_k=2)
                        for doc in results:
                            all_results.append(
                                f"[知识库: {kb_name}]: {doc.page_content}"
                            )
                    except Exception as e:
                        logger.error(f"搜索知识库 {kb_name} 出错: {str(e)}")
                        continue

                return "\n\n".join(all_results) if all_results else "未找到相关内容"
        except Exception as e:
            return f"搜索出错: {str(e)}"


class ListKBsTool(BaseTool):
    """Tool for listing all available knowledge bases"""

    name: str = "list_kbs"
    description: str = "列出所有可用的知识库。"

    rag_manager: LarkRAGManager = Field(exclude=True)

    class Input(BaseModel):
        pass  # 此工具不需要输入参数

    args_schema: Type[BaseModel] = Input

    def _run(self, *args, **kwargs):
        raise NotImplementedError(
            "This tool only supports async execution. Please use _arun() instead."
        )

    async def _arun(self) -> str:
        """List all available knowledge bases"""
        try:
            available_kbs: list[(str, str)] = (
                self.rag_manager.list_knowledge_bases()
            )  # space_id, desc

            if not available_kbs:
                return "暂无可用的知识库"
            return f"list[(space_id, desc)]: {str(available_kbs)}"

        except Exception as e:
            return f"获取知识库列表出错: {str(e)}"


class WebSearchTool(BaseTool):
    """Tool for web search - supports multiple search engines"""

    name: str = "web_search"
    description: str = "搜索网络内容，请加入主题"

    class Input(BaseModel):
        query: str = Field(..., description="搜索查询")
        engine: str = Field(
            default="tavily", description="搜索引擎选择: tavily, duckduckgo"
        )
        max_results: int = Field(default=5, description="最大结果数量")

    args_schema: Type[BaseModel] = Input

    def _run(self, *args, **kwargs):
        raise NotImplementedError(
            "This tool only supports async execution. Please use _arun() instead."
        )

    async def _arun(
        self, query: str, engine: str = "tavily", max_results: int = 5
    ) -> str:
        """Execute web search using specified engine"""

        if engine == "tavily":
            # Tavily Search - 专为AI优化的搜索引擎
            try:
                from langchain_tavily import TavilySearch

                tool = TavilySearch(max_results=max_results)
                result = await tool.ainvoke({"query": query})
                return f"Tavily搜索结果: {result}"
            except ImportError:
                return "Tavily未安装，请安装: pip install langchain-tavily"
            except Exception as e:
                return f"Tavily搜索失败: {str(e)}"

        elif engine == "duckduckgo":
            # DuckDuckGo Search - 免费隐私友好搜索
            try:
                from langchain_community.tools import DuckDuckGoSearchResults

                tool = DuckDuckGoSearchResults(num_results=max_results)
                result = await tool.ainvoke({"query": query})
                return f"DuckDuckGo搜索结果: {result}"
            except ImportError:
                return "DuckDuckGo搜索未安装，请安装: pip install duckduckgo-search"
            except Exception as e:
                return f"DuckDuckGo搜索失败: {str(e)}"

        else:
            return (
                f"不支持的搜索引擎: {engine}. 支持的引擎: tavily, duckduckgo, serpapi"
            )


class CreateLarkDocToolkit(BaseTool):
    """
    create doc and send to user.
    """


class DeepResearchTool(BaseTool):
    """
    DeerFlow DeepResearch as a Tool.
    """

    name: str = "deep_research"
    description: str = (
        "执行深度研究任务。使用DeerFlow的AI研究能力对给定主题进行全面分析和调研。"
    )

    class Input(BaseModel):
        query: str = Field(..., description="研究查询或主题")
        debug: bool = Field(default=False, description="是否启用调试模式")
        max_plan_iterations: int = Field(default=3, description="最大计划迭代次数")
        max_step_num: int = Field(default=20, description="计划中的最大步骤数")
        enable_background_investigation: bool = Field(
            default=False, description="是否启用背景调查（网络搜索）"
        )

    args_schema: Type[BaseModel] = Input

    def _run(self, *args, **kwargs):
        raise NotImplementedError(
            "This tool only supports async execution. Please use _arun() instead."
        )

    async def _arun(
        self,
        query: str,
        debug: bool = False,
        max_plan_iterations: int = 3,
        max_step_num: int = 20,
        enable_background_investigation: bool = False,
    ) -> str:
        """Execute deep research using DeerFlow"""
        try:
            import sys
            import os

            # Add deer_flow to path
            deer_flow_path = os.path.join(os.getcwd(), "deer_flow")
            if deer_flow_path not in sys.path:
                sys.path.insert(0, deer_flow_path)

            from deer_flow.src.graph import build_graph

            # Create the graph
            graph = build_graph()

            if not query:
                return "查询不能为空"

            logger.info(f"开始深度研究: {query}")

            initial_state = {
                "messages": [{"role": "user", "content": query}],
                "auto_accepted_plan": True,
                "enable_background_investigation": enable_background_investigation,
            }

            config = {
                "configurable": {
                    "thread_id": "deep_research_tool",
                    "max_plan_iterations": max_plan_iterations,
                    "max_step_num": max_step_num,
                },
                "recursion_limit": 100,
            }

            final_report = None

            async for s in graph.astream(
                input=initial_state, config=config, stream_mode="values"
            ):
                if isinstance(s, dict) and "final_report" in s:
                    final_report = s["final_report"]
                    break

            if final_report:
                logger.info("深度研究完成")
                return final_report
            else:
                return "研究过程中未能生成最终报告"

        except ImportError as e:
            logger.error(f"导入DeerFlow模块失败: {str(e)}")
            return f"无法导入DeerFlow模块: {str(e)}。请确保deer_flow目录存在且包含必要的模块。"
        except Exception as e:
            logger.error(f"深度研究执行失败: {str(e)}")
            return f"深度研究执行失败: {str(e)}"


class LarkToolkit(BaseToolkit):
    """Toolkit containing all Lark-related tools"""

    rag_manager: LarkRAGManager = Field(exclude=True)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_tools(self) -> list[BaseTool]:
        """Get all tools in this toolkit"""
        return [
            SearchDocsTool(rag_manager=self.rag_manager),
            WebSearchTool(),
        ]

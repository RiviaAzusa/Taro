# Taro Lark Runner - 飞书端交互逻辑
import os
from typing import Literal, Optional, Callable
from pydantic import BaseModel

from easylark.conn import EasyLarkAPI, EasyLarkWsServer
from easylark.client.lark_client import LarkClient
from .utlis.config import Config, get_config
from .utlis.logger_config import logger
from .core.db_client import DatabaseClient
from .core.lark_sync import LarkSynchronizer
from .core.rag import LarkRAGManager
from .agents.agent import TaroAgent


class RuntimeConfig(BaseModel):
    chat_title: str = None
    thread_id: Optional[str] = None
    tenant_id: Optional[str] = None

    messages_len: int = 1
    max_messages_len: int = 10
    messages_queue: list[str] = []
    take_interupt: Optional[bool] = None
    processing: bool = False


class TaroLarkRunner:
    def __init__(self, config: str | Config = "dev"):
        if isinstance(config, str):
            self.config = get_config(config)
        else:
            self.config = config

        self.lark_api = EasyLarkAPI(
            app_id=os.getenv("LARK_APP_ID"), app_secret=os.getenv("LARK_APP_SECRET")
        )
        self.db_api = DatabaseClient(self.config.db_file)
        self.larkSynchronizer = LarkSynchronizer(self.lark_api, self.db_api)
        self.rag_manager = LarkRAGManager(self.larkSynchronizer, self.config.kb_folder)
        self.lark_client = LarkClient(self.lark_api)
        self.lark_ws = None
        self.runtime_configs = {}

        # 初始化 TaroAgent
        self.taro_agent = TaroAgent(self.rag_manager, self.config)

    def build_agent(self, model):
        """构建LangGraph agent

        Args:
            model: LLM模型实例
        """
        return self.taro_agent.build_agent(model)

    def set_agent(self, agent: Any):
        self.agent = agent

    async def callback_card_action(self, open_id: str, chat_id: str, actions: dict):
        """
        处理卡片点击事件的回调
        设置中断标志来停止对应会话的消息发送
        """
        runtime_config = self.runtime_configs.get((open_id, chat_id), None)
        if actions["name"] == "stop":
            runtime_config.take_interupt = True
            card_content = {"toast": {"type": "info", "content": "已停止生成"}}
            # do stop -> update the card -> `icon:stop` to `icon:retry`
        elif actions["name"] == "retry":
            card_content = {"toast": {"type": "info", "content": "已重试"}}
            # do retry -> update the card -> `icon:retry` to `icon:stop`
        elif actions["name"] == "new_chat":
            card_content = {"toast": {"type": "info", "content": "已清除上下文"}}
            self._do_new_chat(runtime_config)

        elif actions["name"] == "setting":
            card_content = {
                "toast": {"type": "info", "content": "抱歉，现在还不支持设置～"}
            }
        else:
            # do nothing
            card_content = {"toast": {"type": "info", "content": "未知操作"}}
        return card_content

    async def callback_reply_message(
        self,
        open_id: str,
        chat_id: str,
        msg_id: str,
        content: str,
        recv_id_type: Literal["open_id", "chat_id"],
    ):
        if (open_id, chat_id) not in self.runtime_configs:
            self.runtime_configs[(open_id, chat_id)] = RuntimeConfig()

        runtime_config = self.runtime_configs[(open_id, chat_id)]

        runtime_config.messages_queue.append(content)

        if runtime_config.thread_id is None:
            runtime_config.thread_id = msg_id
            runtime_config.chat_title = "**New Chat**"

        if not runtime_config.processing:
            await self._process_next_message(open_id, chat_id, recv_id_type)

    async def _process_next_message(
        self, open_id: str, chat_id: str, recv_id_type: Literal["open_id", "chat_id"]
    ):
        """处理队列中的下一条消息"""
        runtime_config = self.runtime_configs.get((open_id, chat_id))
        if not runtime_config or not runtime_config.messages_queue:
            return
        runtime_config.processing = True
        content = runtime_config.messages_queue[0]

        def check_interrupt():
            if runtime_config.take_interupt:
                return True
            return False

        await self.lark_client.send_card_pipeline(
            self._run_workflow(
                content,
                interrupt=check_interrupt,
                thread_id=runtime_config.thread_id,
            ),
            open_id,
            chat_id,
            recv_id_type,
            injection_config=runtime_config.model_dump(),
        )
        runtime_config.messages_len += 1
        runtime_config.messages_queue.pop(0)
        runtime_config.processing = False

        # 处理队列中的下一条消息
        if runtime_config.messages_queue:
            await self._process_next_message(open_id, chat_id, recv_id_type)

    async def _run_workflow(
        self,
        content: str,
        interrupt: Optional[Callable] = None,
        thread_id: Optional[str] = None,
    ):
        """Run Agent 并生成流式响应

        Args:
            content: 用户输入内容
            interrupt: 中断检查函数
            thread_id: 线程ID

        Yields:
            dict: 包含type和text的字典
        """
        async for chunk in self.taro_agent.invoke_agent(
            query=content,
            thread_id=thread_id,
            interrupt=interrupt,
            chunk_size=30,
            recursion_limit=25,
        ):
            yield chunk

    def _do_new_chat(self, runtime_config: RuntimeConfig):
        """清除会话上下文

        Args:
            runtime_config: 运行时配置
        """
        runtime_config.thread_id = None
        runtime_config.chat_title = "**New Chat**"
        runtime_config.messages_len = 1
        runtime_config.messages_queue.clear()
        runtime_config.take_interupt = None
        runtime_config.processing = False

    def start(self):
        """启动WebSocket服务器"""
        if not self.taro_agent.agent:
            raise ValueError("请先调用build_agent()来创建 agent")

        # 初始化WebSocket服务器
        self.lark_ws = EasyLarkWsServer(
            app_id=os.getenv("LARK_APP_ID"),
            app_secret=os.getenv("LARK_APP_SECRET"),
            callback_reply_message=self.callback_reply_message,
            callback_card_action=self.callback_card_action,
        )

        # 启动服务器
        self.lark_ws.start()

    def run(self):
        """启动服务"""
        self.start()

# Taro Lark Runner - 飞书端交互逻辑
import os
from typing import Literal, Optional, Any
from pydantic import BaseModel

from easylark.conn import EasyLarkAPI, EasyLarkWsServer
from easylark.client.lark_client import LarkClient
from .utlis.config import Config, get_config
from .utlis.logger_config import logger
from .agents.agent import Agent


class RuntimeConfig(BaseModel):
    chat_title: str = None
    thread_id: Optional[str] = None
    tenant_id: Optional[str] = None

    messages_len: int = 1
    max_messages_len: int = 10
    messages_queue: list[str] = []
    take_interupt: Optional[bool] = None
    processing: bool = False


class LarkRunner:
    """飞书交互运行器 - 专注于飞书WebSocket连接和消息处理"""

    def __init__(self, config: str | Config = "dev"):
        if isinstance(config, str):
            self.config = get_config(config)
        else:
            self.config = config

        # 初始化飞书相关组件
        self.lark_api = EasyLarkAPI(
            app_id=os.getenv("LARK_APP_ID"),
            app_secret=os.getenv("LARK_APP_SECRET"),
            log_level="INFO",
            auto_refresh=True,
        )
        self.lark_client = LarkClient(self.lark_api)
        self.lark_ws = None

        # Agent实例 - 由外部设置
        self.agent: Optional[Agent] = None

        # 运行时配置
        self.runtime_configs: dict[str, RuntimeConfig] = {}

    def set_agent(self, agent: Agent):
        """设置Agent实例

        Args:
            agent: 已配置好的Agent实例
        """
        self.agent = agent

    async def call_back_hello(
        self, open_id, chat_id, recv_id_id_type: Literal["open_id", "chat_id"]
    ):
        card_content = '{"data":{"template_id":"AAqIOw1f3LPoL","template_version_name":"1.0.3"},"type":"template"}'
        sent_id = open_id if recv_id_id_type == "open_id" else chat_id
        await self.lark_api.do_send_msg(
            sent_id, card_content, "interactive", recv_id_id_type
        )

    async def callback_card_action(self, open_id: str, chat_id: str, actions: dict):
        """处理卡片点击事件的回调"""
        if (open_id, chat_id) not in self.runtime_configs:
            self.runtime_configs[(open_id, chat_id)] = RuntimeConfig()

        runtime_config = self.runtime_configs[(open_id, chat_id)]

        if actions["name"] == "stop":
            runtime_config.take_interupt = True
            card_content = {"toast": {"type": "info", "content": "已停止生成"}}
        elif actions["name"] == "retry":
            card_content = {"toast": {"type": "info", "content": "已重试"}}
        elif actions["name"] == "new_chat":
            card_content = {"toast": {"type": "info", "content": "已清除上下文"}}
            self._clear_chat_context(runtime_config)
        elif actions["name"] == "setting":
            card_content = {
                "toast": {"type": "info", "content": "抱歉，现在还不支持设置～"}
            }
        else:
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
        """处理飞书消息回复"""
        # 获取或创建运行时配置
        if (open_id, chat_id) not in self.runtime_configs:
            self.runtime_configs[(open_id, chat_id)] = RuntimeConfig()

        runtime_config = self.runtime_configs[(open_id, chat_id)]

        # 添加消息到队列
        runtime_config.messages_queue.append(content)

        # 初始化会话
        if runtime_config.thread_id is None:
            runtime_config.thread_id = msg_id
            runtime_config.chat_title = f"**{content}**"

        # 如果当前没有正在处理的消息，开始处理
        if not runtime_config.processing:
            await self._process_message_queue(open_id, chat_id, recv_id_type)

    async def _process_message_queue(
        self, open_id: str, chat_id: str, recv_id_type: Literal["open_id", "chat_id"]
    ):
        """处理消息队列中的消息"""
        runtime_config = self.runtime_configs.get((open_id, chat_id))
        if not runtime_config or not runtime_config.messages_queue:
            return

        runtime_config.processing = True

        try:
            content = runtime_config.messages_queue[0]

            # 定义中断检查函数
            def check_interrupt():
                return runtime_config.take_interupt is True

            # 通过invoke_lark接口运行agent
            await self.lark_client.send_card_pipeline(
                self.agent.invoke2lark(
                    query=content,
                    thread_id=runtime_config.thread_id,
                    interrupt=check_interrupt,
                    chunk_size=30,
                    recursion_limit=25,
                ),
                open_id,
                chat_id,
                recv_id_type,
                injection_config=runtime_config.model_dump(),
            )

            # 更新状态
            runtime_config.messages_len += 1
            runtime_config.messages_queue.pop(0)
            runtime_config.take_interupt = None

        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
        finally:
            runtime_config.processing = False

        # 继续处理队列中的下一条消息
        if runtime_config.messages_queue:
            await self._process_message_queue(open_id, chat_id, recv_id_type)

    def _clear_chat_context(self, runtime_config: RuntimeConfig):
        """清除会话上下文"""
        runtime_config.thread_id = None
        runtime_config.chat_title = "**New Chat**"
        runtime_config.messages_len = 1
        runtime_config.messages_queue.clear()
        runtime_config.take_interupt = None
        runtime_config.processing = False

    def start(self):
        """启动WebSocket服务器"""
        if not self.agent:
            raise ValueError("请先调用set_agent()来指定agent")

        # 初始化WebSocket服务器
        self.lark_ws = EasyLarkWsServer(
            app_id=os.getenv("LARK_APP_ID"),
            app_secret=os.getenv("LARK_APP_SECRET"),
            callback_reply_message=self.callback_reply_message,
            callback_card_action=self.callback_card_action,
            callback_hello=self.call_back_hello,
        )

        # 启动服务器
        self.lark_ws.start()

    def run(self):
        """启动服务 - 入口方法"""
        self.start()

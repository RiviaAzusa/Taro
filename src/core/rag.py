import os
from pathlib import Path
from src.core.lark_sync import LarkSynchronizer
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_community.embeddings import DashScopeEmbeddings
from typing import Optional, List, Dict, Tuple
from src.utlis.logger_config import logger


class KnowledgeBase:
    """单个RAG知识库，负责构建、保存、加载和查询"""

    def __init__(
        self,
        space_id: str,
        lark_sync: LarkSynchronizer,
        embeddings: Optional[Embeddings] = None,
        storage_folder: str = "resources/kb",
    ):
        self.space_id = space_id
        self.desc = ""

        self.lark_sync = lark_sync
        self.embeddings = embeddings or DashScopeEmbeddings(model="text-embedding-v4")
        self.vector_store: Optional[FAISS] = None
        self.storage_folder = storage_folder

        self.is_built = False

        # 尝试读取README.md文件作为描述
        self._load_description()

    def _load_description(self) -> None:
        """从README.md文件加载知识库描述"""
        readme_path = os.path.join(self.storage_folder, self.space_id, "README.md")
        try:
            if os.path.exists(readme_path):
                with open(readme_path, "r", encoding="utf-8") as f:
                    self.desc = f.read().strip()
                logger.info(f"Loaded description for knowledge base {self.space_id}")
        except Exception as e:
            logger.warning(f"Failed to load description for {self.space_id}: {str(e)}")
            self.desc = ""

    def _save_description(self, save_path: str) -> None:
        """保存知识库描述到README.md文件"""
        readme_path = os.path.join(save_path, "README.md")
        try:
            with open(readme_path, "w", encoding="utf-8") as f:
                if self.desc:
                    f.write(self.desc)
                else:
                    f.write(
                        f"# Knowledge Base: {self.space_id}\n\nThis knowledge base was created from Lark Wiki Space: {self.space_id}"
                    )
            logger.info(f"Saved description for knowledge base {self.space_id}")
        except Exception as e:
            logger.warning(f"Failed to save description for {self.space_id}: {str(e)}")

    async def build(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        """构建知识库"""
        # 获取原始文档
        documents = await self._fetch_documents()

        if not documents:
            raise ValueError(f"No documents found for space_id: {self.space_id}")

        # 分割文档
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        split_docs = text_splitter.split_documents(documents)

        # 添加元数据
        for i, doc in enumerate(split_docs):
            doc.metadata.update(
                {
                    "chunk_id": i,
                    "space_id": self.space_id,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                }
            )

        # 创建向量存储
        self.vector_store = FAISS.from_documents(split_docs, self.embeddings)
        self.is_built = True

        logger.info(f"Built knowledge base for space {self.space_id}")
        logger.info(f"Documents: {len(documents)}, Chunks: {len(split_docs)}")
        logger.info(f"Chunk size: {chunk_size}, Overlap: {chunk_overlap}")

    async def query(self, query: str, top_k: int = 5) -> List[Document]:
        """查询知识库"""
        if not self.is_built or not self.vector_store:
            raise ValueError("Knowledge base not built yet. Call build() first.")

        return self.vector_store.similarity_search(query, k=top_k)

    def save(self, save_path: str) -> None:
        """保存知识库"""
        if not self.is_built or not self.vector_store:
            raise ValueError("Knowledge base not built yet. Call build() first.")

        Path(save_path).mkdir(parents=True, exist_ok=True)
        self.vector_store.save_local(save_path)
        # 保存描述文件
        self._save_description(save_path)
        logger.info(f"Knowledge base saved to: {save_path}")

    def load(self, load_path: str = None) -> None:
        """加载知识库"""
        if not load_path:
            load_path = os.path.join(self.storage_folder, self.space_id)

        if not os.path.exists(load_path):
            raise FileNotFoundError(f"Knowledge base not found at: {load_path}")

        self.vector_store = FAISS.load_local(
            load_path, self.embeddings, allow_dangerous_deserialization=True
        )
        self.is_built = True
        # 重新加载描述
        self._load_description()
        logger.info(f"Knowledge base loaded from: {load_path}")

    def get_info(self) -> Dict:
        """获取知识库信息"""
        if not self.is_built or not self.vector_store:
            return {
                "space_id": self.space_id,
                "status": "not_built",
                "description": self.desc,
            }

        return {
            "space_id": self.space_id,
            "status": "built",
            "total_chunks": len(self.vector_store.index_to_docstore_id),
            "description": self.desc,
        }

    async def _fetch_documents(self) -> List[Document]:
        """从Lark获取文档"""
        documents = []
        results = await self.lark_sync.get_wiki_nodes_content(self.space_id)

        for title, link, content in results:
            if not content or not content.strip():
                continue

            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": link,
                        "title": title,
                        "space_id": self.space_id,
                    },
                )
            )
        return documents


class LarkRAGManager:
    """RAG管理器，负责管理多个知识库的存储和访问"""

    def __init__(
        self,
        lark_sync: LarkSynchronizer,
        storage_folder: str = "resources/kb",
        embeddings: Optional[Embeddings] = None,
    ):
        self.storage_folder = Path(storage_folder)
        self.lark_sync = lark_sync
        self.embeddings = embeddings or DashScopeEmbeddings(model="text-embedding-v4")
        self.knowledge_bases: Dict[str, KnowledgeBase] = {}

        # 确保存储文件夹存在
        self.storage_folder.mkdir(parents=True, exist_ok=True)

    def get_knowledge_base(self, space_id: str) -> KnowledgeBase:
        """获取或创建知识库"""
        if space_id not in self.knowledge_bases:
            self.knowledge_bases[space_id] = KnowledgeBase(
                space_id=space_id, lark_sync=self.lark_sync, embeddings=self.embeddings
            )
        return self.knowledge_bases[space_id]

    async def build_knowledge_base(
        self, space_id: str, chunk_size: int = 500, chunk_overlap: int = 50
    ) -> KnowledgeBase:
        """构建指定的知识库"""
        kb = self.get_knowledge_base(space_id)
        await kb.build(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        save_path = os.path.join(self.storage_folder, space_id)
        kb.save(save_path)
        return kb

    def load_knowledge_base(self, space_id: str) -> KnowledgeBase:
        """加载已保存的知识库"""
        kb = self.get_knowledge_base(space_id)
        kb.load()
        return kb

    def list_knowledge_bases(self) -> List[Tuple[str, str]]:
        """列出所有可用的知识库，返回(space_id, description)元组列表"""
        kb_list = []

        for kb_dir in self.storage_folder.iterdir():
            if kb_dir.is_dir():
                space_id = kb_dir.name
                description = ""

                # 读取README.md文件
                readme_path = kb_dir / "README.md"
                try:
                    if readme_path.exists():
                        with open(readme_path, "r", encoding="utf-8") as f:
                            description = f.read().strip()
                except Exception as e:
                    logger.warning(
                        f"Failed to read description for {space_id}: {str(e)}"
                    )
                    description = f"Description unavailable for {space_id}"

                kb_list.append((space_id, description))

        return kb_list

    async def query(
        self,
        space_id: str,
        query: str,
        top_k: int = 5,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> List[Document]:
        """查询知识库（如果不存在则尝试加载）"""
        try:
            # 尝试加载已存在的知识库
            kb = self.load_knowledge_base(space_id)
        except FileNotFoundError:
            # 如果不存在，则构建新的知识库
            logger.info(
                f"Knowledge base not found, building new one for space: {space_id}"
            )
            kb = await self.build_knowledge_base(space_id, chunk_size, chunk_overlap)

        return await kb.query(query, top_k)

    def get_manager_info(self) -> Dict:
        """获取管理器信息"""
        kb_list = self.list_knowledge_bases()
        return {
            "storage_folder": str(self.storage_folder),
            "loaded_knowledge_bases": len(self.knowledge_bases),
            "available_knowledge_bases": [
                {"space_id": space_id, "description": desc}
                for space_id, desc in kb_list
            ],
        }

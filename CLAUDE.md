# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
**Taro** is an AI-powered research assistant that integrates DeepResearch capabilities into the Feishu (Lark) ecosystem. It combines LangChain, LangGraph, and Feishu APIs to provide intelligent document analysis and research capabilities.

- **Python Version**: >=3.13
- **Package Manager**: uv
- **Architecture**: Fully async, ReAct agent pattern with LangGraph

## Essential Commands

### Development & Testing
```bash
# Run tests
uv run pytest
uv run pytest tests/test_agent.py -v
uv run pytest tests/test_lark_sync.py -v

# Code quality
uv run ruff check
uv run ruff format
uv run mypy src/

# Single test function
uv run pytest tests/test_agent.py::test_function_name -v
```

### Running Components
```bash
# Main AI Agent (TaroLarkRunner)
uv run python -m src.agents.agent

# Feishu Wiki synchronization
uv run python -m src.core.lark_sync

# Knowledge base and RAG operations
uv run python -m src.core.rag
```

## Core Architecture

### Main Components
1. **TaroLarkRunner** (`src/agents/agent.py`): Main orchestrator class
   - Manages Feishu WebSocket connections and message handling
   - Implements ReAct pattern with LangGraph state management
   - Handles streaming responses with interrupt capability

2. **RAG System** (`src/core/rag.py`): 
   - `KnowledgeBase`: Individual RAG knowledge base per Feishu space
   - `LarkRAGManager`: Manages multiple knowledge bases
   - Uses FAISS for vector similarity search with DashScope embeddings

3. **Feishu Integration** (`src/core/lark_sync.py`):
   - `LarkSynchronizer`: Syncs Feishu Wiki content to local database
   - Handles document metadata and incremental updates

4. **Database Layer** (`src/core/db_client.py`):
   - `DatabaseClient`: Async SQLite operations
   - Tables: `docs_metadata`, `docs_content`

### Key Technologies
- **LangChain/LangGraph**: Core AI framework and state management
- **FAISS**: Vector similarity search for RAG
- **aiosqlite**: Async database operations
- **lark-oapi**: Feishu API integration (custom fork)
- **DashScope**: Qwen-Plus model and embeddings

### Configuration System
- Environment configs: `resources/configs/{dev,test,prod}.yaml`
- Main config: `conf.yaml` (model configuration)
- Database: `resources/db/dev.db`
- Knowledge bases: `resources/kb/[space_id]/`

### Important Implementation Details
- All I/O operations are async/await
- Document search tools support both specific space and cross-space search
- Streaming responses use Feishu card interface with interrupt handling
- Knowledge bases are built incrementally based on document timestamps
- Session management with thread persistence for chat continuity

## Known Issues
- Folder name typo: `src/utlis/` should be `src/utils/`
- Empty module: `src/core/embeds.py` appears unused
- Missing `__init__.py` files in some packages
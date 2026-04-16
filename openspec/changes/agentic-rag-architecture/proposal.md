## Why

当前 RAG 检索效果不够理想：仅支持简单的向量检索 + 重排序，无法处理复杂查询（如多跳推理、条件过滤、聚合分析）。引入 Agentic RAG 架构，通过 Agent 自主规划检索策略、调用工具、多轮迭代，显著提升复杂场景的检索精度和用户满意度。

## What Changes

- **新增 Agentic RAG 核心引擎**：基于 LangGraph 的状态机编排，支持查询理解、检索规划、工具调用、结果合成
- **新增检索工具集**：向量检索、关键词检索、元数据过滤、时间范围过滤、多路召回融合
- **新增查询路由**：基于意图识别，自动分发到简单检索或 Agentic RAG 路径
- **新增代码架构优化**：
  - 模块化重构：`rag/` 目录拆分为 `rag/core/`、`rag/tools/`、`rag/agents/`
  - 依赖注入：支持灵活切换 embedding 模型、向量库、重排序模型
  - 配置驱动：通过 YAML 配置 Agent 工具组合和检索策略
- **保留现有模块**：
  - 聊天记忆系统：独立模块，不属于检索，Agent 可通过工具调用
  - Small-to-Big 检索：作为基础检索策略保留（小块索引，大块返回）
- **删除旧代码**：`rag/rag_utils.py`，功能迁移到新架构

## Capabilities

### New Capabilities

- `query-router`: 查询意图识别和路由分发，判断使用简单检索还是 Agentic RAG
- `retrieval-tools`: 检索工具集，包括向量检索、BM25、元数据过滤、时间过滤、多路融合
- `agentic-rag`: Agentic RAG 核心引擎，基于 LangGraph 的状态机编排
- `modular-architecture`: 代码架构模块化重构，支持依赖注入和配置驱动
- `chat-memory-integration`: 聊天记忆系统集成，Agent 可通过工具调用获取对话上下文

**Note**: Small-to-Big 是基础检索策略，不是独立 capability

### Modified Capabilities

（无 - 现有 RAG 功能保持兼容，仅内部架构优化）

## Impact

- **新增依赖**：
  - `langgraph>=1.1.0`（Agent 状态机编排，独立包，需单独安装，2026 年 4 月最新 1.1.6）
  - `langchain` 已包含核心功能，但不包含 langgraph
- **架构调整**：
  - `rag/rag_utils.py` → 拆分为 `rag/core/`、`rag/tools/`、`rag/agents/`，旧文件删除
  - `app/api/routes.py` → 新增 `/api/test-query-agent` 端点
- **配置变更**：新增 `config/rag_config.yaml`，支持灵活配置 Agent 工具和策略
- **代码清理**：删除未使用的旧代码，保持代码库简洁

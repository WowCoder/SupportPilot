## 1. 创建新目录结构

- [x] 1.1 创建 `rag/offline/parsers/`、`rag/offline/steps/` 目录及 `__init__.py`
- [x] 1.2 创建 `rag/online/pipeline/nodes/` 目录及 `__init__.py`
- [x] 1.3 创建 `rag/online/retrievers/`、`rag/online/rerankers/`、`rag/online/generators/` 目录及 `__init__.py`
- [x] 1.4 创建 `rag/utils/` 目录及 `__init__.py`
- [x] 1.5 创建 `evaluation/test_cases/` 目录及 `__init__.py`
- [x] 1.6 创建 `tests/unit/` 目录及 `__init__.py`
- [x] 1.7 创建 `scripts/migrations/` 目录

**完成标准**: 所有新目录存在且含 `__init__.py`

## 2. 迁移 RAG 离线模块

- [x] 2.1 `rag/cleaning.py` → `rag/offline/cleaning.py`（git mv）
- [x] 2.2 `rag/parent_store.py` → `rag/offline/parent_store.py`（git mv）
- [x] 2.3 将 `rag/rag_utils.py` 离线部分拆分到 `rag/offline/`（chunking.py, embedding.py, indexing.py, pipeline.py）
- [x] 2.4 更新 `rag/offline/` 下所有内部 import

**完成标准**: 离线模块文件就位，内部引用正确

## 3. 迁移 RAG 在线模块 — pipeline/nodes

- [x] 3.1 `rag/agents/states.py` → `rag/online/pipeline/state.py`（git mv）
- [x] 3.2 `rag/agents/retrieval_agent.py` → `rag/online/pipeline/builder.py`（git mv）
- [x] 3.3 `rag/agents/nodes/*.py` → `rag/online/pipeline/nodes/*.py`（9 个文件，git mv）
- [x] 3.4 更新 pipeline 内所有内部 import

**完成标准**: LangGraph pipeline 文件就位，内部引用正确

## 4. 迁移 RAG 在线模块 — router

- [x] 4.1 `rag/agents/router.py` → `rag/online/router.py`（git mv）
- [x] 4.2 `rag/agents/router_classifier.py` → `rag/online/router_classifier.py`（git mv）
- [x] 4.3 `rag/agents/router_rules.py` → `rag/online/router_rules.py`（git mv）
- [x] 4.4 更新 router 文件内的 import

**完成标准**: Router 文件就位，内部引用正确

## 5. 迁移 RAG 在线模块 — retrievers/rerankers/generators

- [x] 5.1 `rag/tools/vector_tool.py` → `rag/online/retrievers/dense.py`（git mv）
- [x] 5.2 `rag/tools/bm25_tool.py` → `rag/online/retrievers/bm25.py`（git mv）
- [x] 5.3 `rag/tools/ensemble_tool.py` → `rag/online/retrievers/hybrid.py`（git mv）
- [x] 5.4 `rag/tools/filter_tool.py` → `rag/online/retrievers/filter_tool.py`（git mv）
- [x] 5.5 `rag/core/tool.py` → `rag/online/retrievers/base.py`（git mv）
- [x] 5.6 创建 `rag/online/rerankers/base.py` 和 `cross_encoder.py`
- [x] 5.7 创建 `rag/online/generators/base.py` 和 `llm_generator.py`

**完成标准**: 检索/重排/生成文件就位，内部引用正确

## 6. 迁移 RAG 在线模块 — service

- [x] 6.1 `rag/service.py` → `rag/online/service.py`（git mv），更新内部 import
- [x] 6.2 `rag/rag_utils.py` 检索部分整合入 `rag/online/retrievers/`

**完成标准**: `rag/online/service.py` 功能与旧版完全一致

## 7. 迁移 RAG utils

- [x] 7.1 `rag/core/config.py` → `rag/utils/config.py`（git mv）
- [x] 7.2 `rag/core/observability.py` → `rag/utils/observability.py`（git mv）
- [x] 7.3 `rag/core/container.py` → `rag/utils/container.py`（git mv）
- [x] 7.4 `rag/faq_vector_sync.py` → `rag/utils/faq_vector_sync.py`（git mv）

**完成标准**: utils 文件就位，内部引用正确

## 8. 合并 migrations 入 scripts/migrations/

- [x] 8.1 `migrations/*.py`（4 个文件）→ `scripts/migrations/*.py`（git mv）

**完成标准**: 所有迁移文件在 scripts/migrations/ 下

## 9. 提取 evaluation 模块

- [x] 9.1 `app/services/rag_evaluation.py` → `evaluation/rag_evaluation.py`（git mv）
- [x] 9.2 更新 evaluation/ 内 import，确保脱离 Flask 依赖
- [x] 9.3 创建 `evaluation/test_cases/cases.json`（或迁移现有测试数据）

**完成标准**: evaluation/ 模块可独立运行

## 10. 新增 retriever_service 封装 RAG 调用

- [x] 10.1 创建 `app/services/retriever_service.py`，封装对 `rag/online/service.py` 的调用
- [x] 10.2 更新 `app/api/` 中直接调用 `rag/service.py` 的路由，改为通过 `retriever_service` 调用

**完成标准**: app 层所有 RAG 调用统一走 retriever_service，query_rewriter 只做改写

## 11. 重组 tests/

- [x] 11.1 移动单元测试文件到 `tests/unit/`（git mv）：test_chat_memory.py, test_chunking.py, test_rag_tools.py, test_retrieval_agent.py, test_router.py, test_chroma_simple.py
- [x] 11.2 `tests/test_app.py` 和 `tests/test_integration.py` 保持在 tests/ 顶层

**完成标准**: tests/ 按 unit/ + playwright/ + 顶层划分完毕

## 12. 重命名 app/api/ 文件

- [x] 11.1 `app/api/chat_memory_routes.py` → `app/api/chat.py`（git mv）
- [x] 11.2 `app/api/ticket_routes.py` → `app/api/tickets.py`（git mv）
- [x] 11.3 `app/api/faq_routes.py` → `app/api/faq.py`（git mv）
- [x] 11.4 `app/api/rag_dashboard_routes.py` → `app/api/rag_dashboard.py`（git mv）

**完成标准**: api/ 下文件命名统一（无 `_routes` 后缀）

## 13. 更新所有 Python 文件 import 路径

- [x] 13.1 更新 `app/__init__.py` 蓝图 import（对应 api 文件重命名 + rag 路径）
- [x] 13.2 更新 `app/services/` 下所有文件的 RAG import
- [x] 13.3 更新 `app/api/` 下新文件的内部 import
- [x] 13.4 更新 `app/document/routes.py` 的 RAG import
- [x] 13.5 更新 `tests/` 下所有文件的 import（对应新路径）
- [x] 13.6 全量搜索 `from rag.agents`、`from rag.tools`、`from rag.core` 确认无残留引用

**完成标准**: 全局搜索无旧 import 路径

## 14. 删除旧目录

- [x] 14.1 删除 `rag/agents/`
- [x] 14.2 删除 `rag/tools/`
- [x] 14.3 删除 `rag/core/`
- [x] 14.4 删除 `migrations/`
- [x] 14.5 清理 `rag/rag_utils.py`、`rag/service.py` 等已迁移的顶层文件
- [x] 14.6 清理 `rag/README.md`（如内容过时）

**完成标准**: 旧目录/文件全部删除，无残留

## 15. 全量验证

- [x] 15.1 运行 `pytest` 全量测试，确认全部通过
- [x] 15.2 运行 `python -c "from app import create_app; app=create_app(); print('OK')"` 确认 Flask 启动成功
- [x] 15.3 使用 `bash start.sh` 启动开发服务器，验证首页可访问

**完成标准**: 全部测试通过，应用启动无错误

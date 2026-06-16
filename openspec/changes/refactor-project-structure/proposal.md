## Why

当前项目目录结构杂糅——RAG 核心逻辑散落在 `rag/agents/`、`rag/tools/`、`rag/core/` 三个不同粒度的目录中，离线文档处理和在线检索混在一起；`app/api/` 下路由文件命名不统一（`faq_routes.py` vs `chat_memory_routes.py`）；`tests/` 所有测试文件平铺；评估相关代码散落在 `app/services/`、`app/models/`、`app/api/` 三处。每次新增功能时开发者需要猜测代码应该放在哪里。现在一次性重组，建立清晰的模块边界和单向依赖流。

## What Changes

- **RAG 重组**: 按 **在线/离线** 拆分：`rag/offline/`（文档→索引）、`rag/online/`（查询→答案）、`rag/utils/`（通用）；将 `rag/agents/` 中 LangGraph 编排代码（state、builder、nodes）整合到 `rag/online/pipeline/`；删除旧目录 `rag/agents/`、`rag/tools/`、`rag/core/`
- **app/api/ 文件统一命名**: `chat_memory_routes.py` → `chat.py`，`ticket_routes.py` → `tickets.py`，`faq_routes.py` → `faq.py`，`rag_dashboard_routes.py` → `rag_dashboard.py`
- **app/models/ 保持**: 不改动（与 Flask-SQLAlchemy 绑定）
- **app/services/ 调整**: 新增 `retriever_service.py` 作为 RAG 调用统一入口，`query_rewriter.py` 保持专门做查询改写
- **evaluation/ 独立**: 将 `app/services/rag_evaluation.py` 移入 `evaluation/`，与 RAGAS 指标、测试用例集合同目录
- **tests/ 分层**: 按 `unit/` / `playwright/` 拆分，消除平铺
- **scripts/ 合并 migrations/**: `migrations/*.py` → `scripts/migrations/*.py`，未来其他运维脚本放 `scripts/` 顶层
- **llm/、config/、templates/、static/ 保持**: 位置不变
- 更新所有 import 路径，确保 `app → rag/online → llm` 单向依赖
- **BREAKING**: 所有 `from rag.agents...`、`from rag.tools...`、`from rag.core...` 的 import 路径将失效

## Capabilities

### New Capabilities

- `rag-offline-pipeline`: 文档解析、清洗、分块、向量化、索引入库的离线流水线
- `rag-online-pipeline`: 查询路由、多路检索、重排序、LLM 生成、LangGraph 自纠正的在线流水线
- `rag-utils`: RAG 配置加载、可观测性追踪、FAQ 向量同步
- `evaluation-module`: RAGAS 指标评估、测试用例管理、评估执行入口

### Modified Capabilities

<!-- No existing specs to modify -->

## Impact

- **所有 Python 文件**: import 路径全面更新（~50+ 文件）
- **`app/__init__.py`**: 蓝图 import 路径更新，对应 api 文件重命名
- **`app/api/`**: 4 个文件重命名，import 路径更新
- **`app/services/retriever_service.py`**: 新增，封装 RAG 调用，作为 app → rag/online 的唯一入口
- **`app/services/rag_evaluation.py`**: 移入 `evaluation/`
- **`rag/`**: agents/、tools/、core/ 删除，service.py / rag_utils.py 拆分迁移
- **`tests/`**: 移入 `unit/` + `playwright/` 子目录，import 路径更新
- **`migrations/`**: 整个目录合并入 `scripts/migrations/`

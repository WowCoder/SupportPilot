## Context

当前项目目录结构，完整如下（标注了各模块的问题）：

```
SupportPilot/
├── app/
│   ├── api/
│   │   ├── chat_memory_routes.py   # 命名不统一，与 tickets/faq 不一致
│   │   ├── ticket_routes.py        # 同上
│   │   ├── faq_routes.py           # 同上
│   │   ├── rag_dashboard_routes.py # 同上
│   │   └── routes.py
│   ├── services/
│   │   ├── rag_evaluation.py       # 评估逻辑混在 services 中
│   │   └── ...
│   ├── models/                     # OK
│   ├── auth/ / main/ / conversation/ / document/  # OK
│   └── ...
├── rag/
│   ├── agents/          # LangGraph 状态机节点 + router
│   ├── tools/           # 检索器 + 过滤器
│   ├── core/            # config, observability, tool 基类
│   ├── cleaning.py      # 离线（混在顶层）
│   ├── parent_store.py  # 离线（混在顶层）
│   ├── rag_utils.py     # 离线+在线混合（混在顶层）
│   ├── service.py       # 在线入口（混在顶层）
│   └── faq_vector_sync.py
├── tests/               # 所有测试平铺，无结构
├── migrations/          # 与 scripts/ 功能重叠
├── llm/                 # OK
├── config/              # OK
├── templates/           # OK
└── static/              # OK
```

目标结构：

```
SupportPilot/
├── app/
│   ├── api/
│   │   ├── chat.py / tickets.py / faq.py / rag_dashboard.py  # 统一命名
│   │   └── routes.py
│   ├── services/       # rag_evaluation.py 移出
│   ├── models/         # 不变
│   └── [auth/main/conversation/document]/  # 不变
├── rag/
│   ├── offline/        # 文档 → 索引
│   ├── online/         # 查询 → 答案（含 pipeline/、retrievers/、rerankers/、generators/）
│   └── utils/          # 跨模块通用工具
├── evaluation/         # 独立的评估模块
├── tests/
│   ├── unit/           # 单元测试
│   ├── playwright/     # E2E 测试
│   ├── test_app.py     # 应用级别测试
│   └── test_integration.py
├── scripts/            # 运维脚本
│   ├── migrations/      # 迁移脚本
│   └── ...              # 其他运维脚本
├── llm/ / config/ / templates/ / static/  # 不变
```

约束条件：
- 所有 LLM 调用必须走 `llm/llm_client.py`
- Flask 应用通过 `app/services/retriever_service.py` 调用 RAG（`rag/online/service.py`），`query_rewriter.py` 专门负责用对话历史改写查询
- 不能破坏现有的 ChromaDB 持久化数据路径
- 不能改变任何运行时行为（只是目录重组 + 文件重命名）

## Goals / Non-Goals

**Goals:**
- 建立 `app → rag/online → llm` 的单向依赖流
- 统一 `app/api/` 文件命名风格（去掉 `_routes` 后缀）
- 提取 `evaluation/` 为独立模块
- `tests/` 按 `unit/` / `playwright/` 分层
- 合并 `migrations/` 入 `scripts/migrations/`
- 删除 `rag/agents/`、`rag/tools/`、`rag/core/` 旧目录
- 所有 import 路径准确更新，`pytest` 全量通过

**Non-Goals:**
- 不修改任何业务逻辑或算法
- 不修改 RAG 配置参数
- 不修改数据库 schema
- 不修改 LLM provider 配置
- 不新增或删除功能

## Decisions

### 1. RAG 用 online/offline 切分

**选择**: `rag/offline/` + `rag/online/`（按处理阶段分）
**备选**: `rag/ingestion/` + `rag/retrieval/`（按技术手段分）
**理由**: "离线/在线"是 RAG 领域的标准术语，对 LLM 生成器的归属也比 ingestion/retrieval 更清晰。

### 2. 将 rag/agents/ 中 LangGraph 代码整合到 pipeline/

**选择**: `rag/online/pipeline/` 包含 state、builder、nodes/，代码全部来自 `rag/agents/`
**备选**: 保持 `rag/agents/` 目录不变
**理由**: `rag/agents/` 与 `rag/tools/`、`rag/core/` 的职责分界不清晰——router 和 retrieval_agent 放在 agents/，但检索工具在 tools/，基类在 core/。把它们全部按在线/离线重新分配后，`rag/agents/` 自然消失，pipeline/ 是 LangGraph 编排层的合理归宿。

### 3. retrievers/ + rerankers/ + generators/ 平级放在 online 下

**选择**: 三者平级在 `rag/online/` 下
**备选**: 合并为一个 `rag/online/components/` 目录
**理由**: 三者职责分明、文件数量足够（>3 个文件每个），扁平化更容易 import 和测试。

### 4. app/api/ 文件命名统一

**选择**: 去掉 `_routes` 后缀，文件名与功能名一致：`chat.py`、`tickets.py`、`faq.py`、`rag_dashboard.py`
**备选**: 保持现状
**理由**: 当前 `chat_memory_routes.py` 和 `ticket_routes.py` 命名风格不一致，统一去掉后缀后更简洁，功能一目了然。

### 5. evaluation/ 独立为顶层模块

**选择**: 将 `app/services/rag_evaluation.py` 移入 `evaluation/`，与 RAGAS 封装、测试用例同目录
**备选**: 保持在 `app/services/` 下
**理由**: 评估逻辑与业务服务不同——它不处理用户请求，只做质量度量。独立后可以脱离 Flask 运行，方便 CI/CD 集成。

### 6. tests/ 按类型分层

**选择**: `unit/`（单元测试）+ `playwright/`（E2E）+ 顶层保留 `test_app.py`、`test_integration.py`
**备选**: 平铺所有测试文件
**理由**: 时间增长后平铺测试文件会难以管理，按类型分层是 Python 项目标准实践。

### 7. models 保持在 app/ 下

**选择**: `app/models/`（不变）
**备选**: 抽到项目顶层
**理由**: 所有 model 绑定 Flask-SQLAlchemy，过度解耦无意义。

### 8. migrations 移入 scripts/migrations/

**选择**: `scripts/migrations/` 专门放迁移脚本，`scripts/` 顶层留给未来其他运维脚本
**备选**: 保持独立的 `migrations/` 顶层目录，或平铺到 `scripts/` 下
**理由**: 迁移脚本需要与其他运维脚本（如缓存清理、数据修复）区分开，独立的 `migrations/` 子目录表意清晰，也方便 CI 中按目录执行迁移。

### 9. 完整文件映射表

| 旧路径 | 新路径 |
|--------|--------|
| **app/api/** | |
| `app/api/chat_memory_routes.py` | `app/api/chat.py` |
| `app/api/ticket_routes.py` | `app/api/tickets.py` |
| `app/api/faq_routes.py` | `app/api/faq.py` |
| `app/api/rag_dashboard_routes.py` | `app/api/rag_dashboard.py` |
| **rag/ → rag/offline/** | |
| `rag/cleaning.py` | `rag/offline/cleaning.py` |
| `rag/parent_store.py` | `rag/offline/parent_store.py` |
| `rag/rag_utils.py` (离线部分) | 拆入 `rag/offline/pipeline.py`、`chunking.py`、`embedding.py`、`indexing.py` |
| **rag/ → rag/online/** | |
| `rag/service.py` | `rag/online/service.py` |
| `rag/agents/router.py` | `rag/online/router.py` |
| `rag/agents/router_classifier.py` | `rag/online/router_classifier.py` |
| `rag/agents/router_rules.py` | `rag/online/router_rules.py` |
| `rag/agents/states.py` | `rag/online/pipeline/state.py` |
| `rag/agents/retrieval_agent.py` | `rag/online/pipeline/builder.py` |
| `rag/agents/nodes/*.py` (9 files) | `rag/online/pipeline/nodes/*.py` |
| `rag/tools/vector_tool.py` | `rag/online/retrievers/dense.py` |
| `rag/tools/bm25_tool.py` | `rag/online/retrievers/bm25.py` |
| `rag/tools/ensemble_tool.py` | `rag/online/retrievers/hybrid.py` |
| `rag/tools/filter_tool.py` | `rag/online/retrievers/filter_tool.py` |
| `rag/core/tool.py` | `rag/online/retrievers/base.py` |
| **rag/ → rag/utils/** | |
| `rag/core/config.py` | `rag/utils/config.py` |
| `rag/core/observability.py` | `rag/utils/observability.py` |
| `rag/core/container.py` | `rag/utils/container.py` |
| `rag/faq_vector_sync.py` | `rag/utils/faq_vector_sync.py` |
| **evaluation/** | |
| `app/services/rag_evaluation.py` | `evaluation/rag_evaluation.py` |
| **tests/** | |
| `tests/test_chat_memory.py` | `tests/unit/test_chat_memory.py` |
| `tests/test_chunking.py` | `tests/unit/test_chunking.py` |
| `tests/test_rag_tools.py` | `tests/unit/test_rag_tools.py` |
| `tests/test_retrieval_agent.py` | `tests/unit/test_retrieval_agent.py` |
| `tests/test_router.py` | `tests/unit/test_router.py` |
| `tests/test_chroma_simple.py` | `tests/unit/test_chroma_simple.py` |
| `tests/playwright/test_rag_dashboard.py` | 不变 |
| `tests/test_app.py` | 不变 |
| `tests/test_integration.py` | 不变 |
| **migrations/ → scripts/** | |
| `migrations/*.py` (4 files) | `scripts/migrations/*.py` |

## Risks / Trade-offs

- **Import 路径遗漏** → 风险最大。缓解：全量 `pytest` + `python -c "from app import create_app"` 验证
- **git blame 断裂** → 缓解：使用 `git mv` 移动文件保留历史
- **蓝图注册名变更** → `app/api/` 文件重命名可能涉及蓝图 `import name` 变化。缓解：检查 `app/__init__.py` 中每个蓝图的注册代码
- **运行时 ChromaDB 路径** → 从 `rag/utils/config.py` 读取，路径不变，风险低
- **其他分支冲突** → 一次性重构，其他 PR 需 rebase

## Migration Plan

1. 创建所有新目录结构（不删除旧目录）
2. `git mv` 移动 rag/ 和 migrations/ 文件
3. 重命名 `app/api/` 文件
4. 移动 `app/services/rag_evaluation.py` → `evaluation/`
5. 移动 `tests/` 单元测试进 `unit/`
6. 批量更新所有文件的 import 路径
7. 更新 `app/__init__.py` 蓝图 import
8. `pytest` 全量 + Flask 启动验证
9. 删除旧目录
10. 提交

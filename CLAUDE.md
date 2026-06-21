## 项目概览

SupportPilot — Flask + Vue 3 前后端分离的智能客服系统。后端纯 API 服务（JWT 认证），前端 Vue 3 SPA（Vite + Element Plus + Pinia + Vue Router）。RAG 引擎基于 LangGraph 9 节点状态机（内建 self-correction），检索支持向量搜索、BM25、RRF 融合。LLM 通过 `llm/llm_client.py` 统一调用，支持多 provider。

## 目录地图

```
app/              Flask API 应用（纯 JSON，无 SSR/模板）
  api/              API 蓝图（auth、chat、faq、tickets、rag_dashboard、routes）
  api/v1/           RESTful v1 API（chat、faq、documents — JWT 认证 + 统一响应格式）
  services/         业务逻辑层
  models/           数据模型（User、Conversation、Message、FAQEntry、Document 等）
  utils/            工具函数（jwt、auth、response、sanitize）
frontend/         Vue 3 SPA 前端
  src/api/          Axios 封装 + API 调用（auth、chat、faq、document、rag）
  src/router/       Vue Router（History 模式 + 导航守卫 + 角色感知重定向）
  src/stores/       Pinia 状态管理（auth、chat）
  src/views/        页面组件（Login、Register、ChatLayout、FaqManage、DocumentUpload、TechDashboard、RagDashboard、UserDashboard）
  src/components/   公共组件（layout/AppTopnav、chat/SessionList/MessageBubble/ChatInput、common/MarkdownRenderer）
  src/composables/  组合式函数（useSSE）
rag/              RAG 核心
  offline/          离线管道（文档→索引：cleaning、chunking、embedding、indexing、pipeline）
  online/           在线管道（查询→答案：pipeline/nodes/、retrievers/、rerankers/、generators/、router、service）
  utils/            通用工具（config、observability、container、faq_vector_sync）
llm/              LLM 客户端（多 provider）
evaluation/       评估模块（RAGAS 指标、测试用例）
config/           rag_config.yaml（RAG 行为）、llm_config.yaml（LLM provider）、nginx.conf（生产部署）
scripts/          运维脚本
  migrations/       数据迁移脚本
```

## 常用命令

```bash
# 后端
bash start.sh -f                         # Flask + Vite 同时启动（开发推荐）
python -m flask --app wsgi:app run --debug --port 5050  # 仅启动 Flask

# 前端
cd frontend && npm run dev                # Vite 开发服务器（HMR，自动 Proxy API 到 5050）
cd frontend && npm run build              # 生产构建

# 测试
pytest tests/test_app.py tests/unit/ tests/test_integration.py   # 全量测试（排除 playwright）
pytest tests/unit/xxx.py                 # 单个测试文件
flake8 .                                  # 代码风格
python scripts/run_smoke_eval.py         # RAGAS smoke test（6 case × 4 指标，约 20-25 分钟）
```

## 架构约定

- **后端是纯 API 服务**：不再渲染 HTML，所有端点返回 JSON。页面渲染由 Vue SPA 接管。
- **JWT 认证**：替代 Flask-Login Session。`@jwt_required` 装饰器从 `Authorization: Bearer <token>` 头提取验证，注入 `g.current_user`。Token 由 `app/utils/jwt.py` 生成和验证。
- **统一响应格式**：`{ "code": <http_status>, "data": <payload>, "message": "<description>" }`，使用 `app/utils/response.py` 的 `api_success()` / `api_error()` / `api_paginated()` helper。
- **新旧 API 共存**：`/api/` 和 `/api/v1/` 两个前缀并存，v1 使用 JWT + 统一格式，旧 `/api/` 端点已切换至 JWT。
- **业务逻辑放 service 层**：新增接口 `app/api/v1/<模块>.py` → `app/services/<模块>_service.py`
- **新蓝图在 `app/__init__.py` 的 `create_app()` 中注册**
- **所有 LLM 调用必须走 `llm/llm_client.py`**（全局 `llm_client`），禁止直接调 provider API
- **配置分两套**：`app/config.py`（Flask 应用 + `.env`）和 `config/rag_config.yaml`（RAG 行为），不要混用
- **Chat memory 和 RAG 是独立系统**：唯一连接点是 `app/services/query_rewriter.py`（用对话上下文改写查询后传给 RAG）
- **RAG 管线**：`rag/offline/pipeline.py` 的 `RAGUtils.process_document()` 负责文档 ingestion（解析→清洗→分块→质量过滤→索引）；`rag/online/service.py` 是 RAG 编排层。文档上传通过 `app/api/v1/documents.py` 调用。
- **临时文件**：一律输出到 `tmp/` 目录，已加入 `.gitignore`

## 前端约定

- **路由守卫**：`beforeEach` 处理认证（未登录→login）、角色重定向（tech_support 访问 /chat → /tech-dashboard）、权限检查（普通用户→tech 页面被拒绝）
- **API 封装**：`frontend/src/api/index.js` 是 Axios 实例，配置了请求拦截器（自动附加 JWT）和响应拦截器（401 自动刷新 Token，刷新失败跳转登录）
- **新增页面**：创建 `src/views/Xxx.vue` → 创建 `src/api/xxx.js` → 在 `src/router/index.js` 注册路由 → 在 `AppTopnav.vue` 添加导航链接（如需要）
- **Element Plus**：全局注册，中文语言包。表单验证用 `el-form` rules，消息提示用 `ElMessage`，确认弹窗用 `ElMessageBox.confirm`

## 修改后验证

- **每次修改 Python 代码后** → `flake8 .`
- **修改 RAG 检索逻辑** → `pytest tests/unit/test_rag_tools.py tests/unit/test_retrieval_agent.py`
- **修改路由/API** → `python -c "from app import create_app; app=create_app(); print('OK')"`
- **修改前端组件** → `cd frontend && npm run build`
- **修改 RAG/检索/LLM 调用链** → `python scripts/run_smoke_eval.py`（规则详见 `.claude/rules/rag-eval.md`）
- **任务完成** → `pytest tests/test_app.py tests/unit/ tests/test_integration.py` + `flake8 .` + `npm run build`

## 注意事项

- 虚拟环境：`venv/`（Python 3.11.11），所有命令都需在 `source venv/bin/activate` 后运行
- 用 `bash start.sh -f` 同时启动前后端开发服务器。单独启动后端：`python -m flask --app wsgi:app run --debug --port 5050`
- **macOS 端口冲突**：5000 端口被 AirPlay 占用，后端默认使用 5050 端口
- Agent 保护参数（3 轮迭代 / 30s 超时 / 2 次纠正）不要随意调高，会直接增加 LLM 调用费用
- ChromaDB 数据文件式持久化在 `instance/chroma_db/`，不可随意删除
- 默认 SQLite，生产切 PostgreSQL 需要数据迁移，不是改连接串就行
- **默认测试账号**：`tech_support / tech123`（启动时自动创建/重置）
- 前端默认 History 模式，Nginx 需配置 `try_files $uri /index.html`（`config/nginx.conf` 已提供）

### 页面验证（Playwright）→ 规则详见 `.claude/rules/playwright.md`

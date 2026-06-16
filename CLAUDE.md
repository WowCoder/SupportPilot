## 项目概览

SupportPilot — Flask + Jinja2 服务端渲染的智能客服系统。RAG 引擎基于 LangGraph 9 节点状态机（内建 self-correction），检索支持向量搜索、BM25、RRF 融合。LLM 通过 `llm/llm_client.py` 统一调用，支持多 provider。

## 目录地图

```
app/          Flask 应用（工厂模式、蓝图、models、services）
rag/          RAG 核心
  offline/      离线管道（文档→索引：cleaning、chunking、embedding、indexing、pipeline）
  online/       在线管道（查询→答案：pipeline/nodes/、retrievers/、rerankers/、generators/、router、service）
  utils/        通用工具（config、observability、container、faq_vector_sync）
llm/          LLM 客户端
evaluation/   评估模块（RAGAS 指标、测试用例）
templates/    Jinja2 模板
static/       CSS
config/       rag_config.yaml（RAG 行为）、llm_config.yaml（LLM provider）
scripts/      运维脚本
  migrations/   数据迁移脚本
```

## 常用命令

```bash
bash start.sh                           # 启动开发服务器（默认 5000 端口，macOS 会冲突）
python -m flask --app wsgi:app run --debug --port 5050  # 手动启动，换端口
pytest tests/test_app.py tests/unit/ tests/test_integration.py   # 全量测试（排除 playwright）
pytest tests/unit/xxx.py               # 单个测试文件
```

## 代码规范

- 业务逻辑放 service 层，路由只做参数校验。新增接口：`app/<模块>/routes.py` → `app/services/<模块>_service.py`
- 新蓝图在 `app/__init__.py` 的 `create_app()` 中注册
- 所有 LLM 调用必须走 `llm/llm_client.py`（全局 `llm_client`），禁止直接调 provider API
- API 蓝图默认 exempt CSRF（在 `create_app()` 中统一处理），页面路由默认受保护
- 配置分两套：`app/config.py`（Flask 应用 + `.env`）和 `config/rag_config.yaml`（RAG 行为），不要混用
- Chat memory 和 RAG 是独立系统，唯一连接点是 `app/services/query_rewriter.py`（用对话上下文改写查询后传给 RAG）
- `rag/offline/pipeline.py` 的 `rag_utils` 负责文档 ingestion 和检索；`rag/online/retrievers/` 是原子检索工具；`rag/online/service.py` 是 RAG 编排层。app 层通过 `app/services/retriever_service.py` 统一调用 RAG

## 标准工作流

### 任务启动：先判断，再行动

- 复杂任务不要直接开始写代码。先判断：是否需要前置调查？是否缺少用户提供的关键信息？验证标准是什么？
- 确认理解无误后，用 `opsx:propose` 生成 spec，以 SDD（Spec-Driven Development）方式驱动开发。

### 任务执行：分阶段交付

- opsx 生成的任务不要写成 checklist，要按 **checkpoint** 组织：每个阶段有明确的完成条件、交付物、禁区（不可触碰的模块/文件）。
- 每个 checkpoint 完成后，提交一次代码，然后 `/clear` 重置上下文，再进入下一阶段。
- 这避免上下文膨胀导致后续阶段质量下降。

### 修改后验证

- 修改 RAG 检索逻辑 → `pytest tests/unit/test_rag_tools.py tests/unit/test_retrieval_agent.py`
- 修改路由/API → 检查 `app/__init__.py` 中蓝图注册和 CSRF 豁免
- 任务完成 → `pytest tests/test_app.py tests/unit/ tests/test_integration.py` + `python -c "from app import create_app; app=create_app(); print('OK')"`

## 注意事项

- 虚拟环境：`venv/`（Python 3.11.11），所有命令都需在 `source venv/bin/activate` 后运行
- 用 `bash start.sh` 启动：自动激活 venv、检查 `.env`、创建 `logs/`，生产模式自动切 Gunicorn。`ORT_DISABLE_COREML=1` 在 `wsgi.py` 顶部设置，无需手动处理
- **macOS 端口冲突**：5000 端口被 AirPlay 占用，需要换端口（如 5050）：`python -m flask --app wsgi:app run --debug --port 5050`
- Agent 保护参数（3 轮迭代 / 30s 超时 / 2 次纠正）不要随意调高，会直接增加 LLM 调用费用
- ChromaDB 数据文件式持久化在 `instance/chroma_db/`，不可随意删除
- 默认 SQLite，生产切 PostgreSQL 需要数据迁移，不是改连接串就行

### 页面验证（Playwright）

```bash
# 查看页面标题 + 文本内容
node scripts/page-check.js http://localhost:5050/login --text

# 截图
node scripts/page-check.js http://localhost:5050/login --screenshot /tmp/page.png

# 查看标题
node scripts/page-check.js http://localhost:5050/rag-dashboard --title
```

首次使用前需安装依赖：`npm install`。
Playwright 浏览器版本与 npm 包版本绑定，如报 "Executable doesn't exist" 需重新安装浏览器：

```bash
npx playwright install chromium
```

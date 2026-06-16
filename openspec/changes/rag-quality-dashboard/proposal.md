## Why

当前 RAG 检索是黑盒——检索了哪些 chunk、相似度多少、用户是否满意，全不可见。调优只能凭感觉在测试页手动搜索。需要一个统一的质量 Dashboard，把用户反馈、检索过程、LLM 自动评估三个维度可视化，让调优有数据依据。

## What Changes

- 新增用户反馈系统：AI 回复下方增加 👍👎 按钮，用户点击后记录问题、检索来源、反馈类型到数据库
- 新增检索日志模块：每次 RAG 检索完整记录（查询、检索结果、相似度分、耗时、路由方式、使用的 chunk 内容），持久化到 SQLite
- 新增 LLM-as-Judge 自动打分：对每次检索结果用 LLM 评估相关性和完整性，给出 1-5 分
- 新增 `/rag-dashboard` 页面（仅技术支持可访问）：展示反馈统计、检索日志列表、每次检索的完整过程（含 LLM-as-Judge 评分和高亮）、Top-N 低质量查询
- 新增 API 端点：`/api/feedback`（提交反馈）、`/api/rag-logs`（查询检索日志）、`/api/rag-logs/<id>/judge`（触发 LLM-as-Judge 评估）

## Capabilities

### New Capabilities
- `user-feedback`: 用户在对 AI 回复的点赞/点踩功能，记录到数据库，包含问题、检索来源、反馈类型
- `rag-retrieval-log`: 每次 RAG 检索的完整过程日志（查询、结果、分数、耗时、路由），持久化存储
- `llm-judge`: LLM 自动对检索结果打分（1-5 分），评估相关性和完整性，判断是否有无关文档混入
- `rag-dashboard-page`: 技术支持专用的质量 Dashboard 页面，展示反馈统计、检索日志列表、完整检索过程可视化、LLM-as-Judge 评分
- `rag-dashboard-api`: 反馈提交、日志查询、LLM-Judge 评分的 API 端点

### Modified Capabilities
- `chat-layout`: 会话页面 SHALL 在每条 AI 回复下方显示 👍👎 反馈按钮，用户点击后异步提交反馈

## Impact

- **新增文件**: `app/models/rag_log.py`（检索日志 + 用户反馈模型）、`app/services/rag_evaluation.py`（LLM-as-Judge 逻辑）、`app/main/rag_dashboard.py`（Dashboard 路由）、`templates/rag_dashboard.html`（Dashboard 页面）
- **修改文件**: `rag/service.py`（增加检索日志记录）、`templates/conversation.html`（增加 👍👎 按钮）、`config/rag_config.yaml`（LLM-as-Judge 配置）
- **新增依赖**: 无（LLM-as-Judge 复用现有 `llm_client`）
- **数据库**: 新增 `rag_retrieval_logs` 和 `user_feedback` 两张表，SQLite 无需迁移工具

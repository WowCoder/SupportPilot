## 1. 数据模型

- [x] 1.1 创建 `RagRetrievalLog` 模型（`app/models/rag_log.py`）：包含 query、result_count、top1_similarity、duration_ms、route_type、results_json、judge_score、judge_reason、created_at
- [x] 1.2 创建 `UserFeedback` 模型（同文件）：包含 conversation_id、message_id、user_id、type、retrieval_log_id、created_at
- [x] 1.3 在 `app/models/__init__.py` 注册新模型，通过 `db.create_all()` 自动建表

## 2. 检索日志自动记录

- [x] 2.1 修改 `rag/service.py` 的 `retrieve()` 方法：在返回结果前自动记录检索日志到 `RagRetrievalLog`
- [x] 2.2 在日志中存储完整 results_json、耗时统计（time.time() 差值）、route_type（agentic/simple）
- [x] 2.3 将日志 ID 注入返回结果（`results[i]['log_id']`），方便后续反馈关联

## 3. LLM-as-Judge

- [x] 3.1 创建 `app/services/rag_evaluation.py`，实现 `judge_retrieval(query, results)` 方法
- [x] 3.2 设计 Judge prompt：要求 LLM 从 relevance/completeness/noise 三维度评分（1-5 分），返回 JSON，附带一句话理由
- [x] 3.3 复用现有 `llm_client` 发送 Judge 请求，容错处理 LLM 返回格式异常（返回 `judge_score=null` 不抛异常）

## 4. API 端点

- [x] 4.1 `POST /api/feedback`：接受 JSON `{message_id, conversation_id, type}`，创建或更新反馈记录，关联最近的检索日志
- [x] 4.2 `GET /api/rag-logs`：分页查询检索日志，支持 `route_type`、`min_similarity`、`search` 筛选，返回 items + pagination + stats
- [x] 4.3 `GET /api/rag-logs/<id>`：单条日志详情，包含完整 results_json 和关联的 UserFeedback
- [x] 4.4 `POST /api/rag-logs/<id>/judge`：异步触发 LLM-as-Judge 评估，返回评分结果
- [x] 4.5 `GET /api/rag-logs/stats`：Dashboard 统计（总检索、平均相似度、平均 judge 分、正反馈率、今日检索数）

## 5. Dashboard 页面

- [x] 5.1 创建 `templates/rag_dashboard.html`：topnav + page-content 布局，顶部 4 个统计卡片，主区域为 data-table 日志列表
- [x] 5.2 日志列表每行显示：查询文本（截断）、结果数、top-1 相似度（颜色区分红/橙/绿）、Judge 均分、耗时、时间，低质量行红色左边框高亮
- [x] 5.3 点击日志行展开详情：查询全文、路由方式、每条检索结果（完整内容 + 相似度分 + 来源文件）、LLM-Judge 三维评分（颜色条 + 理由）+ "重新评分" 按钮、关联的用户反馈（👍👎）
- [x] 5.4 添加筛选器：路由方式 dropdown（全部/agentic/simple）、最低相似度 input、搜索框
- [x] 5.5 创建 `/rag-dashboard` 路由（`app/main/routes.py`）：权限检查 `tech_support` only，渲染模板
- [x] 5.6 topnav 导航链接中添加 Dashboard 入口（仅 tech_support 可见）

## 6. 会话页反馈按钮

- [x] 6.1 修改 `templates/conversation.html`：在每条 AI 消息下方添加 👍👎 按钮
- [x] 6.2 实现按钮 JS：点击提交 `/api/feedback`、选中高亮、切换状态、已关闭会话不显示
- [x] 6.3 按钮样式使用 `btn-ghost btn-xs`，选中状态用 accent（👍）或 danger（👎）颜色

## 7. Playwright 自动化页面验证

- [x] 7.1 编写 `tests/playwright/test_rag_dashboard.py`：使用 Python Playwright 脚本自动化验证所有核心页面行为
- [x] 7.2 验证 Dashboard 页面加载：以 tech_support 登录 → 访问 `/rag-dashboard` → 断言 `.stat-card` 数量 >= 4 → 断言 `.data-table` 存在 → 截图保存 `docs/screenshots/rag-dashboard.png`
- [x] 7.3 验证权限控制：以 testuser 登录 → 访问 `/rag-dashboard` → 断言被重定向到首页（URL 不含 `/rag-dashboard`）→ 断言 flash message 包含权限提示
- [x] 7.4 验证反馈按钮：以 testuser 登录 → 访问会话页 → 断言 AI 消息下方存在 👍👎 按钮 → 点击 👍 → 断言按钮样式变为激活状态 → 点击 👎 → 断言 👍 取消 👎 激活 → 截图保存
- [x] 7.5 验证 API 响应：POST `/api/feedback` → 断言返回 `success: True` → GET `/api/rag-logs` → 断言返回含 `items` + `pagination` + `stats` → POST `/api/rag-logs/1/judge` → 断言返回 `judge_score`
- [x] 7.6 验证日志展开：Dashboard 页点击第一条日志 → 断言展开详情面板可见 → 断言显示检索结果内容 + 相似度分数 → 截图保存
- [x] 7.7 验证数据库记录：检索后断言 `rag_retrieval_logs` 表有新记录 → 反馈后断言 `user_feedback` 表有新记录

## 8. 手动验证

- [ ] 8.1 用 testuser 发消息 → 确认 AI 回复下方出现 👍👎 按钮
- [ ] 8.2 用 tech_support 访问 `/rag-dashboard` → 确认统计卡片、日志列表正常加载 → 展开一条日志验证详情展示
- [ ] 8.3 对一条日志触发 LLM-as-Judge → 确认评分写入 → 确认分数和理由在 Dashboard 展示

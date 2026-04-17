## 1. 数据库迁移

- [x] 1.1 创建工单表 `support_tickets` (id, session_id, status, round_count, created_at, closed_at, closed_by)
- [x] 1.2 创建 FAQ 条目表 `faq_entries` (id, question, answer, category, status, vector_ids, created_by, confirmed_by, created_at)
- [x] 1.3 创建 FAQ 版本历史表 `faq_versions` (id, faq_id, question, answer, change_reason, changed_by, created_at)
- [x] 1.4 在 `chat_memory` 表中添加 `ticket_status` 和 `round_count` 字段

## 2. 后端核心服务

- [x] 2.1 实现对话轮次计数服务（`app/services/round_counter.py`）
- [x] 2.2 实现工单状态管理服务（`app/services/ticket_service.py`）
- [x] 2.3 实现 FAQ 审核工作流服务（`app/services/faq_review_service.py`）
- [x] 2.4 实现 FAQ 管理服务（`app/services/faq_management_service.py`）
- [x] 2.5 实现向量数据库同步工具（`rag/faq_vector_sync.py`）

## 3. 后端 API 路由

- [x] 3.1 添加人工介入 API (`POST /api/ticket/{session_id}/handoff`)
- [x] 3.2 添加关闭工单 API (`POST /api/ticket/{session_id}/close`)
- [x] 3.3 添加获取工单状态 API (`GET /api/ticket/{session_id}/status`)
- [x] 3.4 添加 FAQ 生成 API (`POST /api/faq/generate`)
- [x] 3.5 添加 FAQ 确认 API (`POST /api/faq/{id}/confirm`)
- [x] 3.6 添加 FAQ 列表 API (`GET /api/faq`)
- [x] 3.7 添加 FAQ 新增 API (`POST /api/faq`)
- [x] 3.8 添加 FAQ 编辑 API (`PUT /api/faq/{id}`)
- [x] 3.9 添加 FAQ 删除 API (`DELETE /api/faq/{id}`)

## 4. 前端聊天界面

- [x] 4.1 在聊天界面添加对话轮次显示
- [x] 4.2 实现人工介入按钮（3 轮后显示）
- [x] 4.3 实现关闭工单按钮和确认对话框
- [x] 4.4 实现工单状态提示（待人工处理/已关闭）
- [x] 4.5 实现关单时 FAQ 生成选项弹窗

## 5. FAQ 审核界面

- [x] 5.1 创建 FAQ 草稿审核弹窗组件（在 conversation.html 关闭模态框中）
- [x] 5.2 实现 AI 生成的 FAQ 草稿展示（可编辑）
- [x] 5.3 实现"确认并添加"按钮逻辑
- [x] 5.4 实现"拒绝"按钮逻辑
- [x] 5.5 实现向量化进度提示

## 6. FAQ 管理后台

- [x] 6.1 创建 FAQ 管理页面 (`/faq/manage`)
- [x] 6.2 实现 FAQ 列表展示（表格形式）
- [x] 6.3 实现搜索和筛选功能
- [x] 6.4 实现新增 FAQ 对话框
- [x] 6.5 实现编辑 FAQ 对话框
- [x] 6.6 实现删除确认对话框
- [x] 6.7 实现批量删除功能
- [x] 6.8 实现 FAQ 版本历史查看

## 7. 集成测试

- [ ] 7.1 测试对话轮次计数准确性
- [ ] 7.2 测试人工介入触发逻辑
- [ ] 7.3 测试工单关闭流程
- [ ] 7.4 测试 FAQ 生成→审核→向量化全流程
- [ ] 7.5 测试 FAQ 增删改的向量同步
- [ ] 7.6 测试 RAG 检索能否正确检索到 FAQ

## 8. 文档与配置

- [x] 8.1 更新 CLAUDE.md 添加新功能说明
- [x] 8.2 在 `app/config.py` 中添加配置项（人工介入轮次阈值、窗口大小等）
- [ ] 8.3 编写 API 文档（README 或 OpenAPI spec）

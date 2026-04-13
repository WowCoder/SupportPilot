## 1. 数据库模型层

- [x] 1.1 创建 `ChatMemory` 数据模型（`app/models/chat_memory.py`）
- [x] 1.2 创建 `FAQEntry` 数据模型（`app/models/faq_entry.py`）
- [x] 1.3 在 `app/models/__init__.py` 中注册新模型
- [x] 1.4 创建数据库迁移脚本，创建 `chat_memory` 和 `faq_entries` 表

## 2. 服务层实现

- [x] 2.1 实现 `ChatMemoryService` 核心服务类（`app/services/chat_memory_service.py`）
- [x] 2.2 实现窗口管理方法：`get_window(session_id, limit=5)`, `add_record(session_id, content)`
- [x] 2.3 实现待压缩队列方法：`mark_for_compression(record_id)`, `get_pending_compression(session_id)`
- [x] 2.4 实现批量压缩方法：`compress_batch(session_id, batch_size=5)` - 批量调用 LLM
- [x] 2.5 实现异步任务调度：`schedule_compression_if_idle(session_id, delay=30s)`
- [x] 2.6 实现 `CompressionQueue` 队列管理类（持久化 + 恢复）
- [x] 2.7 实现 `QueryRewriter` 服务类（`app/services/query_rewriter.py`）
- [x] 2.8 实现 Query Rewrite 方法：`rewrite_query(query, session_id, window_size=5)`
- [x] 2.9 实现 `FAQGenerator` 服务类（`app/services/faq_generator.py`）
- [x] 2.10 实现 FAQ 生成方法：`generate_from_session(session_id)`
- [x] 2.11 实现 FAQ 去重方法：`check_similarity(question, threshold=0.9)`
- [x] 2.12 实现 FAQ 入库方法：`save_faq(question, answer, source_session_id)`

## 3. API 路由层

- [x] 3.1 创建 `app/api/chat_memory_routes.py` 路由文件
- [x] 3.2 实现 `GET /api/chat-memory/<session_id>/window` 端点
- [x] 3.3 实现 `GET /api/chat-memory/<session_id>/summary` 端点
- [x] 3.4 实现 `POST /api/faq/generate` 端点（关单生成）
- [x] 3.5 实现 `POST /api/faq/search` 端点（向量检索）
- [x] 3.6 在 `app/__init__.py` 中注册新路由

## 4. 前端集成

- [x] 4.1 修改关单弹窗，添加"生成 FAQ"复选框
- [x] 4.2 实现 FAQ 生成结果展示 UI（flash message）
- [x] 4.3 添加 FAQ 检索测试界面（可选）（通过 API `/api/faq/search`）

## 5. 配置与集成

- [x] 5.1 在 `app/config.py` 中添加配置项：
  - `CHAT_MEMORY_WINDOW_SIZE = 5`
  - `CHAT_MEMORY_COMPRESSION_BATCH_SIZE = 5`
  - `CHAT_MEMORY_IDLE_THRESHOLD_SECONDS = 30`
  - `CHAT_MEMORY_COMPRESSION_MAX_DELAY_SECONDS = 120`
  - `CHAT_MEMORY_COMPRESSION_QUEUE_MAX = 10`
  - `CHAT_MEMORY_QUERY_REWRITE_ENABLED = True`
  - `CHAT_MEMORY_QUERY_REWRITE_TIMEOUT_SECONDS = 5`
  - `FAQ_SIMILARITY_THRESHOLD = 0.9`
  - `SUMMARY_COMPRESSION_RATIO_TARGET = 10`

## 6. 测试与验证

- [x] 6.1 编写窗口管理单元测试（17 个测试全部通过）
- [x] 6.2 编写批量压缩单元测试
- [x] 6.3 编写异步队列持久化测试
- [x] 6.4 编写 Query Rewrite 单元测试
- [x] 6.5 编写 FAQ 生成集成测试
- [x] 6.6 手动测试完整流程：关单 → 生成 FAQ → 检索验证
- [x] 6.7 验证批量压缩触发逻辑（5 条或空闲 30 秒或 2 分钟兜底）

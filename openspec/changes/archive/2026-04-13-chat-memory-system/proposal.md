## Why

当前客服系统与 LLM 交互时，完整聊天记录会迅速消耗 token 预算，导致长对话场景无法使用。同时，关单后的会话数据未被利用，缺少从历史对话中沉淀 FAQ 到向量数据库的正向循环机制。

## What Changes

- **短期记忆窗口**：保留最近 N 条（默认 5 条）完整聊天记录，确保 LLM 获取最新上下文
- **批量异步压缩**：超出窗口的记录先标记，累积 3-5 条后批量调用 LLM 压缩
- **关单总结选项**：关单时可选择是否调用 LLM 生成会话总结
- **关单总结选项**：关单时可选择是否调用 LLM 生成会话总结
- **FAQ 自动生成**：从关单总结中提取 Q&A 对，录入向量数据库供 RAG 检索使用
- **记忆存储结构**：新增 `chat_memory` 数据表，支持窗口查询和摘要检索

## Capabilities

### New Capabilities
- `chat-memory-window`: 短期记忆窗口管理，保留最近 N 条完整记录（默认 5 条，可配置）
- `chat-memory-summary`: 批量异步压缩机制，累积多条待压缩记录后批量生成摘要
- `chat-memory-faq`: 关单后生成 FAQ 并录入向量数据库
- `query-rewrite`: Query Rewrite 机制，检索前改写用户 query 融入对话历史

### Modified Capabilities
- ``

## Impact

- **新增文件**：`app/models/chat_memory.py`, `app/services/chat_memory_service.py`, `app/services/faq_generator.py`
- **数据库变更**：新增 `chat_memory` 表，新增 `faq_entries` 表
- **API 变更**：新增 `/api/chat-memory/*` 端点，新增 `/api/faq/generate` 端点
- **依赖**：需要现有的 RAG 向量数据库基础设施

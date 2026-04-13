## ADDED Requirements

### Requirement: 关单后可选生成 FAQ
系统应在关单时提供选项，允许用户选择是否调用 LLM 生成会话总结并提取 FAQ。

#### Scenario: 关单时选择生成 FAQ
- **WHEN** 技术支持关单时勾选"生成 FAQ"选项
- **THEN** 系统调用 LLM 生成会话总结并提取 Q&A 对

#### Scenario: 关单时不生成 FAQ
- **WHEN** 技术支持关单时未勾选"生成 FAQ"选项
- **THEN** 系统正常关单，不生成 FAQ

#### Scenario: FAQ 生成失败处理
- **WHEN** LLM 调用失败或无法提取有效 Q&A
- **THEN** 关单流程不受影响，FAQ 生成加入重试队列

### Requirement: FAQ 入库前去重
系统应在 FAQ 录入向量数据库前进行相似度去重，避免重复知识污染。

#### Scenario: 检测相似 FAQ
- **WHEN** 新生成的 FAQ 与现有 FAQ 相似度超过 0.9
- **THEN** 系统跳过入库，并提示用户已存在相似 FAQ

#### Scenario: 新 FAQ 成功入库
- **WHEN** 新生成的 FAQ 与现有 FAQ 相似度低于 0.9
- **THEN** 系统将 FAQ 作为新文档录入向量数据库

### Requirement: FAQ 向量检索接口
系统应提供 REST API 端点，支持从 FAQ 向量库中检索相关问题。

#### Scenario: 成功检索 FAQ
- **WHEN** 客户端发送 `POST /api/faq/search` 请求，包含查询文本
- **THEN** 系统返回语义最相关的 Top-N 条 FAQ

#### Scenario: 无匹配 FAQ
- **WHEN** 查询文本与所有 FAQ 相似度低于阈值
- **THEN** 系统返回空列表

### Requirement: FAQ 数据结构
系统应定义 FAQ 的数据结构，包含问题、答案、来源会话 ID、创建时间等字段。

#### Scenario: FAQ 数据完整性
- **WHEN** FAQ 入库时
- **THEN** 必须包含字段：question, answer, source_session_id, created_at

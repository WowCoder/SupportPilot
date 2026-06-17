## ADDED Requirements

### Requirement: FAQ 审核工作流

技术支持关闭工单时，系统应提供 FAQ 生成选项，生成的 FAQ 需经技术支持审核确认后才向量化到知识库。

#### Scenario: 技术支持选择生成 FAQ
- **WHEN** 技术支持关闭工单时勾选"生成 FAQ"选项
- **THEN** 系统调用 AI 生成 FAQ 草稿，包含问题和答案

#### Scenario: 技术支持编辑 FAQ 草稿
- **WHEN** FAQ 草稿展示给技术支持
- **THEN** 技术支持可修改问题和答案内容，预览向量化效果

#### Scenario: 技术支持确认 FAQ
- **WHEN** 技术支持点击"确认并添加"按钮
- **THEN** FAQ 保存到数据库，同时向量化到 ChromaDB，状态标记为"已确认"

#### Scenario: 技术支持拒绝 FAQ
- **WHEN** 技术支持点击"拒绝"按钮
- **THEN** FAQ 草稿被丢弃，工单正常关闭，不向量化

#### Scenario: FAQ 向量化失败处理
- **WHEN** FAQ 确认后向量化到 ChromaDB 失败
- **THEN** 系统回滚数据库状态，提示技术支持"向量化失败，请重试"，FAQ 状态保持"待处理"

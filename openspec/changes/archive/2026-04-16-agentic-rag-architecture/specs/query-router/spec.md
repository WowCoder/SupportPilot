## ADDED Requirements

### Requirement: 查询意图识别
系统应当根据查询内容和复杂度，自动识别查询意图并路由到合适的检索路径。

#### Scenario: 简单查询走默认路径
- **WHEN** 用户查询为单轮事实性问题（如"什么是 RAG"）
- **THEN** 路由到简单检索路径，返回向量检索结果

#### Scenario: 复杂查询走 Agentic RAG 路径
- **WHEN** 用户查询包含对比、列举、推理等复杂意图（如"对比 A 和 B 的异同"）
- **THEN** 路由到 Agentic RAG 路径，启动多轮检索

#### Scenario: 关键词触发规则路由
- **WHEN** 查询包含"对比"、"列出"、"总结"、"分析"等关键词
- **THEN** 直接路由到 Agentic RAG 路径

### Requirement: 路由配置管理
系统应当支持通过配置文件调整路由策略和阈值。

#### Scenario: 调整关键词列表
- **WHEN** 管理员在配置文件中添加新的关键词
- **THEN** 系统重新加载后，新关键词生效

#### Scenario: 切换路由模式
- **WHEN** 配置文件中设置 `router.mode: agentic-only`
- **THEN** 所有查询都路由到 Agentic RAG 路径

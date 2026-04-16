## ADDED Requirements

### Requirement: Agent 状态机编排
系统应当基于 LangGraph 实现 Agent 状态机，支持查询理解、检索规划、工具调用、结果合成。

#### Scenario: 执行单轮检索
- **WHEN** 用户发起简单查询
- **THEN** Agent 执行一次检索并返回结果

#### Scenario: 执行多轮迭代检索
- **WHEN** 用户发起复杂查询，首轮检索结果不足
- **THEN** Agent 自动发起第二轮检索，最多迭代 3 次

#### Scenario: 工具选择
- **WHEN** Agent 分析查询后需要特定检索能力
- **THEN** 自动选择合适的工具（向量/关键词/过滤）

### Requirement: 查询理解节点
Agent 应当理解用户查询的意图、约束条件和期望输出格式。

**注意**: 原有的 QueryRewriter 功能整合到此节点。

#### Scenario: 识别查询类型
- **WHEN** 查询为"对比 A 和 B"
- **THEN** 识别为"对比型"查询，需要检索 A 和 B 各自的信息

#### Scenario: 识别约束条件
- **WHEN** 查询包含"2024 年发布的"
- **THEN** 添加时间过滤条件 `year: 2024`

#### Scenario: 检测对话式查询（原 QueryRewriter 功能）
- **WHEN** 查询包含代词（"它怎么收费"）或省略（"如何重置？"）
- **THEN** 调用聊天记忆系统获取上下文，补全查询

#### Scenario: 识别 Small-to-Big 检索需求
- **WHEN** 查询需要完整上下文（如"这段代码的完整实现"）
- **THEN** 标记使用 Small-to-Big 检索模式

### Requirement: 检索规划节点
Agent 应当根据查询理解结果，制定检索计划和工具调用顺序。

#### Scenario: 生成单步计划
- **WHEN** 简单查询只需一次检索
- **THEN** 规划调用向量检索工具

#### Scenario: 生成多步计划
- **WHEN** 复杂查询需要多源信息
- **THEN** 规划依次调用多个工具

### Requirement: 结果合成节点
Agent 应当将多轮检索结果整合成连贯的回答。

#### Scenario: 整合多轮结果
- **WHEN** 多轮检索返回多个片段
- **THEN** 去重、排序、整合成结构化回答

#### Scenario: 处理空结果
- **WHEN** 检索未找到相关结果
- **THEN** 返回友好的提示，建议用户调整查询

### Requirement: Agent 超时保护
系统应当限制 Agent 的最大执行时间和迭代次数。

#### Scenario: 达到最大迭代次数
- **WHEN** Agent 已执行 3 次迭代
- **THEN** 停止迭代，返回当前最佳结果

#### Scenario: 执行超时
- **WHEN** Agent 执行超过 30 秒
- **THEN** 终止执行，返回超时提示

### Requirement: Agent 配置管理
系统应当支持通过配置文件调整 Agent 行为。

#### Scenario: 调整最大迭代次数
- **WHEN** 配置中设置 `agent.max_iterations: 5`
- **THEN** Agent 最多执行 5 次迭代

#### Scenario: 调整超时时间
- **WHEN** 配置中设置 `agent.timeout_seconds: 60`
- **THEN** Agent 超时时间变为 60 秒

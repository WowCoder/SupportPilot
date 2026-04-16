## ADDED Requirements

### Requirement: 模块化目录结构
代码应当按照功能模块组织，拆分为 core、tools、agents、utils 四个子目录。

#### Scenario: 核心接口位于 core 目录
- **WHEN** 开发者需要实现新工具
- **THEN** 继承 `rag/core/tool.py` 中的 `BaseTool` 基类

#### Scenario: 工具实现位于 tools 目录
- **WHEN** 开发者查找向量检索实现
- **THEN** 在 `rag/tools/vector_tool.py` 中找到

#### Scenario: Agent 定义位于 agents 目录
- **WHEN** 开发者需要修改 Agent 状态机
- **THEN** 在 `rag/agents/retrieval_agent.py` 中修改

### Requirement: 依赖注入容器
系统应当支持依赖注入，方便切换实现和测试。

#### Scenario: 注册服务
- **WHEN** 应用启动时
- **THEN** 所有服务（Embedding、VectorStore、Agent）注册到容器

#### Scenario: 获取服务
- **WHEN** 业务代码需要 Embedding 服务
- **THEN** 从容器获取，而非直接实例化

#### Scenario: 切换实现
- **WHEN** 配置中指定 `embedding.provider: azure`
- **THEN** 容器注入 Azure OpenAI Embedding 实现

### Requirement: 配置驱动
系统应当支持通过 YAML 配置文件管理所有可配置项。

#### Scenario: 加载配置文件
- **WHEN** 应用启动时
- **THEN** 从 `config/rag_config.yaml` 加载配置

#### Scenario: 环境变量覆盖
- **WHEN** 环境变量 `RAG_AGENT_TIMEOUT=60` 存在
- **THEN** 覆盖配置文件中的超时设置

#### Scenario: 配置热重载
- **WHEN** 配置文件修改后发送 SIGHUP 信号
- **THEN** 重新加载配置（不影响正在执行的请求）

### Requirement: 工具基类接口
所有检索工具应当继承统一的基类接口。

#### Scenario: 工具名称
- **WHEN** 工具被调用
- **THEN** 通过 `name` 属性标识（如 "vector_search"）

#### Scenario: 工具描述
- **WHEN** Agent 选择工具
- **THEN** 根据 `description` 属性理解工具用途

#### Scenario: 工具执行
- **WHEN** Agent 调用工具
- **THEN** 执行 `execute(**kwargs)` 方法返回结果

### Requirement: 日志和可观测性
系统应当提供结构化日志和指标采集。

#### Scenario: 记录工具调用
- **WHEN** 工具被调用
- **THEN** 记录工具名称、参数、执行时间、结果数量

#### Scenario: 记录 Agent 状态
- **WHEN** Agent 状态转换
- **THEN** 记录当前状态、触发条件、耗时

#### Scenario: 指标采集
- **WHEN** 请求完成
- **THEN** 采集延迟、令牌数、工具调用次数等指标

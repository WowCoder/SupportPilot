## ADDED Requirements

### Requirement: 向量检索工具
系统应当提供基于向量相似度的检索能力。

#### Scenario: 执行向量检索
- **WHEN** Agent 调用向量检索工具
- **THEN** 返回与查询向量最相似的 top-k 文档片段

#### Scenario: 可配置返回数量
- **WHEN** 调用时指定 `k=5`
- **THEN** 返回 5 个最相关的文档片段

#### Scenario: 相似度阈值过滤
- **WHEN** 设置 `similarity_threshold=0.5`
- **THEN** 仅返回相似度大于 0.5 的文档片段

### Requirement: 关键词检索工具 (BM25)
系统应当提供基于 BM25 算法的关键词检索能力。

#### Scenario: 执行关键词检索
- **WHEN** Agent 调用关键词检索工具
- **THEN** 返回包含查询关键词的文档片段

#### Scenario: 多关键词匹配
- **WHEN** 查询包含多个关键词
- **THEN** 根据 BM25 评分返回相关文档

### Requirement: 元数据过滤工具
系统应当支持按元数据（如来源文件、页面、时间）过滤检索结果。

#### Scenario: 按来源文件过滤
- **WHEN** 指定 `source: "high-concurrency.pdf"`
- **THEN** 仅返回该文件的文档片段

#### Scenario: 按页面范围过滤
- **WHEN** 指定 `page: 1-10`
- **THEN** 仅返回第 1 到 10 页的文档片段

#### Scenario: 组合过滤
- **WHEN** 同时指定来源和页面范围
- **THEN** 返回同时满足两个条件的文档片段

### Requirement: 多路召回融合工具
系统应当支持融合多路检索结果（向量 + 关键词 + 元数据过滤）。

#### Scenario: 执行多路召回
- **WHEN** Agent 调用多路融合工具
- **THEN** 合并向量检索、关键词检索的结果

#### Scenario: RRF 排序融合
- **WHEN** 多路结果返回后
- **THEN** 使用倒数排名融合 (RRF) 算法重新排序

### Requirement: Small-to-Big 检索策略
系统应当支持 Small-to-Big 检索策略：小块索引（高精度），大块返回（完整上下文）。

**注意**: Small-to-Big 是索引和检索的基础策略，不是独立工具。

#### Scenario: 小块检索，大块返回
- **WHEN** Agent 执行向量检索，且文档使用 Small-to-Big 索引
- **THEN** 在小块 ChromaDB 中检索，通过 parent_id 映射返回大块内容

#### Scenario: 配置大块和小块大小
- **WHEN** 配置中设置 `parent_size: 2000`, `child_size: 400`
- **THEN** 索引时大块为 2000 字符，小块为 400 字符

#### Scenario: ParentDocumentStore 集成
- **WHEN** 文档入库时
- **THEN** 同时存储大块到 ParentDocumentStore，小块索引到 ChromaDB

### Requirement: 检索工具配置
系统应当支持通过配置文件管理检索工具的参数和启用状态。

#### Scenario: 启用/禁用工具
- **WHEN** 配置中设置 `tools.bm25.enabled: false`
- **THEN** 关键词检索工具不可用

#### Scenario: 调整工具参数
- **WHEN** 配置中修改 `tools.vector.k: 10`
- **THEN** 向量检索默认返回 10 个结果

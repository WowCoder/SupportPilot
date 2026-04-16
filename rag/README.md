# Agentic RAG Architecture

SupportPilot 的新一代检索增强生成 (RAG) 系统，采用 Agentic 架构和 LangGraph 状态机编排。

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Query Router                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Rules (keywords, patterns) + ML Classifier          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────┬───────────────────────────────────────────────┘
              │
     ┌────────┴────────┐
     │                 │
     ▼                 ▼
┌─────────┐      ┌─────────────────────────────────────────┐
│ Simple  │      │           Agentic Path                  │
│ Path    │      │  ┌──────────────────────────────────┐   │
│ (vector │      │  │  LangGraph State Machine         │   │
│  search)│      │  │  - query_understanding           │   │
│         │      │  │  - planning                      │   │
│         │      │  │  - tool_execution                │   │
│         │      │  │  - synthesis                     │   │
│         │      │  └──────────────────────────────────┘   │
│         │      └─────────────────────────────────────────┘
└─────────┘                       │
     │                            │
     └────────────┬───────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Retrieval Tools                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ vector_search│  │ bm25_search  │  │ metadata_filter │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
│                        ┌─────────────────────────────────┐  │
│                        │      ensemble_retrieval         │  │
│                        │    (RRF fusion)                 │  │
│                        └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Small-to-Big Retrieval                          │
│  - Small chunks (400 chars) indexed in ChromaDB             │
│  - Large chunks (2000 chars) stored in ParentDocumentStore  │
│  - Search small, return large for complete context          │
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
rag/
├── core/                   # 核心模块
│   ├── tool.py            # BaseTool 抽象类和 ToolResult
│   ├── container.py       # 依赖注入容器
│   ├── config.py          # YAML 配置加载器
│   └── observability.py   # 日志和指标采集
├── tools/                  # 检索工具
│   ├── vector_tool.py     # 向量检索工具
│   ├── bm25_tool.py       # BM25 关键词检索工具
│   ├── filter_tool.py     # 元数据过滤工具
│   ├── ensemble_tool.py   # 多路召回融合工具 (RRF)
│   └── parent_store.py    # Small-to-Big 大块存储
├── agents/                 # Agent 模块
│   ├── states.py          # Agent 状态和事件定义
│   ├── router.py          # 查询路由分发器
│   ├── router_rules.py    # 规则匹配器
│   ├── router_classifier.py # ML 意图分类器
│   ├── retrieval_agent.py # LangGraph 状态机编排
│   └── nodes/             # 状态机节点
│       ├── query_understanding.py  # 查询理解（整合 QueryRewriter）
│       ├── planning.py             # 检索规划
│       ├── tool_execution.py       # 工具调用
│       └── synthesis.py            # 结果合成
├── service.py              # RAG 服务兼容层
└── rag_utils.py            # 文档处理工具（保留用于 ingestion）
```

## 核心模块

### 1. Core (rag/core/)

**tool.py**: 工具抽象基类
```python
class BaseTool:
    name = "tool_name"
    description = "Tool description"
    
    def execute(self, **kwargs) -> ToolResult:
        pass
```

**container.py**: 依赖注入容器
```python
container = Container()
container.register('embedding', EmbeddingService)
service = container.get('embedding')
```

**config.py**: YAML 配置加载器
```python
config = get_config()
k = config.get('tools.vector.k', default=5)
```

**observability.py**: 指标采集
```python
@timed_tool
def execute(self, ...):
    pass
```

### 2. Tools (rag/tools/)

| Tool | Description | Use Case |
|------|-------------|----------|
| `vector_search` | 向量相似度检索 | 语义检索，高精度 |
| `bm25_search` | BM25 关键词检索 | 精确匹配，多关键词 |
| `metadata_filter` | 元数据过滤 | 按来源、页面、时间过滤 |
| `ensemble_retrieval` | RRF 融合 | 多路召回结果融合 |

### 3. Agents (rag/agents/)

**Query Router**: 查询路由
- 规则匹配：关键词、正则模式
- ML 分类：Logistic Regression（可选）
- 模式：`simple`（直接检索）、`agentic`（多步推理）、`auto`（自动路由）

**Retrieval Agent**: LangGraph 状态机
```
START → query_understanding → planning → tool_execution → synthesis → END
```

**Nodes**:
- `query_understanding`: 查询改写（代词解析、省略补全）
- `planning`: 选择工具、创建检索计划
- `tool_execution`: 执行工具、收集结果
- `synthesis`: 生成最终答案

## 配置说明

配置文件：`config/rag_config.yaml`

```yaml
# Agent 配置
agent:
  max_iterations: 3
  timeout_seconds: 30
  temperature: 0.3

# Router 配置
router:
  mode: auto  # simple | agentic | auto
  agentic_keywords:
    - "对比"
    - "比较"
    - "列出"
    - "总结"
    - "分析"

# 工具配置
tools:
  vector:
    enabled: true
    k: 5
    similarity_threshold: 0.25
    use_small_to_big: true
  bm25:
    enabled: true
    k: 5
  ensemble:
    enabled: true
    use_rrf: true

# Small-to-Big 配置
small_to_big:
  parent_size: 2000  # 大块大小（返回给用户）
  child_size: 400    # 小块大小（索引检索）
```

## Small-to-Big 检索策略

```
索引阶段:
  原文 → 大块分割 (2000 chars) → 小块分割 (400 chars)
           ↓                        ↓
    ParentDocumentStore          ChromaDB
    (存储大块)                  (索引小块)

检索阶段:
  查询 → 小块向量检索 → 查 parent_id 映射 → 返回大块
         (ChromaDB)         (ParentDocumentStore)
```

**优势**:
- 小块索引：检索精度高
- 大块返回：上下文完整
- 默认启用，无需额外配置

## 使用示例

### 简单检索
```python
from rag.service import rag_service

results = rag_service.retrieve(
    query="高并发的原则是什么",
    k=5,
    similarity_threshold=0.25,
    use_small_to_big=True
)
```

### Agentic 检索
```python
from rag.agents.retrieval_agent import retrieval_agent

result = retrieval_agent.run(
    query="对比 A 和 B 的异同",
    session_id="conversation_123"
)

answer = result['answer']
results = result['retrieval_results']
```

### 直接使用工具
```python
from rag.tools.vector_tool import vector_search

result = vector_search.execute(
    query="高并发原则",
    k=5,
    similarity_threshold=0.25,
    use_small_to_big=True
)

if result.success:
    for doc in result.data:
        print(f"Content: {doc['content'][:100]}...")
        print(f"Similarity: {doc['similarity']}")
```

## API 端点

### POST /api/test-query
测试检索效果（仅 tech_support 权限）

```json
{
  "query": "高并发的原则是什么",
  "k": 5,
  "similarity_threshold": 0.25,
  "use_small_to_big": true
}
```

### POST /api/preview-chunks
预览分块效果（仅 tech_support 权限）

```json
{
  "strategy": "semantic",
  "semantic_threshold": 0.5,
  "use_small_to_big": true,
  "parent_size": 2000,
  "child_size": 400
}
```

## 迁移说明

### 从旧架构迁移

旧代码 (`rag/rag_utils.py`) 仍保留用于文档处理（ingestion），检索功能已迁移到新架构：

| 旧功能 | 新架构 | 状态 |
|--------|--------|------|
| `retrieve_relevant_info` | `rag_service.retrieve()` | 已迁移 |
| `retrieve_with_parent` | Small-to-Big (default) | 已整合 |
| `process_document` | `rag_utils.process_document` | 保留 |
| `preview_chunks` | `rag_utils.preview_chunks` | 保留 |

### 路由更新
`app/api/routes.py` 已更新使用新的 `rag_service`：
- 简单查询：直接使用 `vector_search`
- 复杂查询：自动路由到 Agentic RAG

## 测试

运行测试：
```bash
pytest tests/
```

测试覆盖：
- 工具单元测试
- Router 单元测试
- Agent 集成测试
- 端到端检索测试

## 性能指标

通过 `observability.py` 采集：
- 工具调用次数和延迟
- Agent 迭代次数
- 查询响应时间

```python
from rag.core.observability import metrics

summary = metrics.get_summary()
print(f"Average tool latency: {summary['tool_calls']['avg_duration_ms']}ms")
```

## 故障排除

### 查询无结果
1. 检查 `similarity_threshold` 是否过高
2. 尝试调整 `k` 值获取更多结果
3. 检查文档是否成功入库

### Agent 超时
1. 检查 `agent.timeout_seconds` 配置
2. 减少 `max_iterations`
3. 检查 LLM API 响应时间

### Small-to-Big 未生效
1. 确认上传时启用了 `use_small_to_big`
2. 检查 `parent_store` 数据库文件存在
3. 验证 ChromaDB 中 `parent_id` 元数据

## 未来扩展

1. **多 Agent 协作**: 复杂场景下多 Agent 分工
2. **流式输出**: SSE 实时返回检索结果
3. **查询缓存**: 高频查询缓存
4. **评估框架**: 检索质量自动化评估

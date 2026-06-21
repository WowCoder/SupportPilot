# RAGAS 评估流程

## 概览

SupportPilot 使用 [RAGAS](https://docs.ragas.io) 框架对 RAG 系统进行自动化评估。评估覆盖 **13 篇测试文档**、**6 个查询**、**4 个指标**，完整运行约 20-25 分钟。

```bash
source venv/bin/activate
python scripts/run_smoke_eval.py
```

## 整体架构

```
scripts/run_smoke_eval.py           ← 入口
  ├── Phase 1: 查询执行               ← execute_query()
  │     ├── 路由 (agentic / simple)
  │     ├── 检索 (ChromaDB 向量搜索)
  │     └── 生成 (llm_client → DeepSeek)
  │
  ├── Phase 2: RAGAS 评分            ← evaluate_case()
  │     └── RagasMetrics.compute_all()
  │
  └── Phase 3: 聚合 & 报告            ← aggregate_results()
        ├── evaluation/reports/xxx.json
        └── console summary table
```

## Phase 1：查询执行

```
smoke case {query, reference, ...}
        │
        ▼
  query_router.route(query)
        │
 ┌──────┴─────────┐
 ▼                ▼
agentic           simple
 │                │
 ▼                ▼
retrieval_agent   RAGService.retrieve()
.run()            → rag_utils.retrieve_relevant_info()
 │                → ChromaDB collection.query()
 │                → 阈值过滤 (similarity ≥ 0.25)
 ▼                │
SynthesisNode     ▼
_generate_answer  llm_client.chat(query, contexts)
 │                → POST api.deepseek.com
 ▼                ▼
        最终 answer + contexts
```

**检索** 使用与 ingestion 相同的 `CustomEmbeddingFunction` 实例，保证 embedding 向量一致。

**生成** 通过 `llm_client.chat()` 调用 DeepSeek API（temperature=0.1，max_tokens=512）。

## Phase 2：RAGAS 指标

`RagasMetrics.compute_all()` 接收 `(question, contexts[], answer, reference?)`，构造 `SingleTurnSample`，依次计算 4 个指标：

### Faithfulness（忠实度）

> 回答中有多少内容可以从检索到的上下文中找到依据？

| 步骤 | 说明 |
|------|------|
| 1. 拆解陈述 | LLM 将 answer 拆解为独立的原子陈述 |
| 2. NLI 判断 | LLM 逐条判断每个陈述能否从 contexts 中推断 (0/1) |
| 3. 计算得分 | 可归因的陈述数 / 总陈述数 |

- **需要 reference**：否
- **LLM 调用**：RagasLLMAdapter → llm_factory(deepseek-v4-flash)

### Answer Relevancy（回答相关度）

> 回答与用户问题的相关程度如何？

| 步骤 | 说明 |
|------|------|
| 1. 反向生成 | LLM 根据 answer 反向生成 n 个问题 |
| 2. 相似度计算 | embedding 计算生成问题与原始 question 的 cosine 相似度 |
| 3. 计算得分 | 所有相似度的均值 |

- **需要 reference**：否
- **需要 embedding**：BAAI/bge-m3

### Context Precision（上下文精度）

> 检索结果中有多少是与参考答案真正相关的？（信噪比）

| 步骤 | 说明 |
|------|------|
| 1. 逐条验证 | LLM 逐条判断每个 context chunk 是否与 reference 相关 |
| 2. 加权计算 | 排名越靠前的相关 chunk 权重越高 |

- **需要 reference**：是
- **LLM 调用**：RagasLLMAdapter

### Context Recall（上下文召回）

> 参考答案中的关键信息有多少被检索结果覆盖？

| 步骤 | 说明 |
|------|------|
| 1. 拆解 reference | LLM 将 reference 拆解为原子陈述 |
| 2. 逐条归因 | 逐条判断每个 reference 陈述能否从 contexts 中找到 |
| 3. 计算得分 | 可归因的陈述数 / 总陈述数 |

- **需要 reference**：是
- **LLM 调用**：RagasLLMAdapter

### 指标关注矩阵

| 修改模块 | 重点关注的指标 |
|----------|--------------|
| `rag/online/retrievers/` | Context Precision, Context Recall |
| `rag/offline/steps/chunking.py` | Context Recall |
| `rag/online/pipeline/nodes/synthesis.py` | Faithfulness, Answer Relevancy |
| `llm/llm_client.py` | Faithfulness, Answer Relevancy |
| `rag/online/router.py` | Context Precision |

## Phase 3：聚合 & 报告

```
6 个 case 的 4 维分数
        │
        ▼
 aggregate_results()
 ├── overall      (6 case 均值 / min / max / std)
 ├── by_category  (definition, comparison, factual ...)
 └── by_difficulty (easy, medium, hard)
        │
        ▼
 输出 → evaluation/reports/YYYYMMDD_HHMMSS_report.json
     → console summary table
```

## 前置条件

ChromaDB 中必须已导入测试文档。如果 `instance/chroma_db/` 被清空过：

```bash
source venv/bin/activate
python -c "
from rag.offline.pipeline import rag_utils
import glob
ids = rag_utils.collection.get()['ids']
if ids: rag_utils.collection.delete(ids=ids)
for f in sorted(glob.glob('data/test_docs/*.txt')):
    r = rag_utils.process_document(f, strategy='semantic', chunk_size=1000, chunk_overlap=150)
    print(f'{\"OK\" if r[\"success\"] else \"FAIL\"} {f}')
"
```

## 测试文档

共 13 篇中文文档（`data/test_docs/`，总大小 ~22KB），覆盖 6 个查询：

| 查询 | 类别 | 文档数 |
|------|------|:------:|
| 英特尔 XeSS 技术是什么 | definition | 1 |
| 对比 RTX 4070 和 RTX 4060 的性能差异 | comparison | 3 |
| 京东 2023 年第二季度营收是多少 | factual | 1 |
| 为什么 Steam 调整了最低价格门槛 | explanation | 1 |
| 如何防控儿童青少年近视 | how-to | 1 |
| 英伟达和英特尔在显卡技术上有哪些竞争 | comparison | 4 |

另有 5 篇无关文档作为检索噪声。

## 基线（2026-06-18，deepseek-v4-flash）

| 指标 | Overall | 期望区间 |
|------|:-------:|:-------:|
| Faithfulness | **0.784** | 0.70 - 0.90 |
| Answer Relevancy | **0.614** | 0.55 - 0.80 |
| Context Precision | **0.917** | 0.85 - 1.00 |
| Context Recall | **0.655** | 0.55 - 0.80 |

任一指标低于期望区间下界需要排查对应模块。

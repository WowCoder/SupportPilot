# RAG 架构文档

## 检索增强生成流程

### 完整架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          文档上传阶段                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  用户上传 → Flask 路由 → rag_utils.process_document()                    │
│     ↓                                                                    │
│  文件类型判断 (PDF/TXT/DOCX) → 文档加载器                                │
│     ↓                                                                    │
│  文本提取 (PDF: pdfplumber 布局感知)                                     │
│     ↓                                                                    │
│  清洗：移除页眉页脚 → 清理数字噪声行                                     │
│     ↓                                                                    │
│  质量评分 → 过滤低质量 chunk (<60 分)                                    │
│     ↓                                                                    │
│  智能分块 (语义/句子/递归策略)                                           │
│     ↓                                                                    │
│  MD5 去重 → ChromaDB 向量化存储 (all-MiniLM-L6-v2)                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                          问答检索阶段                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  用户提问 → conversation/send_message()                                 │
│     ↓                                                                    │
│  rag_utils.retrieve_relevant_info(query, k=3)                           │
│     ↓                                                                    │
│  [可选] 查询扩展 → 添加同义词                                           │
│     ↓                                                                    │
│  [可选] 混合搜索：BM25 + 向量 → RRF 融合                                 │
│     ↓                                                                    │
│  向量检索 (余弦相似度) → 过滤阈值 (<0.25)                               │
│     ↓                                                                    │
│  Cross-Encoder 重排序 → 返回 Top-3                                      │
│     ↓                                                                    │
│  qwen_api.generate_response(query, context)                             │
│     ↓                                                                    │
│  构建 Prompt: "相关知识：...\n\n用户问题：..."                           │
│     ↓                                                                    │
│  调用 Qwen API (qwen-turbo) → 生成回答                                  │
│     ↓                                                                    │
│  保存 AI 消息到数据库 → 返回前端                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 阶段 1: 文档处理（上传时）

**代码**: `rag/rag_utils.py:process_document()`

| 步骤 | 说明 | 配置/工具 |
|------|------|-----------|
| 文件加载 | 支持 PDF/TXT/DOCX | PyPDFLoader, TextLoader, Docx2txtLoader |
| PDF 文本提取 | 布局感知提取，保留阅读顺序 | pdfplumber |
| 页眉页脚检测 | 检测跨页重复行 | `_detect_repeated_lines()` |
| 文本清洗 | 移除纯数字行、噪声 | `_clean_text()` |
| 质量评分 | 0-100 分综合评分 | `_quality_score()` - 长度/完整性/密度/噪声 |
| 文档分块 | 智能分块策略 | SemanticChunker / SentenceChunker / RecursiveCharacterTextSplitter |
| 去重处理 | MD5 哈希去重 | 防止重复文档 |
| 向量化 | SentenceTransformer 嵌入 | all-MiniLM-L6-v2 (384 维) |
| 存储 | ChromaDB 持久化 | ./chroma_db, HNSW 索引，余弦相似度 |

**质量评分维度** (`_quality_score()`, 100 分制):
- 长度评分 (20 分): 100-2000 字符得满分
- 句子完整性 (20 分): 包含标点符号
- 信息密度 (20 分): 中英文字符占比 >30%
- 噪声比率 (20 分): 噪声行 <20%
- 语言检测 (20 分): 有意义字符 >50%

### 分块策略详解

系统支持三种智能分块策略，可根据文档类型和质量要求选择：

| 策略 | 说明 | 适用场景 | 特点 |
|------|------|----------|------|
| **semantic** (默认) | 基于 embedding 相似度的语义分块 | 高质量要求场景 | 保持语义完整性，相关内容在同一 chunk，检索质量最佳 |
| **sentence** | 句子级分块，保证不截断句子 | 通用场景 | 支持中英文句子边界，质量稳定，处理速度较快 |
| **recursive** | 传统固定大小递归分块 | 大批量快速处理 | 处理速度最快，但可能在句子中间截断 |

**使用方式**：
```python
result = rag_utils.process_document(
    file_path='document.pdf',
    strategy='semantic',
    chunk_size=1500,
    chunk_overlap=300
)
```

## 阶段 2: 查询扩展

**代码**: `rag/rag_utils.py:_expand_query()`

同义词替换提升召回率:

| 关键词 | 扩展同义词 |
|--------|------------|
| account | user, profile, login, registration |
| password | credential, authentication, reset, change |
| error | issue, problem, bug, failure, exception |
| payment | billing, invoice, transaction, charge |
| subscription | plan, pricing, renewal, upgrade, downgrade |
| feature | functionality, capability, option |
| help | support, assistance, guide, tutorial |
| setup | installation, configuration, initialize |
| api | endpoint, integration, webhook, request |

**示例**: 用户问 `"reset password"` → 同时搜索 `["change credential", "reset authentication"]`

## 阶段 3: 混合检索

**代码**: `rag/rag_utils.py:_hybrid_search()`

| 检索类型 | 优势 | 权重 |
|----------|------|------|
| BM25 关键词检索 | 精确匹配（错误码、产品名） | α=0.5 |
| 向量语义检索 | 理解语义相似性 | 1-α=0.5 |

**RRF (Reciprocal Rank Fusion) 融合算法**:
```python
RRF Score = α / (rank_bm25 + 60) + (1-α) / (rank_vector + 60)
```

## 阶段 4: Cross-Encoder 重排序

**代码**: `rag/rag_utils.py:_rerank_with_cross_encoder()`

- 模型：`cross-encoder/ms-marco-MiniLM-L-6-v2`
- 作用：对粗排结果进行精细相关性评分
- 流程：召回 k×3 条 → 重排序 → 返回 top-k
- 延迟加载：首次使用时加载模型

## 阶段 5: LLM 生成回答

**代码**: `api/qwen_api.py:generate_response()`

- API：Alibaba Qwen (`qwen-turbo`)
- 端点：`https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
- Prompt 构建：
  ```
  相关知识：{content} (相似度：0.85)
  相关知识：{content} (相似度：0.72)
  相关知识：{content} (相似度：0.65)

  用户问题：{query}
  ```
- System Prompt: `你是一个 helpful 的客户支持助手。使用提供的知识来回答用户问题。`
- 温度：0.7
- 最大 token：1024

## 技术组件总览

| 组件 | 技术选型 | 作用 |
|------|----------|------|
| 向量数据库 | ChromaDB (PersistentClient) | 存储文档向量和元数据 |
| Embedding 模型 | sentence-transformers/all-MiniLM-L6-v2 | 384 维向量生成 |
| 重排序模型 | cross-encoder/ms-marco-MiniLM-L-6-v2 | 精细相关性打分 |
| 关键词检索 | BM25Okapi (rank_bm25) | 混合搜索组件 |
| 文本分块 | SemanticChunker / SentenceChunker / RecursiveCharacterTextSplitter | 智能文本切分 |
| PDF 解析 | pdfplumber | 布局感知文本提取 |
| LLM | Qwen-Turbo (阿里云) | 最终回答生成 |

## 性能特征

| 阶段 | 耗时 (预估) |
|------|-------------|
| 查询扩展 | ~1ms |
| BM25 检索 | ~10ms |
| 向量检索 | ~50ms |
| Cross-Encoder 重排序 | ~100-200ms |
| **检索总计** | **~200-300ms** |
| LLM 生成 | ~500-1500ms |
| **端到端总计** | **~700-1800ms** |

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| strategy | semantic | 分块策略 |
| chunk_size | 1500 | 分块大小（字符） |
| chunk_overlap | 300 | 分块重叠 |
| similarity_threshold | 0.25 | 最小相似度阈值 |
| quality_threshold | 60 | 最低质量分数 |
| use_expansion | True | 启用查询扩展 |
| use_hybrid | False | 启用混合检索 |
| use_reranking | True | 启用 Cross-Encoder 重排序 |
| embedding_model | all-MiniLM-L6-v2 | 向量嵌入模型 |
| rerank_model | ms-marco-MiniLM-L-6-v2 | 重排序模型 |

## 核心特性

1. **智能分块**: 语义/句子/递归三种策略
2. **去重机制**: MD5 哈希 + 持久化存储
3. **质量过滤**: 自动化质量评分
4. **混合检索**: BM25 + 向量 + RRF 融合
5. **重排序**: Cross-Encoder 提升排序质量
6. **查询扩展**: 同义词替换提升召回率
7. **线程安全**: `threading.Lock` 保护并发写入
8. **错误处理**: 完善的异常处理和降级策略

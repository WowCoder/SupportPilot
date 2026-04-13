# RAG (检索增强生成) 实现文档

本文档详细描述了 SupportPilot 系统中 RAG (Retrieval-Augmented Generation) 的完整实现。

## 目录

- [架构概览](#架构概览)
- [核心组件](#核心组件)
- [文档处理流程](#文档处理流程)
- [检索流程](#检索流程)
- [生成流程](#生成流程)
- [配置参数](#配置参数)
- [API 参考](#api 参考)

---

## 架构概览

SupportPilot 的 RAG 系统由以下核心组件构成：

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
│  RecursiveCharacterTextSplitter 分块                                    │
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

---

## 核心组件

| 组件 | 技术选型 | 文件位置 |
|------|----------|----------|
| 向量数据库 | ChromaDB (PersistentClient) | `rag/rag_utils.py` |
| Embedding 模型 | sentence-transformers/all-MiniLM-L6-v2 | `CustomEmbeddingFunction` |
| 重排序模型 | cross-encoder/ms-marco-MiniLM-L-6-v2 | `_rerank_with_cross_encoder()` |
| 关键词检索 | BM25Okapi (rank_bm25) | `_hybrid_search()` |
| 文本分块 | RecursiveCharacterTextSplitter | `process_document()` |
| PDF 解析 | pdfplumber | `_extract_pdf_text_layout_aware()` |
| 文档加载 | TextLoader, Docx2txtLoader | `process_document()` |
| LLM | Qwen-Turbo (阿里云) | `api/qwen_api.py` |

---

## 文档处理流程

### 1. 文件加载

支持的文件格式：

| 格式 | 加载器 | 说明 |
|------|--------|------|
| `.pdf` | pdfplumber (首选) / PyPDFLoader (降级) | 布局感知提取 |
| `.txt` | TextLoader | UTF-8 编码 |
| `.docx` | Docx2txtLoader | Word 文档 |

**代码位置**: `rag/rag_utils.py:process_document()` (第 307-366 行)

### 2. PDF 文本提取与清洗

#### 2.1 布局感知提取

```python
def _extract_pdf_text_layout_aware(self, file_path):
    """逐页提取文本，保留页面元数据"""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()  # 按阅读顺序提取
            pages.append({'text': page_text, 'page': page_num})
```

**代码位置**: `rag/rag_utils.py:153-190`

#### 2.2 页眉页脚检测与移除

```python
def _detect_repeated_lines(self, pages, threshold=0.5):
    """检测在超过 threshold% 页面中出现的行"""
    line_counts = Counter()
    for page_text in pages:
        lines = set(page_text.strip().split('\n'))
        for line in lines:
            line_counts[line.strip()] += 1

    min_count = int(len(pages) * threshold)
    repeated = {line for line, count in line_counts.items()
                if count >= min_count and len(line) < 100}
    return repeated
```

**代码位置**: `rag/rag_utils.py:192-217`

#### 2.3 文本清洗

移除以下噪声：
- 重复的页眉页脚行
- 页码标记（如"第 1 页"、"- 1 -"）
- 纯数字行
- 过短的行（<5 字符）

**代码位置**: `rag/rag_utils.py:129-151`, `219-242`

### 3. 质量评分

对每个 chunk 进行 0-100 分的综合质量评分：

| 维度 | 分值 | 评分标准 |
|------|------|----------|
| 长度 | 20 分 | 100-2000 字符=满分，50-100 或 2000-3000=10 分 |
| 句子完整性 | 20 分 | 包含标点符号 (,.!?.:;?) |
| 信息密度 | 20 分 | 中英文字符占比 >30% |
| 噪声比率 | 20 分 | 噪声行 <20% |
| 语言检测 | 20 分 | 有意义字符 >50% |

**过滤规则**: 仅保留分数 >= 60 的 chunk

**代码位置**: `rag/rag_utils.py:244-287`

### 4. 文本分块

使用 `RecursiveCharacterTextSplitter`:

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,      # 每块最大 1500 字符
    chunk_overlap=300,    # 块间重叠 300 字符
    length_function=len
)
chunks = text_splitter.split_documents(documents)
```

**代码位置**: `rag/rag_utils.py:368-373`

### 5. MD5 去重

```python
def _compute_document_hash(self, content):
    """计算内容哈希用于去重"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()
```

- 哈希值持久化存储在 `self.document_hashes`
- 上传时检查，跳过已存在的文档

**代码位置**: `rag/rag_utils.py:125-127`

### 6. 向量化与存储

```python
# 向量化并添加到 ChromaDB
self.collection.add(
    documents=documents_to_add,
    ids=ids_to_add,
    metadatas=metadatas_to_add
)
```

- 使用 `CustomEmbeddingFunction` 自动生成向量
- 集合配置：`metadata={"hnsw:space": "cosine"}` (余弦相似度)

**代码位置**: `rag/rag_utils.py:412-417`

---

## 检索流程

### 1. 查询扩展

通过同义词替换扩展查询，提升召回率：

```python
def _expand_query(self, query):
    """为查询添加同义词和相关词"""
    expansions = {
        'account': ['user', 'profile', 'login', 'registration'],
        'password': ['credential', 'authentication', 'reset', 'change'],
        'error': ['issue', 'problem', 'bug', 'failure', 'exception'],
        'payment': ['billing', 'invoice', 'transaction', 'charge'],
        'subscription': ['plan', 'pricing', 'renewal', 'upgrade', 'downgrade'],
        'feature': ['functionality', 'capability', 'option'],
        'help': ['support', 'assistance', 'guide', 'tutorial'],
        'setup': ['installation', 'configuration', 'initialize', 'start'],
        'api': ['endpoint', 'integration', 'webhook', 'request'],
    }
```

**示例**:
- 输入：`"reset password"`
- 扩展查询：`["reset password", "change credential", "reset authentication"]`

**代码位置**: `rag/rag_utils.py:433-466`

### 2. 向量检索

```python
results = self.collection.query(
    query_texts=[query],
    n_results=k * 3,  # 获取更多候选用于重排序
    include=["documents", "distances", "metadatas"]
)

# 计算相似度：similarity = 1 - distance (余弦距离)
# 过滤阈值：< 0.25
```

**代码位置**: `rag/rag_utils.py:663-699`

### 3. 混合检索 (可选)

结合 BM25 关键词检索和向量语义检索：

```python
def _hybrid_search(self, query, k=3, alpha=0.5):
    # 1. BM25 检索
    tokenized_query = self._tokenize(query)
    bm25_scores = self.bm25_index.get_scores(tokenized_query)

    # 2. 向量检索
    vector_results = self.collection.query(query_texts=[query], n_results=...)

    # 3. RRF 融合
    for doc in all_docs:
        rrf_score = 0
        if doc in bm25_result_map:
            bm25_rank = calculate_rank(doc, bm25_scores)
            rrf_score += alpha / (bm25_rank + 60)
        if doc in vector_result_map:
            vector_rank = calculate_rank(doc, vector_results)
            rrf_score += (1 - alpha) / (vector_rank + 60)
```

**RRF 公式**:
```
RRF Score = α / (rank_bm25 + 60) + (1-α) / (rank_vector + 60)
```

**代码位置**: `rag/rag_utils.py:551-640`

### 4. Cross-Encoder 重排序

```python
def _rerank_with_cross_encoder(self, query, results, k=3):
    # 加载模型 (延迟加载)
    self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    # 准备查询 - 文档对
    pairs = [[query, result['content']] for result in results]

    # 获取精细相关性分数
    scores = self.cross_encoder.predict(pairs)

    # 重排序
    for i, result in enumerate(results):
        result['rerank_score'] = float(scores[i])

    results.sort(key=lambda x: x['rerank_score'], reverse=True)
    return results[:k]
```

**特点**:
- 延迟加载：首次使用时才加载模型
- 降级处理：模型加载失败时返回原始排序结果

**代码位置**: `rag/rag_utils.py:484-522`

---

## 生成流程

### 1. Prompt 构建

```python
def generate_response(self, query, context):
    # 处理带相似度的上下文
    if context and isinstance(context[0], dict):
        context_str = "\n".join([
            f"相关知识：{item['content']} (相似度：{item['similarity']:.2f})"
            for item in context if item.get('similarity', 0) > 0.1
        ])

    message = f"{context_str}\n\n用户问题：{query}"
```

**示例输出**:
```
相关知识：账户密码重置需要在设置页面进行 (相似度：0.85)
相关知识：如果您忘记了密码，可以点击登录页面的"忘记密码"链接 (相似度：0.72)

用户问题：如何重置我的密码？
```

### 2. LLM 调用

```python
POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions

Headers:
    Authorization: Bearer {QWEN_API_KEY}
    Content-Type: application/json

Body:
{
    "model": "qwen-turbo",
    "messages": [
        {"role": "system", "content": "你是一个 helpful 的客户支持助手。使用提供的知识来回答用户问题。如果知识库中没有相关信息，请诚实地告诉用户。"},
        {"role": "user", "content": message}
    ],
    "temperature": 0.7,
    "max_tokens": 1024
}
```

### 3. 错误处理

| 错误类型 | 用户提示 |
|----------|----------|
| 超时 | "抱歉，AI 服务响应超时，请稍后重试。" |
| HTTP 401 | "抱歉，API 密钥验证失败。" |
| HTTP 429 | "抱歉，API 请求过于频繁，请稍后重试。" |
| 连接错误 | "抱歉，无法连接到 AI 服务，请检查网络连接。" |
| 其他错误 | "抱歉，AI 服务请求失败，请稍后重试。" |

**代码位置**: `api/qwen_api.py:31-126`

---

## 配置参数

### 文档处理参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| chunk_size | 1500 | 分块大小（字符） |
| chunk_overlap | 300 | 分块重叠 |
| quality_threshold | 60 | 最低质量分数 |

### 检索参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| similarity_threshold | 0.25 | 最小相似度阈值 |
| k (retrieve_k) | 3 | 返回结果数量 |
| use_expansion | True | 启用查询扩展 |
| use_hybrid | False | 启用混合检索 |
| use_reranking | True | 启用 Cross-Encoder 重排序 |

### 混合检索参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| alpha | 0.5 | BM25 权重 (0.5 = 平等权重) |
| k (constant) | 60 | RRF 分母常数 |

### 模型配置

| 模型 | 位置 | 说明 |
|------|------|------|
| all-MiniLM-L6-v2 | `~/.cache/huggingface` | 向量嵌入 (384 维) |
| ms-marco-MiniLM-L-6-v2 | 延迟加载 | Cross-Encoder 重排序 |

---

## API 参考

### RAGUtils 类方法

#### 文档处理

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `process_document()` | file_path, chunk_size, chunk_overlap | dict | 处理文档并添加到索引 |
| `_extract_pdf_text_layout_aware()` | file_path | list | PDF 布局感知文本提取 |
| `_clean_text()` | text | str | 文本清洗 |
| `_quality_score()` | text | int (0-100) | 质量评分 |

#### 检索

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `retrieve_relevant_info()` | query, k, similarity_threshold, use_expansion, use_hybrid, use_reranking | list | 检索相关文档 |
| `_expand_query()` | query | list | 查询扩展 |
| `_hybrid_search()` | query, k, alpha | list | 混合检索 |
| `_rerank_with_cross_encoder()` | query, results, k | list | Cross-Encoder 重排序 |

#### 工具方法

| 方法 | 说明 |
|------|------|
| `get_document_count()` | 获取文档总数 |
| `delete_documents_by_source(filename)` | 按文件名删除文档 |
| `clear_bm25_index()` | 清除 BM25 索引 |

### QwenAPI 类方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `generate_response()` | query, context | str | 生成 AI 回答 |
| `_get_api_key()` | - | str | 从配置获取 API 密钥 |

---

## 性能特征

| 阶段 | 耗时 (预估) | 可优化点 |
|------|-------------|----------|
| 查询扩展 | ~1ms | - |
| BM25 检索 | ~10ms | 预建索引 |
| 向量检索 | ~50ms | HNSW 参数调优 |
| Cross-Encoder 重排序 | ~100-200ms | GPU 加速/模型蒸馏 |
| **检索总计** | **~200-300ms** | - |
| LLM 生成 | ~500-1500ms | 流式输出/模型选择 |
| **端到端总计** | **~700-1800ms** | - |

---

## 线程安全

RAGUtils 使用线程锁保护并发写入：

```python
class RAGUtils:
    _lock = threading.Lock()  # 类级别锁

    def process_document(self, ...):
        with RAGUtils._lock:  # 临界区
            # ... 文档处理逻辑
```

---

## 故障排除

### 常见问题

1. **Embedding 模型加载失败**
   - 检查网络：首次使用需下载模型
   - 手动下载：`huggingface-cli download sentence-transformers/all-MiniLM-L6-v2`

2. **Cross-Encoder 加载超时**
   - 首次加载需要下载模型（~100MB）
   - 检查 HuggingFace 连接性

3. **ChromaDB 锁错误**
   - 确保单进程访问 PersistentClient
   - 或切换到内存模式进行开发

4. **BM25 索引未构建**
   - 调用 `_build_bm25_index()` 手动构建
   - 或执行一次检索自动触发

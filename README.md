# SupportPilot

<div align="center">

![SupportPilot Banner](https://img.shields.io/badge/SupportPilot-AI%20Customer%20Support-0071e3?style=for-the-badge)

**基于 Flask + RAG 的智能客服系统 · Apple 风格现代化 UI**

[Features](#-功能特性) · [Screenshots](#-界面预览) · [Architecture](#-技术架构) · [Quick Start](#-快速开始)

</div>

---

## 📸 界面预览

### 登录页面

![Login Page](./docs/screenshots/login.png)

*简洁的登录界面，支持用户名密码认证*

### 注册页面

![Register Page](./docs/screenshots/register.png)

*用户注册页面，包含密码强度验证*

### 仪表盘首页

![Dashboard](./docs/screenshots/home.png)

*现代化仪表盘，展示会话统计和快捷操作*

### 上传页面

![Upload](./docs/screenshots/upload.png)

*文档上传向导，支持数据清洗和分块预览*

### 会话对话页面（Apple iMessage 风格）

![Conversation](./docs/screenshots/conversation-chat.png)

*iMessage 风格的对话界面，支持流畅的消息气泡和滚动体验*

---

## ✨ 功能特性

### Apple 风格设计系统

- **iMessage 灵感设计**: 对话气泡采用 Apple iMessage 风格，圆角 + 阴影
- **SF Pro 字体**: 使用 Apple 系统字体栈，呈现原生质感
- **流畅动画**: 消息进入/发送按钮/滚动到底部按钮均带流畅动画
- **固定式布局**: 头部和输入框固定，仅消息区域可滚动
- **玻璃拟态**: 半透明背景 + backdrop-filter 模糊效果

### 核心功能

| 功能模块 | 说明 |
|---------|------|
| 👤 用户管理 | 注册/登录/注销，密码强度验证，角色管理 |
| 💬 会话管理 | 创建/关闭/重开会话，标记需关注 |
| 🤖 智能客服 | RAG 检索 + Qwen LLM 生成，Cross-Encoder 重排序 |
| 📁 文档管理 | PDF/TXT/DOCX 上传，语义分块，Small-to-Big 检索 |
| 🎫 工单系统 | 人工介入触发，状态跟踪（open/pending/closed） |
| 📚 FAQ 管理 | AI 生成草稿，审核工作流，向量化同步 |


## 技术栈

- **后端框架**：Flask 3.0
- **数据库**：SQLite (开发) / PostgreSQL (生产)
- **认证**：Flask-Login
- **RAG 技术**：LangChain + Chroma + SentenceTransformer + SemanticChunker
- **Agentic RAG**: LangGraph 状态机编排
- **API**：Alibaba Qwen API
- **前端**：HTML 模板
- **生产服务器**：Gunicorn

## 项目结构

```
SupportPilot/
├── app/                 # 应用主包（重构后）
│   ├── __init__.py      # 应用工厂
│   ├── extensions.py    # Flask 扩展初始化
│   ├── config.py        # 配置管理
│   ├── utils.py         # 工具函数
│   ├── models/          # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py          # User 模型
│   │   ├── conversation.py  # Conversation 模型
│   │   ├── message.py       # Message 模型
│   │   └── document.py      # Document 模型
│   ├── auth/          # 认证蓝图
│   │   ├── __init__.py
│   │   └── routes.py      # 注册/登录/注销路由
│   ├── main/          # 主路由蓝图
│   │   ├── __init__.py
│   │   └── routes.py      # 首页/仪表盘路由
│   ├── conversation/  # 会话蓝图
│   │   ├── __init__.py
│   │   └── routes.py      # 会话管理路由
│   ├── document/    # 文档蓝图
│   │   ├── __init__.py
│   │   └── routes.py      # 文档上传/删除路由
│   └── api/         # API 蓝图
│       ├── __init__.py
│       └── routes.py      # REST API 端点
├── api/                 # API 客户端（保留）
│   └── qwen_api.py      # Alibaba Qwen API 客户端
├── rag/                 # RAG 相关
│   ├── core/            # 核心模块（Agentic RAG）
│   │   ├── tool.py          # 工具基类
│   │   ├── container.py     # 依赖注入容器
│   │   ├── config.py        # YAML 配置加载器
│   │   └── observability.py # 日志和指标采集
│   ├── tools/           # 检索工具（Agentic RAG）
│   │   ├── vector_tool.py     # 向量检索工具
│   │   ├── bm25_tool.py       # BM25 关键词检索
│   │   ├── filter_tool.py     # 元数据过滤工具
│   │   ├── ensemble_tool.py   # 多路召回融合 (RRF)
│   │   └── parent_store.py    # Small-to-Big 大块存储
│   ├── agents/          # Agent 模块（Agentic RAG）
│   │   ├── states.py          # Agent 状态定义
│   │   ├── router.py          # 查询路由器
│   │   ├── router_rules.py    # 规则匹配器
│   │   ├── router_classifier.py # ML 意图分类器
│   │   ├── retrieval_agent.py # LangGraph 状态机
│   │   └── nodes/             # 状态机节点
│   │       ├── query_understanding.py  # 查询理解
│   │       ├── planning.py             # 检索规划
│   │       ├── tool_execution.py       # 工具调用
│   │       └── synthesis.py            # 结果合成
│   ├── service.py         # RAG 服务兼容层
│   └── rag_utils.py       # 文档处理工具（保留用于 ingestion）
├── config/              # 配置文件
│   └── rag_config.yaml  # Agentic RAG 配置
├── templates/           # HTML 模板
│   ├── conversation.html
│   ├── login.html
│   ├── register.html
│   ├── tech_dashboard.html
│   ├── upload.html
│   └── user_dashboard.html
├── tests/               # 测试文件
│   ├── test_app.py      # 单元测试
│   └── test_chunking.py # 分块策略测试
├── wsgi.py              # WSGI 入口
├── app.py               # 兼容层（导入 app.create_app）
├── config.py            # 兼容层（导入 app.config）
├── models.py            # 兼容层（导入 app.models）
├── utils.py             # 工具函数（根模块导出）
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── start.sh
```

## 核心功能

### 1. 用户管理

- 用户注册/登录/注销
- 密码强度验证
- 角色管理（普通用户 / 技术支持）

### 2. 会话管理

- 创建新会话
- 查看会话历史
- 关闭/重新打开会话
- 标记需关注会话

### 3. 智能客服

- 基于 RAG 的智能问答
- 查询改写（Query Rewriter）
- 多路检索（向量 + BM25）
- Cross-Encoder 重排序
- Agentic RAG（LangGraph 状态机编排）

### 4. 文档管理

- 支持 PDF/TXT/DOCX 格式
- 智能分块（语义/句子/递归策略）
- 质量评分过滤
- 数据清洗可视化
- Small-to-Big 检索策略

### 5. 工单管理系统（Ticket Management）

- 工单状态跟踪（open/pending_human/closed）
- 对话轮次计数
- 人工介入触发（3 轮后显示按钮）
- 用户关闭工单功能

### 6. FAQ 管理与审核（FAQ Management & Review）

- AI 自动生成 FAQ 草稿
- 技术支持审核工作流（审核 → 编辑 → 确认 → 向量化）
- FAQ 管理后台（增删改查、批量操作）
- 版本历史记录
- 向量化进度提示
- ChromaDB 向量同步

---

## RAG 检索增强生成流程

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

### 阶段 1: 文档处理（上传时）

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
# API 调用示例
result = rag_utils.process_document(
    file_path='document.pdf',
    strategy='semantic',  # 推荐
    chunk_size=1500,      # 仅 sentence/recursive 策略使用
    chunk_overlap=300     # 仅 recursive 策略使用
)
```

**上传界面参数**：
- `strategy`: 分块策略选择 (`semantic`/`sentence`/`recursive`)
- `chunk_size`: 分块大小（仅 `sentence` 和 `recursive` 策略）
- `chunk_overlap`: 分块重叠（仅 `recursive` 策略）

### 阶段 2: 查询扩展

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

### 阶段 3: 混合检索

**代码**: `rag/rag_utils.py:_hybrid_search()`

| 检索类型 | 优势 | 权重 |
|----------|------|------|
| BM25 关键词检索 | 精确匹配（错误码、产品名） | α=0.5 |
| 向量语义检索 | 理解语义相似性 | 1-α=0.5 |

**RRF (Reciprocal Rank Fusion) 融合算法**:
```python
RRF Score = α / (rank_bm25 + 60) + (1-α) / (rank_vector + 60)
```

### 阶段 4: Cross-Encoder 重排序

**代码**: `rag/rag_utils.py:_rerank_with_cross_encoder()`

- 模型：`cross-encoder/ms-marco-MiniLM-L-6-v2`
- 作用：对粗排结果进行精细相关性评分
- 流程：召回 k×3 条 → 重排序 → 返回 top-k
- 延迟加载：首次使用时加载模型

### 阶段 5: LLM 生成回答

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

### 技术组件总览

| 组件 | 技术选型 | 作用 |
|------|----------|------|
| 向量数据库 | ChromaDB (PersistentClient) | 存储文档向量和元数据 |
| Embedding 模型 | sentence-transformers/all-MiniLM-L6-v2 | 384 维向量生成 |
| 重排序模型 | cross-encoder/ms-marco-MiniLM-L-6-v2 | 精细相关性打分 |
| 关键词检索 | BM25Okapi (rank_bm25) | 混合搜索组件 |
| 文本分块 | SemanticChunker (语义) / SentenceChunker (句子) / RecursiveCharacterTextSplitter (递归) | 智能文本切分，保持语义完整性 |
| PDF 解析 | pdfplumber | 布局感知文本提取 |
| LLM | Qwen-Turbo (阿里云) | 最终回答生成 |

### 性能特征

| 阶段 | 耗时 (预估) |
|------|-------------|
| 查询扩展 | ~1ms |
| BM25 检索 | ~10ms |
| 向量检索 | ~50ms |
| Cross-Encoder 重排序 | ~100-200ms |
| **检索总计** | **~200-300ms** |
| LLM 生成 | ~500-1500ms (取决于响应长度) |
| **端到端总计** | **~700-1800ms** |

### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| strategy | semantic | 分块策略：semantic(语义)、sentence(句子)、recursive(递归) |
| chunk_size | 1500 | 分块大小（字符，仅 recursive/sentence 策略） |
| chunk_overlap | 300 | 分块重叠（仅 recursive 策略） |
| similarity_threshold | 0.25 | 最小相似度阈值 |
| quality_threshold | 60 | 最低质量分数 |
| use_expansion | True | 启用查询扩展 |
| use_hybrid | False | 启用混合检索（需手动开启） |
| use_reranking | True | 启用 Cross-Encoder 重排序 |
| embedding_model | all-MiniLM-L6-v2 | 向量嵌入模型 |
| rerank_model | ms-marco-MiniLM-L-6-v2 | 重排序模型 |

### 核心特性

1. **智能分块**: 支持语义分块(SemanticChunker)、句子级分块、递归分块三种策略
2. **去重机制**: MD5 哈希 + 持久化存储，避免重复文档
3. **质量过滤**: 自动化质量评分，过滤低质量 chunk
4. **混合检索**: BM25(关键词) + 向量 (语义) + RRF 融合
5. **重排序**: Cross-Encoder 提升最终排序质量
6. **查询扩展**: 同义词替换提升召回率
7. **线程安全**: 使用 `threading.Lock` 保护并发写入
8. **错误处理**: 完善的异常处理和降级策略

## Agentic RAG 架构 (新一代检索系统)

### 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Query Router                               │
│  - Rules: keywords, patterns                                │
│  - ML: Logistic Regression (optional)                       │
│  - Modes: simple | agentic | auto                           │
└─────────────┬───────────────────────────────────────────────┘
              │
     ┌────────┴────────┐
     │                 │
     ▼                 ▼
┌─────────┐      ┌─────────────────────────────────────────┐
│ Simple  │      │           Agentic Path                  │
│ Path    │      │  LangGraph State Machine:               │
│ (vector │      │  query_understanding → planning →       │
│  search)│      │  tool_execution → synthesis             │
└─────────┘      └─────────────────────────────────────────┘
     │                            │
     └────────────┬───────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Retrieval Tools                                 │
│  - vector_search: Vector similarity search                  │
│  - bm25_search: BM25 keyword search                         │
│  - metadata_filter: Metadata filtering                      │
│  - ensemble_retrieval: RRF fusion                           │
└─────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│           Small-to-Big Retrieval                             │
│  - Small chunks (400 chars) indexed in ChromaDB             │
│  - Large chunks (2000 chars) stored in ParentDocumentStore  │
│  - Search small → return large for complete context         │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 位置 | 功能 |
|------|------|------|
| Query Router | `rag/agents/router.py` | 查询路由（simple/agentic/auto） |
| Retrieval Agent | `rag/agents/retrieval_agent.py` | LangGraph 状态机编排 |
| Query Understanding | `rag/agents/nodes/query_understanding.py` | 查询改写（代词解析、省略补全） |
| Planning | `rag/agents/nodes/planning.py` | 检索规划、工具选择 |
| Tool Execution | `rag/agents/nodes/tool_execution.py` | 工具调用、结果收集 |
| Synthesis | `rag/agents/nodes/synthesis.py` | 生成最终答案 |

### 使用示例

```python
# 简单检索（自动路由）
from rag.service import rag_service

results = rag_service.retrieve(
    query="高并发的原则是什么",
    k=5,
    use_small_to_big=True
)

# Agentic 检索（多步推理）
from rag.agents.retrieval_agent import retrieval_agent

result = retrieval_agent.run(
    query="对比 A 和 B 的异同",
    session_id="conversation_123"
)
```

详细架构文档请参考：[rag/README.md](rag/README.md)

## 快速开始

### 1. 安装依赖

```bash
# 生产依赖
pip install -r requirements.txt

# 开发依赖（包含测试工具）
pip install -r requirements-dev.txt
```

### 2. 配置环境变量

复制环境变量示例文件并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下变量：

```bash
SECRET_KEY=your-secret-key-here
QWEN_API_KEY=your-qwen-api-key-here
DATABASE_URL=sqlite:///app.db
FLASK_DEBUG=true  # 开发环境设为 true，生产环境设为 false
```

### 3. 启动应用

**开发模式：**

```bash
python app.py
# 或
./start.sh
```

**生产模式：**

```bash
FLASK_ENV=production gunicorn -c gunicorn_config.py wsgi:app
```

### 4. 访问应用

- 打开浏览器，访问 `http://localhost:5000`
- 注册新用户账号
- 或使用默认技术支持账号登录（仅开发环境）：
  - 用户名：`tech_support`
  - 密码：启动时在日志中显示

## API 文档

### 认证相关

- `POST /register`：注册新用户
- `POST /login`：用户登录
- `GET /logout`：用户注销

### 会话相关

- `POST /conversation/new`：创建新会话
- `GET /conversation/<int:conversation_id>`：查看会话详情
- `POST /conversation/<int:conversation_id>/send`：发送消息
- `POST /conversation/<int:conversation_id>/close`：关闭会话（技术支持）
- `POST /conversation/<int:conversation_id>/reopen`：重新打开会话（技术支持）
- `POST /conversation/<int:conversation_id>/mark-attention`：标记为需要关注（技术支持）

### 文档相关

- `GET /upload`：查看上传页面
- `POST /upload`：上传文档

### 工单管理 (Ticket Management)

新增的工单管理功能，支持人工介入和工单状态跟踪。

- `GET /api/ticket/<int:session_id>/status`
  - 获取工单状态和对话轮数
  - 返回：`{ success: true, status: 'open'|'pending_human'|'closed', round_count: number, should_show_handoff: boolean }`

- `POST /api/ticket/<int:session_id>/handoff`
  - 请求人工介入（用户点击"需要人工介入"按钮时调用）
  - 返回：`{ success: true, message: '已请求人工介入...' }`

- `POST /api/ticket/<int:session_id>/close`
  - 关闭工单（用户或技术支持关闭会话时调用）
  - Request Body: `{ generate_faq: boolean }` (可选，是否生成 FAQ)
  - 返回：`{ success: true, message: '工单已关闭' }`

### FAQ 管理 (FAQ Management)

FAQ 管理后台和审核工作流 API。

#### 审核工作流

- `POST /api/faq/generate`
  - 从对话生成 FAQ 草稿
  - Request Body: `{ session_id: number }`
  - 返回：`{ success: true, faq: { id, question, answer, category, status } }`

- `POST /api/faq/<int:faq_id>/update`
  - 更新 FAQ 草稿（技术支持审核时编辑）
  - Request Body: `{ question: string, answer: string, category: string, change_reason: string }`
  - 返回：`{ success: true }`

- `POST /api/faq/<int:faq_id>/confirm`
  - 确认 FAQ 并向量化到知识库
  - 返回：`{ success: true, message: 'FAQ 已确认并添加到知识库', progress: 100 }`

- `POST /api/faq/<int:faq_id>/reject`
  - 拒绝 FAQ 草稿
  - Request Body: `{ reason: string }` (可选)
  - 返回：`{ success: true, message: 'FAQ 已拒绝' }`

#### CRUD 操作

- `GET /api/faq`
  - 获取 FAQ 列表（支持分页和筛选）
  - Query Params: `status`, `category`, `search`, `page`, `per_page`
  - 返回：`{ success: true, items: [...], pagination: {...} }`

- `GET /api/faq/<int:faq_id>`
  - 获取单个 FAQ 详情
  - 返回：`{ success: true, faq: {...} }`

- `POST /api/faq`
  - 创建新 FAQ
  - Request Body: `{ question: string, answer: string, category: string, status: 'draft'|'confirmed' }`
  - 返回：`{ success: true, faq: {...} }`

- `PUT /api/faq/<int:faq_id>`
  - 更新 FAQ
  - Request Body: `{ question: string, answer: string, category: string, change_reason: string }`
  - 返回：`{ success: true }`

- `DELETE /api/faq/<int:faq_id>`
  - 删除 FAQ（软删除）
  - 返回：`{ success: true, message: 'FAQ 已删除' }`

- `POST /api/faq/bulk-delete`
  - 批量删除 FAQ
  - Request Body: `{ faq_ids: number[] }`
  - 返回：`{ success: true, result: { success: number, failed: number } }`

#### 版本历史

- `GET /api/faq/<int:faq_id>/versions`
  - 获取 FAQ 版本历史
  - 返回：`{ success: true, versions: [{ id, question, answer, change_reason, changed_by, created_at }] }`

## 测试

运行单元测试：

```bash
# 基础测试
pytest tests/test_app.py -v

# 分块策略测试
pytest tests/test_chunking.py -v

# 带覆盖率报告
pytest --cov=. --cov-report=html
```

## 安全特性

- **CSRF 保护**：所有表单都启用了 CSRF Token
- **XSS 防护**：用户输入经过 HTML 转义
- **密码强度验证**：强制要求 8+ 字符，包含大小写字母和数字
- **安全 Cookie**：生产环境启用 HttpOnly 和 Secure 标志
- **输入长度限制**：消息内容限制 10000 字符

## 日志

应用日志输出到：
- 控制台
- `logs/app.log`（轮转日志，最大 10MB，保留 10 个备份）

Gunicorn 日志（生产环境）：
- `logs/gunicorn_access.log`
- `logs/gunicorn_error.log`

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| SECRET_KEY | Flask 密钥 | 随机生成 |
| QWEN_API_KEY | 阿里云 Qwen API 密钥 | 必须设置 |
| DATABASE_URL | 数据库连接 URL | sqlite:///app.db |
| FLASK_ENV | 运行环境 | development |
| FLASK_DEBUG | 调试模式 | true |
| GUNICORN_WORKERS | Gunicorn 工作进程数 | CPU 核心数*2+1 |
| UPLOAD_FOLDER | 上传文件目录 | uploads |

## 生产部署建议

1. 使用 PostgreSQL 或 MySQL 替代 SQLite
2. 配置 Nginx 作为反向代理
3. 使用 HTTPS（配置 SSL 证书）
4. 设置强 SECRET_KEY
5. 关闭 DEBUG 模式
6. 配置日志轮转
7. 使用环境变量管理敏感信息

## 故障排除

### QWEN_API_KEY 错误

确保已设置正确的 API 密钥：
```bash
export QWEN_API_KEY=your-actual-key
```

### 数据库锁定

如果使用 SQLite 遇到锁定问题，考虑迁移到 PostgreSQL：
```bash
export DATABASE_URL=postgresql://user:password@localhost/supportpilot
```

## 技术支持

如果您在使用过程中遇到问题，请查看日志文件获取详细错误信息。

## 许可证

本项目采用 MIT 许可证。

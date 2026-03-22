# SupportPilot

## 项目简介

SupportPilot 是一个基于 Flask 的智能客户支持系统，使用了 RAG (Retrieval-Augmented Generation) 技术和 LLM 来实现智能客服功能。该系统支持用户与 AI 助手进行对话，当对话需要人工介入时，技术支持人员可以接管对话。

## 技术栈

- **后端框架**：Flask 3.0
- **数据库**：SQLite (开发) / PostgreSQL (生产)
- **认证**：Flask-Login
- **RAG 技术**：LangChain + Chroma + SentenceTransformer
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
│   └── rag_utils.py     # RAG 功能实现
├── templates/           # HTML 模板
│   ├── conversation.html
│   ├── login.html
│   ├── register.html
│   ├── tech_dashboard.html
│   ├── upload.html
│   └── user_dashboard.html
├── tests/               # 测试文件
│   └── test_app.py      # 单元测试
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

### 2. 会话管理

### 3. 智能客服

### 4. 文档管理

### 5. 技术支持功能

---

## RAG 检索增强生成流程

### 架构图

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│  用户上传   │ ──► │  文档分块    │ ──► │  向量化      │ ──► │  Chroma DB  │
│  PDF/TXT/DOCX│     │  1500/300    │     │  Embedding   │     │   索引      │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
                                                                    │
                                                                    ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│  LLM 生成   │ ◄── │  重排序      │ ◄── │  混合检索   │ ◄── │  用户提问   │
│  回答       │     │  Cross-Encoder│     │  BM25+ 向量   │     │  查询扩展   │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
```

### 阶段 1: 文档处理（上传时）

**代码**: `rag/rag_utils.py:process_document()`

| 步骤 | 说明 | 配置 |
|------|------|------|
| 文件加载 | 支持 PDF/TXT/DOCX | PyPDFLoader, TextLoader, Docx2txtLoader |
| 文档分块 | 按字符切分 | chunk_size=1500, chunk_overlap=300 |
| 去重处理 | MD5 哈希去重 | 防止重复文档 |
| 向量化 | SentenceTransformer 嵌入 | all-MiniLM-L6-v2 |
| 存储 | Chroma DB 持久化 | ./chroma_db |

### 阶段 2: 查询处理（用户提问时）

**代码**: `rag/rag_utils.py:_expand_query()`

查询扩展 - 同义词替换提升召回率:
- `account` → `user`, `profile`, `login`
- `password` → `credential`, `authentication`, `reset`
- `error` → `issue`, `problem`, `bug`, `failure`
- `payment` → `billing`, `invoice`, `transaction`
- `subscription` → `plan`, `pricing`, `renewal`, `upgrade`

示例：用户问 `"reset password"` → 同时搜索 `["change credential", "reset authentication"]`

### 阶段 3: 混合检索

**代码**: `rag/rag_utils.py:_hybrid_search()`

| 检索类型 | 优势 | 权重 |
|----------|------|------|
| BM25 关键词检索 | 精确匹配（错误码、产品名） | α=0.5 |
| 向量语义检索 | 理解语义相似性 | 1-α=0.5 |

**RRF 融合算法**:
```
RRF Score = α / (rank_bm25 + 60) + (1-α) / (rank_vector + 60)
```

### 阶段 4: Cross-Encoder 重排序

**代码**: `rag/rag_utils.py:_rerank_with_cross_encoder()`

- 模型：`cross-encoder/ms-marco-MiniLM-L-6-v2`
- 作用：对粗排结果进行精细相关性评分
- 流程：召回 9 条 → 重排序 → 返回 top 3

### 阶段 5: LLM 生成回答

**代码**: `api/qwen_api.py:generate_response()`

- API：Alibaba Qwen (`qwen-turbo`)
- Prompt 构建：相关知识 + 用户问题
- 温度：0.7
- 最大 token：1024

### 性能特征

| 阶段 | 耗时 |
|------|------|
| 查询扩展 | ~1ms |
| BM25 检索 | ~10ms |
| 向量检索 | ~50ms |
| Cross-Encoder | ~100-200ms |
| **总计** | **~200-300ms** |

### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| chunk_size | 1500 | 分块大小（字符） |
| chunk_overlap | 300 | 分块重叠 |
| similarity_threshold | 0.25 | 最小相似度阈值 |
| use_expansion | True | 启用查询扩展 |
| use_hybrid | False | 启用混合检索（需手动开启） |
| use_reranking | True | 启用 Cross-Encoder 重排序 |

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

## 测试

运行单元测试：

```bash
pytest tests/test_app.py -v

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

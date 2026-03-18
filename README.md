# SupportPilot

## 项目简介

SupportPilot 是一个基于 Flask 的智能客户支持系统，使用了 RAG (Retrieval-Augmented Generation) 技术和 LLM 来实现智能客服功能。该系统支持用户与 AI 助手进行对话，当对话需要人工介入时，技术支持人员可以接管对话。

## 技术栈

- **后端框架**：Flask
- **数据库**：SQLite
- **认证**：Flask-Login
- **RAG 技术**：LangChain
- **向量存储**：TF-IDF
- **API**：Alibaba Qwen API
- **前端**：HTML 模板

## 项目结构

```
SupportPilot/
├── api/                 # API 相关文件
│   └── qwen_api.py      # 调用 Alibaba Qwen API
├── instance/            # 实例目录
│   └── app.db           # SQLite 数据库文件
├── rag/                 # RAG 相关文件
│   └── rag_utils.py     # RAG 功能实现
├── templates/           # HTML 模板
│   ├── conversation.html     # 会话页面
│   ├── login.html            # 登录页面
│   ├── register.html         # 注册页面
│   ├── tech_dashboard.html   # 技术支持仪表盘
│   ├── upload.html           # 文件上传页面
│   └── user_dashboard.html   # 用户仪表盘
├── uploads/             # 上传文件目录
├── app.py               # 主应用文件
├── config.py            # 配置文件
├── models.py            # 数据模型
├── routes.py            # 路由文件
└── requirements.txt     # 依赖文件
```

## 核心功能

### 1. 用户管理
- 用户注册和登录
- 密码安全存储（使用 PBKDF2 哈希）
- 基于角色的访问控制（用户和技术支持）

### 2. 会话管理
- 创建新会话
- 查看会话历史
- 会话状态跟踪（active、needs_attention、closed）

### 3. 智能客服
- 用户发送消息后，系统使用 RAG 检索相关文档信息
- 系统使用 Alibaba Qwen API 生成智能回复
- 当消息数达到 3 条时，会话自动标记为 "needs_attention"，需要技术支持介入

### 4. 文档管理
- 技术支持可以上传文档（支持 PDF、TXT、DOCX）
- 系统自动处理文档并添加到 RAG 知识库
- 文档内容用于增强 AI 回复的准确性
- RAG 数据持久化存储（使用 pickle 文件）

### 5. 技术支持功能
- 技术支持仪表盘，查看所有会话
- 特别关注需要人工介入的会话
- 技术支持可以直接回复用户消息

## 工作流程

1. **用户注册并登录**：用户创建账号并登录系统
2. **创建新会话**：用户在仪表盘创建新的客服会话
3. **发送消息**：用户向 AI 助手发送问题
4. **AI 回复**：系统使用 RAG 检索相关文档，然后通过 Qwen API 生成回复
5. **技术支持介入**：当会话需要人工介入时，技术支持可以查看并回复
6. **文档上传**：技术支持可以上传相关文档，增强 AI 知识库

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在 `config.py` 文件中配置以下 API 密钥：

- `QWEN_API_KEY`：Alibaba Qwen API 密钥（项目实际使用的 API）

### 3. 启动应用

```bash
python app.py
```

### 4. 访问应用

- 打开浏览器，访问 `http://localhost:5000`
- 注册新用户账号
- 或使用默认技术支持账号登录：
  - 用户名：`tech_support`
  - 密码：`password123`

## API 文档

### 认证相关

- `POST /register`：注册新用户
- `POST /login`：用户登录
- `GET /logout`：用户注销

### 会话相关

- `POST /conversation/new`：创建新会话
- `GET /conversation/<int:conversation_id>`：查看会话详情
- `POST /conversation/<int:conversation_id>/send`：发送消息

### 文档相关

- `GET /upload`：查看上传页面
- `POST /upload`：上传文档

## 技术支持

如果您在使用过程中遇到问题，请联系技术支持团队。

## 许可证

本项目采用 MIT 许可证。


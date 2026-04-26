# SupportPilot

<div align="center">

![SupportPilot Banner](https://img.shields.io/badge/SupportPilot-AI%20Customer%20Support-0071e3?style=for-the-badge)

**基于 Flask + RAG 的智能客服系统 · Apple 风格现代化 UI**

[界面预览](#-界面预览) · [快速开始](#-快速开始) · [架构文档](docs/RAG_ARCHITECTURE.md) · [API 文档](docs/API.md) · [部署指南](docs/DEPLOYMENT.md)

</div>

---

## 📸 界面预览

| 登录 | 注册 | 仪表盘 |
|:---:|:---:|:---:|
| ![Login](./docs/screenshots/login.png) | ![Register](./docs/screenshots/register.png) | ![Dashboard](./docs/screenshots/home.png) |

| 上传 | 对话 |
|:---:|:---:|
| ![Upload](./docs/screenshots/upload.png) | ![Conversation](./docs/screenshots/conversation-chat.png) |

---

## ✨ 核心特性

### Apple 风格设计
- 🎨 **iMessage 风格对话气泡** - 圆角 + 阴影设计
- 📱 **固定式布局** - 头部和输入框固定，仅消息区域滚动
- ✨ **流畅动画** - 消息进入/发送/滚动按钮均带动画
- ️ **玻璃拟态** - 半透明背景 + backdrop-filter 模糊

### 智能客服
- 🤖 **RAG 检索增强生成** - 基于向量检索 + LLM 的精准回答
- 📚 **Agentic RAG** - LangGraph 状态机编排的多步推理检索
- 🔍 **Small-to-Big 检索** - 小块索引，大块返回，兼顾精度与上下文
- 🔁 **混合检索** - BM25 + 向量 + RRF 融合 + Cross-Encoder 重排序

### 工单与 FAQ
- 🎫 **工单系统** - 人工介入触发，状态跟踪 (open/pending/closed)
- 📝 **FAQ 审核工作流** - AI 生成草稿 → 技术支持审核 → 向量化同步

---

## 🏗️ 技术架构

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Query Router                               │
│         (Rules + ML Intent Classification)                   │
└─────────────┬───────────────────────────────────────────────┘
              │
     ┌────────┴────────┐
     │                 │
     ▼                 ▼
┌─────────┐      ┌─────────────────────────────────────────┐
│ Simple  │      │    Agentic (LangGraph State Machine)    │
│ Vector  │      │  query → plan → execute → synthesize   │
└─────────┘      └─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Retrieval Tools                                 │
│  vector_search | bm25_search | metadata_filter | ensemble   │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│           Small-to-Big Retrieval                             │
│  400 字符小块索引 → 2000 字符大块返回                          │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Flask 3.0 + SQLite/PostgreSQL |
| RAG | LangChain + Chroma + LangGraph |
| Embedding | all-MiniLM-L6-v2 (384 维) |
| 重排序 | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| LLM | Alibaba Qwen (qwen-turbo) |
| 前端 | HTML 模板 + CSS 定制 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 设置 QWEN_API_KEY 等
```

### 3. 启动应用

```bash
python app.py
# 访问 http://localhost:5005
```

详细部署指南请参考 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## 📁 项目结构

```
SupportPilot/
├── app/                 # 应用主包
│   ├── auth/           # 认证蓝图
│   ├── main/           # 主路由蓝图
│   ├── conversation/   # 会话蓝图
│   ├── document/       # 文档蓝图
│   └── api/            # API 蓝图
├── rag/                 # RAG 核心模块
│   ├── core/           # Agentic RAG 核心
│   ├── tools/          # 检索工具
│   ├── agents/         # LangGraph Agent
│   └── config/         # 配置文件
├── templates/           # HTML 模板
└── docs/                # 文档
    ├── RAG_ARCHITECTURE.md
    ├── API.md
    └── DEPLOYMENT.md
```

---

## 📚 文档导航

| 文档 | 说明 |
|------|------|
| [RAG 架构](docs/RAG_ARCHITECTURE.md) | 检索增强生成详细流程、分块策略、混合检索、重排序 |
| [API 文档](docs/API.md) | 认证、会话、文档、工单、FAQ 等 API 接口 |
| [部署指南](docs/DEPLOYMENT.md) | 安装、配置、生产部署建议、故障排除 |

---

## 📝 许可证

MIT License

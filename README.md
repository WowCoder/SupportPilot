# SupportPilot

<div align="center">

![SupportPilot Banner](https://img.shields.io/badge/SupportPilot-AI%20Customer%20Support-0071e3?style=for-the-badge)

**基于 Flask + RAG 的智能客服系统 · Apple 风格现代化 UI**

[界面预览](#-界面预览) · [快速开始](#-快速开始) · [项目结构](#-项目结构)

</div>

---

## 📸 界面预览

| 登录 | 注册 | 用户仪表盘 |
|:---:|:---:|:---:|
| ![Login](./docs/screenshots/login.png) | ![Register](./docs/screenshots/register.png) | ![Dashboard](./docs/screenshots/home.png) |

| 技术支持仪表盘 | 会话对话 | 文档上传 |
|:---:|:---:|:---:|
| ![Tech Dashboard](./docs/screenshots/tech-dashboard.png) | ![Conversation](./docs/screenshots/conversation-chat.png) | ![Upload](./docs/screenshots/upload.png) |

| FAQ 管理 |
|:---:|
| ![FAQ](./docs/screenshots/faq-manage.png) |

---

## ✨ 核心特性

### Apple 风格设计
- 🎨 **iMessage 风格对话气泡** - 圆角 + 阴影设计
- 📱 **固定式布局** - 头部和输入框固定，仅消息区域滚动
- ✨ **流畅动画** - 消息进入/发送/滚动按钮均带动画
- ️ **玻璃拟态** - 半透明背景 + backdrop-filter 模糊

### 智能客服
- 🤖 **RAG 检索增强生成** - 基于向量检索 + LLM 的精准回答
- 📚 **Agentic RAG (自我纠正)** - 9 节点 LangGraph 状态机，LLM 驱动工具选择与查询分解，相关性门控 + 忠实度验证，支持自动回环纠正
- 🔍 **Small-to-Big 检索** - 小块索引，大块返回，兼顾精度与上下文
- 🔁 **混合检索** - BM25 + 向量 + RRF 融合，BM25 自动从 ChromaDB 构建索引

### 工单与 FAQ
- 🎫 **工单系统** - 人工介入触发，状态跟踪 (open/pending/closed)
- 📝 **FAQ 审核工作流** - AI 生成草稿 → 技术支持审核 → 向量化同步

---

## 🏗️ 技术架构

### 系统架构

```
                          ┌──────────────────────────────────────────────────┐
                          │        Agentic RAG (9-Node State Machine)        │
                          │                                                  │
   User Query             │  ┌──────────────┐    ┌──────────────┐           │
      │                   │  │   query      │    │    tool      │           │
      ▼                   │  │  understand  │    │  selection   │           │
┌──────────────┐          │  └──────┬───────┘    └──────┬───────┘           │
│    Query     │          │         │                    │                   │
│   Router     │          │         ▼                    ▼                   │
│ (Rules+LLM)  │          │  ┌──────────────┐    ┌──────────────┐           │
└──────┬───────┘          │  │   query      │    │    tool      │           │
       │                  │  │ decompose    │    │  execution   │           │
  ┌────┴────┐             │  └──────┬───────┘    └──────┬───────┘           │
  │         │             │         │                    │                   │
  ▼         ▼             │         │                    ▼                   │
┌─────┐ ┌─────────┐       │  ┌──────┴──────────────────────┐                │
│Simple│ │Agentic  │       │  │       tool_selection        │                │
│Vector│ │ Path ───┼───────┼─►│    (LLM-driven, per sub-Q)  │                │
└─────┘ └─────────┘       │  └─────────────┬───────────────┘                │
                          │                │                                  │
                          │                ▼                                  │
                          │  ┌────────────────────────────┐                  │
                          │  │      relevance_check       │                  │
                          │  │  ┌──────┐     ┌──────────┐ │                  │
                          │  │  │ PASS │     │  FAIL    │ │                  │
                          │  │  └──┬───┘     └────┬─────┘ │                  │
                          │  └─────┼───────────────┼───────┘                  │
                          │        │               │                          │
                          │        ▼               ▼                          │
                          │  ┌──────────────┐ ┌────────────┐                │
                          │  │   result     │ │   query    │                │
                          │  │ aggregation  │ │  refiner   │                │
                          │  └──────┬───────┘ └─────┬──────┘                │
                          │         │               │                         │
                          │         │               └───────┐                │
                          │         ▼                       │                │
                          │  ┌──────────────┐              │                │
                          │  │   answer     │              │                │
                          │  │ generation   │              │                │
                          │  └──────┬───────┘              │                │
                          │         │                      │                │
                          │         ▼                      │                │
                          │  ┌──────────────┐              │                │
                          │  │ faithfulness │              │                │
                          │  │    check     │              │                │
                          │  └──┬───────┬───┘              │                │
                          │     │       │                  │                │
                          │  [PASS] [FAIL]   ◄─────────────┘                │
                          │     │       │    (re-retrieve)                   │
                          │     ▼       ▼                                    │
                          │    END   query_refiner                           │
                          └──────────────────────────────────────────────────┘

   Retrieval Tools: vector_search | bm25_search | metadata_filter | ensemble_retrieval
   Small-to-Big: 400 char child chunks → 2000 char parent chunks
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Flask 3.0 + SQLite/PostgreSQL |
| RAG | LangChain + ChromaDB + LangGraph |
| Embedding | all-MiniLM-L6-v2 (384 维) |
| 检索策略 | Small-to-Big + Hybrid (Vector + BM25) + RRF 融合 |
| Agent | LangGraph 9-节点状态机 + 自我纠正回路 |
| 质量保障 | 相关性门控 + 忠实度验证 + 查询改写回环 |
| LLM | 可配置 (DeepSeek / Qwen / OpenAI 兼容 / Anthropic 兼容) |
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
# 编辑 .env 设置 LLM_API_KEY 等
```

### 3. 启动应用

```bash
bash start.sh
# 访问 http://localhost:5050 （macOS 如 5000 端口冲突，手动指定：python -m flask --app wsgi:app run --debug --port 5050）
```


---

## 📁 项目结构

```
SupportPilot/
├── app/                 # Flask 应用
│   ├── auth/           # 认证蓝图
│   ├── main/           # 主路由蓝图
│   ├── conversation/   # 会话蓝图
│   ├── document/       # 文档蓝图
│   ├── api/            # API 蓝图
│   ├── services/       # 业务逻辑层
│   └── models/         # 数据模型
├── rag/                 # RAG 核心
│   ├── offline/       # 离线管道（文档→索引）
│   ├── online/        # 在线管道（查询→答案）
│   │   ├── pipeline/   # LangGraph 状态机
│   │   ├── retrievers/ # 检索器（向量/BM25/混合）
│   │   ├── rerankers/  # 重排序器
│   │   └── generators/ # 答案生成器
│   └── utils/         # 通用工具
├── evaluation/          # 评估模块（RAGAS）
├── llm/                 # LLM 客户端
├── scripts/             # 运维脚本
│   └── migrations/     # 数据迁移
└── templates/           # HTML 模板
```

---

---

## 📝 许可证

MIT License

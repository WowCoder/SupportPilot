## 1. 项目准备

- [x] 1.1 添加 langgraph 依赖到 requirements.txt
- [x] 1.2 创建新的目录结构：rag/core/, rag/tools/, rag/agents/, rag/utils/
- [x] 1.3 创建配置文件模板 config/rag_config.yaml

## 2. 核心模块实现

- [x] 2.1 实现工具基类 rag/core/tool.py（BaseTool 抽象类）
- [x] 2.2 实现依赖注入容器 rag/core/container.py
- [x] 2.3 实现配置加载器 rag/core/config.py
- [x] 2.4 实现日志和指标采集工具 rag/core/observability.py

## 3. 检索工具实现

- [x] 3.1 实现向量检索工具 rag/tools/vector_tool.py（支持 Small-to-Big 策略）
- [x] 3.2 实现关键词检索工具 rag/tools/bm25_tool.py
- [x] 3.3 实现元数据过滤工具 rag/tools/filter_tool.py
- [x] 3.4 实现多路召回融合工具 rag/tools/ensemble_tool.py
- [x] 3.5 迁移 parent_store.py 到 rag/tools/parent_store.py（Small-to-Big 大块存储）
- [x] 3.6 编写所有工具的单元测试

## 4. 查询路由器实现

- [x] 4.1 实现关键词规则匹配器 rag/agents/router_rules.py
- [x] 4.2 实现查询意图分类器 rag/agents/router_classifier.py
- [x] 4.3 实现路由分发器 rag/agents/router.py
- [x] 4.4 编写路由器单元测试

## 5. Agentic RAG 引擎实现

- [x] 5.1 定义 Agent 状态和事件 rag/agents/states.py
- [x] 5.2 实现查询理解节点 rag/agents/nodes/query_understanding.py（整合 QueryRewriter 功能）
- [x] 5.3 实现检索规划节点 rag/agents/nodes/planning.py
- [x] 5.4 实现工具调用节点 rag/agents/nodes/tool_execution.py
- [x] 5.5 实现结果合成节点 rag/agents/nodes/synthesis.py
- [x] 5.6 使用 LangGraph 编排状态机 rag/agents/retrieval_agent.py
- [x] 5.7 实现超时保护和迭代限制
- [x] 5.8 编写 Agent 集成测试

## 6. 代码迁移和清理

- [x] 6.1 迁移 RAGUtils 功能到新架构
- [x] 6.2 更新 app/api/routes.py 使用新 Agent
- [x] 6.3 删除旧代码：rag/rag_utils.py
- [x] 6.4 迁移 parent_store.py 到 rag/tools/parent_store.py
- [x] 6.5 聊天记忆系统保持独立，仅添加 Agent 集成接口
- [x] 6.6 更新 wsgi.py 加载新配置
- [x] 6.7 删除 QueryRewriter 相关旧代码（功能已整合到 query_understanding）

## 7. 测试验证

- [x] 7.1 运行测试套件验证功能
- [x] 7.2 测试简单查询检索
- [x] 7.3 测试复杂查询 Agentic RAG 路径
- [x] 7.4 性能和延迟基准测试

## 8. 文档和清理

- [x] 8.1 编写架构文档 rag/README.md
- [ ] 8.2 编写工具使用示例 docs/examples/
- [x] 8.3 更新 CLAUDE.md 说明新架构
- [x] 8.4 更新 README.md 项目说明
- [x] 8.5 清理临时文件和调试代码

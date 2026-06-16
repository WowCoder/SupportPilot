## ADDED Requirements

### Requirement: Dashboard 页面入口
仅技术支持角色 SHALL 能访问 `/rag-dashboard` 页面，普通用户访问 SHALL 重定向回首页。

#### Scenario: 权限控制
- **WHEN** 普通用户访问 `/rag-dashboard`
- **THEN** MUST 重定向到首页并显示权限不足提示

### Requirement: Dashboard 整体布局
Dashboard SHALL 使用 topnav + page-content 布局，顶部显示统计卡片区（反馈正负比、检索总数、平均相似度、LLM-Judge 均分），下方显示检索日志列表。

#### Scenario: 统计卡片
- **WHEN** 技术支持访问 Dashboard
- **THEN** MUST 显示 4 个统计卡片：
  - 总检索次数（当日/总计）
  - 正反馈率（👍 / 总反馈 百分比）
  - 平均 Top-1 相似度
  - LLM-Judge 均分（如已评估）
- **THEN** 卡片数值 MUST 从 API 实时加载

### Requirement: 检索日志列表
Dashboard 主体 SHALL 为检索日志列表（data-table），每行显示查询、结果数、top-1 相似度（颜色区分）、Judge 评分、耗时、时间。支持点击行展开完整检索过程。

#### Scenario: 日志列表展开详情
- **WHEN** 技术支持点击某条日志行
- **THEN** 该行 MUST 展开显示：
  - 原始查询全文
  - 路由方式（agentic/simple）
  - 每条检索结果的完整内容、相似度分（颜色高亮）、来源文件
  - LLM-Judge 三维评分（如已评估）+ "重新评分" 按钮
  - 如果该检索关联了用户反馈，显示 👍 或 👎

#### Scenario: 日志列表筛选
- **WHEN** 技术支持使用筛选器
- **THEN** MUST 支持按路由方式（全部/agentic/simple）和最低相似度过滤
- **THEN** MUST 支持搜索查询关键词

### Requirement: 低质量查询高亮
Dashboard SHALL 在列表中高亮 Top-1 相似度 < 0.3 或 Judge 均分 < 3 的低质量检索记录，方便技术支持快速定位问题。

#### Scenario: 低质量标记
- **WHEN** top-1 相似度 < 0.3 或 judge 均分 < 3
- **THEN** 该行 MUST 以红色左边框或红色背景标记

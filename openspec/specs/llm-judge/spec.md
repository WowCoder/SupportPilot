## ADDED Requirements

### Requirement: LLM-as-Judge 自动评分
系统 SHALL 支持用 LLM 对检索结果进行三维度评分：相关性（relevance）、完整性（completeness）、噪声（noise），每个维度 1-5 分。

#### Scenario: Judge 评分触发
- **WHEN** 技术支持在 Dashboard 点击某条日志的 "评估" 按钮（或自动触发）
- **THEN** 系统 MUST 将查询 + 所有检索到的 chunk 内容拼成 prompt 发送给 LLM
- **THEN** LLM MUST 返回包含 `relevance`、`completeness`、`noise` 三个分数的 JSON
- **THEN** 评分 MUST 写入 `rag_retrieval_logs` 的 `judge_score` 和 `judge_reason` 字段

#### Scenario: Judge prompt 结构
- **WHEN** Judge 被调用
- **THEN** prompt MUST 包含：原始查询、检索到的所有 chunk 内容（编号）、评分维度说明、输出格式要求（JSON）
- **THEN** prompt MUST 要求 LLM 对每个维度给出 1-5 分 + 一句话理由

#### Scenario: Judge 评分容错
- **WHEN** LLM 返回格式无法解析
- **THEN** 系统 MUST 记录 `judge_score = null` 和 `judge_reason = "评分失败：{原始响应截断}"`，NOT 抛出异常

### Requirement: Judge 评分展示
每项评分 SHALL 以颜色条展示：5 = 绿色、3-4 = 橙色、1-2 = 红色，附带简短理由。

#### Scenario: 评分可视化
- **WHEN** 某条日志有 LLM-Judge 评分
- **THEN** Dashboard 日志详情 MUST 显示三个维度的分数（带颜色条）+ 理由文字
- **THEN** 无评分时 MUST 显示 "未评估" + "立即评估" 按钮

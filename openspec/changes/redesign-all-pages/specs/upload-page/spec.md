## ADDED Requirements

### Requirement: Upload 页面布局
文档上传页面 SHALL 使用 topnav + `.upload-shell` 布局（最大宽度 720px 仅适用于简单模式），包含已上传文档统计卡片、上传向导（4 步骤）、检索测试区、已上传文档列表。

#### Scenario: 页面整体结构
- **WHEN** 技术支持人员访问上传页面
- **THEN** 页面 MUST 显示标题 "上传知识库文档"
- **THEN** 页面 MUST 包含统计卡片区（已上传文档数、知识库片段数）

### Requirement: 四步骤上传向导
上传流程 SHALL 使用 4 步骤向导（Wizard），含步骤指示器（step-indicator），支持前进/后退/跳过。

#### Scenario: 步骤指示器展示
- **WHEN** 页面加载
- **THEN** 步骤指示器 MUST 显示 4 个步骤：选择文档 → 数据清洗 → 分块设置 → 完成上传
- **THEN** 当前步骤 MUST 高亮（active），已完成步骤 MUST 标记（completed）
- **THEN** 步骤间连线 MUST 显示进度

#### Scenario: 步骤导航
- **WHEN** 用户点击 "下一步" 按钮
- **THEN** 页面 MUST 切换到下一步骤，指示器同步更新
- **WHEN** 用户点击 "上一步" 按钮
- **THEN** 页面 MUST 返回上一步骤，已填写数据保留

### Requirement: Step 1 — 选择文档
第一步 SHALL 包含拖拽上传区、文件信息展示、清除按钮，支持 PDF/TXT/DOC/DOCX 格式，最大 16MB。

#### Scenario: 拖拽上传
- **WHEN** 用户拖拽文件到 `.upload-zone`
- **THEN** 区域 MUST 显示 drag-over 状态（蓝色边框、浅蓝背景）
- **WHEN** 用户释放文件
- **THEN** 文件信息卡 MUST 显示（文件名、大小）
- **THEN** 上传区 MUST 隐藏

#### Scenario: 清除文件
- **WHEN** 用户点击 "清除" 按钮
- **THEN** 文件信息卡 MUST 隐藏
- **THEN** 上传区 MUST 重新显示
- **THEN** "下一步" 按钮 MUST 变为 disabled

#### Scenario: 文件格式限制
- **WHEN** 用户选择不支持的文件格式
- **THEN** 系统 MUST 阻止上传并显示错误提示

### Requirement: Step 2 — 数据清洗
第二步 SHALL 包含 6 个清洗选项、预览清洗效果按钮、清洗对比面板（原始 vs 清洗后字符数 + 文本对比）、文档元数据编辑表单、跳过清洗按钮。

#### Scenario: 清洗选项
- **WHEN** Step 2 加载
- **THEN** MUST 显示 6 个 checkbox 选项（全部默认选中）：移除页眉页脚、移除页码、清理噪音字符、规范化空白、OCR 后处理、过滤非正文

#### Scenario: 预览清洗效果
- **WHEN** 用户点击 "预览清洗效果" 按钮
- **THEN** 系统 MUST 调用 `/api/preview-cleaning` 并展示对比结果
- **THEN** MUST 显示原始字符数、清洗后字符数、缩减百分比
- **THEN** MUST 显示左右对比面板（原始文本 vs 清洗后文本，各显示前 3000 字符）

#### Scenario: 元数据编辑
- **WHEN** 清洗预览完成
- **THEN** 元数据表单 MUST 显示并自动填充提取的 title、author、date、category

#### Scenario: 跳过清洗
- **WHEN** 用户点击 "跳过清洗" 按钮
- **THEN** 系统 MUST 直接跳到 Step 3，不传递清洗参数

### Requirement: Step 3 — 分块设置
第三步 SHALL 包含 3 种分块策略选择（句子分块/语义分块/递归分块）、参数配置、Small-to-Big 配置、分块预览功能。

#### Scenario: 策略选择卡片
- **WHEN** Step 3 加载
- **THEN** MUST 显示 3 个策略卡片（radio 选择）：
  - 句子分块（推荐）：按句子边界分块，适合技术文档和编号列表
  - 语义分块：基于 embedding 相似度，适合连续文本
  - 递归分块：按固定字符数切分，速度最快

#### Scenario: 策略切换联动
- **WHEN** 用户选择 "句子分块" 或 "递归分块"
- **THEN** MUST 显示分块大小输入框
- **WHEN** 用户选择 "递归分块"
- **THEN** MUST 额外显示重叠大小输入框
- **WHEN** 用户选择 "语义分块"
- **THEN** MUST 显示语义阈值滑块（0.1-0.9，默认 0.5）

#### Scenario: Small-to-Big 配置
- **WHEN** "启用 Small-to-Big 检索策略" toggle 开启（默认）
- **THEN** MUST 显示大块大小（默认 2000）和小块大小（默认 400）输入框
- **THEN** MUST 显示工作原理说明文字

#### Scenario: 预览分块效果
- **WHEN** 用户点击 "预览分块效果" 按钮
- **THEN** 系统 MUST 调用 `/api/preview-chunks` 并展示结果
- **THEN** MUST 显示统计：总块数、总字符数、平均大小
- **THEN** 如果启用 Small-to-Big，MUST 分别显示大块预览和小块预览
- **THEN** 每个分块 MUST 支持展开/收起查看全文

### Requirement: Step 4 — 确认上传
第四步 SHALL 显示所有配置的摘要：文档信息（文件名、标题、作者、分类）、清洗结果（原始字符、清洗后、缩减比例）、分块设置（策略、预计块数）。

#### Scenario: 确认摘要展示
- **WHEN** Step 4 加载
- **THEN** MUST 显示文档信息、清洗结果、分块设置三个摘要区块
- **THEN** 每个区块 MUST 以 summary-grid 格式展示

#### Scenario: 上传进度
- **WHEN** 用户点击 "开始上传" 按钮
- **THEN** MUST 显示进度条（30% → 60% → 100%）
- **THEN** MUST 显示当前状态文字（"正在上传..." → "正在处理..." → "上传成功!"）

### Requirement: 上传成功状态
上传成功后 SHALL 显示成功页面，包含成功图标、提示文字、知识库片段数量、"继续上传" 和 "检索测试" 两个操作按钮。

#### Scenario: 成功状态展示
- **WHEN** 上传完成
- **THEN** MUST 显示绿色成功图标
- **THEN** MUST 显示 "上传成功！文档已成功添加到知识库" 文字
- **THEN** MUST 显示本次添加的知识库片段数
- **THEN** "继续上传" 按钮 MUST 重置表单回到 Step 1
- **THEN** "检索测试" 按钮 MUST 滚动到检索测试区域

### Requirement: RAG 检索测试
上传页面底部 SHALL 包含检索测试区，支持输入查询、设置返回数量和相似度阈值，展示带相似度分数的检索结果。

#### Scenario: 检索测试
- **WHEN** 用户在检索测试区输入查询并点击 "开始检索"
- **THEN** 系统 MUST 调用 `/api/test-query` 并展示结果列表
- **THEN** 每条结果 MUST 显示来源文件名、相似度百分比（带颜色：>=70% 绿色，40-70% 橙黄，<40% 红色）、内容文本
- **WHEN** 无匹配结果
- **THEN** MUST 显示 "未找到相关结果" 空状态

### Requirement: 已上传文档列表
页面底部 SHALL 显示当前用户已上传的文档列表，每条显示文件图标（按格式区分）、文件名、上传时间、删除按钮。支持分页。

#### Scenario: 文档列表
- **WHEN** 有已上传文档
- **THEN** 每行 MUST 显示格式图标（PDF 红色、DOCX 蓝色、TXT 灰色）、文件名、上传时间、删除按钮
- **WHEN** 文档数超过每页限制
- **THEN** MUST 显示分页导航（上一页/下一页 + 页码）

#### Scenario: 删除文档
- **WHEN** 用户点击删除按钮
- **THEN** MUST 弹出确认对话框（modal）
- **THEN** 用户确认后 MUST 通过 AJAX 删除文档并刷新列表
- **THEN** 删除成功后 MUST 显示 flash message

#### Scenario: 空文档列表
- **WHEN** 用户没有上传过文档
- **THEN** MUST 显示空状态提示 "暂无上传的文档"

### Requirement: 原型功能差异 — 当前有但原型缺失
以下现有功能在设计原型中未体现，实现时 MUST 保留：

- **4 步骤上传向导**：原型为简单的单页拖拽上传，需要重新设计为向导式布局适配新设计系统
- **数据清洗 6 选项 + 预览对比**：保留清洗选项的 checkbox 布局 + 原文/清洗后对比面板
- **3 种分块策略选择**：保留策略卡片（含推荐标记）、参数联动显示
- **Small-to-Big 配置**：保留 toggle + 大小参数，含工作原理说明
- **分块预览**（展开/收起）：保留 chunk-item 列表 + toggleChunk JS
- **Step 4 确认摘要**：保留三区块摘要展示
- **RAG 检索测试区**：保留 query 输入 + k/threshold 参数 + 相似度结果展示
- **已上传文档列表 + 分页**：保留 document list + pagination + delete modal

### Requirement: 原型功能差异 — 原型有但当前不存在
以下原型功能在当前系统中不存在，实现时作为新增：

- **多文件上传**：原型支持选择多个文件（`multiple` attribute），当前仅支持单文件。实现时保持单文件以匹配后端处理逻辑
- **ZIP/CSV/JSON/LOG/SQL 格式支持**：原型列出更多文件类型。仅当后端 API 支持解析时启用
- **Compress large images**：原型有图片压缩 toggle。当前未实现此功能，toggle 可保留但标注 "Coming soon" 或隐藏
- **Notify assignee**：原型有邮件通知 toggle。当前无邮件通知系统，toggle 可保留但标注 "Coming soon" 或隐藏
- **Auto-analyze documents**：概念上对应当前的自动清洗流程，保留但改名适配

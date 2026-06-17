## 1. CSS 设计系统

- [ ] 1.1 备份现有 `static/css/style.css` 为 `static/css/style-old.css`
- [ ] 1.2 从设计原型复制新的 `style.css` 到 `static/css/style.css`，补充设计原型缺失的组件样式（step-indicator、comparison-panels、strategy-card、chunk-item、summary-grid、upload-progress、result-item、ticket-status-bar、chat-message 三种类型、scroll-to-bottom-btn、version-list、sync-progress）

## 2. Base 布局和导航

- [ ] 2.1 重写 `templates/base.html`：topnav 导航（毛玻璃 sticky + logo-dot + brand + 导航链接按角色区分 + 用户头像）、page-content 容器、flash messages、csrf token、保留 Font Awesome CDN

## 3. Auth 页面

- [ ] 3.1 重写 `templates/login.html`：auth-page + auth-card 布局，保留 Username（非 Email）登录字段、CSRF token、Flash messages 区域
- [ ] 3.2 重写 `templates/register.html`：auth-page + auth-card 布局，保留 Username/Email/Password 三字段、JS 客户端验证（用户名长度、邮箱格式、密码强度）、AJAX 提交、`.form-error` 实时显示、CSRF token

## 4. User Dashboard

- [ ] 4.1 重写 `templates/user_dashboard.html`：section-header（欢迎标题 + 角色 badge + 创建会话按钮）+ stats-grid 3 卡片（会话总数/进行中/需关注，Jinja2 `selectattr` 过滤）+ 创建新会话 POST 表单卡片 + 我的会话列表（status badge 颜色区分）+ 空状态

## 5. Tech Dashboard

- [ ] 5.1 重写 `templates/tech_dashboard.html`：section-header（标题 + 上传文档/FAQ 管理快捷按钮）+ stats-grid 4 卡片（总会话数/进行中 green/需关注 red/已关闭 amber）+ 需关注会话高亮区（条件渲染）+ 全部会话列表（status badge + 用户 ID + 时间）+ 空状态

## 6. Chat/Conversation

- [ ] 6.1 重写 `templates/conversation.html`：chat-layout 双栏 + 页面头部（会话 ID + 返回 + 动态操作按钮：标记需关注/关闭/解决并关闭/重新打开，按角色和状态渲染）+ 状态横幅（needs_attention warning / closed info）+ 用户工单状态栏（status badge + 轮次 + 人工介入 JS + 关闭工单）+ 消息列表（3 种 sender_type：user 右对齐蓝底/AI 左对齐灰底/tech_support 左对齐灰底，含头像文字和图标）+ composer（会话未关闭时显示）+ 已关闭提示 + 滚动到底部按钮 + 关闭会话 Modal（含 FAQ 生成 checkbox）+ 关闭工单 Modal（普通用户）

## 7. Document Upload

- [ ] 7.1 重写上传页面整体布局：统计卡片 + upload wizard 外层容器（step-indicator 4 步骤指示器）
- [ ] 7.2 重写 Step 1（选择文档）：upload-zone 拖拽区 + file-info 卡片（文件名+大小+清除按钮）+ 下一步按钮，保留文件选择和拖拽 JS（PDF/TXT/DOC/DOCX，16MB）
- [ ] 7.3 重写 Step 2（数据清洗）：6 个清洗 checkbox + 预览清洗按钮 + 对比面板（原文/清洗后字符数 + 文本对比 3000 字符）+ 元数据编辑表单（title/author/date/category）+ 跳过清洗，保留 `/api/preview-cleaning` AJAX
- [ ] 7.4 重写 Step 3（分块设置）：3 种策略卡片（句子推荐/语义/递归）+ 参数联动（chunk_size/overlap 按策略显示）+ 语义阈值滑块 + Small-to-Big toggle + 分块预览（统计 + chunk 列表展开/收起，区分大块/小块），保留 `/api/preview-chunks` AJAX
- [ ] 7.5 重写 Step 4（确认上传）：三区块摘要（文档信息/清洗结果/分块设置）+ 进度条 + 成功状态（成功图标 + 片段数 + 继续上传/检索测试按钮），保留 `/upload` AJAX 上传
- [ ] 7.6 重写 RAG 检索测试区：query + k/threshold + 结果展示（相似度颜色：>=70% green / 40-70% amber / <40% red），保留 `/api/test-query` AJAX
- [ ] 7.7 重写已上传文档列表：文件列表（格式图标 + 文件名 + 时间 + 删除按钮）+ 分页 + 删除确认 modal（含 ChromaDB 警告），保留删除 AJAX

## 8. FAQ Management

- [ ] 8.1 重写 `templates/faq_manage.html`：统计卡片 4 个（总 FAQ/已确认/待审核/草稿）+ filter-bar（状态下拉 5 种 + 分类下拉动态加载 + 搜索输入框）+ data-table（checkbox 全选 + 问题/答案预览 100 字符/分类/status badge 颜色/创建时间/操作按钮：编辑+版本历史+删除）+ 分页 + bulk-bar + 3 个 Modal（FAQ 表单含保存/确认双流程+修改原因+向量同步进度条、版本历史列表、删除确认含 ChromaDB 警告），全部 AJAX CRUD + Modal ESC/遮罩关闭
- [ ] 8.2 实现 FAQ 新增/编辑 Modal 内的双向流程：待审核状态显示 "确认并添加" 按钮（触发向量同步进度），其他状态显示 "保存" 按钮

## 9. 验证和收尾

- [ ] 9.1 逐页验证：login（表单提交+flash）→ register（JS 验证+AJAX）→ user dashboard（创建会话+列表）→ tech dashboard（需关注区+列表）→ chat（3 种消息类型+横幅+modal+工单状态栏+composer）→ upload（4 步骤+RAG 测试+文档列表+删除）→ faq manage（筛选+CRUD+批量+版本历史+向量同步）
- [ ] 9.2 验证移动端响应式（768px 断点）
- [ ] 9.3 确认所有 `url_for` 端点正确，无 BuildError
- [ ] 9.4 验证所有 AJAX API（preview-cleaning, preview-chunks, test-query, upload, delete document, ticket status, ticket handoff, ticket close, FAQ CRUD, FAQ confirm, FAQ versions, FAQ bulk-delete）
- [ ] 9.5 删除 `static/css/style-old.css` 备份文件

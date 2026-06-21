## 1. Phase 1: 基础设施 — 后端 JWT 认证

- [x] 1.1 添加后端依赖：在 `requirements.txt` 中新增 `PyJWT>=2.8`、`flask-cors>=4.0`
- [x] 1.2 创建 JWT 工具模块：在 `app/utils/jwt.py` 中实现 `create_access_token()`、`create_refresh_token()`、`verify_token()` 函数
- [x] 1.3 创建 JWT 认证装饰器：在 `app/utils/auth.py` 中实现 `@jwt_required` 装饰器，从 `Authorization: Bearer` 头提取和验证 Token，注入 `current_user`
- [x] 1.4 创建 Auth API 蓝图 `app/api/auth.py`：实现 `POST /api/v1/auth/login`、`POST /api/v1/auth/register`、`POST /api/v1/auth/refresh` 三个端点，返回统一 JSON 格式
- [x] 1.5 CORS 配置：在 `app/__init__.py` 的 `create_app()` 中通过 `flask-cors` 启用 CORS，开发环境允许 `localhost:5173`
- [x] 1.6 蓝图注册：在 `app/__init__.py` 中注册 auth 蓝图，CSRF 豁免
- [x] 1.7 验证：`flake8 .` + `python -c "from app import create_app; app=create_app(); print('OK')"` + 手动测试登录/注册 API

## 2. Phase 1: 基础设施 — Vue 3 前端项目搭建

- [x] 2.1 创建 Vue 3 项目：`npm create vue@latest frontend`，选择 Vue Router + Pinia
- [x] 2.2 安装依赖：`npm install element-plus axios marked`（在 `frontend/` 下）
- [x] 2.3 配置 Vite proxy：`frontend/vite.config.js` 中配置 `/api/v1` 代理到 `http://localhost:5050`
- [x] 2.4 创建环境变量文件：`.env.development`（`VITE_API_BASE=`空）、`.env.production`（`VITE_API_BASE=/api/v1`）
- [x] 2.5 创建 Axios 实例 `frontend/src/api/index.js`：baseURL 从 env 读取、请求拦截器（自动加 Authorization）、响应拦截器（401 自动刷新 Token）
- [x] 2.6 创建 Auth API 封装 `frontend/src/api/auth.js`：`login()`、`register()`、`refreshToken()` 函数
- [x] 2.7 创建 Pinia Auth Store `frontend/src/stores/auth.js`：管理 `access_token`、`refresh_token`、`user` 状态，`login()`/`logout()`/`refreshToken()` actions
- [x] 2.8 创建 Vue Router `frontend/src/router/index.js`：定义路由表，Hash 模式，`beforeEach` 导航守卫（未登录 → login；已登录访问 login → 首页）
- [x] 2.9 创建 `App.vue` 根组件：`<router-view>` + 全局 layout（登录/注册无 topnav，其他页面有 topnav）
- [x] 2.10 全局注册 Element Plus：`frontend/src/main.js` 中 `app.use(ElementPlus, { locale: zhCn })`
- [x] 2.11 验证：`npm run dev` 启动前端，确认 Vite 正常编译且 proxy 转发成功

## 3. Phase 1: 基础设施 — 登录/注册页迁移

- [x] 3.1 创建 Login.vue：Element Plus `el-form` + `el-card`，居中布局，username/password 字段，登录调用 auth store
- [x] 3.2 创建 Register.vue：Element Plus `el-form` + `el-card`，username/email/password 字段，客户端验证，注册调用 auth API
- [x] 3.3 表单验证规则：username 3-64 字符、email 格式、password >= 8 位含大小写和数字
- [x] 3.4 创建共用 AuthLayout 布局：居中卡片（max-width 400px），logo-dot + 标题，底部 router-link 切换
- [x] 3.5 错误处理：API 错误用 `el-message.error` 显示；表单字段错误用 `el-form-item` error slot

## 4. Phase 2: API 层规范化

- [x] 4.1 统一响应格式工具：创建 `app/utils/response.py`，提供 `api_success(data, code, message)` 和 `api_error(code, message)` helper
- [x] 4.2 重构现有 chat API（`app/api/chat.py`）：路由改为 `/api/v1/chat/...`，返回统一 JSON 格式
- [x] 4.3 重构现有 FAQ API（`app/api/faq.py`）：路由改为 `/api/v1/faq/...`，返回统一 JSON 格式
- [x] 4.4 重构现有 RAG Dashboard API（`app/api/rag_dashboard.py`）：路由改为 `/api/v1/rag/...`，返回统一 JSON 格式
- [x] 4.5 重构现有 Tickets API（`app/api/tickets.py`）：路由改为 `/api/v1/tickets/...`，返回统一 JSON 格式
- [x] 4.6 将 `@login_required` 逐步替换为 `@jwt_required`（新增 v1 端点用 jwt_required，旧端点保持不变）
- [x] 4.7 前端 API 封装：创建 `frontend/src/api/chat.js`、`faq.js`、`document.js`、`rag.js`

## 5. Phase 2: 核心页面 — 客服对话 SPA

- [x] 5.1 创建 ChatLayout.vue：双栏布局（SessionList 320px + ChatMain flex:1）
- [x] 5.2 创建 SessionList.vue：会话列表 `el-menu`，每项显示标题+时间+未读标记，"新建会话" 按钮
- [x] 5.3 创建 MessageBubble.vue：根据 `sender_type` prop 渲染不同样式的消息气泡（user 蓝色右对齐/ai 灰色左对齐+markdown/tech_support 灰色左对齐）
- [x] 5.4 创建 ChatInput.vue：`el-input` textarea + 发送按钮，Enter 发送，closed 状态 disabled
- [x] 5.5 创建 MarkdownRenderer.vue：使用 `marked` 库渲染 Markdown，支持代码高亮
- [x] 5.6 创建 Pinia Chat Store `frontend/src/stores/chat.js`：管理当前会话、消息列表、加载/发送 action
- [x] 5.7 实现 SSE 流式接收：`frontend/src/composables/useSSE.js`，处理 `text/event-stream` 流式消息
- [x] 5.8 实现消息列表自动滚动 + "回到底部" 按钮：`el-backtop` 或自定义实现
- [x] 5.9 实现操作按钮：头部根据角色+状态动态显示按钮（标记需关注/关闭/解决并关闭/重新打开/人工介入）
- [x] 5.10 实现关闭会话 Modal：`el-dialog` + FAQ checkbox
- [x] 5.11 实现状态横幅：`el-alert`（needs_attention warning / closed info）
- [x] 5.12 实现用户工单状态栏：`el-tag` 状态、轮次计数、人工介入/关闭按钮

## 6. Phase 2: 核心页面 — FAQ 管理 SPA

- [x] 6.1 创建 FaqManage.vue：`el-row` 统计卡片 + `el-table` + `el-pagination`
- [x] 6.2 实现统计卡片：4 卡片（总数/已确认/待审核/草稿），API 实时加载
- [x] 6.3 实现筛选栏：`el-select` 状态 + `el-select` 分类 + `el-input` 搜索（300ms 防抖）
- [x] 6.4 实现表格：`el-table` 含 selection、问题、答案预览、分类、状态 `el-tag`、创建时间、操作列
- [x] 6.5 实现分页：`el-pagination` layout="prev, pager, next, sizes, total"
- [x] 6.6 实现批量操作：选中时显示批量操作栏（计数 + 批量删除按钮）
- [x] 6.7 实现新增/编辑 Modal：`el-dialog` + `el-form`，区分新增/编辑/待审核三种模式
- [x] 6.8 实现向量同步进度：`el-progress` 组件
- [x] 6.9 实现版本历史 Modal：`el-dialog` + `el-timeline`
- [x] 6.10 实现删除确认：`el-message-box.confirm`

## 7. Phase 2: 核心页面 — 文档上传 SPA

- [x] 7.1 创建 DocumentUpload.vue：统计卡片 + `el-steps` 向导
- [x] 7.2 实现 Step 1 文件选择：`el-upload` drag 模式，格式/大小限制
- [x] 7.3 实现 Step 2 数据清洗：`el-checkbox-group` 6 选项 + 清洗预览对比
- [x] 7.4 实现 Step 3 分块设置：`el-radio-group` 3 策略 + 参数联动 + Small-to-Big `el-switch` + 分块预览
- [x] 7.5 实现 Step 4 确认上传：配置摘要 + `el-progress` 上传进度
- [x] 7.6 实现上传成功页：`el-result` 成功状态 + 继续上传/检索测试按钮
- [x] 7.7 实现 RAG 检索测试区：查询输入 + 相似度结果展示
- [x] 7.8 实现已上传文档列表：文件图标 + 文件名 + 时间 + 删除按钮 + `el-pagination`

## 8. Phase 3: 后台管理页面

- [x] 8.1 创建 RagDashboard.vue：`el-row` 4 统计卡片 + `el-table` 检索日志
- [x] 8.2 实现日志表格筛选：`el-select` 路由方式 + `el-input` 搜索
- [x] 8.3 实现行展开详情：检索结果完整内容、相似度、来源文件、LLM-Judge 评分
- [x] 8.4 实现低质量查询高亮：`row-class-name` 红色左边框
- [x] 8.5 创建 TechDashboard.vue：技术支持工作台
- [x] 8.6 创建 UserDashboard.vue：用户仪表盘

## 9. Phase 3: 部署配置

- [x] 9.1 创建 `config/nginx.conf`：SPA fallback + API 反向代理 + 静态资源缓存
- [x] 9.2 创建 `frontend/Dockerfile`：多阶段构建（Node build → Nginx serve）
- [x] 9.3 创建/更新 `docker-compose.yml`：frontend（Nginx + Vue） + backend（Flask + Gunicorn）服务编排
- [x] 9.4 更新 `start.sh`：同时启动 Vite dev server 和 Flask，显示两个地址
- [x] 9.5 `frontend/vite.config.js` 生产构建配置：base path、output dir、assets 处理

## 10. Phase 4: 收尾 — 下线 SSR

- [x] 10.1 Vue Router 切换为 History 模式
- [x] 10.2 删除 `templates/` 目录（所有 Jinja2 模板）
- [x] 10.3 删除 `static/css/style.css`（样式已迁移到 Vue 组件）
- [x] 10.4 清理 `app/__init__.py`：移除 `template_folder`、`static_folder`、`@app.context_processor`、CSRF 初始化
- [x] 10.5 移除 `flask-login`、`flask-wtf` 等依赖（确认不再使用后）
- [x] 10.6 移除 auth blueprint（`app/auth/`）和页面蓝图（`app/main/`、`app/conversation/routes.py` 的页面路由部分）
- [x] 10.7 清理 `app/__init__.py` 中不再需要的蓝图注册和 CSRF 豁免
- [x] 10.8 全量测试：`pytest tests/test_app.py tests/unit/ tests/test_integration.py`
- [ ] 10.9 RAGAS smoke test：`python scripts/run_smoke_eval.py` ⚠️ 约需 20-25 分钟，建议手动执行

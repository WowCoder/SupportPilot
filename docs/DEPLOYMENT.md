# 部署指南

## 快速开始

### 1. 安装依赖

```bash
# 生产依赖
pip install -r requirements.txt

# 开发依赖（包含测试工具）
pip install -r requirements-dev.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```bash
SECRET_KEY=your-secret-key-here
QWEN_API_KEY=your-qwen-api-key-here
DATABASE_URL=sqlite:///app.db
FLASK_DEBUG=true
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

- 访问 `http://localhost:5005`
- 注册新用户或使用技术支持账号登录

## 生产部署建议

1. **数据库**: 使用 PostgreSQL 或 MySQL 替代 SQLite
2. **反向代理**: 配置 Nginx 作为反向代理
3. **HTTPS**: 配置 SSL 证书
4. **密钥**: 设置强 SECRET_KEY
5. **调试**: 关闭 DEBUG 模式
6. **日志**: 配置日志轮转
7. **环境变量**: 使用环境变量管理敏感信息

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

## 故障排除

### QWEN_API_KEY 错误

```bash
export QWEN_API_KEY=your-actual-key
```

### 数据库锁定

如果使用 SQLite 遇到锁定问题，考虑迁移到 PostgreSQL：
```bash
export DATABASE_URL=postgresql://user:password@localhost/supportpilot
```

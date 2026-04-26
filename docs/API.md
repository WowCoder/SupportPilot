# API 文档

## 认证相关

| 端点 | 方法 | 说明 |
|------|------|------|
| `/register` | POST | 注册新用户 |
| `/login` | POST | 用户登录 |
| `/logout` | GET | 用户注销 |

## 会话相关

| 端点 | 方法 | 说明 |
|------|------|------|
| `/conversation/new` | POST | 创建新会话 |
| `/conversation/<id>` | GET | 查看会话详情 |
| `/conversation/<id>/send` | POST | 发送消息 |
| `/conversation/<id>/close` | POST | 关闭会话（技术支持） |
| `/conversation/<id>/reopen` | POST | 重新打开会话（技术支持） |
| `/conversation/<id>/mark-attention` | POST | 标记需关注（技术支持） |

## 文档相关

| 端点 | 方法 | 说明 |
|------|------|------|
| `/upload` | GET | 查看上传页面 |
| `/upload` | POST | 上传文档 |

## 工单管理 (Ticket Management)

### 获取工单状态
```
GET /api/ticket/<session_id>/status
```

**响应**:
```json
{
  "success": true,
  "status": "open",
  "round_count": 3,
  "should_show_handoff": true
}
```

### 请求人工介入
```
POST /api/ticket/<session_id>/handoff
```

**响应**:
```json
{
  "success": true,
  "message": "已请求人工介入..."
}
```

### 关闭工单
```
POST /api/ticket/<session_id>/close
```

**请求体**:
```json
{ "generate_faq": true }
```

**响应**:
```json
{
  "success": true,
  "message": "工单已关闭"
}
```

## FAQ 管理 (FAQ Management)

### 审核工作流

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/faq/generate` | POST | 从对话生成 FAQ 草稿 |
| `/api/faq/<id>/update` | POST | 更新 FAQ 草稿 |
| `/api/faq/<id>/confirm` | POST | 确认 FAQ 并向量化 |
| `/api/faq/<id>/reject` | POST | 拒绝 FAQ 草稿 |

### CRUD 操作

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/faq` | GET | 获取 FAQ 列表 |
| `/api/faq/<id>` | GET | 获取单个 FAQ |
| `/api/faq` | POST | 创建新 FAQ |
| `/api/faq/<id>` | PUT | 更新 FAQ |
| `/api/faq/<id>` | DELETE | 删除 FAQ |
| `/api/faq/bulk-delete` | POST | 批量删除 |

### 版本历史

```
GET /api/faq/<id>/versions
```

**响应**:
```json
{
  "success": true,
  "versions": [
    {
      "id": 1,
      "question": "...",
      "answer": "...",
      "change_reason": "...",
      "changed_by": "admin",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

## Context

当前项目使用的 `langchain-community==0.0.10` 和 `langchain==0.0.350` 版本过旧，导致以下问题：

1. **Metaclass 冲突**: Python 3.9 下与 `VertexAI` 等类的 metaclass 不兼容
2. **已弃用警告**: `HuggingFaceEmbeddings` 使用旧版导入路径
3. **测试无法运行**: pytest 启动时即因导入错误失败

## Goals / Non-Goals

**Goals:**
- 升级 langchain 相关包到最新稳定版本（0.3.x 或 1.x）
- 修复所有因 API 变更导致的代码问题
- 确保所有现有测试通过
- 保持现有功能行为不变

**Non-Goals:**
- 不引入新的 langchain 功能
- 不改变 RAG 检索逻辑
- 不修改业务层 API

## Decisions

### Decision 1: 使用 langchain 0.3.x 系列（当前 Python 3.9 环境）

**选择**: `langchain>=0.3.28,<1.0.0`, `langchain-community>=0.3.28,<1.0.0`, `langchain-core>=0.3.0,<1.0.0`

**理由**: 
- 0.3.28 是 Python 3.9 可用的最新稳定版本
- 1.x 版本需要 Python 3.10+ (`Requires-Python >=3.10.0`)
- 0.3.x 已解决 metaclass 冲突问题
- 避免升级 Python 版本的连锁变更

**替代方案**: 升级 Python 到 3.10+ 并使用 langchain 1.x
**拒绝原因**: 升级 Python 环境涉及系统级变更，风险较高，不在本次范围

**约束条件**: 
- 当前环境：Python 3.9.6
- 如需使用 1.x，需先升级 Python 到 3.10+

### Decision 2: 更新 HuggingFaceEmbeddings 导入

**选择**: 从 `langchain_huggingface` 包导入

```python
# 旧代码
from langchain_community.embeddings import HuggingFaceEmbeddings

# 新代码
from langchain_huggingface import HuggingFaceEmbeddings
```

**理由**: 
- langchain 0.2+ 将 HuggingFace 相关组件移至独立包
- 官方推荐的导入方式

### Decision 3: 移除 show_progress 参数

**选择**: 移除 `show_progress` 参数

```python
# 旧代码
HuggingFaceEmbeddings(model_name="...", show_progress=True)

# 新代码
HuggingFaceEmbeddings(model_name="...")
```

**理由**: 该参数在新版本中已移除

### Decision 4: 安装 langchain_huggingface 独立包

**选择**: 新增 `langchain_huggingface>=0.1.0` 依赖

**理由**: HuggingFace 相关组件在 1.x 中已独立为单独包

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| API 变更导致功能异常 | 完整运行测试套件验证 |
| 新版本引入新 bug | 保留 requirements.txt 旧版本注释，可快速回滚 |
| 其他依赖不兼容 | 使用 pip check 验证依赖树 |
| 向量数据库兼容性 | ChromaDB 已验证兼容 |
| **1.x API 与 0.3.x 差异大** | **预留更多时间进行代码适配和测试** |

## Migration Plan

### 升级步骤
1. 备份当前 `requirements.txt`
2. 修改 `requirements.txt` 中的版本约束
3. 运行 `pip install -r requirements.txt --upgrade`
4. 修复 `rag/rag_utils.py` 中的 API 调用
5. 运行测试验证

### 回滚策略
```bash
# 恢复旧 requirements.txt
git checkout requirements.txt
pip install -r requirements.txt
```

## Open Questions

无

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { listEntries, createEntry, updateEntry, deleteEntry, bulkDelete, listCategories, testSearch } from '@/api/faq'
import { ElMessage, ElMessageBox } from 'element-plus'

// --- State ---
const loading = ref(false)
const entries = ref([])
const total = ref(0)
const selectedIds = ref([])
const categories = ref([])

// Stats
const stats = reactive({ total: 0, confirmed: 0, pending: 0, draft: 0 })

// Filters
const filters = reactive({
  status: '',
  category: '',
  search: '',
})

// Pagination
const page = ref(1)
const pageSize = ref(20)

// Modals
const formVisible = ref(false)
const formMode = ref('create') // 'create' | 'edit' | 'review'
const formLoading = ref(false)
const form = reactive({ id: null, question: '', answer: '', category: '', reason: '' })

const versionVisible = ref(false)
const versions = ref([])
const versionsLoading = ref(false)

// Search debounce
let searchTimer = null

// --- Methods ---
async function loadData() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
      stats: 'true',
    }
    if (filters.status) params.status = filters.status
    if (filters.category) params.category = filters.category
    if (filters.search) params.search = filters.search

    const { data } = await listEntries(params)
    entries.value = data.data?.items || []
    total.value = data.data?.total || 0
    if (data.data?.stats) {
      Object.assign(stats, data.data.stats)
    }
  } catch (err) {
    ElMessage.error('加载 FAQ 列表失败')
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  try {
    const { data } = await listCategories()
    categories.value = data.data || []
  } catch {
    // Silently ignore
  }
}

function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadData()
  }, 300)
}

function handleSelectChange() {
  page.value = 1
  loadData()
}

function handlePageChange(newPage) {
  page.value = newPage
  loadData()
}

function handleSizeChange(newSize) {
  pageSize.value = newSize
  page.value = 1
  loadData()
}

// --- Form Modal ---
function openCreate() {
  formMode.value = 'create'
  form.id = null
  form.question = ''
  form.answer = ''
  form.category = ''
  form.reason = ''
  formVisible.value = true
}

function openEdit(entry) {
  formMode.value = entry.status === 'pending_review' ? 'review' : 'edit'
  form.id = entry.id
  form.question = entry.question
  form.answer = entry.answer
  form.category = entry.category
  form.reason = ''
  formVisible.value = true
}

async function handleSave() {
  formLoading.value = true
  try {
    const payload = {
      question: form.question,
      answer: form.answer,
      category: form.category,
    }
    if (form.reason) payload.reason = form.reason
    if (formMode.value === 'review') payload.status = 'confirmed'

    if (formMode.value === 'create') {
      await createEntry(payload)
      ElMessage.success('FAQ 创建成功')
    } else {
      await updateEntry(form.id, payload)
      ElMessage.success(
        formMode.value === 'review' ? 'FAQ 已确认并同步到向量库' : 'FAQ 更新成功'
      )
    }
    formVisible.value = false
    loadData()
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '操作失败')
  } finally {
    formLoading.value = false
  }
}

// --- Version History Modal ---
async function openVersions(entry) {
  versionVisible.value = true
  versionsLoading.value = true
  versions.value = []
  try {
    // For now, use entry data as version stub
    // Full version history API would be in a future iteration
    versions.value = [{
      time: entry.updated_at || entry.created_at,
      reason: '当前版本',
      question: entry.question,
      answer: entry.answer,
    }]
  } finally {
    versionsLoading.value = false
  }
}

// --- Delete ---
async function handleDelete(entry) {
  try {
    await ElMessageBox.confirm(
      '此操作将同时从知识库中移除相关条目，是否继续？',
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await deleteEntry(entry.id)
    ElMessage.success('FAQ 已删除')
    loadData()
  } catch {
    // Cancelled
  }
}

async function handleBulkDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的条目')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedIds.value.length} 条 FAQ？此操作将同时从知识库中移除`,
      '批量删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await bulkDelete(selectedIds.value)
    ElMessage.success(`已删除 ${selectedIds.value.length} 条 FAQ`)
    selectedIds.value = []
    loadData()
  } catch {
    // Cancelled
  }
}

// --- Test Search ---
const testQuery = ref('')
const testK = ref(5)
const testThreshold = ref(0.25)
const testResults = ref([])
const testLoading = ref(false)
const testShowPanel = ref(false)

async function runTestSearch() {
  if (!testQuery.value.trim()) {
    ElMessage.warning('请输入搜索内容')
    return
  }
  testLoading.value = true
  testResults.value = []
  try {
    const { data } = await testSearch(testQuery.value, testK.value, testThreshold.value)
    testResults.value = data.results || []
    if (testResults.value.length === 0) {
      ElMessage.info('未找到匹配的 FAQ')
    }
  } catch (err) {
    ElMessage.error('检索失败')
  } finally {
    testLoading.value = false
  }
}

// --- Init ---
onMounted(() => {
  loadData()
  loadCategories()
})

// Status helpers
const statusMap = {
  confirmed: { label: '已确认', type: 'success' },
  pending_review: { label: '待审核', type: 'warning' },
  draft: { label: '草稿', type: 'info' },
  rejected: { label: '已拒绝', type: 'danger' },
}

function truncate(text, max = 100) {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '...' : text
}
</script>

<template>
  <div class="page-content">
    <h1 style="margin-bottom: 24px;">FAQ 管理</h1>

    <!-- Stats cards -->
    <el-row :gutter="16" style="margin-bottom: 24px;">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ stats.total }}</div>
            <div class="stat-label">总 FAQ 数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value" style="color: #52c41a;">{{ stats.confirmed }}</div>
            <div class="stat-label">已确认</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value" style="color: #faad14;">{{ stats.pending }}</div>
            <div class="stat-label">待审核</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value" style="color: #999;">{{ stats.draft }}</div>
            <div class="stat-label">草稿</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Filter bar -->
    <div class="filter-bar">
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 150px;" @change="handleSelectChange">
        <el-option label="全部" value="" />
        <el-option label="已确认" value="confirmed" />
        <el-option label="待审核" value="pending_review" />
        <el-option label="草稿" value="draft" />
        <el-option label="已拒绝" value="rejected" />
      </el-select>
      <el-select v-model="filters.category" placeholder="全部分类" clearable style="width: 180px;" @change="handleSelectChange">
        <el-option label="全部" value="" />
        <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
      </el-select>
      <el-input v-model="filters.search" placeholder="搜索 FAQ..." clearable style="width: 280px;" @input="onSearch" @clear="handleSelectChange" />
      <div style="flex:1;" />
      <el-button type="primary" @click="openCreate">新增 FAQ</el-button>
    </div>

    <!-- Bulk actions -->
    <transition name="fade">
      <div v-if="selectedIds.length > 0" class="bulk-bar">
        <span>已选择 {{ selectedIds.length }} 条</span>
        <el-button type="danger" size="small" @click="handleBulkDelete">批量删除</el-button>
        <el-button size="small" @click="selectedIds = []">取消选择</el-button>
      </div>
    </transition>

    <!-- Table -->
    <el-table
      :data="entries"
      v-loading="loading"
      style="width: 100%;"
      @selection-change="(rows) => selectedIds = rows.map(r => r.id)"
      empty-text="暂无 FAQ"
    >
      <el-table-column type="selection" width="50" />
      <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
      <el-table-column label="答案预览" min-width="250">
        <template #default="{ row }">{{ truncate(row.answer, 100) }}</template>
      </el-table-column>
      <el-table-column prop="category" label="分类" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.category" size="small">{{ row.category }}</el-tag>
          <span v-else style="color: #ccc;">-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type" size="small">
            {{ statusMap[row.status]?.label || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString('zh-CN') }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link type="info" size="small" @click="openVersions(row)">版本</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <div style="margin-top: 16px; display: flex; justify-content: flex-end;">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- Create/Edit Modal -->
    <el-dialog
      v-model="formVisible"
      :title="formMode === 'create' ? '新增 FAQ' : '编辑 FAQ'"
      width="640px"
      :close-on-click-modal="false"
      @closed="formLoading = false"
    >
      <el-form :model="form" label-position="top">
        <el-form-item label="问题" required>
          <el-input v-model="form.question" type="textarea" :rows="2" placeholder="请输入 FAQ 问题" />
        </el-form-item>
        <el-form-item label="答案" required>
          <el-input v-model="form.answer" type="textarea" :rows="4" placeholder="请输入 FAQ 答案" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="form.category" placeholder="例如：账户问题、支付问题" />
        </el-form-item>
        <el-form-item v-if="formMode === 'edit'" label="修改原因">
          <el-input v-model="form.reason" placeholder="请说明修改原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button
          v-if="formMode === 'review'"
          type="success"
          :loading="formLoading"
          @click="handleSave"
        >
          确认并添加
        </el-button>
        <el-button
          v-else
          type="primary"
          :loading="formLoading"
          @click="handleSave"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- Version History Modal -->
    <el-dialog
      v-model="versionVisible"
      title="版本历史"
      width="640px"
    >
      <div v-loading="versionsLoading">
        <el-timeline v-if="versions.length > 0">
          <el-timeline-item
            v-for="(v, idx) in versions"
            :key="idx"
            :timestamp="new Date(v.time).toLocaleString('zh-CN')"
            placement="top"
          >
            <p><strong>原因：</strong>{{ v.reason }}</p>
            <p><strong>问题：</strong>{{ v.question }}</p>
            <p><strong>答案：</strong>{{ v.answer }}</p>
          </el-timeline-item>
        </el-timeline>
        <p v-else style="text-align: center; color: #aaa;">暂无版本记录</p>
      </div>
    </el-dialog>

    <!-- Vector Test Search -->
    <div style="margin-top: 40px;">
      <el-divider />
      <div style="display: flex; align-items: center; gap: 12px; cursor: pointer;" @click="testShowPanel = !testShowPanel">
        <h2 style="margin: 0;">🔍 向量检索测试</h2>
        <el-icon><component :is="testShowPanel ? 'ArrowUp' : 'ArrowDown'" /></el-icon>
      </div>
      <div v-show="testShowPanel" style="margin-top: 16px;">
        <el-card>
          <div style="display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap;">
            <el-input v-model="testQuery" placeholder="输入用户问题，测试检索效果..." style="flex: 1; min-width: 250px;" />
            <span style="font-size: 13px; color: #888;">返回</span>
            <el-input-number v-model="testK" :min="1" :max="20" size="small" style="width: 80px;" />
            <span style="font-size: 13px; color: #888;">条，阈值</span>
            <el-input-number v-model="testThreshold" :min="0" :max="1" :step="0.05" size="small" style="width: 100px;" />
            <el-button type="primary" :loading="testLoading" @click="runTestSearch">开始检索</el-button>
          </div>
          <div v-if="testResults.length > 0" style="margin-top: 16px;">
            <div v-for="(r, idx) in testResults" :key="idx" style="padding: 12px; border-bottom: 1px solid #f5f5f5;">
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <el-tag :type="r.similarity >= 0.7 ? 'success' : r.similarity >= 0.4 ? 'warning' : 'danger'" size="small">
                  相似度 {{ (r.similarity * 100).toFixed(1) }}%
                </el-tag>
                <el-tag v-if="r.will_be_used" type="success" size="small">会被使用</el-tag>
                <el-tag v-else type="info" size="small">不会使用</el-tag>
                <span style="font-size: 12px; color: #888;">FAQ #{{ r.faq_id }}</span>
              </div>
              <p style="font-weight: 500; margin: 4px 0;">Q: {{ r.question }}</p>
              <p style="font-size: 13px; color: #555;">A: {{ r.answer?.slice(0, 200) }}{{ r.answer?.length > 200 ? '...' : '' }}</p>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-content {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.stat-card {
  text-align: center;
  padding: 8px 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #333;
}

.stat-label {
  font-size: 13px;
  color: #999;
  margin-top: 4px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.bulk-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: #e6f7ff;
  border: 1px solid #91d5ff;
  border-radius: 6px;
  margin-bottom: 12px;
  font-size: 14px;
}

.fade-enter-active,
.fade-leave-active {
  transition: all 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>

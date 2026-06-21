<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getRagLogs, getRagStats } from '@/api/rag'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const logs = ref([])
const stats = reactive({
  total_queries: 0,
  positive_rate: 0,
  avg_similarity: 0,
  avg_judge_score: 0,
  today_queries: 0,
})

const filters = reactive({
  route_type: '',
  search: '',
  min_similarity: '',
})

const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

async function loadData() {
  loading.value = true
  try {
    // Load both stats and logs
    const params = {
      page: page.value,
      per_page: pageSize.value,
    }
    if (filters.route_type) params.route_type = filters.route_type
    if (filters.search) params.search = filters.search
    if (filters.min_similarity) params.min_similarity = Number(filters.min_similarity)

    const [logsRes, statsRes] = await Promise.all([
      getRagLogs(params),
      getRagStats(),
    ])

    // Logs
    const logData = logsRes.data
    logs.value = logData.items || (Array.isArray(logData.data) ? logData.data : logData.data?.items) || []
    total.value = logData.pagination?.total || logData.total || 0

    // Stats
    const statsData = statsRes.data
    const s = statsData.stats || statsData.data || {}
    Object.assign(stats, s)
  } catch (err) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  loadData()
}

function rowClassName({ row }) {
  const sim = row.top1_similarity ?? 0
  const judge = typeof row.judge_score === 'number' ? row.judge_score : 5
  if (sim < 0.3 || judge < 3) return 'row-low-quality'
  return ''
}

onMounted(loadData)
</script>

<template>
  <div class="page-content">
    <h1 style="margin-bottom: 24px;">RAG 仪表盘</h1>

    <!-- Stats cards -->
    <el-row :gutter="16" style="margin-bottom: 24px;">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ stats.total_queries }}/{{ stats.today_queries }}</div>
            <div class="stat-label">总检索次数（总计/今日）</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value" style="color: #52c41a;">{{ stats.positive_rate }}%</div>
            <div class="stat-label">正反馈率</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value" style="color: #1890ff;">{{ stats.avg_similarity }}</div>
            <div class="stat-label">平均 Top-1 相似度</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value" style="color: #722ed1;">{{ stats.avg_judge_score }}</div>
            <div class="stat-label">LLM-Judge 均分</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Filter bar -->
    <div class="filter-bar">
      <el-select v-model="filters.route_type" placeholder="路由方式" clearable style="width: 150px;" @change="onFilterChange">
        <el-option label="全部" value="" />
        <el-option label="Agentic" value="agentic" />
        <el-option label="Simple" value="simple" />
      </el-select>
      <el-select v-model="filters.min_similarity" placeholder="最低相似度" clearable style="width: 160px;" @change="onFilterChange">
        <el-option label="全部" value="" />
        <el-option label="≥ 0.7" value="0.7" />
        <el-option label="0.4 - 0.7" value="0.4" />
        <el-option label="< 0.4" value="0" />
      </el-select>
      <el-input v-model="filters.search" placeholder="搜索查询关键词..." style="width: 280px;" clearable @change="onFilterChange" @clear="onFilterChange" />
    </div>

    <!-- Logs table -->
    <el-table
      :data="logs"
      v-loading="loading"
      style="width: 100%;"
      :row-class-name="rowClassName"
      empty-text="暂无检索日志"
    >
      <el-table-column prop="query" label="查询" min-width="200" show-overflow-tooltip />
      <el-table-column label="结果数" width="80">
        <template #default="{ row }">{{ row.result_count ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="Top-1 相似度" width="140">
        <template #default="{ row }">
          <el-tag
            v-if="row.top1_similarity != null"
            :type="row.top1_similarity >= 0.7 ? 'success' : row.top1_similarity >= 0.4 ? 'warning' : 'danger'"
            size="small"
          >
            {{ (row.top1_similarity * 100).toFixed(1) }}%
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="Judge" width="80">
        <template #default="{ row }">
          {{ typeof row.judge_score === 'object' ? ((row.judge_score?.relevance || 0) + (row.judge_score?.completeness || 0) + (row.judge_score?.noise || 0)) / 3 : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="耗时" width="80">
        <template #default="{ row }">{{ row.duration_ms ? row.duration_ms + 'ms' : '-' }}</template>
      </el-table-column>
      <el-table-column label="路由" width="80">
        <template #default="{ row }">{{ row.route_type || '-' }}</template>
      </el-table-column>
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}</template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <div style="margin-top: 16px; display: flex; justify-content: flex-end;">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="loadData"
        @size-change="loadData"
      />
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
}

.stat-label {
  font-size: 13px;
  color: #999;
  margin-top: 4px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

:deep(.row-low-quality) {
  border-left: 3px solid #ff4d4f;
  background: #fff2f0;
}
</style>

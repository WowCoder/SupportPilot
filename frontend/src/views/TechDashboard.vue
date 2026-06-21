<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getStats, listSessions } from '@/api/chat'
import { ElMessage } from 'element-plus'

const router = useRouter()

const stats = reactive({ total: 0, active: 0, needs_attention: 0, closed: 0 })
const recentSessions = ref([])
const allSessions = ref([])
const loading = ref(false)
const statusFilter = ref('')

const statusMap = {
  active: { label: '进行中', type: 'success' },
  needs_attention: { label: '待处理', type: 'warning' },
  closed: { label: '已关闭', type: 'info' },
}

const filteredSessions = computed(() => {
  if (!statusFilter.value) return allSessions.value
  return allSessions.value.filter((s) => s.status === statusFilter.value)
})

async function loadData() {
  loading.value = true
  try {
    // Load stats from the new stats endpoint
    const { data: statsData } = await getStats()
    if (statsData.data) {
      Object.assign(stats, statsData.data)
      recentSessions.value = statsData.data.recent_sessions || []
    }
    // Also load full session list
    const { data: sessionsData } = await listSessions()
    allSessions.value = sessionsData.data || []
  } catch (err) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

function goToSession(id) {
  router.push(`/chat/${id}`)
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(loadData)
</script>

<template>
  <div class="page-content">
    <h1 style="margin-bottom: 24px;">会话管理</h1>

    <!-- Stats cards -->
    <el-row :gutter="16" style="margin-bottom: 24px;">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ stats.total }}</div>
            <div class="stat-label">总会话数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card" style="color: #52c41a;">
            <div class="stat-value">{{ stats.active }}</div>
            <div class="stat-label">AI 服务中</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card" style="color: #faad14;">
            <div class="stat-value">{{ stats.needs_attention }}</div>
            <div class="stat-label">待介入</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card" style="color: #999;">
            <div class="stat-value">{{ stats.closed }}</div>
            <div class="stat-label">已关闭</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Filter -->
    <div style="display: flex; gap: 12px; margin-bottom: 16px; align-items: center;">
      <el-radio-group v-model="statusFilter" size="small">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="active">进行中</el-radio-button>
        <el-radio-button value="needs_attention">待介入</el-radio-button>
        <el-radio-button value="closed">已关闭</el-radio-button>
      </el-radio-group>
    </div>

    <!-- Sessions table -->
    <el-table :data="filteredSessions" v-loading="loading" empty-text="暂无会话" @row-click="goToSession" style="cursor: pointer; width: 100%;">
      <el-table-column label="会话 ID" min-width="80">
        <template #default="{ row }">#{{ row.id }}</template>
      </el-table-column>
      <el-table-column label="状态" min-width="100">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type" size="small">
            {{ statusMap[row.status]?.label || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="消息数" min-width="80">
        <template #default="{ row }">{{ row.message_count }}</template>
      </el-table-column>
      <el-table-column label="最后活动" min-width="160">
        <template #default="{ row }">{{ formatTime(row.last_message_at || row.created_at) }}</template>
      </el-table-column>
    </el-table>

    <!-- Quick links -->
    <el-row :gutter="16" style="margin-top: 32px;">
      <el-col :span="8">
        <el-card shadow="hover" @click="router.push('/faq')" style="cursor: pointer;">
          <div class="card-action">
            <el-icon :size="28" color="#52c41a"><Collection /></el-icon>
            <div><h4>FAQ 管理</h4><p style="font-size: 12px; color: #888;">管理知识库问答对</p></div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" @click="router.push('/upload')" style="cursor: pointer;">
          <div class="card-action">
            <el-icon :size="28" color="#1890ff"><UploadFilled /></el-icon>
            <div><h4>文档上传</h4><p style="font-size: 12px; color: #888;">上传知识库文档</p></div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" @click="router.push('/rag-dashboard')" style="cursor: pointer;">
          <div class="card-action">
            <el-icon :size="28" color="#722ed1"><DataAnalysis /></el-icon>
            <div><h4>RAG 仪表盘</h4><p style="font-size: 12px; color: #888;">检索性能监控</p></div>
          </div>
        </el-card>
      </el-col>
    </el-row>
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

.card-action {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-action h4 {
  margin: 0 0 2px;
  font-size: 14px;
}
</style>

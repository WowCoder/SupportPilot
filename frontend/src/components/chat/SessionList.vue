<script setup>
import { computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'

const chatStore = useChatStore()
const authStore = useAuthStore()

const statusLabels = {
  active: '进行中',
  needs_attention: '待处理',
  closed: '已关闭',
}

const statusTypes = {
  active: 'success',
  needs_attention: 'warning',
  closed: 'info',
}

const sortedSessions = computed(() => {
  return [...chatStore.sessions].sort((a, b) => {
    // Active first, then needs_attention, then closed
    const statusOrder = { active: 0, needs_attention: 1, closed: 2 }
    return (
      statusOrder[a.status] - statusOrder[b.status] ||
      new Date(b.last_message_at || b.created_at) - new Date(a.last_message_at || a.created_at)
    )
  })
})

function formatTime(isoString) {
  if (!isoString) return ''
  const d = new Date(isoString)
  const now = new Date()
  const diffDays = Math.floor((now - d) / (1000 * 60 * 60 * 24))
  if (diffDays === 0) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } else if (diffDays < 7) {
    return `${diffDays}天前`
  }
  return d.toLocaleDateString('zh-CN')
}
</script>

<template>
  <div class="session-list">
    <div class="session-list-header">
      <h3>会话列表</h3>
      <el-button
        v-if="authStore.currentUser?.role === 'user'"
        type="primary"
        size="small"
        @click="chatStore.newSession()"
      >
        新建会话
      </el-button>
    </div>
    <div class="session-items">
      <div
        v-for="session in sortedSessions"
        :key="session.id"
        class="session-item"
        :class="{
          active: chatStore.currentSessionId === session.id,
          closed: session.status === 'closed',
        }"
        @click="chatStore.selectSession(session.id)"
      >
        <div class="session-item-meta">
          <span class="session-id">#{{ session.id }}</span>
          <el-tag :type="statusTypes[session.status]" size="small">
            {{ statusLabels[session.status] }}
          </el-tag>
        </div>
        <div class="session-item-time">{{ formatTime(session.last_message_at || session.created_at) }}</div>
      </div>
      <div v-if="sortedSessions.length === 0" class="session-empty">
        暂无会话
      </div>
    </div>
  </div>
</template>

<style scoped>
.session-list {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.session-list-header {
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.session-list-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.session-items {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  padding: 14px 20px;
  cursor: pointer;
  border-bottom: 1px solid #f5f5f5;
  transition: background 0.15s;
}

.session-item:hover {
  background: #fafafa;
}

.session-item.active {
  background: #e6f7ff;
  border-right: 3px solid #1890ff;
}

.session-item.closed {
  opacity: 0.6;
}

.session-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.session-id {
  font-weight: 500;
  font-size: 14px;
}

.session-item-time {
  font-size: 12px;
  color: #aaa;
}

.session-empty {
  padding: 40px 20px;
  text-align: center;
  color: #aaa;
  font-size: 14px;
}
</style>

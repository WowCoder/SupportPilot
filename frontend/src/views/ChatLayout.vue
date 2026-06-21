<script setup>
import { onMounted, ref, watch, nextTick, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import SessionList from '@/components/chat/SessionList.vue'
import MessageBubble from '@/components/chat/MessageBubble.vue'
import ChatInput from '@/components/chat/ChatInput.vue'

const route = useRoute()
const chatStore = useChatStore()
const authStore = useAuthStore()

const messagesEl = ref(null)
const showScrollBtn = ref(false)
const closeDialogVisible = ref(false)
const generateFaq = ref(false)

onMounted(async () => {
  await chatStore.loadSessions()
  const sessionId = route.params.id
  if (sessionId) {
    chatStore.selectSession(Number(sessionId))
  }
})

// Watch route param changes
watch(() => route.params.id, (newId) => {
  if (newId) {
    chatStore.selectSession(Number(newId))
  }
})

// Auto-scroll to bottom when messages change
watch(() => chatStore.messages.length, () => {
  nextTick(() => scrollToBottom())
})

function scrollToBottom() {
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

function handleScroll() {
  const el = messagesEl.value
  if (!el) return
  const threshold = 100
  showScrollBtn.value = el.scrollHeight - el.scrollTop - el.clientHeight > threshold
}

async function handleClose() {
  await chatStore.closeCurrentSession(generateFaq.value)
  closeDialogVisible.value = false
  generateFaq.value = false
}

async function handleReopen() {
  await chatStore.reopenCurrentSession()
}

async function handleMarkAttention() {
  await chatStore.markCurrentAttention()
  ElMessage.success('已标记为需关注')
}

async function handleHandoff() {
  try {
    await chatStore.requestHumanHandoff()
    ElMessage.success('已请求人工介入，技术支持将尽快为您服务')
  } catch (err) {
    ElMessage.error('请求失败，请重试')
  }
}

// Session status helpers
const isActive = computed(() => chatStore.currentSession?.status === 'active')
const isNeedsAttention = computed(() => chatStore.currentSession?.status === 'needs_attention')
const isClosed = computed(() => chatStore.currentSession?.status === 'closed')
const isTechSupport = computed(() => authStore.isTechSupport)
</script>

<template>
  <div class="chat-layout">
    <!-- Left sidebar: session list -->
    <aside class="chat-sidebar">
      <SessionList />
    </aside>

    <!-- Right main: messages + input -->
    <main class="chat-main">
      <!-- Header with actions -->
      <header class="chat-header" v-if="chatStore.currentSession">
        <div class="chat-header-left">
          <h3>会话 #{{ chatStore.currentSession.id }}</h3>
          <el-tag
            :type="isActive ? 'success' : isNeedsAttention ? 'warning' : 'info'"
            size="small"
          >
            {{ isActive ? '进行中' : isNeedsAttention ? '待处理' : '已关闭' }}
          </el-tag>
        </div>
        <div class="chat-header-actions">
          <template v-if="isTechSupport">
            <el-button
              v-if="isActive"
              type="warning"
              size="small"
              @click="handleMarkAttention"
            >
              标记需关注
            </el-button>
            <el-button
              v-if="isActive || isNeedsAttention"
              type="danger"
              size="small"
              @click="closeDialogVisible = true"
            >
              关闭会话
            </el-button>
            <el-button
              v-if="isClosed"
              type="primary"
              size="small"
              @click="handleReopen"
            >
              重新打开
            </el-button>
          </template>
          <template v-else>
            <el-button
              v-if="isActive && chatStore.messages.length >= 6"
              type="warning"
              size="small"
              @click="handleHandoff"
            >
              请求人工介入
            </el-button>
            <el-button
              v-if="!isClosed"
              size="small"
              @click="closeDialogVisible = true"
            >
              关闭工单
            </el-button>
          </template>
        </div>
      </header>

      <!-- Status banner -->
      <el-alert
        v-if="isNeedsAttention"
        type="warning"
        title="此会话需要技术支持关注！技术支持团队将尽快为您处理"
        show-icon
        :closable="false"
      />
      <el-alert
        v-if="isClosed"
        type="info"
        title="此会话已关闭"
        show-icon
        :closable="false"
      />

      <!-- Messages area -->
      <div
        ref="messagesEl"
        class="chat-messages"
        @scroll="handleScroll"
        v-loading="chatStore.loading"
      >
        <div v-if="!chatStore.currentSession" class="chat-empty">
          <div class="empty-icon">💬</div>
          <p>选择一个会话开始对话</p>
          <el-button
            v-if="authStore.currentUser?.role === 'user'"
            type="primary"
            @click="chatStore.newSession()"
          >
            新建会话
          </el-button>
        </div>
        <template v-else>
          <MessageBubble
            v-for="msg in chatStore.messages"
            :key="msg.id"
            :message="msg"
          />
          <div v-if="chatStore.messages.length === 0 && !chatStore.loading" class="chat-empty">
            <p>还没有消息，开始对话吧</p>
          </div>
        </template>
      </div>

      <!-- Scroll to bottom button -->
      <transition name="fade">
        <el-button
          v-if="showScrollBtn"
          class="scroll-btn"
          circle
          size="small"
          @click="scrollToBottom"
        >
          ↓
        </el-button>
      </transition>

      <!-- Input area -->
      <ChatInput />
    </main>

    <!-- Close session dialog -->
    <el-dialog
      v-model="closeDialogVisible"
      title="关闭会话"
      width="400px"
    >
      <p>确认要关闭此会话吗？</p>
      <el-checkbox
        v-if="isTechSupport"
        v-model="generateFaq"
        style="margin-top: 12px;"
      >
        生成 FAQ — 从对话中提取 Q&A 对并录入知识库
      </el-checkbox>
      <template #footer>
        <el-button @click="closeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleClose">确认关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.chat-layout {
  display: flex;
  height: calc(100vh - 60px);
}

.chat-sidebar {
  width: 320px;
  border-right: 1px solid #e8e8e8;
  flex-shrink: 0;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fafafa;
  position: relative;
  min-width: 0;
}

.chat-header {
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.chat-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chat-header-left h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.chat-header-actions {
  display: flex;
  gap: 8px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #aaa;
  gap: 12px;
}

.empty-icon {
  font-size: 48px;
}

.scroll-btn {
  position: absolute;
  bottom: 100px;
  right: 24px;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

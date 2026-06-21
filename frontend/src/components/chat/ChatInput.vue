<script setup>
import { ref, computed } from 'vue'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()

const input = ref('')
const errorMsg = ref('')

const isDisabled = computed(() => {
  if (!chatStore.currentSession) return true
  return chatStore.currentSession.status === 'closed' || chatStore.sending
})

const placeholder = computed(() => {
  if (!chatStore.currentSession) return '请先选择或创建一个会话'
  if (chatStore.currentSession.status === 'closed') return '会话已关闭'
  return '输入您的问题，按 Enter 发送'
})

async function handleSend() {
  const text = input.value.trim()
  if (!text || isDisabled.value) return

  errorMsg.value = ''
  try {
    await chatStore.postMessage(text)
    input.value = ''
  } catch (err) {
    errorMsg.value = err.response?.data?.message || '发送失败，请重试'
  }
}

function handleKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="chat-input-area">
    <el-alert v-if="errorMsg" type="error" :title="errorMsg" show-icon closable @close="errorMsg = ''" />
    <div class="chat-input-inner">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        :placeholder="placeholder"
        :disabled="isDisabled"
        resize="none"
        @keydown="handleKeydown"
      />
      <el-button
        type="primary"
        :disabled="!input.trim() || isDisabled"
        :loading="chatStore.sending"
        @click="handleSend"
        class="send-btn"
      >
        发送
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.chat-input-area {
  padding: 16px 24px;
  background: #fff;
  border-top: 1px solid #e8e8e8;
}

.chat-input-inner {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.chat-input-inner :deep(.el-textarea) {
  flex: 1;
}

.send-btn {
  height: 40px;
  min-width: 72px;
}

.el-alert {
  margin-bottom: 8px;
}
</style>

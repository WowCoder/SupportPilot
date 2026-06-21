<script setup>
import { computed } from 'vue'
import MarkdownRenderer from '@/components/common/MarkdownRenderer.vue'

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
})

const isUser = computed(() => props.message.sender_type === 'user')
const isAI = computed(() => props.message.sender_type === 'ai')
const isTechSupport = computed(() => props.message.sender_type === 'tech_support')

const isThinking = computed(() => props.message._thinking)

const bubbleClass = computed(() => ({
  'bubble-user': isUser.value,
  'bubble-ai': isAI.value,
  'bubble-tech': isTechSupport.value,
  'bubble-thinking': isThinking.value,
}))

const senderLabel = computed(() => {
  if (isUser.value) return '您'
  if (isAI.value) return 'AI 助手'
  if (isTechSupport.value) return '技术支持'
  return ''
})

function formatTime(isoString) {
  if (!isoString) return ''
  return new Date(isoString).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div class="message-bubble" :class="bubbleClass">
    <div class="bubble-header">
      <span class="bubble-sender">{{ senderLabel }}</span>
      <span class="bubble-time">{{ formatTime(message.timestamp) }}</span>
    </div>
    <div class="bubble-content">
      <MarkdownRenderer v-if="isAI" :content="message.content" />
      <p v-else>{{ message.content }}</p>
    </div>
  </div>
</template>

<style scoped>
.message-bubble {
  max-width: 75%;
  margin: 8px 0;
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.6;
}

.bubble-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}

.bubble-sender {
  font-weight: 500;
}

.bubble-time {
  color: #999;
}

.bubble-content p {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

/* User message — right aligned, blue */
.bubble-user {
  margin-left: auto;
  background: #1890ff;
  color: #fff;
}

.bubble-user .bubble-sender {
  color: rgba(255, 255, 255, 0.85);
}

.bubble-user .bubble-time {
  color: rgba(255, 255, 255, 0.65);
}

/* AI message — left aligned, grey */
.bubble-ai {
  margin-right: auto;
  background: #f5f5f5;
  color: #333;
}

.bubble-ai .bubble-sender {
  color: #1890ff;
}

/* Tech support message — left aligned, grey with tint */
.bubble-tech {
  margin-right: auto;
  background: #fff7e6;
  border: 1px solid #ffe58f;
  color: #333;
}

.bubble-tech .bubble-sender {
  color: #fa8c16;
}

/* Thinking placeholder */
.bubble-thinking {
  margin-right: auto;
  background: #f5f5f5;
  color: #999;
  font-style: italic;
  animation: thinking-pulse 1.5s ease-in-out infinite;
}

@keyframes thinking-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}
</style>

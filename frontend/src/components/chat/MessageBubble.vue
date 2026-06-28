<script setup>
import { computed, ref } from 'vue'
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

const ragMetadata = computed(() => props.message._rag_metadata || null)
const showSources = ref(false)
const sourceExpanded = ref(false)

function formatTime(isoString) {
  if (!isoString) return ''
  return new Date(isoString).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function routeLabel(type) {
  return type === 'agentic' ? 'Agentic RAG' : '简单检索'
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

    <!-- RAG Sources (AI messages only) -->
    <div v-if="isAI && ragMetadata" class="rag-sources">
      <div class="rag-sources-toggle" @click="sourceExpanded = !sourceExpanded">
        <span class="toggle-icon">{{ sourceExpanded ? '▼' : '▶' }}</span>
        <span class="toggle-label">
          检索来源 · {{ ragMetadata.retrieval_count || 0 }} 条结果 · {{ routeLabel(ragMetadata.route_type) }}
        </span>
        <span v-if="ragMetadata.sub_query_count" class="rag-badge">{{ ragMetadata.sub_query_count }} 子查询</span>
        <span v-if="ragMetadata.retry_count" class="rag-badge retry">{{ ragMetadata.retry_count }} 重试</span>
      </div>
      <div v-if="sourceExpanded" class="rag-sources-list">
        <div class="rag-sources-meta">
          <span v-if="ragMetadata.faithfulness_score != null">
            忠实度: {{ (ragMetadata.faithfulness_score * 100).toFixed(0) }}%
          </span>
          <span v-if="ragMetadata.log_id">
            · <router-link :to="'/rag-dashboard'" class="rag-log-link">
              日志 #{{ ragMetadata.log_id }}
            </router-link>
          </span>
        </div>
        <div
          v-for="(src, idx) in (ragMetadata.top_sources || [])"
          :key="idx"
          class="rag-source-item"
        >
          <div class="rag-source-header">
            <span class="rag-source-index">#{{ idx + 1 }}</span>
            <span class="rag-source-score" :class="{
              'score-high': src.score >= 0.7,
              'score-mid': src.score >= 0.4 && src.score < 0.7,
              'score-low': src.score < 0.4,
            }">
              {{ (src.score * 100).toFixed(1) }}%
            </span>
            <span class="rag-source-name">{{ src.source || '未知来源' }}</span>
          </div>
          <div class="rag-source-content">{{ src.content }}</div>
        </div>
        <div v-if="!ragMetadata.top_sources?.length" class="rag-no-sources">
          暂无检索来源信息
        </div>
      </div>
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

/* ── RAG Sources ── */
.rag-sources {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #e8e8e8;
  font-size: 12px;
}

.rag-sources-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #8c8c8c;
  user-select: none;
  padding: 2px 0;
}

.rag-sources-toggle:hover {
  color: #595959;
}

.toggle-icon {
  font-size: 10px;
  width: 12px;
}

.toggle-label {
  flex: 1;
}

.rag-badge {
  display: inline-block;
  font-size: 10px;
  background: #f0f5ff;
  color: #2f54eb;
  padding: 1px 6px;
  border-radius: 2px;
}

.rag-badge.retry {
  background: #fff7e6;
  color: #d46b08;
}

.rag-sources-list {
  margin-top: 8px;
}

.rag-sources-meta {
  font-size: 11px;
  color: #8c8c8c;
  margin-bottom: 8px;
}

.rag-log-link {
  color: #409eff;
  text-decoration: none;
}

.rag-log-link:hover {
  text-decoration: underline;
}

.rag-source-item {
  margin-bottom: 8px;
  padding: 6px 8px;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
}

.rag-source-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.rag-source-index {
  font-weight: 600;
  color: #bfbfbf;
}

.rag-source-score {
  font-weight: 600;
  font-size: 11px;
  padding: 1px 4px;
  border-radius: 2px;
}

.score-high {
  color: #52c41a;
  background: #f6ffed;
}

.score-mid {
  color: #d48806;
  background: #fffbe6;
}

.score-low {
  color: #ff4d4f;
  background: #fff2f0;
}

.rag-source-name {
  color: #8c8c8c;
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rag-source-content {
  color: #595959;
  line-height: 1.4;
  font-size: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.rag-no-sources {
  color: #bfbfbf;
  font-style: italic;
}
</style>

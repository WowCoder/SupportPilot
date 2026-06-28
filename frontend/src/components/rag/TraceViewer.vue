<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  trace: {
    type: Object,
    default: null,
  },
})

const expandedNodes = ref(new Set())

// ---- Computed ----

const summary = computed(() => props.trace?.summary || {})
const events = computed(() => props.trace?.events || [])

// Group events by node invocation (node#visit)
const nodeGroups = computed(() => {
  const groups = []
  let currentStart = null

  for (const event of events.value) {
    if (event.phase === 'start') {
      currentStart = {
        node: event.node,
        label: event.label || event.node,
        visit: event.metadata?.visit || 1,
        timestamp_ms: event.timestamp_ms,
        input: event.input || {},
      }
    } else if (event.phase === 'end' && currentStart && currentStart.node === event.node) {
      groups.push({
        ...currentStart,
        timestamp_ms: currentStart.timestamp_ms,
        duration_ms: event.duration_ms || 0,
        output: event.output || {},
        metadata: event.metadata || {},
      })
      currentStart = null
    } else if (event.phase === 'decision') {
      groups.push({
        node: event.node,
        label: event.label || event.node,
        visit: 1,
        isDecision: true,
        timestamp_ms: event.timestamp_ms,
        duration_ms: 0,
        input: {},
        output: {},
        metadata: event.metadata || {},
      })
    } else if (event.phase === 'error') {
      groups.push({
        node: event.node,
        label: event.label || event.node,
        visit: 1,
        isError: true,
        timestamp_ms: event.timestamp_ms,
        duration_ms: 0,
        input: {},
        output: {},
        metadata: event.metadata || {},
      })
    }
  }

  // Calculate relative bar width based on duration
  const maxDuration = Math.max(1, ...groups.map(g => g.duration_ms || 0))
  groups.forEach(g => {
    g._barWidth = Math.max(2, ((g.duration_ms || 0) / maxDuration) * 100)
  })

  return groups
})

const totalDuration = computed(() => summary.value.total_duration_ms || 0)
const totalNodes = computed(() => nodeGroups.value.filter(g => !g.isDecision).length)
const decisionCount = computed(() => nodeGroups.value.filter(g => g.isDecision).length)
const errorCount = computed(() => nodeGroups.value.filter(g => g.isError).length)
const retryCount = computed(() => summary.value.retry_events || 0)

// ---- Helpers ----

function toggleExpand(label) {
  if (expandedNodes.value.has(label)) {
    expandedNodes.value.delete(label)
  } else {
    expandedNodes.value.add(label)
  }
}

function isExpanded(label) {
  return expandedNodes.value.has(label)
}

function formatMs(ms) {
  if (ms < 1) return '<1ms'
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatJson(obj) {
  if (!obj || Object.keys(obj).length === 0) return '(无)'
  return JSON.stringify(obj, null, 1)
    .replace(/^\{|\}$/g, '')
    .replace(/"/g, '')
    .replace(/,$/gm, '')
    .trim()
}

function decisionTagClass(decision) {
  const map = {
    pass_aggregate: 'success',
    pass_next_sub_query: 'success',
    pass_end: 'success',
    fail_retry: 'warning',
    fail_exhausted: 'danger',
    fail_global_retry: 'danger',
  }
  return map[decision] || 'info'
}

function decisionLabel(decision) {
  const map = {
    pass_aggregate: '✅ 通过 → 聚合',
    pass_next_sub_query: '✅ 通过 → 下一子查询',
    pass_end: '✅ 通过 → 完成',
    fail_retry: '🔄 重试',
    fail_exhausted: '⚠️ 重试耗尽',
    fail_global_retry: '🔄 全局重检索',
  }
  return map[decision] || decision
}
</script>

<template>
  <div v-if="!trace" class="trace-empty">
    <p>该查询未生成 trace 数据（可能为简单检索路径）</p>
  </div>

  <div v-else class="trace-viewer">
    <!-- Summary bar -->
    <div class="trace-summary">
      <div class="summary-item">
        <span class="summary-label">总耗时</span>
        <span class="summary-value">{{ formatMs(totalDuration) }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">节点数</span>
        <span class="summary-value">{{ totalNodes }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">决策点</span>
        <span class="summary-value">{{ decisionCount }}</span>
      </div>
      <div class="summary-item" v-if="retryCount > 0">
        <span class="summary-label">重试</span>
        <span class="summary-value" style="color: #e6a23c;">{{ retryCount }}</span>
      </div>
      <div class="summary-item" v-if="errorCount > 0">
        <span class="summary-label">错误</span>
        <span class="summary-value" style="color: #f56c6c;">{{ errorCount }}</span>
      </div>
    </div>

    <!-- Timeline -->
    <div class="trace-timeline">
      <div
        v-for="(group, idx) in nodeGroups"
        :key="`${group.node}-${group.visit}-${idx}`"
        class="timeline-group"
        :class="{
          'group-decision': group.isDecision,
          'group-error': group.isError,
          'group-retry': group.visit > 1,
        }"
      >
        <!-- Decision events -->
        <div v-if="group.isDecision" class="timeline-node decision-node">
          <div class="node-indicator">
            <div class="indicator-dot decision-dot"></div>
          </div>
          <div class="node-body">
            <div class="node-header" @click="toggleExpand(`decision-${idx}`)">
              <el-tag
                :type="decisionTagClass(group.metadata?.decision)"
                size="small"
              >
                {{ decisionLabel(group.metadata?.decision) }}
              </el-tag>
              <span class="node-time">{{ formatMs(group.timestamp_ms) }}</span>
              <span class="node-reason">{{ group.metadata?.reason || '' }}</span>
            </div>
          </div>
        </div>

        <!-- Error events -->
        <div v-else-if="group.isError" class="timeline-node error-node">
          <div class="node-indicator">
            <div class="indicator-dot error-dot"></div>
          </div>
          <div class="node-body">
            <div class="node-header">
              <span class="node-name">❌ {{ group.label }}</span>
              <span class="node-time">{{ formatMs(group.timestamp_ms) }}</span>
            </div>
            <div class="node-error-msg">{{ group.metadata?.error || '未知错误' }}</div>
          </div>
        </div>

        <!-- Node execution events -->
        <div v-else class="timeline-node exec-node">
          <div class="node-indicator">
            <div class="indicator-dot" :class="{ 'retry-dot': group.visit > 1 }"></div>
            <div v-if="idx < nodeGroups.length - 1" class="indicator-line"></div>
          </div>
          <div class="node-body">
            <div class="node-header" @click="toggleExpand(`${group.node}-${group.visit}`)">
              <span class="node-name">
                {{ group.label }}
                <span v-if="group.visit > 1" class="retry-badge">第{{ group.visit }}次</span>
              </span>
              <span class="node-duration" :style="{ color: group.duration_ms > 5000 ? '#f56c6c' : group.duration_ms > 2000 ? '#e6a23c' : '#67c23a' }">
                {{ formatMs(group.duration_ms) }}
              </span>
            </div>

            <!-- Duration bar -->
            <div class="duration-bar-bg">
              <div
                class="duration-bar-fill"
                :style="{
                  width: group._barWidth + '%',
                  background: group.duration_ms > 5000
                    ? 'linear-gradient(90deg, #f56c6c, #fab6b6)'
                    : group.duration_ms > 2000
                      ? 'linear-gradient(90deg, #e6a23c, #f0d78c)'
                      : 'linear-gradient(90deg, #67c23a, #b3e19d)',
                }"
              ></div>
            </div>

            <!-- Expandable details -->
            <div
              v-if="isExpanded(`${group.node}-${group.visit}`)"
              class="node-details"
            >
              <div v-if="Object.keys(group.input).length" class="detail-section">
                <div class="detail-label">输入</div>
                <pre class="detail-code">{{ formatJson(group.input) }}</pre>
              </div>
              <div v-if="Object.keys(group.output).length" class="detail-section">
                <div class="detail-label">输出</div>
                <pre class="detail-code">{{ formatJson(group.output) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.trace-empty {
  text-align: center;
  padding: 24px;
  color: #999;
  font-size: 13px;
}

.trace-viewer {
  font-size: 13px;
}

/* ── Summary ── */
.trace-summary {
  display: flex;
  gap: 20px;
  padding: 12px 16px;
  background: #fafafa;
  border-radius: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 60px;
}

.summary-label {
  font-size: 11px;
  color: #999;
  margin-bottom: 2px;
}

.summary-value {
  font-size: 18px;
  font-weight: 700;
  color: #303133;
}

/* ── Timeline ── */
.trace-timeline {
  position: relative;
}

.timeline-group {
  position: relative;
}

.timeline-node {
  display: flex;
  padding: 4px 0;
  min-height: 32px;
}

.node-indicator {
  position: relative;
  width: 24px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 6px;
}

.indicator-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #409eff;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px #409eff;
  z-index: 1;
  flex-shrink: 0;
}

.decision-dot {
  background: #e6a23c;
  box-shadow: 0 0 0 1px #e6a23c;
  width: 8px;
  height: 8px;
}

.error-dot {
  background: #f56c6c;
  box-shadow: 0 0 0 1px #f56c6c;
}

.retry-dot {
  background: #e6a23c;
  box-shadow: 0 0 0 1px #e6a23c;
}

.indicator-line {
  flex: 1;
  width: 1px;
  background: #dcdfe6;
  min-height: 8px;
}

.node-body {
  flex: 1;
  margin-left: 8px;
  padding-bottom: 8px;
}

.node-header {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 3px 6px;
  border-radius: 4px;
  transition: background 0.15s;
}

.node-header:hover {
  background: #f5f7fa;
}

.node-name {
  font-weight: 600;
  color: #303133;
}

.retry-badge {
  display: inline-block;
  font-size: 11px;
  background: #fdf6ec;
  color: #e6a23c;
  padding: 1px 6px;
  border-radius: 3px;
  margin-left: 4px;
  font-weight: 400;
}

.node-time {
  font-size: 11px;
  color: #909399;
  flex-shrink: 0;
}

.node-duration {
  font-size: 12px;
  font-weight: 600;
  margin-left: auto;
}

.node-reason {
  font-size: 12px;
  color: #606266;
  flex: 1;
}

.duration-bar-bg {
  height: 3px;
  background: #ebeef5;
  border-radius: 2px;
  margin: 4px 6px;
  overflow: hidden;
}

.duration-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* ── Details ── */
.node-details {
  margin: 8px 6px 4px;
  padding: 10px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.detail-section {
  margin-bottom: 8px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-label {
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
  font-weight: 600;
  text-transform: uppercase;
}

.detail-code {
  font-size: 12px;
  color: #606266;
  line-height: 1.5;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'SF Mono', 'Menlo', monospace;
  max-height: 200px;
  overflow-y: auto;
}

/* ── Decision ── */
.decision-node {
  padding: 2px 0;
}

.group-decision .node-body {
  padding-bottom: 4px;
}

/* ── Error ── */
.error-node .node-name {
  color: #f56c6c;
}

.node-error-msg {
  font-size: 12px;
  color: #f56c6c;
  margin-top: 2px;
  padding: 0 6px;
}

.group-retry {
  opacity: 0.85;
}
</style>

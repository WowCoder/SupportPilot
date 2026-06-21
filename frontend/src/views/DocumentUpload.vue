<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadDocument, listDocuments, deleteDocument, getDocStats } from '@/api/document'
import api from '@/api/index'

// --- AUTO mode ---
const autoMode = ref(false)

// --- State ---
const activeStep = ref(0)
const fileList = ref([])
const allFileList = ref([])
const docStats = reactive({ total_docs: 0, total_chunks: 0 })
const uploadedDocs = ref([])

// Step 1: File selection
const uploadRef = ref(null)

// Step 2: Cleaning options
const cleaningOptions = ref([
  { label: '移除页眉页脚', value: true },
  { label: '移除页码', value: true },
  { label: '清理噪音字符', value: true },
  { label: '规范化空白', value: true },
  { label: 'OCR 后处理', value: true },
  { label: '过滤非正文', value: true },
])
const cleaningPreview = ref(null)

// Step 3: Chunking
const chunkStrategy = ref('sentence')
const chunkSize = ref(400)
const overlapSize = ref(50)
const semanticThreshold = ref(0.5)
const enableSmallToBig = ref(true)
const bigChunkSize = ref(2000)
const chunkPreview = ref(null)

// Step 4: Upload
const uploadProgress = ref(0)
const uploadStatus = ref('')
const uploadResult = ref(null)

// Testing
const testQuery = ref('')
const testResults = ref([])
const testLoading = ref(false)

// --- Methods ---
function handleFileChange(file) {
  fileList.value = [file]
}

function beforeUpload(file) {
  const allowed = ['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
  const ext = file.name.split('.').pop().toLowerCase()
  const allowedExt = ['pdf', 'txt', 'doc', 'docx']

  if (!allowedExt.includes(ext)) {
    ElMessage.error('仅支持 PDF、TXT、DOC、DOCX 格式')
    return false
  }
  if (file.size > 16 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 16MB')
    return false
  }
  return true
}

function clearFile() {
  fileList.value = []
  uploadRef.value?.clearFiles()
}

async function previewCleaning() {
  cleaningPreview.value = {
    originalChars: 12840,
    cleanedChars: 9520,
    reduction: 25.8,
    originalText: '加载中...',
    cleanedText: '加载中...',
  }
  ElMessage.info('清洗预览功能需要后端 API 支持')
}

async function previewChunks() {
  const strategyNames = { sentence: '句子分块', semantic: '语义分块', recursive: '递归分块' }
  chunkPreview.value = {
    strategy: strategyNames[chunkStrategy.value],
    totalChunks: 12,
    totalChars: 9520,
    avgSize: 793,
    hasSmallToBig: enableSmallToBig.value,
    bigChunks: 3,
    smallChunks: 12,
  }
  ElMessage.info('分块预览功能需要后端 API 支持')
}

async function startUpload() {
  if (autoMode.value) {
    // AUTO mode: upload with defaults
    if (allFileList.value.length === 0) {
      ElMessage.warning('请先选择文件')
      return
    }
    uploadProgress.value = 20
    uploadStatus.value = '正在上传并处理...'
    try {
      const file = allFileList.value[0].raw || allFileList.value[0]
      const formData = new FormData()
      formData.append('file', file)
      formData.append('strategy', 'sentence')
      formData.append('use_small_to_big', 'true')
      formData.append('skip_cleaning', 'true')
      const { data } = await uploadDocument(formData)
      uploadProgress.value = 100
      uploadStatus.value = '上传成功!'
      uploadResult.value = { chunks: data.data.chunks_added }
      ElMessage.success(`文档已处理，添加 ${data.data.chunks_added} 个片段`)
      loadDocData()
    } catch (err) {
      uploadStatus.value = ''
      uploadProgress.value = 0
      ElMessage.error('上传失败: ' + (err.response?.data?.message || err.message))
    }
    return
  }

  // Wizard mode: collect all options and upload
  uploadProgress.value = 20
  uploadStatus.value = '正在上传并处理...'
  try {
    const file = fileList.value[0]?.raw || fileList.value[0]
    if (!file) {
      ElMessage.warning('请先选择文件')
      uploadProgress.value = 0
      uploadStatus.value = ''
      return
    }
    const formData = new FormData()
    formData.append('file', file)
    formData.append('strategy', chunkStrategy.value)
    formData.append('chunk_size', String(chunkSize.value))
    formData.append('use_small_to_big', enableSmallToBig.value ? 'true' : 'false')
    formData.append('skip_cleaning', 'false')
    const { data } = await uploadDocument(formData)
    uploadProgress.value = 100
    uploadStatus.value = '上传成功!'
    uploadResult.value = { chunks: data.data.chunks_added }
    ElMessage.success(`文档已处理，添加 ${data.data.chunks_added} 个片段`)
    loadDocData()
  } catch (err) {
    uploadStatus.value = ''
    uploadProgress.value = 0
    ElMessage.error('上传失败: ' + (err.response?.data?.message || err.message))
  }
}

function resetForm() {
  activeStep.value = 0
  fileList.value = []
  cleaningPreview.value = null
  chunkPreview.value = null
  uploadProgress.value = 0
  uploadStatus.value = ''
  uploadResult.value = null
}

function scrollToTest() {
  document.querySelector('.test-section')?.scrollIntoView({ behavior: 'smooth' })
}

async function loadDocData() {
  try {
    const [docsRes, statsRes] = await Promise.all([listDocuments(), getDocStats()])
    uploadedDocs.value = docsRes.data.data?.items || []
    if (statsRes.data.data) Object.assign(docStats, statsRes.data.data)
  } catch {
    // Silently ignore load errors
  }
}

async function handleDeleteDoc(doc) {
  try {
    await ElMessageBox.confirm('确认删除此文档？将从知识库中移除', '确认删除', { type: 'warning' })
    await deleteDocument(doc.id)
    ElMessage.success('文档已删除')
    loadDocData()
  } catch {
    // Cancelled or error
  }
}

onMounted(loadDocData)

async function runTestQuery() {
  if (!testQuery.value.trim()) {
    ElMessage.warning('请输入查询内容')
    return
  }
  testLoading.value = true
  testResults.value = []
  try {
    const { data } = await api.post('/api/test-query', { query: testQuery.value, k: 3 })
    if (data.success && data.results) {
      testResults.value = data.results
    } else {
      ElMessage.info('未找到相关结果')
    }
  } catch (err) {
    ElMessage.error('检索失败')
  } finally {
    testLoading.value = false
  }
}

// Step navigation
const canGoNext = computed(() => {
  if (activeStep.value === 0) return fileList.value.length > 0
  return true
})

function nextStep() {
  if (activeStep.value < 3) activeStep.value++
}

function prevStep() {
  if (activeStep.value > 0) activeStep.value--
}

function skipCleaning() {
  activeStep.value = 2
}
</script>

<template>
  <div class="page-content">
    <h1 style="margin-bottom: 16px;">上传知识库文档</h1>
    <div style="margin-bottom: 24px; display: flex; align-items: center; gap: 12px;">
      <el-switch v-model="autoMode" active-text="AUTO 模式 — 使用默认设置自动处理文档" />
    </div>

    <!-- Stats -->
    <el-row :gutter="16" style="margin-bottom: 24px;">
      <el-col :span="12">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ docStats.total_docs }}</div>
            <div class="stat-label">已上传文档数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ docStats.total_chunks }}</div>
            <div class="stat-label">知识库片段数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Upload wizard -->
    <!-- AUTO mode: simple upload -->
    <div v-if="autoMode" class="wizard-card">
      <h3 style="margin-bottom: 16px;">AUTO 模式</h3>
      <p style="color: #888; margin-bottom: 16px; font-size: 13px;">文档将使用默认设置自动处理：跳过清洗、句子分块、启用 Small-to-Big</p>
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :on-change="(f) => { allFileList = [f]; fileList = [f] }"
        :before-upload="beforeUpload"
        :limit="1"
        :file-list="allFileList"
        accept=".pdf,.txt,.doc,.docx"
      >
        <div class="upload-zone">
          <el-icon :size="48" color="#bbb"><UploadFilled /></el-icon>
          <p style="margin-top: 12px; color: #666;">将文件拖拽到此处，或点击选择</p>
          <p style="font-size: 12px; color: #aaa; margin-top: 4px;">支持 PDF / TXT / DOC / DOCX，最大 16MB</p>
        </div>
      </el-upload>
      <div v-if="allFileList.length > 0" style="margin-top: 24px;">
        <el-button type="primary" size="large" @click="startUpload" :disabled="uploadProgress > 0 && uploadProgress < 100">
          开始上传
        </el-button>
        <el-button @click="allFileList = []; fileList = []; uploadResult = null; uploadProgress = 0" style="margin-left: 8px;">清除</el-button>
      </div>
      <div v-if="uploadStatus" style="margin-top: 20px;">
        <el-progress :percentage="Math.round(uploadProgress)" :status="uploadProgress >= 100 ? 'success' : ''" />
        <p style="text-align: center; margin-top: 8px; color: #888;">{{ uploadStatus }}</p>
      </div>
    </div>

    <!-- Wizard mode -->
    <div v-else class="wizard-card">
      <el-steps :active="activeStep" align-center style="margin-bottom: 40px;">
        <el-step title="选择文档" />
        <el-step title="数据清洗" />
        <el-step title="分块设置" />
        <el-step title="完成上传" />
      </el-steps>

      <!-- Upload result -->
      <div v-if="uploadResult" class="upload-success">
        <el-result icon="success" title="上传成功！" sub-title="文档已成功添加到知识库">
          <template #extra>
            <el-button type="primary" @click="resetForm">继续上传</el-button>
            <el-button @click="scrollToTest">检索测试</el-button>
          </template>
        </el-result>
        <p style="text-align: center; margin-top: 8px; color: #888;">
          本次添加 {{ uploadResult.chunks }} 个知识库片段
        </p>
      </div>

      <!-- Step 1: File selection -->
      <div v-if="!uploadResult && activeStep === 0" class="step-panel">
        <el-upload
          ref="uploadRef"
          drag
          :auto-upload="false"
          :on-change="handleFileChange"
          :before-upload="beforeUpload"
          :limit="1"
          :file-list="fileList"
          accept=".pdf,.txt,.doc,.docx"
        >
          <div class="upload-zone">
            <el-icon :size="48" color="#bbb"><UploadFilled /></el-icon>
            <p style="margin-top: 12px; color: #666;">将文件拖拽到此处，或点击选择</p>
            <p style="font-size: 12px; color: #aaa; margin-top: 4px;">支持 PDF / TXT / DOC / DOCX，最大 16MB</p>
          </div>
        </el-upload>
        <div v-if="fileList.length > 0" style="margin-top: 16px; display: flex; gap: 8px;">
          <el-button @click="clearFile">清除文件</el-button>
        </div>
      </div>

      <!-- Step 2: Cleaning -->
      <div v-if="!uploadResult && activeStep === 1" class="step-panel">
        <h4>数据清洗选项</h4>
        <el-checkbox-group v-model="cleaningOptions" style="display: flex; flex-wrap: wrap; gap: 16px;">
          <el-checkbox v-for="(opt, idx) in cleaningOptions" :key="idx" :label="opt.label" :value="opt.value" />
        </el-checkbox-group>
        <div style="margin-top: 24px; display: flex; gap: 12px;">
          <el-button @click="previewCleaning">预览清洗效果</el-button>
          <el-button @click="skipCleaning">跳过清洗</el-button>
        </div>
        <!-- Cleaning preview -->
        <div v-if="cleaningPreview" style="margin-top: 20px;">
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="原始字符">{{ cleaningPreview.originalChars }}</el-descriptions-item>
            <el-descriptions-item label="清洗后">{{ cleaningPreview.cleanedChars }}</el-descriptions-item>
            <el-descriptions-item label="缩减">{{ cleaningPreview.reduction }}%</el-descriptions-item>
          </el-descriptions>
        </div>
      </div>

      <!-- Step 3: Chunking -->
      <div v-if="!uploadResult && activeStep === 2" class="step-panel">
        <h4>分块策略</h4>
        <el-radio-group v-model="chunkStrategy" style="display: flex; flex-direction: column; gap: 12px;">
          <el-radio value="sentence" border>
            <strong>句子分块</strong> （推荐）— 按句子边界分块，适合技术文档和编号列表
          </el-radio>
          <el-radio value="semantic" border>
            <strong>语义分块</strong> — 基于 embedding 相似度，适合连续文本
          </el-radio>
          <el-radio value="recursive" border>
            <strong>递归分块</strong> — 按固定字符数切分，速度最快
          </el-radio>
        </el-radio-group>

        <!-- Parameters (dynamic) -->
        <div style="margin-top: 20px;">
          <el-form label-width="120px" size="small">
            <template v-if="chunkStrategy === 'sentence' || chunkStrategy === 'recursive'">
              <el-form-item label="分块大小">
                <el-input-number v-model="chunkSize" :min="100" :max="2000" :step="100" />
              </el-form-item>
              <el-form-item v-if="chunkStrategy === 'recursive'" label="重叠大小">
                <el-input-number v-model="overlapSize" :min="0" :max="500" :step="10" />
              </el-form-item>
            </template>
            <template v-if="chunkStrategy === 'semantic'">
              <el-form-item label="语义阈值">
                <el-slider v-model="semanticThreshold" :min="0.1" :max="0.9" :step="0.05" show-input style="width:300px;" />
              </el-form-item>
            </template>
          </el-form>
        </div>

        <!-- Small-to-Big -->
        <el-divider />
        <el-switch v-model="enableSmallToBig" active-text="启用 Small-to-Big 检索策略" />
        <div v-if="enableSmallToBig" style="margin-top: 12px;">
          <el-form label-width="120px" size="small" inline>
            <el-form-item label="大块大小">
              <el-input-number v-model="bigChunkSize" :min="500" :max="5000" :step="100" />
            </el-form-item>
            <el-form-item label="小块大小">
              <el-input-number v-model="chunkSize" :min="100" :max="1000" :step="50" />
            </el-form-item>
          </el-form>
        </div>

        <el-button style="margin-top: 20px;" @click="previewChunks">预览分块效果</el-button>

        <!-- Chunk preview -->
        <div v-if="chunkPreview" style="margin-top: 16px;">
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="策略">{{ chunkPreview.strategy }}</el-descriptions-item>
            <el-descriptions-item label="总块数">{{ chunkPreview.totalChunks }}</el-descriptions-item>
            <el-descriptions-item label="平均大小">{{ chunkPreview.avgSize }} 字符</el-descriptions-item>
            <template v-if="chunkPreview.hasSmallToBig">
              <el-descriptions-item label="大块数">{{ chunkPreview.bigChunks }}</el-descriptions-item>
              <el-descriptions-item label="小块数">{{ chunkPreview.smallChunks }}</el-descriptions-item>
            </template>
          </el-descriptions>
        </div>
      </div>

      <!-- Step 4: Confirmation -->
      <div v-if="!uploadResult && activeStep === 3" class="step-panel">
        <h4>上传确认</h4>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="文件名">{{ fileList[0]?.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="大小">{{ fileList[0] ? (fileList[0].size / 1024).toFixed(1) + ' KB' : '-' }}</el-descriptions-item>
          <el-descriptions-item label="清洗">{{ cleaningPreview ? '已配置' : '跳过' }}</el-descriptions-item>
          <el-descriptions-item label="分块策略">{{ { sentence: '句子分块', semantic: '语义分块', recursive: '递归分块' }[chunkStrategy] }}</el-descriptions-item>
          <el-descriptions-item label="Small-to-Big">{{ enableSmallToBig ? '启用' : '禁用' }}</el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 24px;">
          <el-button type="primary" size="large" @click="startUpload" :disabled="uploadProgress > 0 && uploadProgress < 100">
            开始上传
          </el-button>
        </div>

        <!-- Progress -->
        <div v-if="uploadStatus" style="margin-top: 20px;">
          <el-progress :percentage="Math.round(uploadProgress)" :status="uploadProgress >= 100 ? 'success' : ''" />
          <p style="text-align: center; margin-top: 8px; color: #888;">{{ uploadStatus }}</p>
        </div>
      </div>

      <!-- Step navigation -->
      <div v-if="!uploadResult && uploadProgress === 0" style="display: flex; justify-content: space-between; margin-top: 40px; padding-top: 20px; border-top: 1px solid #f0f0f0;">
        <el-button :disabled="activeStep === 0" @click="prevStep">上一步</el-button>
        <el-button v-if="activeStep < 3" type="primary" :disabled="!canGoNext" @click="nextStep">下一步</el-button>
      </div>
    </div>

    <!-- RAG Test section -->
    <div class="test-section" style="margin-top: 40px;">
      <h2 style="margin-bottom: 16px;">检索测试</h2>
      <el-card>
        <div style="display: flex; gap: 12px; margin-bottom: 16px;">
          <el-input v-model="testQuery" placeholder="输入查询测试检索效果..." style="flex: 1;" />
          <el-button type="primary" :loading="testLoading" @click="runTestQuery">开始检索</el-button>
        </div>
        <div v-if="testResults.length > 0">
          <div v-for="(r, idx) in testResults" :key="idx" class="test-result-item">
            <span class="similarity" :class="r.similarity >= 0.7 ? 'high' : r.similarity >= 0.4 ? 'mid' : 'low'">
              {{ (r.similarity * 100).toFixed(1) }}%
            </span>
            <span class="source">{{ r.source }}</span>
            <p>{{ r.content }}</p>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Uploaded documents list -->
    <div style="margin-top: 40px; margin-bottom: 40px;">
      <h2 style="margin-bottom: 16px;">已上传文档</h2>
      <el-table :data="uploadedDocs" empty-text="暂无上传的文档" style="width: 100%;">
        <el-table-column label="文件" min-width="200">
          <template #default="{ row }">
            <span :style="{ color: row.filename?.endsWith('.pdf') ? '#ff4d4f' : row.filename?.endsWith('.docx') ? '#1890ff' : '#666' }">
              📄 {{ row.filename }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="片段数" width="80">
          <template #default="{ row }">{{ row.chunks_count }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">
              {{ row.status === 'completed' ? '已完成' : row.status === 'failed' ? '失败' : '处理中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="140">
          <template #default="{ row }">{{ row.uploaded_at || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="handleDeleteDoc(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
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

.wizard-card {
  background: #fff;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.step-panel {
  min-height: 200px;
}

.step-panel h4 {
  margin-bottom: 16px;
  font-size: 15px;
}

.upload-zone {
  padding: 40px 20px;
}

.upload-success {
  padding: 40px 0;
}

.test-result-item {
  padding: 12px;
  border-bottom: 1px solid #f5f5f5;
}

.test-result-item .similarity {
  display: inline-block;
  font-weight: 600;
  margin-right: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
}

.similarity.high { background: #f6ffed; color: #52c41a; }
.similarity.mid { background: #fffbe6; color: #faad14; }
.similarity.low { background: #fff2f0; color: #ff4d4f; }

.test-result-item .source {
  color: #888;
  font-size: 12px;
}

.test-result-item p {
  margin: 8px 0 0;
  font-size: 13px;
  color: #555;
}
</style>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
</script>

<template>
  <div class="page-content">
    <h1 style="margin-bottom: 24px;">用户仪表盘</h1>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="hover">
          <div class="card-action" @click="router.push('/chat')" style="cursor: pointer;">
            <el-icon :size="32" color="#1890ff"><ChatDotRound /></el-icon>
            <div>
              <h3>我的会话</h3>
              <p style="color: #888; font-size: 13px;">查看和处理您的客服会话</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <div class="card-action" @click="router.push('/chat')" style="cursor: pointer;">
            <el-icon :size="32" color="#52c41a"><Plus /></el-icon>
            <div>
              <h3>新建会话</h3>
              <p style="color: #888; font-size: 13px;">开始一个新的客服会话</p>
            </div>
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

.card-action {
  display: flex;
  align-items: center;
  gap: 16px;
}

.card-action h3 {
  margin: 0 0 4px;
  font-size: 16px;
}
</style>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <header class="topnav">
    <div class="topnav-brand">
      <span class="logo-dot"></span>
      <span class="brand-text">SupportPilot</span>
    </div>
    <nav class="topnav-links">
      <router-link v-if="!authStore.isTechSupport" to="/chat">客服对话</router-link>
      <template v-if="authStore.isTechSupport">
        <router-link to="/tech-dashboard">会话管理</router-link>
        <router-link to="/faq">FAQ 管理</router-link>
        <router-link to="/upload">文档上传</router-link>
        <router-link to="/rag-dashboard">RAG 仪表盘</router-link>
      </template>
    </nav>
    <div class="topnav-user">
      <span v-if="authStore.currentUser" class="user-info">
        {{ authStore.currentUser.username }}
        <el-tag size="small" :type="authStore.isTechSupport ? 'warning' : 'info'">
          {{ authStore.isTechSupport ? '技术支持' : '用户' }}
        </el-tag>
      </span>
      <el-button text @click="handleLogout">退出</el-button>
    </div>
  </header>
</template>

<style scoped>
.topnav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  padding: 0 24px;
  z-index: 1000;
  gap: 24px;
}

.topnav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #1890ff;
}

.logo-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #1890ff;
  display: inline-block;
}

.topnav-links {
  display: flex;
  gap: 8px;
  flex: 1;
}

.topnav-links a {
  text-decoration: none;
  color: #555;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 14px;
  transition: all 0.2s;
}

.topnav-links a:hover,
.topnav-links a.router-link-active {
  color: #1890ff;
  background: rgba(24, 144, 255, 0.06);
}

.topnav-user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}
</style>

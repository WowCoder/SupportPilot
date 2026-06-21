<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppTopnav from '@/components/layout/AppTopnav.vue'

const route = useRoute()

// Hide topnav on auth pages (login/register)
const showTopnav = computed(() => {
  return !route.meta.guest
})
</script>

<template>
  <div id="app-shell">
    <AppTopnav v-if="showTopnav" />
    <main :class="{ 'has-topnav': showTopnav }">
      <router-view />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif;
  background-color: #f0f2f5;
  color: #333;
}

#app-shell {
  min-height: 100vh;
}

main.has-topnav {
  padding-top: 60px;
  min-height: 100vh;
}
</style>

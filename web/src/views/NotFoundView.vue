<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="not-found">
    <h1>404</h1>
    <p>页面不存在</p>
    <router-link to="/">返回首页</router-link>
  </div>
</template>

<style scoped>
.not-found {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--gray-0);
  color: var(--color-text);
  gap: 8px;
}

.not-found h1 {
  font-size: 48px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.not-found a {
  color: var(--main-color);
  text-decoration: none;
}

.not-found a:hover {
  color: var(--main-700);
}
</style>

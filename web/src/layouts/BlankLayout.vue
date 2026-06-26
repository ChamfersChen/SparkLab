<script setup>
/**
 * 空白布局 - 无侧边栏，无顶栏。
 * 用于欢迎页 `/`、登录 `/login`、激活 `/activate`、404 等公开页面。
 */
</script>

<template>
  <div class="blank-layout">
    <slot />
  </div>
</template>

<style scoped>
.blank-layout {
  min-height: 100vh;
  background: var(--gray-10);
}
</style>

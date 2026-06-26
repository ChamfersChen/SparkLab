<script setup>
/**
 * 根组件 - 根据路由 meta.layout 动态选择布局。
 *
 * - 默认（无 layout 或 layout='blank'）：BlankLayout，无侧边栏
 * - layout='app'：AppLayout，左侧固定导航 + 右侧内容区
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import BlankLayout from '@/layouts/BlankLayout.vue'

const route = useRoute()

const layoutComponent = computed(() => {
  return route.meta?.layout === 'app' ? 'app-layout' : 'blank-layout'
})
</script>

<template>
  <AppLayout v-if="layoutComponent === 'app-layout'">
    <router-view />
  </AppLayout>
  <BlankLayout v-else>
    <router-view />
  </BlankLayout>
</template>

<style>
#app {
  min-height: 100vh;
}
</style>

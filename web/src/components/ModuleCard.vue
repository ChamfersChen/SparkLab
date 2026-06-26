<script setup>
/**
 * 功能入口卡片 - Dashboard 首页用，未来其他工作台页可复用。
 *
 * 设计要点：
 * - 整卡可点击（disabled 时仍渲染，但 hover/click 无效）
 * - icon 槽位通过 lucide 组件传入，避免内置图标列表
 * - disabled 时右上角显示"敬请期待" badge，文字保持可读
 */
import { computed } from 'vue'

const props = defineProps({
  icon: { type: [Object, Function], required: true },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  badge: { type: String, default: '' }
})

const emit = defineEmits(['click'])

const cardClass = computed(() => ({
  'module-card': true,
  'module-card--disabled': props.disabled
}))

function handleClick() {
  if (props.disabled) return
  emit('click')
}
</script>

<template>
  <button :class="cardClass" type="button" :aria-disabled="disabled" @click="handleClick">
    <span class="icon-wrap">
      <component :is="icon" :size="22" :stroke-width="2" />
    </span>
    <div class="text">
      <div class="title-row">
        <span class="title">{{ title }}</span>
        <span v-if="badge" class="badge">{{ badge }}</span>
      </div>
      <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
    </div>
  </button>
</template>

<style scoped>
.module-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  width: 100%;
  padding: 20px;
  background: var(--gray-0);
  border: 1px solid var(--gray-50);
  border-radius: 10px;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease;
  font: inherit;
  color: inherit;
}

.module-card:hover:not(.module-card--disabled) {
  border-color: var(--main-30);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.module-card:hover:not(.module-card--disabled) .icon-wrap {
  background: var(--main-30);
  color: var(--main-700);
}

.module-card--disabled {
  cursor: not-allowed;
  opacity: 0.85;
}

.icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--main-10);
  color: var(--main-color);
  flex-shrink: 0;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.text {
  flex: 1;
  min-width: 0;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  font-size: 11px;
  line-height: 18px;
  font-weight: 500;
  color: var(--gray-600);
  background: var(--gray-25);
  border-radius: 10px;
  border: 1px solid var(--gray-50);
}

.subtitle {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--color-text-secondary);
}
</style>

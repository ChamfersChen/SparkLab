<script setup>
/**
 * 渐变背景 + 浮动圆形动画组件。
 *
 * 用于 Login、Activate、Dashboard Hero 等页面，
 * 提供科技感视觉背景。
 */
</script>

<template>
  <div class="animated-bg">
    <div class="circle circle-1" />
    <div class="circle circle-2" />
    <div class="circle circle-3" />
    <div class="circle circle-4" />
    <div class="circle circle-5" />
    <slot />
  </div>
</template>

<style scoped>
.animated-bg {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #1e40af, #3b82f6, #60a5fa);
}

.circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  pointer-events: none;
}

.circle-1 {
  width: 200px;
  height: 200px;
  top: -40px;
  right: -60px;
  animation: float-1 25s ease-in-out infinite;
}

.circle-2 {
  width: 160px;
  height: 160px;
  bottom: -30px;
  left: -40px;
  animation: float-2 30s ease-in-out infinite;
}

.circle-3 {
  width: 120px;
  height: 120px;
  top: 50%;
  left: 30%;
  background: rgba(255, 255, 255, 0.06);
  animation: float-3 22s ease-in-out infinite;
}

.circle-4 {
  width: 80px;
  height: 80px;
  top: 20%;
  right: 25%;
  background: rgba(255, 255, 255, 0.1);
  animation: float-4 28s ease-in-out infinite;
}

.circle-5 {
  width: 100px;
  height: 100px;
  bottom: 25%;
  right: 10%;
  background: rgba(255, 255, 255, 0.07);
  animation: float-5 20s ease-in-out infinite;
}

@keyframes float-1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(-30px, 40px) scale(1.05); }
  66% { transform: translate(20px, -20px) scale(0.95); }
}

@keyframes float-2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(40px, -30px) scale(1.08); }
  66% { transform: translate(-20px, 20px) scale(0.92); }
}

@keyframes float-3 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(30px, -40px) scale(1.1); }
}

@keyframes float-4 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-25px, 30px) scale(0.9); }
}

@keyframes float-5 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(20px, -20px) scale(1.05); }
  66% { transform: translate(-15px, 25px) scale(0.95); }
}
</style>

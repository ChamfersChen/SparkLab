<script setup>
/**
 * Dashboard 首页（登录后默认落地页）。
 *
 * 功能介绍页：平台简介 + 核心功能卡片 + 使用流程 + 快捷入口。
 * 仅登录用户可见。
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { FileText, BookOpen, Heart, ArrowRight, Layers } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { logout as apiLogout } from '@/apis/auth_api'
import AnimatedBg from '@/components/AnimatedBg.vue'

const userStore = useUserStore()

const router = useRouter()

function goTemplates() {
  router.push('/templates')
}

function goPlaybooks() {
  router.push('/playbooks')
}

const ROLE_META = {
  super_admin: { label: '超管', color: 'red' },
  admin: { label: '管理员', color: 'orange' },
  user: { label: '用户', color: 'default' },
}
const roleMeta = computed(() => ROLE_META[userStore.user?.role] || ROLE_META.user)

async function handleLogout() {
  try {
    await apiLogout()
  } catch {
    // 即使后端登出失败也清除本地状态
  }
  userStore.logout()
  router.push({ name: 'login' })
}

const features = [
  {
    icon: FileText,
    title: 'Prompt 模板',
    desc: '五段式结构化模板，按表单填空即可生成专业提示词',
  },
  {
    icon: BookOpen,
    title: '流程 Playbook',
    desc: '多步骤流程编排，按顺序完成一套完整的创作任务',
  },
  {
    icon: Heart,
    title: '收藏管理',
    desc: '收藏常用的模板和流程，快速访问',
  },
]

const steps = [
  '管理员发布模板和流程',
  '用户选择并填写表单',
  '生成专业提示词',
  '复制到 AI 平台使用',
]
</script>

<template>
  <AnimatedBg class="dashboard">
    <header class="dash-header">
      <router-link to="/" class="brand">
        <img src="/favicon-g.svg" alt="logo" width="35" height="35" />
        <span>SparkLab</span>
      </router-link>

      <nav class="header-nav">
        <a class="nav-link" @click="goTemplates">
          <FileText :size="16" :stroke-width="2" />
          模板库
        </a>
        <a class="nav-link" @click="goPlaybooks">
          <BookOpen :size="16" :stroke-width="2" />
          流程库
        </a>
      </nav>

      <div class="header-right">
        <a-dropdown v-if="userStore.user" placement="bottomRight">
          <span class="user-trigger">
            <span class="username">{{ userStore.user.username }}</span>
            <a-tag :color="roleMeta.color" class="role-tag">{{ roleMeta.label }}</a-tag>
          </span>
          <template #overlay>
            <a-menu>
              <a-menu-item key="logout" @click="handleLogout">退出登录</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </header>

    <!-- Hero -->
    <div class="hero">
      <h1 class="hero-title">SparkLab</h1>
      <p class="hero-subtitle">让团队的 AI 提示词资产沉淀下来</p>
      <a-button type="primary" size="large" ghost class="hero-btn" @click="goTemplates">
        开始使用
        <template #icon><ArrowRight :size="16" :stroke-width="2" /></template>
      </a-button>
    </div>

    <!-- 内容区 -->
    <div class="body">
      <!-- 核心功能 -->
      <section class="section">
        <h2 class="section-title">
          <Layers :size="18" :stroke-width="2" />
          核心功能
        </h2>
        <div class="feature-grid">
          <div v-for="item in features" :key="item.title" class="feature-card">
            <div class="feature-icon">
              <component :is="item.icon" :size="24" :stroke-width="1.75" />
            </div>
            <h3 class="feature-title">{{ item.title }}</h3>
            <p class="feature-desc">{{ item.desc }}</p>
          </div>
        </div>
      </section>

      <!-- 使用流程 -->
      <section class="section">
        <h2 class="section-title">使用流程</h2>
        <div class="steps-card">
          <div v-for="(step, idx) in steps" :key="idx" class="step">
            <span class="step-num">{{ idx + 1 }}</span>
            <span class="step-text">{{ step }}</span>
            <ArrowRight v-if="idx < steps.length - 1" :size="16" :stroke-width="2" class="step-arrow" />
          </div>
        </div>
      </section>

      <!-- 快捷入口 -->
    </div>
  </AnimatedBg>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
}

/* ---------- Header ---------- */
.dash-header {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 32px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  text-decoration: none;
}

.brand:hover {
  color: rgba(255, 255, 255, 0.85);
}

.header-nav {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  text-decoration: none;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

.header-right {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.user-trigger:hover {
  background: rgba(255, 255, 255, 0.12);
}

.username {
  font-size: 14px;
  color: #fff;
  font-weight: 500;
}

.role-tag {
  margin: 0;
}

/* ---------- Hero ---------- */
.hero {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 48px 32px 64px;
}

.hero-title {
  margin: 0 0 12px;
  font-size: 40px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.5px;
}

.hero-subtitle {
  margin: 0 0 28px;
  font-size: 17px;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.6;
}

.hero-btn {
  height: 42px;
  padding: 0 28px;
  border-radius: 8px;
  font-size: 15px;
  border-color: rgba(255, 255, 255, 0.4);
  color: #fff;
}

.hero-btn:hover {
  background: rgba(255, 255, 255, 0.15) !important;
  border-color: rgba(255, 255, 255, 0.6) !important;
  color: #fff !important;
}

/* ---------- Body ---------- */
.body {
  position: relative;
  z-index: 1;
  max-width: 800px;
  margin: 0 auto;
  padding: 0 32px 80px;
}

/* ---------- Section ---------- */
.section {
  margin-bottom: 48px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 20px;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

/* ---------- Feature Cards ---------- */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.feature-card {
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 8px;
  padding: 24px;
  text-align: center;
  transition: background 0.15s, border-color 0.15s;
}

.feature-card:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.35);
}

.feature-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  margin-bottom: 16px;
}

.feature-title {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

.feature-desc {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
}

/* ---------- Steps ---------- */
.steps-card {
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 8px;
  padding: 24px 32px;
}

.step {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.step-text {
  font-size: 14px;
  color: #fff;
}

.step-arrow {
  margin-left: auto;
  color: rgba(255, 255, 255, 0.45);
  flex-shrink: 0;
}

.step + .step {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed rgba(255, 255, 255, 0.15);
}

/* ---------- Responsive ---------- */
@media (max-width: 768px) {
  .dash-header {
    padding: 0 16px;
  }

  .header-nav {
    gap: 0;
  }

  .nav-link {
    padding: 6px 8px;
    font-size: 13px;
  }

  .hero {
    padding: 32px 16px 48px;
  }

  .hero-title {
    font-size: 28px;
  }

  .body {
    padding: 0 16px 64px;
  }

  .feature-grid {
    grid-template-columns: 1fr;
  }

  .steps-card {
    padding: 20px 16px;
  }

  .step-arrow {
    display: none;
  }
}
</style>

<script setup>
/**
 * Dashboard 首页（登录后默认落地页）。
 *
 * 阶段角色：
 * - 当前为骨架阶段：业务模块（Templates/Playbooks/News/Admin）均未上线，
 *   全部以 disabled 卡片形式呈现，给用户"未来会有什么"的预期，而不堆假数据。
 * - 业务模块上线时，把对应 module 的 disabled 改 false 并配上 to/handler 即可。
 */
import { computed } from 'vue'
import { FileText, BookOpen, Newspaper, Settings, Sparkles, LogIn, ArrowRight } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import AppHeader from '@/components/AppHeader.vue'
import ModuleCard from '@/components/ModuleCard.vue'

const userStore = useUserStore()

const greeting = computed(() => {
  if (!userStore.isLoggedIn) return '欢迎来到 SparkLab'
  const name = userStore.user?.username || '探索者'
  return `欢迎回来，${name}`
})

const subtitle = computed(() =>
  userStore.isLoggedIn
    ? '把繁杂的 AI 操作收敛为可复用的模板与剧本，按表单填空即可上手 —— 让团队的提示词资产沉淀下来。'
    : '管理员发布模板与剧本，付费用户持激活码注册后即可使用 —— 按表单填空，生成可直接拷贝的专业提示词。'
)

// ---------- Hero 区按钮处理（UI 阶段：仅 stub，handler 留待 Phase 4 接入） ----------

function handleLogin() {
  // TODO(Phase 4): router.push({ name: 'login' })
  // 当前 UI 阶段不触发跳转
  console.info('[stub] 登录按钮点击')
}

function handleEnterSystem() {
  // TODO(Phase 5): 跳转到首个业务模块（如 templates 列表）
  // router.push({ name: 'templates' })
  console.info('[stub] 进入系统按钮点击')
}

// 业务模块清单 - 业务上线时把对应项 disabled 改 false 并补 to/handler。
const ALL_MODULES = [
  {
    key: 'templates',
    icon: FileText,
    title: 'Prompt 模板',
    subtitle: '把好用的提示词沉淀为可复用的模板，按表单填空即可生成。',
    disabled: true,
    badge: '敬请期待'
  },
  {
    key: 'playbooks',
    icon: BookOpen,
    title: 'Playbook 剧本',
    subtitle: '把多步骤的 AI 操作编排成一份剧本，按步骤拷贝执行。',
    disabled: true,
    badge: '敬请期待'
  },
  {
    key: 'news',
    icon: Newspaper,
    title: 'AI 资讯',
    subtitle: '由管理员维护的精选行业资讯与解读。',
    disabled: true,
    badge: '敬请期待'
  },
  {
    key: 'admin',
    icon: Settings,
    title: '管理后台',
    subtitle: '管理模板、剧本、资讯与激活码。',
    disabled: true,
    badge: '敬请期待',
    adminOnly: true
  }
]

const visibleModules = computed(() =>
  ALL_MODULES.filter((m) => !m.adminOnly || userStore.isAdmin)
)

// 支持的第三方 AI 平台 - 仅展示用，提示用户"模板可用于哪里"
const PLATFORMS = ['DeepSeek', 'Kimi', '豆包', '通义千问']
</script>

<template>
  <a-layout class="dashboard">
    <AppHeader />

    <a-layout-content class="content">
      <section class="hero">
        <div class="hero-eyebrow">
          <Sparkles :size="14" :stroke-width="2.25" />
          <span>SparkLab · AI 内容运营平台</span>
        </div>
        <h1 class="hero-title">{{ greeting }}</h1>
        <p class="hero-subtitle">{{ subtitle }}</p>

        <div class="hero-actions">
          <template v-if="userStore.isLoggedIn">
            <a-button type="primary" size="large" @click="handleEnterSystem">
              <template #icon><ArrowRight :size="16" :stroke-width="2.25" /></template>
              进入系统
            </a-button>
          </template>
          <template v-else>
            <a-button type="primary" size="large" @click="handleLogin">
              <template #icon><LogIn :size="16" :stroke-width="2.25" /></template>
              登录
            </a-button>
            <span class="hero-actions-hint">
              注册需通过管理员发放的激活码邀请链接
            </span>
          </template>
        </div>
      </section>

      <section class="modules-section">
        <header class="section-header">
          <h2 class="section-title">从这里开始</h2>
          <span class="section-tip">业务模块陆续开发中，敬请期待</span>
        </header>
        <div class="modules-grid">
          <ModuleCard
            v-for="m in visibleModules"
            :key="m.key"
            :icon="m.icon"
            :title="m.title"
            :subtitle="m.subtitle"
            :badge="m.badge"
            :disabled="m.disabled"
          />
        </div>
      </section>

      <section class="platforms-section">
        <h3 class="platforms-title">模板可在以下平台使用</h3>
        <div class="platform-list">
          <span v-for="p in PLATFORMS" :key="p" class="platform-tag">{{ p }}</span>
        </div>
      </section>

      <footer class="phase-tip">🚧 当前为骨架版本 · 鉴权与业务模块开发中</footer>
    </a-layout-content>
  </a-layout>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: var(--gray-10);
}

.content {
  max-width: 1080px;
  margin: 0 auto;
  padding: 48px 32px 64px;
}

/* ---------- Hero ---------- */
.hero {
  margin-bottom: 40px;
}

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  margin-bottom: 16px;
  font-size: 12px;
  font-weight: 500;
  color: var(--main-700);
  background: var(--main-10);
  border: 1px solid var(--main-30);
  border-radius: 999px;
}

.hero-title {
  margin: 0 0 12px;
  font-size: 30px;
  font-weight: 700;
  line-height: 1.25;
  color: var(--color-text);
  letter-spacing: -0.3px;
}

.hero-subtitle {
  margin: 0;
  max-width: 680px;
  font-size: 15px;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.hero-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 24px;
}

.hero-actions :deep(.ant-btn) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 40px;
  padding: 0 20px;
  font-weight: 500;
  border-radius: 8px;
}

.hero-actions-hint {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

/* ---------- Modules section ---------- */
.modules-section {
  margin-top: 40px;
}

.section-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
}

.section-tip {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

/* ---------- Platforms section ---------- */
.platforms-section {
  margin-top: 48px;
}

.platforms-title {
  margin: 0 0 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-tertiary);
}

.platform-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.platform-tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  font-size: 12px;
  color: var(--color-text-secondary);
  background: var(--gray-0);
  border: 1px solid var(--gray-50);
  border-radius: 999px;
}

/* ---------- Phase footer ---------- */
.phase-tip {
  margin-top: 56px;
  padding-top: 24px;
  border-top: 1px dashed var(--gray-50);
  font-size: 12px;
  color: var(--color-text-tertiary);
  text-align: center;
}

@media (max-width: 640px) {
  .content {
    padding: 32px 16px 48px;
  }
  .hero-title {
    font-size: 24px;
  }
}
</style>

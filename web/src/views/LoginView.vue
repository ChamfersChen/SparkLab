<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LogIn, User, Lock, Sparkles } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { login } from '@/apis/auth_api'
import AnimatedBg from '@/components/AnimatedBg.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const redirectTo = computed(() => (route.query.redirect || '/'))

async function handleLogin() {
  error.value = ''
  if (!username.value.trim() || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  try {
    const res = await login({
      username: username.value.trim(),
      password: password.value,
    })
    userStore.setSession(res)
    router.push(redirectTo.value)
  } catch (e) {
    error.value = e.message || '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-view">
    <!-- 左侧品牌区 -->
    <AnimatedBg class="brand-panel">
      <div class="brand-content">
        <div class="brand-logo">
          <Sparkles :size="32" :stroke-width="2" />
        </div>
        <h1 class="brand-name">SparkLab</h1>
        <p class="brand-slogan">让团队的 AI 提示词资产沉淀下来</p>
        <div class="brand-features">
          <div class="brand-feature">
            <div class="brand-feature-dot" />
            <span>结构化模板，填空即用</span>
          </div>
          <div class="brand-feature">
            <div class="brand-feature-dot" />
            <span>多步骤流程，串联创作</span>
          </div>
          <div class="brand-feature">
            <div class="brand-feature-dot" />
            <span>团队协作，资产沉淀</span>
          </div>
        </div>
      </div>
    </AnimatedBg>

    <!-- 右侧表单区 -->
    <div class="form-panel">
      <div class="card">
        <div class="brand">
          <LogIn :size="24" :stroke-width="2.25" />
          <span>SparkLab 登录</span>
        </div>

        <a-form layout="vertical" class="login-form" @submit.prevent="handleLogin">
          <a-form-item label="用户名">
            <a-input
              v-model:value="username"
              placeholder="输入用户名"
              :disabled="loading"
              size="large"
            >
              <template #prefix><User :size="16" /></template>
            </a-input>
          </a-form-item>
          <a-form-item label="密码">
            <a-input-password
              v-model:value="password"
              placeholder="输入密码"
              :disabled="loading"
              size="large"
            >
              <template #prefix><Lock :size="16" /></template>
            </a-input-password>
          </a-form-item>
          <p v-if="error" class="form-error">{{ error }}</p>
          <a-button
            type="primary"
            html-type="submit"
            :loading="loading"
            size="large"
            block
          >
            登录
          </a-button>
        </a-form>

        <div class="footer-hint">
          <span>还没有账号？</span>
          <router-link to="/">联系管理员获取激活码</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-view {
  min-height: 100vh;
  display: flex;
}

/* ---------- 左侧品牌区 ---------- */
.brand-panel {
  flex: 0 0 55%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-content {
  position: relative;
  z-index: 1;
  padding: 48px;
  max-width: 420px;
}

.brand-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  margin-bottom: 24px;
}

.brand-name {
  margin: 0 0 12px;
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.5px;
}

.brand-slogan {
  margin: 0 0 36px;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.6;
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.brand-feature {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.75);
}

.brand-feature-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  flex-shrink: 0;
}

/* ---------- 右侧表单区 ---------- */
.form-panel {
  flex: 0 0 45%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gray-0);
  padding: 24px;
}

.card {
  width: 100%;
  max-width: 360px;
  padding: 0;
}

.brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 32px;
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text);
}

.brand :deep(svg) {
  color: var(--main-color);
}

.login-form {
  width: 100%;
}

.form-error {
  color: var(--color-error-700);
  font-size: 13px;
  margin: 0 0 12px;
}

.footer-hint {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.footer-hint a {
  color: var(--main-color);
}

/* ---------- 响应式 ---------- */
@media (max-width: 960px) {
  .brand-panel {
    flex: 0 0 45%;
  }
}

@media (max-width: 768px) {
  .login-view {
    flex-direction: column;
  }

  .brand-panel {
    flex: 0 0 auto;
    min-height: 200px;
  }

  .brand-content {
    padding: 32px 24px;
    text-align: center;
  }

  .brand-name {
    font-size: 26px;
  }

  .brand-features {
    display: none;
  }

  .form-panel {
    flex: 1;
    padding: 32px 24px;
  }

  .card {
    max-width: 100%;
  }
}
</style>

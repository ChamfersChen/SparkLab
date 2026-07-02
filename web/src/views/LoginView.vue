<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LogIn, User, Lock } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { login } from '@/apis/auth_api'

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
</template>

<style scoped>
.login-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gray-10);
  padding: 24px;
}

.card {
  width: 100%;
  max-width: 400px;
  padding: 32px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
}

.brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 24px;
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

@media (max-width: 768px) {
  .login-view {
    padding: 16px;
  }

  .card {
    padding: 24px 20px;
  }
}
</style>

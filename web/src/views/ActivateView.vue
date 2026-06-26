<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { KeyRound, CheckCircle2, XCircle, Loader2, User, Lock } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { verifyActivationCode, activate } from '@/apis/auth_api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const STATUS = {
  LOADING: 'loading',
  VERIFIED: 'verified',
  USED: 'used',
  INVALID: 'invalid',
  FORM: 'form',
  SUBMITTING: 'submitting',
  ERROR: 'error',
}

const status = ref(STATUS.LOADING)
const message = ref('')
const code = ref('')

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const formError = ref('')

const isSubmitting = computed(() => status.value === STATUS.SUBMITTING)

onMounted(async () => {
  code.value = (route.query.code || '').trim().toUpperCase()
  if (!code.value) {
    status.value = STATUS.INVALID
    message.value = '缺少激活码，请检查激活链接'
    return
  }
  try {
    const res = await verifyActivationCode(code.value)
    if (res.valid) {
      status.value = STATUS.VERIFIED
      message.value = '激活码验证通过，请设置您的账号'
    } else if (res.message && res.message.includes('已被使用')) {
      status.value = STATUS.USED
      message.value = res.message
    } else {
      status.value = STATUS.INVALID
      message.value = res.message || '无效的激活码'
    }
  } catch {
    status.value = STATUS.INVALID
    message.value = '验证失败，请稍后重试'
  }
})

async function handleActivate() {
  formError.value = ''
  if (!username.value.trim()) {
    formError.value = '请输入用户名'
    return
  }
  if (username.value.trim().length < 2) {
    formError.value = '用户名至少 2 个字符'
    return
  }
  if (!password.value) {
    formError.value = '请输入密码'
    return
  }
  if (password.value.length < 6) {
    formError.value = '密码至少 6 位'
    return
  }
  if (password.value !== confirmPassword.value) {
    formError.value = '两次输入的密码不一致'
    return
  }

  status.value = STATUS.SUBMITTING
  try {
    const res = await activate({
      code: code.value,
      username: username.value.trim(),
      password: password.value,
    })
    userStore.setSession(res)
    router.push('/')
  } catch (e) {
    formError.value = e.message || '激活失败，请稍后重试'
    status.value = STATUS.FORM
  }
}
</script>

<template>
  <div class="activate-view">
    <div class="card">
      <div class="brand">
        <KeyRound :size="24" :stroke-width="2.25" />
        <span>SparkLab 激活</span>
      </div>

      <!-- 加载中 -->
      <div v-if="status === 'loading'" class="state-box">
        <Loader2 :size="32" class="spin" />
        <p>验证激活码...</p>
      </div>

      <!-- 验证通过 - 显示表单 -->
      <div v-else-if="status === 'verified'" class="state-box">
        <CheckCircle2 :size="32" class="icon-success" />
        <p class="state-msg">{{ message }}</p>
        <a-form layout="vertical" class="activate-form" @submit.prevent="handleActivate">
          <a-form-item label="用户名">
            <a-input
              v-model:value="username"
              placeholder="输入你的用户名"
              :disabled="isSubmitting"
              size="large"
            >
              <template #prefix><User :size="16" /></template>
            </a-input>
          </a-form-item>
          <a-form-item label="密码">
            <a-input-password
              v-model:value="password"
              placeholder="至少 6 位"
              :disabled="isSubmitting"
              size="large"
            >
              <template #prefix><Lock :size="16" /></template>
            </a-input-password>
          </a-form-item>
          <a-form-item label="确认密码">
            <a-input-password
              v-model:value="confirmPassword"
              placeholder="再次输入密码"
              :disabled="isSubmitting"
              size="large"
            >
              <template #prefix><Lock :size="16" /></template>
            </a-input-password>
          </a-form-item>
          <p v-if="formError" class="form-error">{{ formError }}</p>
          <a-button
            type="primary"
            html-type="submit"
            :loading="isSubmitting"
            size="large"
            block
          >
            完成激活
          </a-button>
        </a-form>
      </div>

      <!-- 已被使用 -->
      <div v-else-if="status === 'used'" class="state-box">
        <XCircle :size="32" class="icon-warning" />
        <p class="state-msg">{{ message }}</p>
        <a-button type="primary" @click="router.push('/login')">去登录</a-button>
      </div>

      <!-- 无效 -->
      <div v-else class="state-box">
        <XCircle :size="32" class="icon-error" />
        <p class="state-msg">{{ message }}</p>
        <router-link to="/">返回首页</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.activate-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gray-10);
  padding: 24px;
}

.card {
  width: 100%;
  max-width: 420px;
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

.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
}

.state-msg {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.icon-success { color: var(--color-success-700); }
.icon-warning { color: var(--color-warning-900); }
.icon-error { color: var(--color-error-700); }

.spin {
  animation: spin 1s linear infinite;
  color: var(--main-color);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.activate-form {
  width: 100%;
  margin-top: 8px;
}

.form-error {
  color: var(--color-error-700);
  font-size: 13px;
  margin: 0 0 12px;
}
</style>

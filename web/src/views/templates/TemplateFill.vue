<script setup>
/**
 * 提示词填写页 - 左表单 / 右 Prompt 预览
 *
 * 核心逻辑（纯前端）：
 * 1. 从后端获取模板的 fill data（变量清单 + hints）
 * 2. 左侧表单根据 {{变量名}} 自动生成输入框
 * 3. 用户填写 → 点击"生成提示词" → 前端拼接五段式
 * 4. 右侧预览区展示完整 Prompt，支持编辑、复制
 */
import { ref, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { Copy, ExternalLink, Sparkles } from 'lucide-vue-next'
import { getFillData } from '@/apis/template_api'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const data = ref(null)
const formValues = reactive({})
const generatedPrompt = ref('')

// 第三方 AI 平台列表（硬编码，后续改为从后端获取）
const PLATFORMS = [
  { name: 'DeepSeek', url: 'https://chat.deepseek.com' },
  { name: 'Kimi', url: 'https://kimi.moonshot.cn' },
  { name: '豆包', url: 'https://www.doubao.com/chat' },
  { name: '通义千问', url: 'https://tongyi.aliyun.com/qianwen' },
]

async function fetchData() {
  loading.value = true
  try {
    const res = await getFillData(route.params.id)
    data.value = res
    // 从 variable_hints 的 key 提取变量，初始化空表单
    const vars = Object.keys(res.variable_hints || {})
    if (!vars.length) {
      // 从 input 段解析变量
      const regex = /\{\{(.*?)\}\}/g
      let match
      while ((match = regex.exec(res.input)) !== null) {
        if (!(match[1] in formValues)) {
          formValues[match[1]] = ''
        }
      }
    }
    vars.forEach(v => { formValues[v] = '' })
  } catch (e) {
    if (e.response?.status !== 401) {
      message.error('获取模板填写信息失败')
    }
  } finally {
    loading.value = false
  }
}

/**
 * 生成提示词（纯前端拼接）。
 * 规则：按五段式输出，Input 段中替换 {{变量}} 为用户填写内容。
 */
function generatePrompt() {
  if (!data.value) return
  const d = data.value
  let filledInput = d.input
  for (const [key, val] of Object.entries(formValues)) {
    filledInput = filledInput.replaceAll(
      new RegExp(`\\{\\{\\s*${escapeRegex(key)}\\s*\\}\\}`, 'g'),
      val || `[${key}]`
    )
  }
  generatedPrompt.value = [
    `## Role（角色定义）\n${d.role}`,
    `## Goal（目标说明）\n${d.goal}`,
    `## Input（输入信息）\n${filledInput}`,
    `## Output（输出要求）\n${d.output}`,
    `## Example（示例效果）\n${d.example}`,
  ].join('\n\n---\n\n')
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

async function copyPrompt() {
  try {
    await navigator.clipboard.writeText(generatedPrompt.value)
    message.success('已复制到剪贴板')
  } catch {
    message.error('复制失败，请手动选中后复制')
  }
}

function openPlatform(url) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

onMounted(fetchData)
</script>

<template>
  <div class="page">
    <div class="content">
      <a-page-header
        title="返回模板详情"
        @back="router.push({ name: 'template-detail', params: { id: route.params.id } })"
      />

      <a-spin :spinning="loading">
        <template v-if="data">
          <h1 class="page-title">{{ data.title }}</h1>
          <p class="page-desc">{{ data.description }}</p>

          <div class="fill-layout">
            <!-- 左侧表单 -->
            <div class="fill-form">
              <h2 class="section-title">填写信息</h2>
              <div v-for="(hint, varName) in data.variable_hints" :key="varName" class="form-field">
                <label class="field-label">{{ varName }}</label>
                <a-textarea
                  v-model:value="formValues[varName]"
                  :placeholder="hint || `请输入${varName}`"
                  :rows="3"
                  class="field-input"
                />
                <div v-if="hint" class="field-hint">{{ hint }}</div>
              </div>

              <!-- 无变量时 -->
              <div v-if="!Object.keys(data.variable_hints || {}).length" class="no-vars">
                <p>此模板无需填写变量</p>
              </div>

              <a-button
                type="primary"
                size="large"
                class="generate-btn"
                @click="generatePrompt"
              >
                <template #icon><Sparkles :size="16" /></template>
                生成提示词
              </a-button>
            </div>

            <!-- 右侧预览 -->
            <div class="fill-preview">
              <div class="preview-header">
                <h2 class="section-title">生成的提示词</h2>
              </div>
              <div class="preview-actions" v-if="generatedPrompt">
                <a-button type="primary" class="copy-btn" @click="copyPrompt">
                  <template #icon><Copy :size="16" /></template>
                  复制提示词
                </a-button>
                <div class="platform-buttons">
                  <span class="platform-label">打开 AI 平台：</span>
                  <a-button
                    v-for="p in PLATFORMS"
                    :key="p.name"
                    size="small"
                    @click="openPlatform(p.url)"
                  >
                    <template #icon><ExternalLink :size="13" /></template>
                    {{ p.name }}
                  </a-button>
                </div>
              </div>
              <div class="preview-area">
                <a-textarea
                  v-model:value="generatedPrompt"
                  placeholder="点击「生成提示词」后，拼接完成的 Prompt 将显示在这里。"
                  :rows="18"
                  class="preview-textarea"
                />
              </div>
            </div>
          </div>
        </template>
      </a-spin>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--gray-10);
}

.content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 32px 64px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  margin: 8px 0 4px;
}

.page-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0 0 24px;
}

.fill-layout {
  display: flex;
  gap: 24px;
}

.fill-form {
  flex: 1;
  min-width: 0;
}

.fill-preview {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 16px;
}

/* Form fields */
.form-field {
  margin-bottom: 16px;
}

.field-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
}

.field-hint {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin-top: 4px;
}

.no-vars {
  color: var(--color-text-secondary);
  padding: 24px;
  text-align: center;
  background: var(--gray-0);
  border-radius: 8px;
  border: 1px dashed var(--gray-50);
}

.generate-btn {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 8px;
}

/* Preview */
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.preview-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.copy-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.platform-buttons {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.platform-label {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.preview-textarea {
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.6;
  min-height: 400px;
}

@media (max-width: 768px) {
  .fill-layout {
    flex-direction: column;
  }
  .content {
    padding: 0 16px 48px;
  }
}
</style>

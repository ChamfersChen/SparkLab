<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Copy, ExternalLink, RefreshCcw, Sparkles, Trash2 } from 'lucide-vue-next'
import { message } from 'ant-design-vue'
import { getFillData, incrementUseCount } from '@/apis/template_api'

const route = useRoute()
const router = useRouter()

const PLATFORMS = [
  { name: 'DeepSeek', url: 'https://chat.deepseek.com' },
  { name: '豆包', url: 'https://www.doubao.com/chat/' },
  { name: '通义千问', url: 'https://tongyi.aliyun.com/qianwen/' },
  { name: '文心一言', url: 'https://yiyan.baidu.com/' },
]

const loading = ref(false)
const data = ref(null)
const formValues = ref({})
const generatedPrompt = ref('')
const lastGeneratedAt = ref(null)

/** 草稿存储 key：sparklab:template-draft:<id> */
function draftKey(id) {
  return `sparklab:template-draft:${id}`
}

function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/** 必填变量名列表（从 variable_hints 的 key 推导） */
const varNames = computed(() => Object.keys(data.value?.variable_hints || {}))

/** 缺失字段数（trim 后为空） */
const missingCount = computed(
  () => varNames.value.filter((v) => !formValues[v]?.trim()).length
)

const canGenerate = computed(() => !!data.value && missingCount.value === 0)

/** 变量填充进度 0~1 */
const fillProgress = computed(() => {
  const total = varNames.value.length
  if (!total) return 1
  return (total - missingCount.value) / total
})

async function fetchData() {
  loading.value = true
  try {
    const res = await getFillData(route.params.id)
    data.value = res
    // 1. 初始化为空串
    for (const v of varNames.value) {
      if (!(v in formValues.value)) formValues.value[v] = ''
    }
    // 2. 恢复草稿
    try {
      const raw = localStorage.getItem(draftKey(res.template_id || route.params.id))
      if (raw) {
        const draft = JSON.parse(raw)
        for (const [k, v] of Object.entries(draft.formValues || {})) {
          if (k in formValues.value) formValues.value[k] = v
        }
        if (draft.generatedPrompt) {
          generatedPrompt.value = draft.generatedPrompt
          lastGeneratedAt.value = draft.lastGeneratedAt || null
        }
      }
    } catch {
      // 草稿损坏忽略
    }
  } catch {
    message.error('模板加载失败')
  } finally {
    loading.value = false
  }
}

/** 表单变化时持久化草稿 */
function persistDraft() {
  if (!data.value) return
  try {
    localStorage.setItem(
      draftKey(data.value.template_id || route.params.id),
      JSON.stringify({
        formValues: { ...formValues },
        generatedPrompt: generatedPrompt.value,
        lastGeneratedAt: lastGeneratedAt.value,
        savedAt: Date.now(),
      })
    )
  } catch {
    // localStorage 满 / 隐私模式忽略
  }
}

watch(formValues, persistDraft, { deep: true })
watch(generatedPrompt, persistDraft)

function clearDraft() {
  if (!data.value) return
  for (const v of varNames.value) formValues.value[v] = ''
  generatedPrompt.value = ''
  lastGeneratedAt.value = null
  localStorage.removeItem(draftKey(data.value.template_id || route.params.id))
  message.success('草稿已清除')
}

/**
 * 生成提示词（纯前端拼接）。
 * 规则：按五段式输出，Input 段中替换 {{变量}} 为用户填写内容；
 * 同时异步上报一次使用次数，失败不影响主流程。
 */
function generatePrompt() {
  if (!data.value || !canGenerate.value) return
  const d = data.value
  let filledInput = d.input
  for (const [key, val] of Object.entries(formValues)) {
    filledInput = filledInput.replaceAll(
      new RegExp(`\\{\\{\\s*${escapeRegex(key)}\\s*\\}\\}`, 'g'),
      val.trim()
    )
  }
  generatedPrompt.value = [
    `## Role（角色定义）\n${d.role}`,
    `## Goal（目标说明）\n${d.goal}`,
    `## Input（输入信息）\n${filledInput}`,
    `## Output（输出要求）\n${d.output}`,
    `## Example（示例效果）\n${d.example}`,
  ].join('\n\n---\n\n')
  lastGeneratedAt.value = Date.now()
  incrementUseCount(d.template_id || route.params.id).catch(() => {})
}

async function copyPrompt() {
  if (!generatedPrompt.value) return
  try {
    await navigator.clipboard.writeText(generatedPrompt.value)
    message.success('已复制到剪贴板')
  } catch {
    message.error('复制失败，请手动复制')
  }
}

/**
 * 打开 AI 平台：先复制提示词，再开新标签。
 * 设计意图：用户去第三方 AI 平台时不需要再回来复制。
 */
async function openPlatform(url) {
  if (generatedPrompt.value) {
    try {
      await navigator.clipboard.writeText(generatedPrompt.value)
      message.success('提示词已复制，请在 AI 平台中粘贴（Ctrl/⌘+V）')
    } catch {
      message.warning('请手动复制后再打开 AI 平台')
    }
  } else {
    message.info('尚未生成提示词，将打开 AI 平台空白页')
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getHours().toString().padStart(2, '0')}:${d
    .getMinutes()
    .toString()
    .padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
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
              <div class="form-header">
                <h2 class="section-title">填写信息</h2>
                <span v-if="varNames.length" class="progress-text">
                  <span :class="missingCount ? 'progress-warn' : 'progress-ok'">
                    {{ varNames.length - missingCount }} / {{ varNames.length }}
                  </span>
                  已填
                </span>
              </div>

              <a-progress
                v-if="varNames.length"
                :percent="Math.round(fillProgress * 100)"
                :show-info="false"
                :stroke-color="missingCount ? 'var(--color-warning-500)' : 'var(--color-success-500)'"
                class="progress-bar"
              />

              <div
                v-for="varName in varNames"
                :key="varName"
                class="form-field"
                :class="{ 'field-error': !formValues[varName]?.trim() }"
              >
                <label class="field-label">
                  {{ varName }}
                  <span class="required-mark">*</span>
                </label>
                <a-textarea
                  v-model:value="formValues[varName]"
                  :placeholder="data.variable_hints[varName] || `请输入${varName}`"
                  :rows="3"
                  class="field-input"
                />
                <div v-if="data.variable_hints[varName]" class="field-hint">
                  {{ data.variable_hints[varName] }}
                </div>
              </div>

              <!-- 无变量时 -->
              <div v-if="!varNames.length" class="no-vars">
                <p>此模板无需填写变量，可直接生成提示词</p>
              </div>

              <div class="form-actions">
                <a-button
                  type="primary"
                  size="large"
                  class="generate-btn"
                  :disabled="!canGenerate"
                  @click="generatePrompt"
                >
                  <template #icon><Sparkles :size="16" /></template>
                  {{ canGenerate ? '生成提示词' : `还有 ${missingCount} 项未填` }}
                </a-button>
                <a-button size="large" class="reset-btn" @click="clearDraft">
                  <template #icon><Trash2 :size="16" /></template>
                  清除草稿
                </a-button>
              </div>
            </div>

            <!-- 右侧预览 -->
            <div class="fill-preview">
              <div class="preview-header">
                <h2 class="section-title">生成的提示词</h2>
                <span v-if="lastGeneratedAt" class="generated-time">
                  <RefreshCcw :size="13" />
                  最近生成 {{ formatTime(lastGeneratedAt) }}
                </span>
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
  padding: 32px 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--gray-900);
  margin: 16px 0 8px;
}

.page-desc {
  font-size: 14px;
  color: var(--gray-600);
  margin-bottom: 32px;
}

.fill-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr);
  gap: 24px;
  align-items: start;
}

@media (max-width: 960px) {
  .fill-layout {
    grid-template-columns: 1fr;
  }
}

.fill-form,
.fill-preview {
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  padding: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--gray-900);
  margin: 0;
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-text {
  font-size: 13px;
  color: var(--gray-600);
}

.progress-ok {
  color: var(--color-success-600);
  font-weight: 600;
}

.progress-warn {
  color: var(--color-warning-600);
  font-weight: 600;
}

.progress-bar {
  margin-bottom: 20px;
}

.form-field {
  margin-bottom: 16px;
}

.field-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--gray-800);
  margin-bottom: 6px;
}

.required-mark {
  color: var(--color-error-500);
  margin-left: 2px;
}

.field-input {
  width: 100%;
}

.field-hint {
  font-size: 12px;
  color: var(--gray-500);
  margin-top: 4px;
  line-height: 1.5;
}

.field-error .field-input {
  border-color: var(--color-warning-500);
}

.no-vars {
  padding: 16px;
  background: var(--gray-25);
  border: 1px dashed var(--gray-200);
  border-radius: 6px;
  text-align: center;
  color: var(--gray-600);
  margin-bottom: 16px;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.generate-btn,
.reset-btn {
  flex: 1;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.generated-time {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--gray-500);
}

.preview-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--gray-100);
}

.copy-btn {
  align-self: flex-start;
}

.platform-buttons {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.platform-label {
  font-size: 13px;
  color: var(--gray-700);
  margin-right: 4px;
}

.preview-area {
  width: 100%;
}

.preview-textarea {
  font-family: 'SF Mono', Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
}
</style>

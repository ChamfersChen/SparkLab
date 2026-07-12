<script setup>
/**
 * 模板填写页（用户端，三栏布局）。
 *
 * 布局:
 *   - 左栏: 变量填写表单
 *   - 中栏: 提示词拼接结果 + AI 平台链接
 *   - 右栏: AI 回复结果 (markdown textarea) + 保存按钮
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  Check,
  ChevronLeft,
  Copy,
  ExternalLink,
  RefreshCcw,
  Save,
  Sparkles,
  Trash2,
  Wand2,
} from 'lucide-vue-next'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { getFillData, incrementUseCount } from '@/apis/template_api'
import { createTemplateRun } from '@/apis/template_runs_api'
import { extractVariables } from '@/composables/useTemplateVariables'

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

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
const aiResult = ref('')
const saveTitle = ref('')
const saving = ref(false)
const summarySaved = ref(false)

const renderedPrompt = computed(() => {
  if (!generatedPrompt.value) return ''
  return DOMPurify.sanitize(md.render(generatedPrompt.value))
})

const renderedAiResult = computed(() => {
  if (!aiResult.value) return ''
  return DOMPurify.sanitize(md.render(aiResult.value))
})

function draftKey(id) {
  return `sparklab:template-draft:${id}`
}

function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

const variables = computed(() => {
  if (!data.value) return []
  const inputVars = extractVariables(data.value.content || '')
  const hintKeys = Object.keys(data.value.variable_hints || {})
  const seen = new Set()
  const merged = []
  for (const v of [...inputVars, ...hintKeys]) {
    if (!seen.has(v)) {
      seen.add(v)
      merged.push({
        name: v,
        hint: data.value.variable_hints?.[v] || null,
        usedInInput: inputVars.includes(v),
      })
    }
  }
  return merged
})

const varNames = computed(() => variables.value.map((v) => v.name))

const missingCount = computed(
  () => varNames.value.filter((v) => !formValues.value[v]?.trim()).length
)

const canGenerate = computed(() => !!data.value && missingCount.value === 0)

const fillProgress = computed(() => {
  const total = varNames.value.length
  if (!total) return 1
  return (total - missingCount.value) / total
})

const progressState = computed(() => {
  if (!varNames.value.length) return 'idle'
  if (missingCount.value === 0) return 'done'
  if (missingCount.value === varNames.value.length) return 'empty'
  return 'partial'
})

async function fetchData() {
  loading.value = true
  try {
    const res = await getFillData(route.params.id)
    data.value = res
    for (const v of varNames.value) {
      if (!(v in formValues.value)) formValues.value[v] = ''
    }
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
        if (draft.aiResult) aiResult.value = draft.aiResult
        if (draft.saveTitle) saveTitle.value = draft.saveTitle
      }
    } catch {
      // ignore
    }
  } catch {
    message.error('模板加载失败')
  } finally {
    loading.value = false
  }
}

let persistTimer = null
function schedulePersistDraft() {
  if (persistTimer) clearTimeout(persistTimer)
  persistTimer = setTimeout(persistDraft, 500)
}

function persistDraft() {
  if (!data.value) return
  try {
    localStorage.setItem(
      draftKey(data.value.template_id || route.params.id),
      JSON.stringify({
        formValues: { ...formValues.value },
        generatedPrompt: generatedPrompt.value,
        lastGeneratedAt: lastGeneratedAt.value,
        aiResult: aiResult.value,
        saveTitle: saveTitle.value,
        savedAt: Date.now(),
      }),
    )
  } catch {
    // ignore
  }
}

watch(formValues, schedulePersistDraft, { deep: true })
watch(generatedPrompt, schedulePersistDraft)
watch(aiResult, schedulePersistDraft)
watch(saveTitle, schedulePersistDraft)

function clearDraft() {
  if (!data.value) return
  for (const v of varNames.value) formValues.value[v] = ''
  generatedPrompt.value = ''
  lastGeneratedAt.value = null
  aiResult.value = ''
  saveTitle.value = ''
  summarySaved.value = false
  if (persistTimer) {
    clearTimeout(persistTimer)
    persistTimer = null
  }
  localStorage.removeItem(draftKey(data.value.template_id || route.params.id))
  message.success('草稿已清除')
}

function generatePrompt() {
  if (!data.value || !canGenerate.value) return
  const d = data.value
  let filled = d.content || ''
  for (const [key, val] of Object.entries(formValues.value)) {
    filled = filled.replaceAll(
      new RegExp(`\\{\\{\\s*${escapeRegex(key)}\\s*\\}\\}`, 'g'),
      val.trim(),
    )
  }
  generatedPrompt.value = filled
  lastGeneratedAt.value = Date.now()
  summarySaved.value = false
  persistDraft()
  incrementUseCount(d.template_id || route.params.id).catch(() => {
    message.warning('使用次数上报失败,不影响 Prompt 生成')
  })
}

import { copyToClipboard } from '@/utils/clipboard'

async function copyPrompt() {
  if (!generatedPrompt.value) return
  try {
    await copyToClipboard(generatedPrompt.value)
    message.success('已复制到剪贴板')
  } catch {
    message.error('复制失败,请手动复制')
  }
}

async function openPlatform(url) {
  if (generatedPrompt.value) {
    try {
      await copyToClipboard(generatedPrompt.value)
      message.success('提示词已复制,请在 AI 平台中粘贴（Ctrl/⌘+V）')
    } catch {
      message.warning('请手动复制后再打开 AI 平台')
    }
  } else {
    message.info('尚未生成提示词,将打开 AI 平台空白页')
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

async function saveToMyRuns() {
  if (!generatedPrompt.value || saving.value) return
  saving.value = true
  try {
    await createTemplateRun({
      template_id: data.value.template_id || Number(route.params.id),
      form_values: { ...formValues.value },
      generated_prompt: generatedPrompt.value,
      title: saveTitle.value.trim() || data.value.title || '',
      ai_result: aiResult.value || null,
    })
    summarySaved.value = true
    message.success('已保存到「个人中心 - 模板」')
  } catch {
    message.error('保存失败,请稍后重试')
  } finally {
    saving.value = false
  }
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getHours().toString().padStart(2, '0')}:${d
    .getMinutes()
    .toString()
    .padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
}

function goBack() {
  if (route.query.from === 'my') {
    router.push({ name: 'my-template-detail', params: { id: route.params.id } })
  } else {
    router.push({ name: 'template-detail', params: { id: route.params.id } })
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="page-bg">
    <div class="page-content">
      <a-spin :spinning="loading">
        <template v-if="data">
          <header class="page-bar page-bar--fill">
            <div class="page-bar__left-group">
              <button type="button" class="icon-text-btn" @click="goBack">
                <ChevronLeft :size="16" />
                <span>返回</span>
              </button>
              <h1 class="page-bar__title">{{ data.title }}</h1>
            </div>
            <div v-if="varNames.length" class="hero-progress">
              <span
                class="progress-pill"
                :class="`progress-pill--${progressState}`"
              >
                已填 {{ varNames.length - missingCount }} / {{ varNames.length }}
              </span>
            </div>
          </header>

          <p v-if="data.description" class="page-bar__sub page-bar__sub--fill">{{ data.description }}</p>

          <div class="fill-layout">
            <!-- 左栏:变量填写表单 -->
            <section class="panel fill-form">
              <div class="panel-header">
                <h2 class="panel-title">
                  <span class="panel-title-icon"><Wand2 :size="16" /></span>
                  <span>填写信息</span>
                </h2>
                <div v-if="varNames.length" class="header-meta">
                  <span
                    class="header-badge"
                    :class="`header-badge--${progressState}`"
                  >{{ varNames.length - missingCount }} / {{ varNames.length }}</span>
                  <a-progress
                    :percent="Math.round(fillProgress * 100)"
                    :show-info="false"
                    :stroke-color="progressState === 'done' ? 'var(--color-success-500)' : 'var(--color-warning-500)'"
                    class="progress-bar"
                  />
                </div>
              </div>

              <div class="panel-body">
                <div
                  v-for="v in variables"
                  :key="v.name"
                  class="form-field"
                  :class="{ 'form-field--error': !formValues[v.name]?.trim() }"
                >
                  <div class="field-label-row">
                    <label class="field-label">
                      {{ v.name }}
                      <span class="required-mark">*</span>
                    </label>
                    <span
                      v-if="!v.usedInInput"
                      class="field-pill"
                      title="该变量在 Input 段未通过 {{}} 引用,仅作为提示项"
                    >
                      仅提示
                    </span>
                  </div>
                  <a-textarea
                    v-model:value="formValues[v.name]"
                    :placeholder="v.hint || `请输入${v.name}`"
                    :rows="3"
                    :status="!formValues[v.name]?.trim() ? 'error' : ''"
                    class="field-input"
                  />
                  <p v-if="v.hint" class="field-hint">{{ v.hint }}</p>
                  <p v-else class="field-hint field-hint--empty">
                    填写 {{ v.name }}
                  </p>
                </div>

                <div v-if="!varNames.length" class="no-vars">
                  <p class="no-vars-title">此模板无需填写变量</p>
                  <p class="no-vars-desc">点击下方「生成提示词」即可直接得到完整 Prompt。</p>
                </div>
              </div>

              <div class="panel-footer panel-footer--actions">
                <a-button
                  type="primary"
                  class="generate-btn"
                  :disabled="!canGenerate"
                  @click="generatePrompt"
                >
                  <template #icon><Sparkles :size="16" /></template>
                  {{ canGenerate ? '生成提示词' : `还有 ${missingCount} 项未填` }}
                </a-button>
                <a-tooltip title="清除全部内容">
                  <a-button class="reset-btn" @click="clearDraft">
                    <template #icon><Trash2 :size="14" /></template>
                  </a-button>
                </a-tooltip>
              </div>
            </section>

            <!-- 中栏:提示词结果 + AI平台 -->
            <section class="panel fill-prompt">
              <div class="panel-header">
                <h2 class="panel-title">
                  <span class="panel-title-icon panel-title-icon--accent"><Sparkles :size="16" /></span>
                  <span>生成的提示词</span>
                </h2>
                <div class="header-meta">
                  <span v-if="lastGeneratedAt" class="generated-time">
                    <RefreshCcw :size="12" />
                    {{ formatTime(lastGeneratedAt) }}
                  </span>
                  <button
                    v-if="generatedPrompt"
                    type="button"
                    class="header-action-btn"
                    @click="copyPrompt"
                  >
                    <Copy :size="14" />
                    <span>复制</span>
                  </button>
                </div>
              </div>

              <div class="panel-body panel-body--prompt">
                <div v-if="generatedPrompt" class="prompt-content" v-html="renderedPrompt" />
                <div v-else class="prompt-placeholder">
                  <Sparkles :size="32" class="prompt-placeholder-icon" />
                  <p class="prompt-placeholder-title">填写左侧变量后,点击「生成提示词」</p>
                  <p class="prompt-placeholder-sub">结果会在这里显示</p>
                </div>
              </div>

              <div v-if="generatedPrompt" class="panel-footer panel-footer--platforms">
                <span class="platform-label">复制提示词到 AI 平台</span>
                <div class="platform-group">
                  <button
                    v-for="p in PLATFORMS"
                    :key="p.name"
                    type="button"
                    class="platform-chip"
                    @click="openPlatform(p.url)"
                  >
                    <span>{{ p.name }}</span>
                    <ExternalLink :size="11" />
                  </button>
                </div>
              </div>
            </section>

            <!-- 右栏:AI结果 + 保存 -->
            <section class="panel fill-result">
              <div class="panel-header">
                <h2 class="panel-title">
                  <span class="panel-title-icon"><Wand2 :size="16" /></span>
                  <span>AI 回复结果</span>
                </h2>
              </div>

              <div class="panel-body panel-body--result">
                <a-textarea
                  v-model:value="aiResult"
                  placeholder="在 AI 平台获得回复后,将结果粘贴到这里..."
                  :rows="12"
                  class="result-textarea"
                />
                <div v-if="aiResult" class="result-preview">
                  <div class="result-preview__label">预览</div>
                  <div class="result-preview__content" v-html="renderedAiResult" />
                </div>
              </div>

              <div class="panel-footer panel-footer--save">
                <div class="save-row">
                  <a-input
                    v-model:value="saveTitle"
                    placeholder="为这次使用命名（可选）"
                    class="save-title-input"
                    :maxlength="200"
                  />
                  <a-button
                    type="primary"
                    class="save-btn"
                    :disabled="!generatedPrompt || summarySaved"
                    :loading="saving"
                    @click="saveToMyRuns"
                  >
                    <template v-if="summarySaved" #icon><Check :size="16" /></template>
                    <template v-else #icon><Save :size="16" /></template>
                    {{ summarySaved ? '已保存' : '保存' }}
                  </a-button>
                </div>
                <p class="save-hint">保存到「个人中心 - 模板」</p>
              </div>
            </section>
          </div>
        </template>
      </a-spin>
    </div>
  </div>
</template>

<style scoped>
.page-bg {
  height: 100vh;
  overflow: hidden;
  padding-bottom: 0;
  display: flex;
  flex-direction: column;
}

.page-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 24px 32px 16px;
}

:deep(.ant-spin-nested-loading),
:deep(.ant-spin-container) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.page-bar--fill {
  padding: 0 24px;
  flex-shrink: 0;
}

.page-bar--fill .page-bar__title {
  margin-bottom: 0;
  font-size: 20px;
}

.page-bar--fill .page-bar__left-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.page-bar__sub--fill {
  padding: 0 24px;
  margin-bottom: 20px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  flex-shrink: 0;
}

.hero-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: var(--gray-100);
  color: var(--gray-600);
}

.progress-pill--partial {
  background: var(--color-warning-50);
  color: var(--color-warning-900);
}

.progress-pill--done {
  background: var(--color-success-50);
  color: var(--color-success-700);
}

.progress-pill--empty,
.progress-pill--idle {
  background: var(--gray-100);
  color: var(--gray-600);
}

/* 三栏布局 */
.fill-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr) minmax(0, 1fr);
  gap: 16px;
  flex: 1;
  min-height: 0;
  align-items: stretch;
}

/* 面板 */
.panel {
  display: flex;
  flex-direction: column;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  overflow: hidden;
  min-height: 0;
}

.panel-header {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 12px;
  min-height: 52px;
  padding: 0 16px;
  box-sizing: border-box;
  background: var(--gray-0);
  border-bottom: 1px solid var(--gray-100);
  flex-shrink: 0;
}

.panel-header > * {
  align-self: center;
}

.panel-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 28px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.panel-title-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 7px;
  background: var(--main-10);
  color: var(--main-color);
  flex-shrink: 0;
}

.panel-title-icon--accent {
  background: var(--main-color);
  color: var(--gray-0);
}

.header-meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  height: 28px;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  background: var(--gray-100);
  color: var(--gray-700);
  white-space: nowrap;
}

.header-badge--partial {
  background: var(--color-warning-50);
  color: var(--color-warning-900);
}

.header-badge--done {
  background: var(--color-success-50);
  color: var(--color-success-700);
}

.progress-bar {
  width: 60px;
  height: 22px !important;
  display: flex !important;
  align-items: center;
}

.progress-bar :deep(.ant-progress-inner) {
  background: var(--gray-100);
}

.progress-bar :deep(.ant-progress-bg) {
  height: 4px !important;
}

.generated-time {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 22px;
  padding: 0 6px;
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-variant-numeric: tabular-nums;
}

.header-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 10px;
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  color: var(--color-text);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.header-action-btn:hover {
  border-color: var(--main-color);
  color: var(--main-color);
  background: var(--main-10);
}

.panel-body {
  flex: 1;
  min-height: 0;
  padding: 16px;
  overflow-y: auto;
}

.panel-body--prompt {
  padding: 0;
  background: var(--gray-10);
}

.panel-body--result {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 左栏:表单 */
.form-field {
  margin-bottom: 14px;
}

.form-field:last-child {
  margin-bottom: 0;
}

.field-label-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.field-label {
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
}

.required-mark {
  color: var(--color-error-500);
  margin-left: 2px;
}

.field-pill {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  background: var(--color-warning-50);
  color: var(--color-warning-900);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
}

.field-input {
  width: 100%;
}

.field-input :deep(textarea) {
  background: var(--gray-0);
  border-radius: 8px;
}

.field-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin: 6px 0 0;
  line-height: 1.5;
}

.field-hint--empty {
  color: var(--color-text-tertiary);
  font-style: italic;
}

.form-field--error .field-label {
  color: var(--color-error-700);
}

.no-vars {
  padding: 32px 16px;
  background: var(--gray-10);
  border: 1px dashed var(--gray-200);
  border-radius: 8px;
  text-align: center;
  color: var(--color-text-secondary);
}

.no-vars-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  margin: 0 0 4px;
}

.no-vars-desc {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin: 0;
}

/* Footer */
.panel-footer {
  padding: 12px 16px;
  background: var(--gray-10);
  border-top: 1px solid var(--gray-100);
  flex-shrink: 0;
}

.panel-footer--actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.generate-btn {
  flex: 1;
  height: 36px;
  font-weight: 500;
}

.reset-btn {
  height: 36px;
  width: 36px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--gray-600);
}

/* 中栏:提示词 */
.prompt-content {
  padding: 16px;
  font-size: 13px;
  line-height: 1.75;
  color: var(--color-text);
  word-break: break-word;
}

.prompt-content :deep(h2) {
  font-size: 15px;
  font-weight: 600;
  margin: 16px 0 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--gray-50);
}

.prompt-content :deep(p) {
  margin: 0 0 8px;
}

.prompt-content :deep(code) {
  background: var(--gray-25);
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 12px;
  font-family: var(--font-mono);
}

.prompt-content :deep(pre) {
  background: var(--gray-25);
  padding: 10px 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 0 0 8px;
}

.prompt-content :deep(pre code) {
  background: none;
  padding: 0;
}

.prompt-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--color-text-tertiary);
  min-height: 200px;
  padding: 32px 20px;
}

.prompt-placeholder-icon {
  color: var(--main-500);
  margin-bottom: 10px;
  opacity: 0.5;
}

.prompt-placeholder-title {
  font-size: 13px;
  color: var(--color-text-secondary);
  font-weight: 500;
  margin: 0 0 4px;
}

.prompt-placeholder-sub {
  font-size: 12px;
  color: var(--gray-400);
  margin: 0;
}

.panel-footer--platforms {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 8px;
}

.platform-label {
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-weight: 500;
}

.platform-group {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 5px;
}

.platform-chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  height: 24px;
  padding: 0 8px;
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 999px;
  color: var(--color-text-secondary);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.platform-chip:hover {
  background: var(--main-10);
  border-color: var(--main-color);
  color: var(--main-700);
}

/* 右栏:AI结果 */
.result-textarea {
  width: 100%;
}

.result-textarea :deep(textarea) {
  background: var(--gray-0);
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
}

.result-preview {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.result-preview__label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-tertiary);
  margin-bottom: 6px;
}

.result-preview__content {
  flex: 1;
  min-height: 0;
  padding: 12px;
  background: var(--gray-10);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-text);
  overflow-y: auto;
  word-break: break-word;
}

.result-preview__content :deep(h2) {
  font-size: 15px;
  font-weight: 600;
  margin: 12px 0 6px;
}

.result-preview__content :deep(p) {
  margin: 0 0 8px;
}

.result-preview__content :deep(code) {
  background: var(--gray-25);
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 12px;
  font-family: var(--font-mono);
}

/* 保存区域 */
.panel-footer--save {
  padding: 12px 16px;
}

.save-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.save-title-input {
  flex: 1;
  height: 34px;
}

.save-btn {
  height: 34px;
  padding: 0 14px;
  font-weight: 500;
  flex-shrink: 0;
}

.save-hint {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin: 6px 0 0;
}

/* 响应式 */
@media (max-width: 1100px) {
  .fill-layout {
    grid-template-columns: 1fr 1fr;
  }
  .fill-result {
    grid-column: 1 / -1;
  }
}

@media (max-width: 768px) {
  .page-bg {
    height: auto;
    overflow: visible;
  }

  .page-content {
    overflow: visible;
    padding: 16px;
  }

  :deep(.ant-spin-nested-loading),
  :deep(.ant-spin-container) {
    overflow: visible;
  }

  .fill-layout {
    grid-template-columns: 1fr;
  }
  .panel-header {
    padding: 10px 12px;
    min-height: 48px;
  }
  .panel-body {
    padding: 12px;
  }
  .panel-footer {
    padding: 10px 12px;
  }
  .panel-footer--actions {
    flex-direction: column-reverse;
    align-items: stretch;
  }
  .generate-btn {
    width: 100%;
  }
  .save-row {
    flex-direction: column;
    align-items: stretch;
  }
  .progress-bar {
    display: none;
  }
}
</style>

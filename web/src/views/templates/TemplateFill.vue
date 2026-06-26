<script setup>
/**
 * 模板填写页（用户端）。
 *
 * 布局参考 docs/design.md：
 * - 顶部 Hero：返回按钮 + 标题 + 描述 + 变量进度徽标
 * - 主体两栏：左侧填写表单（带进度条 + 变量字段），右侧生成结果预览（带复制 + 平台快捷入口）
 * - 错误状态用 --color-error-*；主操作「生成提示词」为唯一主按钮
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronLeft, Copy, ExternalLink, FileText, RefreshCcw, Sparkles, Trash2, Wand2 } from 'lucide-vue-next'
import { message } from 'ant-design-vue'
import { getFillData, incrementUseCount } from '@/apis/template_api'
import { extractVariables } from '@/composables/useTemplateVariables'

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

/** 必填变量名列表 = Input 段中提取的变量 ∪ variable_hints 的 key（去重、按出现顺序）。 */
const variables = computed(() => {
  if (!data.value) return []
  const inputVars = extractVariables(data.value.input || '')
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

/** debounce 500ms 持久化草稿 */
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
        savedAt: Date.now(),
      })
    )
  } catch {
    // localStorage 满 / 隐私模式忽略
  }
}

watch(formValues, schedulePersistDraft, { deep: true })
watch(generatedPrompt, schedulePersistDraft)

function clearDraft() {
  if (!data.value) return
  for (const v of varNames.value) formValues.value[v] = ''
  generatedPrompt.value = ''
  lastGeneratedAt.value = null
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
  let filledInput = d.input
  for (const [key, val] of Object.entries(formValues.value)) {
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
  persistDraft()
  incrementUseCount(d.template_id || route.params.id).catch(() => {
    message.warning('使用次数上报失败,不影响 Prompt 生成')
  })
}

async function copyPrompt() {
  if (!generatedPrompt.value) return
  try {
    await navigator.clipboard.writeText(generatedPrompt.value)
    message.success('已复制到剪贴板')
  } catch {
    message.error('复制失败,请手动复制')
  }
}

async function openPlatform(url) {
  if (generatedPrompt.value) {
    try {
      await navigator.clipboard.writeText(generatedPrompt.value)
      message.success('提示词已复制,请在 AI 平台中粘贴（Ctrl/⌘+V）')
    } catch {
      message.warning('请手动复制后再打开 AI 平台')
    }
  } else {
    message.info('尚未生成提示词,将打开 AI 平台空白页')
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

function goBack() {
  router.push({ name: 'template-detail', params: { id: route.params.id } })
}

onMounted(fetchData)
</script>

<template>
  <div class="page-bg">
    <div class="page-content">
      <a-spin :spinning="loading">
        <template v-if="data">
          <!-- 顶部:图标+返回+标题 -->
          <header class="page-bar page-bar--fill">
            <div class="page-bar__left-group">
              <FileText :size="20" class="page-bar__icon" />
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

          <!-- 主体两栏:填写表单 + 预览 -->
          <div class="fill-layout">
            <!-- 左侧:填写表单 -->
            <section class="panel fill-form">
              <div class="panel-header">
                <h2 class="panel-title">
                  <Wand2 :size="18" class="panel-title-icon" />
                  填写信息
                </h2>
                <a-progress
                  v-if="varNames.length"
                  :percent="Math.round(fillProgress * 100)"
                  :show-info="false"
                  :stroke-color="progressState === 'done' ? 'var(--color-success-500)' : 'var(--color-warning-500)'"
                  class="progress-bar"
                />
              </div>

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
                <a-tooltip title="清除当前已填写的全部内容和已生成的 Prompt">
                  <a-button
                    class="reset-btn"
                    @click="clearDraft"
                  >
                    <template #icon><Trash2 :size="14" /></template>
                    清除草稿
                  </a-button>
                </a-tooltip>
              </div>
            </section>

            <!-- 右侧:预览 -->
            <section class="panel fill-preview">
              <div class="panel-header">
                <h2 class="panel-title">
                  <Copy :size="18" class="panel-title-icon" />
                  生成的提示词
                </h2>
                <span v-if="lastGeneratedAt" class="generated-time">
                  <RefreshCcw :size="13" />
                  最近生成 {{ formatTime(lastGeneratedAt) }}
                </span>
              </div>

              <div v-if="generatedPrompt" class="preview-actions">
                <a-button
                  type="primary"
                  class="copy-btn"
                  @click="copyPrompt"
                >
                  <template #icon><Copy :size="16" /></template>
                  复制提示词
                </a-button>
                <div class="platform-group">
                  <span class="platform-label">打开 AI 平台：</span>
                  <a-button
                    v-for="p in PLATFORMS"
                    :key="p.name"
                    size="small"
                    class="platform-chip"
                    @click="openPlatform(p.url)"
                  >
                    <template #icon><ExternalLink :size="13" /></template>
                    {{ p.name }}
                  </a-button>
                </div>
              </div>

              <div class="preview-area" :class="{ 'preview-area--empty': !generatedPrompt }">
                <pre v-if="generatedPrompt" class="preview-text">{{ generatedPrompt }}</pre>
                <div v-else class="preview-placeholder">
                  <Sparkles :size="28" class="preview-placeholder-icon" />
                  <p>填写左侧变量后,点击「生成提示词」</p>
                  <p class="preview-placeholder-sub">结果会在这里显示,可复制到任意 AI 平台使用</p>
                </div>
              </div>
            </section>
          </div>
        </template>
      </a-spin>
    </div>
  </div>
</template>

<style scoped>
/* ==========================================================================
 * 页面骨架 - 已迁移到全局 .page-bg / .page-content / .page-bar
 * Hero 内部块(.hero-progress) 保留在组件内
 * ========================================================================== */
.page-content {
  padding: 24px 0;
}

.page-bar__title {
  font-size: 20px;
}

.page-bar--fill {
  padding: 0 24px;
}

.page-bar--fill .page-bar__title {
  margin-bottom: 0;
}

.page-bar--fill .page-bar__left-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.page-bar--fill .page-bar__icon {
  color: var(--main-color);
  flex-shrink: 0;
}

.page-bar__sub--fill {
  padding: 0 24px;
  margin-bottom: 16px;
}

.fill-layout {
  padding: 0 24px;
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

/* ==========================================================================
 * 主体布局
 * ========================================================================== */
.fill-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr);
  gap: 24px;
  align-items: start;
  margin: 0 auto;
  max-width: 1400px;
}

@media (max-width: 960px) {
  .fill-layout {
    grid-template-columns: 1fr;
  }
}

/* ==========================================================================
 * 面板（卡片化）
 * ========================================================================== */
.panel {
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  padding: 20px 24px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--gray-100);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.panel-title-icon {
  color: var(--main-color);
}

.progress-bar {
  flex: 1;
  max-width: 200px;
}

/* ==========================================================================
 * 填写表单
 * ========================================================================== */
.form-field {
  margin-bottom: 16px;
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
}

.field-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin: 4px 0 0;
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
  padding: 20px 16px;
  background: var(--gray-10);
  border: 1px dashed var(--gray-150);
  border-radius: 6px;
  text-align: center;
  color: var(--color-text-secondary);
  margin-bottom: 16px;
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

.form-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--gray-100);
}

.generate-btn {
  flex: 1;
  font-weight: 500;
}

.reset-btn {
  color: var(--gray-600);
}

/* ==========================================================================
 * 预览面板
 * ========================================================================== */
.generated-time {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.preview-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--gray-100);
}

.copy-btn {
  align-self: flex-start;
}

.platform-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.platform-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-right: 4px;
}

.platform-chip {
  /* chip 形态:中性边框 + hover 主色,符合 design.md 「工具栏按钮」规范 */
  background: var(--gray-0);
  border-color: var(--gray-150);
  color: var(--color-text);
}

.platform-chip:hover {
  border-color: var(--main-color);
  color: var(--main-color);
  background: var(--main-10);
}

.preview-area {
  background: var(--gray-10);
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  padding: 16px;
  min-height: 320px;
}

.preview-area--empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-text {
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-text);
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.preview-placeholder {
  text-align: center;
  color: var(--color-text-tertiary);
}

.preview-placeholder-icon {
  color: var(--gray-200);
  margin-bottom: 12px;
}

.preview-placeholder p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
}

.preview-placeholder-sub {
  margin-top: 4px !important;
  font-size: 12px !important;
  color: var(--gray-400);
}

/* ==========================================================================
 * 响应式
 * ========================================================================== */
@media (max-width: 768px) {
  .content {
    padding: 16px;
  }
  .panel {
    padding: 16px;
  }
  .form-actions {
    flex-direction: column;
    align-items: stretch;
  }
  .generate-btn {
    width: 100%;
  }
  .panel-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .progress-bar {
    max-width: 100%;
    width: 100%;
  }
}
</style>

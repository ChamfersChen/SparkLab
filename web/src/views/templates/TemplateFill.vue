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
import { ChevronLeft, Copy, ExternalLink, RefreshCcw, Sparkles, Trash2, Wand2 } from 'lucide-vue-next'
import { message } from 'ant-design-vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { getFillData, incrementUseCount } from '@/apis/template_api'
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

const renderedPrompt = computed(() => {
  if (!generatedPrompt.value) return ''
  return DOMPurify.sanitize(md.render(generatedPrompt.value))
})

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
              <!-- <FileText :size="20" class="page-bar__icon" /> -->
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
                  size="large"
                  class="generate-btn"
                  :disabled="!canGenerate"
                  @click="generatePrompt"
                >
                  <template #icon><Sparkles :size="16" /></template>
                  {{ canGenerate ? '生成提示词' : `还有 ${missingCount} 项未填` }}
                </a-button>
                <a-tooltip title="清除当前已填写的全部内容和已生成的 Prompt">
                  <a-button class="reset-btn" @click="clearDraft">
                    <template #icon><Trash2 :size="14" /></template>
                    清除草稿
                  </a-button>
                </a-tooltip>
              </div>
            </section>

            <!-- 右侧:预览(sticky,跟随滚动) -->
            <section class="panel fill-preview">
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

              <div class="panel-body panel-body--preview">
                <div v-if="generatedPrompt" class="preview-markdown" v-html="renderedPrompt" />
                <div v-else class="preview-placeholder">
                  <Sparkles :size="32" class="preview-placeholder-icon" />
                  <p class="preview-placeholder-title">填写左侧变量后,点击「生成提示词」</p>
                  <p class="preview-placeholder-sub">结果会在这里显示,可一键复制到任意 AI 平台使用</p>
                </div>
              </div>

              <div v-if="generatedPrompt" class="panel-footer panel-footer--platforms">
                <span class="platform-label">在 AI 平台中打开</span>
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
          </div>
        </template>
      </a-spin>
    </div>
  </div>
</template>

<style scoped>
/* ==========================================================================
 * 页面骨架
 * ========================================================================== */
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

.page-bar__title {
  font-size: 20px;
}

.page-bar--fill {
  padding: 0 24px;
  flex-shrink: 0;
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

/* ==========================================================================
 * 主体两栏布局
 * 关键设计:
 *   1. 两个面板都是 column flex; header / body / footer 三段对齐
 *   2. header min-height 固定 -> 左右栏头部完美对齐(无论内部内容多寡)
 *   3. 右侧 sticky 跟随滚动,顶端贴 24px,最高占满视口 - 48px
 *   4. body 用 flex:1 占满剩余空间,footer 自然贴底
 * ========================================================================== */
.fill-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.25fr);
  gap: 20px;
  flex: 1;
  min-height: 0;
  align-items: stretch;
}

/* ==========================================================================
 * 面板（卡片化,统一 header/body/footer 骨架）
 * ========================================================================== */
.panel {
  display: flex;
  flex-direction: column;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.02);
}

.fill-preview {
  min-height: 0;
}

.fill-form {
  min-height: 0;
}

/* 所有面板 header 同高度 -> 顶部对齐
 * 关键:
 *   - min-height 与 padding 共同保证 box-sizing 下的总高固定
 *   - 子元素统一 align-self: center,避免 Ant 组件默认 baseline 漂移
 *   - header-meta 用 height: 28px 占位,子元素全部 stretch/center
 */
.panel-header {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 12px;
  min-height: 56px;
  padding: 0 20px;
  box-sizing: border-box;
  background: linear-gradient(180deg, var(--gray-0) 0%, var(--gray-10) 100%);
  border-bottom: 1px solid var(--gray-100);
  flex-shrink: 0;
}

.panel-header > * {
  align-self: center;       /* 强制子元素在 56px 内垂直居中,抹平基线差异 */
}

.panel-title {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  height: 28px;              /* 与 header-meta 同高,保证 baseline 锚定 */
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
  letter-spacing: 0.01em;
}

/* 标题图标: 28px 圆角徽章,主色淡底 + 主色 icon */
.panel-title-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--main-10);
  color: var(--main-color);
  flex-shrink: 0;
}

.panel-title-icon--accent {
  background: linear-gradient(135deg, var(--main-color), var(--main-700));
  color: #fff;
  box-shadow: 0 2px 6px rgba(59, 130, 246, 0.25);
}

.header-meta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  height: 28px;             /* 与右侧 header-action-btn 同高,锚定行高 */
}

/* 进度徽章: 与右侧 header 元素体量一致(高度对齐) */
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
  width: 80px;
  height: 22px !important;   /* 锁定 Ant Progress 外层高度,避免挤压行高 */
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

/* body: 占满中段,可滚动 */
.panel-body {
  flex: 1;
  min-height: 0;
  padding: 20px;
  overflow-y: auto;
}

.panel-body--preview {
  padding: 0;
  background: var(--gray-10);
}

/* ==========================================================================
 * 填写表单
 * ========================================================================== */
.form-field {
  margin-bottom: 16px;
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
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
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

/* ==========================================================================
 * footer(两种形态,但外形态体量一致)
 * ========================================================================== */
.panel-footer {
  padding: 14px 20px;
  background: var(--gray-10);
  border-top: 1px solid var(--gray-100);
  flex-shrink: 0;
}

.panel-footer--actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.generate-btn {
  flex: 1;
  height: 40px;
  font-weight: 500;
  box-shadow: 0 1px 2px rgba(59, 130, 246, 0.15);
  transition: box-shadow 0.15s ease, transform 0.05s ease;
}

.generate-btn:not(:disabled):hover {
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.28);
}

.generate-btn:not(:disabled):active {
  transform: translateY(1px);
}

.reset-btn {
  height: 40px;
  color: var(--gray-600);
}

/* ==========================================================================
 * 预览面板 - Markdown 渲染
 * ========================================================================== */
.preview-markdown {
  padding: 20px;
  font-size: 14px;
  line-height: 1.75;
  color: var(--color-text);
  word-break: break-word;
}

.preview-markdown h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin: 24px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--gray-50);
}

.preview-markdown h2:first-child {
  margin-top: 0;
}

.preview-markdown p {
  margin: 0 0 12px;
  line-height: 1.75;
}

.preview-markdown hr {
  border: none;
  border-top: 1px dashed var(--gray-100);
  margin: 20px 0;
}

.preview-markdown ul,
.preview-markdown ol {
  padding-left: 20px;
  margin: 0 0 12px;
}

.preview-markdown li {
  margin-bottom: 4px;
  line-height: 1.75;
}

.preview-markdown code {
  background: var(--gray-25);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: var(--font-mono);
}

.preview-markdown pre {
  background: var(--gray-25);
  padding: 12px 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0 0 12px;
}

.preview-markdown pre code {
  background: none;
  padding: 0;
}

.preview-markdown blockquote {
  border-left: 3px solid var(--main-color);
  padding: 4px 12px;
  margin: 0 0 12px;
  color: var(--color-text-secondary);
  background: var(--main-10);
  border-radius: 0 6px 6px 0;
}

.preview-markdown strong {
  font-weight: 600;
  color: var(--color-text);
}

.preview-markdown a {
  color: var(--main-color);
  text-decoration: none;
}

.preview-markdown a:hover {
  text-decoration: underline;
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--color-text-tertiary);
  min-height: 360px;
  padding: 40px 24px;
}

.preview-placeholder-icon {
  color: var(--main-500);
  margin-bottom: 12px;
  opacity: 0.5;
}

.preview-placeholder-title {
  font-size: 14px;
  color: var(--color-text-secondary);
  font-weight: 500;
  margin: 0 0 4px;
}

.preview-placeholder-sub {
  font-size: 12px;
  color: var(--gray-400);
  margin: 0;
  line-height: 1.6;
}

.panel-footer--platforms {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 10px;
}

.platform-label {
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-weight: 500;
}

.platform-group {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* chip 形态:中性边框 + hover 主色淡底,克制感 */
.platform-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 10px;
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 999px;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.platform-chip:hover {
  background: var(--main-10);
  border-color: var(--main-color);
  color: var(--main-700);
}

/* ==========================================================================
 * 响应式
 * ========================================================================== */
@media (max-width: 960px) {
  .page-bg {
    height: auto;
    min-height: 100vh;
    overflow: visible;
    padding-bottom: 64px;
  }
  .page-content {
    overflow: visible;
    display: block;
  }
  :deep(.ant-spin-nested-loading),
  :deep(.ant-spin-container) {
    overflow: visible;
    display: block;
  }
  .fill-layout {
    grid-template-columns: 1fr;
    min-height: auto;
  }
  .fill-form,
  .fill-preview {
    min-height: auto;
  }
  .fill-preview {
    position: static;
    max-height: none;
  }
}

@media (max-width: 768px) {
  .page-content {
    padding: 16px 0;
  }
  .fill-layout {
    padding: 0 12px;
    gap: 16px;
  }
  .panel-header {
    padding: 10px 14px;
    min-height: 52px;
  }
  .panel-body {
    padding: 16px;
  }
  .panel-footer {
    padding: 12px 14px;
  }
  .panel-footer--actions {
    flex-direction: column-reverse;
    align-items: stretch;
  }
  .generate-btn,
  .reset-btn {
    width: 100%;
  }
  .progress-bar {
    display: none;
  }
}
</style>

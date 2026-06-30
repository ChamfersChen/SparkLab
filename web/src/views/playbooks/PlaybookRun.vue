<script setup>
/**
 * 工作流运行页（用户端）。
 *
 * 流程：
 *   1. 进入页面：拉取 playbook 详情 + 顶部 +1 use_count
 *   2. 每步循环：
 *      - 顶部可折叠的"上一步 AI 结果"粘回区(仅当本步 content 引用了 {{prev_output}})
 *      - 本步变量填写区(自动从 content 提取 {{var}},排除 {{prev_output}})
 *      - 底部"复制本步 prompt / 打开 AI 平台"按钮 → 用户去第三方 AI 平台提问
 *      - 粘贴 AI 结果到粘回区 → 下一步继续
 *   3. 最后一步:调用 /run 返回拼接后的完整 prompt,Markdown 渲染 + 复制 + AI 平台跳转
 *   4. 草稿持久化：localStorage 存 formValues (workflow-level + step-level),**不存 prev_output**(私密)
 *
 * 与 TemplateFill 一致的设计:
 *   - 28px 紧凑工具栏
 *   - markdown-it 渲染 + 复制/平台跳转
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronLeft,
  Copy,
  ExternalLink,
  RefreshCcw,
  Sparkles,
  Wand2,
} from 'lucide-vue-next'
import MarkdownIt from 'markdown-it'
import { getPlaybook, incrementUseCount, runPlaybook } from '@/apis/playbook_api'

const route = useRoute()
const router = useRouter()

const PLATFORMS = [
  { name: 'DeepSeek', url: 'https://chat.deepseek.com' },
  { name: '豆包', url: 'https://www.doubao.com/chat/' },
  { name: '通义千问', url: 'https://tongyi.aliyun.com/qianwen/' },
  { name: '文心一言', url: 'https://yiyan.baidu.com/' },
]

const loading = ref(false)
const playbook = ref(null)
// workflow-level form values
const workflowFormValues = ref({})
// per-step form values, keyed by step_order
const stepFormValues = ref({})
// 渲染好的每步 prompt(用于本地预览,不持久化)
const stepFilledPrompts = ref({})
// 每步用户粘回的 AI 结果,keyed by step_order,**不持久化**
const stepPrevOutputs = ref({})

const currentStepIndex = ref(0)
const running = ref(false)

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
}).use((mdInstance) => {
  const defaultLinkOpen =
    mdInstance.renderer.rules.link_open ||
    function (tokens, idx, options, _env, self) {
      return self.renderToken(tokens, idx, options)
    }
  mdInstance.renderer.link_open = function (tokens, idx, options, env, self) {
    const t = tokens[idx]
    t.attrSet('target', '_blank')
    t.attrSet('rel', 'noopener noreferrer')
    return defaultLinkOpen(tokens, idx, options, env, self)
  }
})

const renderedFinal = ref('')

function draftKey(id) {
  return `sparklab:playbook-draft:${id}`
}

function saveDraft() {
  if (!playbook.value) return
  try {
    localStorage.setItem(
      draftKey(playbook.value.id),
      JSON.stringify({
        workflowFormValues: { ...workflowFormValues.value },
        stepFormValues: { ...stepFormValues.value },
        currentStepIndex: currentStepIndex.value,
        savedAt: Date.now(),
      }),
    )
  } catch {
    // ignore
  }
}

function loadDraft() {
  if (!playbook.value) return
  try {
    const raw = localStorage.getItem(draftKey(playbook.value.id))
    if (!raw) return
    const d = JSON.parse(raw)
    if (d.workflowFormValues) Object.assign(workflowFormValues.value, d.workflowFormValues)
    if (d.stepFormValues) {
      for (const [k, v] of Object.entries(d.stepFormValues)) {
        stepFormValues.value[Number(k)] = { ...(v || {}) }
      }
    }
    if (typeof d.currentStepIndex === 'number') currentStepIndex.value = d.currentStepIndex
  } catch {
    // ignore
  }
}

function clearDraft() {
  if (!playbook.value) return
  workflowFormValues.value = {}
  stepFormValues.value = {}
  stepFilledPrompts.value = {}
  stepPrevOutputs.value = {}
  currentStepIndex.value = 0
  renderedFinal.value = ''
  localStorage.removeItem(draftKey(playbook.value.id))
  message.success('草稿已清除')
}

function extractVariables(text) {
  const re = /\{\{(.*?)\}\}/g
  const result = []
  const seen = new Set()
  let m
  while ((m = re.exec(text || '')) !== null) {
    const k = m[1].trim()
    if (k === 'prev_output') continue
    if (!seen.has(k)) {
      seen.add(k)
      result.push(k)
    }
  }
  return result
}

function refPrevOutput(text) {
  return /\{\{\s*prev_output\s*\}\}/.test(text || '')
}

/** 在本地用 prev_output (若有) + form_values 替换 {{var}}。返回 (filled, prev_output_injected) */
function fillLocal(text, formValues, prevOutput) {
  if (!text) return { filled: '', injected: false }
  let t = text
  let injected = false
  if (prevOutput && /\{\{\s*prev_output\s*\}\}/.test(t)) {
    t = t.replace(/\{\{\s*prev_output\s*\}\}/g, prevOutput)
    injected = true
  }
  t = (t || '').replace(/\{\{(.*?)\}\}/g, (m, k) => {
    const key = k.trim()
    if (key === 'prev_output') return m  // 已被替换,残留的当字面量
    const v = formValues[key]
    return v && String(v).trim() ? String(v).trim() : m
  })
  return { filled: t, injected }
}

async function fetchData() {
  loading.value = true
  try {
    const p = await getPlaybook(route.params.id)
    playbook.value = p
    // 初始化 workflowFormValues 的 key
    const wfVars = extractVariables(p.content || '')
    for (const v of wfVars) {
      if (!(v in workflowFormValues.value)) workflowFormValues.value[v] = ''
    }
    // 初始化每步 form values key(排除 prev_output)
    for (const step of p.steps) {
      const stepVars = extractVariables(step.content || '')
      if (!stepFormValues.value[step.step_order]) stepFormValues.value[step.step_order] = {}
      for (const v of stepVars) {
        if (!(v in stepFormValues.value[step.step_order])) {
          stepFormValues.value[step.step_order][v] = ''
        }
      }
    }
    loadDraft()
    incrementUseCount(p.id).catch(() => {
      // 静默失败,不影响使用
    })
  } catch (e) {
    if (e?.response?.status !== 401) {
      message.error('工作流加载失败')
    }
    router.replace({ name: 'playbooks' })
  } finally {
    loading.value = false
  }
}

const totalSteps = computed(() => playbook.value?.steps.length || 0)
const currentStep = computed(() => playbook.value?.steps[currentStepIndex.value] || null)
const currentStepVars = computed(() => extractVariables(currentStep.value?.content || ''))
const currentStepUsesPrev = computed(() => refPrevOutput(currentStep.value?.content || ''))
const currentStepMissingCount = computed(() => {
  if (!currentStep.value) return 0
  return currentStepVars.value.filter(
    (v) => !stepFormValues.value[currentStep.value.step_order]?.[v]?.trim(),
  ).length
})

// prev_output 仅当 (a) 当前步引用了 {{prev_output}} (b) 不是首步 才渲染粘回区
const showPrevOutputSection = computed(() => {
  if (!currentStep.value) return false
  if (currentStepIndex.value === 0) return false
  return currentStepUsesPrev.value
})

const workflowMissingCount = computed(() => {
  if (!playbook.value) return 0
  return extractVariables(playbook.value.content || '').filter(
    (v) => !workflowFormValues.value[v]?.trim(),
  ).length
})

/** 在本地生成本步渲染结果(用于顶部折叠预览 + 复制) */
function generateCurrentStep() {
  if (!currentStep.value) return
  const so = currentStep.value.step_order
  const { filled } = fillLocal(
    currentStep.value.content || '',
    stepFormValues.value[so] || {},
    stepPrevOutputs.value[so] || null,
  )
  stepFilledPrompts.value[so] = filled
  message.success('已生成本步提示词预览')
  saveDraft()
}

function goToPrev() {
  if (currentStepIndex.value > 0) {
    currentStepIndex.value -= 1
    saveDraft()
  }
}

function goToNext() {
  if (currentStepIndex.value < totalSteps.value - 1) {
    currentStepIndex.value += 1
    saveDraft()
  }
}

function setPrevOutputForCurrent(text) {
  if (!currentStep.value) return
  stepPrevOutputs.value[currentStep.value.step_order] = text
}

/** 当前步渲染(用户点击"复制本步 prompt"时调用,确保本地有最新值) */
function currentStepRendered() {
  if (!currentStep.value) return ''
  // 优先用已生成的预览(保证用户视觉与复制一致);否则临时渲染
  const so = currentStep.value.step_order
  if (stepFilledPrompts.value[so]) return stepFilledPrompts.value[so]
  const { filled } = fillLocal(
    currentStep.value.content || '',
    stepFormValues.value[so] || {},
    stepPrevOutputs.value[so] || null,
  )
  return filled
}

async function copyCurrentStep() {
  const text = currentStepRendered()
  if (!text) {
    message.warning('请先生成预览或填写变量')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    message.success('本步 prompt 已复制')
  } catch {
    message.error('复制失败,请手动复制')
  }
}

async function openPlatformForCurrent(url) {
  const text = currentStepRendered()
  if (text) {
    try {
      await navigator.clipboard.writeText(text)
      message.success('已复制本步 prompt,请到 AI 平台粘贴')
    } catch {
      message.warning('请手动复制后再打开 AI 平台')
    }
  } else {
    message.info('本步尚无内容,将打开 AI 平台空白页')
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

async function generateFinal() {
  if (!playbook.value) return
  // 校验: 含 prev_output 的步必须有粘回
  for (const s of playbook.value.steps) {
    if (refPrevOutput(s.content) && !(stepPrevOutputs.value[s.step_order] || '').trim()) {
      message.warning(`第 ${s.step_order + 1} 步「${s.name}」需要「上一步结果」,请先粘回`)
      return
    }
  }
  running.value = true
  try {
    const step_outputs = playbook.value.steps.map((s) => ({
      step_order: s.step_order,
      form_values: { ...(stepFormValues.value[s.step_order] || {}) },
      prev_output: stepPrevOutputs.value[s.step_order] || null,
    }))
    const res = await runPlaybook(playbook.value.id, {
      form_values: { ...workflowFormValues.value },
      step_outputs,
    })
    renderedFinal.value = md.render(res.final_prompt)
    message.success('已生成最终提示词')
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '生成失败')
  } finally {
    running.value = false
  }
}

async function copyFinal() {
  if (!playbook.value) return
  try {
    const step_outputs = playbook.value.steps.map((s) => ({
      step_order: s.step_order,
      form_values: { ...(stepFormValues.value[s.step_order] || {}) },
      prev_output: stepPrevOutputs.value[s.step_order] || null,
    }))
    const res = await runPlaybook(playbook.value.id, {
      form_values: { ...workflowFormValues.value },
      step_outputs,
    })
    await navigator.clipboard.writeText(res.final_prompt)
    message.success('已复制到剪贴板')
  } catch {
    message.error('复制失败,请手动复制')
  }
}

async function openPlatformFinal(url) {
  if (!playbook.value) return
  try {
    const step_outputs = playbook.value.steps.map((s) => ({
      step_order: s.step_order,
      form_values: { ...(stepFormValues.value[s.step_order] || {}) },
      prev_output: stepPrevOutputs.value[s.step_order] || null,
    }))
    const res = await runPlaybook(playbook.value.id, {
      form_values: { ...workflowFormValues.value },
      step_outputs,
    })
    await navigator.clipboard.writeText(res.final_prompt)
    message.success('提示词已复制,请在 AI 平台中粘贴')
  } catch {
    message.warning('请手动复制后再打开 AI 平台')
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

function goBack() {
  router.push({ name: 'playbooks' })
}

onMounted(fetchData)
</script>

<template>
  <div class="page-bg">
    <div class="page-content">
      <a-spin :spinning="loading">
        <template v-if="playbook">
          <header class="page-bar page-bar--fill">
            <div class="page-bar__left-group">
              <button type="button" class="icon-text-btn" @click="goBack">
                <ChevronLeft :size="16" />
                <span>返回</span>
              </button>
              <h1 class="page-bar__title">{{ playbook.title }}</h1>
            </div>
            <div class="hero-progress">
              <span class="progress-pill">
                {{ totalSteps }} 个步骤
              </span>
            </div>
          </header>

          <p v-if="playbook.description" class="page-bar__sub page-bar__sub--fill">{{ playbook.description }}</p>

          <!-- 工作流级变量填写(若 playbook.content 有 {{var}}) -->
          <section v-if="extractVariables(playbook.content || '').length" class="workflow-form card-block">
            <h3 class="workflow-form__title">工作流参数</h3>
            <div class="workflow-form__grid">
              <div
                v-for="v in extractVariables(playbook.content || '')"
                :key="v"
                class="form-field"
                :class="{ 'form-field--error': !workflowFormValues[v]?.trim() }"
              >
                <div class="field-label-row">
                  <label class="field-label">{{ v }}<span class="required-mark">*</span></label>
                </div>
                <a-input
                  v-model:value="workflowFormValues[v]"
                  :placeholder="`请输入${v}`"
                  class="field-input"
                />
              </div>
            </div>
            <div v-if="workflowMissingCount > 0" class="workflow-form__hint">
              还有 {{ workflowMissingCount }} 个工作流参数未填
            </div>
          </section>

          <div class="run-layout">
            <!-- 左:步骤导航 -->
            <aside class="step-nav">
              <div class="step-nav__title">步骤导航</div>
              <div
                v-for="(s, idx) in playbook.steps"
                :key="s.id || idx"
                class="step-nav__item"
                :class="{
                  'step-nav__item--current': idx === currentStepIndex,
                  'step-nav__item--done': idx < currentStepIndex,
                }"
                @click="currentStepIndex = idx"
              >
                <span class="step-nav__no">{{ idx + 1 }}</span>
                <div class="step-nav__body">
                  <div class="step-nav__name">{{ s.name }}</div>
                  <div v-if="s.description" class="step-nav__desc">{{ s.description }}</div>
                </div>
                <Check v-if="idx < currentStepIndex" :size="14" class="step-nav__check" />
              </div>
            </aside>

            <!-- 右:主交互区 -->
            <main class="run-main">
              <!-- 当前步骤交互 -->
              <section class="panel">
                <div class="panel-header">
                  <h2 class="panel-title">
                    <span class="panel-title-icon"><Wand2 :size="16" /></span>
                    <span>第 {{ currentStepIndex + 1 }} 步：{{ currentStep?.name }}</span>
                  </h2>
                  <div class="header-meta">
                    <span
                      v-if="currentStepMissingCount > 0"
                      class="header-badge header-badge--partial"
                    >还差 {{ currentStepMissingCount }} 项</span>
                    <span
                      v-else
                      class="header-badge header-badge--done"
                    >已填完</span>
                  </div>
                </div>

                <div class="panel-body">
                  <!-- 1) 上一步 AI 结果粘回区 -->
                  <div v-if="showPrevOutputSection" class="prev-paste">
                    <div class="prev-paste__header">
                      <span class="prev-paste__title">📋 上一步 AI 平台返回的结果</span>
                      <span v-if="(stepPrevOutputs[currentStep?.step_order] || '').trim()" class="prev-paste__status">
                        已粘回 · {{ (stepPrevOutputs[currentStep.step_order] || '').length }} 字
                      </span>
                    </div>
                    <p class="prev-paste__hint">
                      去 AI 平台把上一步生成的内容贴回来,会自动注入到本步的 <code>{`{{prev_output}}`}</code> 占位符。
                    </p>
                    <a-textarea
                      :model-value="stepPrevOutputs[currentStep?.step_order] || ''"
                      @update:model-value="(v) => setPrevOutputForCurrent(v)"
                      :rows="5"
                      :auto-size="{ minRows: 5, maxRows: 16 }"
                      :placeholder="`把第 ${currentStepIndex} 步在 AI 平台生成的内容粘到这里`"
                    />
                  </div>

                  <p v-if="currentStep?.description" class="step-desc">{{ currentStep.description }}</p>

                  <!-- 2) 本步变量填写 -->
                  <div
                    v-for="v in currentStepVars"
                    :key="v"
                    class="form-field"
                    :class="{ 'form-field--error': !stepFormValues[currentStep?.step_order]?.[v]?.trim() }"
                  >
                    <div class="field-label-row">
                      <label class="field-label">
                        {{ v }}
                        <span class="required-mark">*</span>
                      </label>
                    </div>
                    <a-textarea
                      v-model:value="stepFormValues[currentStep.step_order][v]"
                      :placeholder="`请输入${v}`"
                      :rows="3"
                      :status="!stepFormValues[currentStep.step_order][v]?.trim() ? 'error' : ''"
                      class="field-input"
                    />
                  </div>

                  <div v-if="!currentStepVars.length && !showPrevOutputSection" class="no-vars">
                    <p class="no-vars-title">本步无变量</p>
                    <p class="no-vars-desc">直接生成或跳到 AI 平台即可</p>
                  </div>

                  <!-- 3) 本步 prompt 预览(若已生成) -->
                  <div v-if="stepFilledPrompts[currentStep?.step_order]" class="current-preview">
                    <div class="current-preview__title">本步 prompt 预览</div>
                    <pre class="current-preview__pre">{{ stepFilledPrompts[currentStep.step_order] }}</pre>
                  </div>
                </div>

                <div class="panel-footer panel-footer--pipeline">
                  <a-button :disabled="currentStepIndex === 0" @click="goToPrev">
                    <template #icon><ArrowLeft :size="14" /></template>
                    上一步
                  </a-button>
                  <a-button
                    :disabled="currentStepMissingCount > 0"
                    @click="generateCurrentStep"
                  >
                    <template #icon><Sparkles :size="14" /></template>
                    生成本步预览
                  </a-button>
                  <a-button
                    type="primary"
                    :disabled="currentStepMissingCount > 0 || (showPrevOutputSection && !(stepPrevOutputs[currentStep?.step_order] || '').trim())"
                    @click="copyCurrentStep"
                  >
                    <template #icon><Copy :size="14" /></template>
                    复制本步 prompt
                  </a-button>
                  <div class="platform-group platform-group--inline">
                    <button
                      v-for="p in PLATFORMS"
                      :key="p.name"
                      type="button"
                      class="platform-chip"
                      @click="openPlatformForCurrent(p.url)"
                    >
                      <span>{{ p.name }}</span>
                      <ExternalLink :size="11" />
                    </button>
                  </div>
                  <a-button
                    v-if="currentStepIndex < totalSteps - 1"
                    type="primary"
                    ghost
                    @click="goToNext"
                  >
                    下一步
                    <template #icon><ArrowRight :size="14" /></template>
                  </a-button>
                  <a-button
                    v-else
                    type="primary"
                    :loading="running"
                    @click="generateFinal"
                  >
                    查看最终结果
                    <template #icon><Sparkles :size="14" /></template>
                  </a-button>
                </div>
              </section>

              <!-- 最终结果 -->
              <section v-if="renderedFinal" class="panel panel--result">
                <div class="panel-header">
                  <h2 class="panel-title">
                    <span class="panel-title-icon panel-title-icon--accent"><Sparkles :size="16" /></span>
                    <span>最终提示词</span>
                  </h2>
                  <div class="header-meta">
                    <button
                      type="button"
                      class="header-action-btn"
                      @click="copyFinal"
                    >
                      <Copy :size="14" />
                      <span>复制</span>
                    </button>
                  </div>
                </div>

                <div class="panel-body panel-body--preview">
                  <div class="preview-md" v-html="renderedFinal"></div>
                </div>

                <div class="panel-footer panel-footer--platforms">
                  <span class="platform-label">在 AI 平台中打开</span>
                  <div class="platform-group">
                    <button
                      v-for="p in PLATFORMS"
                      :key="p.name"
                      type="button"
                      class="platform-chip"
                      @click="openPlatformFinal(p.url)"
                    >
                      <span>{{ p.name }}</span>
                      <ExternalLink :size="11" />
                    </button>
                  </div>
                </div>
              </section>

              <!-- 底部工具栏 -->
              <div class="run-toolbar">
                <a-tooltip title="清除当前已填写的全部内容和已生成的最终结果">
                  <a-button size="small" @click="clearDraft">
                    <template #icon><RefreshCcw :size="12" /></template>
                    清除草稿
                  </a-button>
                </a-tooltip>
              </div>
            </main>
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
  padding: 20px 0 0;
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
  margin-bottom: 8px;
}

.page-bar--fill .page-bar__left-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.page-bar__sub--fill {
  padding: 0 24px;
  margin-bottom: 16px;
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
  background: var(--main-10);
  color: var(--main-700);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}

/* 工作流级参数卡片 */
.workflow-form {
  margin: 0 24px 16px;
  padding: 16px 20px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 10px;
}

.workflow-form__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.workflow-form__title::before {
  content: '';
  display: inline-block;
  width: 3px;
  height: 14px;
  background: var(--main-color);
  border-radius: 2px;
}

.workflow-form__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.workflow-form__hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--color-warning-700);
}

.run-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 16px;
  padding: 0 24px 24px;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
}

/* 左侧步骤导航 */
.step-nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  height: fit-content;
  position: sticky;
  top: 20px;
  align-self: start;
}

.step-nav__title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  margin-bottom: 4px;
  padding: 0 4px;
}

.step-nav__item {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  align-items: flex-start;
  gap: 8px;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.step-nav__item:hover {
  background: var(--gray-10);
}

.step-nav__item--current {
  background: var(--main-10);
}

.step-nav__no {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--gray-150);
  color: var(--color-text-secondary);
  font-size: 11px;
  font-weight: 600;
}

.step-nav__item--current .step-nav__no {
  background: var(--main-color);
  color: #fff;
}

.step-nav__item--done .step-nav__no {
  background: var(--color-success-500);
  color: #fff;
}

.step-nav__body {
  min-width: 0;
}

.step-nav__name {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-nav__item--current .step-nav__name {
  color: var(--main-700);
  font-weight: 600;
}

.step-nav__desc {
  font-size: 11px;
  color: var(--color-text-tertiary);
  line-height: 1.4;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.step-nav__check {
  color: var(--color-success-500);
  margin-top: 4px;
}

/* 右侧主区域 */
.run-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
}

.panel {
  display: flex;
  flex-direction: column;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 10px;
  overflow: hidden;
  flex: 1;
  min-height: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 56px;
  padding: 0 20px;
  background: linear-gradient(180deg, var(--gray-0) 0%, var(--gray-10) 100%);
  border-bottom: 1px solid var(--gray-100);
}

.panel-header > * {
  align-self: center;
}

.panel-title {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  height: 28px;
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

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
  background: var(--gray-100);
  color: var(--gray-700);
}

.header-badge--partial {
  background: var(--color-warning-50);
  color: var(--color-warning-900);
}

.header-badge--done {
  background: var(--color-success-50);
  color: var(--color-success-700);
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
  flex: 1 1 0;
  min-height: 0;
  padding: 20px;
  overflow-y: auto;
}

.panel-body--preview {
  padding: 0;
  background: var(--gray-10);
}

/* 上一步 AI 结果粘回区 */
.prev-paste {
  margin-bottom: 20px;
  padding: 14px 16px;
  background: var(--color-warning-50);
  border: 1px solid var(--color-warning-200);
  border-radius: 8px;
}

.prev-paste__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.prev-paste__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-warning-900);
}

.prev-paste__status {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  background: var(--gray-0);
  color: var(--color-success-700);
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid var(--color-success-200);
}

.prev-paste__hint {
  font-size: 12px;
  color: var(--color-warning-700);
  margin: 0 0 8px;
  line-height: 1.6;
}

.prev-paste__hint code {
  background: var(--gray-0);
  padding: 0 4px;
  border-radius: 3px;
  font-size: 11px;
  color: var(--color-warning-900);
  border: 1px solid var(--color-warning-200);
}

.step-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0 0 16px;
  padding: 8px 12px;
  background: var(--main-10);
  border-left: 3px solid var(--main-color);
  border-radius: 0 4px 4px 0;
}

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

.field-input {
  width: 100%;
}

.field-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin: 6px 0 0;
  line-height: 1.5;
}

.form-field--error .field-label {
  color: var(--color-error-700);
}

.no-vars {
  padding: 24px 16px;
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

/* 本步 prompt 预览(粘回区下方) */
.current-preview {
  margin-top: 16px;
  padding: 12px 14px;
  background: var(--gray-10);
  border: 1px solid var(--gray-150);
  border-radius: 6px;
}

.current-preview__title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.current-preview__title::before {
  content: '✦';
  color: var(--main-color);
}

.current-preview__pre {
  margin: 0;
  padding: 10px 12px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-text);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 280px;
  overflow-y: auto;
}

.panel-footer {
  padding: 14px 20px;
  background: var(--gray-10);
  border-top: 1px solid var(--gray-100);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.panel-footer--pipeline {
  /* 流水线按钮较多,允许换行 */
  row-gap: 10px;
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

.platform-group--inline {
  flex: 1;
  min-width: 0;
  justify-content: flex-end;
}

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

.run-toolbar {
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
}

/* Markdown 渲染样式（与 TemplateFill 对齐） */
.preview-md {
  padding: 20px 24px 24px;
  font-size: 13px;
  line-height: 1.75;
  color: var(--color-text);
}

.preview-md :deep(h1),
.preview-md :deep(h2),
.preview-md :deep(h3) {
  margin: 20px 0 8px;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 0.01em;
  line-height: 1.4;
}

.preview-md :deep(h1) { font-size: 18px; }
.preview-md :deep(h2) {
  font-size: 15px;
  padding-left: 10px;
  border-left: 3px solid var(--main-color);
  background: linear-gradient(90deg, var(--main-10) 0%, transparent 70%);
  border-radius: 2px;
}
.preview-md :deep(h3) { font-size: 16px; }

.preview-md :deep(h1:first-child),
.preview-md :deep(h2:first-child),
.preview-md :deep(h3:first-child) {
  margin-top: 0;
}

.preview-md :deep(p) { margin: 0 0 12px; color: var(--color-text); }
.preview-md :deep(p:last-child) { margin-bottom: 0; }

.preview-md :deep(hr) {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--gray-200), transparent);
  margin: 16px 0;
}

.preview-md :deep(ul),
.preview-md :deep(ol) {
  margin: 8px 0 12px;
  padding-left: 24px;
}

.preview-md :deep(li) { margin: 4px 0; }
.preview-md :deep(li::marker) { color: var(--main-color); }

.preview-md :deep(strong) { font-weight: 600; color: var(--color-text); }
.preview-md :deep(em) { color: var(--color-text-secondary); font-style: italic; }

.preview-md :deep(code) {
  font-family: var(--font-mono);
  font-size: 12.5px;
  padding: 1px 6px;
  background: var(--gray-10);
  border: 1px solid var(--gray-100);
  border-radius: 4px;
  color: var(--main-700);
}

.preview-md :deep(pre) {
  margin: 8px 0 12px;
  padding: 12px 14px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12.5px;
  line-height: 1.6;
}

.preview-md :deep(pre code) {
  padding: 0;
  background: transparent;
  border: none;
  color: var(--color-text);
}

.preview-md :deep(a) {
  color: var(--main-color);
  text-decoration: none;
  border-bottom: 1px dashed currentColor;
}

.preview-md :deep(a:hover) {
  color: var(--main-700);
  border-bottom-style: solid;
}

.preview-md :deep(blockquote) {
  margin: 8px 0 12px;
  padding: 6px 12px;
  background: var(--gray-10);
  border-left: 3px solid var(--gray-300);
  color: var(--color-text-secondary);
  border-radius: 0 4px 4px 0;
}

@media (max-width: 960px) {
  .run-layout {
    grid-template-columns: 1fr;
  }
  .step-nav {
    position: static;
    flex-direction: row;
    overflow-x: auto;
  }
  .step-nav__title { display: none; }
  .step-nav__item {
    min-width: 140px;
  }
  .workflow-form {
    margin-left: 16px;
    margin-right: 16px;
  }
}
</style>

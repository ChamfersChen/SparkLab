<script setup>
/**
 * 流程运行页（用户端，v4 三栏布局）。
 *
 * 流程：
 *   1. 进入页面：拉取 playbook 详情 + 顶部 +1 use_count
 *   2. 三栏布局:
 *      - 左: 步骤导航 (切 step)
 *      - 中: 当前 step 填表 (最大) — 上一步 AI 粘回 / 变量填写 / 预览 / 复制本步 prompt / AI 平台 / 上下步
 *      - 右: 最终结果填写 — 始终可见, Markdown textarea, "保存到我的运行" inline
 *   3. localStorage 持久化: workflowFormValues + stepFormValues + 摘要右栏
 *      (summaryFinalContent / summaryTitle / summaryCollapsed)
 *
 * 设计: 28px 紧凑风格, 弹层/抽屉不再使用; 右栏填的内容不跳路由保存.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Copy,
  ExternalLink,
  Heart,
  RefreshCcw,
  Sparkles,
  Wand2,
  X,
} from 'lucide-vue-next'
import { getPlaybook, incrementUseCount } from '@/apis/playbook_api'
import { createPlaybookRun } from '@/apis/playbook_runs_api'
import { checkFavorited, toggleFavorite } from '@/apis/favorite_api'

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
const isFavorited = ref(false)
const workflowFormValues = ref({})
const stepFormValues = ref({})
const stepFilledPrompts = ref({})
const stepPrevOutputs = ref({})

// v4: 右栏"最终结果" — 始终可见
const summaryFinalContent = ref('')
const summaryTitle = ref('')
const summaryCollapsed = ref(false)
const summarySaved = ref(false)        // 短暂显示"✓ 已保存"
const saving = ref(false)

const currentStepIndex = ref(0)

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
        // v4: 摘要右栏内容持久化
        summaryFinalContent: summaryFinalContent.value,
        summaryTitle: summaryTitle.value,
        summaryCollapsed: summaryCollapsed.value,
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
    // v4: 还原右栏
    if (typeof d.summaryFinalContent === 'string') summaryFinalContent.value = d.summaryFinalContent
    if (typeof d.summaryTitle === 'string') summaryTitle.value = d.summaryTitle
    if (typeof d.summaryCollapsed === 'boolean') summaryCollapsed.value = d.summaryCollapsed
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
  summaryFinalContent.value = ''
  summaryTitle.value = ''
  summaryCollapsed.value = false
  summarySaved.value = false
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

function fillLocal(text, formValues, prevOutput) {
  if (!text) return ''
  let t = text
  if (prevOutput && /\{\{\s*prev_output\s*\}\}/.test(t)) {
    t = t.replace(/\{\{\s*prev_output\s*\}\}/g, prevOutput)
  }
  t = (t || '').replace(/\{\{(.*?)\}\}/g, (m, k) => {
    const key = k.trim()
    if (key === 'prev_output') return m
    const v = formValues[key]
    return v && String(v).trim() ? String(v).trim() : m
  })
  return t
}

async function checkFavoriteStatus() {
  if (!playbook.value) return
  try {
    const res = await checkFavorited('playbook', playbook.value.id)
    isFavorited.value = res.favorited
  } catch { /* 忽略 */ }
}

async function toggleFav() {
  if (!playbook.value) return
  try {
    const res = await toggleFavorite('playbook', playbook.value.id)
    isFavorited.value = res.favorited
    message.success(res.favorited ? '已收藏' : '已取消收藏')
  } catch {
    message.error('操作失败')
  }
}

async function fetchData() {
  loading.value = true
  try {
    const p = await getPlaybook(route.params.id)
    playbook.value = p
    const wfVars = extractVariables(p.content || '')
    for (const v of wfVars) {
      if (!(v in workflowFormValues.value)) workflowFormValues.value[v] = ''
    }
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
    checkFavoriteStatus()
  } catch (e) {
    if (e?.response?.status !== 401) {
      message.error('流程加载失败')
    }
    if (route.query.from === 'my') {
      router.replace({ name: 'my-playbooks' })
    } else {
      router.replace({ name: 'playbooks' })
    }
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

function generateCurrentStep() {
  if (!currentStep.value) return
  const so = currentStep.value.step_order
  const filled = fillLocal(
    currentStep.value.content || '',
    stepFormValues.value[so] || {},
    stepPrevOutputs.value[so] || null,
  )
  stepFilledPrompts.value[so] = filled
  message.success('已生成本步提示词预览')
  saveDraft()
}

function clearStepPreview(so) {
  const order = typeof so === 'number' ? so : currentStep.value?.step_order
  if (order === undefined || order === null) return
  delete stepFilledPrompts.value[order]
  stepFilledPrompts.value = { ...stepFilledPrompts.value }
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

function currentStepRendered() {
  if (!currentStep.value) return ''
  const so = currentStep.value.step_order
  if (stepFilledPrompts.value[so]) return stepFilledPrompts.value[so]
  return fillLocal(
    currentStep.value.content || '',
    stepFormValues.value[so] || {},
    stepPrevOutputs.value[so] || null,
  )
}

import { copyToClipboard } from '@/utils/clipboard'

async function copyCurrentStep() {
  const text = currentStepRendered()
  if (!text) {
    message.warning('请先生成预览或填写变量')
    return
  }
  try {
    await copyToClipboard(text)
    message.success('本步 prompt 已复制')
  } catch {
    message.error('复制失败,请手动复制')
  }
}

async function openPlatformForCurrent(url) {
  const text = currentStepRendered()
  if (text) {
    try {
      await copyToClipboard(text)
      message.success('已复制本步 prompt,请到 AI 平台粘贴')
    } catch {
      message.warning('请手动复制后再打开 AI 平台')
    }
  } else {
    message.info('本步尚无内容,将打开 AI 平台空白页')
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

// v4: 保存到我的运行 (inline 在右栏底部, 不跳路由)
// 成功时短暂显示"✓ 已保存"提示, 用户继续在三栏页内编辑
async function confirmSaveSummary() {
  if (!playbook.value) return
  const hasStepOutput = (playbook.value.steps || []).some(
    (s) => (stepPrevOutputs.value[s.step_order] || '').trim(),
  )
  const hasFinal = !!summaryFinalContent.value.trim()
  if (!hasStepOutput && !hasFinal) {
    message.warning('请先粘回至少 1 个 step 的 AI 结果,或在右栏填写最终结果')
    return
  }
  saving.value = true
  summarySaved.value = false
  try {
    const title =
      summaryTitle.value.trim() ||
      `${playbook.value.title} · ${new Date().toLocaleString('zh-CN', { hour12: false })}`
    const payload = {
      playbook_id: playbook.value.id,
      title,
      final_result: summaryFinalContent.value,
      steps: (playbook.value.steps || []).map((s) => ({
        step_order: s.step_order,
        step_name: s.name,
        user_output: stepPrevOutputs.value[s.step_order] || null,
        form_values: stepFormValues.value[s.step_order] || {},
      })),
    }
    await createPlaybookRun(payload)
    incrementUseCount(playbook.value.id).catch(() => {})
    summarySaved.value = true
    message.success('已保存到「我的运行」')
    setTimeout(() => { summarySaved.value = false }, 2500)
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function goBack() {
  if (route.query.from === 'my') {
    router.push({ name: 'my-playbook-detail', params: { id: route.params.id } })
  } else {
    router.push({ name: 'playbooks' })
  }
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
              <button
                class="fav-btn"
                :class="{ 'fav-btn--active': isFavorited }"
                :title="isFavorited ? '取消收藏' : '收藏'"
                @click="toggleFav"
              >
                <Heart :size="16" :fill="isFavorited ? 'currentColor' : 'none'" />
              </button>
              <span class="progress-pill">
                {{ totalSteps }} 个步骤
              </span>
            </div>
          </header>

          <p v-if="playbook.description" class="page-bar__sub page-bar__sub--fill">{{ playbook.description }}</p>

          <!-- 流程级参数(若 playbook.content 有 {{var}}) -->
          <section v-if="extractVariables(playbook.content || '').length" class="workflow-form card-block">
            <h3 class="workflow-form__title">流程参数</h3>
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
              还有 {{ workflowMissingCount }} 个流程参数未填
            </div>
          </section>

          <!-- 三栏布局: 步骤导航 | 当前 step | 最终结果 -->
          <div class="run-layout">
            <!-- 左: 步骤导航 -->
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

              <!-- AI 平台快捷跳转 -->
              <div class="step-nav__divider" />
              <div class="step-nav__platform-title">AI 平台</div>
              <div class="step-nav__platforms">
                <button
                  v-for="p in PLATFORMS"
                  :key="p.name"
                  type="button"
                  class="platform-chip platform-chip--sidebar"
                  @click="openPlatformForCurrent(p.url)"
                >
                  <span>{{ p.name }}</span>
                  <ExternalLink :size="11" />
                </button>
              </div>
            </aside>

            <!-- 中: 当前 step 面板(最大) -->
            <main class="middle-pane">
              <section class="panel panel--current-step">
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
                      去 AI 平台把上一步生成的内容贴回来,会自动注入到本步的 <code v-pre>{{prev_output}}</code> 占位符。
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

                  <!-- 3) 本步 prompt 预览(可关闭) -->
                  <div v-if="stepFilledPrompts[currentStep?.step_order]" class="current-preview">
                    <button
                      type="button"
                      class="current-preview__close"
                      title="清除本步预览"
                      @click="clearStepPreview(currentStep.step_order)"
                    >
                      <X :size="14" />
                    </button>
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
                    ghost
                    @click="goToNext"
                  >
                    重新走一次
                    <template #icon><ArrowRight :size="14" /></template>
                  </a-button>
                </div>
              </section>
            </main>

            <!-- 右: 最终结果填写(始终可见) -->
            <aside class="summary-pane">
              <section class="panel panel--summary">
                <div class="panel-header">
                  <h2 class="panel-title">
                    <span class="panel-title-icon panel-title-icon--accent"><Sparkles :size="16" /></span>
                    <span>最终结果</span>
                    <button
                      type="button"
                      class="panel-collapse-btn"
                      :title="summaryCollapsed ? '展开' : '折叠'"
                      @click="summaryCollapsed = !summaryCollapsed; saveDraft()"
                    >
                      <ChevronRight v-if="summaryCollapsed" :size="14" />
                      <ChevronLeft v-else :size="14" />
                    </button>
                  </h2>
                </div>

                <div v-show="!summaryCollapsed" class="panel-body panel-body--summary">
                  <p class="summary-hint">
                    走完流程后, 把最终结论写在这里。<strong>支持 Markdown</strong>。保存时会与每步补充后的 prompt 一起存入个人中心。
                  </p>
                  <a-form layout="vertical">
                    <a-form-item label="运行标题（可选, 留空自动生成）">
                      <a-input
                        v-model:value="summaryTitle"
                        placeholder="例: 2026 春季产品定位"
                        :maxlength="200"
                        show-count
                      />
                    </a-form-item>
                    <a-form-item label="最终结果（Markdown）">
                      <a-textarea
                        v-model:value="summaryFinalContent"
                        :rows="18"
                        :auto-size="{ minRows: 12, maxRows: 30 }"
                        placeholder="把流程跑完后的最终结论写在这里。例如:

# 产品定位
- 目标人群: 25-35 岁都市女性
- 核心卖点: 极致便携 + 时尚外观
- 价格区间: 299-499 元
..."
                      />
                    </a-form-item>
                  </a-form>
                  <div class="summary-actions">
                    <a-button
                      type="primary"
                      size="middle"
                      :loading="saving"
                      @click="confirmSaveSummary"
                    >
                      保存
                    </a-button>
                    <span v-if="summarySaved" class="summary-saved-tag">✓ 已保存</span>
                    <span v-else class="summary-saved-tip">
                      可随时保存 — 不会打断你的编辑. 可在「个人中心 - 流程」查看
                    </span>
                  </div>
                </div>
              </section>
            </aside>
          </div>

          <!-- 底部工具栏 -->
          <div class="run-toolbar">
            <a-tooltip title="清除当前已填写的全部内容和右栏最终结果">
              <a-button size="small" @click="clearDraft">
                <template #icon><RefreshCcw :size="12" /></template>
                清除草稿
              </a-button>
            </a-tooltip>
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

/* 流程级参数卡片 */
.workflow-form {
  margin: 0 24px 16px;
  padding: 16px 20px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
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

/* v4: 三栏布局 (步骤导航 / 当前 step / 最终结果) */
.run-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 220px minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 16px;
  padding: 0 24px 24px;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
}

@media (max-width: 1280px) {
  .run-layout {
    grid-template-columns: 200px minmax(0, 1.2fr) minmax(0, 1fr);
  }
}

@media (max-width: 1024px) {
  .run-layout {
    grid-template-columns: 200px minmax(0, 1fr);
  }
  .summary-pane {
    grid-column: 2;
  }
}

/* 左侧步骤导航 (复用 v3) */
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
  color: var(--gray-0);
}

.step-nav__item--done .step-nav__no {
  background: var(--color-success-500);
  color: var(--gray-0);
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

.step-nav__divider {
  height: 1px;
  background: var(--gray-150);
  margin: 4px 0;
}

.step-nav__platform-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  padding: 0 4px;
}

.step-nav__platforms {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.platform-chip--sidebar {
  width: 100%;
  justify-content: center;
}

/* 中间栏 */
.middle-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
}

/* 右侧汇总栏 */
.summary-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
}

/* panel 基础 (复用 v3) */
.panel {
  display: flex;
  flex-direction: column;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
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
  background: var(--gray-0);
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
  flex: 1;
  min-width: 0;
}

.panel-collapse-btn {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  padding: 0;
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.panel-collapse-btn:hover {
  border-color: var(--main-color);
  color: var(--main-color);
  background: var(--main-10);
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
  background: var(--main-color);
  color: var(--gray-0);
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

.panel-body {
  flex: 1 1 0;
  min-height: 0;
  padding: 20px;
  overflow-y: auto;
}

.panel-body--summary {
  display: flex;
  flex-direction: column;
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

/* 本步 prompt 预览(可关闭) */
.current-preview {
  position: relative;
  margin-top: 16px;
  padding: 12px 14px;
  background: var(--gray-10);
  border: 1px solid var(--gray-150);
  border-radius: 6px;
}

.current-preview__close {
  position: absolute;
  top: 6px;
  right: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 50%;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.current-preview__close:hover {
  color: var(--color-error-600);
  border-color: var(--color-error-500);
  background: var(--color-error-50);
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
  row-gap: 10px;
}

.platform-group {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
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
  padding: 12px 24px;
}

/* 右侧汇总栏样式 */
.summary-hint {
  font-size: 12px;
  color: var(--color-text-tertiary);
  line-height: 1.6;
  margin: 0 0 16px;
  padding: 10px 12px;
  background: var(--main-10);
  border-radius: 6px;
}

.summary-hint strong {
  color: var(--main-700);
}

.summary-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}

.summary-saved-tag {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  background: var(--color-success-50);
  color: var(--color-success-700);
  border: 1px solid var(--color-success-200);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.summary-saved-tip {
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-style: italic;
}

/* ========== Mobile (<=768px) ========== */
@media (max-width: 768px) {
  .page-bg {
    height: auto;
    overflow: visible;
  }

  .page-content {
    overflow: visible;
    padding: 16px 0 0;
  }

  :deep(.ant-spin-nested-loading),
  :deep(.ant-spin-container) {
    overflow: visible;
  }

  .page-bar--fill {
    padding: 0 16px;
  }

  .page-bar__sub--fill {
    padding: 0 16px;
    margin-bottom: 12px;
  }

  .run-layout {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 0 16px 16px;
  }

  .step-nav {
    flex-direction: row;
    overflow-x: auto;
    gap: 8px;
    padding: 10px 12px;
    height: auto;
    position: static;
    -webkit-overflow-scrolling: touch;
  }

  .step-nav__title {
    display: none;
  }

  .step-nav__item {
    grid-template-columns: 22px 1fr;
    flex-shrink: 0;
    min-width: 120px;
    padding: 6px 10px;
  }

  .step-nav__desc {
    display: none;
  }

  .step-nav__divider {
    display: none;
  }

  .step-nav__platform-title {
    display: none;
  }

  .step-nav__platforms {
    display: none;
  }

  .platform-chip--sidebar {
    width: auto;
  }

  .middle-pane,
  .summary-pane {
    overflow-y: visible;
  }

  .run-toolbar {
    padding: 12px 16px;
  }
}

/* 收藏按钮 */
.fav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--gray-0);
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.fav-btn:hover {
  border-color: var(--main-color);
  color: var(--main-color);
  background: var(--main-10);
}

.fav-btn--active {
  border-color: var(--main-color);
  color: var(--main-color);
  background: var(--main-10);
}
</style>

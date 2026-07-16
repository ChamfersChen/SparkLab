<script setup>
/**
 * 我的流程编辑器（新建/编辑）—— 普通用户创建私有流程。
 *
 * 基于 admin/PlaybookEditor.vue 简化：
 * - 去掉管理员权限检查
 * - 使用 my* API 系列
 * - 导航回 my-playbooks 列表
 */
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ArrowDown,
  ArrowUp,
  ChevronLeft,
  Edit3,
  Eye,
  Plus,
  Save,
  Trash2,
} from 'lucide-vue-next'
import MarkdownIt from 'markdown-it'
import {
  myCreatePlaybook,
  myGetPlaybook,
  myUpdatePlaybook,
} from '@/apis/playbook_api'
import { getTagsGrouped } from '@/apis/tag_api'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const loading = ref(false)
const saving = ref(false)

const form = ref({
  title: '',
  description: '',
  content: '',
  variable_hints: {},
  steps: [],
  tag_ids: [],
  status: 'draft',
})

const tags = ref({ platform: [], content_type: [], industry: [] })
const extractedVars = ref([])
const viewMode = ref('edit')
const stepViewModes = ref({})

const _VAR_REGEX = /\{\{(.*?)\}\}/g
function extractVariables(text) {
  const out = []
  const seen = new Set()
  let m
  while ((m = _VAR_REGEX.exec(text || '')) !== null) {
    const k = m[1].trim()
    if (k === 'prev_output') continue
    if (!seen.has(k)) {
      seen.add(k)
      out.push(k)
    }
  }
  return out
}

function onContentChange() {
  extractedVars.value = extractVariables(form.value.content)
  for (const v of extractedVars.value) {
    if (!(v in form.value.variable_hints)) form.value.variable_hints[v] = ''
  }
  for (const key of Object.keys(form.value.variable_hints)) {
    if (!extractedVars.value.includes(key)) delete form.value.variable_hints[key]
  }
}

watch(() => form.value.content, onContentChange)

const md = new MarkdownIt({ html: false, linkify: true, breaks: true }).use((m) => {
  const defaultOpen =
    m.renderer.rules.link_open ||
    function (tokens, idx, options, _env, self) {
      return self.renderToken(tokens, idx, options)
    }
  m.renderer.rules.link_open = function (tokens, idx, options, env, self) {
    const t = tokens[idx]
    t.attrSet('target', '_blank')
    t.attrSet('rel', 'noopener noreferrer')
    return defaultOpen(tokens, idx, options, env, self)
  }
})

const renderedContent = computed(() => md.render(form.value.content || ''))
const renderedStepContent = (idx) => computed(() =>
  md.render(form.value.steps[idx]?.content || '')
)

function toggleTag(tagId) {
  const idx = form.value.tag_ids.indexOf(tagId)
  if (idx >= 0) form.value.tag_ids.splice(idx, 1)
  else form.value.tag_ids.push(tagId)
}

async function fetchTags() {
  try {
    tags.value = await getTagsGrouped()
  } catch {
    // 标签加载失败不阻塞编辑
  }
}

async function fetchPlaybook() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const p = await myGetPlaybook(route.params.id)
    Object.assign(form.value, {
      title: p.title,
      description: p.description,
      content: p.content || '',
      variable_hints: { ...(p.variable_hints || {}) },
      steps: (p.steps || []).map((s) => ({ ...s })),
      tag_ids: [...(p.tags?.map((x) => x.id) || [])],
      status: p.status,
    })
    onContentChange()
  } catch {
    message.error('获取流程信息失败')
    router.replace({ name: 'my-playbooks' })
  } finally {
    loading.value = false
  }
}

function addStep() {
  form.value.steps.push({
    id: null,
    step_order: form.value.steps.length,
    name: '',
    description: null,
    content: '',
  })
}

function removeStep(idx) {
  form.value.steps.splice(idx, 1)
  reindexSteps()
}

function moveStep(idx, dir) {
  const target = idx + dir
  if (target < 0 || target >= form.value.steps.length) return
  const [item] = form.value.steps.splice(idx, 1)
  form.value.steps.splice(target, 0, item)
  reindexSteps()
}

function reindexSteps() {
  form.value.steps.forEach((s, i) => {
    s.step_order = i
  })
}

async function handleSave() {
  if (!form.value.title.trim()) { message.warning('请输入流程标题'); return }
  if (!form.value.description.trim()) { message.warning('请输入流程描述'); return }
  if (!form.value.content.trim()) { message.warning('请输入流程 Prompt 内容'); return }
  if (form.value.steps.length === 0) { message.warning('请至少添加 1 个步骤'); return }
  for (let i = 0; i < form.value.steps.length; i++) {
    const s = form.value.steps[i]
    if (!s.name.trim()) {
      message.warning(`第 ${i + 1} 步未填写步骤名`)
      return
    }
    if (!s.content.trim()) {
      message.warning(`第 ${i + 1} 步未填写 Prompt 内容`)
      return
    }
  }

  const cleanHints = {}
  for (const [k, v] of Object.entries(form.value.variable_hints || {})) {
    if (v && v.trim()) cleanHints[k] = v.trim()
  }
  const hintsPayload = Object.keys(cleanHints).length ? cleanHints : null
  if (hintsPayload) {
    const missing = extractedVars.value.filter((v) => !cleanHints[v])
    if (missing.length) {
      message.warning(`以下变量未填写提示：${missing.join('、')}`)
      return
    }
  }

  reindexSteps()
  const payload = {
    title: form.value.title,
    description: form.value.description,
    content: form.value.content,
    variable_hints: hintsPayload,
    steps: form.value.steps.map((s) => ({
      step_order: s.step_order,
      name: s.name,
      description: s.description || null,
      content: s.content || '',
    })),
    tag_ids: form.value.tag_ids,
    status: 'draft',
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await myUpdatePlaybook(route.params.id, payload)
      message.success('流程已更新')
      router.push({ name: 'my-playbooks' })
    } else {
      const created = await myCreatePlaybook(payload)
      message.success('流程已创建')
      router.push({ name: 'my-playbook-detail', params: { id: created.id } })
    }
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.push({ name: 'my-playbooks' })
}

onMounted(async () => {
  await fetchTags()
  await fetchPlaybook()
})
</script>

<template>
  <div class="page-bg">
    <div class="page-content">
      <header class="page-bar">
        <button type="button" class="icon-text-btn" @click="goBack">
          <ChevronLeft :size="16" />
          <span>返回</span>
        </button>
        <h1 class="page-bar__title">{{ isEdit ? '编辑流程' : '新建流程' }}</h1>
      </header>

      <a-spin :spinning="loading">
        <div class="editor-grid">
          <!-- 基础信息 -->
          <section class="card-block">
            <h2 class="section-title">基础信息</h2>
            <a-form layout="vertical">
              <a-form-item label="流程标题" required>
                <a-input v-model:value="form.title" placeholder="如「小红书爆款笔记流水线」" maxlength="200" show-count />
              </a-form-item>
              <a-form-item label="一句话描述" required>
                <a-input v-model:value="form.description" placeholder="告诉用户这个流程是做什么的" maxlength="500" show-count />
              </a-form-item>
            </a-form>
          </section>

          <!-- 流程 Prompt 内容 -->
          <section class="card-block">
            <div class="section-header">
              <h2 class="section-title">流程 Prompt（Markdown）</h2>
              <div class="mode-switch">
                <button
                  type="button"
                  class="mode-btn"
                  :class="{ 'mode-btn--active': viewMode === 'edit' }"
                  @click="viewMode = 'edit'"
                >
                  <Edit3 :size="13" />
                  <span>编辑</span>
                </button>
                <button
                  type="button"
                  class="mode-btn"
                  :class="{ 'mode-btn--active': viewMode === 'preview' }"
                  @click="viewMode = 'preview'"
                >
                  <Eye :size="13" />
                  <span>预览</span>
                </button>
              </div>
            </div>
            <p class="section-hint">
              作为「全局上下文」展示在运行页顶部。支持 Markdown 与 <code v-pre>{{变量名}}</code> 占位符。
            </p>

            <div v-show="viewMode === 'edit'" class="content-editor">
              <a-textarea
                v-model:value="form.content"
                :rows="10"
                :auto-size="{ minRows: 10, maxRows: 30 }"
                placeholder="例如：

# 流程说明
本流程将引导你一步步完成一篇小红书爆款笔记的创作。

# 目标
帮助 {{角色}} 在 {{场景}} 中产出可发布的笔记"
              />
            </div>

            <div v-show="viewMode === 'preview'" class="content-preview">
              <div v-if="!form.content" class="preview-empty">尚未输入内容</div>
              <div v-else class="preview-md" v-html="renderedContent"></div>
            </div>

            <div v-if="extractedVars.length" class="extracted-bar">
              <span class="extracted-label">已识别 {{ extractedVars.length }} 个变量：</span>
              <span v-for="v in extractedVars" :key="v" class="var-chip">{{ v }}</span>
            </div>
            <div v-else-if="form.content" class="no-vars-hint">
              当前内容未包含 <code v-pre>{{变量名}}</code>,流程将无变量可填
            </div>
          </section>

          <!-- 变量填写提示 -->
          <section v-if="extractedVars.length" class="card-block">
            <h2 class="section-title">变量填写提示</h2>
            <p class="section-hint">用户在运行页顶部会看到这些提示,按变量顺序填写。</p>
            <div class="hints-grid">
              <div v-for="v in extractedVars" :key="v" class="hint-row">
                <label class="hint-row__name">{{ v }}</label>
                <a-input
                  v-model:value="form.variable_hints[v]"
                  :placeholder="`请输入 ${v} 的填写提示（必填）`"
                />
              </div>
            </div>
          </section>

          <!-- 步骤列表 -->
          <section class="card-block">
            <div class="section-header">
              <h2 class="section-title">步骤列表</h2>
              <span class="section-badge">{{ form.steps.length }} 个步骤</span>
              <button type="button" class="icon-text-btn" @click="addStep">
                <Plus :size="14" />
                <span>添加步骤</span>
              </button>
            </div>
            <p class="section-hint">
              每个步骤自带 Prompt 内容,支持 <code v-pre>{{变量}}</code> 与特殊占位符
              <code v-pre>{{prev_output}}</code>。
            </p>

            <div v-if="!form.steps.length" class="step-empty">
              暂未添加步骤,点击右上角「添加步骤」开始配置
            </div>

            <div v-else class="steps-list">
              <div v-for="(s, idx) in form.steps" :key="idx" class="step-item">
                <div class="step-item__no">{{ idx + 1 }}</div>
                <div class="step-item__body">
                  <a-form layout="vertical">
                    <a-form-item label="步骤名" required>
                      <a-input
                        v-model:value="s.name"
                        placeholder="如「分析产品定位」「提炼卖点」"
                        maxlength="100"
                      />
                    </a-form-item>
                    <a-form-item label="步骤内容（Markdown）" required>
                      <div class="step-mode-bar">
                        <span class="step-mode-hint">支持 <code v-pre>{{变量}}</code> 与 <code v-pre>{{prev_output}}</code></span>
                        <div class="mode-switch">
                          <button
                            type="button"
                            class="mode-btn"
                            :class="{ 'mode-btn--active': (stepViewModes[idx] || 'edit') === 'edit' }"
                            @click="stepViewModes[idx] = 'edit'"
                          >
                            <Edit3 :size="13" />
                            <span>编辑</span>
                          </button>
                          <button
                            type="button"
                            class="mode-btn"
                            :class="{ 'mode-btn--active': stepViewModes[idx] === 'preview' }"
                            @click="stepViewModes[idx] = 'preview'"
                          >
                            <Eye :size="13" />
                            <span>预览</span>
                          </button>
                        </div>
                      </div>
                      <a-textarea
                        v-show="(stepViewModes[idx] || 'edit') === 'edit'"
                        v-model:value="s.content"
                        :rows="6"
                        :auto-size="{ minRows: 6, maxRows: 24 }"
                        placeholder="例如：

请基于以下信息分析产品的目标人群：
- 产品：{{产品名称}}
- 上一步的卖点：{{prev_output}}"
                      />
                      <div
                        v-show="stepViewModes[idx] === 'preview'"
                        class="content-preview step-preview"
                      >
                        <div v-if="!s.content" class="preview-empty">尚未输入内容</div>
                        <div v-else class="preview-md" v-html="renderedStepContent(idx).value"></div>
                      </div>
                    </a-form-item>
                    <a-form-item label="步骤说明（选填）">
                      <a-textarea v-model:value="s.description" :rows="2" maxlength="500" placeholder="给用户看的,这一步要做什么" />
                    </a-form-item>
                  </a-form>
                </div>
                <div class="step-item__actions">
                  <a-tooltip title="上移">
                    <a-button size="small" :disabled="idx === 0" @click="moveStep(idx, -1)">
                      <template #icon><ArrowUp :size="14" /></template>
                    </a-button>
                  </a-tooltip>
                  <a-tooltip title="下移">
                    <a-button size="small" :disabled="idx === form.steps.length - 1" @click="moveStep(idx, 1)">
                      <template #icon><ArrowDown :size="14" /></template>
                    </a-button>
                  </a-tooltip>
                  <a-tooltip title="删除">
                    <a-button size="small" class="action-btn-danger" @click="removeStep(idx)">
                      <template #icon><Trash2 :size="14" /></template>
                    </a-button>
                  </a-tooltip>
                </div>
              </div>
            </div>
          </section>

          <!-- 标签 -->
          <section class="card-block">
            <h2 class="section-title">标签</h2>
            <p class="section-hint">添加标签后,可在列表中按标签筛选。</p>
            <div v-for="(tagList, category) in tags" :key="category" class="filter-group">
              <span class="filter-label">{{ { platform: '平台', content_type: '内容类型', industry: '行业/场景' }[category] }}</span>
              <div class="filter-tags">
                <span
                  v-for="t in tagList"
                  :key="t.id"
                  class="tag-chip"
                  :class="{ 'tag-chip--selected': form.tag_ids.includes(t.id) }"
                  @click="toggleTag(t.id)"
                >{{ t.name }}</span>
                <span v-if="!tagList.length" class="tag-empty">暂无标签</span>
              </div>
            </div>
          </section>

          <!-- 保存 -->
          <div class="submit-bar">
            <a-button @click="goBack">取消</a-button>
            <a-button type="primary" :loading="saving" @click="handleSave">
              <template #icon><Save :size="14" /></template>
              保存
            </a-button>
          </div>
        </div>
      </a-spin>
    </div>
  </div>
</template>

<style scoped>
.editor-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1000px;
  margin: 0 auto;
}

.card-block {
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  padding: 20px 24px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 4px;
}

.section-hint {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin: 0 0 16px;
  line-height: 1.6;
}

.section-hint code {
  background: var(--gray-10);
  border: 1px solid var(--gray-100);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
  color: var(--main-700);
  margin: 0 2px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.section-header .section-title {
  margin: 0;
}

.section-badge {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  background: var(--main-10);
  color: var(--main-700);
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.section-header .icon-text-btn {
  margin-left: auto;
}

.mode-switch {
  display: inline-flex;
  background: var(--gray-10);
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  padding: 2px;
  gap: 2px;
}

.mode-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 24px;
  padding: 0 10px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.mode-btn:hover {
  color: var(--color-text);
}

.mode-btn--active {
  background: var(--gray-0);
  color: var(--main-700);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.content-editor :deep(textarea) {
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.7;
  background: var(--gray-0);
  border-radius: 8px;
}

.content-preview {
  min-height: 240px;
  padding: 20px 24px;
  background: var(--gray-10);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
}

.step-mode-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.step-mode-hint {
  font-size: 11px;
  color: var(--color-text-tertiary);
  line-height: 1.5;
}

.step-mode-hint code {
  background: var(--gray-10);
  padding: 0 4px;
  border-radius: 3px;
  font-size: 11px;
  color: var(--main-700);
  border: 1px solid var(--gray-150);
}

.step-preview {
  min-height: 140px;
  padding: 14px 18px;
}

.preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--color-text-tertiary);
  font-size: 13px;
}

.preview-md {
  font-size: 14px;
  line-height: 1.75;
  color: var(--color-text);
}

.preview-md :deep(h1),
.preview-md :deep(h2),
.preview-md :deep(h3) {
  margin: 16px 0 6px;
  font-weight: 600;
}
.preview-md :deep(h1) { font-size: 18px; }
.preview-md :deep(h2) {
  font-size: 15px;
  padding-left: 10px;
  border-left: 3px solid var(--main-color);
  background: linear-gradient(90deg, var(--main-10) 0%, transparent 70%);
  border-radius: 2px;
}
.preview-md :deep(h3) { font-size: 14px; }
.preview-md :deep(p) { margin: 0 0 10px; }
.preview-md :deep(code) {
  font-family: var(--font-mono);
  font-size: 12.5px;
  padding: 1px 5px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 3px;
  color: var(--main-700);
}
.preview-md :deep(pre) {
  margin: 8px 0 10px;
  padding: 10px 12px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  overflow-x: auto;
}
.preview-md :deep(pre code) {
  padding: 0;
  background: transparent;
  border: none;
}
.preview-md :deep(ul),
.preview-md :deep(ol) { margin: 6px 0 10px; padding-left: 24px; }
.preview-md :deep(li) { margin: 3px 0; }
.preview-md :deep(li::marker) { color: var(--main-color); }

.extracted-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding: 10px 12px;
  background: var(--main-10);
  border: 1px solid var(--main-200);
  border-radius: 6px;
}

.extracted-label {
  font-size: 12px;
  color: var(--main-700);
  font-weight: 500;
  margin-right: 4px;
}

.var-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  background: var(--gray-0);
  border: 1px solid var(--main-color);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  color: var(--main-700);
}

.no-vars-hint {
  margin-top: 12px;
  padding: 10px 12px;
  background: var(--gray-10);
  border: 1px dashed var(--gray-150);
  border-radius: 6px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.no-vars-hint code {
  background: var(--gray-0);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}

.hints-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hint-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 12px;
  align-items: center;
}

.hint-row__name {
  font-size: 13px;
  color: var(--color-text);
  font-weight: 500;
  text-align: right;
  padding: 0 8px;
  background: var(--gray-10);
  border-radius: 4px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
}

.step-empty {
  padding: 32px;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: 13px;
  background: var(--gray-10);
  border: 1px dashed var(--gray-200);
  border-radius: 6px;
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-item {
  display: grid;
  grid-template-columns: 36px 1fr auto;
  gap: 12px;
  align-items: flex-start;
  padding: 12px;
  background: var(--gray-10);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
}

.step-item__no {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--main-color);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  margin-top: 30px;
}

.step-item__body {
  min-width: 0;
}

.step-item__actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 30px;
}

.action-btn-danger {
  color: var(--color-error-600);
}

.action-btn-danger:hover {
  color: var(--color-error-700);
  background: var(--color-error-50);
}

.filter-group {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--gray-100);
}

.filter-group:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.filter-group:first-child {
  padding-top: 0;
}

.filter-label {
  flex-shrink: 0;
  width: 72px;
  font-size: 12px;
  color: var(--color-text-secondary);
  font-weight: 500;
  padding-top: 4px;
}

.filter-tags {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-empty {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.submit-bar {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
}

@media (max-width: 768px) {
  .hint-row {
    grid-template-columns: 1fr;
  }
  .hint-row__name {
    text-align: left;
    justify-content: flex-start;
  }
  .step-item {
    grid-template-columns: 1fr;
  }
  .step-item__no,
  .step-item__actions {
    margin-top: 0;
  }
  .step-item__actions {
    flex-direction: row;
  }
}
</style>

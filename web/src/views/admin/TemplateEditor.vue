<script setup>
/**
 * 模板编辑器（新建/编辑）—— 单 content 字段 + Markdown 编辑 + 实时预览 + 变量自动识别。
 *
 * 不再使用五段式 role/goal/input/output/example。
 * 写作者在一个 Markdown 编辑区自由书写, 使用 {{变量名}} 引用变量。
 * 后端会自动提取变量, 前端在编辑区下方展示「已识别变量」+ 每个变量的填写提示输入框。
 */
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ChevronLeft, Eye, Edit3, Plus, Save } from 'lucide-vue-next'
import MarkdownIt from 'markdown-it'
import { useUserStore } from '@/stores/user'
import { adminCreateTemplate, adminUpdateTemplate, adminGetTemplate } from '@/apis/template_api'
import { getTagsGrouped } from '@/apis/tag_api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

if (!userStore.isAdmin) {
  router.replace({ name: 'dashboard' })
}

const isEdit = computed(() => !!route.params.id)
const loading = ref(false)
const saving = ref(false)

const form = ref({
  title: '',
  description: '',
  content: '',
  variable_hints: {},
  tag_ids: [],
  status: 'draft',
})

// 标签
const tags = ref({ platform: [], content_type: [], industry: [] })

// 编辑区模式：edit（编辑） / preview（预览，纯渲染）
const viewMode = ref('edit')

// 变量提取
const extractedVars = ref([])

const _VAR_REGEX = /\{\{(.*?)\}\}/g
function extractVariables(text) {
  const out = []
  const seen = new Set()
  let m
  while ((m = _VAR_REGEX.exec(text || '')) !== null) {
    const k = m[1].trim()
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

// markdown 渲染
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

function toggleTag(tagId) {
  const idx = form.value.tag_ids.indexOf(tagId)
  if (idx >= 0) form.value.tag_ids.splice(idx, 1)
  else form.value.tag_ids.push(tagId)
}
function isTagSelected(tagId) {
  return form.value.tag_ids.includes(tagId)
}

async function fetchTags() {
  try {
    tags.value = await getTagsGrouped()
  } catch (e) {
    if (e?.response?.status !== 401) {
      message.error('标签加载失败,请先在「标签管理」中确认已配置')
    }
  }
}

async function fetchTemplate() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const t = await adminGetTemplate(route.params.id)
    Object.assign(form.value, {
      title: t.title,
      description: t.description,
      content: t.content || '',
      variable_hints: { ...(t.variable_hints || {}) },
      tag_ids: [...(t.tags?.map((x) => x.id) || [])],
      status: t.status,
    })
    onContentChange()
  } catch {
    message.error('获取模板信息失败')
    router.replace({ name: 'admin-templates' })
  } finally {
    loading.value = false
  }
}

/** 在编辑器光标处插入 {{变量名}} 占位符 */
function insertVariable(name) {
  form.value.content = (form.value.content || '') + `{{${name}}}`
}

async function handleSave(publish = false) {
  if (!form.value.title.trim()) { message.warning('请输入模板标题'); return }
  if (!form.value.description.trim()) { message.warning('请输入模板描述'); return }
  if (!form.value.content.trim()) { message.warning('请输入 Prompt 内容'); return }

  // 清理空 hints
  const cleanHints = {}
  for (const [k, v] of Object.entries(form.value.variable_hints || {})) {
    if (v && v.trim()) cleanHints[k] = v.trim()
  }
  const hintsPayload = Object.keys(cleanHints).length ? cleanHints : null

  // 变量覆盖校验
  const missing = extractedVars.value.filter((v) => !cleanHints[v])
  // variable_hints 设为 dict 时强制覆盖 → 必须全部有 hint
  if (hintsPayload && missing.length) {
    message.warning(`以下变量未填写提示：${missing.join('、')}（在「变量提示」区域补全）`)
    return
  }

  // 状态策略
  let nextStatus
  if (publish) {
    nextStatus = 'published'
  } else if (!isEdit.value) {
    nextStatus = 'draft'
  } else if (form.value.status === 'published') {
    nextStatus = 'published'
  } else {
    nextStatus = 'draft'
  }

  saving.value = true
  const payload = {
    title: form.value.title.trim(),
    description: form.value.description.trim(),
    content: form.value.content,
    variable_hints: hintsPayload,
    tag_ids: [...form.value.tag_ids],
    status: nextStatus,
  }

  try {
    if (isEdit.value) {
      await adminUpdateTemplate(route.params.id, payload)
      message.success('模板已更新')
    } else {
      await adminCreateTemplate(payload)
      message.success('模板已创建')
    }
    router.push({ name: 'admin-templates' })
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const canSaveAsDraft = computed(() => {
  if (!isEdit.value) return true
  return form.value.status !== 'published'
})

onMounted(() => {
  fetchTags()
  fetchTemplate()
})
</script>

<template>
  <div class="page-bg">
    <div class="page-content">
      <header class="page-bar page-bar--editor">
        <div class="page-bar__left-group">
          <button
            type="button"
            class="icon-text-btn"
            @click="router.push({ name: 'admin-templates' })"
          >
            <ChevronLeft :size="16" />
            <span>返回</span>
          </button>
          <h1 class="page-bar__title">{{ isEdit ? '编辑模板' : '新建模板' }}</h1>
        </div>
      </header>

      <a-spin :spinning="loading">
        <div class="editor-layout">
          <!-- 基础信息 -->
          <section class="section">
            <h2 class="section-title">基础信息</h2>
            <a-form layout="vertical">
              <a-form-item label="标题" required>
                <a-input v-model:value="form.title" placeholder="如：小红书种草笔记模板" maxlength="200" show-count />
              </a-form-item>
              <a-form-item label="描述" required>
                <a-textarea
                  v-model:value="form.description"
                  :rows="2"
                  :maxlength="500"
                  show-count
                  placeholder="简要描述模板用途，便于用户在模板库中检索"
                />
              </a-form-item>
            </a-form>
          </section>

          <!-- Prompt 内容（Markdown 编辑 + 预览） -->
          <section class="section">
            <div class="section-header">
              <h2 class="section-title">Prompt 内容（Markdown）</h2>
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
              支持 Markdown。<code>{`{{变量名}}`}</code> 语法会被识别为可填变量,例如：
              <code>{`{{产品名称}}`}</code>。
            </p>

            <div v-show="viewMode === 'edit'" class="content-editor">
              <a-textarea
                v-model:value="form.content"
                :rows="18"
                :auto-size="{ minRows: 18, maxRows: 40 }"
                placeholder="例如：

# 角色
你是一名资深小红书运营专家

# 目标
帮助用户撰写小红书种草笔记

# 输入
产品：{{产品名称}}
核心卖点：{{核心卖点}}
目标人群：{{目标人群}}

# 输出
输出一篇 300 字以内的小红书笔记，含 emoji 与话题标签

# 示例
🌟 这款 XX 真的绝了……"
              />
            </div>

            <div v-show="viewMode === 'preview'" class="content-preview">
              <div v-if="!form.content" class="preview-empty">尚未输入内容</div>
              <div v-else class="preview-md" v-html="renderedContent"></div>
            </div>

            <div v-if="extractedVars.length" class="extracted-bar">
              <span class="extracted-label">已识别 {{ extractedVars.length }} 个变量：</span>
              <span
                v-for="v in extractedVars"
                :key="v"
                class="var-chip"
                @click="insertVariable(v)"
                title="点击追加到内容末尾"
              >{{ v }}</span>
            </div>
            <div v-else-if="form.content" class="no-vars-hint">
              当前内容未包含 <code>{`{{变量名}}`}</code>,提示词将无变量可填
            </div>
          </section>

          <!-- 变量填写提示 -->
          <section v-if="extractedVars.length" class="section">
            <h2 class="section-title">变量填写提示</h2>
            <p class="section-hint">用户在填写页会看到这些提示。请为每个变量写一句填写指导。</p>
            <div class="hints-list">
              <div v-for="v in extractedVars" :key="v" class="hint-item">
                <span class="hint-name">{{ v }}</span>
                <a-input
                  v-model:value="form.variable_hints[v]"
                  :placeholder="`请输入 ${v} 的填写提示（必填）`"
                  size="middle"
                  class="hint-input"
                />
              </div>
            </div>
          </section>

          <!-- 标签 -->
          <section class="section">
            <h2 class="section-title">标签</h2>
            <div v-for="(tagList, category) in tags" :key="category" class="tag-group">
              <span class="tag-group-label">{{ { platform: '平台', content_type: '内容类型', industry: '行业/场景' }[category] }}</span>
              <div class="tag-list">
                <span
                  v-for="t in tagList"
                  :key="t.id"
                  class="tag-chip"
                  :class="{ 'tag-chip--selected': isTagSelected(t.id) }"
                  @click="toggleTag(t.id)"
                >{{ t.name }}</span>
              </div>
            </div>
          </section>

          <!-- 状态 + 提交 -->
          <section class="section actions">
            <a-tooltip
              :title="canSaveAsDraft ? '' : '已发布的模板不能再降级为草稿,如需修改请用「保存并发布」或先去列表下线为「已归档」'"
            >
              <a-button
                type="primary"
                :loading="saving"
                :disabled="!canSaveAsDraft"
                @click="handleSave(false)"
              >
                <template #icon><Save :size="16" /></template>
                保存草稿
              </a-button>
            </a-tooltip>
            <a-button
              type="primary"
              ghost
              :loading="saving"
              @click="handleSave(true)"
            >
              <template #icon><Plus :size="16" /></template>
              保存并发布
            </a-button>
          </section>
        </div>
      </a-spin>
    </div>
  </div>
</template>

<style scoped>
.page-content {
  padding: 24px 0;
}

.page-bar__title {
  font-size: 20px;
}

.page-bar--editor {
  padding: 0 24px;
}

.page-bar--editor .page-bar__title {
  margin-bottom: 0;
}

.page-bar__left-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.editor-layout {
  margin: 8px auto 0;
  max-width: 1000px;
}

.section {
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  padding: 20px 24px;
  margin-bottom: 16px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.section:hover {
  border-color: var(--gray-200);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
  gap: 12px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-header .section-title {
  margin: 0;
}

.section-hint {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin: 0 0 12px;
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

/* 模式切换 */
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

/* 编辑区 */
.content-editor :deep(textarea) {
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.7;
  background: var(--gray-0);
  border-radius: 8px;
}

/* 预览区 */
.content-preview {
  min-height: 360px;
  padding: 20px 24px;
  background: var(--gray-10);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
}

.preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 320px;
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
  margin: 20px 0 8px;
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1.4;
}
.preview-md :deep(h1) { font-size: 20px; }
.preview-md :deep(h2) {
  font-size: 17px;
  padding-left: 10px;
  border-left: 3px solid var(--main-color);
  background: linear-gradient(90deg, var(--main-10) 0%, transparent 70%);
  border-radius: 2px;
}
.preview-md :deep(h3) { font-size: 15px; }
.preview-md :deep(h1:first-child),
.preview-md :deep(h2:first-child),
.preview-md :deep(h3:first-child) { margin-top: 0; }
.preview-md :deep(p) { margin: 0 0 12px; }
.preview-md :deep(p:last-child) { margin-bottom: 0; }
.preview-md :deep(ul),
.preview-md :deep(ol) { margin: 8px 0 12px; padding-left: 24px; }
.preview-md :deep(li) { margin: 4px 0; }
.preview-md :deep(li::marker) { color: var(--main-color); }
.preview-md :deep(code) {
  font-family: var(--font-mono);
  font-size: 12.5px;
  padding: 1px 6px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
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
.preview-md :deep(pre code) { padding: 0; background: transparent; border: none; }
.preview-md :deep(a) {
  color: var(--main-color);
  text-decoration: none;
  border-bottom: 1px dashed currentColor;
}
.preview-md :deep(a:hover) { color: var(--main-700); border-bottom-style: solid; }
.preview-md :deep(blockquote) {
  margin: 8px 0 12px;
  padding: 6px 12px;
  background: var(--gray-0);
  border-left: 3px solid var(--gray-300);
  color: var(--color-text-secondary);
  border-radius: 0 4px 4px 0;
}
.preview-md :deep(strong) { font-weight: 600; }

/* 已识别变量条 */
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
  cursor: pointer;
  transition: all 0.15s ease;
}

.var-chip:hover {
  background: var(--main-color);
  color: #fff;
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

/* 变量提示 */
.hints-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hint-item {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 12px;
  align-items: center;
}

.hint-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
  text-align: right;
  padding: 0 8px;
  background: var(--gray-10);
  border-radius: 4px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
}

.hint-input {
  flex: 1;
}

/* 标签 */
.tag-group {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 12px;
}

.tag-group-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  min-width: 70px;
  line-height: 24px;
  padding-top: 4px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex: 1;
}

.actions {
  display: flex;
  gap: 12px;
}

@media (max-width: 768px) {
  .page-content {
    padding: 16px;
  }
  .section {
    padding: 16px;
    border-radius: 4px;
  }
  .actions {
    flex-direction: column;
    align-items: stretch;
  }
  .actions :deep(.ant-btn) {
    width: 100%;
  }
  .hint-item {
    grid-template-columns: 1fr;
  }
  .hint-name {
    text-align: left;
    justify-content: flex-start;
  }
}
</style>

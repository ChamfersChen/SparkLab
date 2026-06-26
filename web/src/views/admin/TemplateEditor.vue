<script setup>
/**
 * 模板编辑器（新建/编辑）—— 五段式编辑器 + 变量自动识别 + 标签配置。
 */
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ChevronLeft, Plus, Save, FileText } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { adminCreateTemplate, adminUpdateTemplate, adminGetTemplate } from '@/apis/template_api'
import { getTagsGrouped } from '@/apis/tag_api'
import { extractVariables, validateHintsCoverage } from '@/composables/useTemplateVariables'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

if (!userStore.isAdmin) {
  router.replace({ name: 'dashboard' })
}

const isEdit = computed(() => !!route.params.id)
const loading = ref(false)
const saving = ref(false)

// 表单（form.value.tag_ids 作为标签选择的唯一可信源,不再有 selectedTagIds 副本）
const form = ref({
  title: '',
  description: '',
  role: '',
  goal: '',
  input: '',
  output: '',
  example: '',
  variable_hints: {},
  tag_ids: [],
  status: 'draft'
})

// 标签数据
const tags = ref({ platform: [], content_type: [], industry: [] })

// 变量提取
const extractedVars = ref([])

function onInputChange() {
  extractedVars.value = extractVariables(form.value.input)
  // 为新增变量初始化 hints
  for (const v of extractedVars.value) {
    if (!(v in form.value.variable_hints)) {
      form.value.variable_hints[v] = ''
    }
  }
  // 清理已删除变量的 hints
  for (const key of Object.keys(form.value.variable_hints)) {
    if (!extractedVars.value.includes(key)) {
      delete form.value.variable_hints[key]
    }
  }
}

// 监听 input 变更
watch(() => form.value.input, onInputChange)

// 标签选择(单一可信源: form.value.tag_ids)
function toggleTag(tagId) {
  const idx = form.value.tag_ids.indexOf(tagId)
  if (idx >= 0) {
    form.value.tag_ids.splice(idx, 1)
  } else {
    form.value.tag_ids.push(tagId)
  }
}

function isTagSelected(tagId) {
  return form.value.tag_ids.includes(tagId)
}

async function fetchTags() {
  try {
    tags.value = await getTagsGrouped()
  } catch (e) {
    // 标签加载失败要明示,否则编辑器里「标签配置」会空白,用户没法选 tag
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
    // 用 Object.assign 保留 ref 引用,避免断 watch(() => form.value.input)
    Object.assign(form.value, {
      title: t.title,
      description: t.description,
      role: t.role,
      goal: t.goal,
      input: t.input,
      output: t.output,
      example: t.example,
      variable_hints: { ...(t.variable_hints || {}) },
      tag_ids: [...(t.tags?.map((x) => x.id) || [])],
      status: t.status,
    })
    onInputChange()
  } catch {
    message.error('获取模板信息失败')
    router.replace({ name: 'admin-templates' })
  } finally {
    loading.value = false
  }
}

async function handleSave(publish = false) {
  // 基础校验
  if (!form.value.title.trim()) { message.warning('请输入模板标题'); return }
  if (!form.value.description.trim()) { message.warning('请输入模板描述'); return }
  if (!form.value.role.trim() || !form.value.goal.trim() || !form.value.input.trim() || !form.value.output.trim() || !form.value.example.trim()) {
    message.warning('五段式内容均不能为空')
    return
  }

  // 清理空 hints
  const cleanHints = {}
  for (const [k, v] of Object.entries(form.value.variable_hints || {})) {
    if (v && v.trim()) cleanHints[k] = v.trim()
  }
  const hintsPayload = Object.keys(cleanHints).length ? cleanHints : null

  // 变量覆盖校验:Input 段出现的 {{变量}} 必须都在 variable_hints 里
  const missingVars = validateHintsCoverage(form.value.input, hintsPayload)
  if (missingVars.length) {
    message.warning(`Input 段有变量未配置提示：${missingVars.join('、')}`)
    return
  }

  // 状态策略:
  // - "保存并发布": 强制 published
  // - "保存草稿":
  //     - 新建模板: 落 draft
  //     - 编辑现有: draft 保持 draft;archived 恢复到 draft(等价于列表的"恢复"按钮)
  //     - 编辑现有 published: 按钮在 UI 上被禁用,这里兜底强制 published
  let nextStatus
  if (publish) {
    nextStatus = 'published'
  } else if (!isEdit.value) {
    nextStatus = 'draft'
  } else if (form.value.status === 'published') {
    nextStatus = 'published'
  } else {
    // draft 或 archived → 都恢复到 draft
    nextStatus = 'draft'
  }

  saving.value = true
  const payload = {
    title: form.value.title.trim(),
    description: form.value.description.trim(),
    role: form.value.role.trim(),
    goal: form.value.goal.trim(),
    input: form.value.input,
    output: form.value.output.trim(),
    example: form.value.example.trim(),
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
    message.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

/**
 * 「保存草稿」按钮可用性。
 * - 新建模板: 总是可用（自然落 draft）
 * - 编辑已有模板:
 *   - draft: 可用（保持 draft）
 *   - archived: 可用（保存即恢复到 draft，与列表"恢复"按钮语义一致）
 *   - published: 不可用（避免误降级到 draft，如要改内容请用「保存并发布」或先去列表下线）
 */
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
      <!-- 顶部:图标+返回+标题 -->
      <header class="page-bar page-bar--editor">
        <div class="page-bar__left-group">
          <FileText :size="20" class="page-bar__icon" />
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
                <a-input v-model:value="form.title" placeholder="如：小红书种草笔记模板" />
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

          <!-- 五段式编辑器 -->
          <section class="section">
            <h2 class="section-title">Prompt 模板内容（五段式）</h2>
            <a-form layout="vertical">
              <a-form-item label="Role（角色定义）" required>
                <a-textarea v-model:value="form.role" :rows="3" placeholder="如：你是一名资深小红书运营专家" />
              </a-form-item>
              <a-form-item label="Goal（目标说明）" required>
                <a-textarea v-model:value="form.goal" :rows="3" placeholder="如：帮助用户撰写小红书种草笔记" />
              </a-form-item>
              <a-form-item label="Input（变量定义）" required>
                <a-textarea
                  v-model:value="form.input"
                  :rows="4"
                  placeholder="使用 {{变量名}} 语法定义变量，如：产品：{{产品名称}}，核心卖点：{{核心卖点}}"
                />
              </a-form-item>
              <a-form-item label="Output（输出要求）" required>
                <a-textarea v-model:value="form.output" :rows="3" placeholder="如：输出一篇 300 字以内的小红书笔记" />
              </a-form-item>
              <a-form-item label="Example（示例效果）" required>
                <a-textarea v-model:value="form.example" :rows="4" placeholder="填写一段理想输出样例，帮助用户判断模板质量" />
              </a-form-item>
            </a-form>
          </section>

          <!-- 变量填写提示 -->
          <section v-if="extractedVars.length" class="section">
            <h2 class="section-title">
              变量填写提示
              <span class="section-badge">识别到 {{ extractedVars.length }} 个变量</span>
            </h2>
            <div class="hints-list">
              <div v-for="v in extractedVars" :key="v" class="hint-item">
                <span class="hint-name">{{ v }}</span>
                <a-input
                  v-model:value="form.variable_hints[v]"
                  :placeholder="`请输入 ${v} 的填写提示（可选）`"
                  size="small"
                  class="hint-input"
                />
              </div>
            </div>
          </section>
          <div v-else-if="form.input" class="no-vars-hint">
            Input 段中没有找到变量，请使用 <code>{`{{变量名}}`}</code> 语法
          </div>

          <!-- 标签配置 -->
          <section class="section">
            <h2 class="section-title">标签配置</h2>
            <div v-for="(tagList, category) in tags" :key="category" class="tag-group">
              <span class="tag-group-label">{{ { platform: '平台', content_type: '内容类型', industry: '行业/场景' }[category] }}</span>
              <a-tag
                v-for="t in tagList"
                :key="t.id"
                :color="isTagSelected(t.id) ? 'blue' : 'default'"
                class="tag-item"
                @click="toggleTag(t.id)"
              >
                {{ t.name }}
              </a-tag>
            </div>
          </section>

          <!-- 状态 + 提交 -->
          <section class="section actions">
            <a-space>
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
            </a-space>
          </section>
        </div>
      </a-spin>
    </div>
  </div>
</template>

<style scoped>
/* 页面骨架 - 已迁移到全局 .page-bg / .page-content / .page-bar */
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

.page-bar__icon {
  color: var(--main-color);
  flex-shrink: 0;
}

.editor-layout {
  margin: 8px auto 0;
  max-width: 960px;
}

.section {
  background: var(--gray-0);
  border: 1px solid var(--gray-50);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-badge {
  font-size: 11px;
  font-weight: 500;
  color: var(--main-700);
  background: var(--main-10);
  padding: 2px 8px;
  border-radius: 10px;
}

.hints-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hint-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hint-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  min-width: 100px;
}

.hint-input {
  flex: 1;
}

.no-vars-hint {
  background: var(--gray-0);
  border: 1px dashed var(--gray-50);
  border-radius: 8px;
  padding: 16px;
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 16px;
}

.no-vars-hint code {
  background: var(--gray-10);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}

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
}

.tag-item {
  cursor: pointer;
  margin: 2px;
}

.actions {
  display: flex;
  gap: 12px;
}

@media (max-width: 640px) {
  .content {
    padding: 0 16px 48px;
  }
}
</style>

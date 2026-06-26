<script setup>
/**
 * 模板编辑器（新建/编辑）—— 五段式编辑器 + 变量自动识别 + 标签配置。
 */
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { Sparkles, Plus, Save } from 'lucide-vue-next'
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

// 表单
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
const selectedTagIds = ref([])

// 变量提取
const extractedVars = ref([])

function extractVariables(text) {
  const regex = /\{\{(.*?)\}\}/g
  const vars = []
  const seen = new Set()
  let match
  while ((match = regex.exec(text)) !== null) {
    if (!seen.has(match[1])) {
      seen.add(match[1])
      vars.push(match[1])
    }
  }
  return vars
}

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

// 标签选择
function toggleTag(tagId) {
  const idx = selectedTagIds.value.indexOf(tagId)
  if (idx >= 0) {
    selectedTagIds.value.splice(idx, 1)
  } else {
    selectedTagIds.value.push(tagId)
  }
}

function isTagSelected(tagId) {
  return selectedTagIds.value.includes(tagId)
}

async function fetchTags() {
  try {
    const res = await listTags()
    tags.value = res
  } catch {
    // 不阻塞
  }
}

async function fetchTemplate() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const t = await adminGetTemplate(route.params.id)
    form.value = {
      title: t.title,
      description: t.description,
      role: t.role,
      goal: t.goal,
      input: t.input,
      output: t.output,
      example: t.example,
      variable_hints: t.variable_hints || {},
      tag_ids: t.tags?.map(x => x.id) || [],
      status: t.status
    }
    selectedTagIds.value = t.tags?.map(x => x.id) || []
    onInputChange()
  } catch {
    message.error('获取模板信息失败')
    router.replace({ name: 'admin-templates' })
  } finally {
    loading.value = false
  }
}

async function handleSave(publish = false) {
  // 校验
  if (!form.value.title.trim()) { message.warning('请输入模板标题'); return }
  if (!form.value.description.trim()) { message.warning('请输入模板描述'); return }
  if (!form.value.role.trim() || !form.value.goal.trim() || !form.value.input.trim() || !form.value.output.trim() || !form.value.example.trim()) {
    message.warning('五段式内容均不能为空')
    return
  }

  saving.value = true
  const payload = {
    ...form.value,
    tag_ids: selectedTagIds.value,
    status: publish ? 'published' : form.value.status
  }
  // 清理空 hints
  const cleanHints = {}
  for (const [k, v] of Object.entries(payload.variable_hints || {})) {
    if (v && v.trim()) cleanHints[k] = v.trim()
  }
  payload.variable_hints = Object.keys(cleanHints).length ? cleanHints : null

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
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchTags()
  fetchTemplate()
})
</script>

<template>
  <div class="page">
    <div class="content">
      <a-page-header
        :title="isEdit ? '编辑模板' : '新建模板'"
        @back="router.push({ name: 'admin-templates' })"
      />

      <a-spin :spinning="loading">
        <div class="editor-layout">
          <!-- 基础信息 -->
          <section class="section">
            <h2 class="section-title">基础信息</h2>
            <a-form layout="vertical">
              <a-form-item label="标题" required>
                <a-input v-model:value="form.title" placeholder="如：小红书种草笔记模板" />
              </a-form-item>
              <a-form-item label="一句话描述" required>
                <a-input v-model:value="form.description" placeholder="100 字以内描述模板用途" :maxlength="100" show-count />
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
              <a-button
                type="primary"
                :loading="saving"
                @click="handleSave(false)"
              >
                <template #icon><Save :size="16" /></template>
                保存草稿
              </a-button>
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
.page {
  min-height: 100vh;
  background: var(--gray-10);
}

.content {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 32px 64px;
}

.editor-layout {
  margin-top: 8px;
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

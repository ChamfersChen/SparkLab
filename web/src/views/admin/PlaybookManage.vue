<script setup>
import { ref, onMounted, computed, h } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { BookOpen, Edit2, Eye, FileText, Plus, Trash2, Filter, X } from 'lucide-vue-next'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'
import {
  adminListPlaybooks,
  adminChangeStatus,
  adminHardDeletePlaybook,
} from '@/apis/playbook_api'
import { getTagsGrouped } from '@/apis/tag_api'

const router = useRouter()
const userStore = useUserStore()

if (!userStore.isAdmin) {
  router.replace({ name: 'dashboard' })
}

const isSuperAdmin = computed(() => userStore.isSuperAdmin)

const loading = ref(false)
const items = ref([])
const total = ref(0)
const search = ref('')
const statusFilter = ref(undefined)
const page = ref(1)
const pageSize = ref(20)

// 标签筛选
const tags = ref({ platform: [], content_type: [], industry: [] })
const selectedTagIds = ref([])
const showFilter = ref(false)

async function fetchTags() {
  try {
    tags.value = await getTagsGrouped()
  } catch {
    // 标签加载失败不阻塞
  }
}

function toggleTag(tagId) {
  const idx = selectedTagIds.value.indexOf(tagId)
  if (idx >= 0) {
    selectedTagIds.value.splice(idx, 1)
  } else {
    selectedTagIds.value.push(tagId)
  }
  page.value = 1
  fetchData()
}

function clearAllFilters() {
  search.value = ''
  statusFilter.value = undefined
  selectedTagIds.value = []
  page.value = 1
  fetchData()
}

function setStatus(v) {
  if (statusFilter.value === v) return
  statusFilter.value = v
  page.value = 1
  fetchData()
}

const hasActiveFilter = computed(
  () =>
    search.value.trim().length > 0 ||
    !!statusFilter.value ||
    selectedTagIds.value.length > 0
)

function buildTagIdsParam() {
  if (!selectedTagIds.value.length) return ''
  const groups = []
  for (const tagList of Object.values(tags.value)) {
    const ids = tagList
      .filter((t) => selectedTagIds.value.includes(t.id))
      .map((t) => t.id)
    if (ids.length) groups.push(ids.join(','))
  }
  return groups.join(';')
}

async function fetchData() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value.trim()) params.search = search.value.trim()
    if (statusFilter.value) params.status = statusFilter.value
    const tagIdsParam = buildTagIdsParam()
    if (tagIdsParam) params.tag_ids = tagIdsParam
    const res = await adminListPlaybooks(params)
    items.value = res.items
    total.value = res.total
  } catch (e) {
    if (e.response?.status !== 401) {
      message.error('获取工作流列表失败')
    }
  } finally {
    loading.value = false
  }
}

function goCreate() {
  router.push({ name: 'admin-playbook-create' })
}

function goEdit(id) {
  router.push({ name: 'admin-playbook-edit', params: { id } })
}

function goPreview(id) {
  router.push({ name: 'playbook-run', params: { id } })
}

async function changeStatus(id, status) {
  try {
    await adminChangeStatus(id, status)
    message.success(
      `工作流已${status === 'published' ? '发布' : status === 'archived' ? '下线' : '设为草稿'}`,
    )
    if (items.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    await fetchData()
  } catch (e) {
    message.error('操作失败')
  }
}

function handleHardDelete(record) {
  let typedTitle = ''
  Modal.confirm({
    title: `删除工作流「${record.title}」?`,
    content: () =>
      h('div', null, [
        h(
          'p',
          { style: 'margin-bottom: 8px; color: var(--gray-700);' },
          '此操作将从数据库中彻底删除该工作流及其步骤关联，不可恢复。用户端将立即无法访问。',
        ),
        h('p', { style: 'margin-bottom: 4px;' }, '请输入工作流标题以确认：'),
        h('input', {
          value: '',
          placeholder: record.title,
          style:
            'width: 100%; padding: 4px 8px; border: 1px solid var(--gray-200); border-radius: 4px;',
          onInput: (e) => {
            typedTitle = e.target.value
          },
        }),
      ]),
    okText: '确认删除',
    cancelText: '取消',
    okType: 'danger',
    async onOk() {
      if (typedTitle.trim() !== record.title) {
        message.error('输入的标题不匹配,已取消删除')
        return Promise.reject(new Error('title mismatch'))
      }
      try {
        await adminHardDeletePlaybook(record.id)
        message.success('工作流已删除')
        if (items.value.length === 1 && page.value > 1) {
          page.value -= 1
        }
        await fetchData()
      } catch (e) {
        message.error(e?.message || '删除失败')
        return Promise.reject(e)
      }
    },
  })
}

const STATUS_MAP = {
  draft: { text: '草稿', cls: 'status-tag--draft' },
  published: { text: '已发布', cls: 'status-tag--published' },
  archived: { text: '已归档', cls: 'status-tag--archived' },
}

function formatDateTime(v) {
  if (!v) return ''
  const d = dayjs(v)
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm') : v
}

const tableLocale = computed(() => ({
  emptyText: h('div', { class: 'empty-state' }, [
    h('div', { class: 'empty-state__icon' }, [h(BookOpen, { size: 28 })]),
    h(
      'h3',
      { class: 'empty-state__title' },
      search.value || statusFilter.value || selectedTagIds.value.length
        ? '没有匹配的工作流'
        : '暂无工作流',
    ),
    h(
      'p',
      { class: 'empty-state__desc' },
      search.value || statusFilter.value || selectedTagIds.value.length
        ? '试试调整搜索或筛选条件'
        : '点击右上角「新建工作流」开始创建',
    ),
  ]),
}))

onMounted(() => {
  fetchTags()
  fetchData()
})
</script>

<template>
  <div class="page-bg">
    <div class="page-content">
      <header class="page-bar">
        <div class="page-bar__title-area">
          <h1 class="page-bar__title">工作流管理</h1>
        </div>
        <div class="page-bar__actions">
          <a-button type="primary" @click="goCreate">
            <template #icon><Plus :size="16" /></template>
            新建工作流
          </a-button>
        </div>
      </header>

      <div class="toolbar-card toolbar-card--compact">
        <a-input-search
          v-model:value="search"
          placeholder="搜索工作流…"
          allow-clear
          size="small"
          class="search-input"
          @search="() => { page = 1; fetchData() }"
        />
        <div class="status-pills">
          <span
            class="status-pill"
            :class="{ 'status-pill--active': !statusFilter }"
            @click="setStatus(undefined)"
          >全部</span>
          <span
            class="status-pill"
            :class="{ 'status-pill--active': statusFilter === 'draft' }"
            @click="setStatus('draft')"
          >草稿</span>
          <span
            class="status-pill"
            :class="{ 'status-pill--active': statusFilter === 'published' }"
            @click="setStatus('published')"
          >已发布</span>
          <span
            class="status-pill"
            :class="{ 'status-pill--active': statusFilter === 'archived' }"
            @click="setStatus('archived')"
          >已归档</span>
        </div>
        <button
          type="button"
          class="toolbar-btn"
          :class="{ 'toolbar-btn--active': showFilter || selectedTagIds.length }"
          @click="showFilter = !showFilter"
        >
          <Filter :size="14" />
          <span>标签</span>
          <span v-if="selectedTagIds.length" class="toolbar-badge">{{ selectedTagIds.length }}</span>
        </button>
        <button
          v-if="hasActiveFilter"
          type="button"
          class="toolbar-btn toolbar-btn--ghost"
          @click="clearAllFilters"
        >
          <X :size="12" />
          <span>清除</span>
        </button>
      </div>

      <div v-if="showFilter" class="filter-panel filter-panel--compact">
        <div v-for="(tagList, category) in tags" :key="category" class="filter-group">
          <span class="filter-label">{{ { platform: '平台', content_type: '内容类型', industry: '行业/场景' }[category] }}</span>
          <div class="filter-tags">
            <span
              v-for="t in tagList"
              :key="t.id"
              class="tag-chip"
              :class="{ 'tag-chip--selected': selectedTagIds.includes(t.id) }"
              @click="toggleTag(t.id)"
            >{{ t.name }}</span>
          </div>
        </div>
      </div>

      <div class="table-theme table-scroll">
        <a-table
          :data-source="items"
          :columns="[
            { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true, width: 260 },
            { title: '步骤', key: 'step_count', width: 80, align: 'center' },
            { title: '标签', key: 'tags', width: 320 },
            { title: '状态', key: 'status', width: 90, align: 'center' },
            { title: '使用次数', dataIndex: 'use_count', key: 'use_count', width: 90, align: 'center' },
            { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 160 },
            { title: '操作', key: 'action', width: 260, align: 'right', fixed: 'right' }
          ]"
          :scroll="{ x: 1200 }"
          :pagination="false"
          :loading="loading"
          row-key="id"
          size="middle"
          :locale="tableLocale"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'step_count'">
              <span class="step-count">
                <FileText :size="12" />
                {{ record.steps?.length || 0 }} 步
              </span>
            </template>
            <template v-if="column.key === 'tags'">
              <div class="tag-cell">
                <span v-for="t in record.tags" :key="t.id" class="card-tag">{{ t.name }}</span>
                <span v-if="!record.tags?.length" class="tag-empty">—</span>
              </div>
            </template>
            <template v-if="column.key === 'status'">
              <span class="status-tag" :class="STATUS_MAP[record.status]?.cls">
                {{ STATUS_MAP[record.status]?.text || record.status }}
              </span>
            </template>
            <template v-if="column.key === 'updated_at'">
              {{ formatDateTime(record.updated_at) }}
            </template>
            <template v-if="column.key === 'action'">
              <div class="action-group">
                <a-button size="small" class="action-btn-primary" @click="goEdit(record.id)">
                  <template #icon><Edit2 :size="14" /></template>
                  <span>编辑</span>
                </a-button>
                <a-button
                  v-if="record.status === 'draft'"
                  size="small"
                  class="action-btn-primary"
                  @click="changeStatus(record.id, 'published')"
                >
                  <span>发布</span>
                </a-button>
                <a-button
                  v-if="record.status === 'published'"
                  size="small"
                  class="action-btn-warn"
                  @click="changeStatus(record.id, 'archived')"
                >
                  下线
                </a-button>
                <a-button
                  v-if="record.status === 'archived'"
                  size="small"
                  @click="changeStatus(record.id, 'draft')"
                >
                  恢复
                </a-button>
                <a-tooltip title="预览">
                  <a-button size="small" class="action-icon" @click="goPreview(record.id)">
                    <Eye :size="14" />
                  </a-button>
                </a-tooltip>
                <a-tooltip
                  v-if="isSuperAdmin"
                  :title="record.status === 'published'
                    ? '已发布的工作流不能删除,请先下线为「已归档」'
                    : '物理删除：从数据库移除记录，不可恢复'"
                >
                  <a-button
                    size="small"
                    class="action-btn-danger"
                    :disabled="record.status === 'published'"
                    @click="handleHardDelete(record)"
                  >
                    <Trash2 :size="14" />
                  </a-button>
                </a-tooltip>
              </div>
            </template>
          </template>
        </a-table>
      </div>

      <div v-if="total > pageSize" class="pagination-wrap">
        <a-pagination
          v-model:current="page"
          v-model:page-size="pageSize"
          :total="total"
          show-size-changer
          @change="fetchData"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 复用 TemplateManage.vue 的 toolbar / 表格 / 状态 pill 样式 */

.search-input {
  flex: 1;
  max-width: 320px;
  min-width: 180px;
}

.step-count {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.tag-cell {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 6px;
}

.tag-empty {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.action-group {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: nowrap;
  gap: 4px;
}

@media (max-width: 768px) {
  .page-content {
    padding: 16px;
  }

  .toolbar-card {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-card .ant-select,
  .toolbar-card .ant-input-search {
    width: 100% !important;
  }
}
</style>

<script setup>
import { ref, onMounted, computed, h } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { Plus, Edit2, Check, Eye, Trash2, FileText, Filter, X } from 'lucide-vue-next'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'
import { adminListTemplates, adminChangeStatus, adminHardDeleteTemplate } from '@/apis/template_api'
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

/** 点击状态 pill: 同值不重复请求 */
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

/** 把已选 tag 按 category 分组,拼成后端约定的 "1,2;3" 字符串。
 *  组间 AND、组内 OR;空字符串视为未筛选。 */
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
    const res = await adminListTemplates(params)
    items.value = res.items
    total.value = res.total
  } catch (e) {
    if (e.response?.status !== 401) {
      message.error('获取模板列表失败')
    }
  } finally {
    loading.value = false
  }
}

function goCreate() {
  router.push({ name: 'admin-template-create' })
}

function goEdit(id) {
  router.push({ name: 'admin-template-edit', params: { id } })
}

function goPreview(id) {
  router.push({ name: 'template-detail', params: { id } })
}

async function changeStatus(id, status) {
  try {
    await adminChangeStatus(id, status)
    message.success(`模板已${status === 'published' ? '发布' : status === 'archived' ? '下线' : '设为草稿'}`)
    // 当前页被清空时回退一页，避免空列表
    if (items.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    await fetchData()
  } catch (e) {
    message.error('操作失败')
  }
}

/**
 * 物理删除模板（仅超管）。
 * 二次确认：用户必须输入模板标题才能点确认。
 */
function handleHardDelete(record) {
  let typedTitle = ''
  Modal.confirm({
    title: `删除模板「${record.title}」?`,
    content: () =>
      h('div', null, [
        h(
          'p',
          { style: 'margin-bottom: 8px; color: var(--gray-700);' },
          '此操作将从数据库中彻底删除该模板及其标签关联，不可恢复。普通用户端将立即无法访问。',
        ),
        h('p', { style: 'margin-bottom: 4px;' }, '请输入模板标题以确认：'),
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
        await adminHardDeleteTemplate(record.id)
        message.success('模板已删除')
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

/** 后端返回的 ISO 时间 → YYYY-MM-DD HH:mm；空值原样返回 */
function formatDateTime(v) {
  if (!v) return ''
  const d = dayjs(v)
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm') : v
}

const tableLocale = computed(() => ({
  emptyText: h('div', { class: 'empty-state' }, [
    h('div', { class: 'empty-state__icon' }, [h(FileText, { size: 28 })]),
    h('h3', { class: 'empty-state__title' }, search.value || statusFilter.value ? '没有匹配的模板' : '暂无模板'),
    h('p', { class: 'empty-state__desc' }, search.value || statusFilter.value ? '试试调整搜索或筛选条件' : '点击右上角「新建模板」开始创建'),
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
      <!-- 顶部:主标题 + 操作区(无返回) -->
      <header class="page-bar">
        <div class="page-bar__title-area">
          <h1 class="page-bar__title">模板管理</h1>
        </div>
        <div class="page-bar__actions">
          <a-button type="primary" @click="goCreate">
            <template #icon><Plus :size="16" /></template>
            新建模板
          </a-button>
        </div>
      </header>

      <!-- 紧凑工具栏:搜索 + 状态 + 标签筛选触发 -->
      <div class="toolbar-card toolbar-card--compact">
        <a-input-search
          v-model:value="search"
          placeholder="搜索模板…"
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

      <!-- 标签筛选面板 -->
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

      <!-- 表格主题化 + 移动端横向滚动 -->
      <div class="table-theme table-scroll">
        <a-table
          :data-source="items"
          :columns="[
            { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true, width: 260 },
            { title: '标签', key: 'tags', width: 320 },
            { title: '状态', key: 'status', width: 90, align: 'center' },
            { title: '使用次数', dataIndex: 'use_count', key: 'use_count', width: 90, align: 'center' },
            { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 160 },
            { title: '操作', key: 'action', width: 260, align: 'right', fixed: 'right' }
          ]"
          :scroll="{ x: 1180 }"
          :pagination="false"
          :loading="loading"
          row-key="id"
          size="middle"
          :locale="tableLocale"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'tags'">
              <div class="tag-cell">
                <span v-for="t in record.tags" :key="t.id" class="card-tag">{{ t.name }}</span>
                <span v-if="!record.tags?.length" class="tag-empty">—</span>
              </div>
            </template>
            <template v-if="column.key === 'status'">
              <span
                class="status-tag"
                :class="STATUS_MAP[record.status]?.cls"
              >
                {{ STATUS_MAP[record.status]?.text || record.status }}
              </span>
            </template>
            <template v-if="column.key === 'updated_at'">
              {{ formatDateTime(record.updated_at) }}
            </template>
            <template v-if="column.key === 'action'">
              <div class="action-group">
                <!-- 主操作(图标+文字) -->
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
                  <!-- <template #icon><Check :size="14" /></template> -->
                  <!-- <span>发布</span> -->
                  发布
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
                <!-- 次操作(仅图标) -->
                <a-tooltip title="预览">
                  <a-button size="small" class="action-icon" @click="goPreview(record.id)">
                    <Eye :size="14" />
                  </a-button>
                </a-tooltip>
                <!-- 危险操作(分隔线 + danger) -->
                <a-tooltip
                  v-if="isSuperAdmin"
                  :title="record.status === 'published'
                    ? '已发布的模板不能删除,请先下线为「已归档」'
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
/* 紧凑工具栏 */
.toolbar-card--compact {
  padding: 8px 12px;
  gap: 8px;
  border-radius: 8px;
}

/* 普通 button: 直接给最外层圆角 + 28px 高 */
.toolbar-card--compact :deep(.ant-btn-sm:not(.ant-input-search-button)) {
  height: 28px;
  border-radius: 6px;
}

/* a-input-search 的 DOM 是 group-wrapper > [affix-wrapper, group-addon>button]:
 * 只给最外层设圆角,内部 affix-wrapper / input / button 保持矩形,
 * 避免内外圆角不一致或底部边框被相邻 addon 截断。 */
.toolbar-card--compact :deep(.ant-input-search) {
  border-radius: 6px;
  overflow: hidden;
}

.toolbar-card--compact :deep(.ant-input-search .ant-input-affix-wrapper),
.toolbar-card--compact :deep(.ant-input-search .ant-input-search-button) {
  height: 28px;
  border-radius: 0;
}

.search-input {
  flex: 1;
  max-width: 320px;
  min-width: 180px;
}

/* 状态 pills:紧凑、高度 26px、和 toolbar 控件视觉对齐 */
.status-pills {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px;
  background: var(--gray-25);
  border-radius: 6px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  font-size: 12px;
  color: var(--color-text-secondary);
  border-radius: 4px;
  cursor: pointer;
  user-select: none;
  transition: all 0.15s ease;
}

.status-pill:hover {
  color: var(--color-text);
}

.status-pill--active {
  background: var(--gray-0);
  color: var(--main-700);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 10px;
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  color: var(--color-text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.toolbar-btn:hover {
  color: var(--color-text);
  border-color: var(--gray-300);
}

.toolbar-btn--active {
  color: var(--main-700);
  border-color: var(--main-color);
  background: var(--main-10);
}

.toolbar-btn--ghost {
  border-color: transparent;
  background: transparent;
  margin-left: auto;
}

.toolbar-btn--ghost:hover {
  background: var(--gray-25);
  border-color: transparent;
}

.toolbar-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  margin-left: 2px;
  background: var(--main-color);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  border-radius: 999px;
  line-height: 1;
}

.filter-panel {
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  padding: 12px 16px;
  margin-top: -8px;
  margin-bottom: 12px;
}

.filter-panel--compact .filter-group {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--gray-100);
}

.filter-panel--compact .filter-group:first-child {
  padding-top: 0;
}

.filter-panel--compact .filter-group:last-child {
  padding-bottom: 0;
  border-bottom: none;
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

.filter-panel--compact .tag-chip {
  padding: 2px 10px;
  font-size: 12px;
}

/* 表格外层横向滚动(移动端必备) */
.table-scroll {
  overflow-x: auto;
}

.action-group {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: nowrap;
  gap: 4px;
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

.action-btn-primary {
  color: var(--main-700);
}

.action-btn-primary:hover {
  color: var(--main-color);
  background: var(--main-10);
}

.action-btn-warn {
  color: var(--color-warning-700);
}

.action-btn-warn:hover {
  color: var(--color-warning-900);
  background: var(--color-warning-50);
}

.action-btn-danger {
  color: var(--color-error-600);
  margin-left: 8px;
  padding-left: 8px;
  border-left: 1px solid var(--gray-150);
}

.action-btn-danger:hover {
  color: var(--color-error-700);
  background: var(--color-error-50);
}

.action-btn-danger:disabled {
  border-left-color: var(--gray-100);
}

.action-icon {
  color: var(--color-text-secondary);
}

.action-icon:hover {
  color: var(--main-color);
  background: var(--main-10);
}

.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

@media (max-width: 768px) {
  .status-pills {
    margin-left: 0;
    width: 100%;
    overflow-x: auto;
  }
}
</style>

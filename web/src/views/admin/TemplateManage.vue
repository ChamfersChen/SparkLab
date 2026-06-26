<script setup>
import { ref, onMounted, computed, h } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { Plus, Edit2, Check, Eye, Trash2, FileText } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { adminListTemplates, adminChangeStatus, adminHardDeleteTemplate } from '@/apis/template_api'

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

async function fetchData() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value.trim()) params.search = search.value.trim()
    if (statusFilter.value) params.status = statusFilter.value
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

const tableLocale = computed(() => ({
  emptyText: h('div', { class: 'empty-state' }, [
    h('div', { class: 'empty-state__icon' }, [h(FileText, { size: 28 })]),
    h('h3', { class: 'empty-state__title' }, search.value || statusFilter.value ? '没有匹配的模板' : '暂无模板'),
    h('p', { class: 'empty-state__desc' }, search.value || statusFilter.value ? '试试调整搜索或筛选条件' : '点击右上角「新建模板」开始创建'),
  ]),
}))

onMounted(fetchData)
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

      <!-- 工具栏卡片:搜索 + 状态 pill 筛选 -->
      <div class="toolbar-card">
        <a-input-search
          v-model:value="search"
          placeholder="搜索模板…"
          allow-clear
          class="search-input"
          @search="fetchData"
        />
        <div class="status-pills">
          <span
            class="tag-chip"
            :class="{ 'tag-chip--selected': !statusFilter }"
            @click="statusFilter = undefined; fetchData()"
          >
            全部
          </span>
          <span
            class="tag-chip"
            :class="{ 'tag-chip--selected': statusFilter === 'draft' }"
            @click="statusFilter = 'draft'; fetchData()"
          >
            草稿
          </span>
          <span
            class="tag-chip"
            :class="{ 'tag-chip--selected': statusFilter === 'published' }"
            @click="statusFilter = 'published'; fetchData()"
          >
            已发布
          </span>
          <span
            class="tag-chip"
            :class="{ 'tag-chip--selected': statusFilter === 'archived' }"
            @click="statusFilter = 'archived'; fetchData()"
          >
            已归档
          </span>
        </div>
      </div>

      <!-- 表格主题化 + 移动端横向滚动 -->
      <div class="table-theme table-scroll">
        <a-table
          :data-source="items"
          :columns="[
            { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
            { title: '标签', key: 'tags', width: 180 },
            { title: '状态', key: 'status', width: 100 },
            { title: '使用次数', dataIndex: 'use_count', key: 'use_count', width: 90, align: 'center' },
            { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 170 },
            { title: '操作', key: 'action', width: 320 }
          ]"
          :pagination="false"
          :loading="loading"
          row-key="id"
          size="middle"
          :locale="tableLocale"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'tags'">
              <span v-for="t in record.tags?.slice(0, 2)" :key="t.id" class="card-tag">{{ t.name }}</span>
              <span v-if="record.tags?.length > 2" class="tag-more">…</span>
            </template>
            <template v-if="column.key === 'status'">
              <span
                class="status-tag"
                :class="STATUS_MAP[record.status]?.cls"
              >
                {{ STATUS_MAP[record.status]?.text || record.status }}
              </span>
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
                  <template #icon><Check :size="14" /></template>
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
/* 页面顶部 - 已迁移到全局 .page-bar / .page-bar__title / .page-bar__actions */

.search-input {
  flex: 1;
  max-width: 360px;
}

.status-pills {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
}

/* 表格外层横向滚动(移动端必备) */
.table-scroll {
  overflow-x: auto;
}

.action-group {
  display: flex;
  align-items: center;
  gap: 4px;
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

<script setup>
/**
 * 激活码管理(超管)。
 *
 * 视觉与 5 个 Template 视图对齐(背景 / page-bar / 状态标签 / 工具栏卡片 / 表格主题 / 空态 / 响应式)。
 * 保留独有的左侧导航(超管多模块入口),与 Template 视图(单页面)区分。
 */
import { ref, onMounted, computed, h } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { Plus, Copy, Check, Power, PowerOff, Link, Edit2, Inbox, Trash2 } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { listActivationCodes, generateCodes, toggleCodeStatus, updateCodeNote, deleteCode } from '@/apis/activation_code_api'

const router = useRouter()
const userStore = useUserStore()

if (!userStore.isSuperAdmin) {
  router.replace({ name: 'dashboard' })
}

const items = ref([])
const total = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const statusFilter = ref(undefined)
const search = ref('')

// Generate dialog
const showGenerate = ref(false)
const generateCount = ref(10)
const generateNote = ref('')
const generating = ref(false)

// Copy tracking
const copiedId = ref(null)

// Inline note editing
const editingNoteId = ref(null)
const editingNoteValue = ref('')
const editingNoteOriginal = ref('')
const noteSaving = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (statusFilter.value) params.status = statusFilter.value
    if (search.value.trim()) params.search = search.value.trim()

    const res = await listActivationCodes(params)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function handleGenerate() {
  if (generateCount.value < 1 || generateCount.value > 100) {
    message.warning('数量范围 1～100')
    return
  }
  generating.value = true
  try {
    const res = await generateCodes({
      count: generateCount.value,
      note: generateNote.value || null,
    })
    message.success(`成功生成 ${res.items.length} 个激活码`)
    showGenerate.value = false
    generateCount.value = 10
    generateNote.value = ''
    currentPage.value = 1
    await fetchData()
  } finally {
    generating.value = false
  }
}

async function handleToggle(id) {
  try {
    await toggleCodeStatus(id)
    await fetchData()
  } catch {
    // error handled by base.js
  }
}

function handleHardDelete(record) {
  Modal.confirm({
    title: `删除激活码「${record.code}」?`,
    content: () =>
      h('div', null, [
        h(
          'p',
          { style: 'margin-bottom: 8px; color: var(--gray-700);' },
          '此操作将从数据库中彻底删除该激活码，不可恢复。',
        ),
        h('p', { style: 'color: var(--gray-500); font-size: 13px;' }, '仅「未使用」和「已禁用」状态的激活码可被删除。'),
      ]),
    okText: '确认删除',
    cancelText: '取消',
    okType: 'danger',
    async onOk() {
      try {
        await deleteCode(record.id)
        message.success('激活码已删除')
        if (items.value.length === 1 && currentPage.value > 1) {
          currentPage.value -= 1
        }
        await fetchData()
      } catch (e) {
        message.error(e?.response?.data?.detail || '删除失败')
        return Promise.reject(e)
      }
    },
  })
}

function handleStartEditNote(record) {
  editingNoteId.value = record.id
  editingNoteValue.value = record.note || ''
  editingNoteOriginal.value = record.note || ''
}

async function handleSaveNote(id) {
  if (noteSaving.value) return
  noteSaving.value = true
  const newNote = editingNoteValue.value || null
  const oldNote = editingNoteOriginal.value || null
  if (newNote === oldNote) {
    editingNoteId.value = null
    noteSaving.value = false
    return
  }
  try {
    await updateCodeNote(id, { note: newNote })
    message.success('备注已更新')
    editingNoteId.value = null
    await fetchData()
  } catch {
    // error handled by base.js
  } finally {
    noteSaving.value = false
  }
}

function copyCode(code, id) {
  navigator.clipboard.writeText(code)
  copiedId.value = id
  message.success('已复制')
  setTimeout(() => { copiedId.value = null }, 2000)
}

function copyLink(code, id) {
  const link = `${window.location.origin}/activate?code=${code}`
  navigator.clipboard.writeText(link)
  copiedId.value = id
  message.success('激活链接已复制')
  setTimeout(() => { copiedId.value = null }, 2000)
}

const STATUS_LABEL = {
  unused: { text: '未使用', cls: 'status-tag--unused' },
  used: { text: '已使用', cls: 'status-tag--used' },
  disabled: { text: '已禁用', cls: 'status-tag--disabled' },
}

function handleSearch() {
  currentPage.value = 1
  fetchData()
}

function handleTableChange(pagination) {
  currentPage.value = pagination.current
  pageSize.value = pagination.pageSize
  fetchData()
}

const tableLocale = computed(() => ({
  emptyText: h('div', { class: 'empty-state' }, [
    h('div', { class: 'empty-state__icon' }, [h(Inbox, { size: 28 })]),
    h('h3', { class: 'empty-state__title' }, search.value || statusFilter.value ? '没有匹配的激活码' : '暂无激活码'),
    h('p', { class: 'empty-state__desc' }, search.value || statusFilter.value ? '试试调整搜索或筛选条件' : '点击右上角「生成激活码」开始创建'),
  ]),
}))

onMounted(fetchData)
</script>

<template>
  <div class="page-bg">
    <main class="page-content">
      <!-- 顶部:主标题 + 操作区(与其他 5 页统一 .page-bar) -->
      <header class="page-bar">
        <div class="page-bar__title-area">
          <h1 class="page-bar__title">激活码管理</h1>
        </div>
        <div class="page-bar__actions">
          <a-button type="primary" @click="showGenerate = true">
            <template #icon><Plus :size="16" /></template>
            生成激活码
          </a-button>
        </div>
      </header>

      <!-- 工具栏卡片(与其他 5 页统一) -->
      <div class="toolbar-card">
        <a-select
          v-model:value="statusFilter"
          placeholder="所有状态"
          allow-clear
          style="width: 160px"
          @change="handleSearch"
        >
          <a-select-option value="unused">未使用</a-select-option>
          <a-select-option value="used">已使用</a-select-option>
          <a-select-option value="disabled">已禁用</a-select-option>
        </a-select>

        <a-input-search
          v-model:value="search"
          placeholder="搜索激活码/备注/用户名"
          style="width: 320px"
          @search="handleSearch"
        />
      </div>

      <!-- 表格主题化(全局 .table-theme 主题,移动端 .table-scroll 横向滚动) -->
      <div class="table-theme table-scroll">
        <a-table
          :data-source="items"
          :columns="[
            { title: '激活码', dataIndex: 'code', width: 180 },
            { title: '状态', dataIndex: 'status', width: 100 },
            { title: '备注', dataIndex: 'note', width: 240 },
            { title: '创建者', dataIndex: 'creator', width: 120 },
            { title: '使用者', dataIndex: 'user', width: 120 },
            { title: '使用时间', dataIndex: 'used_at', width: 170 },
            { title: '创建时间', dataIndex: 'created_at', width: 170 },
            { title: '操作', key: 'actions', width: 180, fixed: 'right' },
          ]"
          :pagination="{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
          }"
          :loading="loading"
          :locale="tableLocale"
          row-key="id"
          @change="handleTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'code'">
              <code class="code-value">{{ record.code }}</code>
            </template>

            <template v-if="column.dataIndex === 'status'">
              <span
                class="status-tag"
                :class="STATUS_LABEL[record.status]?.cls"
              >
                {{ STATUS_LABEL[record.status]?.text || record.status }}
              </span>
            </template>

            <template v-if="column.dataIndex === 'note'">
              <template v-if="editingNoteId === record.id">
                <a-input
                  v-model:value="editingNoteValue"
                  size="small"
                  style="width: 200px"
                  @press-enter="handleSaveNote(record.id)"
                  @blur="handleSaveNote(record.id)"
                  autofocus
                />
              </template>
              <template v-else>
                <span class="note-cell">
                  <span class="note-text">{{ record.note || '—' }}</span>
                  <a-button
                    type="text"
                    size="small"
                    class="icon-text-btn note-edit-btn"
                    @click="handleStartEditNote(record)"
                  >
                    <Edit2 :size="13" />
                  </a-button>
                </span>
              </template>
            </template>

            <template v-if="column.dataIndex === 'creator'">
              {{ record.creator?.username || '—' }}
            </template>

            <template v-if="column.dataIndex === 'user'">
              {{ record.user?.username || '—' }}
            </template>

            <template v-if="column.dataIndex === 'used_at'">
              {{ record.used_at || '—' }}
            </template>

            <template v-if="column.dataIndex === 'created_at'">
              {{ record.created_at || '—' }}
            </template>

            <template v-if="column.key === 'actions'">
              <div class="action-group">
                <a-tooltip title="复制激活码">
                  <a-button
                    size="small"
                    class="action-icon"
                    @click="copyCode(record.code, record.id)"
                  >
                    <Check v-if="copiedId === record.id" :size="14" />
                    <Copy v-else :size="14" />
                  </a-button>
                </a-tooltip>

                <a-tooltip title="复制激活链接">
                  <a-button
                    size="small"
                    class="action-icon"
                    @click="copyLink(record.code, record.id)"
                  >
                    <Link :size="14" />
                  </a-button>
                </a-tooltip>

                <a-tooltip :title="record.status === 'disabled' ? '启用' : '禁用'">
                  <a-button
                    v-if="record.status !== 'used'"
                    size="small"
                    :class="record.status === 'unused' ? 'action-btn-warn' : 'action-icon'"
                    @click="handleToggle(record.id)"
                  >
                    <PowerOff v-if="record.status === 'unused'" :size="14" />
                    <Power v-else :size="14" />
                  </a-button>
                </a-tooltip>

                <a-tooltip
                  v-if="record.status !== 'used'"
                  title="删除激活码"
                >
                  <a-button
                    size="small"
                    class="action-btn-danger"
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
    </main>

    <!-- Generate Dialog -->
    <a-modal
      v-model:open="showGenerate"
      title="生成激活码"
      @ok="handleGenerate"
      :confirm-loading="generating"
      ok-text="生成"
      cancel-text="取消"
    >
      <a-form layout="vertical">
        <a-form-item label="生成数量">
          <a-input-number
            v-model:value="generateCount"
            :min="1"
            :max="100"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="备注（可选）">
          <a-textarea
            v-model:value="generateNote"
            placeholder="添加备注信息，方便管理"
            :rows="3"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<style lang="less" scoped>
/* ==========================================================================
 * 页面骨架:与其他 5 个 Template 视图一致(.page-bg + .page-content 走全局)
 * 不再有左侧导航栏和顶部 AppHeader,本页面是单页面全宽布局
 * ========================================================================== */

.toolbar-card {
  /* 借用全局 .toolbar-card 容器(背景 + 圆角 + 8px + 内边距) */
  margin-bottom: 16px;
}

.toolbar-card :deep(.ant-input-affix-wrapper) {
  background: var(--gray-0);
}

/* ==========================================================================
 * 激活码(代码片段,monospace)
 * ========================================================================== */
.code-value {
  font-family: var(--font-mono);
  font-size: 13px;
  background: var(--gray-10);
  color: var(--color-text);
  padding: 4px 10px;
  border: 1px solid var(--gray-100);
  border-radius: 6px;
  letter-spacing: 0.5px;
  display: inline-block;
}

/* ==========================================================================
 * 备注单元(行内编辑)
 * ========================================================================== */
.note-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 220px;
}

.note-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text);
}

.note-edit-btn {
  opacity: 0;
  transition: opacity 0.15s ease;
}

tr:hover .note-edit-btn,
.note-cell:hover .note-edit-btn {
  opacity: 1;
}

/* ==========================================================================
 * 操作列按钮(与其他页面 .action-group / .action-icon / .action-btn-warn 对齐)
 * ========================================================================== */
.action-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.action-icon {
  color: var(--color-text-secondary);
}

.action-icon:hover {
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
}

.action-btn-danger:hover {
  color: var(--color-error-700);
  background: var(--color-error-50);
}

/* ==========================================================================
 * 响应式
 * ========================================================================== */
@media (max-width: 768px) {
  .page-content {
    padding: 16px;
  }
}
</style>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { Search, Plus, Copy, Check, Power, PowerOff, Link, Edit2, Save } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { listActivationCodes, generateCodes, toggleCodeStatus, updateCodeNote } from '@/apis/activation_code_api'
import AppHeader from '@/components/AppHeader.vue'

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

function getStatusTag(status) {
  const map = {
    unused: { text: '未使用', cls: 'tag-success' },
    used: { text: '已使用', cls: 'tag-default' },
    disabled: { text: '已禁用', cls: 'tag-error' },
  }
  return map[status] || { text: status, cls: 'tag-default' }
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

onMounted(fetchData)
</script>

<template>
  <div class="admin-page">
    <AppHeader />

    <div class="admin-layout">
      <aside class="admin-sidebar">
        <div class="sidebar-title">管理后台</div>
        <nav class="sidebar-nav">
          <a
            class="nav-item active"
            href="/admin/activation-codes"
            @click.prevent="router.push('/admin/activation-codes')"
          >
            激活码管理
          </a>
          <a
            class="nav-item"
            href="/admin/tags"
            @click.prevent="router.push('/admin/tags')"
          >
            标签管理
          </a>
          <a
            class="nav-item disabled"
            href="#"
            @click.prevent
          >
            模板管理
            <span class="nav-badge">即将上线</span>
          </a>
          <a
            class="nav-item disabled"
            href="#"
            @click.prevent
          >
            Playbook 管理
            <span class="nav-badge">即将上线</span>
          </a>
        </nav>
        <div class="sidebar-footer">
          <a
            class="nav-item"
            href="/"
            @click.prevent="router.push('/')"
          >
            返回首页
          </a>
        </div>
      </aside>

      <main class="admin-content">
        <div class="page-header">
          <h2 class="page-title">激活码管理</h2>
          <a-button
            type="primary"
            @click="showGenerate = true"
          >
            <template #icon><Plus :size="16" /></template>
            生成激活码
          </a-button>
        </div>

        <div class="filter-bar">
          <a-select
            v-model:value="statusFilter"
            placeholder="所有状态"
            allow-clear
            style="width: 140px"
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
          >
            <template #prefix><Search :size="16" /></template>
          </a-input-search>
        </div>

        <a-table
          :data-source="items"
          :columns="[
            { title: '激活码', dataIndex: 'code', width: 180 },
            { title: '状态', dataIndex: 'status', width: 100 },
            { title: '备注', dataIndex: 'note', width: 220 },
            { title: '创建者', dataIndex: 'creator', width: 120 },
            { title: '使用者', dataIndex: 'user', width: 120 },
            { title: '使用时间', dataIndex: 'used_at', width: 170 },
            { title: '创建时间', dataIndex: 'created_at', width: 170 },
            { title: '操作', key: 'actions', width: 200, fixed: 'right' },
          ]"
          :pagination="{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
          }"
          :loading="loading"
          row-key="id"
          @change="handleTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'code'">
              <code class="code-value">{{ record.code }}</code>
            </template>

            <template v-if="column.dataIndex === 'status'">
              <span :class="getStatusTag(record.status).cls">
                {{ getStatusTag(record.status).text }}
              </span>
            </template>

            <template v-if="column.dataIndex === 'note'">
              <template v-if="editingNoteId === record.id">
                <a-input
                  v-model:value="editingNoteValue"
                  size="small"
                  style="width: 180px"
                  @press-enter="handleSaveNote(record.id)"
                  @blur="handleSaveNote(record.id)"
                  autofocus
                />
              </template>
              <template v-else>
                <span class="note-text">{{ record.note || '-' }}</span>
                <a-button
                  type="link"
                  size="small"
                  class="edit-note-btn"
                  @click="handleStartEditNote(record)"
                >
                  <Edit2 :size="13" />
                </a-button>
              </template>
            </template>

            <template v-if="column.dataIndex === 'creator'">
              {{ record.creator?.username || '-' }}
            </template>

            <template v-if="column.dataIndex === 'user'">
              {{ record.user?.username || '-' }}
            </template>

            <template v-if="column.dataIndex === 'used_at'">
              {{ record.used_at || '-' }}
            </template>

            <template v-if="column.dataIndex === 'created_at'">
              {{ record.created_at || '-' }}
            </template>

            <template v-if="column.key === 'actions'">
              <a-tooltip title="复制激活码">
                <a-button
                  type="link"
                  size="small"
                  @click="copyCode(record.code, record.id)"
                >
                  <Check v-if="copiedId === record.id" :size="16" />
                  <Copy v-else :size="16" />
                </a-button>
              </a-tooltip>

              <a-tooltip title="复制激活链接">
                <a-button
                  type="link"
                  size="small"
                  @click="copyLink(record.code, record.id)"
                >
                  <Link :size="16" />
                </a-button>
              </a-tooltip>

              <a-tooltip :title="record.status === 'disabled' ? '启用' : '禁用'">
                <a-button
                  v-if="record.status !== 'used'"
                  type="link"
                  size="small"
                  :danger="record.status === 'unused'"
                  @click="handleToggle(record.id)"
                >
                  <PowerOff v-if="record.status === 'unused'" :size="16" />
                  <Power v-else :size="16" />
                </a-button>
              </a-tooltip>
            </template>
          </template>
        </a-table>
      </main>
    </div>

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
.admin-page {
  min-height: 100vh;
  background: var(--gray-100);
}

.admin-layout {
  display: flex;
  min-height: calc(100vh - 64px);
}

.admin-sidebar {
  width: 220px;
  flex-shrink: 0;
  background: var(--gray-0);
  border-right: 1px solid var(--gray-150);
  padding: 24px 0;
  display: flex;
  flex-direction: column;
}

.sidebar-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-700);
  padding: 0 20px 16px;
  border-bottom: 1px solid var(--gray-150);
  margin-bottom: 8px;
}

.sidebar-nav {
  flex: 1;
}

.sidebar-footer {
  border-top: 1px solid var(--gray-150);
  padding-top: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  font-size: 14px;
  color: var(--gray-600);
  text-decoration: none;
  cursor: pointer;
  transition: background 0.15s;

  &:hover {
    background: var(--gray-100);
    color: var(--gray-800);
  }

  &.active {
    color: var(--color-primary);
    background: var(--color-primary-50);
    font-weight: 500;
  }

  &.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.nav-badge {
  font-size: 11px;
  color: var(--gray-500);
  background: var(--gray-100);
  padding: 2px 6px;
  border-radius: 999px;
}

.admin-content {
  flex: 1;
  padding: 24px 32px;
  overflow-x: auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--gray-900);
  margin: 0;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.note-text {
  margin-right: 4px;
}

.edit-note-btn {
  opacity: 0;
  transition: opacity 0.15s;

  td:hover & {
    opacity: 1;
  }
}

.code-value {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 13px;
  background: var(--gray-100);
  padding: 2px 8px;
  border-radius: 4px;
  letter-spacing: 0.5px;
}

.tag-success {
  display: inline-block;
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--color-success-50);
  color: var(--color-success-700);
}

.tag-default {
  display: inline-block;
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--gray-100);
  color: var(--gray-600);
}

.tag-error {
  display: inline-block;
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--color-danger-50);
  color: var(--color-danger-700);
}
</style>

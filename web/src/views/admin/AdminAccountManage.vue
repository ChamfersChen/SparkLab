
<script setup>
/**
 * 管理员账号管理(超管)。
 *
 * 包含两个标签页:
 * 1. 管理员账号 - 管理已有的管理员和超管账号
 * 2. 管理员激活码 - 生成和管理用于创建管理员的激活码
 */
import { ref, onMounted, computed, h } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal, Tabs } from 'ant-design-vue'
import { Plus, Copy, Check, Power, PowerOff, Link, UserCog, Shield, Inbox, Trash2, ArrowUp, ArrowDown, KeyRound } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import {
  listAdminUsers,
  updateUserRole,
  toggleUserActive,
  deleteUser,
  resetUserPassword,
  listAdminCodes,
  generateAdminCodes,
  toggleAdminCodeStatus,
  deleteAdminCode,
} from '@/apis/admin_account_api'

const router = useRouter()
const userStore = useUserStore()

if (!userStore.isSuperAdmin) {
  router.replace({ name: 'dashboard' })
}

// ========== Tab 切换 ==========
const activeTab = ref('users')

// ========== 标签页 1: 管理员账号 ==========
const users = ref([])
const usersTotal = ref(0)
const usersLoading = ref(false)
const usersCurrentPage = ref(1)
const usersPageSize = ref(20)
const usersRoleFilter = ref(undefined)
const usersActiveFilter = ref(undefined)
const usersSearch = ref('')

const USER_ROLE_LABEL = {
  admin: { text: '管理员', cls: 'status-tag--info' },
  super_admin: { text: '超级管理员', cls: 'status-tag--primary' },
}

const USER_STATUS_LABEL = {
  true: { text: '已启用', cls: 'status-tag--unused' },
  false: { text: '已禁用', cls: 'status-tag--disabled' },
}

async function fetchUsers() {
  usersLoading.value = true
  try {
    const params = {
      page: usersCurrentPage.value,
      page_size: usersPageSize.value,
    }
    if (usersRoleFilter.value) params.role = usersRoleFilter.value
    if (usersActiveFilter.value !== undefined && usersActiveFilter.value !== null) params.active = usersActiveFilter.value
    if (usersSearch.value.trim()) params.search = usersSearch.value.trim()

    const res = await listAdminUsers(params)
    users.value = res.items
    usersTotal.value = res.total
  } finally {
    usersLoading.value = false
  }
}

function handleRoleFilterChange() {
  usersCurrentPage.value = 1
  fetchUsers()
}

function handleActiveFilterChange() {
  usersCurrentPage.value = 1
  fetchUsers()
}

function handleUsersSearch() {
  usersCurrentPage.value = 1
  fetchUsers()
}

function handleUsersTableChange(pagination) {
  usersCurrentPage.value = pagination.current
  usersPageSize.value = pagination.pageSize
  fetchUsers()
}

async function handleToggleUserRole(record) {
  const newRole = record.role === 'admin' ? 'super_admin' : 'admin'
  const action = newRole === 'super_admin' ? '升级为超级管理员' : '降级为管理员'
  try {
    await updateUserRole(record.id, newRole)
    message.success(`${record.username} 已${action}`)
    await fetchUsers()
  } catch {
    // error handled by base.js
  }
}

async function handleToggleUserActive(record) {
  try {
    await toggleUserActive(record.id)
    const newStatus = record.is_active ? '禁用' : '启用'
    message.success(`${record.username} 已${newStatus}`)
    await fetchUsers()
  } catch {
    // error handled by base.js
  }
}

function handleDeleteUser(record) {
  Modal.confirm({
    title: `删除账号「${record.username}」?`,
    content: () =>
      h('div', null, [
        h(
          'p',
          { style: 'margin-bottom: 8px; color: var(--gray-700);' },
          '此操作将从数据库中彻底删除该账号，不可恢复。',
        ),
      ]),
    okText: '确认删除',
    cancelText: '取消',
    okType: 'danger',
    async onOk() {
      try {
        await deleteUser(record.id)
        message.success('账号已删除')
        if (users.value.length === 1 && usersCurrentPage.value > 1) {
          usersCurrentPage.value -= 1
        }
        await fetchUsers()
      } catch (e) {
        message.error(e?.response?.data?.detail || '删除失败')
        return Promise.reject(e)
      }
    },
  })
}

// ========== 重置密码 ==========
const resetPwdVisible = ref(false)
const resetPwdRecord = ref(null)
const resetPwdNew = ref('')
const resetPwdConfirm = ref('')
const resetPwdLoading = ref(false)

function openResetPwd(record) {
  resetPwdRecord.value = record
  resetPwdNew.value = ''
  resetPwdConfirm.value = ''
  resetPwdVisible.value = true
}

async function handleResetPwd() {
  if (!resetPwdNew.value) {
    message.warning('请输入新密码')
    return
  }
  if (resetPwdNew.value.length < 6) {
    message.warning('密码至少 6 位')
    return
  }
  if (resetPwdNew.value !== resetPwdConfirm.value) {
    message.warning('两次密码输入不一致')
    return
  }
  resetPwdLoading.value = true
  try {
    await resetUserPassword(resetPwdRecord.value.id, { new_password: resetPwdNew.value })
    message.success(`已重置「${resetPwdRecord.value.username}」的密码`)
    resetPwdVisible.value = false
  } catch {
    // error handled by base.js
  } finally {
    resetPwdLoading.value = false
  }
}

const usersTableLocale = computed(() => ({
  emptyText: h('div', { class: 'empty-state' }, [
    h('div', { class: 'empty-state__icon' }, [h(Inbox, { size: 28 })]),
    h('h3', { class: 'empty-state__title' }, usersSearch.value || usersRoleFilter.value || usersActiveFilter.value !== undefined ? '没有匹配的账号' : '暂无管理员账号'),
    h('p', { class: 'empty-state__desc' }, usersSearch.value || usersRoleFilter.value || usersActiveFilter.value !== undefined ? '试试调整搜索或筛选条件' : '切换到「管理员激活码」标签生成激活码，然后使用激活码创建管理员账号'),
  ]),
}))

// ========== 标签页 2: 管理员激活码 ==========
const codes = ref([])
const codesTotal = ref(0)
const codesLoading = ref(false)
const codesCurrentPage = ref(1)
const codesPageSize = ref(20)
const codesStatusFilter = ref(undefined)
const codesSearch = ref('')

// Generate dialog
const showGenerate = ref(false)
const generateCount = ref(10)
const generateNote = ref('')
const generating = ref(false)

// Copy tracking
const copiedId = ref(null)

const CODE_STATUS_LABEL = {
  unused: { text: '未使用', cls: 'status-tag--unused' },
  used: { text: '已使用', cls: 'status-tag--used' },
  disabled: { text: '已禁用', cls: 'status-tag--disabled' },
}

async function fetchCodes() {
  codesLoading.value = true
  try {
    const params = {
      page: codesCurrentPage.value,
      page_size: codesPageSize.value,
    }
    if (codesStatusFilter.value) params.status = codesStatusFilter.value
    if (codesSearch.value.trim()) params.search = codesSearch.value.trim()

    const res = await listAdminCodes(params)
    codes.value = res.items
    codesTotal.value = res.total
  } finally {
    codesLoading.value = false
  }
}

async function handleGenerateCodes() {
  if (generateCount.value < 1 || generateCount.value > 100) {
    message.warning('数量范围 1～100')
    return
  }
  generating.value = true
  try {
    const res = await generateAdminCodes({
      count: generateCount.value,
      note: generateNote.value || null,
    })
    message.success(`成功生成 ${res.items.length} 个管理员激活码`)
    showGenerate.value = false
    generateCount.value = 10
    generateNote.value = ''
    codesCurrentPage.value = 1
    await fetchCodes()
  } finally {
    generating.value = false
  }
}

async function handleToggleCode(id) {
  try {
    await toggleAdminCodeStatus(id)
    await fetchCodes()
  } catch {
    // error handled by base.js
  }
}

function handleDeleteCode(record) {
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
        await deleteAdminCode(record.id)
        message.success('激活码已删除')
        if (codes.value.length === 1 && codesCurrentPage.value > 1) {
          codesCurrentPage.value -= 1
        }
        await fetchCodes()
      } catch (e) {
        message.error(e?.response?.data?.detail || '删除失败')
        return Promise.reject(e)
      }
    },
  })
}

import { copyToClipboard } from '@/utils/clipboard'

function copyCode(code, id) {
  copyToClipboard(code)
  copiedId.value = id
  message.success('已复制')
  setTimeout(() => { copiedId.value = null }, 2000)
}

function copyLink(code, id) {
  const link = `${window.location.origin}/activate?code=${code}`
  copyToClipboard(link)
  copiedId.value = id
  message.success('激活链接已复制')
  setTimeout(() => { copiedId.value = null }, 2000)
}

function handleCodesSearch() {
  codesCurrentPage.value = 1
  fetchCodes()
}

function handleCodesTableChange(pagination) {
  codesCurrentPage.value = pagination.current
  codesPageSize.value = pagination.pageSize
  fetchCodes()
}

const codesTableLocale = computed(() => ({
  emptyText: h('div', { class: 'empty-state' }, [
    h('div', { class: 'empty-state__icon' }, [h(Inbox, { size: 28 })]),
    h('h3', { class: 'empty-state__title' }, codesSearch.value || codesStatusFilter.value ? '没有匹配的激活码' : '暂无管理员激活码'),
    h('p', { class: 'empty-state__desc' }, codesSearch.value || codesStatusFilter.value ? '试试调整搜索或筛选条件' : '点击右上角「生成激活码」开始创建'),
  ]),
}))

function handleTabChange() {
  if (activeTab.value === 'users') fetchUsers()
  if (activeTab.value === 'codes') fetchCodes()
}

onMounted(() => {
  fetchUsers()
})
</script>

<template>
  <div class="page-bg">
    <main class="page-content">
      <!-- 顶部:主标题 + 操作区 -->
      <header class="page-bar">
        <div class="page-bar__title-area">
          <h1 class="page-bar__title">管理员账号</h1>
        </div>
        <div class="page-bar__actions">
          <a-button v-if="activeTab === 'codes'" type="primary" @click="showGenerate = true">
            <template #icon><Plus :size="16" /></template>
            生成激活码
          </a-button>
        </div>
      </header>

      <!-- 标签页 -->
      <a-tabs v-model:activeKey="activeTab" @change="handleTabChange" class="admin-tabs">
        <a-tab-pane key="users">
          <template #tab>
            <span class="tab-label">
              <UserCog :size="16" />
              管理员账号
            </span>
          </template>

          <!-- 工具栏 -->
          <div class="toolbar-card">
            <a-select
              v-model:value="usersRoleFilter"
              placeholder="所有角色"
              allow-clear
              style="width: 160px"
              @change="handleRoleFilterChange"
            >
              <a-select-option value="admin">管理员</a-select-option>
              <a-select-option value="super_admin">超级管理员</a-select-option>
            </a-select>

            <a-select
              v-model:value="usersActiveFilter"
              placeholder="所有状态"
              allow-clear
              style="width: 160px"
              @change="handleActiveFilterChange"
            >
              <a-select-option :value="true">已启用</a-select-option>
              <a-select-option :value="false">已禁用</a-select-option>
            </a-select>

            <a-input-search
              v-model:value="usersSearch"
              placeholder="搜索用户名"
              style="width: 320px"
              @search="handleUsersSearch"
            />
          </div>

          <!-- 表格 -->
          <div class="table-theme table-scroll">
            <a-table
              :data-source="users"
              :columns="[
                { title: '用户名', dataIndex: 'username', width: 180 },
                { title: '角色', dataIndex: 'role', width: 140 },
                { title: '状态', dataIndex: 'is_active', width: 100 },
                { title: '加入时间', dataIndex: 'created_at', width: 170 },
                { title: '操作', key: 'actions', width: 210, fixed: 'right' },
              ]"
              :pagination="{
                current: usersCurrentPage,
                pageSize: usersPageSize,
                total: usersTotal,
                showSizeChanger: true,
                showTotal: (t) => `共 ${t} 条`,
              }"
              :loading="usersLoading"
              :locale="usersTableLocale"
              row-key="id"
              @change="handleUsersTableChange"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.dataIndex === 'role'">
                  <span class="status-tag" :class="USER_ROLE_LABEL[record.role]?.cls">
                    {{ USER_ROLE_LABEL[record.role]?.text || record.role }}
                  </span>
                </template>

                <template v-if="column.dataIndex === 'is_active'">
                  <span class="status-tag" :class="USER_STATUS_LABEL[record.is_active]?.cls">
                    {{ USER_STATUS_LABEL[record.is_active]?.text }}
                  </span>
                </template>

                <template v-if="column.dataIndex === 'created_at'">
                  {{ record.created_at || '—' }}
                </template>

                <template v-if="column.key === 'actions'">
                  <div class="action-group">
                    <a-tooltip :title="record.role === 'admin' ? '升级为超级管理员' : '降级为管理员'">
                      <a-button
                        size="small"
                        :class="record.role === 'admin' ? 'action-btn-primary' : 'action-icon'"
                        @click="handleToggleUserRole(record)"
                      >
                        <ArrowUp v-if="record.role === 'admin'" :size="14" />
                        <ArrowDown v-else :size="14" />
                      </a-button>
                    </a-tooltip>

                    <a-tooltip title="重置密码">
                      <a-button
                        size="small"
                        class="action-icon"
                        @click="openResetPwd(record)"
                      >
                        <KeyRound :size="14" />
                      </a-button>
                    </a-tooltip>

                    <a-tooltip :title="record.is_active ? '禁用账号' : '启用账号'">
                      <a-button
                        size="small"
                        :class="record.is_active ? 'action-btn-warn' : 'action-icon'"
                        @click="handleToggleUserActive(record)"
                      >
                        <PowerOff v-if="record.is_active" :size="14" />
                        <Power v-else :size="14" />
                      </a-button>
                    </a-tooltip>

                    <a-tooltip title="删除账号">
                      <a-button
                        size="small"
                        class="action-btn-danger"
                        @click="handleDeleteUser(record)"
                      >
                        <Trash2 :size="14" />
                      </a-button>
                    </a-tooltip>
                  </div>
                </template>
              </template>
            </a-table>
          </div>
        </a-tab-pane>

        <a-tab-pane key="codes">
          <template #tab>
            <span class="tab-label">
              <Shield :size="16" />
              管理员激活码
            </span>
          </template>

          <div class="info-banner">
            <Shield :size="16" />
            <span>使用此页面生成的激活码创建的账号将自动拥有「管理员」权限。</span>
          </div>

          <!-- 工具栏 -->
          <div class="toolbar-card">
            <a-select
              v-model:value="codesStatusFilter"
              placeholder="所有状态"
              allow-clear
              style="width: 160px"
              @change="handleCodesSearch"
            >
              <a-select-option value="unused">未使用</a-select-option>
              <a-select-option value="used">已使用</a-select-option>
              <a-select-option value="disabled">已禁用</a-select-option>
            </a-select>

            <a-input-search
              v-model:value="codesSearch"
              placeholder="搜索激活码/备注/用户名"
              style="width: 320px"
              @search="handleCodesSearch"
            />
          </div>

          <!-- 表格 -->
          <div class="table-theme table-scroll">
            <a-table
              :data-source="codes"
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
                current: codesCurrentPage,
                pageSize: codesPageSize,
                total: codesTotal,
                showSizeChanger: true,
                showTotal: (t) => `共 ${t} 条`,
              }"
              :loading="codesLoading"
              :locale="codesTableLocale"
              row-key="id"
              @change="handleCodesTableChange"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.dataIndex === 'code'">
                  <code class="code-value">{{ record.code }}</code>
                </template>

                <template v-if="column.dataIndex === 'status'">
                  <span class="status-tag" :class="CODE_STATUS_LABEL[record.status]?.cls">
                    {{ CODE_STATUS_LABEL[record.status]?.text || record.status }}
                  </span>
                </template>

                <template v-if="column.dataIndex === 'note'">
                  {{ record.note || '—' }}
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
                        @click="handleToggleCode(record.id)"
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
                        @click="handleDeleteCode(record)"
                      >
                        <Trash2 :size="14" />
                      </a-button>
                    </a-tooltip>
                  </div>
                </template>
              </template>
            </a-table>
          </div>
        </a-tab-pane>
      </a-tabs>
    </main>

    <!-- Generate Dialog -->
    <a-modal
      v-model:open="showGenerate"
      title="生成管理员激活码"
      @ok="handleGenerateCodes"
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
        <a-alert
          type="info"
          message="提示"
          description="使用此页面生成的激活码创建的账号将自动拥有「管理员」权限。"
          show-icon
        />
      </a-form>
    </a-modal>

    <!-- 重置密码 -->
    <a-modal
      v-model:open="resetPwdVisible"
      title="重置密码"
      :confirm-loading="resetPwdLoading"
      ok-text="确认重置"
      cancel-text="取消"
      @ok="handleResetPwd"
    >
      <a-form layout="vertical">
        <a-form-item label="目标用户">
          <a-input :value="resetPwdRecord?.username" disabled />
        </a-form-item>
        <a-form-item label="新密码">
          <a-input-password
            v-model:value="resetPwdNew"
            placeholder="至少 6 位"
            size="large"
          >
            <template #prefix><KeyRound :size="16" /></template>
          </a-input-password>
        </a-form-item>
        <a-form-item label="确认密码">
          <a-input-password
            v-model:value="resetPwdConfirm"
            placeholder="再次输入密码"
            size="large"
          >
            <template #prefix><KeyRound :size="16" /></template>
          </a-input-password>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<style lang="less" scoped>
.admin-tabs {
  :deep(.ant-tabs-nav) {
    margin-bottom: 16px;
  }
}

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.info-banner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--color-info-50);
  color: var(--color-info-700);
  padding: 10px 14px;
  border-radius: 8px;
  margin-bottom: 16px;
  border: 1px solid var(--color-info-100);
}

.toolbar-card {
  margin-bottom: 16px;
}

.toolbar-card :deep(.ant-input-affix-wrapper) {
  background: var(--gray-0);
}

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

.action-btn-primary {
  color: var(--main-color);
}

.action-btn-primary:hover {
  color: var(--main-700);
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


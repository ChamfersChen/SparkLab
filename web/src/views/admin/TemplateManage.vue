<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { Plus, Edit2, Check, StopCircle, Eye, Search } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { adminListTemplates, adminChangeStatus, adminDeleteTemplate } from '@/apis/template_api'

const router = useRouter()
const userStore = useUserStore()

if (!userStore.isAdmin) {
  router.replace({ name: 'dashboard' })
}

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
    fetchData()
  } catch (e) {
    message.error('操作失败')
  }
}

async function handleDelete(id) {
  Modal.confirm({
    title: '确定下线此模板？',
    content: '下线后用户端将不再显示该模板，但数据保留。',
    okText: '确认下线',
    okType: 'danger',
    async onOk() {
      try {
        await adminDeleteTemplate(id)
        message.success('模板已下线')
        fetchData()
      } catch {
        message.error('操作失败')
      }
    }
  })
}

const STATUS_MAP = {
  draft: { text: '草稿', color: 'default' },
  published: { text: '已发布', color: 'green' },
  archived: { text: '已下线', color: 'red' }
}

onMounted(fetchData)
</script>

<template>
  <div class="page">
    <div class="content">
      <div class="page-header">
        <h1 class="page-title">模板管理</h1>
        <a-button type="primary" @click="goCreate">
          <template #icon><Plus :size="16" /></template>
          新建模板
        </a-button>
      </div>

      <div class="toolbar">
        <a-input-search
          v-model:value="search"
          placeholder="搜索模板…"
          allow-clear
          class="search-input"
          @search="fetchData"
        />
        <a-select
          v-model:value="statusFilter"
          placeholder="全部状态"
          allow-clear
          style="width: 140px"
          @change="fetchData"
        >
          <a-select-option value="draft">草稿</a-select-option>
          <a-select-option value="published">已发布</a-select-option>
          <a-select-option value="archived">已下线</a-select-option>
        </a-select>
      </div>

      <a-table
        :data-source="items"
        :columns="[
          { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
          { title: '标签', key: 'tags', width: 200 },
          { title: '状态', key: 'status', width: 100 },
          { title: '使用次数', dataIndex: 'use_count', key: 'use_count', width: 90, align: 'center' },
          { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 170 },
          { title: '操作', key: 'action', width: 240 }
        ]"
        :pagination="false"
        :loading="loading"
        row-key="id"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'tags'">
            <a-tag v-for="t in record.tags?.slice(0, 2)" :key="t.id" size="small">{{ t.name }}</a-tag>
            <span v-if="record.tags?.length > 2">…</span>
          </template>
          <template v-if="column.key === 'status'">
            <a-tag :color="STATUS_MAP[record.status]?.color || 'default'">
              {{ STATUS_MAP[record.status]?.text || record.status }}
            </a-tag>
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button size="small" @click="goEdit(record.id)">
                <template #icon><Edit2 :size="14" /></template>
              </a-button>
              <a-button size="small" @click="goPreview(record.id)">
                <template #icon><Eye :size="14" /></template>
              </a-button>
              <a-button
                v-if="record.status === 'draft'"
                size="small"
                type="primary"
                @click="changeStatus(record.id, 'published')"
              >
                <template #icon><Check :size="14" /></template>
                发布
              </a-button>
              <a-button
                v-if="record.status === 'published'"
                size="small"
                danger
                @click="changeStatus(record.id, 'archived')"
              >
                <template #icon><StopCircle :size="14" /></template>
                下线
              </a-button>
              <a-button
                v-if="record.status === 'archived'"
                size="small"
                @click="changeStatus(record.id, 'draft')"
              >
                恢复
              </a-button>
              <a-button
                size="small"
                danger
                @click="handleDelete(record.id)"
              >
                下线
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>

      <div v-if="total > pageSize" class="pagination-wrap">
        <a-pagination
          v-model:current="page"
          :total="total"
          :page-size="pageSize"
          @change="fetchData"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--gray-10);
}

.content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 32px 64px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-input {
  width: 280px;
}

.pagination-wrap {
  margin-top: 16px;
  text-align: center;
}
</style>

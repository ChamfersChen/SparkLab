<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { Plus, Edit2, Delete, Check, X } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { listTags, createTag, updateTag, deleteTag } from '@/apis/tag_api'

const router = useRouter()
const userStore = useUserStore()

if (!userStore.isAdmin) {
  router.replace({ name: 'dashboard' })
}

const CATEGORIES = [
  { value: 'platform', label: '平台' },
  { value: 'content_type', label: '内容类型' },
  { value: 'industry', label: '行业/场景' },
]

const activeCategory = ref('platform')
const items = ref([])
const total = ref(0)
const loading = ref(false)

// Inline editing
const editingId = ref(null)
const editingName = ref('')
const editingSort = ref(0)

// Create
const showCreate = ref(false)
const createName = ref('')
const createSort = ref(0)

async function fetchData() {
  loading.value = true
  try {
    const res = await listTags({ category: activeCategory.value })
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function switchCategory(cat) {
  activeCategory.value = cat
  editingId.value = null
  fetchData()
}

function startEdit(record) {
  editingId.value = record.id
  editingName.value = record.name
  editingSort.value = record.sort_order
}

async function saveEdit(id) {
  if (!editingName.value.trim()) {
    message.warning('标签名称不能为空')
    return
  }
  try {
    await updateTag(id, {
      name: editingName.value.trim(),
      sort_order: editingSort.value,
    })
    message.success('已更新')
    editingId.value = null
    await fetchData()
  } catch {
    // base.js handles errors
  }
}

function cancelEdit() {
  editingId.value = null
}

async function handleDelete(record) {
  Modal.confirm({
    title: `确认删除标签「${record.name}」？`,
    content: '删除后不可恢复。如该标签已被模板使用，将从相关模板中移除。',
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        await deleteTag(record.id)
        message.success('已删除')
        await fetchData()
      } catch {
        // base.js handles errors
      }
    },
  })
}

async function handleCreate() {
  if (!createName.value.trim()) {
    message.warning('请输入标签名称')
    return
  }
  try {
    await createTag({
      name: createName.value.trim(),
      category: activeCategory.value,
      sort_order: createSort.value,
    })
    message.success('已创建')
    showCreate.value = false
    createName.value = ''
    createSort.value = 0
    await fetchData()
  } catch {
    // base.js handles errors
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="admin-page">
    <main class="admin-content">
        <div class="page-header">
          <h2 class="page-title">标签管理</h2>
          <a-button type="primary" @click="showCreate = true">
            <template #icon><Plus :size="16" /></template>
            新增标签
          </a-button>
        </div>

        <div class="category-tabs">
          <a-button
            v-for="cat in CATEGORIES"
            :key="cat.value"
            :type="activeCategory === cat.value ? 'primary' : 'default'"
            @click="switchCategory(cat.value)"
          >
            {{ cat.label }}
          </a-button>
        </div>

        <div class="tag-info">
          共 {{ total }} 个标签
        </div>

        <a-table
          :data-source="items"
          :columns="[
            { title: '排序', dataIndex: 'sort_order', width: 80 },
            { title: '标签名称', dataIndex: 'name', width: 300 },
            { title: '操作', key: 'actions', width: 160 },
          ]"
          :loading="loading"
          :pagination="false"
          row-key="id"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'sort_order'">
              <template v-if="editingId === record.id">
                <a-input-number
                  v-model:value="editingSort"
                  :min="0"
                  :max="999"
                  size="small"
                  style="width: 70px"
                />
              </template>
              <template v-else>
                {{ record.sort_order }}
              </template>
            </template>

            <template v-if="column.dataIndex === 'name'">
              <template v-if="editingId === record.id">
                <a-input
                  v-model:value="editingName"
                  size="small"
                  style="width: 220px"
                  @press-enter="saveEdit(record.id)"
                />
              </template>
              <template v-else>
                {{ record.name }}
              </template>
            </template>

            <template v-if="column.key === 'actions'">
              <template v-if="editingId === record.id">
                <a-button type="link" size="small" @click="saveEdit(record.id)">
                  <Check :size="16" class="icon-save" />
                </a-button>
                <a-button type="link" size="small" @click="cancelEdit">
                  <X :size="16" class="icon-cancel" />
                </a-button>
              </template>
              <template v-else>
                <a-tooltip title="编辑">
                  <a-button type="link" size="small" @click="startEdit(record)">
                    <Edit2 :size="16" />
                  </a-button>
                </a-tooltip>
                <a-tooltip title="删除">
                  <a-button type="link" size="small" danger @click="handleDelete(record)">
                    <Delete :size="16" />
                  </a-button>
                </a-tooltip>
              </template>
            </template>
          </template>
        </a-table>
      </main>

    <a-modal
      v-model:open="showCreate"
      title="新增标签"
      @ok="handleCreate"
      ok-text="创建"
      cancel-text="取消"
    >
      <a-form layout="vertical">
        <a-form-item label="分类（当前）">
          <a-tag color="blue">{{ CATEGORIES.find(c => c.value === activeCategory)?.label }}</a-tag>
        </a-form-item>
        <a-form-item label="标签名称">
          <a-input
            v-model:value="createName"
            placeholder="输入标签名称"
            @press-enter="handleCreate"
          />
        </a-form-item>
        <a-form-item label="排序序号（越小越靠前）">
          <a-input-number
            v-model:value="createSort"
            :min="0"
            :max="999"
            style="width: 100%"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<style lang="less" scoped>
.admin-page {
  min-height: 100vh;
  background: var(--gray-10);
}

.admin-content {
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
  color: var(--color-text);
  margin: 0;
}

.category-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tag-info {
  font-size: 13px;
  color: var(--gray-500);
  margin-bottom: 12px;
}

.icon-save { color: var(--color-success-700); }
.icon-cancel { color: var(--color-danger-700); }
</style>

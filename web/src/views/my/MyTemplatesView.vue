<script setup>
/**
 * 我的模板列表页 — 普通用户管理自己创建的私有模板。
 *
 * UI 与「模板库」保持一致：2 列网格、可点击行进入详情/使用页。
 * 区别：顶部有「新建模板」按钮，列表项带编辑/删除操作。
 */
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { Plus, Clock, Edit, Trash2, FileSearch } from 'lucide-vue-next'
import { myListTemplates, myDeleteTemplate } from '@/apis/template_api'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const items = ref([])
const total = ref(0)
const search = ref('')
const sortBy = ref('newest')
const page = ref(1)
const pageSize = ref(20)

function syncQueryToUrl() {
  const query = {}
  if (search.value.trim()) query.q = search.value.trim()
  if (sortBy.value !== 'newest') query.sort = sortBy.value
  if (page.value !== 1) query.page = page.value
  router.replace({ query })
}

function loadQueryFromUrl() {
  const q = route.query
  if (typeof q.q === 'string') search.value = q.q
  if (typeof q.sort === 'string' && ['newest', 'use_count'].includes(q.sort)) {
    sortBy.value = q.sort
  }
  if (typeof q.page === 'string') {
    const p = Number(q.page)
    if (Number.isInteger(p) && p > 0) page.value = p
  }
}

async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
      sort_by: sortBy.value,
    }
    if (search.value.trim()) params.search = search.value.trim()
    const res = await myListTemplates(params)
    items.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    if (e.response?.status !== 401) {
      message.error('获取模板列表失败')
    }
  } finally {
    loading.value = false
  }
}

function goDetail(id) {
  router.push({ name: 'my-template-detail', params: { id } })
}

function goToCreate() {
  router.push({ name: 'my-template-create' })
}

function goToEdit(id, event) {
  event?.stopPropagation()
  router.push({ name: 'my-template-edit', params: { id } })
}

function confirmDelete(template, event) {
  event?.stopPropagation()
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除模板「${template.title}」吗？此操作不可恢复。`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        await myDeleteTemplate(template.id)
        message.success('删除成功')
        fetchData()
      } catch {
        message.error('删除失败')
      }
    },
  })
}

function onSearchSubmit() {
  page.value = 1
  fetchData()
  syncQueryToUrl()
}

function onSortChange() {
  page.value = 1
  fetchData()
  syncQueryToUrl()
}

function onPageChange(p, ps) {
  page.value = p
  if (ps && ps !== pageSize.value) pageSize.value = ps
  fetchData()
  syncQueryToUrl()
}

const hasActiveFilter = computed(
  () => search.value.trim().length > 0 || sortBy.value !== 'newest'
)

watch(
  () => route.query,
  (q) => {
    const incomingQ = typeof q.q === 'string' ? q.q : ''
    const incomingSort = typeof q.sort === 'string' && ['newest', 'use_count'].includes(q.sort) ? q.sort : 'newest'
    const incomingPage = typeof q.page === 'string' ? Number(q.page) : 1
    const sameState =
      search.value === incomingQ &&
      sortBy.value === incomingSort &&
      page.value === incomingPage
    if (sameState) return
    search.value = incomingQ
    sortBy.value = incomingSort
    page.value = Number.isInteger(incomingPage) && incomingPage > 0 ? incomingPage : 1
    fetchData()
  }
)

onMounted(() => {
  loadQueryFromUrl()
  fetchData()
})
</script>

<template>
  <div class="page-bg">
    <div class="page-content">
      <header class="page-bar">
        <div class="page-bar__title-area">
          <h1 class="page-bar__title">我的模板</h1>
          <p class="page-bar__sub">管理你创建的私有模板，仅自己可见</p>
        </div>
        <a-button type="primary" @click="goToCreate">
          <template #icon><Plus :size="16" /></template>
          新建模板
        </a-button>
      </header>

      <!-- 搜索 + 排序 — 与模板库一致 -->
      <div class="toolbar-card toolbar-card--compact">
        <a-input-search
          v-model:value="search"
          placeholder="搜索模板名称或描述…"
          allow-clear
          size="small"
          class="search-input"
          @search="onSearchSubmit"
        />
        <a-select v-model:value="sortBy" size="small" style="width: 132px" @change="onSortChange">
          <a-select-option value="newest">按最新创建</a-select-option>
          <a-select-option value="use_count">按使用次数</a-select-option>
        </a-select>
      </div>

      <div v-if="!loading" class="result-summary">
        共 <strong>{{ total }}</strong> 个模板
      </div>

      <div class="loading-wrap" :class="{ 'loading-wrap--active': loading }">
        <a-spin :spinning="loading">
          <ul v-if="items.length" class="template-list">
            <li
              v-for="item in items"
              :key="item.id"
              class="template-row"
              tabindex="0"
              @click="goDetail(item.id)"
              @keydown.enter="goDetail(item.id)"
            >
              <div class="row-main">
                <h3 class="row-title">{{ item.title }}</h3>
                <p v-if="item.description" class="row-desc">{{ item.description }}</p>
                <span v-else class="row-desc-empty">暂无描述</span>
              </div>
              <div class="row-tail">
                <div v-if="item.tags?.length" class="row-tags">
                  <span v-for="t in item.tags.slice(0, 3)" :key="t.id" class="card-tag">{{ t.name }}</span>
                  <span v-if="item.tags.length > 3" class="tag-more">+{{ item.tags.length - 3 }}</span>
                </div>
                <div class="row-usage">
                  <Clock :size="12" />
                  <span><strong>{{ item.use_count || 0 }}</strong> 次使用</span>
                </div>
                <div class="row-actions">
                  <button type="button" class="row-action-btn" title="编辑" @click="goToEdit(item.id, $event)">
                    <Edit :size="14" />
                  </button>
                  <button type="button" class="row-action-btn row-action-btn--danger" title="删除" @click="confirmDelete(item, $event)">
                    <Trash2 :size="14" />
                  </button>
                </div>
              </div>
            </li>
          </ul>

          <div v-else-if="!loading" class="empty-state">
            <div class="empty-state__icon">
              <FileSearch :size="28" />
            </div>
            <h3 class="empty-state__title">
              {{ hasActiveFilter ? '没有找到匹配的模板' : '暂无模板' }}
            </h3>
            <p class="empty-state__desc">
              {{ hasActiveFilter ? '试试调整搜索关键词' : '点击「新建模板」创建你的第一个私有模板' }}
            </p>
            <a-button v-if="!hasActiveFilter" type="primary" @click="goToCreate">
              <template #icon><Plus :size="16" /></template>
              新建模板
            </a-button>
          </div>
        </a-spin>
      </div>

      <div v-if="total > pageSize" class="pagination-wrap">
        <a-pagination
          v-model:current="page"
          v-model:page-size="pageSize"
          :total="total"
          show-size-changer
          :show-total="(t) => `共 ${t} 条`"
          @change="onPageChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-bar__title-area {
  flex: 1;
}

.page-bar__title {
  font-size: 22px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 4px;
}

.page-bar__sub {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin: 0;
}

.loading-wrap {
  min-height: 120px;
}

.loading-wrap--active {
  display: flex;
  justify-content: center;
  align-items: center;
}

.template-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.template-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s ease, background-color 0.15s ease;
  outline: none;
}

.template-row:hover {
  border-color: var(--main-color);
  background: var(--gray-10);
}

.template-row:focus-visible {
  border-color: var(--main-color);
  box-shadow: 0 0 0 3px var(--main-100);
}

.row-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.row-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.row-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-desc-empty {
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-style: italic;
}

.row-tail {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-self: end;
  min-width: 0;
}

.row-tags {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.card-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  background: var(--main-10);
  color: var(--main-700);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}

.tag-more {
  font-size: 12px;
  color: var(--color-text-tertiary);
  padding-left: 2px;
}

.row-usage {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-tertiary);
  white-space: nowrap;
  flex-shrink: 0;
}

.row-usage strong {
  color: var(--color-text);
  font-weight: 600;
}

.row-actions {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.template-row:hover .row-actions {
  opacity: 1;
}

.row-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.row-action-btn:hover {
  background: var(--gray-0);
  color: var(--color-text);
}

.row-action-btn--danger:hover {
  background: var(--color-error-50);
  color: var(--color-error-600);
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
}

.empty-state__icon {
  color: var(--gray-200);
  margin-bottom: 16px;
}

.empty-state__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 8px;
}

.empty-state__desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0 0 20px;
}

.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

@media (max-width: 960px) {
  .template-list {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-content {
    padding: 16px;
  }
  .page-bar {
    flex-direction: column;
    gap: 12px;
  }
  .template-row {
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 10px 12px;
  }
  .row-tail {
    justify-self: start;
    flex-wrap: wrap;
  }
  .row-actions {
    opacity: 1;
  }
}
</style>

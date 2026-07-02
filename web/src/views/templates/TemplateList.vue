<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { Filter, Clock, X, FileSearch } from 'lucide-vue-next'
import { listTemplates } from '@/apis/template_api'
import { getTagsGrouped } from '@/apis/tag_api'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const items = ref([])
const total = ref(0)
const search = ref('')
const sortBy = ref('use_count')

// 标签筛选
const tags = ref({ platform: [], content_type: [], industry: [] })
const selectedTagIds = ref([])
const showFilter = ref(false)

const page = ref(1)
const pageSize = ref(20)

/** 把筛选条件写回 URL query（可分享/可后退） */
function syncQueryToUrl() {
  const query = {}
  if (search.value.trim()) query.q = search.value.trim()
  if (sortBy.value !== 'use_count') query.sort = sortBy.value
  if (selectedTagIds.value.length) query.tags = selectedTagIds.value.join(',')
  if (page.value !== 1) query.page = page.value
  router.replace({ query })
}

/** 从 URL query 恢复筛选条件 */
function loadQueryFromUrl() {
  const q = route.query
  if (typeof q.q === 'string') search.value = q.q
  if (typeof q.sort === 'string' && ['use_count', 'newest'].includes(q.sort)) {
    sortBy.value = q.sort
  }
  if (typeof q.tags === 'string' && q.tags.trim()) {
    selectedTagIds.value = q.tags
      .split(',')
      .map((s) => Number(s))
      .filter((n) => Number.isInteger(n) && n > 0)
  }
  if (typeof q.page === 'string') {
    const p = Number(q.page)
    if (Number.isInteger(p) && p > 0) page.value = p
  }
}

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
    const params = {
      page: page.value,
      page_size: pageSize.value,
      sort_by: sortBy.value,
    }
    if (search.value.trim()) {
      params.search = search.value.trim()
    }
    const tagIdsParam = buildTagIdsParam()
    if (tagIdsParam) {
      params.tag_ids = tagIdsParam
    }
    const res = await listTemplates(params)
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

/** 跳转到模板详情 */
function goDetail(id) {
  router.push({ name: 'template-detail', params: { id } })
}

/** 用户回车或点击搜索按钮 → 立即查询（a-input-search 自带 input 防抖，不需要我们再加） */
function onSearchSubmit() {
  page.value = 1
  fetchData()
  syncQueryToUrl()
}

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
  syncQueryToUrl()
}

function clearAllFilters() {
  search.value = ''
  selectedTagIds.value = []
  sortBy.value = 'use_count'
  page.value = 1
  fetchData()
  syncQueryToUrl()
}

/** 排序变更：仅重置 page 并刷新，不再误用 onPageChange(1) */
function onSortChange() {
  page.value = 1
  fetchData()
  syncQueryToUrl()
}

/** 分页变更（页码 / 每页条数） */
function onPageChange(p, ps) {
  page.value = p
  if (ps && ps !== pageSize.value) pageSize.value = ps
  fetchData()
  syncQueryToUrl()
}

const hasActiveFilter = computed(
  () =>
    search.value.trim().length > 0 ||
    selectedTagIds.value.length > 0 ||
    sortBy.value !== 'use_count'
)

const allSelectedTags = computed(() => {
  const result = []
  for (const cat of Object.values(tags.value)) {
    for (const t of cat) {
      if (selectedTagIds.value.includes(t.id)) {
        result.push(t)
      }
    }
  }
  return result
})

/** 浏览器后退/前进：把 query 状态重新写回本地 ref 并刷新 */
watch(
  () => route.query,
  (q) => {
    const incomingQ = typeof q.q === 'string' ? q.q : ''
    const incomingSort = typeof q.sort === 'string' && ['use_count', 'newest'].includes(q.sort) ? q.sort : 'use_count'
    const incomingTags = typeof q.tags === 'string' && q.tags.trim()
      ? q.tags.split(',').map((s) => Number(s)).filter((n) => Number.isInteger(n) && n > 0)
      : []
    const incomingPage = typeof q.page === 'string' ? Number(q.page) : 1
    const sameState =
      search.value === incomingQ &&
      sortBy.value === incomingSort &&
      selectedTagIds.value.length === incomingTags.length &&
      selectedTagIds.value.every((v, i) => v === incomingTags[i]) &&
      page.value === incomingPage
    if (sameState) return
    search.value = incomingQ
    sortBy.value = incomingSort
    selectedTagIds.value = incomingTags
    page.value = Number.isInteger(incomingPage) && incomingPage > 0 ? incomingPage : 1
    fetchData()
  }
)

onMounted(() => {
  loadQueryFromUrl()
  fetchTags()
  fetchData()
})
</script>

<template>
  <div class="page-bg">
    <div class="page-content">
      <!-- 顶部:主标题 + 副标题(无返回按钮,无操作区) -->
      <header class="page-bar">
        <div class="page-bar__title-area">
          <h1 class="page-bar__title">模板库</h1>
          <p class="page-bar__sub">浏览可用的提示词模板,找到适合你的开始使用</p>
        </div>
      </header>

      <!-- 搜索 + 排序 + 筛选 — 紧凑工具栏 -->
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
          <a-select-option value="use_count">按使用次数</a-select-option>
          <a-select-option value="newest">按最新发布</a-select-option>
        </a-select>
        <button
          type="button"
          class="toolbar-btn"
          :class="{ 'toolbar-btn--active': showFilter || selectedTagIds.length }"
          @click="showFilter = !showFilter"
        >
          <Filter :size="14" />
          <span>筛选</span>
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

      <!-- 标签筛选面板 — 紧凑版 -->
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
            >
              {{ t.name }}
            </span>
          </div>
        </div>
      </div>

      <!-- 已选标签 -->
      <!-- <div v-if="allSelectedTags.length" class="selected-tags">
        <span class="selected-label">已选：</span>
        <span
          v-for="t in allSelectedTags"
          :key="t.id"
          class="tag-chip tag-chip--selected"
          @click="toggleTag(t.id)"
        >
          {{ t.name }}
          <X :size="12" />
        </span>
      </div> -->

      <!-- 结果数 -->
      <div v-if="!loading" class="result-summary">
        共 <strong>{{ total }}</strong> 个模板
        <span v-if="hasActiveFilter" class="filter-hint">（已应用筛选）</span>
      </div>

      <!-- 模板列表 -->
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
              </div>
            </li>
          </ul>

          <!-- 空态:替换 a-empty 为带图标的 .empty-state -->
          <div v-else-if="!loading" class="empty-state">
            <div class="empty-state__icon">
              <FileSearch :size="28" />
            </div>
            <h3 class="empty-state__title">
              {{ hasActiveFilter ? '没有找到匹配的模板' : '暂无可用模板' }}
            </h3>
            <p class="empty-state__desc">
              {{ hasActiveFilter ? '试试调整筛选条件,或清除筛选后查看全部模板' : '管理员发布后,模板会出现在这里' }}
            </p>
            <a-button v-if="hasActiveFilter" type="primary" @click="clearAllFilters">
              清除筛选
            </a-button>
          </div>
        </a-spin>
      </div>

      <!-- 分页 -->
      <div v-if="total > pageSize" class="pagination-wrap">
        <a-pagination
          v-model:current="page"
          v-model:page-size="pageSize"
          :total="total"
          show-size-changer
          show-total="total => `共 ${total} 条`"
          @change="onPageChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* toolbar / filter / result-summary 样式已移至 base.css, 全局共用 */

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
  .search-input {
    max-width: none;
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
  .filter-group {
    flex-direction: column;
    gap: 8px;
  }
  .filter-label {
    width: auto;
    padding-top: 0;
  }
}
</style>

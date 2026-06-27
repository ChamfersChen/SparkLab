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
            <h3 class="row-title">{{ item.title }}</h3>
            <div class="row-tags">
              <template v-if="item.tags?.length">
                <span v-for="t in item.tags.slice(0, 4)" :key="t.id" class="card-tag">{{ t.name }}</span>
                <span v-if="item.tags.length > 4" class="tag-more">+{{ item.tags.length - 4 }}</span>
              </template>
              <span v-else class="row-tags-empty">—</span>
            </div>
            <div class="row-usage">
              <Clock :size="13" />
              <span><strong>{{ item.use_count || 0 }}</strong> 次使用</span>
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
/* 页面顶部 .page-bar__title 用全局 24px(已对齐 design.md),不再局部覆盖 */

/* 紧凑工具栏：覆盖全局 .toolbar-card 的 padding/gap，控件高度统一 28px */
.toolbar-card--compact {
  padding: 8px 12px;
  gap: 8px;
  border-radius: 8px;
}

/* 普通 select / button: 直接给最外层圆角 + 28px 高 */
.toolbar-card--compact :deep(.ant-select-sm .ant-select-selector),
.toolbar-card--compact :deep(.ant-btn-sm:not(.ant-input-search-button)) {
  height: 28px;
  border-radius: 6px;
}

/* a-input-search 的 DOM 是 group-wrapper > [affix-wrapper, group-addon>button]:
 * 只给最外层 .ant-input-group-wrapper 设圆角,内部 affix-wrapper / input / button
 * 都保持矩形,避免内外圆角不一致或底部边框被相邻 addon 截断。 */
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
  max-width: 420px;
  min-width: 180px;
}

/* 自定义紧凑按钮：跟 Ant 小号控件高度对齐 */
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

/* 紧凑模式下的 tag-chip 缩小一档 */
.filter-panel--compact .tag-chip {
  padding: 2px 10px;
  font-size: 12px;
}

.selected-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.selected-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-right: 4px;
}

.selected-tags .tag-chip {
  gap: 6px;
  padding: 4px 8px 4px 12px;
}

.result-summary {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 4px 0 16px;
}

.result-summary strong {
  color: var(--color-text);
  font-weight: 600;
}

.filter-hint {
  color: var(--main-600);
  margin-left: 4px;
}

.template-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.template-row {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 2fr) auto;
  align-items: center;
  gap: 24px;
  padding: 14px 20px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
  outline: none;
}

.template-row:hover {
  border-color: var(--main-300, var(--gray-300));
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.template-row:focus-visible {
  border-color: var(--main-500, var(--gray-400));
  box-shadow: 0 0 0 3px var(--main-100, rgba(0, 0, 0, 0.06));
}

.row-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.row-tags-empty {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.card-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  background: var(--gray-10);
  color: var(--color-text-secondary);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}

.tag-more {
  font-size: 12px;
  color: var(--color-text-tertiary);
  padding-left: 2px;
}

.row-usage {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text-tertiary);
  white-space: nowrap;
  justify-self: end;
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

@media (max-width: 768px) {
  .search-input {
    max-width: none;
  }
  .template-row {
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 12px 14px;
  }
  .row-usage {
    justify-self: start;
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

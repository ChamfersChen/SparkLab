<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { BookOpen, Clock, Filter, FileSearch, X } from 'lucide-vue-next'
import { listPlaybooks } from '@/apis/playbook_api'
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
    if (search.value.trim()) params.search = search.value.trim()
    const tagIdsParam = buildTagIdsParam()
    if (tagIdsParam) params.tag_ids = tagIdsParam
    const res = await listPlaybooks(params)
    items.value = res.items
    total.value = res.total
  } catch (e) {
    if (e.response?.status !== 401) {
      message.error('获取流程列表失败')
    }
  } finally {
    loading.value = false
  }
}

function goRun(id) {
  router.push({ name: 'playbook-run', params: { id } })
}

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
  () =>
    search.value.trim().length > 0 ||
    selectedTagIds.value.length > 0 ||
    sortBy.value !== 'use_count'
)

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
      <header class="page-bar">
        <div class="page-bar__title-area">
          <h1 class="page-bar__title">流程库</h1>
          <p class="page-bar__sub">按顺序完成各步提示词,走完流程拿到一套完整结果</p>
        </div>
      </header>

      <div class="toolbar-card toolbar-card--compact">
        <a-input-search
          v-model:value="search"
          placeholder="搜索流程名称或描述…"
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

      <div v-if="!loading" class="result-summary">
        共 <strong>{{ total }}</strong> 个流程
        <span v-if="hasActiveFilter" class="filter-hint">（已应用筛选）</span>
      </div>

      <div class="loading-wrap" :class="{ 'loading-wrap--active': loading }">
        <a-spin :spinning="loading">
          <ul v-if="items.length" class="playbook-list">
            <li
              v-for="item in items"
              :key="item.id"
              class="playbook-row"
              tabindex="0"
              @click="goRun(item.id)"
              @keydown.enter="goRun(item.id)"
            >
              <div class="row-main">
                <h3 class="row-title">{{ item.title }}</h3>
                <p class="row-desc">{{ item.description }}</p>
              </div>
              <div class="row-steps">
                <template v-if="item.steps?.length">
                  <span
                    v-for="(s, idx) in item.steps.slice(0, 4)"
                    :key="s.id || idx"
                    class="step-chip"
                  >
                    <span class="step-chip__no">{{ idx + 1 }}</span>
                    <span class="step-chip__name">{{ s.name }}</span>
                  </span>
                  <span v-if="item.steps.length > 4" class="tag-more">+{{ item.steps.length - 4 }}</span>
                </template>
                <span v-else class="row-tags-empty">无步骤</span>
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

          <div v-else-if="!loading" class="empty-state">
            <div class="empty-state__icon">
              <FileSearch :size="28" />
            </div>
            <h3 class="empty-state__title">
              {{ hasActiveFilter ? '没有找到匹配的流程' : '暂无可用流程' }}
            </h3>
            <p class="empty-state__desc">
              {{ hasActiveFilter ? '试试调整筛选条件,或清除筛选后查看全部' : '管理员发布后,流程会出现在这里' }}
            </p>
            <a-button v-if="hasActiveFilter" type="primary" @click="clearAllFilters">
              清除筛选
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
/* 复用 TemplateList 的 toolbar / filter / result-summary 模式, 只重写行样式 */

.loading-wrap {
  min-height: 120px;
}

.loading-wrap--active {
  display: flex;
  justify-content: center;
  align-items: center;
}

.playbook-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.playbook-row {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 2fr) auto;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s ease, background-color 0.15s ease;
  outline: none;
}

.playbook-row:hover {
  border-color: var(--main-color);
  background: var(--gray-10);
}

.playbook-row:focus-visible {
  border-color: var(--main-color);
  box-shadow: 0 0 0 3px var(--main-100);
}

.row-main {
  min-width: 0;
}

.row-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 2px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-steps {
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

.step-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px 2px 4px;
  background: var(--gray-10);
  border: 1px solid var(--gray-150);
  border-radius: 999px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.step-chip__no {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--main-color);
  color: var(--gray-0);
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
}

.step-chip__name {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tag-more {
  font-size: 12px;
  color: var(--color-text-tertiary);
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

@media (max-width: 768px) {
  .playbook-row {
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 12px 14px;
  }
  .row-tail {
    justify-self: start;
    flex-wrap: wrap;
  }
}
</style>

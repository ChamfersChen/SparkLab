<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { Search, Filter, ArrowUpDown, Star, Clock, LayoutGrid } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { listTemplates } from '@/apis/template_api'
import { getTagsGrouped } from '@/apis/tag_api'

const router = useRouter()
const userStore = useUserStore()

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

async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
      sort_by: sortBy.value
    }
    if (search.value.trim()) {
      params.search = search.value.trim()
    }
    if (selectedTagIds.value.length) {
      params.tag_ids = selectedTagIds.value.join(',')
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

async function fetchTags() {
  try {
    const res = await getTagsGrouped()
    tags.value = res
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
}

function goDetail(id) {
  router.push({ name: 'template-detail', params: { id } })
}

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

onMounted(() => {
  fetchTags()
  fetchData()
})
</script>

<template>
  <div class="page">
    <div class="content">
      <div class="page-header">
        <h1 class="page-title">模板库</h1>
        <p class="page-desc">浏览可用的提示词模板，找到适合你的开始使用</p>
      </div>

      <!-- 搜索 + 排序 -->
      <div class="toolbar">
        <a-input-search
          v-model:value="search"
          placeholder="搜索模板名称或描述…"
          allow-clear
          class="search-input"
          @search="fetchData"
        />
        <a-select v-model:value="sortBy" style="width: 140px" @change="fetchData">
          <a-select-option value="use_count">按使用次数</a-select-option>
          <a-select-option value="newest">按最新发布</a-select-option>
        </a-select>
        <a-button :type="showFilter ? 'primary' : 'default'" @click="showFilter = !showFilter">
          <template #icon><Filter :size="16" /></template>
          筛选
        </a-button>
      </div>

      <!-- 标签筛选面板 -->
      <div v-if="showFilter" class="filter-panel">
        <div v-for="(tagList, category) in tags" :key="category" class="filter-group">
          <span class="filter-label">{{ { platform: '平台', content_type: '内容类型', industry: '行业/场景' }[category] }}</span>
          <a-tag
            v-for="t in tagList"
            :key="t.id"
            :color="selectedTagIds.includes(t.id) ? 'blue' : 'default'"
            style="cursor: pointer; margin: 2px"
            @click="toggleTag(t.id)"
          >
            {{ t.name }}
          </a-tag>
        </div>
      </div>

      <!-- 已选标签 -->
      <div v-if="allSelectedTags.length" class="selected-tags">
        <span class="selected-label">已选：</span>
        <a-tag v-for="t in allSelectedTags" :key="t.id" closable color="blue" @close="toggleTag(t.id)">
          {{ t.name }}
        </a-tag>
      </div>

      <!-- 模板列表 -->
      <a-spin :spinning="loading">
        <div v-if="items.length" class="template-grid">
          <div
            v-for="item in items"
            :key="item.id"
            class="template-card"
            @click="goDetail(item.id)"
          >
            <div class="card-header">
              <h3 class="card-title">{{ item.title }}</h3>
              <a-tag v-if="item.status === 'published'" color="green" class="status-tag">已发布</a-tag>
            </div>
            <p class="card-desc">{{ item.description }}</p>
            <div class="card-tags">
              <a-tag v-for="t in item.tags.slice(0, 3)" :key="t.id" color="default" class="tag-item">{{ t.name }}</a-tag>
              <span v-if="item.tags.length > 3" class="tag-more">+{{ item.tags.length - 3 }}</span>
            </div>
            <div class="card-meta">
              <span class="meta-item">
                <Clock :size="13" />
                {{ item.use_count || 0 }} 次使用
              </span>
            </div>
          </div>
        </div>

        <a-empty v-else-if="!loading" description="没有找到匹配的模板，换个关键词试试" />
      </a-spin>

      <!-- 分页 -->
      <div v-if="total > pageSize" class="pagination-wrap">
        <a-pagination
          v-model:current="page"
          :total="total"
          :page-size="pageSize"
          show-size-changer
          show-total="total => `共 ${total} 条`"
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
  max-width: 1080px;
  margin: 0 auto;
  padding: 32px 32px 64px;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 6px;
}

.page-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0;
}

/* Toolbar */
.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.search-input {
  max-width: 360px;
  flex: 1;
}

/* Filter panel */
.filter-panel {
  background: var(--gray-0);
  border: 1px solid var(--gray-50);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}

.filter-group {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
}

.filter-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  min-width: 60px;
  line-height: 24px;
}

.selected-tags {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.selected-label {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

/* Card grid */
.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.template-card {
  background: var(--gray-0);
  border: 1px solid var(--gray-50);
  border-radius: 10px;
  padding: 20px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.template-card:hover {
  border-color: var(--main-30);
  box-shadow: var(--shadow-sm);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.status-tag {
  flex-shrink: 0;
}

.card-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin: 0 0 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.tag-item {
  font-size: 11px;
}

.tag-more {
  font-size: 11px;
  color: var(--color-text-tertiary);
  line-height: 22px;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.pagination-wrap {
  margin-top: 24px;
  text-align: center;
}

@media (max-width: 640px) {
  .content {
    padding: 24px 16px 48px;
  }
  .toolbar {
    flex-wrap: wrap;
  }
  .search-input {
    max-width: 100%;
  }
}
</style>

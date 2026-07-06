<script setup>
/**
 * 我的收藏 — Tab 切换 (全部/模板/流程) + 卡片列表
 */
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { Heart, FileText, BookOpen, Clock, Trash2, FolderOpen } from 'lucide-vue-next'
import { getFavorites, toggleFavorite } from '@/apis/favorite_api'

const router = useRouter()

const loading = ref(false)
const items = ref([])
const total = ref(0)
const activeTab = ref('all')
const page = ref(1)
const pageSize = ref(50)

const TABS = [
  { key: 'all', label: '全部' },
  { key: 'template', label: '模板' },
  { key: 'playbook', label: '流程' },
]

const TYPE_META = {
  template: { label: '模板', icon: FileText, cls: 'fav-type--template' },
  playbook: { label: '流程', icon: BookOpen, cls: 'fav-type--playbook' },
}

async function fetchData() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (activeTab.value !== 'all') {
      params.type = activeTab.value
    }
    const res = await getFavorites(params)
    items.value = res.items || []
    total.value = res.total || 0
  } catch {
    message.error('加载收藏列表失败')
  } finally {
    loading.value = false
  }
}

function handleTabChange(key) {
  activeTab.value = key
  page.value = 1
  fetchData()
}

function handleRemove(item) {
  toggleFavorite(item.target_type, item.target_id).then((res) => {
    if (!res.favorited) {
      message.success('已取消收藏')
      fetchData()
    }
  }).catch(() => {
    message.error('操作失败')
  })
}

function goDetail(item) {
  if (item.target_type === 'template') {
    router.push({ name: 'template-detail', params: { id: item.target_id } })
  } else {
    router.push({ name: 'playbook-run', params: { id: item.target_id } })
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="page-bg">
    <div class="page-content">
      <a-spin :spinning="loading">
        <!-- 顶部:标题 + Tab -->
        <header class="page-bar">
          <h1 class="page-bar__title">我的收藏</h1>
          <div class="page-bar__tabs">
            <button
              v-for="tab in TABS"
              :key="tab.key"
              class="tab-btn"
              :class="{ 'tab-btn--active': activeTab === tab.key }"
              @click="handleTabChange(tab.key)"
            >
              {{ tab.label }}
            </button>
          </div>
        </header>

        <!-- 收藏列表 -->
        <ul v-if="items.length" class="fav-list">
          <li
            v-for="item in items"
            :key="item.id"
            class="fav-row"
            @click="goDetail(item)"
          >
            <div class="fav-row__main">
              <div class="fav-row__header">
                <span class="fav-type" :class="TYPE_META[item.target_type]?.cls">
                  <component :is="TYPE_META[item.target_type]?.icon" :size="12" />
                  {{ TYPE_META[item.target_type]?.label }}
                </span>
                <h3 class="fav-row__title">{{ item.title }}</h3>
              </div>
              <p v-if="item.description" class="fav-row__desc">{{ item.description }}</p>
            </div>
            <div class="fav-row__tail">
              <span v-if="item.created_at" class="fav-row__time">
                <Clock :size="12" />
                {{ new Date(item.created_at).toLocaleDateString() }}
              </span>
              <button
                class="fav-remove-btn"
                title="取消收藏"
                @click.stop="handleRemove(item)"
              >
                <Trash2 :size="14" />
              </button>
            </div>
          </li>
        </ul>

        <!-- 空态 -->
        <div v-else-if="!loading" class="empty-state">
          <div class="empty-state__icon">
            <Heart :size="28" />
          </div>
          <h3 class="empty-state__title">
            {{ activeTab === 'all' ? '还没有收藏任何内容' : `还没有收藏${activeTab === 'template' ? '模板' : '流程'}` }}
          </h3>
          <p class="empty-state__desc">
            {{ activeTab === 'all' ? '去模板库或流程库看看' : `去${activeTab === 'template' ? '模板库' : '流程库'}看看` }}
          </p>
          <a-button type="primary" @click="router.push(activeTab === 'playbook' ? '/playbooks' : '/templates')">
            <template #icon><FolderOpen :size="14" /></template>
            {{ activeTab === 'playbook' ? '去流程库' : '去模板库' }}
          </a-button>
        </div>
      </a-spin>
    </div>
  </div>
</template>

<style scoped>
.page-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.page-bar__title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.page-bar__tabs {
  display: inline-flex;
  gap: 4px;
  background: var(--gray-10);
  border-radius: 6px;
  padding: 3px;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 12px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tab-btn:hover {
  color: var(--color-text);
}

.tab-btn--active {
  background: var(--gray-0);
  color: var(--color-text);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

/* 收藏列表 */
.fav-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.fav-row {
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
}

.fav-row:hover {
  border-color: var(--main-color);
  background: var(--gray-10);
}

.fav-row__main {
  min-width: 0;
}

.fav-row__header {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.fav-type {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.fav-type--template {
  background: var(--main-10);
  color: var(--main-700);
}

.fav-type--playbook {
  background: var(--color-success-50);
  color: var(--color-success-700);
}

.fav-row__title {
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

.fav-row__desc {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin: 2px 0 0;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fav-row__tail {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.fav-row__time {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.fav-remove-btn {
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
  opacity: 0;
}

.fav-row:hover .fav-remove-btn {
  opacity: 1;
}

.fav-remove-btn:hover {
  background: var(--color-error-50);
  color: var(--color-error-600);
}

/* 空态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 64px 24px;
}

.empty-state__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--gray-10);
  color: var(--color-text-tertiary);
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

/* 响应式 */
@media (max-width: 960px) {
  .fav-list {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .fav-row__tail {
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
  }

  .fav-remove-btn {
    opacity: 1;
  }
}
</style>

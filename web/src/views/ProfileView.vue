<script setup>
/**
 * 个人中心 (左右两栏布局).
 *
 * 左侧导航: 基础信息 / 模板使用记录 / 流程使用记录
 * 右侧内容: 根据选中导航展示对应面板
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import {
  BookOpen,
  Check,
  Clock,
  Copy,
  FileText,
  LayoutGrid,
  Settings,
  Sparkles,
  Trash2,
  X,
} from 'lucide-vue-next'
import MarkdownIt from 'markdown-it'
import {
  deletePlaybookRun,
  getPlaybookRun,
  listPlaybookRuns,
} from '@/apis/playbook_runs_api'
import {
  deleteTemplateRun,
  getTemplateRun,
  listTemplateRuns,
} from '@/apis/template_runs_api'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

if (!userStore.isLoggedIn) {
  router.replace({ name: 'login' })
}

/* ── 左侧导航 ── */
const currentTab = ref('basic')
const navItems = [
  { key: 'basic', label: '基础信息', icon: Settings },
  { key: 'templates', label: '模板', icon: FileText },
  { key: 'playbooks', label: '流程', icon: LayoutGrid },
]

/* ── 流程运行记录 ── */
const runsLoading = ref(false)
const runs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const drawerOpen = ref(false)
const drawerLoading = ref(false)
const activeRun = ref(null)

async function fetchRuns() {
  runsLoading.value = true
  try {
    const res = await listPlaybookRuns({ page: page.value, page_size: pageSize.value })
    runs.value = res.items || []
    total.value = res.total || 0
  } catch {
    message.error('加载运行记录失败')
  } finally {
    runsLoading.value = false
  }
}

function onPageChange(p) {
  page.value = p
  fetchRuns()
}

async function openDetail(runId) {
  drawerOpen.value = true
  activeRun.value = null
  drawerLoading.value = true
  try {
    activeRun.value = await getPlaybookRun(runId)
  } catch {
    message.error('加载详情失败')
    drawerOpen.value = false
  } finally {
    drawerLoading.value = false
  }
}

function closeDetail() {
  drawerOpen.value = false
  activeRun.value = null
  if (route.query.runId) {
    const rest = { ...route.query }
    delete rest.runId
    router.replace({ query: rest })
  }
}

function handleDelete(run) {
  Modal.confirm({
    title: `删除运行记录「${run.title || run.playbook_title}」?`,
    content: '此操作不可恢复。',
    okText: '删除',
    cancelText: '取消',
    okType: 'danger',
    async onOk() {
      try {
        await deletePlaybookRun(run.id)
        message.success('已删除')
        if (activeRun.value?.id === run.id) closeDetail()
        runs.value = runs.value.filter((r) => r.id !== run.id)
        total.value = Math.max(0, total.value - 1)
      } catch (e) {
        message.error(e?.response?.data?.detail || e?.message || '删除失败')
        return Promise.reject(e)
      }
    },
  })
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const diff = Math.floor((Date.now() - d.getTime()) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`
  return d.toLocaleString('zh-CN', { hour12: false })
}

function formatAbsolute(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

const hasRuns = computed(() => runs.value.length > 0)

/* ── 模板运行记录 ── */
const templateRunsLoading = ref(false)
const templateRuns = ref([])
const templateTotal = ref(0)
const templatePage = ref(1)
const templatePageSize = ref(20)

const templateDrawerOpen = ref(false)
const templateDrawerLoading = ref(false)
const activeTemplateRun = ref(null)

async function fetchTemplateRuns() {
  templateRunsLoading.value = true
  try {
    const res = await listTemplateRuns({ page: templatePage.value, page_size: templatePageSize.value })
    templateRuns.value = res.items || []
    templateTotal.value = res.total || 0
  } catch {
    message.error('加载模板使用记录失败')
  } finally {
    templateRunsLoading.value = false
  }
}

function onTemplatePageChange(p) {
  templatePage.value = p
  fetchTemplateRuns()
}

async function openTemplateDetail(runId) {
  templateDrawerOpen.value = true
  activeTemplateRun.value = null
  templateDrawerLoading.value = true
  try {
    activeTemplateRun.value = await getTemplateRun(runId)
  } catch {
    message.error('加载详情失败')
    templateDrawerOpen.value = false
  } finally {
    templateDrawerLoading.value = false
  }
}

function closeTemplateDetail() {
  templateDrawerOpen.value = false
  activeTemplateRun.value = null
}

function handleDeleteTemplateRun(run) {
  Modal.confirm({
    title: `删除「${run.title || run.template_title}」?`,
    content: '此操作不可恢复。',
    okText: '删除',
    cancelText: '取消',
    okType: 'danger',
    async onOk() {
      try {
        await deleteTemplateRun(run.id)
        message.success('已删除')
        if (activeTemplateRun.value?.id === run.id) closeTemplateDetail()
        templateRuns.value = templateRuns.value.filter((r) => r.id !== run.id)
        templateTotal.value = Math.max(0, templateTotal.value - 1)
      } catch (e) {
        message.error(e?.response?.data?.detail || e?.message || '删除失败')
        return Promise.reject(e)
      }
    },
  })
}

const hasTemplateRuns = computed(() => templateRuns.value.length > 0)

/* ── Markdown 渲染 ── */
const md = new MarkdownIt({ html: false, linkify: true, breaks: true }).use((m) => {
  const defaultOpen =
    m.renderer.rules.link_open ||
    function (tokens, idx, options, _env, self) {
      return self.renderToken(tokens, idx, options)
    }
  m.renderer.link_open = function (tokens, idx, options, env, self) {
    const t = tokens[idx]
    t.attrSet('target', '_blank')
    t.attrSet('rel', 'noopener noreferrer')
    return defaultOpen(tokens, idx, options, env, self)
  }
})

const activeRunFinalHtml = computed(() => {
  if (!activeRun.value?.final_result) return ''
  return md.render(activeRun.value.final_result)
})

function renderTemplateRunHtml(text) {
  if (!text) return ''
  return md.render(text)
}

import { copyToClipboard } from '@/utils/clipboard'

async function copyText(text, label) {
  if (!text) return
  try {
    await copyToClipboard(text)
    message.success(`${label}已复制到剪贴板`)
  } catch {
    message.error('复制失败,请手动复制')
  }
}

/* ── 角色映射 ── */
const roleLabel = computed(() => {
  const map = { user: '普通用户', admin: '管理员', super_admin: '超级管理员' }
  return map[userStore.user?.role] || '未知'
})

/* ── 生命周期 ── */
onMounted(async () => {
  if (route.query.tab) currentTab.value = route.query.tab
  if (currentTab.value === 'templates') {
    await fetchTemplateRuns()
  } else {
    await fetchRuns()
  }
  const rid = route.query.runId
  if (rid) openDetail(Number(rid))
})

watch(
  () => route.query.runId,
  (rid) => { if (rid) openDetail(Number(rid)) },
)

function switchTab(key) {
  currentTab.value = key
  router.replace({ query: { ...route.query, tab: key } })
  if (key === 'templates' && !templateRuns.value.length) {
    fetchTemplateRuns()
  } else if (key === 'playbooks' && !runs.value.length) {
    fetchRuns()
  }
}
</script>

<template>
  <div class="page-bg">
    <div class="page-content">
      <header class="page-bar">
        <h1 class="page-bar__title">个人中心</h1>
      </header>

      <div class="profile-layout">
        <!-- 左: 导航 -->
        <aside class="profile-nav">
          <div class="profile-nav__title">导航</div>
          <button
            v-for="item in navItems"
            :key="item.key"
            type="button"
            class="profile-nav__item"
            :class="{ 'profile-nav__item--active': currentTab === item.key }"
            @click="switchTab(item.key)"
          >
            <component :is="item.icon" :size="16" />
            <span>{{ item.label }}</span>
          </button>
        </aside>

        <!-- 右: 内容 -->
        <main class="profile-main">
          <!-- ====== 基础信息 ====== -->
          <section v-if="currentTab === 'basic'" class="card-block">
            <h2 class="section-title">
              <Settings :size="16" />
              <span>基础信息</span>
            </h2>
            <div class="info-grid">
              <div class="info-item">
                <div class="info-item__label">用户名</div>
                <div class="info-item__value">{{ userStore.user?.username || '-' }}</div>
              </div>
              <div class="info-item">
                <div class="info-item__label">角色</div>
                <div class="info-item__value">
                  <span class="role-tag">{{ roleLabel }}</span>
                </div>
              </div>
              <div class="info-item">
                <div class="info-item__label">用户 ID</div>
                <div class="info-item__value info-item__value--mono">{{ userStore.user?.id || '-' }}</div>
              </div>
            </div>
          </section>

          <!-- ====== 模板保存 ====== -->
          <section v-else-if="currentTab === 'templates'" class="card-block">
            <h2 class="section-title">
              <FileText :size="16" />
              <span>保存的模板</span>
              <span class="section-title__count" v-if="templateTotal > 0">共 {{ templateTotal }} 条</span>
            </h2>

            <a-spin :spinning="templateRunsLoading">
              <div v-if="!templateRunsLoading && !hasTemplateRuns" class="empty-state">
                <div class="empty-state__icon">
                  <FileText :size="28" />
                </div>
                <h3 class="empty-state__title">还没有保存记录</h3>
                <p class="empty-state__desc">
                  填写模板变量并生成提示词后，点击「保存到我的」，即可在这里查看历史结果。
                </p>
                <a-button type="primary" @click="$router.push({ name: 'templates' })">
                  去模板库
                </a-button>
              </div>

              <ul v-else class="runs-list">
                <li
                  v-for="r in templateRuns"
                  :key="r.id"
                  class="run-card"
                  :class="{ 'run-card--active': activeTemplateRun?.id === r.id }"
                >
                  <div class="run-card__main" @click="openTemplateDetail(r.id)">
                    <div class="run-card__header">
                      <FileText :size="14" class="run-card__icon" />
                      <span class="run-card__playbook-title">{{ r.template_title }}</span>
                      <span v-if="r.title && r.title !== r.template_title" class="run-card__custom-title">
                        · {{ r.title }}
                      </span>
                    </div>
                    <div class="run-card__meta">
                      <span class="run-card__time" :title="formatAbsolute(r.created_at)">
                        {{ formatTime(r.created_at) }}
                      </span>
                      <span v-if="r.has_result" class="run-card__final-badge">
                        <Check :size="11" />
                        <span>含 AI 结果</span>
                      </span>
                      <span v-else-if="r.has_prompt" class="run-card__prompt-badge">
                        <Sparkles :size="11" />
                        <span>含提示词</span>
                      </span>
                    </div>
                  </div>
                  <div class="run-card__actions">
                    <a-button size="small" @click="openTemplateDetail(r.id)">查看</a-button>
                    <a-tooltip title="删除">
                      <a-button size="small" class="action-btn-danger" @click="handleDeleteTemplateRun(r)">
                        <template #icon><Trash2 :size="14" /></template>
                      </a-button>
                    </a-tooltip>
                  </div>
                </li>
              </ul>

              <div v-if="templateTotal > templatePageSize" class="pagination-wrap">
                <a-pagination
                  v-model:current="templatePage"
                  :total="templateTotal"
                  :page-size="templatePageSize"
                  show-total="total => `共 ${total} 条`"
                  @change="onTemplatePageChange"
                />
              </div>
            </a-spin>
          </section>

          <!-- ====== 保存流程 ====== -->
          <section v-else class="card-block">
            <h2 class="section-title">
              <LayoutGrid :size="16" />
              <span>保存流程</span>
              <span class="section-title__count" v-if="total > 0">共 {{ total }} 条</span>
            </h2>

            <a-spin :spinning="runsLoading">
              <div v-if="!runsLoading && !hasRuns" class="empty-state">
                <div class="empty-state__icon">
                  <BookOpen :size="28" />
                </div>
                <h3 class="empty-state__title">还没有保存记录</h3>
                <p class="empty-state__desc">
                  完成一个流程后，点击「保存」，即可在「个人中心 - 流程」查看保存结果。
                </p>
                <a-button type="primary" @click="$router.push({ name: 'playbooks' })">
                  去流程库
                </a-button>
              </div>

              <ul v-else class="runs-list">
                <li
                  v-for="r in runs"
                  :key="r.id"
                  class="run-card"
                  :class="{ 'run-card--active': activeRun?.id === r.id }"
                >
                  <div class="run-card__main" @click="openDetail(r.id)">
                    <div class="run-card__header">
                      <FileText :size="14" class="run-card__icon" />
                      <span class="run-card__playbook-title">{{ r.playbook_title }}</span>
                      <span v-if="r.title && r.title !== r.playbook_title" class="run-card__custom-title">
                        · {{ r.title }}
                      </span>
                    </div>
                    <div class="run-card__meta">
                      <span class="run-card__time" :title="formatAbsolute(r.created_at)">
                        {{ formatTime(r.created_at) }}
                      </span>
                      <span v-if="r.has_final_result" class="run-card__final-badge">
                        <Check :size="11" />
                        <span>含最终结果</span>
                      </span>
                    </div>
                  </div>
                  <div class="run-card__actions">
                    <a-button size="small" @click="openDetail(r.id)">查看</a-button>
                    <a-tooltip title="删除">
                      <a-button size="small" class="action-btn-danger" @click="handleDelete(r)">
                        <template #icon><Trash2 :size="14" /></template>
                      </a-button>
                    </a-tooltip>
                  </div>
                </li>
              </ul>

              <div v-if="total > pageSize" class="pagination-wrap">
                <a-pagination
                  v-model:current="page"
                  :total="total"
                  :page-size="pageSize"
                  show-total="total => `共 ${total} 条`"
                  @change="onPageChange"
                />
              </div>
            </a-spin>
          </section>
        </main>
      </div>
    </div>

    <!-- 详情 drawer -->
    <a-drawer
      :open="drawerOpen"
      :width="560"
      :title="null"
      :footer="null"
      :closable="false"
      @close="closeDetail"
    >
      <a-spin :spinning="drawerLoading">
        <template v-if="activeRun">
          <div class="detail-header">
            <div>
              <div class="detail-header__title">
                {{ activeRun.title || activeRun.playbook_title }}
              </div>
              <div class="detail-header__meta">
                <span>{{ activeRun.playbook_title }}</span>
                <span>·</span>
                <span :title="formatAbsolute(activeRun.created_at)">
                  {{ formatTime(activeRun.created_at) }}
                </span>
              </div>
            </div>
            <button type="button" class="detail-close" title="关闭" @click="closeDetail">
              <X :size="16" />
            </button>
          </div>

          <!--<div class="detail-meta-bar">
            <button
              type="button"
              class="detail-delete-btn"
              @click="handleDelete({ id: activeRun.id, title: activeRun.title, playbook_title: activeRun.playbook_title })"
            >
              <Trash2 :size="13" />
              <span>删除</span>
            </button>
          </div>-->

          <section v-if="activeRun.final_result" class="result-section">
            <div class="result-section__title">
              <Sparkles :size="14" />
              <span>最终结果</span>
              <button
                type="button"
                class="copy-inline-btn"
                title="复制最终结果"
                @click="copyText(activeRun.final_result, '最终结果')"
              >
                <Copy :size="12" />
              </button>
            </div>
            <div class="final-result-card" v-html="activeRunFinalHtml"></div>
          </section>

          <div v-else class="detail-empty">
            这条记录没有保存最终结果。
          </div>
        </template>
      </a-spin>
    </a-drawer>

    <!-- 模板使用记录详情 drawer -->
    <a-drawer
      :open="templateDrawerOpen"
      :width="600"
      :title="null"
      :footer="null"
      :closable="false"
      @close="closeTemplateDetail"
    >
      <a-spin :spinning="templateDrawerLoading">
        <template v-if="activeTemplateRun">
          <div class="detail-header">
            <div>
              <div class="detail-header__title">
                {{ activeTemplateRun.title || activeTemplateRun.template_title }}
              </div>
              <div class="detail-header__meta">
                <span>{{ activeTemplateRun.template_title }}</span>
                <span>·</span>
                <span :title="formatAbsolute(activeTemplateRun.created_at)">
                  {{ formatTime(activeTemplateRun.created_at) }}
                </span>
              </div>
            </div>
            <button type="button" class="detail-close" title="关闭" @click="closeTemplateDetail">
              <X :size="16" />
            </button>
          </div>

          <section v-if="activeTemplateRun.generated_prompt" class="result-section">
            <div class="result-section__title">
              <Sparkles :size="14" />
              <span>生成的提示词</span>
              <button
                type="button"
                class="copy-inline-btn"
                title="复制提示词"
                @click="copyText(activeTemplateRun.generated_prompt, '提示词')"
              >
                <Copy :size="12" />
              </button>
            </div>
            <div class="final-result-card" v-html="renderTemplateRunHtml(activeTemplateRun.generated_prompt)"></div>
          </section>

          <section v-if="activeTemplateRun.ai_result" class="result-section">
            <div class="result-section__title">
              <FileText :size="14" />
              <span>AI 回复结果</span>
              <button
                type="button"
                class="copy-inline-btn"
                title="复制 AI 结果"
                @click="copyText(activeTemplateRun.ai_result, 'AI 结果')"
              >
                <Copy :size="12" />
              </button>
            </div>
            <div class="final-result-card final-result-card--ai" v-html="renderTemplateRunHtml(activeTemplateRun.ai_result)"></div>
          </section>

          <div v-if="!activeTemplateRun.generated_prompt && !activeTemplateRun.ai_result" class="detail-empty">
            这条记录没有保存内容。
          </div>
        </template>
      </a-spin>
    </a-drawer>
  </div>
</template>

<style scoped>
/* ── 布局 ── */
.page-content {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.page-bar {
  display: flex;
  align-items: center;
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

.profile-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  gap: 12px;
}

/* ── 左侧导航 ── */
.profile-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  height: fit-content;
  position: sticky;
  top: 16px;
}

.profile-nav__title {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  padding: 0 8px;
  margin-bottom: 2px;
}

.profile-nav__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
  text-align: left;
  width: 100%;
}

.profile-nav__item:hover {
  background: var(--gray-10);
  color: var(--color-text);
}

.profile-nav__item--active {
  background: var(--main-10);
  color: var(--main-700);
  font-weight: 600;
}

/* ── 右侧内容 ── */
.profile-main {
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
}

.card-block {
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  padding: 20px 24px;
  height: 100%;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--gray-100);
}

.section-title__count {
  margin-left: auto;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-tertiary);
}

/* ── 基础信息 ── */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.info-item {
  padding: 12px 16px;
  background: var(--gray-10);
  border-radius: 6px;
}

.info-item__label {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin-bottom: 4px;
}

.info-item__value {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

.info-item__value--mono {
  font-family: var(--font-mono);
  font-size: 13px;
}

.role-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  background: var(--main-10);
  color: var(--main-700);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

/* ── 空态 ── */
.empty-state {
  padding: 48px 24px;
  text-align: center;
}

.empty-state__icon {
  color: var(--color-text-tertiary);
  margin-bottom: 12px;
  opacity: 0.6;
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
  line-height: 1.6;
}

/* ── 运行记录列表 ── */
.runs-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.run-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--gray-10);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  transition: border-color 0.15s ease, background-color 0.15s ease;
  cursor: pointer;
}

.run-card:hover {
  border-color: var(--main-color);
  background: var(--main-10);
}

.run-card--active {
  border-color: var(--main-color);
  background: var(--main-10);
}

.run-card__main {
  flex: 1;
  min-width: 0;
}

.run-card__header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.run-card__icon {
  color: var(--main-color);
  flex-shrink: 0;
}

.run-card__playbook-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

.run-card__custom-title {
  font-size: 13px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.run-card__meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-tertiary);
  padding-left: 20px;
}

.run-card__final-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  background: var(--color-success-50);
  color: var(--color-success-700);
  border: 1px solid var(--color-success-200);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}

.run-card__prompt-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  background: var(--main-10);
  color: var(--main-700);
  border: 1px solid var(--main-200);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}

.run-card__actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.action-btn-danger {
  color: var(--color-error-600);
}

.action-btn-danger:hover {
  color: var(--color-error-700);
  background: var(--color-error-50);
}

.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

/* ── drawer 详情 ── */
.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--gray-100);
}

.detail-header__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
  word-break: break-all;
}

.detail-header__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-tertiary);
  flex-wrap: wrap;
}

.detail-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.detail-close:hover {
  color: var(--main-color);
  border-color: var(--main-color);
  background: var(--main-10);
}

.detail-meta-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: var(--gray-10);
  border-radius: 6px;
  font-size: 12px;
}

.detail-delete-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: transparent;
  border: 1px solid var(--color-error-300, #fca5a5);
  color: var(--color-error-600);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.detail-delete-btn:hover {
  background: var(--color-error-50);
  border-color: var(--color-error-600);
}

.detail-empty {
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: 13px;
  padding: 32px 0;
}

.result-section {
  margin-bottom: 16px;
}

.result-section__title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--main-700);
  margin-bottom: 8px;
  padding-left: 4px;
}

.copy-inline-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  margin-left: 4px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all 0.15s ease;
  opacity: 0;
}

.result-section:hover .copy-inline-btn {
  opacity: 1;
}

.copy-inline-btn:hover {
  background: var(--main-10);
  border-color: var(--main-200);
  color: var(--main-color);
}

.copy-inline-btn:active {
  background: var(--main-50);
}

.final-result-card {
  background: var(--main-10);
  border: 1px solid var(--main-200);
  border-radius: 8px;
  padding: 14px 16px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-text);
}

.final-result-card :deep(h1) { font-size: 18px; margin: 12px 0 6px; font-weight: 600; }
.final-result-card :deep(h2) {
  font-size: 15px; margin: 12px 0 6px; padding-left: 10px;
  border-left: 3px solid var(--main-color);
  background: var(--main-10);
  border-radius: 2px; font-weight: 600;
}
.final-result-card :deep(h3) { font-size: 14px; margin: 10px 0 4px; font-weight: 600; }
.final-result-card :deep(p) { margin: 0 0 8px; }
.final-result-card :deep(ul),
.final-result-card :deep(ol) { margin: 6px 0 8px; padding-left: 24px; }
.final-result-card :deep(li) { margin: 2px 0; }
.final-result-card :deep(li::marker) { color: var(--main-color); }
.final-result-card :deep(code) {
  font-family: var(--font-mono); font-size: 12.5px; padding: 1px 5px;
  background: var(--gray-0); border: 1px solid var(--gray-150);
  border-radius: 3px; color: var(--main-700);
}
.final-result-card :deep(pre) {
  margin: 6px 0 8px; padding: 10px 12px;
  background: var(--gray-0); border: 1px solid var(--gray-150);
  border-radius: 6px; overflow-x: auto; font-size: 12.5px;
}
.final-result-card :deep(pre code) { padding: 0; background: transparent; border: none; }
.final-result-card :deep(a) {
  color: var(--main-color); text-decoration: none; border-bottom: 1px dashed currentColor;
}
.final-result-card :deep(blockquote) {
  margin: 6px 0 8px; padding: 6px 12px;
  background: var(--gray-0); border-left: 3px solid var(--gray-300);
  color: var(--color-text-secondary); border-radius: 0 4px 4px 0;
}
.final-result-card :deep(strong) { font-weight: 600; }

.final-result-card--ai {
  background: var(--gray-0);
  border-color: var(--gray-200);
}

/* ========== Mobile (<=768px) ========== */
@media (max-width: 768px) {
  .page-content {
    height: auto;
    overflow: visible;
  }

  .page-bar {
    padding: 0 16px;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .profile-layout {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 0 16px 16px;
  }

  .profile-nav {
    flex-direction: row;
    overflow-x: auto;
    gap: 4px;
    padding: 8px;
    position: static;
    -webkit-overflow-scrolling: touch;
  }

  .profile-nav__title {
    display: none;
  }

  .profile-nav__item {
    flex-shrink: 0;
    white-space: nowrap;
    padding: 6px 12px;
  }

  .profile-main {
    overflow-y: visible;
  }

  .drawer-content {
    width: 100% !important;
  }
}
</style>

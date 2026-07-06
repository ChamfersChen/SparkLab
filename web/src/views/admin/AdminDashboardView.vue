<script setup>
/**
 * 数据看板 - 管理员视图
 *
 * 一次性拉取 4 个端点：
 *  - /admin/dashboard/stats         核心指标 + 趋势 + 激活码分布
 *  - /admin/dashboard/top-templates 模板 Top10
 *  - /admin/dashboard/top-playbooks 流程 Top10
 *  - /admin/dashboard/recent-activity 近期发布动态
 *
 * 顶部 Segmented 切换 7d/30d/all，触发 stats / top-* 重拉；
 * recent-activity 不接受 range，仅在首次进入加载。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  BarChart3,
  FileText,
  BookOpen,
  Users,
  Heart,
  KeyRound,
  TrendingUp,
  Calendar,
  Hash,
  Layers
} from 'lucide-vue-next'
import dayjs from 'dayjs'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import { useUserStore } from '@/stores/user'
import {
  getDashboardStats,
  getTopTemplates,
  getTopPlaybooks,
  getRecentActivity
} from '@/apis/dashboard_api'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent
])

const router = useRouter()
const userStore = useUserStore()

if (!userStore.isAdmin) {
  router.replace({ name: 'dashboard' })
}

// ---------------------------------------------------------------------------
// ECharts 颜色
// ---------------------------------------------------------------------------
// ECharts 使用 Canvas/SVG 渲染，不识别 `var(--xxx)` CSS 变量。
// 这里在每次图表 option 计算时通过 getComputedStyle 读取真实色值，
// 这样既跟 design token 保持单一事实源，又能在深色模式下随主题切换。
function readCss(name) {
  if (typeof document === 'undefined') return ''
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

// ----- 顶部时间范围 -----
const range = ref('7d') // 默认近 7 天，最贴近日常运营视角
const rangeOptions = [
  { label: '近 7 天', value: '7d' },
  { label: '近 30 天', value: '30d' },
  { label: '全部', value: 'all' }
]

const isAll = computed(() => range.value === 'all')

// ----- 4 个端点的数据状态 -----
const stats = ref(null)
const topTemplates = ref([])
const topPlaybooks = ref([])
const recentActivity = ref([])

const loading = ref(false)
const activityLoading = ref(false)

async function fetchStats() {
  try {
    stats.value = await getDashboardStats(range.value)
  } catch (e) {
    if (e.response?.status !== 401) message.error('获取指标数据失败')
  }
}

async function fetchTop() {
  try {
    const [tpls, pbs] = await Promise.all([
      getTopTemplates(range.value, 10),
      getTopPlaybooks(range.value, 10)
    ])
    topTemplates.value = tpls.items
    topPlaybooks.value = pbs.items
  } catch (e) {
    if (e.response?.status !== 401) message.error('获取排行榜失败')
  }
}

async function fetchActivity() {
  activityLoading.value = true
  try {
    const res = await getRecentActivity(20)
    recentActivity.value = res.items
  } catch (e) {
    if (e.response?.status !== 401) message.error('获取近期动态失败')
  } finally {
    activityLoading.value = false
  }
}

async function fetchAll() {
  loading.value = true
  try {
    await Promise.all([fetchStats(), fetchTop()])
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.all([fetchAll(), fetchActivity()])
})

watch(range, () => {
  // 切换 range 时重拉 stats + top，recent-activity 不变
  fetchAll()
})

// ----- 指标卡数据 -----
const statCards = computed(() => {
  const s = stats.value
  if (!s) return []
  return [
    {
      key: 'templates',
      label: '已发布模板',
      value: s.templates_published,
      icon: FileText,
      accent: 'var(--chart-palette-1)'
    },
    {
      key: 'playbooks',
      label: '已发布流程',
      value: s.playbooks_published,
      icon: BookOpen,
      accent: 'var(--chart-palette-2)'
    },
    {
      key: 'uses',
      label: isAll.value ? '累计使用' : '区间使用',
      value: s.total_uses,
      icon: TrendingUp,
      accent: 'var(--chart-palette-3)'
    },
    {
      key: 'favorites',
      label: isAll.value ? '累计收藏' : '区间新增收藏',
      value: s.total_favorites,
      icon: Heart,
      accent: 'var(--chart-palette-4)'
    },
    {
      key: 'users',
      label: '用户总数',
      value: s.users_total,
      icon: Users,
      accent: 'var(--chart-palette-6)',
      extra: isAll.value ? null : `+${s.users_new} 新增`
    },
    {
      key: 'codes',
      label: '激活码总量',
      value: s.activation_codes?.total ?? 0,
      icon: KeyRound,
      accent: 'var(--chart-palette-5)'
    }
  ]
})

// ----- 趋势折线图 -----
const usesTrendOption = computed(() => {
  const trend = stats.value?.uses_trend ?? []
  const main = readCss('--main-color')
  return {
    grid: { left: 40, right: 16, top: 24, bottom: 28 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: readCss('--gray-0'),
      borderColor: readCss('--gray-150'),
      textStyle: { color: readCss('--color-text'), fontSize: 12 }
    },
    xAxis: {
      type: 'category',
      data: trend.map((p) => p.date),
      axisLine: { lineStyle: { color: readCss('--gray-100') } },
      axisLabel: { color: readCss('--gray-500'), fontSize: 11 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: readCss('--gray-25') } },
      axisLabel: { color: readCss('--gray-500'), fontSize: 11 }
    },
    series: [
      {
        name: '使用次数',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: trend.map((p) => p.count),
        itemStyle: { color: main },
        lineStyle: { color: main, width: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: main + '40' }, // ~25% alpha (hex)
              { offset: 1, color: main + '00' } // 透明
            ]
          }
        }
      }
    ]
  }
})

const hasTrend = computed(() => (stats.value?.uses_trend?.length ?? 0) > 0)

// ----- 激活码饼图 -----
const codesOption = computed(() => {
  const ac = stats.value?.activation_codes
  if (!ac) return {}
  const data = [
    { name: '未使用', value: ac.unused, itemStyle: { color: readCss('--color-success-500') } },
    { name: '已使用', value: ac.used, itemStyle: { color: readCss('--gray-300') } },
    { name: '已禁用', value: ac.disabled, itemStyle: { color: readCss('--color-error-500') } }
  ]
  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: readCss('--gray-0'),
      borderColor: readCss('--gray-150'),
      textStyle: { color: readCss('--color-text'), fontSize: 12 }
    },
    legend: {
      bottom: 0,
      textStyle: { color: readCss('--color-text-secondary'), fontSize: 12 },
      icon: 'circle'
    },
    series: [
      {
        name: '激活码',
        type: 'pie',
        radius: ['55%', '78%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        label: { show: false },
        labelLine: { show: false },
        data
      }
    ]
  }
})

// ----- Top 模板 / 流程 横向柱状图 -----
// 为了让每个 label（不同模板/流程）有自己颜色，用 chart-palette 轮询。
// 位置 index = 0 分配在原数组未序上（不反转），与原始排名顺序一致。
function buildBarOption(items, valueKey) {
  // 横向柱状图：把数据倒序（用 slice().reverse()），让最高分排最上面
  const data = items.slice().reverse()
  const palette = [
    readCss('--chart-palette-1'),
    readCss('--chart-palette-2'),
    readCss('--chart-palette-3'),
    readCss('--chart-palette-4'),
    readCss('--chart-palette-5'),
    readCss('--chart-palette-6'),
    readCss('--chart-palette-7'),
    readCss('--chart-palette-8')
  ]
  return {
    grid: { left: 8, right: 32, top: 8, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: readCss('--gray-0'),
      borderColor: readCss('--gray-150'),
      textStyle: { color: readCss('--color-text'), fontSize: 12 }
    },
    xAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: readCss('--gray-25') } },
      axisLabel: { color: readCss('--gray-500'), fontSize: 11 }
    },
    yAxis: {
      type: 'category',
      data: data.map((it) => it.title),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: readCss('--color-text'), fontSize: 12, width: 140, overflow: 'truncate' }
    },
    series: [
      {
        type: 'bar',
        // ECharts 的 data 需要用对象数组才能逐项设置颜色
        data: data.map((it, idx) => ({
          value: it[valueKey],
          itemStyle: {
            // 从原数组位置取色，保留排名 → 颜色的直观映射
            color: palette[(items.length - 1 - idx) % palette.length],
            borderRadius: [0, 4, 4, 0]
          }
        })),
        barMaxWidth: 18,
        label: {
          show: true,
          position: 'right',
          color: readCss('--color-text-secondary'),
          fontSize: 12
        }
      }
    ]
  }
}

const topTemplatesOption = computed(() => buildBarOption(topTemplates.value, 'use_count'))
const topPlaybooksOption = computed(() => buildBarOption(topPlaybooks.value, 'use_count'))

// ----- 时间格式 -----
function formatDateTime(v) {
  if (!v) return ''
  const d = dayjs(v)
  return d.isValid() ? d.format('MM-DD HH:mm') : v
}

const ACTIVITY_LABEL = {
  template: { text: '模板', cls: 'status-tag--published' },
  playbook: { text: '流程', cls: 'status-tag--draft' }
}
</script>

<template>
  <div class="page-bg">
    <div class="page-content">
      <!-- 顶部条 -->
      <div class="page-bar">
        <div class="page-bar__title-area">
          <h1 class="page-bar__title">数据看板</h1>
          <p class="page-bar__sub">平台整体运营指标 · 切换时间范围查看近 7 / 30 天或累计数据</p>
        </div>
        <div class="page-bar__actions">
          <a-segmented v-model:value="range" :options="rangeOptions" />
        </div>
      </div>

      <!-- 6 张指标卡 -->
      <a-row :gutter="[16, 16]" style="margin-bottom: 16px">
        <a-col v-for="card in statCards" :key="card.key" :xs="24" :sm="12" :md="8" :lg="8" :xl="4">
          <div class="stat-card panel">
            <div
              class="stat-card__icon"
              :style="{ color: card.accent, background: 'var(--gray-10)' }"
            >
              <component :is="card.icon" :size="20" />
            </div>
            <div class="stat-card__body">
              <div class="stat-card__label">{{ card.label }}</div>
              <div class="stat-card__value">{{ card.value }}</div>
              <div v-if="card.extra" class="stat-card__extra">{{ card.extra }}</div>
            </div>
          </div>
        </a-col>
      </a-row>

      <!-- 趋势 + 激活码分布 -->
      <a-row :gutter="[16, 16]" style="margin-bottom: 16px">
        <a-col :xs="24" :lg="16">
          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">
                <TrendingUp :size="18" class="panel-title-icon" />
                使用趋势
              </h3>
              <span class="panel-header__hint">
                <Calendar :size="14" />
                {{ isAll ? '全量无趋势' : `近 ${range === '7d' ? 7 : 30} 天` }}
              </span>
            </div>
            <div class="chart-host">
              <template v-if="isAll">
                <div class="empty-state" style="padding: 48px 24px">
                  <div class="empty-state__icon"><Hash :size="28" /></div>
                  <h3 class="empty-state__title">全量视图不展示趋势</h3>
                  <p class="empty-state__desc">切换到「近 7 天」或「近 30 天」查看每日使用趋势</p>
                </div>
              </template>
              <template v-else-if="!hasTrend">
                <div class="empty-state" style="padding: 48px 24px">
                  <div class="empty-state__icon"><BarChart3 :size="28" /></div>
                  <h3 class="empty-state__title">暂无趋势数据</h3>
                  <p class="empty-state__desc">区间内尚无使用记录</p>
                </div>
              </template>
              <v-chart v-else class="chart" :option="usesTrendOption" autoresize />
            </div>
          </div>
        </a-col>
        <a-col :xs="24" :lg="8">
          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">
                <KeyRound :size="18" class="panel-title-icon" />
                激活码分布
              </h3>
            </div>
            <div class="chart-host chart-host--pie">
              <v-chart class="chart" :option="codesOption" autoresize />
            </div>
          </div>
        </a-col>
      </a-row>

      <!-- Top10 排行 -->
      <a-row :gutter="[16, 16]" style="margin-bottom: 16px">
        <a-col :xs="24" :lg="12">
          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">
                <FileText :size="18" class="panel-title-icon" />
                模板 Top10
              </h3>
              <span class="panel-header__hint">{{ isAll ? '按累计使用' : '按区间使用' }}</span>
            </div>
            <div class="chart-host chart-host--rank">
              <template v-if="topTemplates.length === 0">
                <div class="empty-state" style="padding: 48px 24px">
                  <div class="empty-state__icon"><FileText :size="28" /></div>
                  <h3 class="empty-state__title">暂无排行数据</h3>
                </div>
              </template>
              <v-chart v-else class="chart" :option="topTemplatesOption" autoresize />
            </div>
          </div>
        </a-col>
        <a-col :xs="24" :lg="12">
          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">
                <BookOpen :size="18" class="panel-title-icon" />
                流程 Top10
              </h3>
              <span class="panel-header__hint">{{ isAll ? '按累计使用' : '按区间使用' }}</span>
            </div>
            <div class="chart-host chart-host--rank">
              <template v-if="topPlaybooks.length === 0">
                <div class="empty-state" style="padding: 48px 24px">
                  <div class="empty-state__icon"><BookOpen :size="28" /></div>
                  <h3 class="empty-state__title">暂无排行数据</h3>
                </div>
              </template>
              <v-chart v-else class="chart" :option="topPlaybooksOption" autoresize />
            </div>
          </div>
        </a-col>
      </a-row>

      <!-- 近期发布动态 -->
      <div class="panel">
        <div class="panel-header">
          <h3 class="panel-title">
            <Layers :size="18" class="panel-title-icon" />
            近期发布动态
          </h3>
          <span class="panel-header__hint">最近 20 条已发布</span>
        </div>
        <a-skeleton v-if="activityLoading" :paragraph="{ rows: 4 }" active />
        <a-empty v-else-if="recentActivity.length === 0" description="暂无发布动态" />
        <a-timeline v-else>
          <a-timeline-item v-for="item in recentActivity" :key="`${item.type}-${item.id}`">
            <div class="activity-row">
              <span class="status-tag" :class="ACTIVITY_LABEL[item.type].cls">
                {{ ACTIVITY_LABEL[item.type].text }}
              </span>
              <span class="activity-row__title">{{ item.title }}</span>
              <span class="activity-row__time">{{ formatDateTime(item.created_at) }}</span>
            </div>
          </a-timeline-item>
        </a-timeline>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ==========================================================================
 * 指标卡
 * - 横向：左侧图标圆形 + 右侧文本
 * - 8px 圆角 + 1px 边框 + 灰 0 背景 = 复用 .panel 风格
 * ========================================================================== */
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease;
}

.stat-card:hover {
  border-color: var(--main-200);
  background: var(--main-10);
}

.stat-card__icon {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-card__body {
  flex: 1;
  min-width: 0;
}

.stat-card__label {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-card__value {
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.stat-card__extra {
  margin-top: 2px;
  font-size: 12px;
  color: var(--color-success-700);
}

/* ==========================================================================
 * 图表容器
 * ========================================================================== */
.chart-host {
  position: relative;
  width: 100%;
  height: 320px;
}

.chart-host--pie {
  height: 320px;
}

.chart-host--rank {
  height: 380px;
}

.chart {
  width: 100%;
  height: 100%;
}

.panel-header__hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-tertiary);
}

/* ==========================================================================
 * 近期动态行
 * ========================================================================== */
.activity-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.activity-row__title {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.activity-row__time {
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
</style>

<script setup>
/**
 * 模板详情预览页（用户端）。
 *
 * 布局参考 docs/design.md：
 * - 顶部：面包屑(返回) + 状态徽标 + 标题 + 描述 + 标签
 * - 中部：五段式段卡(Role / Goal / Input / Output / Example),统一卡片样式
 * - 下方：变量填写区(variable_hints 完整呈现)
 * - 底部：主 CTA「立即使用」+ 次操作「返回模板库」
 *
 * 变量来源 = input 段提取 ∪ variable_hints 的 key,避免 hints 有但 input 没用上时被吞。
 */
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ArrowRight,
  ChevronLeft,
  Clock,
  User,
  FileText,
  Sparkles,
  Target,
  PenLine,
  ListChecks,
  Eye,
} from 'lucide-vue-next'
import { getTemplate } from '@/apis/template_api'
import { extractVariables } from '@/composables/useTemplateVariables'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const template = ref(null)

async function fetchData() {
  loading.value = true
  try {
    const res = await getTemplate(route.params.id)
    template.value = res
  } catch (e) {
    if (e.response?.status === 404) {
      message.error('模板已下架或不存在')
      router.replace({ name: 'templates' })
    } else if (e.response?.status !== 401) {
      message.error('获取模板详情失败')
    }
  } finally {
    loading.value = false
  }
}

function goFill() {
  router.push({ name: 'template-fill', params: { id: route.params.id } })
}

function goBack() {
  router.push({ name: 'templates' })
}

// 变量来源 = input 段 ∪ variable_hints 的 key
const variables = computed(() => {
  if (!template.value) return []
  const inputVars = extractVariables(template.value.input)
  const hintKeys = Object.keys(template.value.variable_hints || {})
  const seen = new Set()
  const merged = []
  for (const v of [...inputVars, ...hintKeys]) {
    if (!seen.has(v)) {
      seen.add(v)
      merged.push({
        name: v,
        hint: template.value.variable_hints?.[v] || null,
        usedInInput: inputVars.includes(v),
      })
    }
  }
  return merged
})

const STATUS_LABEL = {
  draft: { text: '草稿', cls: 'status-tag--draft' },
  published: { text: '已发布', cls: 'status-tag--published' },
  archived: { text: '已归档', cls: 'status-tag--archived' },
}

// 五段式定义,顺序固定;按 data 是否非空决定是否渲染
const sections = computed(() => {
  if (!template.value) return []
  const t = template.value
  return [
    {
      key: 'role',
      icon: User,
      label: 'Role · 角色定义',
      tone: 'role',
      content: t.role,
    },
    {
      key: 'goal',
      icon: Target,
      label: 'Goal · 目标说明',
      tone: 'goal',
      content: t.goal,
    },
    {
      key: 'input',
      icon: PenLine,
      label: 'Input · 变量定义',
      tone: 'input',
      content: t.input,
      note: variables.value.length
        ? `共 ${variables.value.length} 个变量，使用 {{变量名}} 语法`
        : '无变量,可直接生成提示词',
    },
    {
      key: 'output',
      icon: ListChecks,
      label: 'Output · 输出要求',
      tone: 'output',
      content: t.output,
    },
    {
      key: 'example',
      icon: Eye,
      label: 'Example · 示例效果',
      tone: 'example',
      content: t.example,
    },
  ]
})

const createdAtText = computed(() => {
  if (!template.value?.created_at) return ''
  return new Date(template.value.created_at).toLocaleDateString('zh-CN')
})

onMounted(fetchData)
</script>

<template>
  <div class="page-bg">
    <div class="page-content">
      <a-spin :spinning="loading">
        <template v-if="template">
          <!-- 顶部:图标+返回+标题(左),状态+使用量+发布时间(右) -->
          <header class="page-bar page-bar--detail">
            <div class="page-bar__left-group">
              <!-- <FileText :size="20" class="page-bar__icon" /> -->
              <button type="button" class="icon-text-btn" @click="goBack">
                <ChevronLeft :size="16" />
                <span>返回</span>
              </button>
              <h1 class="page-bar__title">{{ template.title }}</h1>
            </div>
            <div class="page-bar__right-meta">
              <span
                v-if="STATUS_LABEL[template.status]"
                class="status-tag"
                :class="STATUS_LABEL[template.status].cls"
              >
                {{ STATUS_LABEL[template.status].text }}
              </span>
              <span class="meta-item">
                <Clock :size="14" />
                {{ template.use_count || 0 }} 次使用
              </span>
              <span v-if="createdAtText" class="meta-item">
                <FileText :size="14" />
                {{ createdAtText }} 发布
              </span>
            </div>
          </header>

          <p v-if="template.description" class="page-bar__sub page-bar__sub--detail">{{ template.description }}</p>

          <!-- <div v-if="template.tags?.length" class="hero-tags">
            <a-tag v-for="t in template.tags" :key="t.id" class="hero-tag">{{ t.name }}</a-tag>
          </div> -->

          <!-- 主操作区(放 hero 之下,内容之上,符合「主操作靠近内容」) -->
          <div class="primary-cta">
            <a-button
              type="primary"
              size="large"
              class="cta-btn"
              @click="goFill"
            >
              <template #icon><Sparkles :size="16" /></template>
              立即使用此模板
            </a-button>
            <span class="cta-hint">
              <ArrowRight :size="14" />
              填写 {{ variables.length }} 个变量,生成可直接粘贴的 Prompt
            </span>
          </div>

          <!-- 主体:左侧内容(五段式 + 变量) -->
          <div class="detail-layout">
            <main class="detail-main">
              <!-- 五段式卡片 -->
              <section
                v-for="s in sections"
                :key="s.key"
                class="section"
                :class="`section--${s.tone}`"
              >
                <h2 class="section-title">
                  <component :is="s.icon" :size="18" class="section-icon" />
                  {{ s.label }}
                </h2>
                <p
                  v-if="s.note"
                  class="section-note"
                >
                  {{ s.note }}
                </p>
                <div class="section-body">
                  <pre class="section-text">{{ s.content }}</pre>
                </div>
              </section>

              <!-- 变量填写提示 -->
              <section v-if="variables.length" class="section section--vars">
                <h2 class="section-title">
                  <FileText :size="18" class="section-icon" />
                  需要填写的信息
                  <span class="section-badge">{{ variables.length }} 项</span>
                </h2>
                <ul class="var-list">
                  <li
                    v-for="v in variables"
                    :key="v.name"
                    class="var-item"
                  >
                    <div class="var-row">
                      <span class="var-name">{{ v.name }}</span>
                      <span
                        v-if="!v.usedInInput"
                        class="var-pill"
                        title="该变量在 Input 段未通过 {{}} 引用,仅作为提示项"
                      >
                        仅提示
                      </span>
                    </div>
                    <p v-if="v.hint" class="var-hint">{{ v.hint }}</p>
                    <p v-else class="var-hint var-hint--empty">
                      填写 {{ v.name }}
                    </p>
                  </li>
                </ul>
              </section>
            </main>
          </div>

          <!-- 底部:次操作(返回) -->
          <footer class="page-footer">
            <a-button @click="goBack">返回模板库</a-button>
          </footer>
        </template>
      </a-spin>
    </div>
  </div>
</template>

<style scoped>
/* ==========================================================================
 * 页面骨架 - 已迁移到全局 .page-bg / .page-content / .page-bar
 * Hero 内部块(.hero-meta / .meta-item / .hero-tags / .hero-tag) 保留在组件内
 * ========================================================================== */

/* ==========================================================================
 * 覆盖全局 .page-content 左右内边距,让内容铺满
 * ========================================================================== */
.page-content {
  padding: 24px 0;
}

.page-bar__title {
  font-size: 20px;
}

/* ==========================================================================
 * 顶部栏
 * ========================================================================== */
.page-bar--detail {
  padding: 0 24px;
}

.page-bar__left-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.page-bar__icon {
  color: var(--main-color);
  flex-shrink: 0;
}

.page-bar__right-meta {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
  color: var(--gray-600);
  font-size: 13px;
}

.page-bar__sub--detail {
  padding: 0 24px;
  margin-bottom: 16px;
}

.hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0 24px;
  margin-bottom: 24px;
}

.hero-tag {
  background: var(--main-10);
  border-color: var(--main-30);
  color: var(--main-700);
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* ==========================================================================
 * 主操作区
 * ========================================================================== */
.primary-cta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  padding: 20px 24px;
  background: var(--main-10);
  border: 1px solid var(--main-30);
  border-left: none;
  border-right: none;
  margin-bottom: 24px;
}

.cta-btn {
  min-width: 200px;
  font-weight: 500;
  box-shadow: 0 1px 2px rgba(59, 130, 246, 0.15);
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.cta-btn:hover {
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.28);
}

.cta-btn:focus-visible {
  outline: 2px solid var(--main-200);
  outline-offset: 2px;
}

.cta-hint {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--gray-600);
  font-size: 13px;
}

/* ==========================================================================
 * 主体布局
 * ========================================================================== */
.detail-layout {
  display: flex;
  gap: 24px;
}

.detail-main {
  flex: 1;
  min-width: 0;
}

/* ==========================================================================
 * 段卡片(五段式 + 变量)
 * ========================================================================== */
.section {
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  padding: 20px 24px;
  margin-bottom: 16px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.section:hover {
  border-color: var(--gray-200);
  box-shadow: var(--shadow-sm);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 8px;
}

.section-icon {
  color: var(--main-color);
  flex-shrink: 0;
}

.section-note {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin: 0 0 12px;
  padding-left: 26px; /* 与图标对齐 */
}

.section-body {
  background: var(--gray-10);
  border: 1px solid var(--gray-100);
  border-radius: 6px;
  padding: 16px;
  margin-top: 4px;
}

.section-text {
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-text);
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

/* 段卡左侧 4px 语义色条,五段差异化(role/goal/input/output/example)
   info=稳定身份 / accent=目标强调 / warning=需填写 / main=主操作 / success=完成参考 */
.section--role { border-left: 4px solid var(--color-info-500); }
.section--goal { border-left: 4px solid var(--color-accent-500); }
.section--input { border-left: 4px solid var(--color-warning-500); }
.section--output { border-left: 4px solid var(--main-color); }
.section--example { border-left: 4px solid var(--color-success-500); }

.section--vars {
  border-left: 4px solid var(--main-500);
}

.section-badge {
  display: inline-flex;
  align-items: center;
  margin-left: auto;
  padding: 2px 8px;
  background: var(--main-10);
  color: var(--main-700);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}

/* ==========================================================================
 * 变量列表
 * ========================================================================== */
.var-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.var-item {
  background: var(--gray-10);
  border: 1px solid var(--gray-100);
  border-radius: 6px;
  padding: 12px 16px;
}

.var-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.var-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  font-family: var(--font-mono);
}

.var-pill {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  background: var(--color-warning-50);
  color: var(--color-warning-900);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
}

.var-hint {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0;
}

.var-hint--empty {
  color: var(--color-text-tertiary);
  font-style: italic;
}

/* ==========================================================================
 * 底部 footer
 * ========================================================================== */
.page-footer {
  display: flex;
  justify-content: center;
  margin-top: 32px;
  padding: 24px 24px 0;
  border-top: 1px solid var(--gray-100);
}

/* ==========================================================================
 * 响应式
 * ========================================================================== */
@media (max-width: 768px) {
  .page-content {
    padding: 16px 0;
  }
  .page-bar--detail {
    padding: 0 16px;
  }
  .page-bar__left-group {
    flex-wrap: wrap;
  }
  .page-bar__right-meta {
    flex-wrap: wrap;
    gap: 8px;
  }
  .page-bar__sub--detail {
    padding: 0 16px;
  }
  .hero-tags {
    padding: 0 16px;
  }
  .section {
    padding: 16px;
    border-radius: 4px;
  }
  .primary-cta {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  .cta-btn {
    min-width: 0;
    width: 100%;
  }
  .page-footer {
    padding: 16px 16px 0;
  }
}
</style>

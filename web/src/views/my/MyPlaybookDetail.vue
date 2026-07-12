<script setup>
/**
 * 我的流程详情页 — 查看和使用自己的私有流程。
 *
 * 参考 playbooks/PlaybookRun.vue 的 UI 风格，但简化为详情页：
 * - 使用 myGetPlaybook API
 * - 返回按钮回到 my-playbooks
 * - 增加编辑按钮
 * - "立即使用"按钮跳转到 playbook-run 页面
 * - 不显示收藏按钮（自己的流程无需收藏）
 */
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ArrowRight, ChevronLeft, Clock, Edit, FileText, Sparkles, Wand2 } from 'lucide-vue-next'
import MarkdownIt from 'markdown-it'
import { myGetPlaybook } from '@/apis/playbook_api'
import { extractVariables } from '@/composables/useTemplateVariables'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const playbook = ref(null)

async function fetchData() {
  loading.value = true
  try {
    const res = await myGetPlaybook(route.params.id)
    playbook.value = res
  } catch (e) {
    if (e.response?.status === 404) {
      message.error('流程不存在或已被删除')
      router.replace({ name: 'my-playbooks' })
    } else if (e.response?.status !== 401) {
      message.error('获取流程详情失败')
    }
  } finally {
    loading.value = false
  }
}

function goRun() {
  router.push({ name: 'playbook-run', params: { id: route.params.id }, query: { from: 'my' } })
}

function goEdit() {
  router.push({ name: 'my-playbook-edit', params: { id: route.params.id } })
}

function goBack() {
  router.push({ name: 'my-playbooks' })
}

const workflowVars = computed(() => {
  if (!playbook.value) return []
  return extractVariables(playbook.value.content)
})

const createdAtText = computed(() => {
  if (!playbook.value?.created_at) return ''
  return new Date(playbook.value.created_at).toLocaleDateString('zh-CN')
})

// Markdown 渲染
const PBKVAR_OPEN = 'PBKVAR'
const PBKVAR_CLOSE = 'PBKVARC'

function escapeAttr(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const md = new MarkdownIt({ html: false, linkify: true, breaks: true }).use((m) => {
  const defaultOpen =
    m.renderer.rules.link_open ||
    function (tokens, idx, options, _env, self) {
      return self.renderToken(tokens, idx, options)
    }
  m.renderer.rules.link_open = function (tokens, idx, options, env, self) {
    const t = tokens[idx]
    t.attrSet('target', '_blank')
    t.attrSet('rel', 'noopener noreferrer')
    return defaultOpen(tokens, idx, options, env, self)
  }
})

const renderedContent = computed(() => {
  if (!playbook.value?.content) return ''
  const varMap = []
  const prepared = (playbook.value.content || '').replace(
    /\{\{(.*?)\}\}/g,
    (_, name) => {
      const trimmed = name.trim()
      varMap.push(trimmed)
      return PBKVAR_OPEN + (varMap.length - 1) + PBKVAR_CLOSE
    }
  )
  const html = md.render(prepared)
  const placeholderRe = new RegExp(PBKVAR_OPEN + '(\\d+)' + PBKVAR_CLOSE, 'g')
  return html.replace(placeholderRe, (_, idx) => {
    const name = varMap[Number(idx)] || ''
    return (
      '<span class="md-var-chip" title="变量 ' +
      escapeAttr(name) +
      '">{{' +
      escapeAttr(name) +
      '}}</span>'
    )
  })
})

onMounted(fetchData)
</script>

<template>
  <div class="page-bg">
    <div class="page-content">
      <a-spin :spinning="loading">
        <template v-if="playbook">
          <header class="page-bar page-bar--detail">
            <div class="page-bar__left-group">
              <button type="button" class="icon-text-btn" @click="goBack">
                <ChevronLeft :size="16" />
                <span>返回</span>
              </button>
              <h1 class="page-bar__title">{{ playbook.title }}</h1>
            </div>
            <div class="page-bar__right-meta">
              <button type="button" class="icon-text-btn" @click="goEdit">
                <Edit :size="14" />
                <span>编辑</span>
              </button>
              <span class="meta-item">
                <Clock :size="14" />
                {{ playbook.use_count || 0 }} 次使用
              </span>
              <span v-if="createdAtText" class="meta-item">
                <FileText :size="14" />
                {{ createdAtText }} 创建
              </span>
            </div>
          </header>

          <p v-if="playbook.description" class="page-bar__sub page-bar__sub--detail">{{ playbook.description }}</p>

          <!-- 主操作区 -->
          <div class="primary-cta">
            <a-button
              type="primary"
              size="large"
              class="cta-btn"
              @click="goRun"
            >
              <template #icon><Sparkles :size="16" /></template>
              立即使用此流程
            </a-button>
            <span class="cta-hint">
              <ArrowRight :size="14" />
              <template v-if="playbook.steps?.length">
                共 {{ playbook.steps.length }} 个步骤，按顺序完成各步提示词
              </template>
              <template v-else>
                暂无步骤，请先编辑添加步骤
              </template>
            </span>
          </div>

          <!-- 步骤概览 -->
          <div v-if="playbook.steps?.length" class="steps-overview">
            <h2 class="section-title">
              <Wand2 :size="18" class="section-icon" />
              流程步骤
              <span class="section-badge">{{ playbook.steps.length }} 步</span>
            </h2>
            <div class="steps-grid">
              <div
                v-for="(s, idx) in playbook.steps"
                :key="s.id || idx"
                class="step-card"
              >
                <span class="step-card__no">{{ idx + 1 }}</span>
                <div class="step-card__body">
                  <h4 class="step-card__name">{{ s.name }}</h4>
                  <p v-if="s.description" class="step-card__desc">{{ s.description }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 流程 Prompt 预览 + 变量 -->
          <div class="detail-layout">
            <main class="detail-main">
              <section v-if="playbook.content" class="section section--preview">
                <h2 class="section-title">
                  <FileText :size="18" class="section-icon" />
                  流程 Prompt 预览
                </h2>
                <div class="section-body">
                  <div class="preview-md" v-html="renderedContent"></div>
                </div>
              </section>

              <section v-if="workflowVars.length" class="section section--vars">
                <h2 class="section-title">
                  <Sparkles :size="18" class="section-icon" />
                  流程参数
                  <span class="section-badge">{{ workflowVars.length }} 项</span>
                </h2>
                <ul class="var-list">
                  <li v-for="v in workflowVars" :key="v" class="var-item">
                    <div class="var-row">
                      <code class="var-name">{{ v }}</code>
                    </div>
                    <p v-if="playbook.variable_hints?.[v]" class="var-hint">{{ playbook.variable_hints[v] }}</p>
                    <p v-else class="var-hint var-hint--empty">填写 {{ v }}</p>
                  </li>
                </ul>
              </section>
            </main>
          </div>

          <footer class="page-footer">
            <a-button @click="goBack">返回我的流程</a-button>
          </footer>
        </template>
      </a-spin>
    </div>
  </div>
</template>

<style scoped>
.page-content {
  padding: 24px 0;
}

.page-bar__title {
  font-size: 20px;
}

.page-bar--detail {
  padding: 0 24px;
}

.page-bar__left-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
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

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.primary-cta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  padding: 20px 24px;
  background: var(--main-10);
  border-top: 1px solid var(--main-30);
  border-bottom: 1px solid var(--main-30);
  margin-bottom: 24px;
}

.cta-btn {
  min-width: 200px;
  font-weight: 500;
  box-shadow: 0 1px 2px rgba(59, 130, 246, 0.15);
  transition: box-shadow 0.15s ease;
}

.cta-btn:hover {
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.28);
}

.cta-hint {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--gray-600);
  font-size: 13px;
}

/* 步骤概览 */
.steps-overview {
  padding: 0 24px;
  margin-bottom: 24px;
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.step-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  transition: border-color 0.15s ease;
}

.step-card:hover {
  border-color: var(--main-color);
}

.step-card__no {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--main-color);
  color: var(--gray-0);
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
  margin-top: 2px;
}

.step-card__body {
  min-width: 0;
  flex: 1;
}

.step-card__name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 2px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-card__desc {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.detail-layout {
  display: flex;
  gap: 24px;
  padding: 0 24px;
}

.detail-main {
  flex: 1;
  min-width: 0;
}

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
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 12px;
}

.section-icon {
  color: var(--main-color);
  flex-shrink: 0;
}

.section-body {
  background: var(--gray-10);
  border: 1px solid var(--gray-100);
  border-radius: 6px;
  padding: 20px 24px;
}

.section--preview {
  border-left: 4px solid var(--main-color);
}

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

.preview-md {
  font-size: 14px;
  line-height: 1.75;
  color: var(--color-text);
}

.preview-md :deep(h1) { font-size: 20px; }
.preview-md :deep(h2) {
  font-size: 17px;
  padding-left: 10px;
  border-left: 3px solid var(--main-color);
  background: linear-gradient(90deg, var(--main-10) 0%, transparent 70%);
  border-radius: 2px;
}
.preview-md :deep(h3) { font-size: 15px; }
.preview-md :deep(h1),
.preview-md :deep(h2),
.preview-md :deep(h3) {
  margin: 18px 0 8px;
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1.4;
}
.preview-md :deep(h1:first-child),
.preview-md :deep(h2:first-child),
.preview-md :deep(h3:first-child) { margin-top: 0; }
.preview-md :deep(p) { margin: 0 0 12px; }
.preview-md :deep(p:last-child) { margin-bottom: 0; }
.preview-md :deep(hr) {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--gray-200), transparent);
  margin: 16px 0;
}
.preview-md :deep(ul),
.preview-md :deep(ol) { margin: 8px 0 12px; padding-left: 24px; }
.preview-md :deep(li) { margin: 4px 0; }
.preview-md :deep(li::marker) { color: var(--main-color); }
.preview-md :deep(strong) { font-weight: 600; }
.preview-md :deep(em) { color: var(--color-text-secondary); font-style: italic; }
.preview-md :deep(code) {
  font-family: var(--font-mono);
  font-size: 12.5px;
  padding: 1px 6px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 4px;
  color: var(--main-700);
}
.preview-md :deep(pre) {
  margin: 8px 0 12px;
  padding: 12px 14px;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12.5px;
  line-height: 1.6;
}
.preview-md :deep(pre code) { padding: 0; background: transparent; border: none; }
.preview-md :deep(a) {
  color: var(--main-color);
  text-decoration: none;
  border-bottom: 1px dashed currentColor;
}
.preview-md :deep(a:hover) { color: var(--main-700); border-bottom-style: solid; }
.preview-md :deep(blockquote) {
  margin: 8px 0 12px;
  padding: 6px 12px;
  background: var(--gray-0);
  border-left: 3px solid var(--gray-300);
  color: var(--color-text-secondary);
  border-radius: 0 4px 4px 0;
}

.preview-md :deep(.md-var-chip) {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  margin: 0 2px;
  background: var(--color-warning-50);
  border: 1px solid var(--color-warning-200);
  color: var(--color-warning-900);
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1.5;
  cursor: default;
  white-space: nowrap;
}

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
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  padding: 1px 8px;
  border-radius: 4px;
  font-family: var(--font-mono);
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

.page-footer {
  display: flex;
  justify-content: center;
  margin-top: 32px;
  padding: 24px 24px 0;
  border-top: 1px solid var(--gray-100);
}

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
  .steps-overview {
    padding: 0 16px;
  }
  .steps-grid {
    grid-template-columns: 1fr;
  }
  .detail-layout {
    padding: 0 16px;
  }
  .page-footer {
    padding: 16px 16px 0;
  }
}
</style>

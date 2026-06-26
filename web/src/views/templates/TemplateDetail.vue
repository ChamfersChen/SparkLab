<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ArrowRight, Star, Clock, FileText, Eye } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { getTemplate } from '@/apis/template_api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const template = ref(null)

async function fetchData() {
  loading.value = true
  try {
    const res = await getTemplate(route.params.id)
    template.value = res
  } catch (e) {
    if (e.response?.status === 404) {
      message.error('模板不存在')
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

// 从 input 段提取变量
const variables = computed(() => {
  if (!template.value) return []
  const regex = /\{\{(.*?)\}\}/g
  const vars = []
  const seen = new Set()
  let match
  while ((match = regex.exec(template.value.input)) !== null) {
    if (!seen.has(match[1])) {
      seen.add(match[1])
      vars.push({
        name: match[1],
        hint: template.value.variable_hints?.[match[1]] || null
      })
    }
  }
  return vars
})

onMounted(fetchData)
</script>

<template>
  <div class="page">
    <div class="content">
      <a-spin :spinning="loading">
        <template v-if="template">
          <a-page-header
            title="返回模板库"
            @back="router.push({ name: 'templates' })"
          />

          <div class="detail-layout">
            <!-- 左侧主信息 -->
            <div class="detail-main">
              <h1 class="detail-title">{{ template.title }}</h1>
              <p class="detail-desc">{{ template.description }}</p>

              <!-- 标签 -->
              <div class="detail-tags">
                <a-tag v-for="t in template.tags" :key="t.id" color="blue">{{ t.name }}</a-tag>
              </div>

              <!-- 需要填写的信息 -->
              <section class="section">
                <h2 class="section-title">
                  <FileText :size="18" />
                  需要填写的信息
                </h2>
                <div v-if="variables.length" class="variable-list">
                  <div v-for="v in variables" :key="v.name" class="variable-item">
                    <div class="var-name">{{ v.name }}</div>
                    <div v-if="v.hint" class="var-hint">{{ v.hint }}</div>
                    <div v-else class="var-hint muted">填写 {{ v.name }}</div>
                  </div>
                </div>
                <div v-else class="no-vars">此模板无需填写变量，可直接生成提示词。</div>
              </section>

              <!-- 示例效果 -->
              <section class="section">
                <h2 class="section-title">
                  <Eye :size="18" />
                  示例效果
                </h2>
                <div class="example-box">
                  <pre class="example-text">{{ template.example }}</pre>
                </div>
              </section>
            </div>

            <!-- 右侧边栏 -->
            <div class="detail-sidebar">
              <div class="sidebar-card">
                <div class="sidebar-stat">
                  <Clock :size="16" />
                  <span>{{ template.use_count || 0 }} 次使用</span>
                </div>
                <a-button type="primary" size="large" block class="cta-btn" @click="goFill">
                  <template #icon><ArrowRight :size="16" /></template>
                  填写信息生成提示词
                </a-button>
              </div>
            </div>
          </div>
        </template>
      </a-spin>
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
  padding: 0 32px 64px;
}

.detail-layout {
  display: flex;
  gap: 32px;
  margin-top: 8px;
}

.detail-main {
  flex: 1;
  min-width: 0;
}

.detail-sidebar {
  width: 300px;
  flex-shrink: 0;
}

.detail-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 8px;
}

.detail-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0 0 16px;
}

.detail-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}

.section {
  margin-bottom: 24px;
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

.variable-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.variable-item {
  background: var(--gray-0);
  border: 1px solid var(--gray-50);
  border-radius: 8px;
  padding: 12px 16px;
}

.var-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
}

.var-hint {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.var-hint.muted {
  color: var(--color-text-tertiary);
  font-style: italic;
}

.no-vars {
  font-size: 14px;
  color: var(--color-text-secondary);
  padding: 16px;
  background: var(--gray-0);
  border-radius: 8px;
  border: 1px dashed var(--gray-50);
}

.example-box {
  background: var(--gray-0);
  border: 1px solid var(--gray-50);
  border-radius: 8px;
  padding: 16px;
}

.example-text {
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-text);
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

/* Sidebar */
.sidebar-card {
  background: var(--gray-0);
  border: 1px solid var(--gray-50);
  border-radius: 10px;
  padding: 20px;
  position: sticky;
  top: 88px;
}

.sidebar-stat {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 16px;
}

.cta-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

@media (max-width: 768px) {
  .detail-layout {
    flex-direction: column;
  }
  .detail-sidebar {
    width: 100%;
  }
  .content {
    padding: 0 16px 48px;
  }
}
</style>

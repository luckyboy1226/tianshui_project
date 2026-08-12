<template>
  <ErrorBoundary>
    <div class="feedback-page-apple">
      <div class="feedback-layout-apple">
        <section class="feedback-card-apple form-panel-apple">
          <RouterLink to="/" class="feedback-back-link" title="返回主界面">
            <ArrowLeft class="back-home-icon" />
            <span>主界面</span>
          </RouterLink>

          <div class="page-heading-apple">
            <span class="heading-kicker-apple">公众参与</span>
            <h1 class="title-apple">民众意见反馈</h1>
            <p class="subtitle-apple">请留下你看到的问题、建议或数据纠错信息，我们会认真处理。</p>
          </div>

          <el-form :model="form" :rules="rules" ref="formRef" label-position="top" class="form-apple">
            <el-form-item label="反馈类型" prop="category">
              <el-select v-model="form.category" placeholder="选择一种类型">
                <el-option label="功能建议" value="suggestion" />
                <el-option label="问题报告" value="bug" />
                <el-option label="数据纠错" value="data_issue" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>

            <el-form-item label="标题" prop="title">
              <el-input v-model="form.title" maxlength="80" show-word-limit placeholder="一句话概述你的反馈" />
            </el-form-item>

            <el-form-item label="详细描述" prop="content">
              <el-input
                v-model="form.content"
                type="textarea"
                :rows="7"
                maxlength="1000"
                show-word-limit
                placeholder="请描述现象、期望、复现步骤或截图链接等"
              />
            </el-form-item>

            <el-form-item label="联系方式（可选）" prop="contact">
              <el-input v-model="form.contact" placeholder="邮箱/电话/微信（可选）" />
            </el-form-item>

            <div class="actions-apple">
              <el-button :loading="submitting" type="primary" size="large" @click="onSubmit">
                <el-icon><Promotion /></el-icon>
                <span>提交反馈</span>
              </el-button>
              <el-button size="large" @click="onReset">
                <el-icon><RefreshLeft /></el-icon>
                <span>重置</span>
              </el-button>
            </div>
          </el-form>

          <p class="privacy-apple">
            提交即表示你同意我们将信息用于产品改进。联系方式仅用于必要沟通。
          </p>
        </section>

        <aside class="feedback-side-apple">
          <div class="side-summary-apple">
            <div>
              <span class="heading-kicker-apple">管理</span>
              <h2 class="side-title-apple">反馈记录</h2>
              <p class="side-copy-apple">记录默认收起，避免干扰提交流程；需要查看时再打开。</p>
            </div>
            <div class="record-count-apple">
              <strong>{{ feedbackRecords.length }}</strong>
              <span>条记录</span>
            </div>
          </div>

          <div class="side-actions-apple">
            <el-button type="primary" class="records-open-button" @click="openRecordsDrawer">
              <el-icon><Tickets /></el-icon>
              <span>查看反馈记录</span>
            </el-button>
            <el-button :loading="loadingRecords" @click="loadFeedbackRecords">
              <el-icon><Refresh /></el-icon>
              <span>刷新</span>
            </el-button>
          </div>

          <div class="side-note-apple">
            <el-icon><InfoFilled /></el-icon>
            <span>打开记录后可删除单条反馈，也可以一键清空全部记录。</span>
          </div>
        </aside>
      </div>

      <el-drawer
        v-model="recordsDrawerVisible"
        direction="rtl"
        size="520px"
        class="records-drawer-apple"
        :with-header="false"
        destroy-on-close
      >
        <div class="drawer-shell-apple">
          <header class="drawer-header-apple">
            <div>
              <span class="heading-kicker-apple">已收到</span>
              <h2 class="records-title-apple">反馈记录</h2>
              <p class="drawer-subtitle-apple">共 {{ feedbackRecords.length }} 条民众意见</p>
            </div>
            <el-button circle @click="recordsDrawerVisible = false" aria-label="关闭反馈记录">
              <el-icon><Close /></el-icon>
            </el-button>
          </header>

          <div class="drawer-toolbar-apple">
            <el-button :loading="loadingRecords" @click="loadFeedbackRecords">
              <el-icon><Refresh /></el-icon>
              <span>刷新</span>
            </el-button>
            <el-popconfirm
              width="220"
              title="确定清空所有反馈记录吗？"
              confirm-button-text="清空"
              cancel-button-text="取消"
              @confirm="clearRecords"
            >
              <template #reference>
                <el-button
                  type="danger"
                  plain
                  :loading="clearingRecords"
                  :disabled="feedbackRecords.length === 0"
                >
                  <el-icon><Delete /></el-icon>
                  <span>清空</span>
                </el-button>
              </template>
            </el-popconfirm>
          </div>

          <div v-if="loadingRecords" class="records-loading-apple">
            <el-skeleton :rows="4" animated />
          </div>

          <el-empty
            v-else-if="feedbackRecords.length === 0"
            description="暂无反馈记录"
            class="records-empty-apple"
          />

          <div v-else class="records-list-apple">
            <article v-for="item in feedbackRecords" :key="item.id" class="record-item-apple">
              <div class="record-title-row-apple">
                <h3 class="record-title-text-apple">{{ item.title }}</h3>
                <el-tag size="small" effect="plain" :type="tagTypeMap[item.category] || 'info'">
                  {{ item.category_display || categoryMap[item.category] || item.category }}
                </el-tag>
              </div>
              <p class="record-content-apple">{{ item.content }}</p>
              <div class="record-meta-apple">
                <span>{{ formatDate(item.created_at) }}</span>
                <span v-if="item.contact">联系方式：{{ item.contact }}</span>
              </div>
              <div class="record-actions-apple">
                <el-popconfirm
                  width="220"
                  title="确定删除这条反馈吗？"
                  confirm-button-text="删除"
                  cancel-button-text="取消"
                  @confirm="deleteRecord(item.id)"
                >
                  <template #reference>
                    <el-button text type="danger" :loading="deletingRecordId === item.id">
                      <el-icon><Delete /></el-icon>
                      <span>删除</span>
                    </el-button>
                  </template>
                </el-popconfirm>
              </div>
            </article>
          </div>
        </div>
      </el-drawer>
    </div>
  </ErrorBoundary>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  Close,
  Delete,
  InfoFilled,
  Promotion,
  Refresh,
  RefreshLeft,
  Tickets
} from '@element-plus/icons-vue'
import ErrorBoundary from '../components/Common/ErrorBoundary.vue'
import { feedbackService } from '../services/api.js'

const formRef = ref(null)
const submitting = ref(false)
const loadingRecords = ref(false)
const clearingRecords = ref(false)
const deletingRecordId = ref('')
const recordsDrawerVisible = ref(false)
const feedbackRecords = ref([])
const form = ref({
  category: '',
  title: '',
  content: '',
  contact: ''
})

const categoryMap = {
  suggestion: '功能建议',
  bug: '问题报告',
  data_issue: '数据纠错',
  other: '其他'
}

const tagTypeMap = {
  suggestion: '',
  bug: 'danger',
  data_issue: 'warning',
  other: 'info'
}

const rules = {
  category: [
    { required: true, message: '请选择反馈类型', trigger: 'change' }
  ],
  title: [
    { required: true, message: '请输入标题', trigger: 'blur' },
    { min: 4, max: 80, message: '标题长度 4-80 字', trigger: 'blur' }
  ],
  content: [
    { required: true, message: '请输入详细描述', trigger: 'blur' },
    { min: 10, max: 1000, message: '描述长度 10-1000 字', trigger: 'blur' }
  ]
}

function onReset() {
  form.value = { category: '', title: '', content: '', contact: '' }
  formRef.value?.clearValidate()
}

function normalizeFeedbackList(response) {
  if (Array.isArray(response)) return response
  if (Array.isArray(response?.results)) return response.results
  if (Array.isArray(response?.data)) return response.data
  return []
}

function formatDate(value) {
  if (!value) return '时间未知'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

async function loadFeedbackRecords() {
  try {
    loadingRecords.value = true
    const response = await feedbackService.getList()
    feedbackRecords.value = normalizeFeedbackList(response)
  } catch (e) {
    const message = e.response?.data?.error || e.response?.data?.detail || '反馈记录加载失败'
    ElMessage.error(message)
  } finally {
    loadingRecords.value = false
  }
}

async function openRecordsDrawer() {
  recordsDrawerVisible.value = true
  await loadFeedbackRecords()
}

async function deleteRecord(id) {
  try {
    deletingRecordId.value = id
    await feedbackService.delete(id)
    feedbackRecords.value = feedbackRecords.value.filter((item) => item.id !== id)
    ElMessage.success('反馈记录已删除')
  } catch (e) {
    const message = e.response?.data?.error || e.response?.data?.detail || '删除失败，请稍后重试'
    ElMessage.error(message)
  } finally {
    deletingRecordId.value = ''
  }
}

async function clearRecords() {
  try {
    clearingRecords.value = true
    await feedbackService.clear()
    feedbackRecords.value = []
    ElMessage.success('反馈记录已清空')
  } catch (e) {
    const message = e.response?.data?.error || e.response?.data?.detail || '清空失败，请稍后重试'
    ElMessage.error(message)
  } finally {
    clearingRecords.value = false
  }
}

function toBackendPayload(v) {
  return {
    category: v.category,
    title: v.title,
    content: v.content,
    contact: v.contact
  }
}

function onSubmit() {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      submitting.value = true
      const payload = toBackendPayload(form.value)
      await feedbackService.create(payload)
      ElMessage.success('感谢你的反馈，我们已收到！')
      onReset()
      await loadFeedbackRecords()
    } catch (e) {
      const message = e.response?.data?.error || e.response?.data?.detail || '提交失败，请稍后重试'
      ElMessage.error(message)
    } finally {
      submitting.value = false
    }
  })
}

onMounted(() => {
  loadFeedbackRecords()
})
</script>

<style scoped>
.feedback-page-apple {
  min-height: 100vh;
  overflow-y: auto;
  background: #f4f7fa;
  padding: 24px 20px;
}

.feedback-layout-apple {
  width: min(1120px, 100%);
  min-height: calc(100vh - 64px);
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(460px, 760px) minmax(300px, 360px);
  gap: 24px;
  align-items: start;
}

.feedback-card-apple,
.feedback-side-apple {
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid #dbe6f0;
  border-radius: 8px;
  box-shadow: 0 14px 34px rgba(30, 50, 70, 0.08);
}

.form-panel-apple {
  padding: 28px 30px 26px;
}

.feedback-side-apple {
  position: sticky;
  top: 32px;
  padding: 24px;
}

.page-heading-apple {
  margin-bottom: 28px;
}

.feedback-back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 18px;
  padding: 6px 10px;
  border-radius: 8px;
  color: #315f8c;
  background: #eef5fb;
  text-decoration: none;
  font-size: 12px;
  font-weight: 600;
  transition: background 0.2s ease, transform 0.2s ease;
}

.feedback-back-link:hover {
  background: #e4eff9;
  transform: translateY(-1px);
}

.back-home-icon {
  width: 14px;
  height: 14px;
}

.heading-kicker-apple {
  display: inline-flex;
  margin-bottom: 8px;
  color: #315f8c;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
}

.title-apple {
  margin: 0 0 8px;
  font-size: 30px;
  line-height: 1.2;
  font-weight: 750;
  letter-spacing: 0;
  color: #26384a;
}

.subtitle-apple,
.side-copy-apple,
.drawer-subtitle-apple {
  margin: 0;
  color: #667789;
  font-size: 14px;
  line-height: 1.65;
}

.form-apple :deep(.el-form-item) {
  margin-bottom: 22px;
}

.form-apple :deep(.el-form-item__label) {
  color: #26384a;
  font-weight: 700;
}

.form-apple :deep(.el-input__wrapper),
.form-apple :deep(.el-textarea__inner),
.form-apple :deep(.el-select__wrapper) {
  border-radius: 7px;
  box-shadow: 0 0 0 1px #dbe3ec inset;
}

.form-apple :deep(.el-textarea__inner) {
  resize: vertical;
}

.actions-apple {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 6px;
}

.actions-apple :deep(.el-button),
.side-actions-apple :deep(.el-button),
.drawer-toolbar-apple :deep(.el-button) {
  border-radius: 7px;
}

.privacy-apple {
  margin: 22px 0 0;
  color: #8a98a8;
  font-size: 12px;
  line-height: 1.7;
}

.side-summary-apple {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 18px;
  align-items: start;
  padding-bottom: 18px;
  border-bottom: 1px solid #e7eef5;
}

.side-title-apple,
.records-title-apple {
  margin: 0 0 8px;
  color: #26384a;
  font-size: 22px;
  line-height: 1.25;
}

.record-count-apple {
  min-width: 76px;
  padding: 12px 10px;
  border: 1px solid #dbe6f0;
  border-radius: 8px;
  background: #f8fbfd;
  text-align: center;
}

.record-count-apple strong {
  display: block;
  color: #315f8c;
  font-size: 28px;
  line-height: 1;
}

.record-count-apple span {
  display: block;
  margin-top: 6px;
  color: #667789;
  font-size: 12px;
}

.side-actions-apple {
  display: grid;
  gap: 10px;
  margin-top: 22px;
}

.records-open-button {
  width: 100%;
}

.side-actions-apple :deep(.el-button) {
  height: 40px;
  font-weight: 600;
}

.side-note-apple {
  display: flex;
  gap: 8px;
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 8px;
  background: #eef4f9;
  color: #5f7f9d;
  font-size: 12px;
  line-height: 1.6;
}

.side-note-apple .el-icon {
  margin-top: 2px;
  flex-shrink: 0;
}

.drawer-shell-apple {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  background: #f4f7fa;
}

.drawer-header-apple,
.drawer-toolbar-apple {
  background: #ffffff;
  border-bottom: 1px solid #dbe6f0;
}

.drawer-header-apple {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 24px;
}

.drawer-toolbar-apple {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 24px;
}

.records-loading-apple,
.records-empty-apple {
  padding: 28px 24px;
}

.records-list-apple {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 12px;
  padding: 18px 24px 24px;
  overflow-y: auto;
}

.record-item-apple {
  padding: 16px;
  border: 1px solid #dbe6f0;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 6px 16px rgba(30, 50, 70, 0.06);
}

.record-title-row-apple {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.record-title-text-apple {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: #26384a;
  font-size: 16px;
  font-weight: 750;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-content-apple {
  margin: 10px 0 12px;
  color: #425466;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}

.record-meta-apple {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  color: #8a98a8;
  font-size: 12px;
}

.record-actions-apple {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

:deep(.records-drawer-apple .el-drawer__body) {
  padding: 0;
}

@media (max-width: 900px) {
  .feedback-page-apple {
    padding: 18px;
  }

  .feedback-layout-apple {
    min-height: auto;
    grid-template-columns: 1fr;
  }

  .feedback-side-apple {
    position: static;
  }
}

@media (max-width: 640px) {
  .form-panel-apple,
  .feedback-side-apple {
    padding: 22px 16px;
  }

  .title-apple {
    font-size: 26px;
  }

  .actions-apple,
  .drawer-toolbar-apple {
    align-items: stretch;
    flex-direction: column;
  }

  .actions-apple :deep(.el-button),
  .drawer-toolbar-apple :deep(.el-button) {
    width: 100%;
    margin-left: 0;
  }

  :deep(.records-drawer-apple.el-drawer) {
    width: min(100vw, 520px) !important;
  }

  .drawer-header-apple,
  .drawer-toolbar-apple,
  .records-list-apple {
    padding-left: 16px;
    padding-right: 16px;
  }
}
</style>

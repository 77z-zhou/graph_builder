<template>
  <div class="chat-panel">
    <!-- Chat Header -->
    <div class="chat-header">
      <div class="chat-title">
        <el-icon size="20"><ChatDotRound /></el-icon>
        <span>Graph RAG Chat</span>
      </div>
      <div class="chat-subtitle">与知识图谱对话</div>
      <div class="chat-time">{{ currentTime }}</div>
    </div>

    <!-- Chat Configuration -->
    <div class="chat-config">
      <div class="config-item">
        <label>Agent 模式</label>
        <el-select v-model="chatMode" size="small" style="flex: 1;">
          <el-option label="Cypher Generate" value="cypher" />
          <el-option label="Graph Retriever(Vector + Fulltext)" value="retriever" />
        </el-select>
      </div>

      <div class="config-item">
        <label>选择文档</label>
        <el-select
          v-model="selectedDocument"
          size="small"
          placeholder="选择要对话的文档"
          style="flex: 1;"
          clearable
          :disabled="chatMode === 'cypher'"
        >
          <el-option
            v-for="doc in documents"
            :key="doc.fileName"
            :label="doc.fileName"
            :value="doc.fileName"
          >
            <div class="document-option">
              <span>{{ doc.fileName }}</span>
              <el-tag size="small" :type="getStatusType(doc.status)">
                {{ doc.status }}
              </el-tag>
            </div>
          </el-option>
        </el-select>
      </div>
    </div>

    <!-- Chat Messages -->
    <div class="chat-messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="empty-state">
        <el-icon size="48" color="#909399"><ChatLineRound /></el-icon>
        <p>开始对话吧！</p>
        <p class="hint">
          <template v-if="chatMode === 'cypher'">
            Cypher Generate 模式：直接生成 Cypher 查询语句
          </template>
          <template v-else>
            Graph Retriever(Vector + Fulltext) 模式：基于向量检索和全文检索的混合搜索
          </template>
        </p>
      </div>

      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['message', message.role]"
      >
        <div class="message-content">{{ message.content }}</div>
        <div class="message-time">{{ message.time }}</div>
      </div>

      <div v-if="loading" class="message assistant">
        <div class="message-content">
          <el-icon class="is-loading"><Loading /></el-icon>
          正在思考...
        </div>
      </div>
    </div>

    <!-- Chat Input -->
    <div class="chat-input-area">
      <div class="input-info">
        <span v-if="chatMode === 'cypher'" class="mode-badge cypher-badge">
          <el-icon><ChatDotRound /></el-icon>
          Cypher Generate 模式
        </span>
        <span v-else class="mode-badge retriever-badge">
          <el-icon><Document /></el-icon>
          Graph Retriever(Vector + Fulltext) 模式
        </span>

        <span v-if="selectedDocument && chatMode === 'retriever'" class="selected-doc">
          <el-icon><Document /></el-icon>
          {{ selectedDocument }}
        </span>
      </div>
      <div class="chat-input-wrapper">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="3"
          placeholder="输入问题..."
          @keydown.enter.exact.prevent="sendMessage"
          @keydown.enter.shift.prevent
          :disabled="loading"
        />
        <el-button
          type="primary"
          :loading="loading"
          :disabled="!inputText.trim()"
          @click="sendMessage"
          size="large"
        >
          <el-icon><Promotion /></el-icon>
          发送
        </el-button>
      </div>
      <div class="input-hint">按 Enter 发送，Shift + Enter 换行</div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, ChatLineRound, Loading, Document, Warning, Promotion } from '@element-plus/icons-vue'
import { chatApi } from '@/api/graph'
import { useDocumentStore } from '@/stores/documents'

const documentStore = useDocumentStore()
const { documents } = documentStore

const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const messagesRef = ref(null)
const currentTime = ref('')
const chatMode = ref('cypher')
const selectedDocument = ref('')

let timeInterval = null

const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN')
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  // Add user message
  messages.value.push({
    role: 'user',
    content: text,
    time: new Date().toLocaleTimeString('zh-CN')
  })

  inputText.value = ''
  loading.value = true
  await scrollToBottom()

  try {
    // Clear document selection when using cypher mode
    const docToSend = chatMode.value === 'cypher' ? '' : selectedDocument.value
    const response = await chatApi(text, chatMode.value, docToSend)

    messages.value.push({
      role: 'assistant',
      content: response.response || '处理完成',
      time: new Date().toLocaleTimeString('zh-CN')
    })

    await scrollToBottom()
  } catch (error) {
    ElMessage.error('发送失败: ' + error.message)
    messages.value.push({
      role: 'assistant',
      content: '抱歉，发生了错误: ' + error.message,
      time: new Date().toLocaleTimeString('zh-CN')
    })
    await scrollToBottom()
  } finally {
    loading.value = false
  }
}

const getStatusType = (status) => {
  const typeMap = {
    'Completed': 'success',
    'Processing': 'warning',
    'Failed': 'danger',
    'New': 'info'
  }
  return typeMap[status] || 'info'
}

// Watch mode changes to clear document selection when switching to cypher mode
const handleModeChange = () => {
  if (chatMode.value === 'cypher') {
    selectedDocument.value = ''
  }
}

// Add watcher for chatMode
watch(chatMode, handleModeChange)

onMounted(() => {
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
  documentStore.loadDocuments()

  // Listen for model changes
  window.addEventListener('model-change', (e) => {
    console.log('Model changed to:', e.detail)
  })
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-header {
  padding: 1.5rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
  background: var(--background);
  transition: all 0.3s;
}

.chat-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 600;
  margin-bottom: 0.35rem;
  font-size: 1.1rem;
}

.chat-subtitle {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-weight: 400;
}

.chat-time {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-top: 0.6rem;
  opacity: 0.8;
}

.chat-config {
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
  background: var(--surface);
  display: flex;
  flex-direction: column;
  gap: 1rem;
  transition: all 0.3s;
}

.config-item {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.config-item label {
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  min-width: 90px;
  letter-spacing: 0.2px;
}

.config-item :deep(.el-select) {
  font-size: 0.95rem;
}

.config-item :deep(.el-select .el-input__wrapper) {
  padding: 0.5rem 1rem;
  font-size: 0.95rem;
  border-radius: 8px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
}

.config-item :deep(.el-select:hover .el-input__wrapper) {
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.15);
}

.config-item :deep(.el-select .el-input__wrapper.is-focus) {
  box-shadow: 0 2px 10px rgba(102, 126, 234, 0.25);
}

.document-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  font-size: 0.95rem;
  padding: 0.35rem 0;
}

.document-option :deep(.el-tag) {
  font-size: 0.85rem;
  padding: 0.25rem 0.625rem;
  border-radius: 6px;
  font-weight: 500;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  background: var(--background);
  transition: all 0.3s;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-secondary);
  gap: 0.75rem;
  padding: 2rem;
}

.empty-state .hint {
  font-size: 0.9rem;
  opacity: 0.9;
  line-height: 1.6;
  text-align: center;
  max-width: 320px;
  color: var(--text-secondary);
  font-weight: 400;
}

.message {
  max-width: 85%;
  padding: 1rem 1.25rem;
  border-radius: 16px;
  animation: messageIn 0.3s ease-out;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
  line-height: 1.6;
}

@keyframes messageIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message.user {
  align-self: flex-end;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.message.user:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}

.message.assistant {
  align-self: flex-start;
  background: var(--surface);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.message.assistant:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  border-color: var(--border-color);
}

.message-content {
  word-break: break-word;
  white-space: pre-wrap;
  font-size: 0.95rem;
  line-height: 1.7;
  font-weight: 400;
}

.message-time {
  font-size: 0.75rem;
  opacity: 0.7;
  margin-top: 0.5rem;
  font-weight: 400;
}

.chat-input-area {
  padding: 1.25rem 1.5rem;
  border-top: 1px solid var(--border-color);
  background: var(--surface);
  transition: all 0.3s;
}

.input-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  background: var(--background);
  border-radius: 10px;
  font-size: 0.9rem;
  border: 1px solid var(--border-color);
}

.selected-doc {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--primary-color);
  font-weight: 500;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.9rem;
}

.mode-badge {
  padding: 0.4rem 0.875rem;
  border-radius: 16px;
  font-size: 0.85rem;
  font-weight: 500;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.cypher-badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
}

.retriever-badge {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(240, 147, 251, 0.4);
}

.chat-input-wrapper {
  display: flex;
  gap: 0.75rem;
}

.chat-input-wrapper :deep(.el-textarea__inner) {
  border-radius: 12px;
  padding: 0.875rem 1rem;
  font-size: 0.95rem;
  line-height: 1.6;
  resize: none;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
  transition: all 0.3s;
  border: 1px solid var(--border-color);
}

.chat-input-wrapper :deep(.el-textarea__inner:focus) {
  box-shadow: 0 2px 10px rgba(102, 126, 234, 0.2);
  border-color: var(--primary-color);
}

.chat-input-wrapper :deep(.el-button) {
  border-radius: 12px;
  padding: 0 1.5rem;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  transition: all 0.3s;
}

.chat-input-wrapper :deep(.el-button:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.input-hint {
  font-size: 0.8rem;
  color: var(--text-secondary);
  text-align: center;
  margin-top: 0.75rem;
  opacity: 0.85;
  font-weight: 400;
}

/* Dark theme adjustments for Element Plus components */
:deep(.el-select__placeholder) {
  color: var(--text-secondary);
}

:deep(.el-select-dropdown) {
  background: #1a1a1d !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

:deep(.el-select-dropdown__item) {
  color: #ffffff;
}

:deep(.el-select-dropdown__item:hover) {
  background: rgba(255, 255, 255, 0.08);
}

:deep(.el-select-dropdown__item.is-selected) {
  color: #ffffff;
  background: rgba(102, 126, 234, 0.2);
}

:deep(.el-tag) {
  border-color: transparent;
}

:deep(.el-icon) {
  color: var(--text-primary);
}

/* Ensure all dropdown components are dark */
:deep(.el-select-dropdown__list) {
  background: #1a1a1d !important;
}

:deep(.el-select-dropdown__wrap) {
  background: #1a1a1d !important;
}

:deep(.el-select-dropdown .el-scrollbar__wrap) {
  background: #1a1a1d !important;
}

:deep(.el-select-dropdown .el-scrollbar__view) {
  background: #1a1a1d !important;
}
</style>

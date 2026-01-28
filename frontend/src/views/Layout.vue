<template>
  <el-container class="app-container" :class="{ dark: isDark }">
    <!-- Header -->
    <el-header class="app-header">
      <div class="header-left">
        <div class="logo">
          <span class="logo-icon">🧠</span>
          <span class="logo-text">Knowledge Graph Builder</span>
        </div>

        <!-- Neo4j Connection Button -->
        <el-button
          :type="isNeo4jConnected ? 'success' : 'primary'"
          :icon="Connection"
          size="default"
          @click="testNeo4jConnection"
          :loading="connectingNeo4j"
        >
          {{ connectingNeo4j ? '连接中' : isNeo4jConnected ? '已连接' : '连接Neo4j' }}
        </el-button>
      </div>

      <div class="header-actions">
        <!-- Model Selection -->
        <div class="model-selector">
          <span class="model-label">模型选择(图构建&Chat)</span>
          <el-select
            v-model="selectedModel"
            placeholder="选择模型"
            size="large"
            style="width: 220px;"
            @change="handleModelChange"
          >
            <template #prefix>
              <el-icon><Cpu /></el-icon>
            </template>
            <el-option label="DeepSeek Chat" value="deepseek-deepseek-chat" />
            <el-option label="Qwen 3 Max" value="dashscope-qwen3-max" />
          </el-select>
        </div>

        <!-- Theme Toggle -->
        <el-button
          circle
          @click="toggleTheme"
          :icon="isDark ? Sunny : Moon"
          size="large"
          class="theme-btn"
        />
      </div>
    </el-header>

    <el-container class="main-container">
      <!-- Main Content -->
      <el-main class="content-area">
        <router-view />
      </el-main>

      <!-- Sidebar Chat -->
      <el-aside width="420px" class="chat-sidebar">
        <ChatPanel />
      </el-aside>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Moon, Sunny, Cpu, Connection } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ChatPanel from '@/components/ChatPanel.vue'
import { useNeo4jStore } from '@/stores/neo4j'

const neo4jStore = useNeo4jStore()
const isDark = ref(false)
const selectedModel = ref('deepseek-deepseek-chat')
const isNeo4jConnected = ref(false)
const connectingNeo4j = ref(false)

// Initialize theme from localStorage
onMounted(() => {
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme === 'dark') {
    isDark.value = true
    document.documentElement.classList.add('dark')
  }

  const savedModel = localStorage.getItem('selectedModel')
  if (savedModel) {
    selectedModel.value = savedModel
  }

  // Check Neo4j connection status from store
  isNeo4jConnected.value = neo4jStore.isConnected
})

const toggleTheme = () => {
  isDark.value = !isDark.value
  if (isDark.value) {
    document.documentElement.classList.add('dark')
    localStorage.setItem('theme', 'dark')
  } else {
    document.documentElement.classList.remove('dark')
    localStorage.setItem('theme', 'light')
  }
}

const handleModelChange = (value) => {
  localStorage.setItem('selectedModel', value)
  window.dispatchEvent(new CustomEvent('model-change', { detail: value }))
}

const testNeo4jConnection = async () => {
  connectingNeo4j.value = true

  try {
    const response = await fetch('http://localhost:7860/backend_connection_configuration', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(neo4jStore.config)
    })

    const data = await response.json()

    if (response.ok && data.status === 'Success') {
      isNeo4jConnected.value = true
      neo4jStore.setConnected(true)
      ElMessage.success('Neo4j 连接成功')
    } else {
      isNeo4jConnected.value = false
      neo4jStore.setConnected(false)
      ElMessage.error('Neo4j 连接失败')
    }
  } catch (error) {
    isNeo4jConnected.value = false
    neo4jStore.setConnected(false)
    ElMessage.error('Neo4j 连接失败: ' + error.message)
  } finally {
    connectingNeo4j.value = false
  }
}
</script>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  transition: background-color 0.3s, color 0.3s;
}

.app-header {
  background: var(--surface);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2.5rem;
  height: 68px;
  transition: all 0.3s;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.logo {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo-icon {
  font-size: 2rem;
  line-height: 1;
}

.logo-text {
  font-size: 1.5rem;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-actions {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

.model-selector {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.model-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
  white-space: nowrap;
}

.theme-btn {
  transition: all 0.3s;
  flex-shrink: 0;
}

.theme-btn:hover {
  transform: rotate(180deg);
}

.main-container {
  flex: 1;
  overflow: hidden;
}

.content-area {
  overflow-y: auto;
  padding: 2rem;
  background: var(--background);
  transition: background-color 0.3s;
}

.chat-sidebar {
  background: var(--surface);
  border-left: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.3s;
}
</style>

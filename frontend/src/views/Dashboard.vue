<template>
  <div class="dashboard">
    <!-- File Upload Section -->
    <el-card class="upload-section" shadow="hover">
      <template #header>
        <div class="section-header">
          <div class="section-title">
            <Upload style="width: 1.2em; height: 1.2em; margin-right: 0.5em;" />
            <span>文件上传</span>
          </div>
          <el-button
            type="primary"
            :disabled="!selectedFile"
            :loading="uploading"
            @click="uploadFile"
            :icon="uploading ? '' : Upload"
          >
            {{ uploading ? '上传中...' : '上传文件' }}
          </el-button>
        </div>
      </template>

      <el-upload
        ref="uploadRef"
        class="upload-area"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".pdf,.txt,.docx,.doc"
      >
        <UploadFilled style="width: 4em; height: 4em; color: #667eea;" />
        <div class="el-upload__text" style="margin-top: 1rem;">
          拖拽文件到此处或 <em>点击选择</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 PDF, TXT, DOCX 等格式，文件大小不超过 100MB
          </div>
        </template>
      </el-upload>

      <el-progress
        v-if="uploadProgress > 0"
        :percentage="uploadProgress"
        :stroke-width="10"
        :color="progressColors"
        style="margin-top: 1.5rem;"
      />

      <div v-if="uploadMessage" style="margin-top: 1rem;">
        <el-alert
          :type="uploadSuccess ? 'success' : 'error'"
          :title="uploadMessage"
          :closable="false"
          show-icon
        />
      </div>
    </el-card>

    <!-- Graph Extraction Section -->
    <el-card class="extraction-section" shadow="hover">
      <template #header>
        <div class="section-header">
          <div class="section-title">
            <Promotion style="width: 1.2em; height: 1.2em; margin-right: 0.5em;" />
            <span>知识图谱提取</span>
          </div>
        </div>
      </template>

      <el-form :model="extractConfig" label-width="120px">
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="数据源">
              <el-select v-model="extractConfig.sourceType" style="width: 100%;">
                <el-option label="本地文件" value="local_file" />
                <el-option label="网页 URL" value="web-url" />
                <el-option label="Bilibili" value="bilibili" />
                <el-option label="维基百科" value="Wikipedia" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="文件名">
              <el-input
                v-if="extractConfig.sourceType === 'local_file'"
                v-model="extractConfig.fileName"
                placeholder="选择文件"
              >
                <template #append>
                  <el-button :icon="CopyDocument" @click="useUploadedFileName" />
                </template>
              </el-input>
              <el-input
                v-else-if="['web-url', 'bilibili'].includes(extractConfig.sourceType)"
                v-model="extractConfig.url"
                :placeholder="extractConfig.sourceType === 'bilibili' ? 'Bilibili URL' : '网页 URL'"
              />
              <el-input
                v-else-if="extractConfig.sourceType === 'Wikipedia'"
                v-model="extractConfig.wikiQuery"
                placeholder="搜索关键词"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="Token 块大小">
              <el-input-number
                v-model="extractConfig.tokenChunkSize"
                :min="1000"
                :step="1000"
                style="width: 100%;"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="块重叠">
              <el-input-number
                v-model="extractConfig.chunkOverlap"
                :min="0"
                style="width: 100%;"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-button
            type="primary"
            :loading="extracting"
            @click="extractGraph"
            size="large"
            style="width: 200px;"
          >
            <Promotion style="width: 1em; height: 1em; margin-right: 0.5em;" />
            提取知识图谱
          </el-button>
          <el-button @click="resetExtractConfig" size="large">
            <RefreshLeft style="width: 1em; height: 1em; margin-right: 0.25em;" />
            重置
          </el-button>
        </el-form-item>

        <el-alert
          v-if="extractMessage"
          :type="extractSuccess ? 'success' : 'error'"
          :title="extractMessage"
          :closable="false"
          show-icon
        />
      </el-form>
    </el-card>

    <!-- Document List Section -->
    <el-card class="documents-section" shadow="hover">
      <template #header>
        <div class="section-header">
          <div class="section-title">
            <Document style="width: 1.2em; height: 1.2em; margin-right: 0.5em;" />
            <span>文档列表</span>
            <el-tag v-if="documents.length > 0" type="info" size="small" style="margin-left: 0.5rem;">
              {{ documents.length }} 个文档
            </el-tag>
          </div>
          <el-button :icon="Refresh" @click="loadDocuments">刷新</el-button>
        </div>
      </template>

      <el-table :data="documents" stripe style="width: 100%" v-loading="loadingDocuments">
        <el-table-column prop="fileName" label="文件名" min-width="200" />
        <el-table-column prop="status" label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="nodeCount" label="节点数" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.nodeCount || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="fileSize" label="大小 (KB)" width="120" align="right">
          <template #default="{ row }">
            {{ (row.fileSize / 1024).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="fileType" label="类型" width="120" align="center" />
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loadingDocuments && documents.length === 0" description="暂无文档数据" />
    </el-card>
  </div>
</template>


<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Upload,
  Document,
  RefreshLeft,
  Refresh,
  CopyDocument,
  UploadFilled,
  Promotion
} from '@element-plus/icons-vue'
import { useDocumentStore } from '@/stores/documents'
import { useNeo4jStore } from '@/stores/neo4j'
import { uploadFileApi, extractGraphApi } from '@/api/graph'

// Stores
const neo4jStore = useNeo4jStore()
const documentStore = useDocumentStore()

// File Upload
const selectedFile = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadMessage = ref('')
const uploadSuccess = ref(false)
const uploadedFileName = ref('')

// Get model from localStorage
const getCurrentModel = () => {
  return localStorage.getItem('selectedModel') || 'deepseek-deepseek-chat'
}

const progressColors = [
  { color: '#f56c6c', percentage: 20 },
  { color: '#e6a23c', percentage: 40 },
  { color: '#5cb87a', percentage: 60 },
  { color: '#1989fa', percentage: 80 },
  { color: '#6f7ad3', percentage: 100 }
]

// Documents
const { documents, loadingDocuments, loadDocuments } = documentStore

// Graph Extraction
const extractConfig = reactive({
  sourceType: 'local_file',
  fileName: '',
  url: '',
  wikiQuery: '',
  tokenChunkSize: 10000,
  chunkOverlap: 200
})

const extracting = ref(false)
const extractMessage = ref('')
const extractSuccess = ref(false)

// Methods
const handleFileChange = (file) => {
  selectedFile.value = file.raw
  uploadMessage.value = ''
  uploadProgress.value = 0
}

const uploadFile = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  uploadProgress.value = 0
  uploadMessage.value = ''

  try {
    const result = await uploadFileApi(selectedFile.value, getCurrentModel(), neo4jStore.config, (progress) => {
      uploadProgress.value = progress
    })

    uploadSuccess.value = result.success
    uploadMessage.value = result.message || '上传成功'

    if (result.success) {
      uploadedFileName.value = result.fileName
      extractConfig.fileName = result.fileName
      ElMessage.success('文件上传成功')
      loadDocuments()
    }
  } catch (error) {
    uploadSuccess.value = false
    uploadMessage.value = error.message
    ElMessage.error('上传失败: ' + error.message)
  } finally {
    uploading.value = false
  }
}

const extractGraph = async () => {
  if (!neo4jStore.isConnected) {
    ElMessage.warning('请先连接到 Neo4j 数据库')
    return
  }

  extracting.value = true
  extractMessage.value = ''

  try {
    const result = await extractGraphApi(getCurrentModel(), extractConfig, neo4jStore.config)
    extractSuccess.value = result.success
    extractMessage.value = result.message || '提取成功'

    if (result.success) {
      ElMessage.success('知识图谱提取成功')
      loadDocuments()
    }
  } catch (error) {
    extractSuccess.value = false
    extractMessage.value = error.message
    ElMessage.error('提取失败: ' + error.message)
  } finally {
    extracting.value = false
  }
}

const resetExtractConfig = () => {
  extractConfig.sourceType = 'local_file'
  extractConfig.fileName = ''
  extractConfig.url = ''
  extractConfig.wikiQuery = ''
  extractConfig.tokenChunkSize = 10000
  extractConfig.chunkOverlap = 200
  extractMessage.value = ''
}

const useUploadedFileName = () => {
  if (uploadedFileName.value) {
    extractConfig.fileName = uploadedFileName.value
  } else {
    ElMessage.warning('请先上传文件')
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

// Load documents on mount
loadDocuments()
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

/* Sections */
.upload-section,
.extraction-section,
.documents-section {
  border-radius: 12px;
  transition: all 0.3s;
  border: 1px solid var(--border-color);
}

.upload-section:hover,
.extraction-section:hover,
.documents-section:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 1.125rem;
  font-weight: 500;
  color: var(--text-primary);
}

.upload-area {
  margin: 1.5rem 0;
}

:deep(.el-upload-dragger) {
  padding: 3rem;
  border-radius: 12px;
  border: 2px dashed rgba(255, 255, 255, 0.15);
  transition: all 0.3s;
  background: rgba(255, 255, 255, 0.02);
}

:deep(.el-upload-dragger:hover) {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.1);
}

:deep(.el-form-item__label) {
  font-weight: 400;
  color: var(--text-primary);
}

:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
  background: transparent;
}

:deep(.el-table th) {
  font-weight: 500;
  color: var(--text-primary);
  background-color: var(--surface);
}

:deep(.el-table__empty-block) {
  padding: 3rem 0;
}
</style>

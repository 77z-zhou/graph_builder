import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:7860'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const message = error.response?.data?.message || error.message || '请求失败'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

// ===== Neo4j Connection =====
export const testConnectionApi = async (config) => {
  const formData = new FormData()
  formData.append('uri', config.uri)
  formData.append('userName', config.username)
  formData.append('password', config.password)
  formData.append('database', config.database)

  try {
    const response = await api.post('/backend_connection_configuration', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    return {
      success: response.status === 'Success',
      message: response.message || '',
      data: response
    }
  } catch (error) {
    return {
      success: false,
      message: error.message
    }
  }
}

// ===== File Upload =====
export const uploadFileApi = async (file, model, neo4jConfig, onProgress) => {
  const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE)

  try {
    for (let chunkNumber = 1; chunkNumber <= totalChunks; chunkNumber++) {
      const start = (chunkNumber - 1) * CHUNK_SIZE
      const end = Math.min(chunkNumber * CHUNK_SIZE, file.size)
      const chunk = file.slice(start, end)

      const formData = new FormData()
      formData.append('file', chunk, file.name)
      formData.append('chunkNumber', chunkNumber)
      formData.append('totalChunks', totalChunks)
      formData.append('originalname', file.name)
      formData.append('model', model)
      formData.append('uri', neo4jConfig.uri)
      formData.append('userName', neo4jConfig.username)
      formData.append('password', neo4jConfig.password)
      formData.append('database', neo4jConfig.database)

      await api.post('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      if (onProgress) {
        const progress = Math.round((chunkNumber / totalChunks) * 100)
        onProgress(progress)
      }
    }

    return {
      success: true,
      message: '上传成功',
      fileName: file.name
    }
  } catch (error) {
    return {
      success: false,
      message: error.message
    }
  }
}

// ===== Graph Extraction =====
export const extractGraphApi = async (model, config, neo4jConfig) => {
  const formData = new FormData()
  formData.append('uri', neo4jConfig.uri)
  formData.append('userName', neo4jConfig.username)
  formData.append('password', neo4jConfig.password)
  formData.append('database', neo4jConfig.database)
  formData.append('model', model)
  formData.append('source_type', config.sourceType)

  if (config.sourceType === 'local_file') {
    formData.append('file_name', config.fileName)
  } else if (['web-url', 'bilibili'].includes(config.sourceType)) {
    formData.append('source_url', config.url)
  } else if (config.sourceType === 'Wikipedia') {
    formData.append('wiki_query', config.wikiQuery)
  }

  formData.append('token_chunk_size', config.tokenChunkSize)
  formData.append('chunk_overlap', config.chunkOverlap)

  try {
    const response = await api.post('/extract', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    return {
      success: true,
      message: '提取成功',
      data: response
    }
  } catch (error) {
    return {
      success: false,
      message: error.message
    }
  }
}

// ===== Get Documents =====
export const getDocumentsApi = async () => {
  try {
    // TODO: Implement actual API call when backend provides document list endpoint
    // const response = await api.get('/documents')
    // return response.data

    // Mock data for now
    return []
  } catch (error) {
    console.error('Failed to get documents:', error)
    return []
  }
}

// ===== Chat =====
export const chatApi = async (message, mode = 'simple', documentName = '') => {
  try {
    const response = await api.post('/chat', {
      message,
      mode,
      document_name: documentName
    })

    return {
      response: response.response || response.message || '处理完成'
    }
  } catch (error) {
    throw new Error(error.message)
  }
}

export default api

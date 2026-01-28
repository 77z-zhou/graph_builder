import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getDocumentsApi } from '@/api/graph'

export const useDocumentStore = defineStore('documents', () => {
  const documents = ref([])
  const loadingDocuments = ref(false)

  const loadDocuments = async () => {
    loadingDocuments.value = true
    try {
      const data = await getDocumentsApi()
      documents.value = data || []
    } catch (error) {
      console.error('Failed to load documents:', error)
      documents.value = []
    } finally {
      loadingDocuments.value = false
    }
  }

  const addDocument = (document) => {
    documents.value.push(document)
  }

  const updateDocument = (id, updates) => {
    const index = documents.value.findIndex(doc => doc.id === id)
    if (index !== -1) {
      documents.value[index] = { ...documents.value[index], ...updates }
    }
  }

  const removeDocument = (id) => {
    documents.value = documents.value.filter(doc => doc.id !== id)
  }

  return {
    documents,
    loadingDocuments,
    loadDocuments,
    addDocument,
    updateDocument,
    removeDocument
  }
})

import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNeo4jStore = defineStore('neo4j', () => {
  const config = ref({
    uri: 'bolt://127.0.0.1:7687',
    username: 'neo4j',
    password: '',
    database: 'neo4j'
  })

  const isConnected = ref(false)

  const setConfig = (newConfig) => {
    config.value = { ...newConfig }
  }

  const setConnected = (status) => {
    isConnected.value = status
  }

  const clearConfig = () => {
    config.value = {
      uri: 'bolt://127.0.0.1:7687',
      username: 'neo4j',
      password: '',
      database: 'neo4j'
    }
    isConnected.value = false
  }

  return {
    config,
    isConnected,
    setConfig,
    setConnected,
    clearConfig
  }
})

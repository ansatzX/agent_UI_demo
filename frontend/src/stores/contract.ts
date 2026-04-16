import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Contract, ContractField, Template, RiskReview } from '@/types'
import { contractApi, templateApi } from '@/api/client'

export const useContractStore = defineStore('contract', () => {
  const currentContract = ref<Contract | null>(null)
  const templates = ref<Template[]>([])
  const riskReview = ref<RiskReview | null>(null)
  const isLoading = ref(false)
  const wordBlob = ref<Blob | null>(null)

  const loadTemplates = async () => {
    isLoading.value = true
    try {
      templates.value = await templateApi.list()
    } catch (error) {
      console.error('Failed to load templates:', error)
    } finally {
      isLoading.value = false
    }
  }

  const uploadTemplate = async (file: File, name: string, type: string) => {
    isLoading.value = true
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('name', name)
      formData.append('type', type)

      const template = await templateApi.upload(formData)
      templates.value.unshift(template)
      return template
    } finally {
      isLoading.value = false
    }
  }

  const createContract = async (name: string, type: string, templateId?: number) => {
    isLoading.value = true
    try {
      const contract = await contractApi.create({ name, type, template_id: templateId })
      currentContract.value = contract
      return contract
    } finally {
      isLoading.value = false
    }
  }

  const loadContract = async (id: number) => {
    isLoading.value = true
    try {
      currentContract.value = await contractApi.get(id)
    } finally {
      isLoading.value = false
    }
  }

  const updateField = async (fieldName: string, value: string) => {
    if (!currentContract.value) return

    try {
      const contract = await contractApi.updateFields(
        currentContract.value.id,
        { field_updates: { [fieldName]: value } }
      )
      currentContract.value = contract
    } catch (error) {
      console.error('Failed to update field:', error)
    }
  }

  const generateContract = async () => {
    if (!currentContract.value) return

    isLoading.value = true
    try {
      const blob = await contractApi.generate(currentContract.value.id)
      wordBlob.value = blob
      return blob
    } finally {
      isLoading.value = false
    }
  }

  const reviewContract = async () => {
    if (!currentContract.value) return

    isLoading.value = true
    try {
      riskReview.value = await contractApi.review(currentContract.value.id)
      return riskReview.value
    } finally {
      isLoading.value = false
    }
  }

  const downloadContract = () => {
    if (!wordBlob.value || !currentContract.value) return

    const url = URL.createObjectURL(wordBlob.value)
    const a = document.createElement('a')
    a.href = url
    a.download = `${currentContract.value.name}.docx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const fieldsByGroup = computed(() => {
    if (!currentContract.value) return {}

    const groups: Record<string, ContractField[]> = {}
    currentContract.value.fields.forEach(field => {
      const group = field.group || '其他'
      if (!groups[group]) {
        groups[group] = []
      }
      groups[group].push(field)
    })

    Object.values(groups).forEach(fields => {
      fields.sort((a, b) => a.order - b.order)
    })

    return groups
  })

  const setCurrentContract = (contract: Contract | null) => {
    currentContract.value = contract
  }

  return {
    currentContract,
    templates,
    riskReview,
    isLoading,
    wordBlob,
    fieldsByGroup,
    loadTemplates,
    uploadTemplate,
    createContract,
    loadContract,
    updateField,
    generateContract,
    reviewContract,
    downloadContract,
    setCurrentContract
  }
})

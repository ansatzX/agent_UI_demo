import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Message, Option } from '@/types'
import { chatApi, type TokenUsage } from '@/api/client'
import axios from 'axios'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const isLoading = ref(false)
  const currentSessionId = ref<string | null>(null)
  const abortController = ref<AbortController | null>(null)
  const currentTokenUsage = ref<TokenUsage | null>(null)
  const currentResponseTime = ref<number | null>(null)
  const sessions = ref<any[]>([])

  const addMessage = (message: Message) => {
    messages.value.push(message)
  }

  const loadHistory = async (sessionId: string) => {
    try {
      const history = await chatApi.getHistory(sessionId)
      messages.value = history.map(msg => ({
        role: msg.role,
        content: msg.content,
        options: msg.options,
        uploaded_file: msg.uploaded_file
      }))
      currentSessionId.value = sessionId
    } catch (error) {
      console.error('Failed to load history:', error)
    }
  }

  const loadSessions = async () => {
    try {
      sessions.value = await chatApi.listSessions()
    } catch (error) {
      console.error('Failed to load sessions:', error)
    }
  }

  const sendMessage = async (content: string, optionId?: string, fileInfo?: any) => {
    isLoading.value = true
    abortController.value = new AbortController()

    try {
      const response = await chatApi.send({
        message: content,
        session_id: currentSessionId.value ?? undefined,
        option_id: optionId,
        uploaded_file: fileInfo
      }, abortController.value.signal)

      // 添加用户消息（包含文件信息）
      addMessage({
        role: 'user',
        content: content,
        uploaded_file: fileInfo
      })

      // 添加AI响应消息
      addMessage({
        role: 'assistant',
        content: response.message,
        options: response.options
      })

      if (response.session_id) {
        currentSessionId.value = response.session_id
        // 保存到localStorage
        localStorage.setItem('currentSessionId', response.session_id)
        // 刷新会话列表
        await loadSessions()
      }

      // 保存token统计和响应时间
      if (response.token_usage) {
        currentTokenUsage.value = response.token_usage
      }
      if (response.response_time) {
        currentResponseTime.value = response.response_time
      }
    } catch (error) {
      if (axios.isCancel(error)) {
        console.log('Request cancelled')
        addMessage({
          role: 'assistant',
          content: '响应已中断'
        })
      } else {
        console.error('Failed to send message:', error)
        addMessage({
          role: 'assistant',
          content: '抱歉，发生了错误，请稍后重试。'
        })
      }
    } finally {
      isLoading.value = false
      abortController.value = null
    }
  }

  const cancelRequest = () => {
    if (abortController.value) {
      abortController.value.abort()
    }
  }

  const selectOption = async (option: Option) => {
    await sendMessage(option.label, option.id)
  }

  const clearChat = () => {
    messages.value = []
    currentSessionId.value = null
    currentTokenUsage.value = null
    currentResponseTime.value = null
    localStorage.removeItem('currentSessionId')
  }

  const deleteSession = async (sessionId: string) => {
    try {
      await chatApi.deleteSession(sessionId)
      await loadSessions()

      // 如果删除的是当前会话，清空聊天
      if (sessionId === currentSessionId.value) {
        clearChat()
      }
    } catch (error) {
      console.error('Failed to delete session:', error)
    }
  }

  const initSession = async () => {
    // 尝试从localStorage恢复会话
    const savedSessionId = localStorage.getItem('currentSessionId')
    if (savedSessionId) {
      await loadHistory(savedSessionId)
    }
  }

  return {
    messages,
    isLoading,
    currentSessionId,
    currentTokenUsage,
    currentResponseTime,
    sessions,
    addMessage,
    loadHistory,
    loadSessions,
    sendMessage,
    cancelRequest,
    selectOption,
    clearChat,
    deleteSession,
    initSession
  }
})

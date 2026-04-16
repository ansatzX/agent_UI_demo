<template>
  <div class="workspace">
    <header class="workspace-header">
      <h1>📄 企业技术合同智能助手</h1>
    </header>

    <div class="workspace-content">
      <!-- 会话列表 -->
      <div class="sessions-panel">
        <div class="sessions-header">
          <h2>历史会话</h2>
          <button @click="createNewSession" class="new-chat-btn">+ 新对话</button>
        </div>
        <div class="sessions-list">
          <div
            v-for="session in chatStore.sessions"
            :key="session.id"
            :class="['session-item', { active: session.id === chatStore.currentSessionId }]"
            @click="switchSession(session.id)"
          >
            <div class="session-preview">
              <div class="session-time">{{ formatTime(session.created_at) }}</div>
              <div class="session-message">{{ session.last_message || '新会话' }}</div>
              <div v-if="session.has_file" class="session-file">
                <span class="file-indicator">📎</span>
                <span class="file-name">
                  {{ session.file_names && session.file_names.length > 0
                    ? (session.file_names.length === 1
                        ? session.file_names[0]
                        : `${session.file_names.length}个文件`)
                    : ''
                  }}
                </span>
                <button
                  v-if="session.file_names && session.file_names.length === 1"
                  @click.stop="downloadSessionFile(
                    session.files && session.files[0]
                      ? session.files[0].stored_filename
                      : session.file_names[0]
                  )"
                  class="download-link"
                  title="下载文件"
                >
                  ⬇️
                </button>
              </div>
            </div>
            <button @click.stop="deleteSession(session.id)" class="delete-btn">🗑️</button>
          </div>
          <div v-if="chatStore.sessions.length === 0" class="empty-sessions">
            暂无历史会话
          </div>
        </div>
      </div>

      <div class="chat-panel">
        <!-- 文件拖放上传提示 -->
        <div
          v-if="isDraggingFile"
          class="drag-overlay"
          @drop.prevent.stop="handleChatDrop"
          @dragover.prevent.stop
          @dragleave.prevent.stop="isDraggingFile = false"
        >
          <div class="drag-content">
            <div class="drag-icon">📁</div>
            <p>拖放文件到此处上传</p>
            <p class="drag-hint">仅支持 .docx 格式，最大 200MB</p>
          </div>
        </div>

        <div
          class="chat-messages"
          @dragenter.prevent.stop="isDraggingFile = true"
          @dragover.prevent.stop
          @drop.prevent.stop
        >
          <div v-for="(msg, idx) in chatStore.messages" :key="idx" :class="['message', msg.role]">
            <div class="bubble">
              <template v-if="'content' in msg">
                <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
              </template>
              <!-- 在用户消息后显示文件快捷链接 -->
              <div
                v-if="msg.role === 'user' && 'uploaded_file' in msg && msg.uploaded_file"
                class="message-file-link"
              >
                <button
                  @click="showFile(msg.uploaded_file)"
                  class="file-link-btn"
                  :title="`查看文档: ${msg.uploaded_file.original_filename || msg.uploaded_file.filename}`"
                >
                  📎 {{ msg.uploaded_file.original_filename || msg.uploaded_file.filename }}
                </button>
              </div>
              <!-- 在 assistant 消息后显示工具结果（表单） -->
              <div
                v-if="msg.role === 'assistant' && 'tool_results' in msg && msg.tool_results"
                class="tool-results"
              >
                <template v-for="(tr, trIdx) in msg.tool_results" :key="trIdx">
                  <DynamicForm
                    v-if="tr.output && tr.output.type === 'form' && tr.output.form_id"
                    :form-def="{
                      type: 'form',
                      form_id: tr.output.form_id,
                      title: tr.output.title || '填写表单',
                      fields: tr.output.fields || []
                    }"
                    @submit="(values) => chatStore.submitForm(tr.output.form_id, values)"
                  />
                  <a
                    v-else-if="tr.tool_name === 'generate_document' && tr.success && tr.output && tr.output.download_url"
                    :href="tr.output.download_url"
                    :download="tr.output.display_name || tr.output.filename"
                    class="download-doc-btn"
                  >
                    ⬇️ 下载 {{ tr.output.display_name || tr.output.filename }}
                  </a>
                  <button
                    v-if="tr.tool_name === 'generate_document' && tr.success && tr.output && tr.output.filename"
                    @click="previewGeneratedDoc(tr.output.filename)"
                    class="preview-doc-btn"
                  >
                    👁️ 预览
                  </button>
                </template>
              </div>
            </div>
          </div>

          <!-- 响应中状态 -->
          <div v-if="chatStore.isLoading" class="loading-container">
            <div class="loading">
              <div class="loading-spinner"></div>
              <span>AI 正在思考...</span>
              <button @click="cancelResponse" class="cancel-btn">中断</button>
            </div>
          </div>
        </div>

        <!-- 统计信息 -->
        <div class="stats-bar" v-if="chatStore.currentTokenUsage || chatStore.currentResponseTime">
          <span v-if="chatStore.currentResponseTime" class="stat">
            ⏱️ {{ chatStore.currentResponseTime.toFixed(2) }}秒
          </span>
          <span v-if="chatStore.currentTokenUsage" class="stat">
            📊 输入: {{ chatStore.currentTokenUsage.prompt_tokens }} |
            输出: {{ chatStore.currentTokenUsage.completion_tokens }} |
            总计: {{ chatStore.currentTokenUsage.total_tokens }}
          </span>
        </div>

        <!-- 已上传文件显示 -->
        <div v-if="uploadedFile" class="uploaded-file-preview">
          <div class="file-card">
            <span class="file-icon">📄</span>
            <span class="file-name">{{ uploadedFile.filename }}</span>
            <button @click="uploadedFile = null" class="remove-file-btn" title="移除文件">
              ✕
            </button>
          </div>
        </div>

        <div class="input-area">
          <input
            v-model="inputText"
            @keyup.enter="send"
            :placeholder="uploadedFile ? '已附加文件，输入消息发送...' : '输入消息...'"
            :disabled="chatStore.isLoading"
          />
          <button @click="send" :disabled="chatStore.isLoading">发送</button>
        </div>
      </div>

      <div class="contract-panel">
        <!-- 空状态提示 -->
        <div v-if="!uploadedFile" class="empty-state">
          <div class="empty-icon">📄</div>
          <h2>文档预览区</h2>
          <p>在左侧聊天区拖放文件以上传</p>
          <p class="hint-text">或点击聊天消息中的文档链接预览</p>
        </div>

        <!-- 文件预览区域 -->
        <div v-else class="preview-area">
          <div class="preview-header">
            <h3>📄 {{ uploadedFile.filename }}</h3>
            <div class="preview-actions">
              <!-- 缩放控制 -->
              <div class="zoom-controls">
                <button @click="zoomOut" class="zoom-btn" :disabled="zoomLevel <= 50" title="缩小">
                  ➖
                </button>
                <span class="zoom-level">{{ zoomLevel }}%</span>
                <button @click="zoomIn" class="zoom-btn" :disabled="zoomLevel >= 200" title="放大">
                  ➕
                </button>
                <button @click="resetZoom" class="zoom-btn" title="重置">
                  🔄
                </button>
              </div>
              <button @click="downloadFile" class="action-btn">⬇️ 下载</button>
              <button @click="clearFile" class="action-btn delete-btn">🗑️ 删除</button>
            </div>
          </div>

          <div class="file-stats">
            <span class="stat-item">📊 文件大小: {{ formatFileSize(uploadedFile.size) }}</span>
            <span v-if="uploadedFile.parsed?.paragraphs_count" class="stat-item">
              📝 段落数: {{ uploadedFile.parsed.paragraphs_count }}
            </span>
            <span v-if="uploadedFile.parsed?.tables_count" class="stat-item">
              📊 表格数: {{ uploadedFile.parsed.tables_count }}
            </span>
          </div>

          <!-- 使用VueOfficeDocx预览Word文档 -->
          <div v-if="uploadedFile.unique_filename" class="preview-content">
            <div class="preview-wrapper" :style="{ transform: `scale(${zoomLevel / 100})` }">
              <VueOfficeDocx
                :src="`/api/files/preview-docx/${uploadedFile.unique_filename}`"
                class="docx-preview"
              />
            </div>
          </div>

          <!-- 后备：显示解析的文本内容 -->
          <div v-else-if="uploadedFile.parsed?.success" class="preview-content fallback">
            <div class="content-section">
              <h4>📝 文档内容</h4>
              <div class="document-content">
                <div v-for="(para, idx) in uploadedFile.parsed.paragraphs" :key="idx" class="paragraph">
                  {{ para }}
                </div>
              </div>
            </div>

            <div v-if="uploadedFile.parsed.tables.length > 0" class="content-section">
              <h4>📊 表格内容 ({{ uploadedFile.parsed.tables.length }} 个表格)</h4>
              <div v-for="(table, tIdx) in uploadedFile.parsed.tables" :key="tIdx" class="table-container">
                <table class="preview-table">
                  <tbody>
                    <tr v-for="(row, rIdx) in table" :key="rIdx">
                      <td v-for="(cell, cIdx) in row" :key="cIdx">{{ cell }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div v-else class="error-message">
            ❌ 文件解析失败: {{ uploadedFile.parsed?.error }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useContractStore } from '@/stores/contract'
import DynamicForm from '@/components/DynamicForm.vue'
import axios from 'axios'
import VueOfficeDocx from '@vue-office/docx'
import '@vue-office/docx/lib/index.css'
import { marked } from 'marked'

// Configure marked for safe rendering
marked.setOptions({
  breaks: true, // Convert line breaks to <br>
  gfm: true // GitHub Flavored Markdown
})

const renderMarkdown = (text: string) => {
  if (!text) return ''
  try {
    return marked.parse(text) as string
  } catch (e) {
    console.error('Markdown parse error:', e)
    return text
  }
}

const chatStore = useChatStore()
const contractStore = useContractStore()

const inputText = ref('')
const uploadedFile = ref<any>(null)
const isDraggingFile = ref(false)
const zoomLevel = ref(100) // 文档缩放级别

const send = () => {
  if (inputText.value.trim() && !chatStore.isLoading) {
    // 如果当前有上传的文件，将文件信息附加到消息
    const fileInfo = uploadedFile.value ? {
      filename: uploadedFile.value.unique_filename,
      original_filename: uploadedFile.value.filename,
      size: uploadedFile.value.size,
      content: uploadedFile.value.parsed
    } : undefined

    chatStore.sendMessage(inputText.value, undefined, fileInfo)
    inputText.value = ''

    // 发送后清空文件预览
    if (fileInfo) {
      uploadedFile.value = null
    }
  }
}

const cancelResponse = () => {
  chatStore.cancelRequest()
}

const createNewSession = () => {
  chatStore.clearChat()
  chatStore.sendMessage('你好')
}

const switchSession = async (sessionId: string) => {
  await chatStore.loadHistory(sessionId)
  localStorage.setItem('currentSessionId', sessionId)

  // 切换会话时清空右侧预览区
  // 文件链接会在消息历史中自动显示（通过 msg.uploaded_file）
  uploadedFile.value = null
}

const deleteSession = async (sessionId: string) => {
  if (confirm('确定要删除这个会话吗？')) {
    await chatStore.deleteSession(sessionId)
  }
}

const downloadSessionFile = async (filename: string) => {
  try {
    const response = await axios.get(`/api/files/download/${filename}`, {
      responseType: 'blob'
    })

    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('文件下载失败:', error)
    alert('文件下载失败')
  }
}

const formatTime = (timestamp: string) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } else if (days === 1) {
    return '昨天'
  } else if (days < 7) {
    return `${days}天前`
  } else {
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  }
}

const handleChatDrop = async (event: DragEvent) => {
  event.preventDefault()
  event.stopPropagation()
  isDraggingFile.value = false

  const file = event.dataTransfer?.files[0]
  if (file) {
    await uploadFile(file)
  }
}

const showFile = (fileData: any) => {
  uploadedFile.value = {
    filename: fileData.original_filename || fileData.filename,
    unique_filename: fileData.filename,
    size: fileData.size || 0,
    parsed: fileData.content
  }
  // 重置缩放级别
  zoomLevel.value = 100
}

const previewGeneratedDoc = (filename: string) => {
  uploadedFile.value = {
    filename,
    unique_filename: filename,
    size: 0,
    parsed: null
  }
  zoomLevel.value = 100
}

const zoomIn = () => {
  if (zoomLevel.value < 200) {
    zoomLevel.value = Math.min(zoomLevel.value + 25, 200)
  }
}

const zoomOut = () => {
  if (zoomLevel.value > 50) {
    zoomLevel.value = Math.max(zoomLevel.value - 25, 50)
  }
}

const resetZoom = () => {
  zoomLevel.value = 100
}

const uploadFile = async (file: File) => {
  // 检查文件格式
  if (!file.name.endsWith('.doc') && !file.name.endsWith('.docx')) {
    alert('只支持 .doc 和 .docx 格式的文件')
    return
  }

  // 检查文件大小 (200MB)
  const maxSize = 200 * 1024 * 1024
  if (file.size > maxSize) {
    alert(`文件大小不能超过 200MB，当前文件大小: ${(file.size / (1024 * 1024)).toFixed(2)}MB`)
    return
  }

  const formData = new FormData()
  formData.append('file', file)

  try {
    // 上传文件并关联到当前会话
    const response = await axios.post('/api/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      params: {
        session_id: chatStore.currentSessionId || undefined
      }
    })

    uploadedFile.value = {
      filename: response.data.filename,
      unique_filename: response.data.unique_filename,
      size: response.data.size,
      parsed: response.data.parsed
    }
    console.log('文件上传成功:', response.data)

    // 更新会话列表，显示文件关联
    await chatStore.loadSessions()

    // 不自动触发LLM对话，让用户自己决定何时发送
  } catch (error: any) {
    console.error('文件上传失败:', error)
    const errorMsg = error.response?.data?.detail || '文件上传失败，请重试'
    alert(errorMsg)
  }
}

const downloadFile = async () => {
  if (!uploadedFile.value) return

  try {
    const response = await axios.get(`/api/files/download/${uploadedFile.value.filename}`, {
      responseType: 'blob'
    })

    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', uploadedFile.value.filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('文件下载失败:', error)
    alert('文件下载失败')
  }
}

const clearFile = async () => {
  if (!confirm('确定要删除这个文件吗？')) return

  try {
    await axios.delete(`/api/files/${uploadedFile.value.unique_filename}`)
    uploadedFile.value = null
  } catch (error) {
    console.error('文件删除失败:', error)
    alert('文件删除失败')
  }
}

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

onMounted(async () => {
  // 阻止浏览器默认的拖放行为
  const preventDefaults = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  // 添加全局拖放事件监听
  document.addEventListener('dragenter', preventDefaults)
  document.addEventListener('dragover', preventDefaults)
  document.addEventListener('drop', preventDefaults)

  await contractStore.loadTemplates()
  await chatStore.loadSessions()

  // 初始化会话（恢复历史）
  await chatStore.initSession()

  // 如果没有历史消息，发送欢迎消息
  if (chatStore.messages.length === 0) {
    chatStore.sendMessage('你好')
  }
})
</script>

<style scoped>
.workspace {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f7fa;
}

.workspace-header {
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
}

.workspace-header h1 {
  font-size: 20px;
  font-weight: 600;
}

.workspace-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* 会话列表面板 */
.sessions-panel {
  width: 260px;
  background: white;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
}

.sessions-header {
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sessions-header h2 {
  font-size: 16px;
  font-weight: 600;
}

.new-chat-btn {
  padding: 6px 12px;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.new-chat-btn:hover {
  background: #1d4ed8;
}

.sessions-list {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.session-item:hover {
  background: #f9fafb;
}

.session-item.active {
  background: #eff6ff;
  border-left: 3px solid #2563eb;
}

.session-preview {
  flex: 1;
  min-width: 0;
}

.session-time {
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 4px;
}

.session-message {
  font-size: 13px;
  color: #1f2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-file {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 4px 8px;
  border-radius: 4px;
}

.file-indicator {
  font-size: 12px;
}

.file-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #374151;
}

.download-link {
  padding: 2px 6px;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 3px;
  font-size: 11px;
  cursor: pointer;
  transition: background 0.2s;
}

.download-link:hover {
  background: #1d4ed8;
}

.delete-btn {
  padding: 4px;
  background: transparent;
  border: none;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
  font-size: 14px;
}

.session-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  transform: scale(1.1);
}

.empty-sessions {
  padding: 24px;
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
}

/* 聊天面板 */
.chat-panel {
  width: 420px;
  display: flex;
  flex-direction: column;
  background: white;
  border-right: 1px solid #e5e7eb;
  position: relative;
}

/* 拖放上传遮罩 */
.drag-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(37, 99, 235, 0.95);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  margin: 8px;
}

.drag-content {
  text-align: center;
  color: white;
}

.drag-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.drag-content p {
  margin: 8px 0;
  font-size: 16px;
}

.drag-hint {
  font-size: 14px;
  opacity: 0.8;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.message {
  margin-bottom: 16px;
}

.message.assistant .bubble {
  background: #f3f4f6;
  padding: 12px 16px;
  border-radius: 16px;
  border-bottom-left-radius: 4px;
}

.message.user .bubble {
  background: #2563eb;
  color: white;
  padding: 12px 16px;
  border-radius: 16px;
  border-bottom-right-radius: 4px;
}

.message-file-link {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.3);
}

.file-link-btn {
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.file-link-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
}

.message-content {
  line-height: 1.6;
  word-wrap: break-word;
}

.message-content h1,
.message-content h2,
.message-content h3 {
  margin-top: 16px;
  margin-bottom: 8px;
  font-weight: 600;
}

.message-content h1 { font-size: 1.5em; }
.message-content h2 { font-size: 1.3em; }
.message-content h3 { font-size: 1.1em; }

.message-content p {
  margin: 8px 0;
}

.message-content ul,
.message-content ol {
  margin: 8px 0;
  padding-left: 24px;
}

.message-content li {
  margin: 4px 0;
}

.message-content code {
  background: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.9em;
}

.message-content pre {
  background: rgba(0, 0, 0, 0.05);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 12px 0;
}

.message-content pre code {
  background: none;
  padding: 0;
}

.message-content a {
  color: #3b82f6;
  text-decoration: none;
}

.message-content a:hover {
  text-decoration: underline;
}

.message-content blockquote {
  border-left: 3px solid rgba(0, 0, 0, 0.2);
  padding-left: 12px;
  margin: 12px 0;
  color: rgba(0, 0, 0, 0.7);
}

.message-content strong {
  font-weight: 600;
}

.message-content em {
  font-style: italic;
}

.message-content hr {
  border: none;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  margin: 16px 0;
}

.download-doc-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 8px 16px;
  background: #10b981;
  color: white;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: background 0.2s;
}

.download-doc-btn:hover {
  background: #059669;
}

.preview-doc-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  margin-left: 8px;
  padding: 8px 16px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.preview-doc-btn:hover {
  background: #2563eb;
}

.loading-container {
  margin-bottom: 16px;
}

.loading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f3f4f6;
  border-radius: 12px;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.cancel-btn {
  margin-left: auto;
  padding: 4px 12px;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.cancel-btn:hover {
  background: #dc2626;
}

.stats-bar {
  padding: 8px 16px;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
  font-size: 12px;
  color: #6b7280;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.stat {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.input-area {
  padding: 16px;
  display: flex;
  gap: 8px;
  border-top: 1px solid #e5e7eb;
}

/* 已上传文件预览 */
.uploaded-file-preview {
  padding: 8px 16px;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
}

.file-card {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: white;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  font-size: 13px;
}

.file-icon {
  font-size: 18px;
}

.file-name {
  color: #374151;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remove-file-btn {
  padding: 2px 6px;
  background: transparent;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  transition: color 0.2s;
}

.remove-file-btn:hover {
  color: #ef4444;
}

.input-area input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
}

.input-area input:disabled {
  background: #f3f4f6;
  cursor: not-allowed;
}

.input-area button {
  padding: 10px 20px;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.input-area button:hover:not(:disabled) {
  background: #1d4ed8;
}

.input-area button:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.contract-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  overflow: hidden;
}

/* 预览区域 */
.preview-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.preview-header {
  padding: 16px 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.preview-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* 缩放控制 */
.zoom-controls {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  background: #f3f4f6;
  border-radius: 8px;
}

.zoom-btn {
  padding: 4px 8px;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  min-width: 28px;
}

.zoom-btn:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}

.zoom-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.zoom-level {
  padding: 0 8px;
  font-size: 12px;
  color: #6b7280;
  min-width: 45px;
  text-align: center;
  font-weight: 500;
}

.action-btn {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #f9fafb;
}

.delete-btn {
  border-color: #ef4444;
  color: #ef4444;
}

.delete-btn:hover {
  background: #fef2f2;
}

.file-stats {
  padding: 8px 24px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  font-size: 13px;
  color: #6b7280;
}

.stat-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* 预览内容 */
.preview-content {
  flex: 1;
  overflow: auto;
  padding: 24px;
  background: #f3f4f6;
}

.preview-wrapper {
  transform-origin: top center;
  transition: transform 0.2s ease;
}

/* Docx预览样式 */
.docx-preview {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  min-height: 500px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.docx-preview :deep(.docx-wrapper) {
  background: white;
  padding: 20px;
}

.docx-preview :deep(.docx) {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin: 0 auto;
}

.fallback {
  padding: 24px;
}

.content-section {
  margin-bottom: 32px;
}

.content-section h4 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #1f2937;
}

.document-content {
  background: #f9fafb;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.paragraph {
  margin-bottom: 12px;
  line-height: 1.6;
  color: #374151;
}

.paragraph:last-child {
  margin-bottom: 0;
}

.table-container {
  margin-bottom: 16px;
  overflow-x: auto;
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border: 1px solid #e5e7eb;
}

.preview-table td {
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  font-size: 13px;
  color: #374151;
}

.preview-table tr:first-child td {
  background: #f9fafb;
  font-weight: 600;
}

.error-message {
  padding: 24px;
  text-align: center;
  color: #ef4444;
  font-size: 14px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #6b7280;
  padding: 32px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state h2 {
  font-size: 24px;
  margin-bottom: 8px;
  color: #1f2937;
}

.hint-text {
  font-size: 13px;
  color: #9ca3af;
  margin-top: 8px;
}
</style>

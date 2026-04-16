import axios from 'axios'
import type {
  Option, Contract, Template, RiskReview
} from '@/types'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

export interface FileUploadResponse {
  filename: string
  unique_filename: string
  size: number
  parsed: {
    success: boolean
    paragraphs: string[]
    tables: any[][]
    full_text: string
    error?: string
  }
  session_id?: string
}

export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

export interface ChatRequest {
  message: string
  session_id?: string
  option_id?: string
  uploaded_file?: {
    filename: string
    original_filename?: string
    size?: number
    content?: any
  }
}

export interface ChatResponse {
  message: string
  options: Option[]
  session_id?: string
  token_usage?: TokenUsage
  response_time?: number
  tool_results?: any[]
}

export interface FormSubmitRequest {
  form_id: string
  values: Record<string, any>
  session_id: string
}

export interface ContractFillRequest {
  field_updates: Record<string, string>
}

export const chatApi = {
  send: (data: ChatRequest, signal?: AbortSignal): Promise<ChatResponse> =>
    api.post('/chat', data, { signal }).then(r => r.data),

  getHistory: (sessionId: string): Promise<any[]> =>
    api.get(`/chat/history/${sessionId}`).then(r => r.data),

  listSessions: (): Promise<any[]> =>
    api.get('/chat/sessions').then(r => r.data),

  deleteSession: (sessionId: string): Promise<void> =>
    api.delete(`/chat/sessions/${sessionId}`).then(r => r.data),

  submitForm: (data: FormSubmitRequest): Promise<ChatResponse> =>
    api.post('/chat/submit-form', data).then(r => r.data)
}

export const templateApi = {
  list: (type?: string): Promise<Template[]> =>
    api.get('/templates', { params: { type } }).then(r => r.data),

  get: (id: number): Promise<Template> =>
    api.get(`/templates/${id}`).then(r => r.data),

  upload: (formData: FormData): Promise<Template> =>
    api.post('/templates', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(r => r.data)
}

export const contractApi = {
  list: (): Promise<Contract[]> =>
    api.get('/contracts').then(r => r.data),

  get: (id: number): Promise<Contract> =>
    api.get(`/contracts/${id}`).then(r => r.data),

  create: (data: { name: string; type: string; template_id?: number }): Promise<Contract> =>
    api.post('/contracts', data).then(r => r.data),

  updateFields: (id: number, data: ContractFillRequest): Promise<Contract> =>
    api.patch(`/contracts/${id}/fields`, data).then(r => r.data),

  generate: (id: number): Promise<Blob> =>
    api.post(`/contracts/${id}/generate`, null, { responseType: 'blob' }).then(r => r.data),

  review: (id: number): Promise<RiskReview> =>
    api.post(`/contracts/${id}/review`).then(r => r.data),

  updateStatus: (id: number, status: string): Promise<Contract> =>
    api.patch(`/contracts/${id}/status`, null, { params: { status } }).then(r => r.data)
}

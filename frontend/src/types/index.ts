export interface Option {
  id: string
  label: string
  description: string
  action: string
  payload?: Record<string, any>
}

export interface BaseMessage {
  id?: number
  timestamp?: string
}

export interface UserMessage extends BaseMessage {
  role: 'user'
  content: string
  uploaded_file?: {
    filename: string
    original_filename?: string
    size?: number
    content?: any
  }
}

export interface AssistantMessage extends BaseMessage {
  role: 'assistant'
  content: string
  options?: Option[]
  tool_results?: ToolResult[]
}

export interface FormSubmissionMessage extends BaseMessage {
  role: 'user'
  type: 'form_submission'
  content: string
  form_values: Record<string, any>
}

export interface ToolResultMessage extends BaseMessage {
  role: 'assistant'
  type: 'tool_result'
  tool: string
  result: any
}

export type Message = UserMessage | AssistantMessage | FormSubmissionMessage | ToolResultMessage

export interface ToolResult {
  tool_call_id?: string
  tool_name?: string
  success?: boolean
  type?: string            // 'form' | ...
  form_id?: string
  title?: string
  fields?: FormField[]
  output?: any
  error?: string
  [k: string]: any
}

export interface FormField {
  name: string
  label: string
  type: 'text' | 'number' | 'date' | 'select' | 'textarea'
  required?: boolean
  options?: string[]
  default?: string
  placeholder?: string
}

export interface ContractField {
  id: number
  name: string
  label: string
  value?: string
  placeholder?: string
  field_type: string
  group?: string
  required: boolean
  order: number
}

export interface Contract {
  id: number
  name: string
  type: string
  status: string
  template_id?: number
  fields: ContractField[]
  created_at: string
  updated_at: string
}

export interface Template {
  id: number
  name: string
  type: string
  description?: string
  created_at: string
  updated_at: string
}

export interface RiskIssue {
  level: string
  title: string
  description: string
  suggestion?: string
}

export interface RiskReview {
  issues: RiskIssue[]
  summary: string
}

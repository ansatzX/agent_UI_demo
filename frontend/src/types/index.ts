export interface Option {
  id: string
  label: string
  description: string
  action: string
  payload?: Record<string, any>
}

export interface Message {
  id?: number
  role: 'user' | 'assistant'
  content: string
  options?: Option[]
  timestamp?: string
  uploaded_file?: {
    filename: string
    original_filename?: string
    size?: number
    content?: any
  }
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

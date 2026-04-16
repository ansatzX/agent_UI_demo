// frontend/src/types/form.ts
export interface FormField {
  name: string
  label: string
  type: 'text' | 'number' | 'date' | 'select' | 'textarea'
  required?: boolean
  options?: string[]
  default?: string
  placeholder?: string
}

export interface FormDefinition {
  type: 'form'
  form_id: string
  title: string
  fields: FormField[]
}

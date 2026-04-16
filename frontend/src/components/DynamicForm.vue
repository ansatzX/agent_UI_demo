<!-- frontend/src/components/DynamicForm.vue -->
<template>
  <div class="dynamic-form">
    <h3 class="form-title">{{ formDef.title }}</h3>

    <form @submit.prevent="handleSubmit">
      <div
        v-for="field in formDef.fields"
        :key="field.name"
        class="form-field"
      >
        <label class="field-label">
          {{ field.label }}
          <span v-if="field.required" class="required">*</span>
        </label>

        <!-- 文本输入 -->
        <input
          v-if="field.type === 'text'"
          v-model="formData[field.name]"
          :placeholder="field.placeholder"
          :required="field.required"
          type="text"
          class="form-input"
        />

        <!-- 数字输入 -->
        <input
          v-else-if="field.type === 'number'"
          v-model.number="formData[field.name]"
          :required="field.required"
          type="number"
          class="form-input"
        />

        <!-- 日期选择 -->
        <input
          v-else-if="field.type === 'date'"
          v-model="formData[field.name]"
          :required="field.required"
          type="date"
          class="form-input"
        />

        <!-- 下拉选择 -->
        <select
          v-else-if="field.type === 'select'"
          v-model="formData[field.name]"
          :required="field.required"
          class="form-select"
        >
          <option value="">请选择</option>
          <option
            v-for="option in field.options"
            :key="option"
            :value="option"
          >
            {{ option }}
          </option>
        </select>

        <!-- 文本域 -->
        <textarea
          v-else-if="field.type === 'textarea'"
          v-model="formData[field.name]"
          :placeholder="field.placeholder"
          :required="field.required"
          class="form-textarea"
          rows="4"
        />
      </div>

      <button type="submit" class="submit-btn">提交</button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { FormDefinition } from '@/types/form'

const props = defineProps<{
  formDef: FormDefinition
}>()

const emit = defineEmits<{
  submit: [values: Record<string, any>]
}>()

// 初始化表单数据
const formData = ref<Record<string, any>>({})

onMounted(() => {
  // 设置默认值
  props.formDef.fields.forEach(field => {
    formData.value[field.name] = field.default || ''
  })
})

const handleSubmit = () => {
  emit('submit', formData.value)
}
</script>

<style scoped>
.dynamic-form {
  background: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
  margin: 10px 0;
}

.form-title {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #333;
}

.form-field {
  margin-bottom: 16px;
}

.field-label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: #555;
}

.required {
  color: #e74c3c;
  margin-left: 2px;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #3498db;
}

.submit-btn {
  width: 100%;
  padding: 12px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  margin-top: 10px;
}

.submit-btn:hover {
  background: #2980b9;
}
</style>

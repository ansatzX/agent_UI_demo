<template>
  <div v-if="error" class="error-boundary">
    <div class="error-content">
      <div class="error-icon">⚠️</div>
      <h2 class="error-title">出错了</h2>
      <p class="error-message">{{ error.message || '抱歉，页面遇到了一些问题' }}</p>
      <div class="error-actions">
        <button @click="resetError" class="retry-button">
          🔄 重试
        </button>
        <button @click="goHome" class="home-button">
          🏠 返回首页
        </button>
      </div>
    </div>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'

const error = ref<Error | null>(null)
const router = useRouter()

onErrorCaptured((err: Error) => {
  error.value = err
  console.error('Vue error:', err)
  return false // 阻止错误继续传播
})

const resetError = () => {
  error.value = null
}

const goHome = () => {
  error.value = null
  router.push('/')
}
</script>

<style scoped>
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.error-content {
  max-width: 500px;
  padding: 40px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  text-align: center;
}

.error-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.error-title {
  font-size: 28px;
  font-weight: bold;
  color: #2d3748;
  margin-bottom: 16px;
}

.error-message {
  font-size: 16px;
  color: #718096;
  margin-bottom: 32px;
  line-height: 1.6;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.retry-button,
.home-button {
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.retry-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
}

.home-button {
  background: #edf2f7;
  color: #4a5568;
}

.home-button:hover {
  background: #e2e8f0;
  transform: translateY(-2px);
}
</style>

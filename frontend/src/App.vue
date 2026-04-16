<template>
  <div id="app" class="app-container">
    <ContractWorkspace />
  </div>
</template>

<script setup lang="ts">
import ContractWorkspace from './views/ContractWorkspace.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.app-container {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}
</style>

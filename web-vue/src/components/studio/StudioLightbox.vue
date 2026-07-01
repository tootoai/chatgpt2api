<template>
  <Teleport to="body">
    <div v-if="preview" class="studio-lightbox" @click.self="$emit('close')">
      <button type="button" class="studio-lightbox-close" @click="$emit('close')">
        <Icon icon="lucide:x" class="h-5 w-5" />
      </button>
      <img :src="preview.src" :alt="preview.name" />
      <div class="studio-lightbox-actions">
        <span>{{ preview.name }}</span>
        <button type="button" @click="$emit('copy', preview.src)">
          <Icon icon="lucide:copy" class="h-3.5 w-3.5" />
          复制链接
        </button>
        <button type="button" @click="$emit('download')">
          <Icon icon="lucide:download" class="h-3.5 w-3.5" />
          下载
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { StudioPreviewImage } from './types'

defineProps<{
  preview: StudioPreviewImage | null
}>()

defineEmits<{
  close: []
  copy: [value: string]
  download: []
}>()
</script>

<style scoped>
.studio-lightbox {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(15 23 42 / 0.82);
  padding: 1.5rem;
}

.studio-lightbox img {
  max-width: min(92vw, 78rem);
  max-height: 82dvh;
  border-radius: 1rem;
  object-fit: contain;
  box-shadow: 0 24px 80px rgb(15 23 42 / 0.45);
}

.studio-lightbox-close {
  position: fixed;
  top: 1rem;
  right: 1rem;
  display: inline-flex;
  width: 2.5rem;
  height: 2.5rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.12);
  color: white;
  backdrop-filter: blur(12px);
}

.studio-lightbox-actions {
  position: fixed;
  left: 50%;
  bottom: 1rem;
  display: flex;
  max-width: calc(100vw - 2rem);
  transform: translateX(-50%);
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border-radius: 999px;
  background: rgb(15 23 42 / 0.72);
  padding: 0.55rem 0.75rem;
  color: white;
  font-size: 0.75rem;
  backdrop-filter: blur(12px);
}

.studio-lightbox-actions span {
  max-width: 18rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.studio-lightbox-actions button {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.12);
  padding: 0.35rem 0.65rem;
  font-weight: 650;
}
</style>

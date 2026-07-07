<template>
  <div class="markdown-body chat-markdown" dir="auto" v-html="html" @click="handleMarkdownClick"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderStudioMarkdown } from '@/lib/studioMarkdownRenderer'

const props = defineProps<{
  content: string
  status?: string
}>()

const emit = defineEmits<{
  'citation-click': [href: string]
}>()

const html = computed(() => {
  const isStreaming = props.status === 'streaming' || props.status === 'sending'
  return renderStudioMarkdown(props.content || '', { cache: !isStreaming })
})

async function handleMarkdownClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  const citationLink = target?.closest<HTMLAnchorElement>('a[href^="studio-citation:"]')
  if (citationLink) {
    event.preventDefault()
    emit('citation-click', citationLink.getAttribute('href') || '')
    return
  }
  const button = target?.closest<HTMLButtonElement>('.studio-code-copy')
  if (!button) return
  const block = button.closest('.studio-code-pre, .studio-code-block')
  const code = block?.querySelector('code')?.textContent || ''
  if (!code) return
  try {
    await writeClipboardText(code)
    button.textContent = '已复制'
    window.setTimeout(() => {
      button.textContent = '复制'
    }, 1200)
  } catch {
    button.textContent = '复制失败'
    window.setTimeout(() => {
      button.textContent = '复制'
    }, 1200)
  }
}

async function writeClipboardText(text: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'readonly')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  const ok = document.execCommand('copy')
  document.body.removeChild(textarea)
  if (!ok) throw new Error('copy failed')
}
</script>

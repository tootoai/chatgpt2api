<template>
  <section class="studio-chat-panel" :class="{ 'is-fullscreen': fullscreen }">
    <div ref="scrollEl" class="studio-chat-scroll custom-scrollbar" @scroll="handleScroll">
      <div v-if="!conversation || !conversation.messages.length" class="studio-chat-empty">
        <h1>对话画图</h1>
        <p>输入文字可以直接对话；切到画图后，在同一个窗口里生成图片、上传参考图和继续编辑。</p>
      </div>

      <div v-else class="studio-turns">
        <article
          v-for="message in conversation.messages"
          :key="message.id"
          class="chat-message-row"
          :class="message.role === 'user' ? 'is-user' : 'is-assistant'"
        >
          <div
            class="chat-message-container"
            :class="[
              message.role === 'user' ? 'is-user' : 'is-assistant',
              message.role === 'assistant' && message.mode === 'image' ? 'is-image-message' : '',
              isPendingImageMessage(message) ? 'is-pending-image-message' : '',
            ]"
          >
            <div class="chat-message-header" :class="{ 'is-user': message.role === 'user' }">
              <div
                class="chat-message-avatar"
                :class="{ 'chat-message-avatar-user': message.role === 'user' }"
                aria-hidden="true"
              >
                <Icon :icon="message.role === 'user' ? 'lucide:user' : 'lucide:bot'" class="h-4 w-4" />
              </div>

              <div class="chat-message-actions">
                <button
                  v-for="action in messageActions(message)"
                  :key="action.key"
                  type="button"
                  class="chat-input-action chat-message-action"
                  :class="{ 'chat-message-action-danger': action.danger }"
                  :title="action.label"
                  :aria-label="action.label"
                  @click="handleMessageAction(action.key, message)"
                >
                  <span class="icon"><Icon :icon="action.icon" class="h-3.5 w-3.5" /></span>
                  <span class="text">{{ action.label }}</span>
                </button>
              </div>
            </div>

            <div class="chat-message-bubble-wrap">
              <div
                class="chat-message-bubble"
                :class="[
                  message.role === 'user' ? 'chat-message-bubble-user' : 'chat-message-bubble-assistant',
                  message.role === 'assistant' && message.mode === 'image' ? 'chat-message-bubble-image' : '',
                  isPendingImageMessage(message) ? 'chat-message-bubble-image-pending' : '',
                  message.status === 'error' ? 'chat-message-bubble-error' : '',
                ]"
                :style="message.role === 'assistant' && message.mode === 'image' ? imagePreviewStyle(message) : undefined"
              >
                <div
                  class="chat-message-content"
                  :class="{
                    'is-collapsible': isCollapsibleMessage(message),
                    'is-collapsed': isMessageCollapsed(message),
                  }"
                >
                  <template v-if="message.role === 'user'">
                    <p v-if="message.content" class="studio-user-prompt">{{ message.content }}</p>
                    <div v-if="message.attachments?.length" class="studio-attachment-line">
                      <Icon icon="lucide:paperclip" class="h-3.5 w-3.5" />
                      {{ message.attachments.join('、') }}
                    </div>
                  </template>

                  <template v-else-if="message.mode === 'chat'">
                    <div
                      v-if="message.content || message.status === 'streaming'"
                      class="chat-markdown"
                      v-html="renderMarkdown(message.content || ' ')"
                      @click="handleMarkdownClick"
                    ></div>
                    <span v-if="message.status === 'streaming'" class="studio-cursor"></span>
                    <p v-if="message.error && !message.content.includes(message.error)" class="studio-error-text">
                      {{ message.error }}
                    </p>
                  </template>

                  <template v-else>
                    <template v-if="!taskForMessage(message) || taskForMessage(message)?.status === 'queued' || taskForMessage(message)?.status === 'running'">
                      <div class="studio-result-block studio-result-block-pending">
                        <div class="studio-result-grid" :class="{ 'is-single': imageSlotCount(message) <= 1 }">
                          <div
                            v-for="slot in pendingSlots(message)"
                            :key="`${message.id}-pending-${slot}`"
                            class="studio-result-item"
                          >
                            <div class="studio-result-media studio-result-placeholder">
                              <Icon icon="lucide:loader-circle" class="h-5 w-5 animate-spin" />
                              <span>正在处理图片</span>
                              <small>{{ imagePendingStageText(message) }}</small>
                            </div>
                            <div v-if="imageSlotCount(message) > 1" class="studio-result-caption">
                              <span>图片 {{ slot + 1 }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </template>

                    <template v-else>
                      <div v-if="taskForMessage(message)?.status === 'error'" class="studio-image-status is-error">
                        <Icon icon="lucide:circle-alert" class="h-4 w-4" />
                        <span>{{ primaryMessage(taskForMessage(message)) || '上游没有返回可用图片。' }}</span>
                      </div>

                      <div v-else class="studio-result-block">
                        <div class="studio-result-grid" :class="{ 'is-single': taskAssets(taskForMessage(message)).length <= 1 }">
                          <div
                            v-for="(asset, assetIndex) in taskAssets(taskForMessage(message))"
                            :key="`${message.id}-${assetIndex}`"
                            class="studio-result-item"
                          >
                            <button
                              type="button"
                              class="studio-result-media"
                              :class="{ 'has-image': Boolean(assetUrl(asset)) }"
                              @click="emit('preview', assetUrl(asset), `结果 ${assetIndex + 1}`, String(asset.path || ''))"
                            >
                              <img v-if="assetUrl(asset)" :src="assetUrl(asset)" :alt="`结果 ${assetIndex + 1}`" loading="lazy" />
                              <span v-else>无图片 URL</span>
                            </button>
                            <div v-if="taskAssets(taskForMessage(message)).length > 1" class="studio-result-caption">
                              <span>结果 {{ assetIndex + 1 }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </template>
                  </template>
                </div>

                <button
                  v-if="isCollapsibleMessage(message)"
                  type="button"
                  class="chat-message-expand"
                  @click.stop="toggleMessageExpanded(message)"
                >
                  {{ isMessageCollapsed(message) ? '展开全部' : '收起' }}
                  <Icon :icon="isMessageCollapsed(message) ? 'lucide:chevron-down' : 'lucide:chevron-up'" class="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
        </article>
      </div>
    </div>

    <button
      v-if="showScrollLatest"
      type="button"
      class="studio-scroll-latest"
      aria-label="滚动到最新消息"
      title="滚动到最新消息"
      @click="scrollToBottom"
    >
      <Icon icon="lucide:arrow-down" class="h-5 w-5" />
    </button>
  </section>
</template>

<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import css from 'highlight.js/lib/languages/css'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import markdownLang from 'highlight.js/lib/languages/markdown'
import python from 'highlight.js/lib/languages/python'
import shell from 'highlight.js/lib/languages/shell'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'
import { Icon } from '@iconify/vue'
import { computed, nextTick, ref, type CSSProperties } from 'vue'
import {
  imageAssetUrl,
  imageTaskProgressLabel,
  parseImageSize,
  taskPrimaryMessage,
  type ImageTask,
  type ImageTaskAsset,
} from '@/api/imageTasks'
import type { StudioConversation, StudioMessage } from './types'

const props = defineProps<{
  conversation: StudioConversation | null
  conversationsCount: number
  tasks: ImageTask[]
  fullscreen: boolean
}>()

const emit = defineEmits<{
  create: []
  'open-history': []
  'toggle-fullscreen': []
  retry: [message: StudioMessage]
  edit: [message: StudioMessage]
  resend: [message: StudioMessage]
  'retry-assistant': [message: StudioMessage]
  'delete-message': [messageId: string]
  'copy-message': [content: string]
  preview: [src: string, name: string, localPath?: string]
}>()

type MessageActionKey = 'copy' | 'edit' | 'resend' | 'fill' | 'retry' | 'delete'
interface MessageAction {
  key: MessageActionKey
  label: string
  icon: string
  danger?: boolean
}

const scrollEl = ref<HTMLElement | null>(null)
const showScrollLatest = ref(false)
const expandedMessageIds = ref<Set<string>>(new Set())
const collapsedMessageIds = ref<Set<string>>(new Set())
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('sh', shell)
hljs.registerLanguage('shell', shell)
hljs.registerLanguage('zsh', shell)
hljs.registerLanguage('css', css)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('vue', xml)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('jsonc', json)
hljs.registerLanguage('markdown', markdownLang)
hljs.registerLanguage('md', markdownLang)
hljs.registerLanguage('python', python)
hljs.registerLanguage('py', python)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('ts', typescript)
hljs.registerLanguage('tsx', typescript)
hljs.registerLanguage('yaml', yaml)
hljs.registerLanguage('yml', yaml)

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight: (code, language) => highlightCode(code, language),
})

markdown.renderer.rules.fence = (tokens, idx, options, env, self) => {
  const token = tokens[idx]
  const language = token.info.trim().split(/\s+/)[0] || 'text'
  const highlighted = options.highlight?.(token.content, language, '') || markdown.utils.escapeHtml(token.content)
  const langLabel = markdown.utils.escapeHtml(language)
  return `<div class="studio-code-block" data-language="${langLabel}">`
    + `<div class="studio-code-header"><span>${langLabel}</span><button type="button" class="studio-code-copy" title="复制代码">复制</button></div>`
    + `<pre class="hljs studio-code-pre"><code>${highlighted}</code></pre>`
    + `</div>`
}

const taskById = computed(() => new Map(props.tasks.map((task) => [task.id, task])))

function taskForMessage(message: StudioMessage) {
  return message.taskId ? taskById.value.get(message.taskId) : undefined
}

function taskAssets(task: ImageTask | undefined): ImageTaskAsset[] {
  if (!task?.data?.length) return []
  return task.data.filter((asset) => Boolean(assetUrl(asset)))
}

function assetUrl(asset: ImageTaskAsset) {
  return imageAssetUrl(asset)
}

function primaryMessage(task: ImageTask | undefined) {
  return taskPrimaryMessage(task)
}

function isPendingImageMessage(message: StudioMessage) {
  if (message.role !== 'assistant' || message.mode !== 'image') return false
  const task = taskForMessage(message)
  if (!task) return true
  if (task.status === 'success' || task.status === 'error') return false
  return taskAssets(task).length === 0
}

function imagePendingStageText(message: StudioMessage) {
  return imageTaskProgressLabel(taskForMessage(message))
}

function imageSlotCount(message: StudioMessage) {
  const task = taskForMessage(message)
  const assetCount = taskAssets(task).length
  const taskCount = Number(task?.n)
  const messageCount = Number(message.imageCount)
  if (task?.status === 'success' && assetCount > 0) {
    return Math.min(4, Math.max(1, assetCount))
  }
  const count = Math.max(
    1,
    Number.isFinite(taskCount) ? taskCount : 0,
    Number.isFinite(messageCount) ? messageCount : 0,
  )
  return Math.min(4, Math.max(1, Math.trunc(count)))
}

function pendingSlots(message: StudioMessage) {
  return Array.from({ length: imageSlotCount(message) }, (_, index) => index)
}

function imagePreviewStyle(message: StudioMessage): CSSProperties {
  const task = taskForMessage(message)
  const parsed = parseImageSize(task?.size || message.imageSize || '')
  const aspectRatio = parsed ? `${parsed.width} / ${parsed.height}` : '1 / 1'
  return {
    '--studio-image-aspect-ratio': aspectRatio,
    '--studio-image-grid-columns': String(Math.min(2, imageSlotCount(message))),
  } as CSSProperties
}

function normalizeCodeLanguage(language: string | undefined) {
  const value = String(language || '').trim().toLowerCase().replace(/^language-/, '')
  const aliases: Record<string, string> = {
    console: 'shell',
    powershell: 'shell',
    ps1: 'shell',
    plaintext: 'text',
    text: 'text',
  }
  return aliases[value] || value
}

function highlightCode(code: string, language: string | undefined) {
  const normalized = normalizeCodeLanguage(language)
  if (normalized && normalized !== 'text' && hljs.getLanguage(normalized)) {
    return hljs.highlight(code, { language: normalized, ignoreIllegals: true }).value
  }
  return markdown.utils.escapeHtml(code)
}

async function handleMarkdownClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  const button = target?.closest<HTMLButtonElement>('.studio-code-copy')
  if (!button) return
  const block = button.closest('.studio-code-block')
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

function renderMarkdown(content: string) {
  return markdown.render(content || '')
}

function isTextLikeMessage(message: StudioMessage) {
  return message.role === 'user' || message.mode === 'chat' || message.status === 'error'
}

function isCollapsibleMessage(message: StudioMessage) {
  if (!isTextLikeMessage(message)) return false
  const content = String(message.content || message.error || '')
  if (!content.trim()) return false
  return content.length > 420 || content.split(/\r?\n/).length > 8
}

function isMessageCollapsed(message: StudioMessage) {
  if (!isCollapsibleMessage(message)) return false
  if (message.role === 'assistant') return collapsedMessageIds.value.has(message.id)
  return !expandedMessageIds.value.has(message.id)
}

function toggleMessageExpanded(message: StudioMessage) {
  if (message.role === 'assistant') {
    const next = new Set(collapsedMessageIds.value)
    if (next.has(message.id)) next.delete(message.id)
    else next.add(message.id)
    collapsedMessageIds.value = next
    return
  }
  const next = new Set(expandedMessageIds.value)
  if (next.has(message.id)) next.delete(message.id)
  else next.add(message.id)
  expandedMessageIds.value = next
}

function messageActions(message: StudioMessage): MessageAction[] {
  const actions: MessageAction[] = []
  if (message.content) actions.push({ key: 'copy', label: '复制', icon: 'lucide:copy' })
  if (message.role === 'user') {
    if (message.content) actions.push({ key: 'edit', label: '编辑', icon: 'lucide:pencil' })
    actions.push({ key: 'resend', label: '重发', icon: 'lucide:refresh-cw' })
    if (message.content) actions.push({ key: 'fill', label: '填入', icon: 'lucide:clipboard-paste' })
  } else if (message.mode === 'chat' || message.status === 'error') {
    actions.push({ key: 'retry', label: '重试', icon: 'lucide:refresh-cw' })
  }
  actions.push({ key: 'delete', label: '删除', icon: 'lucide:trash-2', danger: true })
  return actions
}

function handleMessageAction(action: MessageActionKey, message: StudioMessage) {
  if (action === 'copy') emit('copy-message', message.content)
  else if (action === 'edit') emit('edit', message)
  else if (action === 'resend') emit('resend', message)
  else if (action === 'fill') emit('retry', message)
  else if (action === 'retry') emit('retry-assistant', message)
  else if (action === 'delete') emit('delete-message', message.id)
}

function handleScroll() {
  const el = scrollEl.value
  if (!el) return
  showScrollLatest.value = el.scrollHeight - el.scrollTop - el.clientHeight > 160
}

function scrollToBottom() {
  const el = scrollEl.value
  if (!el) return
  el.scrollTop = el.scrollHeight
  showScrollLatest.value = false
}

defineExpose({
  scrollToBottom: () => nextTick(scrollToBottom),
})
</script>

<style scoped>
.studio-chat-panel {
  position: relative;
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  --studio-image-slot-size: clamp(12rem, 28vw, 18rem);
  --studio-image-aspect-ratio: 1 / 1;
  --studio-image-grid-columns: 1;
}

.studio-chat-scroll {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 1rem clamp(0.75rem, 2.4vw, 1.75rem) 1rem;
}

.studio-chat-empty {
  display: flex;
  min-height: calc(100% - 1rem);
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: clamp(2rem, 7vh, 5rem) 1rem 1rem;
  text-align: center;
}

.studio-chat-panel.is-fullscreen .studio-chat-empty {
  padding-top: clamp(3rem, 10vh, 7rem);
}

.studio-chat-empty h1 {
  color: hsl(var(--foreground));
  font-size: clamp(1.8rem, 5vw, 3.2rem);
  font-weight: 700;
  letter-spacing: 0;
}

.studio-chat-empty p {
  margin-top: 0.875rem;
  max-width: 34rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  line-height: 1.8;
}

.studio-turns {
  margin: 0 auto;
  display: flex;
  width: var(--studio-content-width);
  flex-direction: column;
  gap: 1.25rem;
  padding-bottom: 0.5rem;
}

.chat-message-row {
  display: flex;
}

.chat-message-row.is-user {
  justify-content: flex-end;
}

.chat-message-row.is-assistant {
  justify-content: flex-start;
}

.chat-message-container {
  display: flex;
  min-width: 0;
  max-width: min(100%, 44rem);
  width: fit-content;
  flex-direction: column;
}

.chat-message-container.is-pending-image-message {
  width: fit-content;
  min-width: 0;
  max-width: 100%;
}

.chat-message-container.is-user {
  align-items: flex-end;
}

.chat-message-container.is-assistant {
  align-items: flex-start;
}

.chat-message-header {
  display: flex;
  min-height: 1.75rem;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.chat-message-header.is-user {
  flex-direction: row-reverse;
}

.chat-message-avatar {
  display: flex;
  width: 1.75rem;
  height: 1.75rem;
  flex: 0 0 1.75rem;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--ui-control-border, hsl(var(--border)));
  border-radius: 999px;
  background: var(--ui-control-bg, hsl(var(--background)));
  color: var(--ui-fg-muted, hsl(var(--muted-foreground)));
  font-size: 0.6875rem;
  font-weight: 600;
}

.chat-message-avatar-user {
  border-color: var(--ui-accent-border, hsl(var(--foreground) / 0.18));
  background: var(--ui-accent-soft, hsl(var(--secondary)));
  color: var(--ui-accent-strong, hsl(var(--foreground)));
}

.chat-message-actions {
  display: flex;
  min-width: 0;
  max-width: min(26rem, calc(100vw - 8rem));
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
  opacity: 1;
  transition: opacity var(--ui-duration-normal, 180ms) var(--ui-ease-out, ease);
}

@media (min-width: 640px) {
  .chat-message-actions {
    pointer-events: none;
    opacity: 0;
  }

  .chat-message-container:hover .chat-message-actions,
  .chat-message-container:focus-within .chat-message-actions {
    pointer-events: auto;
    opacity: 1;
  }
}

.chat-input-action {
  display: inline-flex;
  box-sizing: border-box;
  min-height: 1.625rem;
  height: 1.625rem;
  align-items: center;
  justify-content: center;
  gap: 0.3125rem;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: var(--ui-fg-muted, hsl(var(--muted-foreground)));
  padding: 0.25rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}

.chat-input-action:hover,
.chat-input-action:focus-visible {
  border-color: var(--ui-control-hover-border, hsl(var(--foreground) / 0.18));
  background: var(--ui-control-hover-bg, hsl(var(--secondary)));
  color: var(--ui-fg-strong, hsl(var(--foreground)));
}

.chat-input-action .icon {
  display: inline-flex;
  width: 1rem;
  height: 1rem;
  flex: 0 0 1rem;
  align-items: center;
  justify-content: center;
  line-height: 0;
}

.chat-input-action .text {
  display: inline-block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  pointer-events: none;
}

.chat-message-action {
  width: 1.85rem;
  min-width: 1.85rem;
  height: 1.85rem;
  min-height: 1.85rem;
  padding: 0.25rem;
}

.chat-message-action .text {
  display: none;
}

.chat-message-action-danger:hover,
.chat-message-action-danger:focus-visible {
  border-color: var(--ui-danger-border, rgb(248 113 113 / 0.32));
  background: var(--ui-danger-bg, rgb(254 242 242 / 0.86));
  color: var(--ui-danger-fg, rgb(220 38 38));
}

.chat-message-bubble {
  max-width: 100%;
  border: 1px solid var(--ui-panel-border, hsl(var(--border)));
  border-radius: 18px;
  background: var(--ui-panel-bg, hsl(var(--card)));
  box-shadow: var(--ui-panel-shadow, 0 8px 24px rgb(15 23 42 / 0.045));
  color: var(--ui-fg-strong, hsl(var(--foreground)));
  padding: 0.625rem 0.875rem;
  font-size: 0.875rem;
  line-height: 1.75;
}

.chat-message-bubble-wrap {
  position: relative;
  max-width: 100%;
}

.chat-message-content {
  position: relative;
  max-width: 100%;
  overflow-wrap: anywhere;
}

.chat-message-content.is-collapsible {
  overflow: hidden;
  transition: max-height 0.18s ease;
}

.chat-message-content.is-collapsed {
  max-height: 12rem;
}

.chat-message-content.is-collapsed::after {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 3.25rem;
  pointer-events: none;
  background: linear-gradient(180deg, transparent, var(--studio-bubble-fade-bg, hsl(var(--card))));
  content: '';
}

.chat-message-expand {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-top: 0.5rem;
  border-radius: 999px;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 650;
  line-height: 1;
  transition: color 0.15s, background 0.15s;
}

.chat-message-expand:hover,
.chat-message-expand:focus-visible {
  color: hsl(var(--foreground));
}

.chat-message-bubble-user {
  --studio-bubble-fade-bg: hsl(var(--secondary));
  border-color: var(--ui-accent-border, hsl(var(--foreground) / 0.16));
  background: var(--ui-accent-soft, hsl(var(--secondary)));
}

.chat-message-bubble-assistant {
  --studio-bubble-fade-bg: hsl(var(--card));
  border-color: var(--ui-panel-border, hsl(var(--border)));
}

.chat-message-bubble-image {
  width: fit-content;
  min-width: 0;
  padding: 0.75rem;
}

.chat-message-bubble-image-pending {
  padding: 0.75rem;
}

.chat-message-bubble-error {
  --studio-bubble-fade-bg: rgb(254 242 242);
  border-color: rgb(254 202 202);
  background: rgb(254 242 242);
}

.studio-user-prompt {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.studio-attachment-line {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-top: 0.45rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.chat-markdown {
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.chat-markdown :deep(> :first-child) {
  margin-top: 0;
}

.chat-markdown :deep(> :last-child) {
  margin-bottom: 0;
}

.chat-markdown :deep(p) {
  margin: 0.35rem 0;
}

.chat-markdown :deep(ul),
.chat-markdown :deep(ol) {
  margin: 0.55rem 0;
  padding-left: 1.25rem;
}

.chat-markdown :deep(ul) {
  list-style: disc;
}

.chat-markdown :deep(ol) {
  list-style: decimal;
}

.chat-markdown :deep(li) {
  margin: 0.25rem 0;
}

.chat-markdown :deep(blockquote) {
  margin: 0.75rem 0;
  border-left: 3px solid rgb(113 113 122 / 0.32);
  padding-left: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.chat-markdown :deep(pre) {
  overflow-x: auto;
  overflow-wrap: normal;
  word-break: normal;
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
  background: hsl(var(--muted) / 0.45);
  padding: 0.75rem;
  font-size: 0.8125rem;
}

.chat-markdown :deep(code) {
  border-radius: 0.35rem;
  background: hsl(var(--muted) / 0.55);
  padding: 0.1rem 0.25rem;
  font-size: 0.84em;
}

.chat-markdown :deep(pre code) {
  background: transparent;
  padding: 0;
}

.chat-markdown :deep(.studio-code-block) {
  margin: 0.75rem 0;
  overflow: hidden;
  border: 1px solid hsl(var(--border));
  border-radius: 0.875rem;
  background: hsl(var(--muted) / 0.36);
}

.chat-markdown :deep(.studio-code-header) {
  display: flex;
  min-height: 2.25rem;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  border-bottom: 1px solid hsl(var(--border));
  background: hsl(var(--background) / 0.72);
  padding: 0.35rem 0.5rem 0.35rem 0.75rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.72rem;
  font-weight: 650;
  line-height: 1;
}

.chat-markdown :deep(.studio-code-copy) {
  display: inline-flex;
  height: 1.55rem;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 0 0.625rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.72rem;
  font-weight: 650;
  line-height: 1;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.chat-markdown :deep(.studio-code-copy:hover),
.chat-markdown :deep(.studio-code-copy:focus-visible) {
  border-color: hsl(var(--foreground) / 0.14);
  background: hsl(var(--secondary));
  color: hsl(var(--foreground));
}

.chat-markdown :deep(.studio-code-pre) {
  margin: 0;
  overflow-x: auto;
  border: 0;
  border-radius: 0;
  background: transparent;
  padding: 0.75rem 0.875rem;
  color: hsl(var(--foreground));
  font-size: 0.78rem;
  line-height: 1.65;
}

.chat-markdown :deep(.studio-code-pre code) {
  display: block;
  min-width: max-content;
  background: transparent;
  padding: 0;
  font-family: var(--font-ui-mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace);
}

.chat-markdown :deep(.hljs-comment),
.chat-markdown :deep(.hljs-quote) {
  color: #6b7280;
}

.chat-markdown :deep(.hljs-keyword),
.chat-markdown :deep(.hljs-selector-tag),
.chat-markdown :deep(.hljs-subst) {
  color: #7c3aed;
}

.chat-markdown :deep(.hljs-string),
.chat-markdown :deep(.hljs-doctag) {
  color: #047857;
}

.chat-markdown :deep(.hljs-number),
.chat-markdown :deep(.hljs-literal),
.chat-markdown :deep(.hljs-variable),
.chat-markdown :deep(.hljs-template-variable),
.chat-markdown :deep(.hljs-tag .hljs-attr) {
  color: #b45309;
}

.chat-markdown :deep(.hljs-title),
.chat-markdown :deep(.hljs-section),
.chat-markdown :deep(.hljs-selector-id) {
  color: #2563eb;
}

.chat-markdown :deep(.hljs-type),
.chat-markdown :deep(.hljs-class .hljs-title) {
  color: #0f766e;
}

.chat-markdown :deep(.hljs-tag),
.chat-markdown :deep(.hljs-name),
.chat-markdown :deep(.hljs-attribute) {
  color: #be123c;
}

.studio-error-text {
  margin-top: 0.45rem;
  color: rgb(190 18 60);
  font-size: 0.8125rem;
  line-height: 1.6;
}

.studio-cursor {
  display: inline-block;
  width: 0.45rem;
  height: 1rem;
  border-radius: 999px;
  background: hsl(var(--primary));
  animation: studio-cursor 1s ease-in-out infinite;
}

@keyframes studio-cursor {
  0%, 100% { opacity: 0.2; }
  50% { opacity: 1; }
}

.studio-image-status {
  display: flex;
  min-width: 0;
  width: 100%;
  min-height: 3.25rem;
  align-items: center;
  gap: 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  line-height: 1.6;
}

.studio-image-status.is-error {
  align-items: flex-start;
  color: rgb(185 28 28);
}

.studio-result-block {
  display: inline-block;
  max-width: 100%;
}

.studio-result-grid {
  display: grid;
  width: fit-content;
  max-width: 100%;
  grid-template-columns: repeat(var(--studio-image-grid-columns), minmax(0, var(--studio-image-slot-size)));
  gap: 0.625rem;
}

.studio-result-grid.is-single {
  grid-template-columns: minmax(0, var(--studio-image-slot-size));
}

.studio-result-item {
  width: var(--studio-image-slot-size);
  min-width: 0;
}

.studio-result-grid.is-single .studio-result-item {
  width: var(--studio-image-slot-size);
}

.studio-result-media {
  display: flex;
  width: 100%;
  aspect-ratio: var(--studio-image-aspect-ratio);
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: 0.75rem;
  background: hsl(var(--secondary) / 0.35);
  color: inherit;
  cursor: zoom-in;
}

.studio-result-media.has-image {
  background: hsl(var(--secondary) / 0.18);
  padding: 0;
}

.studio-result-media img {
  display: block;
  width: 100%;
  height: 100%;
  max-width: none;
  max-height: none;
  border-radius: 0.75rem;
  object-fit: contain;
}

.studio-result-media span {
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
}

.studio-result-placeholder {
  cursor: default;
  flex-direction: column;
  gap: 0.625rem;
  text-align: center;
}

.studio-result-placeholder svg {
  color: hsl(var(--muted-foreground));
}

.studio-result-placeholder span,
.studio-result-placeholder small {
  display: block;
  max-width: calc(100% - 1rem);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.studio-result-placeholder small {
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: 0.75rem;
}

.studio-result-caption {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
  padding: 0.35rem 0.125rem 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.studio-scroll-latest {
  position: absolute;
  left: 50%;
  bottom: 1rem;
  z-index: 30;
  display: inline-flex;
  width: 2.75rem;
  height: 2.75rem;
  transform: translateX(-50%);
  align-items: center;
  justify-content: center;
  border: 1px solid hsl(var(--border));
  border-radius: 999px;
  background: hsl(var(--card) / 0.95);
  color: hsl(var(--foreground));
  box-shadow: 0 18px 42px -24px rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(10px);
}

@media (max-width: 720px) {
  .studio-chat-scroll {
    padding: 0.75rem;
  }

  .studio-turns {
    gap: 1rem;
  }

  .chat-message-container {
    max-width: min(100%, 38rem);
  }

  .chat-message-container.is-pending-image-message {
    width: fit-content;
    min-width: 0;
    max-width: 100%;
  }

  .studio-chat-panel {
    --studio-image-slot-size: min(14rem, calc(100vw - 5.5rem));
  }

  .studio-result-grid {
    grid-template-columns: minmax(0, var(--studio-image-slot-size));
  }

  .chat-message-actions {
    max-width: calc(100vw - 5.5rem);
    overflow-x: auto;
    overflow-y: hidden;
    padding-bottom: 1px;
  }
}
</style>

<template>
  <article
    class="chat-message-row"
    :class="message.role === 'user' ? 'is-user' : 'is-assistant'"
  >
    <div
      class="chat-message-container"
      :class="[
        message.role === 'user' ? 'is-user' : 'is-assistant',
        message.isImageMessage ? 'is-image-message' : '',
        message.isPendingImageMessage ? 'is-pending-image-message' : '',
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
            v-for="action in actionsForMessage(message)"
            :key="action.key"
            type="button"
            class="chat-input-action chat-message-action"
            :class="{ 'chat-message-action-danger': action.danger }"
            :title="action.label"
            :aria-label="action.label"
            @click="$emit('action', action.key, message)"
          >
            <span class="icon"><Icon :icon="action.icon" class="h-3.5 w-3.5" /></span>
            <span class="text">{{ action.label }}</span>
          </button>
        </div>
      </div>

      <div class="chat-message-bubble-wrap">
        <div
          v-if="isStandaloneErrorMessage(message)"
          class="chat-message-error-card"
          role="alert"
        >
          <Icon icon="lucide:circle-alert" class="chat-message-error-icon h-4 w-4" />
          <p>{{ standaloneErrorText(message) }}</p>
        </div>
        <div
          v-else
          class="chat-message-bubble"
          :class="[
            message.role === 'user' ? 'chat-message-bubble-user' : 'chat-message-bubble-assistant',
            message.isImageMessage ? 'chat-message-bubble-image' : '',
            message.isPendingImageMessage ? 'chat-message-bubble-image-pending' : '',
            message.status === 'error' ? 'chat-message-bubble-error' : '',
          ]"
          :style="message.imagePreviewStyle"
        >
          <div
            class="chat-message-content"
            :class="{
              'is-collapsible': message.isCollapsible,
              'is-collapsed': message.isCollapsed,
              'is-markdown': message.role !== 'user' && message.mode !== 'image',
            }"
          >
            <template v-if="message.role === 'user'">
              <p v-if="message.content" class="studio-user-prompt">{{ message.content }}</p>
              <div v-if="message.attachments?.length" class="studio-attachment-line">
                <Icon icon="lucide:paperclip" class="h-3.5 w-3.5" />
                {{ message.attachments.join('、') }}
              </div>
            </template>

            <template v-else-if="message.mode !== 'image'">
              <StudioMarkdownContent
                v-if="message.content || message.status === 'streaming'"
                :content="message.markdownContent || ' '"
                :status="message.status"
                @citation-click="$emit('citation-click', $event)"
              />
              <span v-if="message.status === 'streaming'" class="studio-cursor"></span>
              <p v-if="message.error && !message.content.includes(message.error)" class="studio-error-text">
                {{ message.error }}
              </p>
              <button
                v-if="message.mode === 'search' && message.searchSources?.length"
                type="button"
                class="studio-search-source-chip"
                @click="$emit('open-search-sources', message)"
              >
                <Icon icon="lucide:external-link" class="studio-search-source-chip-icon" />
                <span class="studio-search-source-chip-label">参考来源</span>
                <strong>{{ message.searchSources.length }}</strong>
                <small>查看</small>
              </button>
              <div v-if="message.mode === 'search' && message.searchImageGroups?.length" class="studio-search-image-groups">
                <div
                  v-for="(group, groupIndex) in message.searchImageGroups"
                  :key="`${message.id}-image-group-${groupIndex}`"
                  class="studio-search-image-group"
                >
                  <span class="studio-search-image-group-title">
                    <Icon icon="lucide:image" class="h-3.5 w-3.5" />
                    图片参考<span v-if="group.aspectRatio"> {{ group.aspectRatio }}</span>
                  </span>
                  <span class="studio-search-image-group-queries">
                    <span v-for="query in group.queries" :key="query" class="studio-search-image-query">{{ query }}</span>
                  </span>
                </div>
              </div>
            </template>

            <template v-else>
              <template v-if="!message.task || message.task.status === 'queued' || message.task.status === 'running'">
                <div class="studio-result-block studio-result-block-pending">
                  <div class="studio-result-grid" :class="{ 'is-single': message.imageSlotCount <= 1 }">
                    <div
                      v-for="slot in message.pendingSlots"
                      :key="`${message.id}-pending-${slot}`"
                      class="studio-result-item"
                    >
                      <div class="studio-result-media studio-result-placeholder">
                        <Icon icon="lucide:loader-circle" class="h-5 w-5 animate-spin" />
                        <span>正在处理图片</span>
                        <small>{{ message.imagePendingStageText }}</small>
                      </div>
                      <div v-if="message.imageSlotCount > 1" class="studio-result-caption">
                        <span>图片 {{ slot + 1 }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </template>

              <template v-else>
                <div v-if="message.task?.status === 'error'" class="studio-image-status is-error">
                  <Icon icon="lucide:circle-alert" class="h-4 w-4" />
                  <span>{{ message.primaryMessage || '上游没有返回可用图片。' }}</span>
                </div>

                <div v-else class="studio-result-block">
                  <div class="studio-result-grid" :class="{ 'is-single': message.assets.length <= 1 }">
                    <div
                      v-for="(asset, assetIndex) in message.assets"
                      :key="`${message.id}-${assetIndex}`"
                      class="studio-result-item"
                    >
                      <button
                        type="button"
                        class="studio-result-media"
                        :class="{ 'has-image': Boolean(asset.url) }"
                        @click="$emit('preview', asset.url, `结果 ${assetIndex + 1}`, asset.path)"
                      >
                        <img v-if="asset.url" :src="asset.url" :alt="`结果 ${assetIndex + 1}`" loading="lazy" />
                        <span v-else>无图片 URL</span>
                      </button>
                      <div v-if="message.assets.length > 1" class="studio-result-caption">
                        <span>结果 {{ assetIndex + 1 }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </template>
          </div>

          <button
            v-if="message.isCollapsible"
            type="button"
            class="chat-message-expand"
            @click.stop="$emit('toggle-expanded', message)"
          >
            {{ message.isCollapsed ? '展开全部' : '收起' }}
            <Icon :icon="message.isCollapsed ? 'lucide:chevron-down' : 'lucide:chevron-up'" class="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { CSSProperties } from 'vue'
import type { ImageTask } from '@/api/imageTasks'
import StudioMarkdownContent from './StudioMarkdownContent.vue'
import type { StudioMessage } from './types'

export type StudioMessageActionKey = 'copy' | 'edit' | 'resend' | 'fill' | 'retry' | 'delete'

export interface StudioMessageAction {
  key: StudioMessageActionKey
  label: string
  icon: string
  danger?: boolean
}

export interface StudioImageAssetView {
  url: string
  path: string
}

export type StudioMessageView = StudioMessage & {
  memoKey: string
  task?: ImageTask
  assets: StudioImageAssetView[]
  isImageMessage: boolean
  isPendingImageMessage: boolean
  imageSlotCount: number
  pendingSlots: number[]
  imagePendingStageText: string
  primaryMessage: string
  imagePreviewStyle?: CSSProperties
  isCollapsible: boolean
  isCollapsed: boolean
  markdownContent: string
}

defineProps<{
  message: StudioMessageView
}>()

defineEmits<{
  action: [key: StudioMessageActionKey, message: StudioMessage]
  'toggle-expanded': [message: StudioMessage]
  'open-search-sources': [message: StudioMessage]
  'citation-click': [href: string]
  preview: [src: string, name: string, localPath?: string]
}>()

function actionsForMessage(message: StudioMessageView): StudioMessageAction[] {
  const actions: StudioMessageAction[] = []
  if (message.content) actions.push({ key: 'copy', label: '复制', icon: 'lucide:copy' })
  if (message.role === 'user') {
    if (message.content) actions.push({ key: 'edit', label: '编辑', icon: 'lucide:pencil' })
    actions.push({ key: 'resend', label: '重发', icon: 'lucide:refresh-cw' })
    if (message.content) actions.push({ key: 'fill', label: '填入', icon: 'lucide:clipboard-paste' })
  } else if (message.mode !== 'image' || message.status === 'error') {
    actions.push({ key: 'retry', label: '重试', icon: 'lucide:refresh-cw' })
  }
  actions.push({ key: 'delete', label: '删除', icon: 'lucide:trash-2', danger: true })
  return actions
}

function textValue(value: string | null | undefined) {
  return String(value || '').trim()
}

function isStandaloneErrorMessage(message: StudioMessageView) {
  if (message.role !== 'assistant' || message.mode === 'image' || message.status !== 'error') return false
  const content = textValue(message.content)
  const error = textValue(message.error)
  return !content || content === error
}

function standaloneErrorText(message: StudioMessageView) {
  return textValue(message.error) || textValue(message.content) || '请求失败，请稍后重试。'
}
</script>

<style scoped>
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
  inline-size: min(100%, var(--studio-image-message-width, 22rem));
  min-width: 0;
  max-width: 100%;
}

.chat-message-container.is-image-message {
  inline-size: min(100%, var(--studio-image-message-width, 22rem));
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

.chat-message-error-card {
  display: flex;
  max-width: min(100%, 44rem);
  align-items: flex-start;
  gap: 0.55rem;
  border: 1px solid rgb(254 202 202);
  border-radius: 14px;
  background: rgb(254 242 242);
  color: rgb(190 18 60);
  padding: 0.62rem 0.78rem;
  font-size: 0.835rem;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.chat-message-error-card p {
  margin: 0;
}

.chat-message-error-icon {
  flex: 0 0 auto;
  margin-top: 0.15rem;
}

.chat-message-container.is-image-message .chat-message-bubble-wrap {
  width: 100%;
}

.chat-message-content {
  position: relative;
  max-width: 100%;
  overflow-wrap: anywhere;
}

.chat-message-content.is-markdown {
  overflow-wrap: normal;
}

.chat-message-container.is-image-message .chat-message-content {
  width: 100%;
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
  box-sizing: border-box;
  inline-size: 100%;
  min-width: 0;
  padding: 0.75rem;
}

.chat-message-bubble-image-pending {
  box-sizing: border-box;
  inline-size: 100%;
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

.studio-assistant-plain {
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

.studio-search-source-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.42rem;
  margin-top: 0.65rem;
  border: 1px solid hsl(var(--primary) / 0.18);
  border-radius: 999px;
  background:
    linear-gradient(135deg, hsl(var(--primary) / 0.1), hsl(var(--muted) / 0.42));
  color: hsl(var(--foreground));
  padding: 0.34rem 0.68rem 0.34rem 0.5rem;
  font-size: 0.72rem;
  font-weight: 720;
  line-height: 1;
  box-shadow: 0 8px 22px hsl(var(--primary) / 0.08);
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s, transform 0.15s;
}

.studio-search-source-chip-icon {
  display: inline-flex;
  width: 0.9rem;
  height: 0.9rem;
  flex: 0 0 0.9rem;
  color: hsl(var(--primary));
}

.studio-search-source-chip-label {
  color: hsl(var(--foreground));
}

.studio-search-source-chip strong {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.15rem;
  height: 1.15rem;
  border-radius: 999px;
  background: hsl(var(--primary) / 0.13);
  color: hsl(var(--primary));
  font-size: 0.68rem;
  font-weight: 820;
}

.studio-search-source-chip small {
  border-left: 1px solid hsl(var(--primary) / 0.16);
  padding-left: 0.42rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.68rem;
  font-weight: 780;
}

.studio-search-source-chip:hover,
.studio-search-source-chip:focus-visible {
  border-color: hsl(var(--primary) / 0.34);
  background:
    linear-gradient(135deg, hsl(var(--primary) / 0.14), hsl(var(--secondary) / 0.72));
  box-shadow: 0 10px 26px hsl(var(--primary) / 0.12);
  transform: translateY(-1px);
}

.studio-search-image-groups {
  display: grid;
  gap: 0.45rem;
  margin-top: 0.65rem;
}

.studio-search-image-group {
  display: grid;
  gap: 0.42rem;
  border: 1px solid hsl(var(--border) / 0.68);
  border-radius: 0.78rem;
  background: hsl(var(--muted) / 0.32);
  padding: 0.56rem 0.62rem;
}

.studio-search-image-group-title {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: hsl(var(--foreground));
  font-size: 0.72rem;
  font-weight: 780;
  line-height: 1;
}

.studio-search-image-group-title svg {
  color: hsl(var(--primary));
}

.studio-search-image-group-queries {
  display: flex;
  flex-wrap: wrap;
  gap: 0.32rem;
}

.studio-search-image-query {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 1px solid hsl(var(--border) / 0.62);
  border-radius: 999px;
  background: hsl(var(--background) / 0.72);
  padding: 0.24rem 0.48rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.68rem;
  font-weight: 650;
}

.chat-message-bubble :deep(a[href^='studio-citation:']) {
  display: inline-flex;
  min-width: 1.12rem;
  height: 1.12rem;
  align-items: center;
  justify-content: center;
  margin: 0 0.08rem;
  border: 1px solid var(--ui-accent-border, hsl(var(--primary) / 0.28));
  border-radius: 999px;
  background: var(--ui-accent-soft, hsl(var(--primary) / 0.08));
  color: var(--ui-accent-strong, hsl(var(--primary)));
  font-size: 0.68em;
  font-weight: 800;
  line-height: 1;
  text-decoration: none;
  vertical-align: super;
}

.chat-message-bubble :deep(a[href^='studio-citation:']:hover),
.chat-message-bubble :deep(a[href^='studio-citation:']:focus-visible) {
  border-color: var(--ui-accent-border, hsl(var(--primary) / 0.5));
  background: hsl(var(--primary) / 0.12);
}

.chat-message-bubble :deep(.chat-markdown) {
  min-width: 0;
  color: inherit;
  line-height: 1.5;
  overflow-wrap: anywhere;
  word-wrap: break-word;
  word-break: normal;
}

.chat-message-bubble :deep(.chat-markdown > :first-child) {
  margin-top: 0;
}

.chat-message-bubble :deep(.chat-markdown > :last-child) {
  margin-bottom: 0;
}

.chat-message-bubble :deep(.chat-markdown p) {
  margin: 0 0 10px;
}

.chat-message-bubble :deep(.chat-markdown ul),
.chat-message-bubble :deep(.chat-markdown ol) {
  margin: 0.55rem 0;
  padding-left: 1.25rem;
}

.chat-message-bubble :deep(.chat-markdown ul) {
  list-style: disc;
}

.chat-message-bubble :deep(.chat-markdown ol) {
  list-style: decimal;
}

.chat-message-bubble :deep(.chat-markdown li) {
  margin: 0.25rem 0;
}

.chat-message-bubble :deep(.chat-markdown blockquote) {
  margin: 0.75rem 0;
  border-left: 3px solid rgb(113 113 122 / 0.32);
  padding-left: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.chat-message-bubble :deep(.chat-markdown pre) {
  box-sizing: border-box;
  max-width: 100%;
  max-height: min(60vh, 28rem);
  margin: 0 0 16px;
  overflow: auto;
  overflow-wrap: normal;
  word-break: normal;
  border: 0;
  border-radius: 6px;
  background: hsl(var(--muted) / 0.48);
  padding: 16px 16px 8px;
  color: hsl(var(--foreground));
  direction: ltr;
  font-family: var(--font-ui-mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace);
  font-size: 85%;
  line-height: 1.45;
  tab-size: 2;
  text-align: left;
}

.chat-message-bubble :deep(.chat-markdown code) {
  border-radius: 0.35rem;
  background: hsl(var(--muted) / 0.55);
  padding: 0.1rem 0.25rem;
  font-size: 0.84em;
}

.chat-message-bubble :deep(.chat-markdown pre code) {
  display: inline-block;
  min-width: max-content;
  max-width: none;
  overflow-x: visible;
  overflow-wrap: normal;
  word-break: normal;
  white-space: pre;
  background: transparent;
  border: 0;
  padding: 0;
  line-height: inherit;
}

.chat-message-bubble :deep(.studio-code-block) {
  position: relative;
  max-width: 100%;
  margin: 0 0 16px;
}

.chat-message-bubble :deep(.studio-code-copy) {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  z-index: 1;
  display: inline-flex;
  height: 1.45rem;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  border: 1px solid hsl(var(--border));
  border-radius: 6px;
  background: hsl(var(--background) / 0.94);
  padding: 0 0.45rem;
  color: hsl(var(--foreground));
  cursor: pointer;
  font-size: 0.68rem;
  font-weight: 650;
  line-height: 1;
  opacity: 0;
  transform: translateX(6px);
  transition: opacity 0.15s, transform 0.15s, background 0.15s, border-color 0.15s, color 0.15s;
}

.chat-message-bubble :deep(.studio-code-block:hover .studio-code-copy),
.chat-message-bubble :deep(.studio-code-block:focus-within .studio-code-copy),
.chat-message-bubble :deep(.studio-code-copy:hover),
.chat-message-bubble :deep(.studio-code-copy:focus-visible) {
  pointer-events: auto;
  opacity: 0.82;
  transform: translateX(0);
  border-color: hsl(var(--foreground) / 0.14);
  background: hsl(var(--background));
  color: hsl(var(--foreground));
}

.chat-message-bubble :deep(.studio-code-pre) {
  margin: 0;
  overflow: auto;
  white-space: pre;
}

.chat-message-bubble :deep(.studio-code-pre code) {
  display: inline-block;
  min-width: max-content;
  white-space: pre;
}

.chat-message-bubble :deep(.hljs-comment),
.chat-message-bubble :deep(.hljs-quote) {
  color: #6b7280;
}

.chat-message-bubble :deep(.hljs-keyword),
.chat-message-bubble :deep(.hljs-selector-tag),
.chat-message-bubble :deep(.hljs-subst) {
  color: #7c3aed;
}

.chat-message-bubble :deep(.hljs-string),
.chat-message-bubble :deep(.hljs-doctag) {
  color: #047857;
}

.chat-message-bubble :deep(.hljs-number),
.chat-message-bubble :deep(.hljs-literal),
.chat-message-bubble :deep(.hljs-variable),
.chat-message-bubble :deep(.hljs-template-variable),
.chat-message-bubble :deep(.hljs-tag .hljs-attr) {
  color: #b45309;
}

.chat-message-bubble :deep(.hljs-title),
.chat-message-bubble :deep(.hljs-section),
.chat-message-bubble :deep(.hljs-selector-id) {
  color: #2563eb;
}

.chat-message-bubble :deep(.hljs-type),
.chat-message-bubble :deep(.hljs-class .hljs-title) {
  color: #0f766e;
}

.chat-message-bubble :deep(.hljs-tag),
.chat-message-bubble :deep(.hljs-name),
.chat-message-bubble :deep(.hljs-attribute) {
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
  display: block;
  width: 100%;
  max-width: 100%;
}

.studio-result-block-pending {
  width: 100%;
}

.studio-result-grid {
  display: grid;
  width: 100%;
  max-width: 100%;
  grid-template-columns: repeat(var(--studio-image-grid-columns), minmax(0, 1fr));
  gap: 0.625rem;
}

.studio-result-grid.is-single {
  grid-template-columns: minmax(0, 1fr);
}

.studio-result-item {
  width: 100%;
  min-width: 0;
}

.studio-result-grid.is-single .studio-result-item {
  width: 100%;
}

.studio-result-media {
  display: flex;
  box-sizing: border-box;
  width: 100%;
  min-width: 100%;
  min-height: 0;
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

@media (max-width: 720px) {
  .chat-message-container {
    max-width: min(100%, 38rem);
  }

  .chat-message-container.is-pending-image-message {
    width: min(100%, var(--studio-image-message-width, 18rem));
    min-width: 0;
    max-width: 100%;
  }

  .studio-result-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .chat-message-actions {
    max-width: calc(100vw - 5.5rem);
    overflow-x: auto;
    overflow-y: hidden;
    padding-bottom: 1px;
  }
}
</style>

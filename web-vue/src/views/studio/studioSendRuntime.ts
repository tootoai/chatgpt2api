import { nextTick, type Ref } from 'vue'
import { normalizeImageCount } from '@/api/imageTasks'
import type { StudioComposeMode, StudioConversation, StudioImageForm, StudioMessage } from '@/components/studio/types'
import type { useToast } from '@/composables/useToast'
import { createStudioImageTask, runStudioSearchRequest, studioErrorMessage, studioModeRequestErrorFallback, studioModeRetryErrorFallback } from './studioRequestView'
import type { useStudioChatStreamRuntime } from './studioChatStreamRuntime'
import type { useStudioComposerRuntime } from './studioComposerRuntime'
import type { useStudioImageTaskRuntime } from './studioImageTaskRuntime'
import type { useStudioMessageRuntime } from './studioMessageRuntime'
import type { useStudioReferenceRuntime } from './studioReferenceRuntime'

export type StudioSendRuntimeHooks = {
  activeConversationId: Ref<string>
  ensureConversation: (content?: string) => StudioConversation
  markConversationNotice: (conversationId: string, state: 'done' | 'error' | 'running') => void
  clearConversationNotice: (conversationId: string) => void
  touchConversation: (conversation: StudioConversation) => void
  scheduleScrollToBottom: () => void
}

export type StudioSendRuntimeInput = {
  composerRuntime: ReturnType<typeof useStudioComposerRuntime>
  referenceRuntime: ReturnType<typeof useStudioReferenceRuntime>
  messageRuntime: ReturnType<typeof useStudioMessageRuntime>
  chatStreamRuntime: ReturnType<typeof useStudioChatStreamRuntime>
  imageTaskRuntime: Pick<ReturnType<typeof useStudioImageTaskRuntime>, 'rememberTask' | 'merge' | 'schedulePoll'>
  chatModel: Ref<string>
  chatReasoningEffort: Ref<string>
  imageForm: StudioImageForm
  toast: Pick<ReturnType<typeof useToast>, 'success'>
  hooks: StudioSendRuntimeHooks
}

export function useStudioSendRuntime(input: StudioSendRuntimeInput) {
  const {
    chatModel,
    chatReasoningEffort,
    chatStreamRuntime,
    composerRuntime,
    hooks,
    imageForm,
    imageTaskRuntime,
    messageRuntime,
    referenceRuntime,
    toast,
  } = input

  async function sendMessage() {
    const content = composerRuntime.composerText.value.trim()
    if (!content || composerRuntime.isSending.value || chatStreamRuntime.isStreaming.value) return

    if (composerRuntime.editingMessageId.value) {
      await sendEditedMessage(content)
      return
    }

    const conversation = hooks.ensureConversation(content)
    const mode = composerRuntime.composeMode.value
    const files = referenceRuntime.selectedFiles()
    const attachments = referenceRuntime.attachmentNames()

    messageRuntime.addMessage(conversation, {
      role: 'user',
      mode,
      content,
      status: 'done',
      attachments: mode === 'image' && attachments.length ? attachments : undefined,
    })
    composerRuntime.composerText.value = ''
    await runRequestWithComposerState({
      mode,
      conversation,
      prompt: content,
      files,
      requestErrorFallback: studioModeRequestErrorFallback(mode),
      clearReferencesOnImageSuccess: true,
    })
  }

  async function sendEditedMessage(content: string) {
    const target = messageRuntime.findMessage(composerRuntime.editingMessageId.value)
    if (!target || target.message.role !== 'user') {
      composerRuntime.editingMessageId.value = ''
      return
    }

    const { conversation, message } = target
    const mode = composerRuntime.composeMode.value
    const files = referenceRuntime.selectedFiles()
    const attachments = referenceRuntime.attachmentNames()
    const editedMessage: StudioMessage = {
      ...message,
      mode,
      content,
      status: 'done',
      error: undefined,
      attachments: mode === 'image' && attachments.length ? attachments : undefined,
    }

    hooks.activeConversationId.value = conversation.id
    messageRuntime.replaceFromTarget(target, editedMessage)
    composerRuntime.editingMessageId.value = ''
    composerRuntime.composerText.value = ''
    hooks.clearConversationNotice(conversation.id)

    await runRequestWithComposerState({
      mode,
      conversation,
      prompt: content,
      files,
      requestErrorFallback: studioModeRequestErrorFallback(mode),
      clearReferencesOnImageSuccess: true,
    })
  }

  function fillComposerFromMessage(message: StudioMessage) {
    composerRuntime.cancelMessageEdit(false)
    composerRuntime.fillFromMessage(message)
  }

  function editMessage(message: StudioMessage) {
    const target = messageRuntime.findMessage(message.id)
    if (!target || target.message.role !== 'user') return
    hooks.activeConversationId.value = target.conversation.id
    composerRuntime.startEdit(target.message)
    referenceRuntime.clear()
    hooks.scheduleScrollToBottom()
  }

  async function resendMessage(message: StudioMessage) {
    if (composerRuntime.isSending.value || chatStreamRuntime.isStreaming.value) return
    fillComposerFromMessage(message)
    await nextTick()
    await sendMessage()
  }

  async function retryAssistantMessage(message: StudioMessage) {
    if (composerRuntime.isSending.value || chatStreamRuntime.isStreaming.value) return
    const target = messageRuntime.findMessage(message.id)
    if (!target) return
    const previousUserMessage = messageRuntime.findPreviousUserMessage(target)
    if (!previousUserMessage) return

    hooks.activeConversationId.value = target.conversation.id
    messageRuntime.pruneAfterTarget(target)
    hooks.clearConversationNotice(target.conversation.id)

    await runRequestWithComposerState({
      mode: previousUserMessage.mode,
      conversation: target.conversation,
      prompt: previousUserMessage.content,
      files: [],
      requestErrorFallback: studioModeRetryErrorFallback(previousUserMessage.mode),
    })
  }

  async function runRequestWithComposerState(input: {
    mode: StudioComposeMode
    conversation: StudioConversation
    prompt: string
    files: File[]
    requestErrorFallback: string
    clearReferencesOnImageSuccess?: boolean
  }) {
    composerRuntime.setSending(true)
    try {
      await sendByMode(input.conversation, input.mode, input.prompt, input.files)
      if (input.mode === 'image' && input.clearReferencesOnImageSuccess) {
        referenceRuntime.clear()
      }
    } catch (error) {
      const message = studioErrorMessage(error, input.requestErrorFallback)
      hooks.markConversationNotice(input.conversation.id, 'error')
      messageRuntime.addMessage(input.conversation, {
        role: 'assistant',
        mode: input.mode,
        content: message,
        status: 'error',
        error: message,
      })
    } finally {
      composerRuntime.setSending(false)
      hooks.scheduleScrollToBottom()
    }
  }

  async function sendByMode(conversation: StudioConversation, mode: StudioComposeMode, prompt: string, files: File[]) {
    if (mode === 'chat') {
      await sendTextMessage(conversation)
    } else if (mode === 'search') {
      await sendSearchMessage(conversation, prompt)
    } else {
      await sendImageMessage(conversation, prompt, files)
    }
  }

  async function sendTextMessage(conversation: StudioConversation) {
    const assistantMessage = messageRuntime.addMessage(conversation, {
      role: 'assistant',
      mode: 'chat',
      content: '',
      status: 'streaming',
      model: chatModel.value,
    })

    await chatStreamRuntime.stream({
      conversation,
      assistantMessage,
      model: chatModel.value,
      reasoningEffort: chatReasoningEffort.value,
    })
  }

  async function sendSearchMessage(conversation: StudioConversation, prompt: string) {
    const assistantMessage = messageRuntime.addMessage(conversation, {
      role: 'assistant',
      mode: 'search',
      content: '正在搜索...',
      status: 'sending',
      model: 'search',
    })

    try {
      const result = await runStudioSearchRequest(prompt, assistantMessage.id)
      assistantMessage.searchSources = result.sources
      assistantMessage.searchImageGroups = result.imageGroups
      assistantMessage.content = result.content
      assistantMessage.status = 'done'
      hooks.markConversationNotice(conversation.id, 'done')
    } catch (error) {
      const message = studioErrorMessage(error, '搜索请求失败')
      assistantMessage.status = 'error'
      assistantMessage.content = message
      assistantMessage.error = message
      hooks.markConversationNotice(conversation.id, 'error')
    } finally {
      hooks.touchConversation(conversation)
      hooks.scheduleScrollToBottom()
    }
  }

  async function sendImageMessage(conversation: StudioConversation, prompt: string, files: File[]) {
    const assistantMessage = messageRuntime.addMessage(conversation, {
      role: 'assistant',
      mode: 'image',
      content: files.length ? '图像编辑任务已提交' : '图片任务已提交',
      status: 'queued',
      model: imageForm.model,
      imageSize: imageForm.size,
      imageCount: normalizeImageCount(imageForm.n),
    })

    try {
      const task = await createStudioImageTask({ prompt, files, imageForm })
      assistantMessage.taskId = task.id
      assistantMessage.status = 'running'
      hooks.touchConversation(conversation)
      imageTaskRuntime.rememberTask(task.id)
      imageTaskRuntime.merge([task])
      toast.success('图片任务已提交')
      imageTaskRuntime.schedulePoll()
    } catch (error) {
      const message = studioErrorMessage(error, '图片任务提交失败')
      assistantMessage.status = 'error'
      assistantMessage.content = message
      assistantMessage.error = message
      hooks.touchConversation(conversation)
      hooks.markConversationNotice(conversation.id, 'error')
    }
  }

  return {
    editMessage,
    fillComposerFromMessage,
    resendMessage,
    retryAssistantMessage,
    sendMessage,
  }
}

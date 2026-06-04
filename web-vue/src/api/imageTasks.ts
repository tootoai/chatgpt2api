import apiClient from './client'

export type ImageTaskStatus = 'queued' | 'running' | 'success' | 'error'
export type ImageTaskMode = 'generate' | 'edit'

export interface ImageTaskAsset {
  url?: string
  b64_json?: string
  revised_prompt?: string
  [key: string]: unknown
}

export interface ImageTask {
  id: string
  status: ImageTaskStatus
  mode: ImageTaskMode
  model: string
  size?: string
  quality?: string
  stage?: string
  progress?: string
  created_at?: string
  updated_at?: string
  elapsed_secs?: number
  duration_ms?: number
  conversation_id?: string
  data?: ImageTaskAsset[]
  usage?: Record<string, unknown>
  error?: string
  error_code?: string
  reason?: string
  can_resume_poll?: boolean
  raw_upstream_message?: string
  raw_upstream_message_len?: number
  raw_upstream_message_truncated?: boolean
  upstream_message_preview?: string
  upstream_message_len?: number
  upstream_message_truncated?: boolean
  tool_invoked?: boolean
  terminal_message?: string
  blocked?: boolean
  diagnosis?: Record<string, unknown>
}

export interface ImageTasksResponse {
  items: ImageTask[]
  missing_ids: string[]
}

export interface CreateGenerationTaskInput {
  prompt: string
  model?: string
  size?: string
  quality?: string
  clientTaskId?: string
}

export interface CreateEditTaskInput extends CreateGenerationTaskInput {
  files?: File[]
  imageUrls?: string[]
}

export const DEFAULT_IMAGE_MODEL = 'gpt-image-2'
export const DEFAULT_IMAGE_QUALITY = 'auto'
export const DEFAULT_IMAGE_SIZE = 'auto'

export const IMAGE_SIZE_OPTIONS = [
  { label: '自动', value: 'auto' },
  { label: '1024 x 1024', value: '1024x1024' },
  { label: '1024 x 1536', value: '1024x1536' },
  { label: '1536 x 1024', value: '1536x1024' },
  { label: '1920 x 1080', value: '1920x1080' },
  { label: '1080 x 1920', value: '1080x1920' },
]

export const IMAGE_QUALITY_OPTIONS = [
  { label: '自动', value: 'auto' },
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
]

function cleanString(value: unknown, fallback = '') {
  const text = String(value ?? '').trim()
  return text || fallback
}

export function createClientTaskId(prefix = 'img') {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function normalizeTask(raw: Partial<ImageTask>): ImageTask {
  return {
    id: cleanString(raw.id),
    status: (cleanString(raw.status, 'queued') as ImageTaskStatus),
    mode: (cleanString(raw.mode, 'generate') as ImageTaskMode),
    model: cleanString(raw.model, DEFAULT_IMAGE_MODEL),
    size: cleanString(raw.size),
    quality: cleanString(raw.quality, DEFAULT_IMAGE_QUALITY),
    stage: cleanString(raw.stage),
    progress: cleanString(raw.progress),
    created_at: cleanString(raw.created_at),
    updated_at: cleanString(raw.updated_at),
    elapsed_secs: Number.isFinite(Number(raw.elapsed_secs)) ? Number(raw.elapsed_secs) : undefined,
    duration_ms: Number.isFinite(Number(raw.duration_ms)) ? Number(raw.duration_ms) : undefined,
    conversation_id: cleanString(raw.conversation_id),
    data: Array.isArray(raw.data) ? raw.data : [],
    usage: raw.usage && typeof raw.usage === 'object' ? raw.usage : undefined,
    error: cleanString(raw.error),
    error_code: cleanString(raw.error_code),
    reason: cleanString(raw.reason),
    can_resume_poll: Boolean(raw.can_resume_poll),
    raw_upstream_message: cleanString(raw.raw_upstream_message),
    raw_upstream_message_len: Number.isFinite(Number(raw.raw_upstream_message_len))
      ? Number(raw.raw_upstream_message_len)
      : undefined,
    raw_upstream_message_truncated: Boolean(raw.raw_upstream_message_truncated),
    upstream_message_preview: cleanString(raw.upstream_message_preview),
    upstream_message_len: Number.isFinite(Number(raw.upstream_message_len))
      ? Number(raw.upstream_message_len)
      : undefined,
    upstream_message_truncated: Boolean(raw.upstream_message_truncated),
    tool_invoked: typeof raw.tool_invoked === 'boolean' ? raw.tool_invoked : undefined,
    terminal_message: cleanString(raw.terminal_message),
    blocked: typeof raw.blocked === 'boolean' ? raw.blocked : undefined,
    diagnosis: raw.diagnosis && typeof raw.diagnosis === 'object' ? raw.diagnosis : undefined,
  }
}

function normalizeResponse(response: Partial<ImageTasksResponse>): ImageTasksResponse {
  return {
    items: (response.items || []).map((item) => normalizeTask(item)),
    missing_ids: Array.isArray(response.missing_ids) ? response.missing_ids.map((id) => String(id)) : [],
  }
}

function requestSize(size?: string) {
  const value = cleanString(size, DEFAULT_IMAGE_SIZE)
  return value === DEFAULT_IMAGE_SIZE ? undefined : value
}

function normalizeUrlList(value: string[] | undefined) {
  return (value || []).map((item) => item.trim()).filter(Boolean)
}

function createEditForm(input: CreateEditTaskInput) {
  const form = new FormData()
  form.append('client_task_id', input.clientTaskId || createClientTaskId('edit'))
  form.append('prompt', input.prompt)
  form.append('model', input.model || DEFAULT_IMAGE_MODEL)
  form.append('quality', input.quality || DEFAULT_IMAGE_QUALITY)
  const size = requestSize(input.size)
  if (size) form.append('size', size)

  const imageUrls = normalizeUrlList(input.imageUrls)
  if (imageUrls.length === 1) {
    form.append('image_url', imageUrls[0])
  } else if (imageUrls.length > 1) {
    form.append('images', JSON.stringify(imageUrls))
  }

  for (const file of input.files || []) {
    form.append('image', file, file.name)
  }
  return form
}

export function isImageTaskTerminal(task: ImageTask) {
  return task.status === 'success' || task.status === 'error'
}

export function taskPrimaryMessage(task: ImageTask) {
  return task.reason || task.error || task.upstream_message_preview || task.terminal_message || ''
}

export function imageAssetUrl(asset: ImageTaskAsset) {
  const url = cleanString(asset.url)
  if (url) return url
  const base64 = cleanString(asset.b64_json)
  return base64 ? `data:image/png;base64,${base64}` : ''
}

export const imageTasksApi = {
  list: async (ids?: string[]) => {
    const params = ids?.length ? { ids: ids.join(',') } : undefined
    const response = await apiClient.get<never, ImageTasksResponse>('/api/image-tasks', { params })
    return normalizeResponse(response)
  },

  createGeneration: async (input: CreateGenerationTaskInput) => {
    const response = await apiClient.post<Record<string, unknown>, ImageTask>('/api/image-tasks/generations', {
      client_task_id: input.clientTaskId || createClientTaskId('gen'),
      prompt: input.prompt,
      model: input.model || DEFAULT_IMAGE_MODEL,
      size: requestSize(input.size),
      quality: input.quality || DEFAULT_IMAGE_QUALITY,
    })
    return normalizeTask(response)
  },

  createEdit: async (input: CreateEditTaskInput) => {
    const response = await apiClient.post<FormData, ImageTask>('/api/image-tasks/edits', createEditForm(input))
    return normalizeTask(response)
  },

  resumePoll: async (taskId: string, extraTimeoutSecs = 30) => {
    const response = await apiClient.post<{ extra_timeout_secs: number }, ImageTask>(
      `/api/image-tasks/${encodeURIComponent(taskId)}/resume-poll`,
      { extra_timeout_secs: extraTimeoutSecs },
    )
    return normalizeTask(response)
  },
}

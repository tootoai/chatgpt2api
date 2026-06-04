import apiClient from './client'
import type { AdminLogGroup, AdminLogStats, AdminLogsResponse, LogEntry } from '@/types/api'

type LogsListParams = {
  limit?: number
  level?: string
  search?: string
}

export type SystemLog = {
  id?: string
  time?: string
  type?: string
  summary?: string
  detail?: Record<string, any>
}

type BackendLogsResponse = {
  items?: SystemLog[]
  total?: number
  limit?: number
  offset?: number
  has_more?: boolean
  facets?: {
    statuses?: Record<string, number>
    endpoints?: Record<string, number>
    models?: Record<string, number>
    accounts?: Record<string, number>
  }
  stats?: {
    total?: number
    success?: number
    failed?: number
    limited?: number
    image?: number
    text_reply?: number
  }
}

export type SystemLogsListParams = {
  type?: string
  start_date?: string
  end_date?: string
  status?: string
  endpoint?: string
  model?: string
  account?: string
  conversation_id?: string
  search?: string
  limit?: number
  offset?: number
}

export type SystemLogsResponse = {
  items: SystemLog[]
  total: number
  limit: number
  offset: number
  has_more: boolean
  facets: {
    statuses: Record<string, number>
    endpoints: Record<string, number>
    models: Record<string, number>
    accounts: Record<string, number>
  }
  stats: {
    total: number
    success: number
    failed: number
    limited: number
    image: number
    textReply: number
  }
}

export type RuntimeLog = {
  id?: string
  time?: string
  level?: string
  message?: string
  source?: string
  path?: string
}

type RuntimeLogsResponseRaw = {
  items?: RuntimeLog[]
  total?: number
  limit?: number
  sources?: {
    memory?: boolean
    files?: string[]
  }
}

export type RuntimeLogsListParams = {
  level?: string
  search?: string
  source?: string
  limit?: number
}

export type RuntimeLogsResponse = {
  items: RuntimeLog[]
  total: number
  limit: number
  sources: {
    memory: boolean
    files: string[]
  }
}

function cleanString(value: unknown): string {
  return String(value || '').trim()
}

function normalizeLevel(item: SystemLog): LogEntry['level'] {
  const detail = item.detail || {}
  const status = cleanString(detail.status).toLowerCase()
  const error = cleanString(detail.error)
  const errorCode = cleanString(detail.error_code || detail?.diagnosis?.error_code)
  if (status === 'failed' || error || errorCode) return 'ERROR'
  if (status === 'warning' || status === 'limited') return 'WARNING'
  return 'INFO'
}

function pickEndpointTag(endpoint: string): string {
  if (endpoint.includes('/images/edits')) return 'IMAGE-EDIT'
  if (endpoint.includes('/images/generations')) return 'IMAGE-GEN'
  if (endpoint.includes('/v1/chat')) return 'CHAT'
  return 'SYSTEM'
}

function terminalStage(status: string, error: string): string {
  if (status === 'success') return 'success'
  if (status === 'failed' || error) return 'failed'
  return ''
}

function terminalStatus(status: string, error: string): AdminLogGroup['status'] {
  if (status === 'success') return 'success'
  if (status === 'failed' || error) return 'error'
  return 'in_progress'
}

function detailValue(detail: Record<string, any>, key: string): string {
  const value = detail[key]
  if (value !== undefined && value !== null && value !== '') return cleanString(value)
  const diagnosis = detail.diagnosis
  if (diagnosis && typeof diagnosis === 'object') return cleanString(diagnosis[key])
  return ''
}

function summarizeDetail(detail: Record<string, any>) {
  const parts = [
    detailValue(detail, 'stage') ? `stage=${detailValue(detail, 'stage')}` : '',
    detailValue(detail, 'error_code') ? `error_code=${detailValue(detail, 'error_code')}` : '',
    detailValue(detail, 'reason') ? `reason=${detailValue(detail, 'reason')}` : '',
    detailValue(detail, 'conversation_id') ? `conversation=${detailValue(detail, 'conversation_id')}` : '',
    detailValue(detail, 'duration_ms') ? `duration_ms=${detailValue(detail, 'duration_ms')}` : '',
    detailValue(detail, 'upstream_message_preview') ? `upstream="${detailValue(detail, 'upstream_message_preview')}"` : '',
    detailValue(detail, 'raw_upstream_message') ? `raw_upstream="${detailValue(detail, 'raw_upstream_message')}"` : '',
  ].filter(Boolean)
  return parts.join(' | ')
}

function buildMessage(item: SystemLog): string {
  const detail = item.detail || {}
  const endpoint = cleanString(detail.endpoint)
  const model = cleanString(detail.model)
  const status = cleanString(detail.status)
  const summary = cleanString(item.summary)
  const requestText = cleanString(detail.request_text)
  const error = cleanString(detail.error)
  const detailSummary = summarizeDetail(detail)
  const tags = [`[${pickEndpointTag(endpoint)}]`]
  const conversationId = cleanString(detail.conversation_id)
  if (conversationId) tags.push(`[req_${conversationId.replace(/[^a-z0-9]/gi, '').slice(0, 12)}]`)

  return [
    tags.join(''),
    summary || 'log',
    endpoint ? `endpoint=${endpoint}` : '',
    model ? `model=${model}` : '',
    status ? `status=${status}` : '',
    detailSummary,
    requestText ? `request: ${requestText}` : '',
    error ? `error: ${error}` : '',
  ].filter(Boolean).join(' ')
}

function mapLog(item: SystemLog, index: number): LogEntry {
  const detail = item.detail || {}
  const id = cleanString(item.id) || `log-${index}`
  const endpoint = cleanString(detail.endpoint)
  const status = cleanString(detail.status)
  const error = cleanString(detail.error)
  const conversationId = cleanString(detail.conversation_id)
  const reqId = conversationId || id
  const message = buildMessage(item)
  return {
    time: cleanString(item.time),
    level: normalizeLevel(item),
    message,
    row_id: id,
    req_id: reqId,
    tags: [pickEndpointTag(endpoint), cleanString(item.type).toUpperCase()].filter(Boolean),
    account_id: cleanString(detail.account_email || detail.key_name || detail.key_id),
    text: message,
    layer: endpoint ? 'reverse' : 'system',
    lane: '',
    model: cleanString(detail.model),
    kind: detailValue(detail, 'error_code') || (error ? 'upstream_error' : ''),
    stage: terminalStage(status, error),
    served_label: '',
  }
}

function applyLocalFilters(logs: LogEntry[], params?: LogsListParams) {
  const level = cleanString(params?.level).toUpperCase()
  const search = cleanString(params?.search).toLowerCase()
  const limit = Math.min(Math.max(Number(params?.limit || 300), 10), 1000)
  const filtered = logs.filter((log) => {
    if (level && log.level !== level) return false
    if (!search) return true
    return [
      log.message,
      log.model,
      log.kind,
      log.account_id,
      log.req_id,
    ].some((value) => cleanString(value).toLowerCase().includes(search))
  })
  return filtered.slice(0, limit)
}

function buildStats(logs: LogEntry[]): AdminLogStats {
  const byLevel: Record<string, number> = {}
  logs.forEach((log) => {
    byLevel[log.level] = (byLevel[log.level] || 0) + 1
  })
  const recentErrors = logs.filter((log) => log.level === 'ERROR' || log.level === 'CRITICAL').slice(0, 10)
  return {
    memory: {
      total: logs.length,
      by_level: byLevel,
      capacity: 1000,
    },
    active: {
      source: 'file',
      total: logs.length,
    },
    errors: {
      count: recentErrors.length,
      recent: recentErrors,
    },
    chat_count: logs.filter((log) => log.tags?.includes('CHAT')).length,
  }
}

function buildGroups(logs: LogEntry[], rawItems: SystemLog[]): AdminLogGroup[] {
  const itemById = new Map(rawItems.map((item, index) => [cleanString(item.id) || `log-${index}`, item]))
  const grouped = new Map<string, { logs: LogEntry[]; raws: SystemLog[] }>()
  logs.forEach((log) => {
    const groupId = cleanString(log.req_id || log.row_id)
    const bucket = grouped.get(groupId) || { logs: [], raws: [] }
    bucket.logs.push(log)
    bucket.raws.push(itemById.get(cleanString(log.row_id)) || {})
    grouped.set(groupId, bucket)
  })

  return Array.from(grouped.entries()).map(([groupId, bucket]) => {
    const firstLog = bucket.logs[0]
    const lastLog = bucket.logs[bucket.logs.length - 1]
    const terminalRaw = [...bucket.raws].reverse().find((raw) => {
      const detail = raw.detail || {}
      return cleanString(detail.status) || cleanString(detail.error)
    }) || bucket.raws[bucket.raws.length - 1] || {}
    const firstRaw = bucket.raws[0] || {}
    const raw = terminalRaw
    const firstDetail = firstRaw.detail || {}
    const detail = raw.detail || {}
    const status = cleanString(detail.status)
    const error = cleanString(detail.error)
    return {
      id: groupId,
      row_ids: bucket.logs.map((log) => cleanString(log.row_id)).filter(Boolean),
      status: terminalStatus(status, error),
      account_id: cleanString(firstLog.account_id || lastLog.account_id),
      model: cleanString(firstLog.model || lastLog.model),
      lane: cleanString(firstLog.lane || lastLog.lane),
      terminal_kind: cleanString(lastLog.kind || firstLog.kind),
      started_at: detailValue(firstDetail, 'started_at') || cleanString(firstRaw.time),
      ended_at: detailValue(detail, 'ended_at') || cleanString(raw.time),
      user_preview: cleanString(firstDetail.request_text || detail.request_text).slice(0, 140),
      assistant_preview: cleanString(detail.error || detail.upstream_message_preview || detail.raw_upstream_message).slice(0, 140),
      count: bucket.logs.length,
    }
  })
}

function mapResponse(response: BackendLogsResponse, params?: LogsListParams): AdminLogsResponse {
  const rawItems = response.items || []
  const allLogs = rawItems.map(mapLog)
  const logs = applyLocalFilters(allLogs, params)
  return {
    total: logs.length,
    limit: Math.min(Math.max(Number(params?.limit || 300), 10), 1000),
    logs,
    groups: buildGroups(logs, rawItems),
    filters: {
      level: params?.level || null,
      search: params?.search || null,
      start_time: null,
      end_time: null,
    },
    stats: buildStats(logs),
  }
}

function normalizeSystemParams(params?: SystemLogsListParams) {
  const limit = Number(params?.limit || 500)
  const offset = Number(params?.offset || 0)
  return {
    type: cleanString(params?.type),
    start_date: cleanString(params?.start_date),
    end_date: cleanString(params?.end_date),
    status: cleanString(params?.status),
    endpoint: cleanString(params?.endpoint),
    model: cleanString(params?.model),
    account: cleanString(params?.account),
    conversation_id: cleanString(params?.conversation_id),
    search: cleanString(params?.search),
    limit: Number.isFinite(limit) ? Math.min(Math.max(Math.trunc(limit), 1), 20000) : 500,
    offset: Number.isFinite(offset) ? Math.max(Math.trunc(offset), 0) : 0,
  }
}

function buildSystemStatsFallback(items: SystemLog[]) {
  const isSuccess = (item: SystemLog) => cleanString(detailValue(item.detail || {}, 'status')).toLowerCase() === 'success'
  const isFailed = (item: SystemLog) => {
    const detail = item.detail || {}
    return cleanString(detailValue(detail, 'status')).toLowerCase() === 'failed'
      || Boolean(detailValue(detail, 'error') || detailValue(detail, 'error_code'))
  }
  const isLimited = (item: SystemLog) => {
    const detail = item.detail || {}
    return [
      detailValue(detail, 'status'),
      detailValue(detail, 'error_code'),
      detailValue(detail, 'reason'),
      detailValue(detail, 'error'),
    ].join(' ').toLowerCase().includes('limit')
  }
  return {
    total: items.length,
    success: items.filter(isSuccess).length,
    failed: items.filter(isFailed).length,
    limited: items.filter(isLimited).length,
    image: items.filter((item) => cleanString(detailValue(item.detail || {}, 'endpoint')).includes('/images/')).length,
    textReply: items.filter((item) => {
      const detail = item.detail || {}
      return detailValue(detail, 'error_code') === 'upstream_text_reply' || Boolean(detailValue(detail, 'raw_upstream_message'))
    }).length,
  }
}

function normalizeSystemResponse(response: BackendLogsResponse): SystemLogsResponse {
  const items = response.items || []
  const facets = response.facets || {}
  const stats = response.stats || {}
  const fallbackStats = buildSystemStatsFallback(items)
  const total = response.total === undefined ? items.length : Number(response.total || 0)
  return {
    items,
    total,
    limit: Number(response.limit || items.length || 0),
    offset: Number(response.offset || 0),
    has_more: response.has_more === true,
    facets: {
      statuses: facets.statuses || {},
      endpoints: facets.endpoints || {},
      models: facets.models || {},
      accounts: facets.accounts || {},
    },
    stats: {
      total: Number(stats.total ?? total),
      success: Number(stats.success ?? fallbackStats.success),
      failed: Number(stats.failed ?? fallbackStats.failed),
      limited: Number(stats.limited ?? fallbackStats.limited),
      image: Number(stats.image ?? fallbackStats.image),
      textReply: Number(stats.text_reply ?? fallbackStats.textReply),
    },
  }
}

function normalizeRuntimeParams(params?: RuntimeLogsListParams) {
  const limit = Number(params?.limit || 300)
  return {
    level: cleanString(params?.level),
    search: cleanString(params?.search),
    source: cleanString(params?.source),
    limit: Number.isFinite(limit) ? Math.min(Math.max(Math.trunc(limit), 1), 2000) : 300,
  }
}

function normalizeRuntimeResponse(response: RuntimeLogsResponseRaw): RuntimeLogsResponse {
  const sources = response.sources || {}
  return {
    items: response.items || [],
    total: Number(response.total || response.items?.length || 0),
    limit: Number(response.limit || response.items?.length || 0),
    sources: {
      memory: sources.memory !== false,
      files: Array.isArray(sources.files) ? sources.files : [],
    },
  }
}

export const logsApi = {
  list: async (params?: LogsListParams) => {
    const limit = Math.min(Math.max(Number(params?.limit || 500), 10), 20000)
    const response = await apiClient.get<never, BackendLogsResponse>('/api/logs', {
      params: { limit },
    })
    return mapResponse(response, params)
  },

  listSystem: async (params?: SystemLogsListParams) => {
    const response = await apiClient.get<never, BackendLogsResponse>('/api/logs', {
      params: normalizeSystemParams(params),
    })
    return normalizeSystemResponse(response)
  },

  listRuntime: async (params?: RuntimeLogsListParams) => {
    const response = await apiClient.get<never, RuntimeLogsResponseRaw>('/api/runtime-logs', {
      params: normalizeRuntimeParams(params),
    })
    return normalizeRuntimeResponse(response)
  },

  delete: async (ids: string[]) =>
    apiClient.post<{ ids: string[] }, { removed: number }>('/api/logs/delete', { ids }),

  clear: async () => {
    const response = await apiClient.get<never, BackendLogsResponse>('/api/logs', {
      params: { limit: 20000 },
    })
    const ids = (response.items || []).map((item) => cleanString(item.id)).filter(Boolean)
    if (!ids.length) return { removed: 0 }
    return logsApi.delete(ids)
  },
}

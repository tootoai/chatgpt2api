import apiClient from './client'

export type ReverseLane = 'fast' | 'thinking' | 'pro'

export interface ReverseAccount {
  id: string
  access_token?: string
  backend_status?: string
  email?: string
  user_id?: string
  type?: string
  source_type?: string
  proxy?: string
  quota?: number
  image_quota_unknown?: boolean
  name: string
  status?: 'ready' | 'incomplete' | 'disabled' | 'invalid' | 'auto_disabled' | 'cooling' | 'backoff'
  status_reason?: string
  status_reason_code?:
    | 'disabled'
    | 'snlm0e_refresh_failed'
    | 'account_invalid'
    | 'pro_cooldown'
    | 'video_cooldown'
    | 'lane_backoff'
    | 'lane_degraded'
    | 'image_generation_unavailable'
    | 'image_degraded_to_fast'
    | 'parse_failure'
    | 'text_pending'
    | 'upstream_error'
    | 'image_quota_exhausted'
    | ''
  cookie: string
  snlm0e: string
  push_id: string
  push_id_set?: boolean
  enabled: boolean
  auto_disabled?: boolean
  auto_disabled_reason?: string
  auto_disabled_at?: number
  health_fail_streak?: number
  last_health_check_at?: number
  lanes: ReverseLane[]
  model_ids: Record<ReverseLane, string>
  failure_count: number
  success_count: number
  last_error: string
  last_error_kind?:
    | 'quota_exhausted'
    | 'media_pending'
    | 'media_generation_unavailable'
    | 'media_degraded'
    | 'lane_degraded'
    | 'parse_failure'
    | 'text_pending'
    | 'upstream_error'
    | 'auth_invalid'
    | ''
  pro_cooldown_until?: number
  pro_cooldown_seconds?: number
  pro_cooldown_local?: string
  pro_cooldown_reason?: string
  video_cooldown_until?: number
  video_cooldown_seconds?: number
  video_cooldown_local?: string
  video_cooldown_reason?: string
  snlm0e_refreshed_at?: number
  snlm0e_refresh_fail_count?: number
  snlm0e_last_refresh_error?: string
  snlm0e_next_refresh_after?: number
  daily_usage?: {
    fast: number
    thinking: number
    pro: number
    image: number
    music: number
    video: number
  }
  quota_limits?: {
    enabled: boolean
    fast: number
    thinking: number
    pro: number
    image: number
    music: number
    video: number
  }
  quota_summary?: {
    enabled: boolean
    period: string
    reset_in_seconds: number
    conversation: { used: number; limit: number; remaining: number; limited: boolean }
    pro: { used: number; limit: number; remaining: number; limited: boolean }
    image: { used: number; limit: number; remaining: number; limited: boolean }
    music: { used: number; limit: number; remaining: number; limited: boolean }
    video: { used: number; limit: number; remaining: number; limited: boolean }
  }
  lane_backoff_until?: Partial<Record<ReverseLane, number>>
  lane_backoff_reason?: Partial<Record<ReverseLane, string>>
  lane_backoff_kind?: Partial<Record<ReverseLane, string>>
  lane_backoff_summary?: {
    active: boolean
    lanes: ReverseLane[]
    max_wait_seconds: number
    summary: string
    items: Array<{
      lane: ReverseLane
      wait_seconds: number
      until: number
      until_local: string
      reason: string
      kind: string
      label: string
    }>
  }
  last_used_at: number
  created_at: number
  restore_at?: number
  updated_at: number
  is_demo?: boolean
}

export interface ReverseMonitorLane {
  total: number
  enabled: number
  available: number
}

export interface ReverseMonitor {
  total_accounts: number
  lanes: Record<ReverseLane, ReverseMonitorLane>
}

export interface ReverseAccountsResponse {
  accounts: ReverseAccount[]
  total?: number
}

export interface ReverseAccountsBulkResponse {
  status: string
  success_count: number
  errors: string[]
}

export interface AccountRefreshProgress {
  total: number
  processed: number
  done: boolean
  error?: string | null
  status_counts?: Record<string, number>
  total_quota?: number
  result?: {
    refreshed?: number
    relogined?: number
    errors?: Array<{ token?: string; error?: string } | string>
    items?: BackendAccount[]
  } | null
}

export interface AccountReLoginProgress {
  total: number
  processed: number
  done: boolean
  error?: string | null
  results?: Array<{
    token?: string
    status?: string
    error?: string | null
  }>
  result?: {
    relogined?: number
    skipped?: number
    errors?: Array<{ token?: string; error?: string } | string>
    items?: BackendAccount[]
  } | null
}

type BackendAccount = Record<string, any>

type BackendAccountsResponse = {
  items?: BackendAccount[]
}

const DEFAULT_LANES: ReverseLane[] = ['fast', 'thinking', 'pro']
const EMPTY_MODEL_IDS: Record<ReverseLane, string> = { fast: '', thinking: '', pro: '' }
const STATUS_NORMAL = '正常'
const STATUS_DISABLED = '禁用'
const STATUS_LIMITED = '限流'
const STATUS_INVALID = '异常'

const accountTokenById = new Map<string, string>()

function cleanString(value: unknown): string {
  return String(value || '').trim()
}

function toTimestampSeconds(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.floor(value > 10_000_000_000 ? value / 1000 : value)
  }
  const raw = cleanString(value)
  if (!raw) return 0
  const parsed = Date.parse(raw.replace(' ', 'T'))
  return Number.isNaN(parsed) ? 0 : Math.floor(parsed / 1000)
}

function maskToken(token: string): string {
  if (!token) return ''
  if (token.length <= 12) return '********'
  return `${token.slice(0, 6)}...${token.slice(-4)}`
}

function isMaskedToken(value: string): boolean {
  return value.includes('...') || /^\*+$/.test(value)
}

function displayIdForAccount(item: BackendAccount, index: number, usedIds: Set<string>): string {
  const base = (
    cleanString(item.email)
    || cleanString(item.user_id)
    || cleanString(item.account_id)
    || `account-${index + 1}`
  ).slice(0, 96)
  let candidate = base
  let suffix = 2
  while (usedIds.has(candidate)) {
    candidate = `${base}#${suffix}`
    suffix += 1
  }
  usedIds.add(candidate)
  return candidate
}

function backendStatusToFrontend(item: BackendAccount): Pick<
  ReverseAccount,
  'enabled' | 'status' | 'status_reason' | 'status_reason_code' | 'last_error_kind'
> {
  const rawStatus = cleanString(item.status)
  const quota = Number(item.quota ?? 0)
  const imageQuotaUnknown = Boolean(item.image_quota_unknown)
  const lastRefreshError = cleanString(item.last_refresh_error || item.last_token_refresh_error)

  if (rawStatus === STATUS_DISABLED || rawStatus.toLowerCase() === 'disabled') {
    return {
      enabled: false,
      status: 'disabled',
      status_reason: '账号已禁用',
      status_reason_code: 'disabled',
      last_error_kind: '',
    }
  }

  if (rawStatus === STATUS_INVALID || rawStatus.toLowerCase() === 'invalid') {
    return {
      enabled: true,
      status: 'invalid',
      status_reason: lastRefreshError || '账号鉴权异常',
      status_reason_code: 'account_invalid',
      last_error_kind: 'auth_invalid',
    }
  }

  if (rawStatus === STATUS_LIMITED || (!imageQuotaUnknown && quota <= 0)) {
    return {
      enabled: true,
      status: 'cooling',
      status_reason: rawStatus === STATUS_LIMITED ? '账号被标记为限流' : '本地图片额度已用完',
      status_reason_code: 'image_quota_exhausted',
      last_error_kind: 'quota_exhausted',
    }
  }

  return {
    enabled: true,
    status: 'ready',
    status_reason: lastRefreshError,
    status_reason_code: '',
    last_error_kind: lastRefreshError ? 'upstream_error' : '',
  }
}

function mapBackendAccount(item: BackendAccount, index: number, usedIds: Set<string>): ReverseAccount {
  const accessToken = cleanString(item.access_token || item.accessToken)
  const id = displayIdForAccount(item, index, usedIds)
  if (accessToken) accountTokenById.set(id, accessToken)

  const quota = Math.max(0, Number(item.quota ?? 0) || 0)
  const imageQuotaUnknown = Boolean(item.image_quota_unknown)
  const rawStatus = cleanString(item.status)
  const status = backendStatusToFrontend(item)
  const createdAt = toTimestampSeconds(item.created_at)
  const updatedAt = toTimestampSeconds(item.updated_at || item.last_used_at || item.created_at)
  const restoreAt = toTimestampSeconds(item.restore_at || item.quota_restore_at || item.reset_at)
  const lastRefreshError = cleanString(item.last_refresh_error || item.last_token_refresh_error)
  const type = cleanString(item.type || item.plan_type || 'free')
  const sourceType = cleanString(item.source_type || 'web')
  const email = cleanString(item.email)
  const userId = cleanString(item.user_id)

  return {
    id,
    access_token: accessToken,
    backend_status: rawStatus || STATUS_NORMAL,
    email,
    user_id: userId,
    type,
    source_type: sourceType,
    proxy: cleanString(item.proxy),
    quota,
    image_quota_unknown: imageQuotaUnknown,
    name: email || `${type} / ${sourceType}`,
    cookie: maskToken(accessToken),
    snlm0e: '',
    push_id: '',
    enabled: status.enabled,
    status: status.status,
    status_reason: status.status_reason,
    status_reason_code: status.status_reason_code,
    lanes: [...DEFAULT_LANES],
    model_ids: { ...EMPTY_MODEL_IDS },
    failure_count: Number(item.fail ?? 0) || 0,
    success_count: Number(item.success ?? 0) || 0,
    last_error: lastRefreshError,
    last_error_kind: status.last_error_kind,
    daily_usage: { fast: 0, thinking: 0, pro: 0, image: 0, music: 0, video: 0 },
    quota_limits: {
      enabled: !imageQuotaUnknown,
      fast: -1,
      thinking: -1,
      pro: -1,
      image: imageQuotaUnknown ? -1 : quota,
      music: -1,
      video: -1,
    },
    quota_summary: {
      enabled: !imageQuotaUnknown,
      period: 'current',
      reset_in_seconds: 0,
      conversation: { used: 0, limit: -1, remaining: -1, limited: false },
      pro: { used: 0, limit: -1, remaining: -1, limited: false },
      image: {
        used: 0,
        limit: imageQuotaUnknown ? -1 : quota,
        remaining: imageQuotaUnknown ? -1 : quota,
        limited: !imageQuotaUnknown,
      },
      music: { used: 0, limit: -1, remaining: -1, limited: false },
      video: { used: 0, limit: -1, remaining: -1, limited: false },
    },
    last_used_at: toTimestampSeconds(item.last_used_at),
    created_at: createdAt,
    restore_at: restoreAt,
    updated_at: updatedAt || createdAt,
  }
}

function mapAccountsResponse(response: BackendAccountsResponse): ReverseAccountsResponse {
  accountTokenById.clear()
  const usedIds = new Set<string>()
  const accounts = (response.items || []).map((item, index) => mapBackendAccount(item, index, usedIds))
  return { accounts, total: accounts.length }
}

function resolveToken(accountIdOrToken: string): string {
  const value = cleanString(accountIdOrToken)
  return accountTokenById.get(value) || value
}

function payloadToken(payload: Partial<ReverseAccount>): string {
  const mappedToken = payload.id ? accountTokenById.get(payload.id) : ''
  const candidate = cleanString(payload.access_token || payload.cookie || mappedToken)
  if (candidate && !isMaskedToken(candidate)) return candidate
  return mappedToken || ''
}

function backendStatusForEnabled(enabled: boolean | undefined): string {
  return enabled === false ? STATUS_DISABLED : STATUS_NORMAL
}

function backendStatusForPayload(payload: Partial<ReverseAccount>): string {
  const raw = cleanString(payload.backend_status || payload.status)
  if ([STATUS_NORMAL, STATUS_LIMITED, STATUS_INVALID, STATUS_DISABLED].includes(raw)) {
    return raw
  }
  return backendStatusForEnabled(payload.enabled)
}

function accountFromPayload(payload: Partial<ReverseAccount>) {
  const accessToken = payloadToken(payload)
  if (!accessToken) {
    throw new Error('请填写 access token')
  }
  return {
    access_token: accessToken,
    type: payload.type,
    source_type: payload.source_type,
    proxy: payload.proxy,
    quota: payload.quota,
    status: backendStatusForPayload(payload),
  }
}

async function refreshAndPoll(accessTokens: string[]) {
  const start = await apiClient.post<{ access_tokens: string[] }, { progress_id: string }>(
    '/api/accounts/refresh',
    { access_tokens: accessTokens },
  )
  const progressId = cleanString(start.progress_id)
  if (!progressId) return { status: 'ok' }

  const deadline = Date.now() + 60_000
  while (Date.now() < deadline) {
    const progress = await apiClient.get<never, any>(
      `/api/accounts/refresh/progress/${encodeURIComponent(progressId)}`,
    )
    if (progress?.done || progress?.status === 'done' || progress?.finished) {
      if (progress.error) throw new Error(String(progress.error))
      return { status: 'ok', progress }
    }
    await new Promise((resolve) => window.setTimeout(resolve, 800))
  }
  return { status: 'ok', progress_id: progressId }
}

async function refreshAndPollWithProgress(
  accountIdsOrTokens: string[],
  onProgress?: (progress: AccountRefreshProgress) => void,
) {
  const accessTokens = Array.from(new Set(accountIdsOrTokens.map(resolveToken).filter(Boolean)))
  if (!accessTokens.length) {
    throw new Error('没有可刷新的 access token')
  }

  const start = await apiClient.post<{ access_tokens: string[] }, { progress_id: string }>(
    '/api/accounts/refresh',
    { access_tokens: accessTokens },
  )
  const progressId = cleanString(start.progress_id)
  if (!progressId) {
    return { status: 'ok', progress: null as AccountRefreshProgress | null }
  }

  const deadline = Date.now() + Math.max(90_000, accessTokens.length * 15_000)
  while (Date.now() < deadline) {
    const progress = await apiClient.get<never, AccountRefreshProgress>(
      `/api/accounts/refresh/progress/${encodeURIComponent(progressId)}`,
    )
    onProgress?.(progress)
    if (progress.done || progress.error) {
      if (progress.error) throw new Error(String(progress.error))
      return { status: 'ok', progress }
    }
    await new Promise((resolve) => window.setTimeout(resolve, 900))
  }

  throw new Error('刷新进度超时，请稍后重新打开列表查看结果')
}

async function reLoginAndPollWithProgress(
  accountIdsOrTokens: string[],
  onProgress?: (progress: AccountReLoginProgress) => void,
) {
  const accessTokens = Array.from(new Set(accountIdsOrTokens.map(resolveToken).filter(Boolean)))
  if (!accessTokens.length) {
    throw new Error('没有可恢复的 access token')
  }

  const start = await apiClient.post<{ access_tokens: string[] }, { progress_id: string }>(
    '/api/accounts/re-login',
    { access_tokens: accessTokens },
  )
  const progressId = cleanString(start.progress_id)
  if (!progressId) {
    return { status: 'ok', progress: null as AccountReLoginProgress | null }
  }

  const deadline = Date.now() + Math.max(120_000, accessTokens.length * 60_000)
  while (Date.now() < deadline) {
    const progress = await apiClient.get<never, AccountReLoginProgress>(
      `/api/accounts/re-login/progress/${encodeURIComponent(progressId)}`,
    )
    onProgress?.(progress)
    if (progress.done || progress.error) {
      if (progress.error) throw new Error(String(progress.error))
      return { status: 'ok', progress }
    }
    await new Promise((resolve) => window.setTimeout(resolve, 900))
  }

  throw new Error('恢复异常账号进度超时，请稍后重新打开列表查看结果')
}

async function updateStatus(accountId: string, status: string) {
  const accessToken = resolveToken(accountId)
  const response = await apiClient.post<
    { access_token: string; status: string },
    { item?: BackendAccount; items?: BackendAccount[] }
  >('/api/accounts/update', { access_token: accessToken, status })
  return {
    status: 'ok',
    account: response.item ? mapBackendAccount(response.item, 0, new Set()) : undefined,
  }
}

async function bulkByIds(accountIds: string[], action: (accountId: string) => Promise<unknown>) {
  let successCount = 0
  const errors: string[] = []
  for (const accountId of accountIds) {
    try {
      await action(accountId)
      successCount += 1
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      errors.push(`${accountId}: ${message}`)
    }
  }
  return { status: 'ok', success_count: successCount, errors }
}

export const reverseAccountsApi = {
  list: async () => {
    const response = await apiClient.get<never, BackendAccountsResponse>('/api/accounts')
    return mapAccountsResponse(response)
  },

  upsert: async (payload: Partial<ReverseAccount>) => {
    const account = accountFromPayload(payload)
    const response = await apiClient.post<
      { tokens: string[]; accounts: Array<Record<string, unknown>> },
      { items?: BackendAccount[] }
    >('/api/accounts', {
      tokens: [],
      accounts: [account],
    })
    const mapped = mapAccountsResponse({ items: response.items || [] })
    return { status: 'ok', account: mapped.accounts.find((item) => item.access_token === account.access_token) || mapped.accounts[0] }
  },

  delete: async (accountId: string) => {
    const accessToken = resolveToken(accountId)
    await apiClient.request<unknown, { removed: number }>({
      method: 'DELETE',
      url: '/api/accounts',
      data: { tokens: [accessToken] },
    })
    accountTokenById.delete(accountId)
    return { status: 'ok', deleted: accountId }
  },

  refreshToken: async (accountId: string) => {
    await refreshAndPoll([resolveToken(accountId)])
    return { status: 'ok', account: undefined as unknown as ReverseAccount }
  },

  refreshAccountsWithProgress: (
    accountIdsOrTokens: string[],
    onProgress?: (progress: AccountRefreshProgress) => void,
  ) => refreshAndPollWithProgress(accountIdsOrTokens, onProgress),

  reLoginAccountsWithProgress: (
    accountIdsOrTokens: string[],
    onProgress?: (progress: AccountReLoginProgress) => void,
  ) => reLoginAndPollWithProgress(accountIdsOrTokens, onProgress),

  exportAccounts: (accountIdsOrTokens: string[], format: 'json' | 'zip' = 'json') =>
    apiClient.post<{ access_tokens: string[]; format: 'json' | 'zip' }, Blob>('/api/accounts/export', {
      access_tokens: Array.from(new Set(accountIdsOrTokens.map(resolveToken).filter(Boolean))),
      format,
    }, {
      responseType: 'blob',
    }),

  resetAccountState: async (accountId: string) => {
    return updateStatus(accountId, STATUS_NORMAL)
  },

  enable: async (accountId: string) =>
    updateStatus(accountId, STATUS_NORMAL),

  disable: async (accountId: string) =>
    updateStatus(accountId, STATUS_DISABLED),

  bulkEnable: (accountIds: string[]) =>
    bulkByIds(accountIds, (accountId) => reverseAccountsApi.enable(accountId)),

  bulkDisable: (accountIds: string[]) =>
    bulkByIds(accountIds, (accountId) => reverseAccountsApi.disable(accountId)),

  bulkDelete: (accountIds: string[]) =>
    bulkByIds(accountIds, (accountId) => reverseAccountsApi.delete(accountId)),

  resolveCookie: async (_cookie: string) => ({
    status: 'unsupported',
    snlm0e: '',
    model_ids: { ...EMPTY_MODEL_IDS },
  }),
}

import { computed, onActivated, onMounted, reactive, ref, watch } from 'vue'
import { accountImportsApi, proxyApi, reverseAccountsApi } from '@/api'
import type {
  CPAImportJob,
  CPAPool,
  CPARemoteFile,
  OAuthLoginStartResponse,
  Sub2APIRemoteAccount,
  Sub2APIServer,
} from '@/api/accountImports'
import type { ProxyProfile } from '@/api/proxy'
import type { AccountReLoginProgress, AccountRefreshProgress, ReverseAccount } from '@/api/reverseAccounts'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useToast } from '@/composables/useToast'
import { statusCategory, type AccountStatusFilter } from './viewUtils'

type AccountsViewMode = 'list' | 'cards'
type BulkAction = 'refresh' | 'relogin' | 'reset' | 'enable' | 'disable' | 'delete'
type AccountProxyMode = 'global' | 'direct' | 'profile' | 'custom'
export type AccountImportMode = 'oauth' | 'access_token' | 'session_json' | 'codex_json' | 'cpa_json' | 'remote_cpa' | 'sub2api'
type ImportedAccountRecord = Partial<ReverseAccount> & Record<string, unknown>
type BackendStatus = '正常' | '限流' | '异常' | '禁用'

type AccountForm = {
  id: string
  access_token: string
  type: string
  source_type: string
  proxy: string
  quota: string
  status: BackendStatus
}

const ACCOUNTS_VIEW_MODE_KEY = 'accounts-view-mode'
const BACKEND_STATUS_VALUES = ['正常', '限流', '异常', '禁用'] as const
const ACCOUNT_PAGE_SIZE_OPTIONS = [20, 50, 100]
const DEFAULT_PAGE_SIZE = 50
const REFRESH_BATCH_SIZE = 20

function createDefaultForm(): AccountForm {
  return {
    id: '',
    access_token: '',
    type: 'free',
    source_type: 'web',
    proxy: '',
    quota: '',
    status: '正常',
  }
}

function normalizeErrorMessage(error: unknown): string {
  const raw = error instanceof Error ? error.message : String(error)
  const duplicateMatch = raw.match(
    /duplicate cookie principal:\s*same\s+(__Secure-[^\s]+)\s+as\s+account\s+([a-z0-9_-]+)/i
  )
  if (!duplicateMatch) return raw
  const [, principal, accountId] = duplicateMatch
  return `账号主身份重复：${principal}（已存在于账号 ${accountId}）`
}

function normalizeBackendStatus(value: unknown, fallback: BackendStatus = '正常'): BackendStatus {
  const raw = String(value || '').trim()
  return BACKEND_STATUS_VALUES.includes(raw as BackendStatus) ? raw as BackendStatus : fallback
}

function normalizeQuota(value: unknown): number | undefined {
  const raw = String(value ?? '').trim()
  if (!raw) return undefined
  const parsed = Number(raw)
  return Number.isFinite(parsed) ? Math.max(0, Math.trunc(parsed)) : undefined
}

function proxyProfileIdFromValue(value: unknown): string {
  const raw = String(value || '').trim()
  return raw.toLowerCase().startsWith('profile:') ? raw.slice('profile:'.length).trim() : ''
}

function firstMutationError(errors: unknown): string {
  if (!Array.isArray(errors) || errors.length === 0) return ''
  const first = errors[0]
  if (typeof first === 'string') return first
  if (first && typeof first === 'object') {
    return String((first as Record<string, unknown>).error || '').trim()
  }
  return ''
}

function normalizeImportAccount(row: unknown): ImportedAccountRecord {
  if (!row || typeof row !== 'object' || Array.isArray(row)) {
    throw new Error('导入文件中的账号项必须是对象')
  }

  const source = row as Record<string, unknown>
  const payload: ImportedAccountRecord = {}
  const accountId = String(source.id || '').trim()
  const accessToken = String(source.access_token || source.accessToken || source.cookie || '').trim()

  if (!accountId && !accessToken) {
    throw new Error('账号至少需要包含 id 或 access_token')
  }

  if (accountId) payload.id = accountId
  if (accessToken) payload.access_token = accessToken
  if ('name' in source) payload.name = String(source.name || '').trim()
  if ('type' in source) payload.type = String(source.type || '').trim()
  if ('source_type' in source) payload.source_type = String(source.source_type || '').trim()
  if ('proxy' in source) payload.proxy = String(source.proxy || '').trim()
  if ('quota' in source) payload.quota = normalizeQuota(source.quota)
  if ('status' in source) payload.backend_status = normalizeBackendStatus(source.status)
  if ('enabled' in source) payload.enabled = Boolean(source.enabled)

  return payload
}

function createExportFilename(extension = 'json') {
  const now = new Date()
  const parts = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0'),
    '-',
    String(now.getHours()).padStart(2, '0'),
    String(now.getMinutes()).padStart(2, '0'),
    String(now.getSeconds()).padStart(2, '0'),
  ]
  return `accounts-export-${parts.join('')}.${extension}`
}

function saveBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  window.URL.revokeObjectURL(url)
}

function uniqueTokens(tokens: string[]) {
  return Array.from(new Set(tokens.map((token) => token.trim()).filter(Boolean)))
}

function parseTokenLines(text: string) {
  return uniqueTokens(
    text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith('#')),
  )
}

function collectAccessTokens(value: unknown, tokens = new Set<string>()): string[] {
  if (!value) return Array.from(tokens)

  if (typeof value === 'string') {
    const raw = value.trim()
    if (/^(sk-|eyJ|sess-|ya29\.|at-)/i.test(raw) || raw.length > 80) {
      tokens.add(raw)
    }
    return Array.from(tokens)
  }

  if (Array.isArray(value)) {
    value.forEach((item) => collectAccessTokens(item, tokens))
    return Array.from(tokens)
  }

  if (typeof value === 'object') {
    const source = value as Record<string, unknown>
    for (const [key, item] of Object.entries(source)) {
      const normalizedKey = key.toLowerCase()
      if (
        normalizedKey === 'accesstoken' ||
        normalizedKey === 'access_token' ||
        normalizedKey === 'access-token' ||
        normalizedKey === 'token'
      ) {
        const token = String(item || '').trim()
        if (token) tokens.add(token)
        continue
      }
      collectAccessTokens(item, tokens)
    }
  }

  return Array.from(tokens)
}

function parseJsonTokens(rawText: string, label: string) {
  const text = rawText.trim()
  if (!text) throw new Error(`请先粘贴${label}`)
  const parsed = JSON.parse(text)
  const tokens = uniqueTokens(collectAccessTokens(parsed))
  if (!tokens.length) throw new Error(`${label}中没有找到 access token`)
  return tokens
}

export function useAccountsPage() {
  const loading = ref(false)
  const saving = ref(false)
  const showModal = ref(false)
  const showOAuthModal = ref(false)
  const keyword = ref('')
  const statusFilter = ref<AccountStatusFilter>('all')
  const currentPage = ref(1)
  const pageSize = ref(DEFAULT_PAGE_SIZE)
  const editingId = ref<string | null>(null)
  const accounts = ref<ReverseAccount[]>([])
  const selectedIds = ref<string[]>([])
  const batchBusy = ref(false)
  const batchActionLabel = ref('')
  const viewMode = ref<AccountsViewMode>('list')
  const refreshingAccountId = ref('')
  const resettingAccountId = ref('')
  const reloginingAccountId = ref('')
  const importBusy = ref(false)
  const exportBusy = ref(false)
  const showImportModal = ref(false)
  const importMode = ref<AccountImportMode>('oauth')
  const manualTokenText = ref('')
  const sessionJsonText = ref('')
  const codexJsonText = ref('')
  const remoteCPAPools = ref<CPAPool[]>([])
  const remoteCPAFiles = ref<CPARemoteFile[]>([])
  const selectedCPAPoolId = ref('')
  const selectedCPAFileNames = ref<string[]>([])
  const cpaImportJob = ref<CPAImportJob | null>(null)
  const sub2apiServers = ref<Sub2APIServer[]>([])
  const sub2apiAccounts = ref<Sub2APIRemoteAccount[]>([])
  const selectedSub2APIServerId = ref('')
  const selectedSub2APIAccountIds = ref<string[]>([])
  const sub2apiImportJob = ref<CPAImportJob | null>(null)
  const proxyProfiles = ref<ProxyProfile[]>([])
  const proxyProfilesLoading = ref(false)
  const proxyTesting = ref(false)
  const proxyMode = ref<AccountProxyMode>('global')
  const selectedProxyProfileId = ref('')
  const customProxyInput = ref('')
  const showRefreshProgress = ref(false)
  const refreshProgressTitle = ref('')
  const refreshProgress = ref<AccountRefreshProgress | null>(null)
  const oauthStarting = ref(false)
  const oauthSubmitting = ref(false)
  const oauthEmailHint = ref('')
  const oauthCallback = ref('')
  const oauthSession = ref<OAuthLoginStartResponse | null>(null)
  const lastLoadedAt = ref(0)
  const toast = useToast()
  const confirmDialog = useConfirmDialog()
  const form = reactive(createDefaultForm())
  const accountStatusOptions = [
    { label: '正常', value: '正常' },
    { label: '限流', value: '限流' },
    { label: '异常', value: '异常' },
    { label: '禁用', value: '禁用' },
  ] as const

  const filteredAccounts = computed(() => {
    const query = keyword.value.trim().toLowerCase()
    return accounts.value.filter((item) => {
      const matchesQuery = !query || (
        item.id.toLowerCase().includes(query) ||
        (item.name || '').toLowerCase().includes(query) ||
        (item.cookie || '').toLowerCase().includes(query) ||
        (item.access_token || '').toLowerCase().includes(query) ||
        (item.email || '').toLowerCase().includes(query) ||
        (item.user_id || '').toLowerCase().includes(query) ||
        (item.type || '').toLowerCase().includes(query) ||
        (item.source_type || '').toLowerCase().includes(query) ||
        (item.proxy || '').toLowerCase().includes(query)
      )
      const matchesStatus =
        statusFilter.value === 'all' || statusCategory(item) === statusFilter.value
      return (
        matchesQuery &&
        matchesStatus
      )
    })
  })

  const pageCount = computed(() => Math.max(1, Math.ceil(filteredAccounts.value.length / pageSize.value)))

  const pagedAccounts = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value
    return filteredAccounts.value.slice(start, start + pageSize.value)
  })

  const statusFilterOptions = [
    { label: '全部状态', value: 'all' },
    { label: '正常', value: 'normal' },
    { label: '受限', value: 'limited' },
    { label: '异常', value: 'abnormal' },
    { label: '禁用', value: 'disabled' },
  ] as const

  const importModeOptions = [
    { label: 'OAuth 登录', value: 'oauth' },
    { label: 'Access Token', value: 'access_token' },
    { label: 'Session JSON', value: 'session_json' },
    { label: 'Codex JSON', value: 'codex_json' },
    { label: 'CPA JSON 文件', value: 'cpa_json' },
    { label: '远程 CPA', value: 'remote_cpa' },
    { label: 'Sub2API', value: 'sub2api' },
  ] as const

  const accountProxyModeOptions = [
    { label: '使用全局代理', value: 'global' },
    { label: '强制直连', value: 'direct' },
    { label: '代理分组', value: 'profile' },
    { label: '自定义代理', value: 'custom' },
  ] as const

  const selectedSet = computed(() => new Set(selectedIds.value))

  const selectedCount = computed(() => selectedIds.value.length)

  const abnormalAccountIds = computed(() => (
    accounts.value
      .filter((item) => statusCategory(item) === 'abnormal')
      .map((item) => item.id)
  ))

  const abnormalAccountCount = computed(() => abnormalAccountIds.value.length)

  const allVisibleSelected = computed(() => {
    const visible = pagedAccounts.value
      .filter((item) => !item.is_demo)
      .map((item) => item.id)
    if (!visible.length) return false
    return visible.every((id) => selectedSet.value.has(id))
  })

  const refreshProgressPercent = computed(() => {
    const progress = refreshProgress.value
    const total = Math.max(0, Number(progress?.total || 0))
    if (total <= 0) return 0
    return Math.min(100, Math.round((Math.max(0, Number(progress?.processed || 0)) / total) * 100))
  })

  const cpaPoolOptions = computed(() => [
    { label: '选择 CPA 服务器', value: '' },
    ...remoteCPAPools.value.map((pool) => ({ label: pool.name || pool.base_url || pool.id, value: pool.id })),
  ])

  const sub2apiServerOptions = computed(() => [
    { label: '选择 Sub2API 服务器', value: '' },
    ...sub2apiServers.value.map((server) => ({ label: server.name || server.base_url || server.id, value: server.id })),
  ])

  const proxyProfileOptions = computed(() => {
    const rows = proxyProfiles.value.map((profile) => ({
      label: `${profile.enabled === false ? '停用 · ' : ''}${profile.name || profile.id}`,
      value: profile.id,
    }))
    const selectedId = selectedProxyProfileId.value
    if (selectedId && !rows.some((item) => item.value === selectedId)) {
      rows.unshift({ label: `未知分组 · ${selectedId}`, value: selectedId })
    }
    return [
      { label: '选择代理分组', value: '' },
      ...rows,
    ]
  })

  const accountProxyPreview = computed(() => {
    const raw = form.proxy.trim()
    if (!raw) return '当前：使用全局代理'
    if (raw.toLowerCase() === 'direct') return '当前：强制直连'
    const profileId = proxyProfileIdFromValue(raw)
    if (profileId) {
      const profile = proxyProfiles.value.find((item) => item.id === profileId)
      return `当前：代理分组 ${profile?.name || profileId}`
    }
    return `当前：${raw}`
  })

  function setError(prefix: string, error: unknown, notify = true) {
    const message = normalizeErrorMessage(error)
    if (notify) toast.error(`${prefix}: ${message}`)
  }

  function resetForm() {
    editingId.value = null
    Object.assign(form, createDefaultForm())
    syncProxyControlsFromValue(form.proxy)
  }

  function syncProxyControlsFromValue(value: unknown) {
    const raw = String(value || '').trim()
    customProxyInput.value = ''
    selectedProxyProfileId.value = ''
    if (!raw) {
      proxyMode.value = 'global'
      return
    }
    if (raw.toLowerCase() === 'direct') {
      proxyMode.value = 'direct'
      return
    }
    const profileId = proxyProfileIdFromValue(raw)
    if (profileId) {
      proxyMode.value = 'profile'
      selectedProxyProfileId.value = profileId
      return
    }
    proxyMode.value = 'custom'
    customProxyInput.value = raw
  }

  function setProxyMode(mode: string) {
    const nextMode = ['global', 'direct', 'profile', 'custom'].includes(mode)
      ? mode as AccountProxyMode
      : 'global'
    proxyMode.value = nextMode
    if (nextMode === 'global') {
      form.proxy = ''
    } else if (nextMode === 'direct') {
      form.proxy = 'direct'
    } else if (nextMode === 'profile') {
      form.proxy = selectedProxyProfileId.value ? `profile:${selectedProxyProfileId.value}` : ''
    } else {
      form.proxy = customProxyInput.value.trim()
    }
  }

  function selectProxyProfile(profileId: string) {
    selectedProxyProfileId.value = profileId.trim()
    proxyMode.value = 'profile'
    form.proxy = selectedProxyProfileId.value ? `profile:${selectedProxyProfileId.value}` : ''
  }

  function setCustomProxyInput(value: string) {
    customProxyInput.value = value.trim()
    proxyMode.value = 'custom'
    form.proxy = customProxyInput.value
  }

  async function loadData(options?: { silentErrorToast?: boolean }) {
    loading.value = true
    try {
      const res = await reverseAccountsApi.list()
      accounts.value = (res.accounts || []).map((item) => ({
        ...item,
        lanes: Array.isArray(item.lanes) ? item.lanes : [],
        model_ids: {
          fast: item.model_ids?.fast || '',
          thinking: item.model_ids?.thinking || '',
          pro: item.model_ids?.pro || '',
        },
      }))
      const existingIds = new Set(accounts.value.map((item) => item.id))
      selectedIds.value = selectedIds.value.filter((id) => existingIds.has(id))
      lastLoadedAt.value = Date.now()
    } catch (error) {
      setError('加载失败', error, !options?.silentErrorToast)
    } finally {
      loading.value = false
    }
  }

  async function loadProxyProfiles(options?: { silentErrorToast?: boolean }) {
    proxyProfilesLoading.value = true
    try {
      const response = await proxyApi.listProfiles()
      proxyProfiles.value = Array.isArray(response.profiles)
        ? response.profiles.filter((profile) => profile.id)
        : []
    } catch (error) {
      if (!options?.silentErrorToast) {
        setError('加载代理分组失败', error)
      }
    } finally {
      proxyProfilesLoading.value = false
    }
  }

  async function testAccountProxy() {
    if (proxyTesting.value) return

    const rawProxy = form.proxy.trim()
    if (rawProxy.toLowerCase() === 'direct') {
      toast.info('当前账号强制直连，不需要测试代理')
      return
    }

    if (proxyMode.value === 'profile' && !selectedProxyProfileId.value) {
      toast.warning('请先选择代理分组')
      return
    }

    if (proxyMode.value === 'custom' && !customProxyInput.value.trim()) {
      toast.warning('请先填写自定义代理地址')
      return
    }

    const confirmed = await confirmDialog.ask({
      title: '确认测试账号代理',
      message: '即将通过当前账号代理配置发起外部网络测试请求。请确认当前允许测试该代理连接。',
      confirmText: '开始测试',
      cancelText: '取消',
    })
    if (!confirmed) return

    proxyTesting.value = true
    try {
      const response = proxyMode.value === 'profile'
        ? await proxyApi.testProfile({ id: selectedProxyProfileId.value })
        : await proxyApi.test(proxyMode.value === 'custom' ? customProxyInput.value.trim() : '')
      const result = response.result
      if (result.ok) {
        toast.success(`代理可用：${result.latency_ms} ms，HTTP ${result.status}`)
      } else {
        toast.error(`代理不可用：${result.error || '未知错误'}`)
      }
    } catch (error) {
      setError('测试代理失败', error)
    } finally {
      proxyTesting.value = false
    }
  }

  function setViewMode(mode: AccountsViewMode) {
    viewMode.value = mode
    localStorage.setItem(ACCOUNTS_VIEW_MODE_KEY, mode)
  }

  function isSelected(accountId: string) {
    return selectedSet.value.has(accountId)
  }

  function toggleSelect(accountId: string, checked?: boolean) {
    const next = new Set(selectedIds.value)
    const shouldSelect = typeof checked === 'boolean' ? checked : !next.has(accountId)
    if (shouldSelect) {
      next.add(accountId)
    } else {
      next.delete(accountId)
    }
    selectedIds.value = Array.from(next)
  }

  function clearSelection() {
    selectedIds.value = []
  }

  function toggleSelectAllVisible(checked?: boolean) {
    const ids = pagedAccounts.value
      .filter((item) => !item.is_demo)
      .map((item) => item.id)
    const next = new Set(selectedIds.value)
    const shouldSelect = typeof checked === 'boolean' ? checked : !allVisibleSelected.value
    for (const id of ids) {
      if (shouldSelect) next.add(id)
      else next.delete(id)
    }
    selectedIds.value = Array.from(next)
  }

  async function setImportMode(mode: AccountImportMode) {
    importMode.value = mode
    if (mode === 'remote_cpa' && remoteCPAPools.value.length === 0) {
      await loadCPAPools()
    }
    if (mode === 'sub2api' && sub2apiServers.value.length === 0) {
      await loadSub2APIServers()
    }
  }

  async function openImportModal(mode: AccountImportMode = 'oauth') {
    showImportModal.value = true
    await setImportMode(mode)
  }

  function closeImportModal() {
    if (importBusy.value) return
    showImportModal.value = false
  }

  async function importTokenBatch(tokens: string[], sourceType: string, title: string) {
    const normalizedTokens = uniqueTokens(tokens)
    if (!normalizedTokens.length) {
      toast.warning('没有可导入的 access token')
      return
    }

    const confirmed = await confirmDialog.ask({
      title,
      message: `即将导入 ${normalizedTokens.length} 个账号，已存在账号会刷新远端信息。是否继续？`,
      confirmText: '确认导入',
      cancelText: '取消',
    })
    if (!confirmed) return

    importBusy.value = true
    let successCount = 0
    const errors: string[] = []
    try {
      for (let index = 0; index < normalizedTokens.length; index += 20) {
        const batch = normalizedTokens.slice(index, index + 20)
        await Promise.all(batch.map(async (token) => {
          try {
            await reverseAccountsApi.upsert({
              access_token: token,
              type: 'free',
              source_type: sourceType,
              backend_status: '正常',
              enabled: true,
            })
            successCount += 1
          } catch (error) {
            errors.push(`${token.slice(0, 6)}...${token.slice(-4)}: ${normalizeErrorMessage(error)}`)
          }
        }))
      }

      await loadData({ silentErrorToast: true })
      if (errors.length > 0) {
        toast.warning(`${title}完成：成功 ${successCount} 个，失败 ${errors.length} 个`)
      } else {
        toast.success(`${title}完成：成功 ${successCount} 个`)
      }
      if (successCount > 0) {
        manualTokenText.value = ''
        sessionJsonText.value = ''
        codexJsonText.value = ''
      }
    } finally {
      importBusy.value = false
    }
  }

  async function importManualTokenText() {
    await importTokenBatch(parseTokenLines(manualTokenText.value), 'manual', '导入 Access Token')
  }

  async function importTokenTextFile(file: File | null | undefined) {
    if (!file) return
    const text = await file.text()
    manualTokenText.value = text
    await importManualTokenText()
  }

  async function importSessionJson() {
    await importTokenBatch(parseJsonTokens(sessionJsonText.value, 'Session JSON'), 'session_json', '导入 Session JSON')
  }

  async function importCodexJson() {
    await importTokenBatch(parseJsonTokens(codexJsonText.value, 'Codex 认证 JSON'), 'codex', '导入 Codex 认证 JSON')
  }

  async function importLocalCPAFiles(files: FileList | File[] | null | undefined) {
    const fileList = Array.from(files || [])
    if (!fileList.length) return
    importBusy.value = true
    try {
      const tokens: string[] = []
      for (const file of fileList) {
        const text = await file.text()
        tokens.push(...parseJsonTokens(text, file.name))
      }
      importBusy.value = false
      await importTokenBatch(tokens, 'cpa_json', '导入 CPA JSON 文件')
    } catch (error) {
      setError('导入 CPA JSON 文件失败', error)
    } finally {
      importBusy.value = false
    }
  }

  async function loadCPAPools() {
    importBusy.value = true
    try {
      const response = await accountImportsApi.listCPAPools()
      remoteCPAPools.value = response.pools || []
      if (!selectedCPAPoolId.value && remoteCPAPools.value.length > 0) {
        selectedCPAPoolId.value = remoteCPAPools.value[0].id
      }
    } catch (error) {
      setError('加载 CPA 服务器失败', error)
    } finally {
      importBusy.value = false
    }
  }

  async function loadCPAFiles() {
    const poolId = selectedCPAPoolId.value
    if (!poolId) {
      toast.warning('请先选择 CPA 服务器')
      return
    }
    const confirmed = await confirmDialog.ask({
      title: '加载远程 CPA 文件',
      message: '即将访问已配置的远程 CPA 服务器并读取文件列表。请确认当前允许连接该外部服务。',
      confirmText: '确认加载',
      cancelText: '取消',
    })
    if (!confirmed) return

    importBusy.value = true
    try {
      const response = await accountImportsApi.listCPAPoolFiles(poolId)
      remoteCPAFiles.value = response.files || []
      selectedCPAFileNames.value = []
    } catch (error) {
      setError('加载 CPA 文件失败', error)
    } finally {
      importBusy.value = false
    }
  }

  function toggleCPAFile(name: string, checked?: boolean) {
    const next = new Set(selectedCPAFileNames.value)
    const shouldSelect = typeof checked === 'boolean' ? checked : !next.has(name)
    if (shouldSelect) next.add(name)
    else next.delete(name)
    selectedCPAFileNames.value = Array.from(next)
  }

  async function pollCPAImportJob(poolId: string) {
    for (let index = 0; index < 180; index += 1) {
      const response = await accountImportsApi.getCPAImportJob(poolId)
      cpaImportJob.value = response.import_job || null
      const status = cpaImportJob.value?.status
      if (status === 'completed' || status === 'failed') return cpaImportJob.value
      await new Promise((resolve) => window.setTimeout(resolve, 1000))
    }
    throw new Error('CPA 导入进度超时')
  }

  async function startRemoteCPAImport() {
    const poolId = selectedCPAPoolId.value
    const names = selectedCPAFileNames.value
    if (!poolId) {
      toast.warning('请先选择 CPA 服务器')
      return
    }
    if (!names.length) {
      toast.warning('请先选择要导入的 CPA 文件')
      return
    }

    const confirmed = await confirmDialog.ask({
      title: '确认远程 CPA 导入',
      message: `即将从远程 CPA 服务器导入 ${names.length} 个文件里的账号，并写入本地账号池。请确认远程来源可信且当前不在生产压测窗口。`,
      confirmText: '开始导入',
      cancelText: '取消',
    })
    if (!confirmed) return

    importBusy.value = true
    try {
      const start = await accountImportsApi.startCPAImport(poolId, names)
      cpaImportJob.value = start.import_job || null
      const job = await pollCPAImportJob(poolId)
      const failed = Number(job?.failed || 0)
      toast[failed > 0 ? 'warning' : 'success'](
        `远程 CPA 导入完成：新增 ${job?.added || 0}，跳过 ${job?.skipped || 0}，刷新 ${job?.refreshed || 0}，失败 ${failed}`,
      )
      await loadData({ silentErrorToast: true })
    } catch (error) {
      setError('远程 CPA 导入失败', error)
    } finally {
      importBusy.value = false
    }
  }

  async function loadSub2APIServers() {
    importBusy.value = true
    try {
      const response = await accountImportsApi.listSub2APIServers()
      sub2apiServers.value = response.servers || []
      if (!selectedSub2APIServerId.value && sub2apiServers.value.length > 0) {
        selectedSub2APIServerId.value = sub2apiServers.value[0].id
      }
    } catch (error) {
      setError('加载 Sub2API 服务器失败', error)
    } finally {
      importBusy.value = false
    }
  }

  async function loadSub2APIAccounts() {
    const serverId = selectedSub2APIServerId.value
    if (!serverId) {
      toast.warning('请先选择 Sub2API 服务器')
      return
    }
    const confirmed = await confirmDialog.ask({
      title: '加载 Sub2API 账号',
      message: '即将访问已配置的 Sub2API 服务器并读取远程 OpenAI 账号列表。请确认当前允许连接该外部服务。',
      confirmText: '确认加载',
      cancelText: '取消',
    })
    if (!confirmed) return

    importBusy.value = true
    try {
      const response = await accountImportsApi.listSub2APIServerAccounts(serverId)
      sub2apiAccounts.value = response.accounts || []
      selectedSub2APIAccountIds.value = []
    } catch (error) {
      setError('加载 Sub2API 账号失败', error)
    } finally {
      importBusy.value = false
    }
  }

  function toggleSub2APIAccount(accountId: string, checked?: boolean) {
    const next = new Set(selectedSub2APIAccountIds.value)
    const shouldSelect = typeof checked === 'boolean' ? checked : !next.has(accountId)
    if (shouldSelect) next.add(accountId)
    else next.delete(accountId)
    selectedSub2APIAccountIds.value = Array.from(next)
  }

  async function pollSub2APIImportJob(serverId: string) {
    for (let index = 0; index < 180; index += 1) {
      const response = await accountImportsApi.getSub2APIImportJob(serverId)
      sub2apiImportJob.value = response.import_job || null
      const status = sub2apiImportJob.value?.status
      if (status === 'completed' || status === 'failed') return sub2apiImportJob.value
      await new Promise((resolve) => window.setTimeout(resolve, 1000))
    }
    throw new Error('Sub2API 导入进度超时')
  }

  async function startSub2APIImport() {
    const serverId = selectedSub2APIServerId.value
    const accountIds = selectedSub2APIAccountIds.value
    if (!serverId) {
      toast.warning('请先选择 Sub2API 服务器')
      return
    }
    if (!accountIds.length) {
      toast.warning('请先选择要导入的 Sub2API 账号')
      return
    }

    const confirmed = await confirmDialog.ask({
      title: '确认 Sub2API 导入',
      message: `即将从 Sub2API 服务器导入 ${accountIds.length} 个账号，并写入本地账号池。请确认远程来源可信且当前不在生产压测窗口。`,
      confirmText: '开始导入',
      cancelText: '取消',
    })
    if (!confirmed) return

    importBusy.value = true
    try {
      const start = await accountImportsApi.startSub2APIImport(serverId, accountIds)
      sub2apiImportJob.value = start.import_job || null
      const job = await pollSub2APIImportJob(serverId)
      const failed = Number(job?.failed || 0)
      toast[failed > 0 ? 'warning' : 'success'](
        `Sub2API 导入完成：新增 ${job?.added || 0}，跳过 ${job?.skipped || 0}，刷新 ${job?.refreshed || 0}，失败 ${failed}`,
      )
      await loadData({ silentErrorToast: true })
    } catch (error) {
      setError('Sub2API 导入失败', error)
    } finally {
      importBusy.value = false
    }
  }

  async function refreshAccountsWithProgress(accountIds: string[], title: string) {
    const targetIds = Array.from(new Set(accountIds.filter(Boolean)))
    if (!targetIds.length) {
      toast.warning('没有可刷新的账号')
      return
    }

    const confirmed = await confirmDialog.ask({
      title,
      message: `即将按每批 ${REFRESH_BATCH_SIZE} 个刷新 ${targetIds.length} 个账号的信息和额度，是否继续？`,
      confirmText: '开始刷新',
      cancelText: '取消',
    })
    if (!confirmed) return

    showRefreshProgress.value = true
    refreshProgressTitle.value = title
    refreshProgress.value = {
      total: targetIds.length,
      processed: 0,
      done: false,
      status_counts: {},
      total_quota: 0,
      result: null,
    }

    batchBusy.value = true
    batchActionLabel.value = title
    let processedOffset = 0
    let failedCount = 0
    const errors: string[] = []

    try {
      for (let index = 0; index < targetIds.length; index += REFRESH_BATCH_SIZE) {
        const batch = targetIds.slice(index, index + REFRESH_BATCH_SIZE)
        const result = await reverseAccountsApi.refreshAccountsWithProgress(batch, (progress) => {
          refreshProgress.value = {
            ...progress,
            total: targetIds.length,
            processed: Math.min(targetIds.length, processedOffset + Number(progress.processed || 0)),
            done: false,
          }
        })

        const batchProgress = result.progress
        const batchErrors = Array.isArray(batchProgress?.result?.errors)
          ? batchProgress.result.errors
          : []
        failedCount += batchErrors.length
        errors.push(...batchErrors.map((entry) => (
          typeof entry === 'string'
            ? entry
            : [entry.token, entry.error].filter(Boolean).join(': ')
        )).filter(Boolean))
        processedOffset += batch.length
        refreshProgress.value = {
          ...(batchProgress || refreshProgress.value || {}),
          total: targetIds.length,
          processed: Math.min(targetIds.length, processedOffset),
          done: processedOffset >= targetIds.length,
        }
      }

      await loadData({ silentErrorToast: true })
      refreshProgress.value = {
        ...(refreshProgress.value || { total: targetIds.length, processed: targetIds.length }),
        total: targetIds.length,
        processed: targetIds.length,
        done: true,
      }
      if (failedCount > 0) {
        toast.warning(`${title}完成，失败 ${failedCount} 个${errors[0] ? `：${errors[0]}` : ''}`)
      } else {
        toast.success(`${title}完成，共刷新 ${targetIds.length} 个账号`)
      }
    } catch (error) {
      refreshProgress.value = {
        ...(refreshProgress.value || { total: targetIds.length, processed: processedOffset }),
        total: targetIds.length,
        processed: Math.min(targetIds.length, processedOffset),
        done: true,
        error: normalizeErrorMessage(error),
      }
      setError(`${title}失败`, error)
      await loadData({ silentErrorToast: true })
    } finally {
      batchBusy.value = false
      batchActionLabel.value = ''
    }
  }

  async function refreshAllAccounts() {
    await refreshAccountsWithProgress(accounts.value.map((item) => item.id), '刷新所有账号信息和额度')
  }

  async function refreshSelectedAccounts() {
    await refreshAccountsWithProgress(selectedIds.value, '刷新选中账号信息和额度')
  }

  async function reLoginAccountsWithProgress(accountIds: string[], title = '恢复异常账号') {
    const abnormalSet = new Set(abnormalAccountIds.value)
    const targetIds = Array.from(new Set(accountIds.filter((id) => abnormalSet.has(id))))

    if (!targetIds.length) {
      toast.warning('没有可恢复的异常账号')
      return
    }

    if (targetIds.length < accountIds.length) {
      toast.info(`已过滤 ${accountIds.length - targetIds.length} 个非异常账号`)
    }

    const confirmed = await confirmDialog.ask({
      title,
      message: `确认对 ${targetIds.length} 个异常账号执行恢复登录流程吗？只有保存了邮箱和密码的账号才能恢复。`,
      confirmText: '确认恢复',
      cancelText: '取消',
    })
    if (!confirmed) return

    batchBusy.value = true
    batchActionLabel.value = title
    showRefreshProgress.value = true
    refreshProgressTitle.value = title
    refreshProgress.value = {
      total: targetIds.length,
      processed: 0,
      done: false,
      error: null,
      total_quota: 0,
    }

    try {
      const result = await reverseAccountsApi.reLoginAccountsWithProgress(targetIds, (progress: AccountReLoginProgress) => {
        refreshProgress.value = {
          ...progress,
          total: targetIds.length,
          processed: Math.min(targetIds.length, Number(progress.processed || 0)),
          done: Boolean(progress.done),
          total_quota: 0,
        }
      })

      const progress = result.progress
      const resultErrors = Array.isArray(progress?.result?.errors) ? progress.result.errors : []
      const progressErrors = Array.isArray(progress?.results)
        ? progress.results.filter((entry) => String(entry.error || '').trim())
        : []
      const failedCount = resultErrors.length + progressErrors.length
      const skippedCount = Number(progress?.result?.skipped || 0)

      await loadData({ silentErrorToast: true })
      refreshProgress.value = {
        ...(refreshProgress.value || { total: targetIds.length, processed: targetIds.length }),
        total: targetIds.length,
        processed: targetIds.length,
        done: true,
        total_quota: 0,
      }

      if (failedCount > 0 || skippedCount > 0) {
        const firstError = progressErrors[0]?.error
          || (typeof resultErrors[0] === 'string' ? resultErrors[0] : resultErrors[0]?.error)
          || ''
        toast.warning(`${title}完成：恢复 ${progress?.result?.relogined || 0} 个，跳过 ${skippedCount} 个，失败 ${failedCount} 个${firstError ? `，${firstError}` : ''}`)
      } else {
        toast.success(`${title}完成，共处理 ${targetIds.length} 个异常账号`)
      }
      selectedIds.value = selectedIds.value.filter((id) => !targetIds.includes(id))
    } catch (error) {
      refreshProgress.value = {
        ...(refreshProgress.value || { total: targetIds.length, processed: 0 }),
        total: targetIds.length,
        done: true,
        error: normalizeErrorMessage(error),
        total_quota: 0,
      }
      setError(`${title}失败`, error)
      await loadData({ silentErrorToast: true })
    } finally {
      batchBusy.value = false
      batchActionLabel.value = ''
      reloginingAccountId.value = ''
    }
  }

  async function reLoginAbnormalAccounts() {
    await reLoginAccountsWithProgress(abnormalAccountIds.value, '恢复所有异常账号')
  }

  async function reLoginAccount(accountId: string) {
    reloginingAccountId.value = accountId
    await reLoginAccountsWithProgress([accountId], '恢复异常账号')
  }

  function closeRefreshProgress() {
    if (!refreshProgress.value?.done && batchBusy.value) return
    showRefreshProgress.value = false
  }

  function openCreateModal() {
    resetForm()
    void loadProxyProfiles({ silentErrorToast: true })
    showModal.value = true
  }

  function openEditModal(item: ReverseAccount) {
    editingId.value = item.id
    form.id = item.id
    form.access_token = item.access_token || ''
    form.type = item.type || 'free'
    form.source_type = item.source_type || 'web'
    form.proxy = item.proxy || ''
    form.quota = item.image_quota_unknown ? '' : String(item.quota ?? '')
    form.status = normalizeBackendStatus(item.backend_status, item.enabled ? '正常' : '禁用')
    syncProxyControlsFromValue(form.proxy)
    void loadProxyProfiles({ silentErrorToast: true })
    showModal.value = true
  }

  function closeModal() {
    showModal.value = false
    resetForm()
  }

  function resetOAuthForm() {
    oauthStarting.value = false
    oauthSubmitting.value = false
    oauthEmailHint.value = ''
    oauthCallback.value = ''
    oauthSession.value = null
  }

  function openOAuthModal() {
    resetOAuthForm()
    showOAuthModal.value = true
  }

  function closeOAuthModal() {
    showOAuthModal.value = false
    resetOAuthForm()
  }

  async function copyOAuthUrl() {
    const url = oauthSession.value?.authorize_url || ''
    if (!url) return
    try {
      await navigator.clipboard.writeText(url)
      toast.success('授权 URL 已复制')
    } catch {
      toast.warning('复制失败，请手动复制')
    }
  }

  function reopenOAuthUrl() {
    const url = oauthSession.value?.authorize_url || ''
    if (url) window.open(url, '_blank', 'noopener,noreferrer')
  }

  async function startOAuthLogin() {
    const confirmed = await confirmDialog.ask({
      title: '确认开始 OAuth 登录',
      message: '即将生成 OAuth 授权会话并打开外部 ChatGPT 登录页面。请确认当前要用自己的账号完成授权。',
      confirmText: '开始登录',
      cancelText: '取消',
    })
    if (!confirmed) return

    oauthStarting.value = true
    try {
      const session = await accountImportsApi.startOAuthLogin(oauthEmailHint.value.trim())
      oauthSession.value = session
      oauthCallback.value = ''
      window.open(session.authorize_url, '_blank', 'noopener,noreferrer')
      toast.success('已打开授权页面')
    } catch (error) {
      setError('OAuth 启动失败', error)
    } finally {
      oauthStarting.value = false
    }
  }

  async function finishOAuthLogin() {
    const sessionId = oauthSession.value?.session_id || ''
    const callback = oauthCallback.value.trim()
    if (!sessionId) {
      toast.warning('请先生成授权 URL')
      return
    }
    if (!callback) {
      toast.warning('请粘贴 callback URL 或 code')
      return
    }

    const confirmed = await confirmDialog.ask({
      title: '确认导入 OAuth 账号',
      message: '即将使用当前 callback/code 换取账号认证信息并写入本地账号池，后台会保存 refresh_token 用于后续自动续期。是否继续？',
      confirmText: '确认导入',
      cancelText: '取消',
    })
    if (!confirmed) return

    oauthSubmitting.value = true
    try {
      const result = await accountImportsApi.finishOAuthLogin(sessionId, callback)
      const errorCount = Array.isArray(result.errors) ? result.errors.length : 0
      const firstError = firstMutationError(result.errors)
      if (errorCount > 0) {
        toast.warning(
          `OAuth 导入完成，新增 ${result.added || 0} 个，失败 ${errorCount} 个${firstError ? `：${firstError}` : ''}`,
        )
      } else {
        toast.success(`OAuth 导入完成，新增 ${result.added || 0} 个，跳过 ${result.skipped || 0} 个，已刷新 ${result.refreshed || 0} 个`)
      }
      closeOAuthModal()
      await loadData({ silentErrorToast: true })
    } catch (error) {
      setError('OAuth 导入失败', error)
    } finally {
      oauthSubmitting.value = false
    }
  }

  async function saveAccount() {
    if (!form.access_token.trim()) {
      toast.warning('Access token 不能为空')
      return
    }

    saving.value = true
    const accountIdForNotice = editingId.value || form.id || ''
    const isEditing = Boolean(editingId.value)

    try {
      const payloadId = editingId.value || form.id || undefined
      await reverseAccountsApi.upsert({
        id: payloadId,
        access_token: form.access_token.trim(),
        type: form.type.trim() || undefined,
        source_type: form.source_type.trim() || undefined,
        proxy: form.proxy.trim(),
        quota: normalizeQuota(form.quota),
        backend_status: form.status,
        enabled: form.status !== '禁用',
      })
      toast.success(isEditing ? `账号 ${accountIdForNotice} 已更新` : '账号已添加')
      closeModal()
      await loadData({ silentErrorToast: true })
    } catch (error) {
      setError('保存失败', error)
    } finally {
      saving.value = false
    }
  }

  async function toggleEnabled(item: ReverseAccount) {
    const nextEnabled = !item.enabled
    const confirmed = await confirmDialog.ask({
      title: nextEnabled ? '确认启用账号' : '确认禁用账号',
      message: `即将${nextEnabled ? '启用' : '禁用'}账号 ${item.id}。这会影响该账号是否参与后续请求分配，是否继续？`,
      confirmText: nextEnabled ? '启用' : '禁用',
      cancelText: '取消',
    })
    if (!confirmed) return

    try {
      if (item.enabled) {
        await reverseAccountsApi.disable(item.id)
      } else {
        await reverseAccountsApi.enable(item.id)
      }
      toast.success(`账号 ${item.id} 已${item.enabled ? '禁用' : '启用'}`)
      await loadData({ silentErrorToast: true })
    } catch (error) {
      setError('切换状态失败', error)
    }
  }

  async function refreshToken(accountId: string) {
    const confirmed = await confirmDialog.ask({
      title: '确认刷新账号',
      message: `即将刷新账号 ${accountId} 的远端信息和额度，可能触发外部 ChatGPT 请求。是否继续？`,
      confirmText: '开始刷新',
      cancelText: '取消',
    })
    if (!confirmed) return

    refreshingAccountId.value = accountId
    toast.info(`正在刷新账号 ${accountId} 的远端信息...`)
    try {
      await reverseAccountsApi.refreshToken(accountId)
      toast.success(`账号 ${accountId} 刷新成功`)
      await loadData({ silentErrorToast: true })
    } catch (error) {
      toast.error(`账号 ${accountId} 刷新失败：${normalizeErrorMessage(error)}`)
      await loadData({ silentErrorToast: true })
    } finally {
      refreshingAccountId.value = ''
    }
  }

  async function resetAccountState(accountId: string) {
    const confirmed = await confirmDialog.ask({
      title: '重置账号状态',
      message: `是否重置账号 ${accountId} 的配额和冷却？此操作会清空本地计数并移除冷却状态。`,
      confirmText: '确认重置',
      cancelText: '取消',
    })
    if (!confirmed) return

    resettingAccountId.value = accountId
    try {
      await reverseAccountsApi.resetAccountState(accountId)
      toast.success(`账号 ${accountId} 已重置`)
      await loadData({ silentErrorToast: true })
    } catch (error) {
      toast.error(`账号 ${accountId} 重置失败：${normalizeErrorMessage(error)}`)
      await loadData({ silentErrorToast: true })
    } finally {
      resettingAccountId.value = ''
    }
  }

  async function removeAccount(accountId: string) {
    const confirmed = await confirmDialog.ask({
      title: '删除账号',
      message: `确认删除账号 ${accountId} 吗？此操作不可恢复。`,
      confirmText: '确认删除',
      cancelText: '取消',
    })
    if (!confirmed) return

    try {
      await reverseAccountsApi.delete(accountId)
      toast.success(`账号 ${accountId} 已删除`)
      await loadData({ silentErrorToast: true })
    } catch (error) {
      setError('删除失败', error)
    }
  }

  async function runBulkAction(
    action: BulkAction,
    ids?: string[]
  ) {
    const targetIds = (ids || selectedIds.value).filter(Boolean)
    if (!targetIds.length) {
      toast.warning('请先选择账号')
      return
    }

    if (action === 'refresh') {
      await refreshAccountsWithProgress(targetIds, '批量刷新账号信息和额度')
      return
    }

    if (action === 'relogin') {
      await reLoginAccountsWithProgress(targetIds, '批量恢复异常账号')
      return
    }

    const actionMeta = {
      refresh: { title: '批量刷新账号信息', confirmText: '确认刷新', successText: '批量刷新完成' },
      reset: { title: '批量重置账号状态', confirmText: '确认重置', successText: '批量重置完成' },
      enable: { title: '批量启用账号', confirmText: '确认启用', successText: '批量启用完成' },
      disable: { title: '批量禁用账号', confirmText: '确认禁用', successText: '批量禁用完成' },
      delete: { title: '批量删除账号', confirmText: '确认删除', successText: '批量删除完成' },
    }[action]

    const confirmed = await confirmDialog.ask({
      title: actionMeta.title,
      message: `确认对选中的 ${targetIds.length} 个账号执行该操作吗？`,
      confirmText: actionMeta.confirmText,
      cancelText: '取消',
    })
    if (!confirmed) return

    batchBusy.value = true
    batchActionLabel.value = actionMeta.title
    try {
      let res: { success_count: number; errors: string[] }
      if (action === 'enable') {
        res = await reverseAccountsApi.bulkEnable(targetIds)
      } else if (action === 'disable') {
        res = await reverseAccountsApi.bulkDisable(targetIds)
      } else if (action === 'delete') {
        res = await reverseAccountsApi.bulkDelete(targetIds)
      } else {
        let successCount = 0
        const errors: string[] = []
        for (const accountId of targetIds) {
          try {
            await reverseAccountsApi.resetAccountState(accountId)
            successCount += 1
          } catch (error) {
            errors.push(`${accountId}: ${normalizeErrorMessage(error)}`)
          }
        }
        res = { success_count: successCount, errors }
      }

      const errors = Array.isArray(res.errors) ? res.errors.filter(Boolean) : []
      if (errors.length > 0) {
        toast.warning(`${actionMeta.successText}，成功 ${res.success_count} 个，失败 ${errors.length} 个`)
      } else {
        toast.success(`${actionMeta.successText}，共 ${res.success_count} 个`)
      }
      if (action === 'delete') {
        selectedIds.value = selectedIds.value.filter((id) => !targetIds.includes(id))
      }
      await loadData({ silentErrorToast: true })
      if (action !== 'delete') {
        clearSelection()
      }
    } catch (error) {
      setError(`${actionMeta.title}失败`, error)
    } finally {
      batchBusy.value = false
      batchActionLabel.value = ''
    }
  }

  async function exportAccounts(scope: 'selected' | 'all' | 'auto' = 'auto') {
    const targetIds = new Set(scope === 'all' ? [] : selectedIds.value)
    if (scope === 'selected' && targetIds.size === 0) {
      toast.warning('请先选择要导出的账号')
      return
    }

    const targetAccounts = (scope !== 'all' && targetIds.size
      ? accounts.value.filter((item) => targetIds.has(item.id))
      : accounts.value
    )

    if (!targetAccounts.length) {
      toast.warning('暂无可导出的账号')
      return
    }

    const exportScopeLabel = scope === 'all' || targetIds.size === 0 ? '全部' : '选中'
    const confirmed = await confirmDialog.ask({
      title: '导出账号认证',
      message: `即将导出${exportScopeLabel} ${targetAccounts.length} 个账号。导出文件可能包含 refresh_token、id_token 或 access token，请只在可信环境保存。是否继续？`,
      confirmText: '确认导出',
      cancelText: '取消',
    })
    if (!confirmed) return

    exportBusy.value = true
    try {
      const blob = await reverseAccountsApi.exportAccounts(targetAccounts.map((item) => item.id), 'json')
      saveBlob(blob, createExportFilename('json'))
      toast.success(`已导出 ${targetAccounts.length} 个完整认证账号`)
    } catch (error) {
      const status = (error as { status?: number }).status
      if (status !== 400) {
        setError('导出失败', error)
        return
      }

      const tokens = uniqueTokens(targetAccounts.map((item) => item.access_token || ''))
      if (!tokens.length) {
        setError('导出失败', error)
        return
      }

      saveBlob(new Blob([`${tokens.join('\n')}\n`], { type: 'text/plain;charset=utf-8' }), createExportFilename('txt'))
      toast.warning(`没有可导出的完整认证 JSON，已改为导出 ${tokens.length} 个 Access Token`)
    } finally {
      exportBusy.value = false
    }
  }

  async function importAccounts(file: File | null | undefined) {
    if (!file) return

    importBusy.value = true
    try {
      const rawText = await file.text()
      const parsed = JSON.parse(rawText)
      const rows = Array.isArray(parsed)
        ? parsed
        : Array.isArray(parsed?.accounts)
          ? parsed.accounts
          : null

      if (!rows) {
        throw new Error('导入文件格式不正确，需要是账号数组或 { accounts: [] }')
      }

      const normalizedRows = rows.map(normalizeImportAccount)
      if (!normalizedRows.length) {
        throw new Error('导入文件中没有可用账号')
      }

      const confirmed = await confirmDialog.ask({
        title: '批量导入账号',
        message: `即将导入 ${normalizedRows.length} 个账号。若 ID 已存在，将覆盖对应账号配置。是否继续？`,
        confirmText: '确认导入',
        cancelText: '取消',
      })
      if (!confirmed) return

      let successCount = 0
      const errors: string[] = []

      for (const row of normalizedRows) {
        try {
          await reverseAccountsApi.upsert(row)
          successCount += 1
        } catch (error) {
          const accountId = String(row.id || row.name || row.access_token || 'unknown')
          errors.push(`${accountId}: ${normalizeErrorMessage(error)}`)
        }
      }

      await loadData({ silentErrorToast: true })

      if (errors.length > 0) {
        const detail = errors.slice(0, 3).join('；')
        toast.warning(`导入完成：成功 ${successCount} 个，失败 ${errors.length} 个。${detail}`)
      } else {
        toast.success(`批量导入完成，共 ${successCount} 个账号`)
      }
    } catch (error) {
      setError('导入失败', error)
    } finally {
      importBusy.value = false
    }
  }

  watch(
    [keyword, statusFilter],
    () => {
      currentPage.value = 1
    },
  )

  watch(pageSize, () => {
    currentPage.value = 1
  })

  watch(pageCount, (count) => {
    if (currentPage.value > count) currentPage.value = count
    if (currentPage.value < 1) currentPage.value = 1
  })

  onMounted(async () => {
    const storedViewMode = localStorage.getItem(ACCOUNTS_VIEW_MODE_KEY)
    if (storedViewMode === 'list' || storedViewMode === 'cards') {
      viewMode.value = storedViewMode
    }
    await Promise.all([
      loadData({ silentErrorToast: true }),
      loadProxyProfiles({ silentErrorToast: true }),
    ])
  })

  onActivated(() => {
    if (!lastLoadedAt.value || Date.now() - lastLoadedAt.value > 30000) {
      void loadData({ silentErrorToast: true })
    }
  })

  return {
    loading,
    saving,
    showModal,
    showOAuthModal,
    keyword,
    statusFilter,
    statusFilterOptions,
    editingId,
    accounts,
    selectedIds,
    selectedCount,
    abnormalAccountCount,
    allVisibleSelected,
    currentPage,
    pageSize,
    pageSizeOptions: ACCOUNT_PAGE_SIZE_OPTIONS,
    pageCount,
    batchBusy,
    batchActionLabel,
    viewMode,
    refreshingAccountId,
    resettingAccountId,
    reloginingAccountId,
    importBusy,
    exportBusy,
    showImportModal,
    importMode,
    importModeOptions,
    manualTokenText,
    sessionJsonText,
    codexJsonText,
    remoteCPAPools,
    remoteCPAFiles,
    selectedCPAPoolId,
    selectedCPAFileNames,
    cpaImportJob,
    sub2apiServers,
    sub2apiAccounts,
    selectedSub2APIServerId,
    selectedSub2APIAccountIds,
    sub2apiImportJob,
    proxyProfiles,
    proxyProfilesLoading,
    proxyTesting,
    proxyMode,
    accountProxyModeOptions,
    proxyProfileOptions,
    selectedProxyProfileId,
    customProxyInput,
    accountProxyPreview,
    showRefreshProgress,
    refreshProgressTitle,
    refreshProgress,
    refreshProgressPercent,
    cpaPoolOptions,
    sub2apiServerOptions,
    oauthStarting,
    oauthSubmitting,
    oauthEmailHint,
    oauthCallback,
    oauthSession,
    accountStatusOptions,
    form,
    filteredAccounts,
    pagedAccounts,
    setViewMode,
    isSelected,
    toggleSelect,
    clearSelection,
    toggleSelectAllVisible,
    setImportMode,
    openImportModal,
    closeImportModal,
    loadProxyProfiles,
    testAccountProxy,
    setProxyMode,
    selectProxyProfile,
    setCustomProxyInput,
    importManualTokenText,
    importTokenTextFile,
    importSessionJson,
    importCodexJson,
    importLocalCPAFiles,
    loadCPAPools,
    loadCPAFiles,
    toggleCPAFile,
    startRemoteCPAImport,
    loadSub2APIServers,
    loadSub2APIAccounts,
    toggleSub2APIAccount,
    startSub2APIImport,
    refreshAllAccounts,
    refreshSelectedAccounts,
    reLoginAbnormalAccounts,
    reLoginAccount,
    closeRefreshProgress,
    loadData,
    openCreateModal,
    openEditModal,
    closeModal,
    openOAuthModal,
    closeOAuthModal,
    startOAuthLogin,
    finishOAuthLogin,
    copyOAuthUrl,
    reopenOAuthUrl,
    saveAccount,
    toggleEnabled,
    refreshToken,
    resetAccountState,
    removeAccount,
    runBulkAction,
    exportAccounts,
    importAccounts,
  }
}

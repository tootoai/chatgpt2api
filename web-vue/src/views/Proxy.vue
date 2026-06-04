<template>
  <div class="space-y-6">
    <section class="ui-panel space-y-5">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="ui-section-title">代理管理</p>
          <p class="mt-1 text-xs text-muted-foreground">
            优先级：账号代理 > 代理分组 > 全局代理。账号填 <code>direct</code> 表示强制直连。
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" :disabled="loading" @click="loadData">
            {{ loading ? '刷新中...' : '刷新' }}
          </Button>
          <Button size="sm" variant="primary" :disabled="savingGlobal || loading" @click="saveGlobalProxy">
            {{ savingGlobal ? '保存中...' : '保存全局代理' }}
          </Button>
        </div>
      </div>

      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div class="rounded-xl border border-border bg-card p-4">
          <label class="block text-xs">
            <span class="ui-field-label">全局代理 URL</span>
            <Input
              v-model.trim="globalProxy"
              block
              root-class="font-mono"
              placeholder="http://127.0.0.1:7890 或 socks5://127.0.0.1:7890"
            />
          </label>
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <Button size="xs" variant="outline" :disabled="testingKey === GLOBAL_TEST_KEY || !globalProxy" @click="testGlobalProxy">
              {{ testingKey === GLOBAL_TEST_KEY ? '测试中...' : '测试全局代理' }}
            </Button>
            <Button size="xs" variant="outline" :disabled="savingGlobal || testingKey === GLOBAL_TEST_KEY" @click="clearGlobalProxy">
              清空
            </Button>
          </div>
        </div>

        <div class="rounded-xl border border-border bg-background p-4">
          <p class="text-xs text-muted-foreground">全局测试结果</p>
          <div v-if="globalTestResult" class="mt-3 space-y-1 text-xs">
            <p :class="globalTestResult.ok ? 'text-emerald-600' : 'text-rose-600'">
              {{ globalTestResult.ok ? '可用' : '不可用' }}
            </p>
            <p class="text-muted-foreground">HTTP {{ globalTestResult.status || '-' }} · {{ globalTestResult.latency_ms || 0 }}ms</p>
            <p v-if="globalTestResult.error" class="break-all text-rose-600">{{ globalTestResult.error }}</p>
          </div>
          <p v-else class="mt-3 text-xs text-muted-foreground">尚未测试</p>
        </div>
      </div>

      <div class="grid gap-3 md:grid-cols-3">
        <div class="ui-card-sm">
          <p class="text-xs text-muted-foreground">代理分组</p>
          <p class="mt-1 text-2xl font-semibold text-foreground">{{ profiles.length }}</p>
        </div>
        <div class="ui-card-sm">
          <p class="text-xs text-muted-foreground">启用分组</p>
          <p class="mt-1 text-2xl font-semibold text-foreground">{{ enabledProfilesCount }}</p>
        </div>
        <div class="ui-card-sm">
          <p class="text-xs text-muted-foreground">测试目标</p>
          <p class="mt-2 break-all font-mono text-xs text-foreground">https://chatgpt.com/api/auth/csrf</p>
        </div>
      </div>
    </section>

    <section class="ui-panel space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <Input
          :model-value="keyword"
          block
          root-class="min-w-[12rem] flex-1 md:w-96 md:flex-none"
          placeholder="搜索分组 ID / 名称 / 代理 / 备注"
          @update:model-value="keyword = $event.trim()"
        />
        <Button size="sm" variant="primary" @click="openCreateModal">新建代理分组</Button>
      </div>

      <div v-if="loading && profiles.length === 0" class="rounded-xl border border-border bg-card px-4 py-8 text-center text-sm text-muted-foreground">
        加载中...
      </div>

      <div v-else-if="filteredProfiles.length === 0" class="rounded-xl border border-border bg-card px-4 py-8">
        <EmptyState plain title="暂无代理分组" description="新建一个分组后，可以在账号代理里填 profile:分组ID 使用。" />
      </div>

      <div v-else class="scrollbar-slim overflow-x-auto">
        <table class="min-w-[920px] w-full table-fixed text-left text-sm">
          <colgroup>
            <col class="w-[18%]" />
            <col class="w-[8rem]" />
            <col class="w-[28%]" />
            <col class="w-[14%]" />
            <col class="w-[18%]" />
            <col class="w-[11rem]" />
          </colgroup>
          <thead class="text-xs uppercase tracking-[0.16em] text-muted-foreground">
            <tr>
              <th class="py-3 pr-4">分组</th>
              <th class="py-3 pr-4">状态</th>
              <th class="py-3 pr-4">代理地址</th>
              <th class="py-3 pr-4">账号引用</th>
              <th class="py-3 pr-4">测试结果</th>
              <th class="py-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody class="text-sm text-foreground">
            <tr
              v-for="profile in pagedProfiles"
              :key="profile.id"
              class="border-t border-border transition-colors hover:bg-muted/20"
              :class="profile.enabled ? '' : 'bg-muted/30'"
            >
              <td class="py-3 pr-4 align-top">
                <p class="truncate font-medium">{{ profile.name || profile.id }}</p>
                <p class="mt-1 truncate font-mono text-xs text-muted-foreground">{{ profile.id }}</p>
                <p v-if="profile.notes" class="mt-1 truncate text-xs text-muted-foreground" :title="profile.notes">{{ profile.notes }}</p>
              </td>
              <td class="py-3 pr-4 align-top">
                <span
                  class="inline-flex h-6 min-w-12 items-center justify-center rounded-full border px-2 text-xs"
                  :class="profile.enabled ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-600' : 'border-border bg-muted text-muted-foreground'"
                >
                  {{ profile.enabled ? '启用' : '停用' }}
                </span>
              </td>
              <td class="py-3 pr-4 align-top">
                <p class="break-all font-mono text-xs text-muted-foreground" :title="profile.proxy">
                  {{ maskProxy(profile.proxy) || '未设置' }}
                </p>
                <p v-if="profile.no_proxy" class="mt-1 truncate text-xs text-muted-foreground" :title="profile.no_proxy">
                  NO_PROXY {{ profile.no_proxy }}
                </p>
              </td>
              <td class="py-3 pr-4 align-top">
                <button
                  type="button"
                  class="font-mono text-xs text-primary hover:underline"
                  @click="copyReference(profile.id)"
                >
                  profile:{{ profile.id }}
                </button>
              </td>
              <td class="py-3 pr-4 align-top">
                <p class="truncate text-xs" :class="testResultClass(profile.id)">
                  {{ profileTestSummary(profile.id) }}
                </p>
              </td>
              <td class="py-3 text-right align-top">
                <div class="inline-flex flex-wrap justify-end gap-1.5">
                  <Button size="xs" variant="outline" root-class="w-14 justify-center" :disabled="testingKey === profile.id || !profile.proxy" @click="testProfile(profile)">
                    {{ testingKey === profile.id ? '中...' : '测试' }}
                  </Button>
                  <Button size="xs" variant="outline" root-class="w-14 justify-center" @click="openEditModal(profile)">
                    编辑
                  </Button>
                  <Button size="xs" variant="outline" root-class="w-14 justify-center" :disabled="savingProfileId === profile.id" @click="toggleProfile(profile)">
                    {{ profile.enabled ? '停用' : '启用' }}
                  </Button>
                  <Button size="xs" variant="outline" root-class="w-14 justify-center text-rose-600" :disabled="deletingProfileId === profile.id" @click="deleteProfile(profile)">
                    删除
                  </Button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <ListPagination
        v-model:page="currentPage"
        v-model:page-size="pageSize"
        :total-count="filteredProfiles.length"
        :page-size-options="pageSizeOptions"
        unit="个分组"
        :disabled="loading"
      />
    </section>

    <Teleport to="body">
      <div v-if="showModal" class="fixed inset-0 z-[125] overflow-y-auto bg-black/40 px-3 py-4">
        <div class="flex min-h-full items-center justify-center">
          <div class="ui-surface w-full max-w-[40rem] overflow-hidden shadow-lg">
            <div class="flex items-center justify-between border-b border-border px-5 py-3">
              <h4 class="ui-section-title">{{ editingId ? '编辑代理分组' : '新建代理分组' }}</h4>
              <Button size="xs" variant="outline" root-class="min-w-14 justify-center text-muted-foreground" :disabled="savingProfileId === FORM_TEST_KEY" @click="closeModal">
                关闭
              </Button>
            </div>

            <div class="space-y-3 px-4 py-4">
              <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2">
                <label class="text-xs">
                  <span class="ui-field-label">分组 ID</span>
                  <Input
                    :model-value="form.id"
                    :disabled="Boolean(editingId)"
                    block
                    placeholder="hk-1 / us-west"
                    @update:model-value="form.id = normalizeProfileId($event)"
                  />
                </label>
                <label class="text-xs">
                  <span class="ui-field-label">显示名称</span>
                  <Input
                    :model-value="form.name"
                    block
                    placeholder="香港代理池"
                    @update:model-value="form.name = $event.trim()"
                  />
                </label>
              </div>

              <label class="block text-xs">
                <span class="ui-field-label">代理地址</span>
                <Input
                  :model-value="form.proxy"
                  block
                  root-class="font-mono"
                  placeholder="http://user:password@host:port"
                  @update:model-value="form.proxy = $event.trim()"
                />
              </label>

              <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2">
                <label class="text-xs">
                  <span class="ui-field-label">NO_PROXY（记录用）</span>
                  <Input
                    :model-value="form.no_proxy"
                    block
                    placeholder="localhost,127.0.0.1"
                    @update:model-value="form.no_proxy = $event.trim()"
                  />
                </label>
                <label class="text-xs">
                  <span class="ui-field-label">备注</span>
                  <Input
                    :model-value="form.notes"
                    block
                    placeholder="可选"
                    @update:model-value="form.notes = $event.trim()"
                  />
                </label>
              </div>

              <div class="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-card p-3">
                <Checkbox v-model="form.enabled">启用分组</Checkbox>
                <div class="flex flex-wrap items-center gap-2">
                  <Button size="xs" variant="outline" :disabled="testingKey === FORM_TEST_KEY || !form.proxy" @click="testFormProxy">
                    {{ testingKey === FORM_TEST_KEY ? '检测中...' : '检测当前代理' }}
                  </Button>
                  <p v-if="testResults[FORM_TEST_KEY]" class="text-xs" :class="testResultClass(FORM_TEST_KEY)">
                    {{ profileTestSummary(FORM_TEST_KEY) }}
                  </p>
                </div>
              </div>
            </div>

            <div class="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
              <Button size="xs" variant="outline" root-class="min-w-14 justify-center" :disabled="savingProfileId === FORM_TEST_KEY" @click="closeModal">
                取消
              </Button>
              <Button size="xs" variant="primary" root-class="min-w-14 justify-center" :disabled="savingProfileId === FORM_TEST_KEY" @click="saveProfile">
                {{ savingProfileId === FORM_TEST_KEY ? '保存中...' : editingId ? '更新' : '保存' }}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Button, Checkbox, EmptyState, Input } from 'nanocat-ui'
import { proxyApi, settingsApi } from '@/api'
import type { ProxyProfile, ProxyTestResult } from '@/api/proxy'
import ListPagination from '@/components/ai/ListPagination.vue'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useSettingsStore } from '@/stores/settings'
import { useToast } from '@/composables/useToast'
import type { Settings } from '@/types/api'

type ProfileForm = {
  id: string
  name: string
  proxy: string
  no_proxy: string
  enabled: boolean
  notes: string
}

const GLOBAL_TEST_KEY = '__global__'
const FORM_TEST_KEY = '__form__'
const pageSizeOptions = [20, 50, 100]

const settingsStore = useSettingsStore()
const toast = useToast()
const confirmDialog = useConfirmDialog()

const loading = ref(false)
const savingGlobal = ref(false)
const savingProfileId = ref('')
const deletingProfileId = ref('')
const testingKey = ref('')
const keyword = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const showModal = ref(false)
const editingId = ref('')
const globalProxy = ref('')
const currentSettings = ref<Settings | null>(null)
const globalTestResult = ref<ProxyTestResult | null>(null)
const profiles = ref<ProxyProfile[]>([])
const testResults = reactive<Record<string, ProxyTestResult>>({})
const form = reactive<ProfileForm>(createDefaultForm())

const enabledProfilesCount = computed(() => profiles.value.filter((item) => item.enabled).length)

const filteredProfiles = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  const rows = [...profiles.value].sort((left, right) => (
    (left.name || left.id).localeCompare(right.name || right.id, 'zh-Hans-CN')
  ))
  if (!query) return rows
  return rows.filter((item) => [
    item.id,
    item.name,
    item.proxy,
    item.no_proxy,
    item.notes,
  ].some((value) => String(value || '').toLowerCase().includes(query)))
})

const pageCount = computed(() => Math.max(1, Math.ceil(filteredProfiles.value.length / pageSize.value)))

const pagedProfiles = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredProfiles.value.slice(start, start + pageSize.value)
})

function createDefaultForm(): ProfileForm {
  return {
    id: '',
    name: '',
    proxy: '',
    no_proxy: '',
    enabled: true,
    notes: '',
  }
}

function cloneSettings(settings: Settings): Settings {
  return JSON.parse(JSON.stringify(settings)) as Settings
}

function normalizeProfileId(value: string) {
  return value
    .trim()
    .replace(/[^A-Za-z0-9._-]+/g, '-')
    .replace(/^[-._]+|[-._]+$/g, '')
    .slice(0, 64)
}

function normalizeProfile(item: ProxyProfile): ProxyProfile {
  return {
    id: normalizeProfileId(item.id || item.name || ''),
    name: String(item.name || item.id || '').trim(),
    proxy: String(item.proxy || '').trim(),
    no_proxy: String(item.no_proxy || '').trim(),
    enabled: item.enabled !== false,
    notes: String(item.notes || '').trim(),
  }
}

function updateProfiles(items: ProxyProfile[]) {
  profiles.value = Array.isArray(items) ? items.map(normalizeProfile).filter((item) => item.id) : []
}

async function loadData() {
  loading.value = true
  try {
    const [settings, profileResponse] = await Promise.all([
      settingsApi.get(),
      proxyApi.listProfiles(),
    ])
    currentSettings.value = cloneSettings(settings)
    settingsStore.$patch({ settings })
    globalProxy.value = String(settings.basic?.proxy || settings.proxy || '').trim()
    globalTestResult.value = null
    updateProfiles(profileResponse.profiles || [])
  } catch (error: any) {
    toast.error(error.message || '加载代理配置失败')
  } finally {
    loading.value = false
  }
}

async function saveGlobalProxy() {
  if (!currentSettings.value) {
    toast.warning('配置尚未加载完成')
    return
  }
  const confirmed = await confirmDialog.ask({
    title: '确认保存全局代理',
    message: '即将保存全局代理配置。未单独指定代理的账号后续请求会受到影响，是否继续？',
    confirmText: '保存',
    cancelText: '取消',
  })
  if (!confirmed) return

  savingGlobal.value = true
  try {
    const next = cloneSettings(currentSettings.value)
    next.proxy = globalProxy.value.trim()
    next.basic = next.basic || {}
    next.basic.proxy = next.proxy
    const response = await settingsStore.updateSettings(next)
    currentSettings.value = cloneSettings(response.config || next)
    toast.success('全局代理已保存')
  } catch (error: any) {
    toast.error(error.message || '保存全局代理失败')
  } finally {
    savingGlobal.value = false
  }
}

function clearGlobalProxy() {
  globalProxy.value = ''
  globalTestResult.value = null
}

async function testGlobalProxy() {
  const url = globalProxy.value.trim()
  if (!url) {
    toast.warning('请先填写全局代理 URL')
    return
  }
  const confirmed = await confirmDialog.ask({
    title: '确认测试全局代理',
    message: '即将使用全局代理地址发起外部网络测试请求。请确认当前允许测试该代理连接。',
    confirmText: '开始测试',
    cancelText: '取消',
  })
  if (!confirmed) return

  testingKey.value = GLOBAL_TEST_KEY
  try {
    const response = await proxyApi.test(url)
    globalTestResult.value = response.result
    if (response.result.ok) toast.success(`全局代理可用，耗时 ${response.result.latency_ms}ms`)
    else toast.warning(response.result.error || '全局代理测试失败')
  } catch (error: any) {
    globalTestResult.value = {
      ok: false,
      status: 0,
      latency_ms: 0,
      error: error.message || '全局代理测试失败',
    }
    toast.error(error.message || '全局代理测试失败')
  } finally {
    testingKey.value = ''
  }
}

function resetForm() {
  editingId.value = ''
  Object.assign(form, createDefaultForm())
  delete testResults[FORM_TEST_KEY]
}

function openCreateModal() {
  resetForm()
  showModal.value = true
}

function openEditModal(profile: ProxyProfile) {
  editingId.value = profile.id
  Object.assign(form, {
    id: profile.id,
    name: profile.name || profile.id,
    proxy: profile.proxy || '',
    no_proxy: profile.no_proxy || '',
    enabled: profile.enabled !== false,
    notes: profile.notes || '',
  })
  delete testResults[FORM_TEST_KEY]
  showModal.value = true
}

function closeModal() {
  if (savingProfileId.value === FORM_TEST_KEY) return
  showModal.value = false
  resetForm()
}

async function saveProfile() {
  const id = normalizeProfileId(form.id || form.name)
  if (!id) {
    toast.warning('请填写分组 ID 或显示名称')
    return
  }
  if (!form.proxy.trim()) {
    toast.warning('请填写代理地址')
    return
  }

  savingProfileId.value = FORM_TEST_KEY
  try {
    const response = await proxyApi.saveProfile({
      id,
      name: form.name.trim() || id,
      proxy: form.proxy.trim(),
      no_proxy: form.no_proxy.trim(),
      enabled: form.enabled,
      notes: form.notes.trim(),
      create_only: !editingId.value,
    })
    updateProfiles(response.profiles || [])
    closeModal()
    toast.success(editingId.value ? '代理分组已更新' : '代理分组已创建')
  } catch (error: any) {
    toast.error(error.message || '保存代理分组失败')
  } finally {
    savingProfileId.value = ''
  }
}

async function toggleProfile(profile: ProxyProfile) {
  const nextEnabled = !profile.enabled
  const confirmed = await confirmDialog.ask({
    title: nextEnabled ? '确认启用代理分组' : '确认停用代理分组',
    message: `即将${nextEnabled ? '启用' : '停用'}代理分组 ${profile.name || profile.id}。使用 profile:${profile.id} 的账号路由会受到影响，是否继续？`,
    confirmText: nextEnabled ? '启用' : '停用',
    cancelText: '取消',
  })
  if (!confirmed) return

  savingProfileId.value = profile.id
  try {
    const response = await proxyApi.saveProfile({
      ...profile,
      enabled: nextEnabled,
    })
    updateProfiles(response.profiles || [])
    toast.success(`代理分组 ${profile.name || profile.id} 已${profile.enabled ? '停用' : '启用'}`)
  } catch (error: any) {
    toast.error(error.message || '切换代理分组失败')
  } finally {
    savingProfileId.value = ''
  }
}

async function deleteProfile(profile: ProxyProfile) {
  const confirmed = await confirmDialog.ask({
    title: '删除代理分组',
    message: `确认删除代理分组 ${profile.name || profile.id}？账号中已有的 profile:${profile.id} 引用不会自动清空。`,
    confirmText: '确认删除',
    cancelText: '取消',
  })
  if (!confirmed) return

  deletingProfileId.value = profile.id
  try {
    const response = await proxyApi.deleteProfile(profile.id)
    updateProfiles(response.profiles || [])
    delete testResults[profile.id]
    toast.success('代理分组已删除')
  } catch (error: any) {
    toast.error(error.message || '删除代理分组失败')
  } finally {
    deletingProfileId.value = ''
  }
}

async function testProfile(profile: ProxyProfile) {
  await runProxyTest(profile.id, profile.proxy)
}

async function testFormProxy() {
  await runProxyTest(FORM_TEST_KEY, form.proxy)
}

async function runProxyTest(key: string, proxyUrl: string) {
  const url = proxyUrl.trim()
  if (!url) {
    toast.warning('请先填写代理地址')
    return
  }
  const confirmed = await confirmDialog.ask({
    title: '确认测试代理',
    message: '即将使用当前代理地址发起外部网络测试请求。请确认当前允许测试该代理连接。',
    confirmText: '开始测试',
    cancelText: '取消',
  })
  if (!confirmed) return

  testingKey.value = key
  try {
    const response = await proxyApi.testProfile({ url })
    testResults[key] = response.result
    if (response.result.ok) toast.success(`代理检测通过，耗时 ${response.result.latency_ms}ms`)
    else toast.warning(response.result.error || '代理检测失败')
  } catch (error: any) {
    testResults[key] = {
      ok: false,
      status: 0,
      latency_ms: 0,
      error: error.message || '代理检测失败',
    }
    toast.error(error.message || '代理检测失败')
  } finally {
    testingKey.value = ''
  }
}

function profileTestSummary(key: string) {
  const result = testResults[key]
  if (!result) return '尚未测试'
  if (result.ok) return `HTTP ${result.status || '-'} · ${result.latency_ms || 0}ms`
  return result.error || '检测失败'
}

function testResultClass(key: string) {
  const result = testResults[key]
  if (!result) return 'text-muted-foreground'
  return result.ok ? 'text-emerald-600' : 'text-rose-600'
}

function maskProxy(value: unknown) {
  const raw = String(value || '').trim()
  if (!raw) return ''
  return raw.replace(/:\/\/([^/@:]+):([^/@]+)@/, (_match, user) => `://${user}:***@`)
}

async function copyReference(id: string) {
  try {
    await navigator.clipboard.writeText(`profile:${id}`)
    toast.success('代理引用已复制')
  } catch {
    toast.warning('复制失败，请手动复制')
  }
}

watch(keyword, () => {
  currentPage.value = 1
})

watch(pageSize, () => {
  currentPage.value = 1
})

watch(pageCount, (count) => {
  if (currentPage.value > count) currentPage.value = count
  if (currentPage.value < 1) currentPage.value = 1
})

onMounted(() => {
  void loadData()
})
</script>

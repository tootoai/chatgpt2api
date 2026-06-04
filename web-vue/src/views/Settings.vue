<template>
  <div class="space-y-6">
    <section class="ui-panel space-y-5">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="ui-section-title">系统设置</p>
          <p class="mt-1 text-xs text-muted-foreground">
            这里展示 chatgpt2api 真实配置。代理分组请到代理管理页维护，账号可以填 <code>profile:分组ID</code> 或 <code>direct</code>。
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" :disabled="settingsStore.isLoading || isSaving" @click="reloadSettings">
            {{ settingsStore.isLoading ? '刷新中...' : '刷新' }}
          </Button>
          <Button size="sm" variant="primary" :disabled="isSaving || !localSettings" @click="handleSave">
            {{ isSaving ? '保存中...' : '保存设置' }}
          </Button>
        </div>
      </div>

      <div v-if="localSettings" class="grid gap-3 md:grid-cols-3">
        <div class="ui-card-sm">
          <p class="text-xs text-muted-foreground">图片轮询超时</p>
          <p class="mt-1 text-2xl font-semibold text-foreground">{{ localSettings.image_poll_timeout_secs || 0 }}s</p>
        </div>
        <div class="ui-card-sm">
          <p class="text-xs text-muted-foreground">图片账号并发</p>
          <p class="mt-1 text-2xl font-semibold text-foreground">{{ localSettings.image_account_concurrency || 1 }}</p>
        </div>
        <div class="ui-card-sm">
          <p class="text-xs text-muted-foreground">代理分组</p>
          <p class="mt-1 text-2xl font-semibold text-foreground">{{ localSettings.proxy_profiles?.length || 0 }}</p>
        </div>
      </div>
    </section>

    <div v-if="localSettings" class="grid gap-4 xl:grid-cols-3">
      <div class="space-y-4">
        <FormSection title="基础连接">
          <FormField label="上游 Base URL">
            <Input
              v-model.trim="localSettings.base_url"
              block
              placeholder="留空使用默认 ChatGPT 上游"
            />
          </FormField>

          <FormField label="全局代理">
            <template #label-extra>
              <HelpTip text="留空表示直连。账号代理优先于全局代理；账号填 direct 会强制直连。" />
            </template>
            <Input
              v-model.trim="localSettings.proxy"
              block
              root-class="font-mono"
              placeholder="http://127.0.0.1:7890"
            />
          </FormField>

          <FormField label="图片保留天数">
            <Input
              :model-value="imageRetentionDaysField.input.value"
              type="number"
              block
              @update:model-value="imageRetentionDaysField.update"
            />
          </FormField>

          <div class="rounded-xl border border-border bg-card px-3 py-2 text-xs text-muted-foreground">
            全局代理保存后会同步写入旧版 <code>basic.proxy</code>，避免老代码读不到。
          </div>
        </FormSection>

        <FormSection title="图片链路">
          <FormField label="轮询总超时（秒）">
            <Input
              :model-value="imagePollTimeoutField.input.value"
              type="number"
              block
              @update:model-value="imagePollTimeoutField.update"
            />
          </FormField>

          <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <FormField label="轮询间隔（秒）">
              <Input
                :model-value="imagePollIntervalField.input.value"
                type="number"
                block
                @update:model-value="imagePollIntervalField.update"
              />
            </FormField>

            <FormField label="初始等待（秒）">
              <Input
                :model-value="imagePollInitialWaitField.input.value"
                type="number"
                block
                @update:model-value="imagePollInitialWaitField.update"
              />
            </FormField>
          </div>

          <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <FormField label="命中后沉淀（秒）">
              <Input
                :model-value="imageSettleSecsField.input.value"
                type="number"
                block
                @update:model-value="imageSettleSecsField.update"
              />
            </FormField>

            <FormField label="超时补轮询（秒）">
              <Input
                :model-value="imageTimeoutRetrySecsField.input.value"
                type="number"
                block
                @update:model-value="imageTimeoutRetrySecsField.update"
              />
            </FormField>
          </div>

          <div class="space-y-2">
            <Checkbox v-model="localSettings.image_settle_enabled">命中 file id 后等待沉淀</Checkbox>
            <Checkbox v-model="localSettings.image_check_before_hit_enabled">命中前检查已有图片资产</Checkbox>
            <Checkbox v-model="localSettings.image_parallel_generation">允许图片并行生成</Checkbox>
          </div>
        </FormSection>
      </div>

      <div class="space-y-4">
        <FormSection title="账号和并发">
          <FormField label="每账号图片并发">
            <Input
              :model-value="imageAccountConcurrencyField.input.value"
              type="number"
              block
              @update:model-value="imageAccountConcurrencyField.update"
            />
          </FormField>

          <div class="space-y-2">
            <Checkbox v-model="localSettings.auto_remove_invalid_accounts">自动移除异常账号</Checkbox>
            <Checkbox v-model="localSettings.auto_remove_rate_limited_accounts">自动移除限流账号</Checkbox>
            <Checkbox v-model="localSettings.auto_relogin_after_refresh">刷新后自动重登</Checkbox>
          </div>
        </FormSection>

        <FormSection title="缓存">
          <Checkbox v-model="localSettings.chat_completion_cache.enabled">启用聊天补全缓存</Checkbox>

          <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <FormField label="TTL（秒）">
              <Input
                :model-value="cacheTtlField.input.value"
                type="number"
                block
                @update:model-value="cacheTtlField.update"
              />
            </FormField>

            <FormField label="最大条目">
              <Input
                :model-value="cacheMaxEntriesField.input.value"
                type="number"
                block
                @update:model-value="cacheMaxEntriesField.update"
              />
            </FormField>
          </div>

          <div class="space-y-2">
            <Checkbox v-model="localSettings.chat_completion_cache.dedupe_inflight">合并进行中的相同请求</Checkbox>
            <Checkbox v-model="localSettings.chat_completion_cache.stream_cache">缓存流式响应</Checkbox>
            <Checkbox v-model="localSettings.chat_completion_cache.normalize_messages">标准化消息后计算缓存键</Checkbox>
            <Checkbox v-model="localSettings.chat_completion_cache.drop_adjacent_duplicates">去掉相邻重复消息</Checkbox>
            <Checkbox v-model="localSettings.chat_completion_cache.drop_assistant_history">缓存键忽略 assistant 历史</Checkbox>
          </div>
        </FormSection>

        <FormSection title="提示词和审核">
          <FormField label="全局系统提示词">
            <textarea
              v-model="localSettings.global_system_prompt"
              rows="5"
              class="ui-textarea-sm"
              placeholder="可选，会写入后端 global_system_prompt"
            ></textarea>
          </FormField>

          <FormField label="敏感词">
            <textarea
              v-model="sensitiveWordsText"
              rows="5"
              class="ui-textarea-sm"
              placeholder="一行一个敏感词"
            ></textarea>
          </FormField>
        </FormSection>
      </div>

      <div class="space-y-4">
        <FormSection title="图片存储">
          <Checkbox v-model="localSettings.image_storage.enabled">启用远端图片存储</Checkbox>

          <FormField label="存储模式">
            <SelectMenu
              v-model="localSettings.image_storage.mode"
              :options="imageStorageModeOptions"
              aria-label="图片存储模式"
              class="w-full"
            />
          </FormField>

          <FormField label="WebDAV URL">
            <Input v-model.trim="localSettings.image_storage.webdav_url" block placeholder="https://example.com/dav" />
          </FormField>

          <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <FormField label="用户名">
              <Input v-model.trim="localSettings.image_storage.webdav_username" block />
            </FormField>

            <FormField label="密码">
              <Input v-model="localSettings.image_storage.webdav_password" type="password" block />
            </FormField>
          </div>

          <FormField label="根路径">
            <Input v-model.trim="localSettings.image_storage.webdav_root_path" block placeholder="chatgpt2api/images" />
          </FormField>

          <FormField label="公开访问前缀">
            <Input v-model.trim="localSettings.image_storage.public_base_url" block placeholder="https://cdn.example.com/images" />
          </FormField>

          <div class="flex flex-wrap items-center gap-2">
            <Button size="xs" variant="outline" :disabled="imageStorageBusy === 'test'" @click="testImageStorageConnection">
              {{ imageStorageBusy === 'test' ? '测试中...' : '测试 WebDAV' }}
            </Button>
            <Button size="xs" variant="outline" :disabled="imageStorageBusy === 'sync'" @click="syncImageStorageFiles">
              {{ imageStorageBusy === 'sync' ? '同步中...' : '同步本地图片' }}
            </Button>
          </div>

          <div v-if="imageStorageTestResult" class="rounded-xl border border-border bg-background px-3 py-2 text-xs">
            <p :class="imageStorageTestResult.ok ? 'text-emerald-600' : 'text-rose-600'">
              {{ imageStorageTestResult.ok ? 'WebDAV 可用' : 'WebDAV 不可用' }}
              <span v-if="imageStorageTestResult.status"> · HTTP {{ imageStorageTestResult.status }}</span>
            </p>
            <p v-if="imageStorageTestResult.error" class="mt-1 break-all text-rose-600">{{ imageStorageTestResult.error }}</p>
          </div>
        </FormSection>

        <FormSection title="备份">
          <Checkbox v-model="localSettings.backup.enabled">启用自动备份</Checkbox>

          <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <FormField label="Provider">
              <Input v-model.trim="localSettings.backup.provider" block placeholder="cloudflare_r2" />
            </FormField>

            <FormField label="Bucket">
              <Input v-model.trim="localSettings.backup.bucket" block />
            </FormField>
          </div>

          <FormField label="Account ID">
            <Input v-model.trim="localSettings.backup.account_id" block />
          </FormField>

          <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <FormField label="Access Key">
              <Input v-model.trim="localSettings.backup.access_key_id" block />
            </FormField>

            <FormField label="Secret Key">
              <Input v-model="localSettings.backup.secret_access_key" type="password" block />
            </FormField>
          </div>

          <div class="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <FormField label="备份前缀">
              <Input v-model.trim="localSettings.backup.prefix" block placeholder="backups" />
            </FormField>

            <FormField label="保留份数">
              <Input
                :model-value="backupRotationKeepField.input.value"
                type="number"
                block
                @update:model-value="backupRotationKeepField.update"
              />
            </FormField>
          </div>

          <FormField label="备份间隔（分钟）">
            <Input
              :model-value="backupIntervalMinutesField.input.value"
              type="number"
              block
              @update:model-value="backupIntervalMinutesField.update"
            />
          </FormField>

          <div class="space-y-2">
            <Checkbox v-model="localSettings.backup.encrypt">加密备份</Checkbox>
            <Checkbox v-model="localSettings.backup.include.config">包含配置</Checkbox>
            <Checkbox v-model="localSettings.backup.include.logs">包含日志</Checkbox>
            <Checkbox v-model="localSettings.backup.include.images">包含图片</Checkbox>
            <Checkbox v-model="localSettings.backup.include.accounts_snapshot">包含账号快照</Checkbox>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <Button size="xs" variant="outline" :disabled="backupBusy === 'test'" @click="testBackupConnection">
              {{ backupBusy === 'test' ? '测试中...' : '测试连接' }}
            </Button>
            <Button size="xs" variant="outline" :disabled="backupBusy === 'run' || backupState?.running" @click="runBackupNow">
              {{ backupBusy === 'run' || backupState?.running ? '备份中...' : '立即备份' }}
            </Button>
            <Button size="xs" variant="outline" :disabled="backupLoading" @click="loadBackups">
              {{ backupLoading ? '加载中...' : '刷新历史' }}
            </Button>
          </div>

          <div v-if="backupTestResult" class="rounded-xl border border-border bg-background px-3 py-2 text-xs">
            <p :class="backupTestResult.ok ? 'text-emerald-600' : 'text-rose-600'">
              {{ backupTestResult.ok ? '备份连接可用' : '备份连接不可用' }}
              <span v-if="backupTestResult.status"> · HTTP {{ backupTestResult.status }}</span>
            </p>
            <p v-if="backupTestResult.error" class="mt-1 break-all text-rose-600">{{ backupTestResult.error }}</p>
          </div>

          <div class="rounded-xl border border-border bg-background px-3 py-3 text-xs">
            <div class="grid grid-cols-2 gap-2 text-muted-foreground">
              <span>最近状态</span>
              <span class="text-right text-foreground">{{ backupStatusText }}</span>
              <span>最近对象</span>
              <span class="break-all text-right font-mono text-foreground">{{ backupState?.last_object_key || '-' }}</span>
              <span>最近错误</span>
              <span class="break-all text-right text-rose-600">{{ backupState?.last_error || '-' }}</span>
            </div>
          </div>

          <div v-if="backupItems.length > 0" class="space-y-2">
            <div
              v-for="item in backupItems.slice(0, 5)"
              :key="item.key"
              class="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-card px-3 py-2 text-xs"
            >
              <div class="min-w-0">
                <p class="truncate font-medium text-foreground">{{ item.name || item.key }}</p>
                <p class="mt-1 text-muted-foreground">{{ formatBytes(item.size_bytes ?? item.size ?? 0) }} · {{ item.last_modified || '-' }}</p>
              </div>
              <Button size="xs" variant="outline" root-class="text-rose-600" :disabled="backupBusy === item.key" @click="deleteBackupItem(item)">
                删除
              </Button>
            </div>
          </div>
        </FormSection>
      </div>
    </div>

    <section v-if="localSettings" class="ui-panel space-y-4">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="ui-section-title">外部账号源</p>
          <p class="mt-1 text-xs text-muted-foreground">
            这里配置远程 CPA 和 Sub2API，账号管理页的远程导入会读取这些连接。
          </p>
        </div>
        <Button size="sm" variant="outline" :disabled="externalSourcesLoading" @click="loadExternalSources">
          {{ externalSourcesLoading ? '刷新中...' : '刷新连接' }}
        </Button>
      </div>

      <div class="grid gap-4 xl:grid-cols-2">
        <div class="rounded-xl border border-border bg-card p-4">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-foreground">CPA 连接管理</p>
              <p class="mt-1 text-xs text-muted-foreground">保存 CLIProxyAPI 地址和管理密钥，供远程 CPA 导入使用。</p>
            </div>
            <span class="text-xs text-muted-foreground">{{ cpaPools.length }} 个连接</span>
          </div>

          <div class="mt-4 grid gap-2 md:grid-cols-2">
            <FormField label="名称">
              <Input v-model.trim="cpaForm.name" block placeholder="主 CPA" />
            </FormField>
            <FormField label="CPA 地址">
              <Input v-model.trim="cpaForm.base_url" block placeholder="http://your-cpa-host:8317" />
            </FormField>
          </div>
          <FormField label="管理密钥" class="mt-2">
            <Input v-model="cpaForm.secret_key" type="password" block :placeholder="editingCPAPoolId ? '留空则不修改密钥' : 'CPA 管理密钥'" />
          </FormField>
          <div class="mt-3 flex flex-wrap gap-2">
            <Button size="xs" variant="primary" :disabled="savingExternalSource === 'cpa'" @click="saveCPAPool">
              {{ savingExternalSource === 'cpa' ? '保存中...' : editingCPAPoolId ? '保存 CPA' : '新增 CPA' }}
            </Button>
            <Button size="xs" variant="outline" :disabled="savingExternalSource === 'cpa'" @click="resetCPAForm">清空</Button>
          </div>

          <div class="mt-4 space-y-2">
            <div
              v-for="pool in cpaPools"
              :key="pool.id"
              class="rounded-xl border border-border bg-background px-3 py-2 text-xs"
            >
              <div class="flex flex-wrap items-start justify-between gap-2">
                <div class="min-w-0">
                  <p class="truncate font-medium text-foreground">{{ pool.name || pool.id }}</p>
                  <p class="mt-1 truncate font-mono text-muted-foreground">{{ pool.base_url }}</p>
                </div>
                <div class="flex gap-1.5">
                  <Button size="xs" variant="outline" root-class="w-12 justify-center" @click="editCPAPool(pool)">编辑</Button>
                  <Button size="xs" variant="outline" root-class="w-12 justify-center text-rose-600" :disabled="savingExternalSource === pool.id" @click="deleteCPAPool(pool)">
                    删除
                  </Button>
                </div>
              </div>
            </div>
            <p v-if="!cpaLoading && cpaPools.length === 0" class="rounded-xl border border-dashed border-border px-3 py-6 text-center text-xs text-muted-foreground">
              暂无 CPA 连接。
            </p>
          </div>
        </div>

        <div class="rounded-xl border border-border bg-card p-4">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-foreground">Sub2API 连接管理</p>
              <p class="mt-1 text-xs text-muted-foreground">保存 Sub2API 服务器，用于读取 OpenAI OAuth 账号并导入本地号池。</p>
            </div>
            <span class="text-xs text-muted-foreground">{{ sub2apiServers.length }} 个连接</span>
          </div>

          <div class="mt-4 grid gap-2 md:grid-cols-2">
            <FormField label="名称">
              <Input v-model.trim="sub2apiForm.name" block placeholder="自建 Sub2API" />
            </FormField>
            <FormField label="Sub2API 地址">
              <Input v-model.trim="sub2apiForm.base_url" block placeholder="http://your-sub2api-host:8080" />
            </FormField>
            <FormField label="管理员邮箱">
              <Input v-model.trim="sub2apiForm.email" block placeholder="admin@example.com" />
            </FormField>
            <FormField label="密码">
              <Input v-model="sub2apiForm.password" type="password" block :placeholder="editingSub2APIId ? '留空则不修改密码' : '管理员密码'" />
            </FormField>
            <FormField label="Admin API Key">
              <Input v-model="sub2apiForm.api_key" type="password" block :placeholder="editingSub2APIId ? '留空则不修改密钥' : '可替代邮箱密码'" />
            </FormField>
            <FormField label="默认分组 ID">
              <Input v-model.trim="sub2apiForm.group_id" block placeholder="可选" />
            </FormField>
          </div>

          <div class="mt-3 flex flex-wrap gap-2">
            <Button size="xs" variant="primary" :disabled="savingExternalSource === 'sub2api'" @click="saveSub2APIServer">
              {{ savingExternalSource === 'sub2api' ? '保存中...' : editingSub2APIId ? '保存 Sub2API' : '新增 Sub2API' }}
            </Button>
            <Button size="xs" variant="outline" :disabled="savingExternalSource === 'sub2api'" @click="resetSub2APIForm">清空</Button>
          </div>

          <div class="mt-4 space-y-2">
            <div
              v-for="server in sub2apiServers"
              :key="server.id"
              class="rounded-xl border border-border bg-background px-3 py-2 text-xs"
            >
              <div class="flex flex-wrap items-start justify-between gap-2">
                <div class="min-w-0">
                  <p class="truncate font-medium text-foreground">{{ server.name || server.id }}</p>
                  <p class="mt-1 truncate font-mono text-muted-foreground">{{ server.base_url }}</p>
                  <p class="mt-1 text-muted-foreground">
                    {{ server.email || '未填邮箱' }} · {{ server.has_api_key ? '已配置 API Key' : '未配置 API Key' }}
                    <span v-if="server.group_id"> · 分组 {{ server.group_id }}</span>
                  </p>
                </div>
                <div class="flex flex-wrap justify-end gap-1.5">
                  <Button size="xs" variant="outline" root-class="w-16 justify-center" :disabled="sub2apiGroupsLoadingId === server.id" @click="loadSub2APIGroups(server)">
                    {{ sub2apiGroupsLoadingId === server.id ? '读取中' : '读分组' }}
                  </Button>
                  <Button size="xs" variant="outline" root-class="w-12 justify-center" @click="editSub2APIServer(server)">编辑</Button>
                  <Button size="xs" variant="outline" root-class="w-12 justify-center text-rose-600" :disabled="savingExternalSource === server.id" @click="deleteSub2APIServer(server)">
                    删除
                  </Button>
                </div>
              </div>

              <div v-if="sub2apiGroups[server.id]?.length" class="mt-2 flex flex-wrap gap-1.5">
                <button
                  v-for="group in sub2apiGroups[server.id]"
                  :key="group.id"
                  type="button"
                  class="rounded-md border border-border bg-card px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
                  @click="useSub2APIGroup(server, group.id)"
                >
                  {{ group.name || group.id }} · {{ group.active_account_count }}/{{ group.account_count }}
                </button>
              </div>
            </div>
            <p v-if="!sub2apiLoading && sub2apiServers.length === 0" class="rounded-xl border border-dashed border-border px-3 py-6 text-center text-xs text-muted-foreground">
              暂无 Sub2API 连接。
            </p>
          </div>
        </div>
      </div>
    </section>

    <section v-else class="ui-panel py-10 text-center text-sm text-muted-foreground">
      <template v-if="settingsStore.isLoading">
        设置加载中...
      </template>
      <template v-else>
        <p class="text-sm font-medium text-foreground">设置加载失败</p>
        <p class="mt-2 text-xs text-muted-foreground">
          {{ settingsLoadError || '未获取到系统配置，请重新加载。' }}
        </p>
        <Button size="sm" variant="outline" root-class="mt-4" @click="reloadSettings">
          重新加载
        </Button>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Button, Checkbox, FormField, FormSection, HelpTip, Input, SelectMenu } from 'nanocat-ui'
import { accountImportsApi, type CPAPool, type Sub2APIRemoteGroup, type Sub2APIServer } from '@/api/accountImports'
import { settingsApi, type BackupItem, type BackupState, type BackupTestResult, type ImageStorageTestResult } from '@/api/settings'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useSettingsStore } from '@/stores/settings'
import { useToast } from '@/composables/useToast'
import type { Settings } from '@/types/api'

type NumberFieldBinding = {
  input: ReturnType<typeof ref<string>>
  update: (value: string) => void
}

const settingsStore = useSettingsStore()
const { settings } = storeToRefs(settingsStore)
const toast = useToast()
const confirmDialog = useConfirmDialog()

const localSettings = ref<Settings | null>(null)
const isSaving = ref(false)
const settingsLoadError = ref('')
const imageStorageBusy = ref('')
const imageStorageTestResult = ref<ImageStorageTestResult | null>(null)
const backupBusy = ref('')
const backupLoading = ref(false)
const backupState = ref<BackupState | null>(null)
const backupItems = ref<BackupItem[]>([])
const backupTestResult = ref<BackupTestResult | null>(null)
const cpaLoading = ref(false)
const sub2apiLoading = ref(false)
const savingExternalSource = ref('')
const cpaPools = ref<CPAPool[]>([])
const sub2apiServers = ref<Sub2APIServer[]>([])
const sub2apiGroups = ref<Record<string, Sub2APIRemoteGroup[]>>({})
const sub2apiGroupsLoadingId = ref('')
const editingCPAPoolId = ref('')
const editingSub2APIId = ref('')
const cpaForm = ref({
  name: '',
  base_url: '',
  secret_key: '',
})
const sub2apiForm = ref({
  name: '',
  base_url: '',
  email: '',
  password: '',
  api_key: '',
  group_id: '',
})

const externalSourcesLoading = computed(() => cpaLoading.value || sub2apiLoading.value)

const backupStatusText = computed(() => {
  const state = backupState.value
  if (!state) return '未加载'
  if (state.running) return '备份中'
  if (state.last_status === 'success') return '最近成功'
  if (state.last_status === 'error') return '最近失败'
  return state.last_status || '未执行'
})

const imageStorageModeOptions = [
  { label: '仅本地', value: 'local' },
  { label: '仅 WebDAV', value: 'webdav' },
  { label: '本地 + WebDAV', value: 'both' },
]

const sensitiveWordsText = computed({
  get: () => (localSettings.value?.sensitive_words || []).join('\n'),
  set: (value: string) => {
    if (!localSettings.value) return
    localSettings.value.sensitive_words = value
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter(Boolean)
  },
})

const numberValue = (value: unknown, fallback: number, min: number, max?: number): number => {
  const parsed = Number(value)
  const finite = Number.isFinite(parsed) ? parsed : fallback
  const bounded = Math.max(min, finite)
  return typeof max === 'number' ? Math.min(max, bounded) : bounded
}

const intValue = (value: unknown, fallback: number, min: number, max?: number): number => (
  Math.round(numberValue(value, fallback, min, max))
)

const createNumberField = (
  getter: () => number,
  setter: (value: number) => void,
  options: { integer?: boolean; min?: number; max?: number; fallback?: number } = {},
): NumberFieldBinding => {
  const input = ref('')

  watch(getter, (value) => {
    const next = String(value)
    if (input.value !== next) {
      input.value = next
    }
  }, { immediate: true })

  const update = (value: string) => {
    input.value = value
    const parsed = Number(value)
    if (value.trim() === '' || !Number.isFinite(parsed)) return
    const min = options.min ?? 0
    const fallback = options.fallback ?? getter()
    const next = options.integer
      ? intValue(parsed, fallback, min, options.max)
      : numberValue(parsed, fallback, min, options.max)
    setter(next)
  }

  return { input, update }
}

const cloneSettings = (value: Settings): Settings => JSON.parse(JSON.stringify(value)) as Settings

const ensureSettingsShape = (value: Settings): Settings => {
  const next = cloneSettings(value)
  next.proxy = String(next.proxy || next.basic?.proxy || '').trim()
  next.base_url = String(next.base_url || next.basic?.base_url || '').trim()
  next.image_retention_days = intValue(next.image_retention_days ?? next.basic?.image_expire_hours, 15, 1)
  next.image_poll_timeout_secs = intValue(next.image_poll_timeout_secs, 120, 1)
  next.image_poll_interval_secs = numberValue(next.image_poll_interval_secs, 5, 0.5)
  next.image_poll_initial_wait_secs = numberValue(next.image_poll_initial_wait_secs, 5, 0)
  next.image_account_concurrency = intValue(next.image_account_concurrency, 1, 1)
  next.image_parallel_generation = next.image_parallel_generation !== false
  next.image_settle_enabled = next.image_settle_enabled === true
  next.image_check_before_hit_enabled = next.image_check_before_hit_enabled === true
  next.image_settle_secs = numberValue(next.image_settle_secs, 2, 0.5)
  next.image_timeout_retry_secs = numberValue(next.image_timeout_retry_secs, 30, 0)
  next.auto_remove_invalid_accounts = next.auto_remove_invalid_accounts !== false
  next.auto_remove_rate_limited_accounts = next.auto_remove_rate_limited_accounts === true
  next.auto_relogin_after_refresh = next.auto_relogin_after_refresh === true
  next.global_system_prompt = String(next.global_system_prompt || '')
  next.sensitive_words = Array.isArray(next.sensitive_words) ? next.sensitive_words : []

  next.basic = next.basic || {}
  next.basic.proxy = next.proxy
  next.basic.base_url = next.base_url
  next.basic.image_expire_hours = next.image_retention_days

  next.public_display = next.public_display || { logo_url: '', chat_url: '' }

  next.image_storage = {
    enabled: next.image_storage?.enabled === true,
    mode: ['webdav', 'both'].includes(String(next.image_storage?.mode || '')) ? next.image_storage!.mode : 'local',
    webdav_url: String(next.image_storage?.webdav_url || '').trim(),
    webdav_username: String(next.image_storage?.webdav_username || '').trim(),
    webdav_password: String(next.image_storage?.webdav_password || ''),
    webdav_root_path: String(next.image_storage?.webdav_root_path || 'chatgpt2api/images').trim(),
    public_base_url: String(next.image_storage?.public_base_url || '').trim(),
  }

  next.backup = {
    enabled: next.backup?.enabled === true,
    provider: String(next.backup?.provider || 'cloudflare_r2').trim(),
    account_id: String(next.backup?.account_id || '').trim(),
    access_key_id: String(next.backup?.access_key_id || '').trim(),
    secret_access_key: String(next.backup?.secret_access_key || ''),
    bucket: String(next.backup?.bucket || '').trim(),
    prefix: String(next.backup?.prefix || 'backups').trim(),
    interval_minutes: intValue(next.backup?.interval_minutes, 1440, 1),
    rotation_keep: intValue(next.backup?.rotation_keep, 10, 0),
    encrypt: next.backup?.encrypt === true,
    passphrase: String(next.backup?.passphrase || ''),
    include: {
      config: next.backup?.include?.config !== false,
      register: next.backup?.include?.register !== false,
      cpa: next.backup?.include?.cpa !== false,
      sub2api: next.backup?.include?.sub2api !== false,
      logs: next.backup?.include?.logs !== false,
      image_tasks: next.backup?.include?.image_tasks !== false,
      accounts_snapshot: next.backup?.include?.accounts_snapshot !== false,
      auth_keys_snapshot: next.backup?.include?.auth_keys_snapshot !== false,
      images: next.backup?.include?.images === true,
    },
  }

  next.chat_completion_cache = {
    enabled: next.chat_completion_cache?.enabled !== false,
    ttl_seconds: intValue(next.chat_completion_cache?.ttl_seconds, 60, 0),
    max_entries: intValue(next.chat_completion_cache?.max_entries, 256, 1),
    dedupe_inflight: next.chat_completion_cache?.dedupe_inflight !== false,
    stream_cache: next.chat_completion_cache?.stream_cache !== false,
    normalize_messages: next.chat_completion_cache?.normalize_messages !== false,
    drop_adjacent_duplicates: next.chat_completion_cache?.drop_adjacent_duplicates !== false,
    drop_assistant_history: next.chat_completion_cache?.drop_assistant_history === true,
  }

  return next
}

const settingsFingerprint = (value: Settings | null | undefined): string => (
  value ? JSON.stringify(ensureSettingsShape(value)) : ''
)

const hasUnsavedSettings = computed(() => {
  if (!localSettings.value || !settings.value) return false
  return settingsFingerprint(localSettings.value) !== settingsFingerprint(settings.value)
})

function requireSavedSettings(actionLabel: string) {
  if (!localSettings.value) return false
  if (hasUnsavedSettings.value) {
    toast.warning(`请先保存设置，再${actionLabel}`)
    return false
  }
  return true
}

const imageRetentionDaysField = createNumberField(
  () => localSettings.value?.image_retention_days ?? 15,
  (value) => {
    if (!localSettings.value) return
    localSettings.value.image_retention_days = value
    localSettings.value.basic.image_expire_hours = value
  },
  { integer: true, min: 1, fallback: 15 },
)
const imagePollTimeoutField = createNumberField(
  () => localSettings.value?.image_poll_timeout_secs ?? 120,
  (value) => { if (localSettings.value) localSettings.value.image_poll_timeout_secs = value },
  { integer: true, min: 1, fallback: 120 },
)
const imagePollIntervalField = createNumberField(
  () => localSettings.value?.image_poll_interval_secs ?? 5,
  (value) => { if (localSettings.value) localSettings.value.image_poll_interval_secs = value },
  { min: 0.5, fallback: 5 },
)
const imagePollInitialWaitField = createNumberField(
  () => localSettings.value?.image_poll_initial_wait_secs ?? 5,
  (value) => { if (localSettings.value) localSettings.value.image_poll_initial_wait_secs = value },
  { min: 0, fallback: 5 },
)
const imageSettleSecsField = createNumberField(
  () => localSettings.value?.image_settle_secs ?? 2,
  (value) => { if (localSettings.value) localSettings.value.image_settle_secs = value },
  { min: 0.5, fallback: 2 },
)
const imageTimeoutRetrySecsField = createNumberField(
  () => localSettings.value?.image_timeout_retry_secs ?? 30,
  (value) => { if (localSettings.value) localSettings.value.image_timeout_retry_secs = value },
  { integer: true, min: 0, fallback: 30 },
)
const imageAccountConcurrencyField = createNumberField(
  () => localSettings.value?.image_account_concurrency ?? 1,
  (value) => { if (localSettings.value) localSettings.value.image_account_concurrency = value },
  { integer: true, min: 1, fallback: 1 },
)
const cacheTtlField = createNumberField(
  () => localSettings.value?.chat_completion_cache?.ttl_seconds ?? 60,
  (value) => { if (localSettings.value) localSettings.value.chat_completion_cache.ttl_seconds = value },
  { integer: true, min: 0, fallback: 60 },
)
const cacheMaxEntriesField = createNumberField(
  () => localSettings.value?.chat_completion_cache?.max_entries ?? 256,
  (value) => { if (localSettings.value) localSettings.value.chat_completion_cache.max_entries = value },
  { integer: true, min: 1, fallback: 256 },
)
const backupIntervalMinutesField = createNumberField(
  () => localSettings.value?.backup?.interval_minutes ?? 1440,
  (value) => { if (localSettings.value) localSettings.value.backup.interval_minutes = value },
  { integer: true, min: 1, fallback: 1440 },
)
const backupRotationKeepField = createNumberField(
  () => localSettings.value?.backup?.rotation_keep ?? 10,
  (value) => { if (localSettings.value) localSettings.value.backup.rotation_keep = value },
  { integer: true, min: 0, fallback: 10 },
)

function formatBytes(value: unknown) {
  const bytes = Number(value) || 0
  if (bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }
  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}

async function persistSettings(showToast = false) {
  if (!localSettings.value) return null
  const payload = ensureSettingsShape(localSettings.value)
  payload.basic.proxy = payload.proxy
  payload.basic.base_url = payload.base_url
  payload.basic.image_expire_hours = payload.image_retention_days
  const result = await settingsStore.updateSettings(payload)
  if (result.config) {
    localSettings.value = ensureSettingsShape(result.config)
  }
  if (showToast) toast.success('设置保存成功')
  return result
}

async function testImageStorageConnection() {
  if (!requireSavedSettings('测试 WebDAV')) return
  const confirmed = await confirmDialog.ask({
    title: '确认测试 WebDAV',
    message: '即将使用已保存的图片存储配置发起 WebDAV/R2 连接测试，可能访问外部存储服务。是否继续？',
    confirmText: '开始测试',
    cancelText: '取消',
  })
  if (!confirmed) return

  imageStorageBusy.value = 'test'
  imageStorageTestResult.value = null
  try {
    const response = await settingsApi.testImageStorage()
    imageStorageTestResult.value = response.result
    if (response.result.ok) toast.success('WebDAV 测试通过')
    else toast.warning(response.result.error || 'WebDAV 测试失败')
  } catch (error: any) {
    imageStorageTestResult.value = { ok: false, error: error.message || 'WebDAV 测试失败' }
    toast.error(error.message || 'WebDAV 测试失败')
  } finally {
    imageStorageBusy.value = ''
  }
}

async function syncImageStorageFiles() {
  if (!requireSavedSettings('同步本地图片')) return
  const confirmed = await confirmDialog.ask({
    title: '确认同步图片存储',
    message: '即将扫描本地图片并同步到已配置的 WebDAV/R2 存储，可能产生外部上传流量。是否继续？',
    confirmText: '开始同步',
    cancelText: '取消',
  })
  if (!confirmed) return

  imageStorageBusy.value = 'sync'
  try {
    const response = await settingsApi.syncImageStorage()
    toast.success(`同步完成：上传 ${response.result.uploaded}，跳过 ${response.result.skipped}，失败 ${response.result.failed}`)
  } catch (error: any) {
    toast.error(error.message || '同步图片失败')
  } finally {
    imageStorageBusy.value = ''
  }
}

async function loadBackups() {
  backupLoading.value = true
  try {
    const response = await settingsApi.listBackups()
    backupItems.value = Array.isArray(response.items) ? response.items : []
    backupState.value = response.state || null
  } catch (error: any) {
    backupItems.value = []
    backupState.value = null
    toast.error(error.message || '加载备份历史失败')
  } finally {
    backupLoading.value = false
  }
}

async function testBackupConnection() {
  if (!requireSavedSettings('测试备份连接')) return
  const confirmed = await confirmDialog.ask({
    title: '确认测试备份连接',
    message: '即将使用已保存的备份配置发起 R2/备份存储连接测试，可能访问外部存储服务。是否继续？',
    confirmText: '开始测试',
    cancelText: '取消',
  })
  if (!confirmed) return

  backupBusy.value = 'test'
  backupTestResult.value = null
  try {
    const response = await settingsApi.testBackup()
    backupTestResult.value = response.result
    if (response.result.ok) toast.success('备份连接测试通过')
    else toast.warning(response.result.error || '备份连接测试失败')
  } catch (error: any) {
    backupTestResult.value = { ok: false, error: error.message || '备份连接测试失败' }
    toast.error(error.message || '备份连接测试失败')
  } finally {
    backupBusy.value = ''
  }
}

async function runBackupNow() {
  if (!requireSavedSettings('执行立即备份')) return
  const confirmed = await confirmDialog.ask({
    title: '确认立即备份',
    message: '即将把当前配置和运行数据写入备份存储，可能产生外部上传流量。是否继续？',
    confirmText: '开始备份',
    cancelText: '取消',
  })
  if (!confirmed) return

  backupBusy.value = 'run'
  try {
    const response = await settingsApi.runBackup()
    toast.success(`备份已完成：${response.result.key}`)
    await loadBackups()
  } catch (error: any) {
    toast.error(error.message || '执行备份失败')
  } finally {
    backupBusy.value = ''
  }
}

async function deleteBackupItem(item: BackupItem) {
  const confirmed = await confirmDialog.ask({
    title: '删除备份',
    message: `确定删除备份 ${item.name || item.key}？`,
    confirmText: '删除',
    cancelText: '取消',
  })
  if (!confirmed) return

  backupBusy.value = item.key
  try {
    await settingsApi.deleteBackup(item.key)
    toast.success('备份已删除')
    await loadBackups()
  } catch (error: any) {
    toast.error(error.message || '删除备份失败')
  } finally {
    backupBusy.value = ''
  }
}

function resetCPAForm() {
  editingCPAPoolId.value = ''
  cpaForm.value = {
    name: '',
    base_url: '',
    secret_key: '',
  }
}

function editCPAPool(pool: CPAPool) {
  editingCPAPoolId.value = pool.id
  cpaForm.value = {
    name: pool.name || '',
    base_url: pool.base_url || '',
    secret_key: '',
  }
}

async function loadCPAPools() {
  cpaLoading.value = true
  try {
    const response = await accountImportsApi.listCPAPools()
    cpaPools.value = Array.isArray(response.pools) ? response.pools : []
  } catch (error: any) {
    cpaPools.value = []
    toast.error(error.message || '加载 CPA 连接失败')
  } finally {
    cpaLoading.value = false
  }
}

async function saveCPAPool() {
  const payload = {
    name: cpaForm.value.name.trim(),
    base_url: cpaForm.value.base_url.trim(),
    secret_key: cpaForm.value.secret_key.trim(),
  }
  if (!payload.base_url) {
    toast.warning('请输入 CPA 地址')
    return
  }
  if (!editingCPAPoolId.value && !payload.secret_key) {
    toast.warning('新增 CPA 连接需要管理密钥')
    return
  }

  savingExternalSource.value = 'cpa'
  try {
    const response = editingCPAPoolId.value
      ? await accountImportsApi.updateCPAPool(editingCPAPoolId.value, {
          name: payload.name,
          base_url: payload.base_url,
          ...(payload.secret_key ? { secret_key: payload.secret_key } : {}),
        })
      : await accountImportsApi.createCPAPool(payload)
    cpaPools.value = response.pools || []
    resetCPAForm()
    toast.success('CPA 连接已保存')
  } catch (error: any) {
    toast.error(error.message || '保存 CPA 连接失败')
  } finally {
    savingExternalSource.value = ''
  }
}

async function deleteCPAPool(pool: CPAPool) {
  const confirmed = await confirmDialog.ask({
    title: '删除 CPA 连接',
    message: `确定删除 ${pool.name || pool.base_url}？账号页将不能再从这个 CPA 连接导入。`,
    confirmText: '删除',
    cancelText: '取消',
  })
  if (!confirmed) return

  savingExternalSource.value = pool.id
  try {
    const response = await accountImportsApi.deleteCPAPool(pool.id)
    cpaPools.value = response.pools || []
    if (editingCPAPoolId.value === pool.id) resetCPAForm()
    toast.success('CPA 连接已删除')
  } catch (error: any) {
    toast.error(error.message || '删除 CPA 连接失败')
  } finally {
    savingExternalSource.value = ''
  }
}

function resetSub2APIForm() {
  editingSub2APIId.value = ''
  sub2apiForm.value = {
    name: '',
    base_url: '',
    email: '',
    password: '',
    api_key: '',
    group_id: '',
  }
}

function editSub2APIServer(server: Sub2APIServer) {
  editingSub2APIId.value = server.id
  sub2apiForm.value = {
    name: server.name || '',
    base_url: server.base_url || '',
    email: server.email || '',
    password: '',
    api_key: '',
    group_id: server.group_id || '',
  }
}

async function loadSub2APIServers() {
  sub2apiLoading.value = true
  try {
    const response = await accountImportsApi.listSub2APIServers()
    sub2apiServers.value = Array.isArray(response.servers) ? response.servers : []
  } catch (error: any) {
    sub2apiServers.value = []
    toast.error(error.message || '加载 Sub2API 连接失败')
  } finally {
    sub2apiLoading.value = false
  }
}

async function saveSub2APIServer() {
  const payload = {
    name: sub2apiForm.value.name.trim(),
    base_url: sub2apiForm.value.base_url.trim(),
    email: sub2apiForm.value.email.trim(),
    password: sub2apiForm.value.password,
    api_key: sub2apiForm.value.api_key.trim(),
    group_id: sub2apiForm.value.group_id.trim(),
  }
  if (!payload.base_url) {
    toast.warning('请输入 Sub2API 地址')
    return
  }
  const hasLogin = Boolean(payload.email && payload.password)
  const hasApiKey = Boolean(payload.api_key)
  if (!editingSub2APIId.value && !hasLogin && !hasApiKey) {
    toast.warning('新增 Sub2API 连接需要邮箱密码或 Admin API Key')
    return
  }

  savingExternalSource.value = 'sub2api'
  try {
    const response = editingSub2APIId.value
      ? await accountImportsApi.updateSub2APIServer(editingSub2APIId.value, {
          name: payload.name,
          base_url: payload.base_url,
          email: payload.email,
          group_id: payload.group_id,
          ...(payload.password ? { password: payload.password } : {}),
          ...(payload.api_key ? { api_key: payload.api_key } : {}),
        })
      : await accountImportsApi.createSub2APIServer(payload)
    sub2apiServers.value = response.servers || []
    resetSub2APIForm()
    toast.success('Sub2API 连接已保存')
  } catch (error: any) {
    toast.error(error.message || '保存 Sub2API 连接失败')
  } finally {
    savingExternalSource.value = ''
  }
}

async function deleteSub2APIServer(server: Sub2APIServer) {
  const confirmed = await confirmDialog.ask({
    title: '删除 Sub2API 连接',
    message: `确定删除 ${server.name || server.base_url}？账号页将不能再从这个 Sub2API 连接导入。`,
    confirmText: '删除',
    cancelText: '取消',
  })
  if (!confirmed) return

  savingExternalSource.value = server.id
  try {
    const response = await accountImportsApi.deleteSub2APIServer(server.id)
    sub2apiServers.value = response.servers || []
    const nextGroups = { ...sub2apiGroups.value }
    delete nextGroups[server.id]
    sub2apiGroups.value = nextGroups
    if (editingSub2APIId.value === server.id) resetSub2APIForm()
    toast.success('Sub2API 连接已删除')
  } catch (error: any) {
    toast.error(error.message || '删除 Sub2API 连接失败')
  } finally {
    savingExternalSource.value = ''
  }
}

async function loadSub2APIGroups(server: Sub2APIServer) {
  const confirmed = await confirmDialog.ask({
    title: '加载 Sub2API 分组',
    message: `即将访问 Sub2API 连接 ${server.name || server.base_url || server.id} 并读取远程分组列表。请确认当前允许连接该外部服务。`,
    confirmText: '确认加载',
    cancelText: '取消',
  })
  if (!confirmed) return

  sub2apiGroupsLoadingId.value = server.id
  try {
    const response = await accountImportsApi.listSub2APIServerGroups(server.id)
    sub2apiGroups.value = {
      ...sub2apiGroups.value,
      [server.id]: Array.isArray(response.groups) ? response.groups : [],
    }
    if (!response.groups?.length) toast.info('这个 Sub2API 连接没有返回分组')
  } catch (error: any) {
    toast.error(error.message || '读取 Sub2API 分组失败')
  } finally {
    sub2apiGroupsLoadingId.value = ''
  }
}

function useSub2APIGroup(server: Sub2APIServer, groupId: string) {
  editSub2APIServer(server)
  sub2apiForm.value.group_id = groupId
  toast.info('已填入分组 ID，保存后生效')
}

async function loadExternalSources() {
  await Promise.allSettled([
    loadCPAPools(),
    loadSub2APIServers(),
  ])
}

watch(settings, (value) => {
  if (!value) return
  localSettings.value = ensureSettingsShape(value)
}, { immediate: true })

const reloadSettings = async () => {
  settingsLoadError.value = ''
  try {
    await settingsStore.loadSettings()
  } catch (error: any) {
    settingsLoadError.value = error.message || '设置加载失败'
    toast.error(settingsLoadError.value)
  }
}

onMounted(async () => {
  await reloadSettings()
  await Promise.allSettled([
    loadExternalSources(),
    loadBackups(),
  ])
})

const handleSave = async () => {
  if (!localSettings.value) return
  const confirmed = await confirmDialog.ask({
    title: '确认保存系统设置',
    message: '即将保存当前系统设置，可能影响接口地址、并发、缓存、图片链路、存储和备份策略。是否继续？',
    confirmText: '保存',
    cancelText: '取消',
  })
  if (!confirmed) return

  isSaving.value = true

  try {
    await persistSettings(true)
  } catch (error: any) {
    toast.error(error.message || '保存失败')
  } finally {
    isSaving.value = false
  }
}
</script>

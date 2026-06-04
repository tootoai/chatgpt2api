<template>
  <div class="space-y-6">
    <section class="ui-panel">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="ui-section-title">日志管理</p>
          <p class="mt-1 text-xs text-muted-foreground">
            <template v-if="activeLogView === 'system'">
              当前页 {{ logs.length }} 条，服务端命中 {{ logMeta.total }} 条，每页 {{ filters.limit }} 条
              <span v-if="selectedLogCount > 0">，已选 {{ selectedLogCount }} 条</span>
            </template>
            <template v-else>
              运行日志 {{ runtimeLogs.length }} 条，来源 {{ runtimeFilters.source || '全部' }}，级别 {{ runtimeFilters.level || '全部' }}
            </template>
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <Button size="sm" :variant="activeLogView === 'system' ? 'primary' : 'outline'" @click="setActiveLogView('system')">
            调用日志
          </Button>
          <Button size="sm" :variant="activeLogView === 'runtime' ? 'primary' : 'outline'" @click="setActiveLogView('runtime')">
            运行日志
          </Button>
          <Button size="sm" variant="outline" :disabled="activeFetching" @click="refreshActiveLogs">
            {{ activeFetching ? '刷新中...' : '刷新' }}
          </Button>
          <Button size="sm" variant="outline" :disabled="activeExportDisabled" @click="exportActiveLogs">
            导出当前页
          </Button>
          <Button
            v-if="activeLogView === 'system'"
            size="sm"
            variant="outline"
            root-class="text-rose-600 hover:text-rose-700"
            :disabled="selectedLogCount === 0 || isFetching || isDeleting"
            @click="requestDeleteSelectedLogs"
          >
            删除所选{{ selectedLogCount ? ` (${selectedLogCount})` : '' }}
          </Button>
          <Button size="sm" :variant="autoRefreshEnabled ? 'primary' : 'outline'" @click="toggleAutoRefresh">
            {{ autoRefreshEnabled ? '自动刷新 8s' : '自动刷新已关' }}
          </Button>
          <Button v-if="activeLogView === 'system'" size="sm" variant="outline" @click="confirmOpen = true">
            清空
          </Button>
        </div>
      </div>

      <div v-if="activeLogView === 'system'" class="mt-5 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <div class="ui-card-sm">
          <p class="text-[11px] text-muted-foreground">总数</p>
          <p class="mt-1 text-lg font-semibold text-foreground">{{ logStats.total }}</p>
        </div>
        <div class="ui-card-sm">
          <p class="text-[11px] text-muted-foreground">成功</p>
          <p class="mt-1 text-lg font-semibold text-emerald-600">{{ logStats.success }}</p>
        </div>
        <div class="ui-card-sm">
          <p class="text-[11px] text-muted-foreground">失败</p>
          <p class="mt-1 text-lg font-semibold text-rose-600">{{ logStats.failed }}</p>
        </div>
        <div class="ui-card-sm">
          <p class="text-[11px] text-muted-foreground">限流 / 受限</p>
          <p class="mt-1 text-lg font-semibold text-amber-600">{{ logStats.limited }}</p>
        </div>
        <div class="ui-card-sm">
          <p class="text-[11px] text-muted-foreground">图片接口</p>
          <p class="mt-1 text-lg font-semibold text-cyan-600">{{ logStats.image }}</p>
        </div>
        <div class="ui-card-sm">
          <p class="text-[11px] text-muted-foreground">文本回复无图</p>
          <p class="mt-1 text-lg font-semibold text-violet-600">{{ logStats.textReply }}</p>
        </div>
      </div>
      <div v-else class="mt-5 grid grid-cols-2 gap-3 md:grid-cols-5">
        <div class="ui-card-sm">
          <p class="text-[11px] text-muted-foreground">运行日志</p>
          <p class="mt-1 text-lg font-semibold text-foreground">{{ runtimeStats.total }}</p>
        </div>
        <div class="ui-card-sm">
          <p class="text-[11px] text-muted-foreground">Warning</p>
          <p class="mt-1 text-lg font-semibold text-amber-600">{{ runtimeStats.warning }}</p>
        </div>
        <div class="ui-card-sm">
          <p class="text-[11px] text-muted-foreground">Error</p>
          <p class="mt-1 text-lg font-semibold text-rose-600">{{ runtimeStats.error }}</p>
        </div>
        <div class="ui-card-sm">
          <p class="text-[11px] text-muted-foreground">内存来源</p>
          <p class="mt-1 text-lg font-semibold text-cyan-600">{{ runtimeStats.memory }}</p>
        </div>
        <div class="ui-card-sm">
          <p class="text-[11px] text-muted-foreground">文件来源</p>
          <p class="mt-1 text-lg font-semibold text-violet-600">{{ runtimeStats.file }}</p>
        </div>
      </div>
    </section>

    <section v-if="activeLogView === 'system'" class="ui-panel">
      <div class="grid gap-3 lg:grid-cols-[repeat(5,minmax(0,1fr))_8rem]">
        <SelectMenu
          v-model="filters.type"
          :options="typeOptions"
          placeholder="全部类型"
          selected-indicator="none"
        />
        <SelectMenu
          v-model="filters.status"
          :options="statusOptions"
          placeholder="全部状态"
          selected-indicator="none"
        />
        <SelectMenu
          v-model="filters.endpoint"
          :options="endpointOptions"
          placeholder="全部接口"
          selected-indicator="none"
        />
        <SelectMenu
          v-model="filters.model"
          :options="modelOptions"
          placeholder="全部模型"
          selected-indicator="none"
        />
        <SelectMenu
          v-model="filters.account"
          :options="accountOptions"
          placeholder="全部账号"
          selected-indicator="none"
        />
        <Input
          :model-value="String(filters.limit)"
          type="number"
          root-class="min-w-28"
          @update:model-value="updateLimit"
        />
      </div>

      <div class="mt-3 grid gap-3 lg:grid-cols-[10rem_10rem_14rem_1fr]">
        <Input
          v-model="filters.startDate"
          type="date"
          root-class="min-w-36"
        />
        <Input
          v-model="filters.endDate"
          type="date"
          root-class="min-w-36"
        />
        <Input
          v-model.trim="filters.conversationId"
          type="text"
          placeholder="conversation_id"
          block
        />
        <Input
          v-model.trim="filters.search"
          type="text"
          placeholder="搜索 request、error、conversation_id、account_email..."
          block
        />
      </div>

      <div class="mt-3 flex flex-wrap items-center gap-2">
        <Button size="xs" variant="outline" @click="setQuickStatus('failed')">只看失败</Button>
        <Button size="xs" variant="outline" @click="setQuickEndpoint('/v1/images/edits')">图生图</Button>
        <Button size="xs" variant="outline" @click="setQuickEndpoint('/v1/images/generations')">文生图</Button>
        <Button size="xs" variant="outline" @click="setQuickError('upstream_text_reply')">文本回复无图</Button>
        <Button size="xs" variant="outline" @click="resetFilters">重置筛选</Button>
      </div>
    </section>

    <section v-else class="ui-panel">
      <div class="grid gap-3 md:grid-cols-[10rem_10rem_1fr_8rem]">
        <SelectMenu
          v-model="runtimeFilters.level"
          :options="runtimeLevelOptions"
          placeholder="全部级别"
          selected-indicator="none"
        />
        <SelectMenu
          v-model="runtimeFilters.source"
          :options="runtimeSourceOptions"
          placeholder="全部来源"
          selected-indicator="none"
        />
        <Input
          v-model.trim="runtimeFilters.search"
          type="text"
          placeholder="搜索运行事件、错误、conversation_id、文件路径..."
          block
        />
        <Input
          :model-value="String(runtimeFilters.limit)"
          type="number"
          root-class="min-w-28"
          @update:model-value="updateRuntimeLimit"
        />
      </div>
      <p class="mt-3 text-xs text-muted-foreground">
        内存日志来自项目统一 logger；文件日志会尝试读取常见部署日志路径或 `CHATGPT2API_RUNTIME_LOG_FILE` 指定路径。
      </p>
    </section>

    <section v-if="activeLogView === 'system'" class="ui-panel !p-0 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[1120px] table-fixed text-left">
          <colgroup>
            <col class="w-12" />
            <col class="w-36" />
            <col class="w-24" />
            <col class="w-40" />
            <col class="w-28" />
            <col class="w-24" />
            <col class="w-28" />
            <col />
            <col class="w-36" />
          </colgroup>
          <thead class="bg-muted/40 text-xs text-muted-foreground">
            <tr>
              <th class="py-3 pl-4 pr-2">
                <Checkbox
                  :model-value="allVisibleLogsSelected"
                  :disabled="visibleLogs.length === 0"
                  @update:model-value="toggleSelectAllVisibleLogs"
                >
                  <span class="sr-only">全选当前页日志</span>
                </Checkbox>
              </th>
              <th class="py-3 pr-5">时间</th>
              <th class="py-3 pr-5">类型</th>
              <th class="py-3 pr-5">令牌名称</th>
              <th class="py-3 pr-5">调用耗时</th>
              <th class="py-3 pr-5">状态</th>
              <th class="py-3 pr-5">图片</th>
              <th class="py-3 pr-5">简述</th>
              <th class="py-3 pr-4 text-right">操作</th>
            </tr>
          </thead>
          <tbody class="text-sm text-foreground">
            <tr v-if="!isFetching && logs.length === 0">
              <td colspan="9" class="py-8">
                <EmptyState
                  plain
                  :title="logsLoadError ? '日志加载失败' : '暂无日志'"
                  :description="logsLoadError || '换个筛选条件或刷新后再看。'"
                />
              </td>
            </tr>
            <tr
              v-for="item in visibleLogs"
              :key="item.id"
              class="border-t border-border transition-colors hover:bg-muted/30"
              :class="{ 'bg-primary/5': isLogSelected(item.id) }"
            >
              <td class="py-4 pl-4 pr-2 align-top">
                <Checkbox
                  :model-value="isLogSelected(item.id)"
                  @update:model-value="(checked) => toggleLogSelection(item.id, checked)"
                >
                  <span class="sr-only">选择日志 {{ item.time || item.id }}</span>
                </Checkbox>
              </td>
              <td class="py-4 pr-5 align-top text-xs text-muted-foreground">
                <p class="whitespace-nowrap text-foreground">{{ item.time || '-' }}</p>
              </td>
              <td class="py-4 pr-5 align-top">
                <span class="ui-chip text-[11px] text-muted-foreground">{{ typeLabel(item.type) }}</span>
              </td>
              <td class="py-4 pr-5 align-top">
                <p class="max-w-[12rem] truncate text-xs text-foreground" :title="tokenLabel(item)">
                  {{ tokenLabel(item) || '-' }}
                </p>
                <p v-if="item.conversationId" class="mt-1 max-w-[12rem] truncate font-mono text-[11px] text-muted-foreground" :title="item.conversationId">
                  {{ item.conversationId }}
                </p>
              </td>
              <td class="py-4 pr-5 align-top text-xs text-muted-foreground">
                {{ formatDuration(item.durationMs) || '-' }}
              </td>
              <td class="py-4 pr-5 align-top">
                <span class="rounded-md px-2 py-1 text-xs font-medium" :class="statusClass(item)">
                  {{ statusLabel(item) }}
                </span>
              </td>
              <td class="py-4 pr-5 align-top">
                <div v-if="item.imageUrls.length" class="flex items-center gap-2">
                  <button
                    type="button"
                    class="relative h-14 w-14 overflow-hidden rounded-lg border border-border bg-muted text-[10px] text-muted-foreground transition-colors hover:border-primary/40"
                    title="查看图片预览"
                    @click="openDetail(item)"
                  >
                    <img
                      v-if="!isPreviewBroken(item.imageUrls[0])"
                      :src="item.imageUrls[0]"
                      :alt="item.preview || '日志结果图片'"
                      loading="lazy"
                      class="h-full w-full object-cover"
                      @error="markPreviewBroken($event, item.imageUrls[0])"
                    />
                    <span v-else class="flex h-full w-full items-center justify-center px-1 text-center">
                      无法预览
                    </span>
                  </button>
                  <span v-if="item.imageUrls.length > 1" class="ui-chip text-[11px] text-muted-foreground">
                    +{{ item.imageUrls.length - 1 }}
                  </span>
                </div>
                <span v-else class="text-xs text-muted-foreground">-</span>
              </td>
              <td class="py-4 pr-5 align-top">
                <p class="max-w-[28rem] truncate text-xs text-foreground" :class="{ 'text-rose-600': isFailed(item) }" :title="summaryText(item)">
                  {{ summaryText(item) || '-' }}
                </p>
              </td>
              <td class="py-4 pr-4 text-right align-top">
                <div class="flex justify-end gap-1.5">
                  <Button size="xs" variant="outline" @click="openDetail(item)">
                    查看详情
                  </Button>
                  <Button size="xs" variant="ghost" root-class="text-rose-600 hover:text-rose-700" @click="requestDeleteLog(item)">
                    删除
                  </Button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3 text-xs text-muted-foreground">
        <div class="flex flex-wrap items-center gap-2">
          <span>第 {{ currentPage }} 页，显示 {{ visibleLogs.length }} 条，筛选命中 {{ logMeta.total }} 条</span>
          <template v-if="selectedLogCount > 0">
            <span class="rounded-full border border-border bg-muted/20 px-2 py-1">已选 {{ selectedLogCount }} 条</span>
            <Button size="xs" variant="ghost" :disabled="isDeleting" @click="clearLogSelection">取消选择</Button>
          </template>
        </div>
        <div class="flex items-center gap-2">
          <span>每页</span>
          <SelectMenu
            :model-value="String(filters.limit)"
            :options="pageSizeOptions"
            selected-indicator="none"
            auto-width
            @update:model-value="updateLimit"
          />
          <Button size="xs" variant="outline" :disabled="currentPage <= 1 || isFetching" @click="goPreviousPage">上一页</Button>
          <Button size="xs" variant="outline" :disabled="!logMeta.hasMore || isFetching" @click="goNextPage">下一页</Button>
        </div>
      </div>
    </section>

    <section v-else class="ui-panel !p-0 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[900px] table-fixed text-left">
          <colgroup>
            <col class="w-40" />
            <col class="w-24" />
            <col class="w-24" />
            <col />
            <col class="w-56" />
          </colgroup>
          <thead class="bg-muted/40 text-xs text-muted-foreground">
            <tr>
              <th class="py-3 pl-4 pr-5">时间</th>
              <th class="py-3 pr-5">级别</th>
              <th class="py-3 pr-5">来源</th>
              <th class="py-3 pr-5">内容</th>
              <th class="py-3 pr-4">路径</th>
            </tr>
          </thead>
          <tbody class="text-sm text-foreground">
            <tr v-if="!runtimeFetching && runtimeLogs.length === 0">
              <td colspan="5" class="py-8">
                <EmptyState
                  plain
                  :title="runtimeLoadError ? '运行日志加载失败' : '暂无运行日志'"
                  :description="runtimeLoadError || '当前进程还没有捕获到运行日志，或部署环境没有挂载日志文件。'"
                />
              </td>
            </tr>
            <tr
              v-for="item in runtimeLogs"
              :key="runtimeLogId(item)"
              class="border-t border-border transition-colors hover:bg-muted/30"
            >
              <td class="py-4 pl-4 pr-5 align-top text-xs text-muted-foreground">
                <p class="whitespace-nowrap text-foreground">{{ item.time || '-' }}</p>
              </td>
              <td class="py-4 pr-5 align-top">
                <span class="rounded-md px-2 py-1 text-xs font-medium" :class="runtimeLevelClass(item.level)">
                  {{ item.level || 'info' }}
                </span>
              </td>
              <td class="py-4 pr-5 align-top">
                <span class="ui-chip text-[11px] text-muted-foreground">{{ item.source || '-' }}</span>
              </td>
              <td class="py-4 pr-5 align-top">
                <p class="whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-foreground">
                  {{ item.message || '-' }}
                </p>
              </td>
              <td class="py-4 pr-4 align-top">
                <p class="break-all font-mono text-[11px] text-muted-foreground">{{ item.path || '-' }}</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3 text-xs text-muted-foreground">
        <span>显示 {{ runtimeLogs.length }} 条，命中 {{ runtimeMeta.total }} 条</span>
        <span>候选文件 {{ runtimeMeta.sources.files.length }} 个</span>
      </div>
    </section>

    <Teleport to="body">
      <div
        v-if="selectedLog"
        class="fixed inset-0 z-[130] bg-black/40"
        @click.self="closeDetail"
      >
        <aside class="ml-auto flex h-full w-full max-w-[46rem] flex-col overflow-hidden border-l border-border bg-background shadow-xl">
          <div class="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
            <div class="min-w-0">
              <p class="ui-section-title">日志详情</p>
              <p class="mt-1 truncate text-xs text-muted-foreground">{{ selectedLog.id }}</p>
            </div>
            <Button size="xs" variant="outline" root-class="min-w-14 justify-center" @click="closeDetail">
              关闭
            </Button>
          </div>

          <div class="scrollbar-slim flex-1 space-y-5 overflow-y-auto px-5 py-4">
            <div class="grid gap-2 sm:grid-cols-2">
              <div
                v-for="field in selectedDetailFields"
                :key="field.label"
                class="rounded-lg border border-border bg-card px-3 py-2 text-xs"
              >
                <div class="flex items-center justify-between gap-2">
                  <span class="text-muted-foreground">{{ field.label }}</span>
                  <Button
                    v-if="field.copyable && field.value"
                    size="xs"
                    variant="ghost"
                    @click="copyText(field.value)"
                  >
                    复制
                  </Button>
                </div>
                <p class="mt-1 break-all font-mono text-foreground">{{ field.value || '-' }}</p>
              </div>
            </div>

            <DetailBlock
              title="请求文本"
              :content="selectedLog.requestText"
              @copy="copyText"
            />
            <DetailBlock
              title="错误"
              :content="selectedLog.error"
              tone="danger"
              @copy="copyText"
            />
            <DetailBlock
              title="上游文本回复"
              :content="selectedLog.rawUpstreamMessage || selectedLog.upstreamPreview"
              tone="warning"
              @copy="copyText"
            />
            <div v-if="selectedLog.imageUrls.length" class="rounded-lg border border-border bg-card">
              <div class="flex items-center justify-between border-b border-border/70 px-3 py-2">
                <span class="text-xs font-medium text-foreground">图片预览</span>
                <span class="text-xs text-muted-foreground">{{ selectedLog.imageUrls.length }} 张</span>
              </div>
              <div class="grid gap-3 p-3 sm:grid-cols-2">
                <a
                  v-for="(url, index) in selectedLog.imageUrls"
                  :key="`${selectedLog.id}-image-${index}-${url}`"
                  :href="url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="group overflow-hidden rounded-lg border border-border bg-muted/30 transition-colors hover:border-primary/40"
                  :title="selectedLog.urls[index] || url"
                >
                  <div class="flex aspect-video items-center justify-center overflow-hidden bg-muted text-xs text-muted-foreground">
                    <img
                      v-if="!isPreviewBroken(url)"
                      :src="url"
                      :alt="`日志结果图片 ${index + 1}`"
                      loading="lazy"
                      class="h-full w-full object-cover transition-transform group-hover:scale-[1.02]"
                      @error="markPreviewBroken($event, url)"
                    />
                    <span v-else>无法预览</span>
                  </div>
                  <p class="truncate px-2 py-1.5 font-mono text-[11px] text-muted-foreground">
                    {{ filenameFromUrl(selectedLog.urls[index] || url) }}
                  </p>
                </a>
              </div>
            </div>
            <DetailBlock
              title="结果 URL"
              :content="selectedLog.urls.join('\n')"
              @copy="copyText"
            />

            <div class="rounded-lg border border-border bg-muted/20">
              <div class="flex items-center justify-between border-b border-border px-3 py-2">
                <span class="text-xs font-medium text-foreground">Raw detail JSON</span>
                <Button size="xs" variant="ghost" @click="copyText(selectedLog.rawJson)">复制</Button>
              </div>
              <pre class="max-h-[24rem] overflow-auto whitespace-pre-wrap break-words p-3 font-mono text-[11px] leading-relaxed text-muted-foreground">{{ selectedLog.rawJson }}</pre>
            </div>
          </div>
        </aside>
      </div>
    </Teleport>

    <ConfirmDialog
      :open="confirmOpen"
      title="确认清空日志"
      message="会删除当前日志文件中可读取到的日志记录，这个操作不可恢复。"
      confirm-text="清空"
      cancel-text="取消"
      @confirm="clearLogs"
      @cancel="confirmOpen = false"
    />
    <ConfirmDialog
      :open="Boolean(deleteTarget)"
      title="删除日志"
      :message="`确认删除这条日志吗？删除后无法恢复。${deleteTarget?.time ? `\n时间：${deleteTarget.time}` : ''}`"
      confirm-text="删除"
      cancel-text="取消"
      @confirm="deleteLog"
      @cancel="deleteTarget = null"
    />
    <ConfirmDialog
      :open="deleteSelectedOpen"
      title="删除所选日志"
      :message="`确认删除当前选中的 ${selectedLogCount} 条日志吗？删除后无法恢复。`"
      confirm-text="删除所选"
      cancel-text="取消"
      @confirm="deleteSelectedLogs"
      @cancel="deleteSelectedOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Button, Checkbox, ConfirmDialog, EmptyState, Input, SelectMenu } from 'nanocat-ui'
import { logsApi } from '@/api'
import type { RuntimeLog, RuntimeLogsResponse, SystemLog, SystemLogsResponse } from '@/api/logs'
import { useToast } from '@/composables/useToast'

type LogRow = {
  id: string
  raw: SystemLog
  time: string
  type: string
  summary: string
  endpoint: string
  model: string
  status: string
  keyId: string
  keyName: string
  role: string
  accountEmail: string
  conversationId: string
  durationMs: string
  statusCode: string
  startedAt: string
  endedAt: string
  requestText: string
  requestShape: string
  error: string
  errorCode: string
  stage: string
  reason: string
  canResumePoll: boolean
  toolInvoked: string
  upstreamMessageLen: string
  blocked: string
  upstreamPreview: string
  rawUpstreamMessage: string
  urls: string[]
  imageUrls: string[]
  diagnosisChips: DiagnosisChip[]
  preview: string
  rawJson: string
}

type DiagnosisChip = {
  label: string
  tone: 'neutral' | 'success' | 'warning' | 'danger' | 'info'
}

type DetailField = {
  label: string
  value: string
  copyable?: boolean
}

type LogView = 'system' | 'runtime'

const DetailBlock = defineComponent({
  props: {
    title: { type: String, required: true },
    content: { type: String, default: '' },
    tone: { type: String, default: 'default' },
  },
  emits: ['copy'],
  setup(props, { emit }) {
    return () => props.content
      ? h('div', {
          class: [
            'rounded-lg border',
            props.tone === 'danger'
              ? 'border-rose-500/30 bg-rose-500/10'
              : props.tone === 'warning'
                ? 'border-amber-500/30 bg-amber-500/10'
                : 'border-border bg-card',
          ],
        }, [
          h('div', { class: 'flex items-center justify-between border-b border-border/70 px-3 py-2' }, [
            h('span', { class: 'text-xs font-medium text-foreground' }, props.title),
            h(Button as any, {
              size: 'xs',
              variant: 'ghost',
              onClick: () => emit('copy', props.content),
            }, () => '复制'),
          ]),
          h('pre', { class: 'max-h-[16rem] overflow-auto whitespace-pre-wrap break-words p-3 font-mono text-[11px] leading-relaxed text-foreground' }, props.content),
        ])
      : null
  },
})

const toast = useToast()
const route = useRoute()
const apiBaseUrl = import.meta.env.VITE_API_URL || window.location.origin
const activeLogView = ref<LogView>('system')
const logs = ref<LogRow[]>([])
const isFetching = ref(false)
const logsLoadError = ref('')
const runtimeLogs = ref<RuntimeLog[]>([])
const runtimeFetching = ref(false)
const runtimeLoadError = ref('')
const confirmOpen = ref(false)
const selectedLog = ref<LogRow | null>(null)
const autoRefreshEnabled = ref(false)
const currentPage = ref(1)
const brokenPreviewUrls = ref<Set<string>>(new Set())
const deleteTarget = ref<LogRow | null>(null)
const deleteSelectedOpen = ref(false)
const selectedLogIds = ref<string[]>([])
const isDeleting = ref(false)

const logMeta = reactive<SystemLogsResponse>({
  items: [],
  total: 0,
  limit: 500,
  offset: 0,
  has_more: false,
  facets: {
    statuses: {},
    endpoints: {},
    models: {},
    accounts: {},
  },
  stats: {
    total: 0,
    success: 0,
    failed: 0,
    limited: 0,
    image: 0,
    textReply: 0,
  },
})

const filters = reactive({
  type: 'call',
  status: '',
  endpoint: '',
  model: '',
  account: '',
  conversationId: '',
  search: '',
  startDate: '',
  endDate: '',
  limit: 500,
})

const runtimeFilters = reactive({
  level: '',
  source: '',
  search: '',
  limit: 300,
})

const runtimeMeta = reactive<RuntimeLogsResponse>({
  items: [],
  total: 0,
  limit: 300,
  sources: {
    memory: true,
    files: [],
  },
})

const typeOptions = [
  { label: '调用日志', value: 'call' },
  { label: '账号日志', value: 'account' },
  { label: '全部类型', value: '' },
]

const visibleLimitOptions = [
  { label: '50', value: '50' },
  { label: '100', value: '100' },
  { label: '200', value: '200' },
  { label: '500', value: '500' },
]
const pageSizeOptions = visibleLimitOptions

const runtimeLevelOptions = [
  { label: '全部级别', value: '' },
  { label: 'debug', value: 'debug' },
  { label: 'info', value: 'info' },
  { label: 'warning', value: 'warning' },
  { label: 'error', value: 'error' },
]

const runtimeSourceOptions = [
  { label: '全部来源', value: '' },
  { label: '内存日志', value: 'memory' },
  { label: '文件尾部', value: 'file' },
]

let autoRefreshTimer: number | null = null
let filterFetchTimer: number | null = null
let isApplyingRouteQuery = false
const routeTargetLogId = ref('')

function cleanString(value: unknown): string {
  if (value === undefined || value === null) return ''
  return String(value).trim()
}

function detailValue(detail: Record<string, any>, key: string): string {
  const value = detail[key]
  if (value !== undefined && value !== null && value !== '') return cleanString(value)
  const diagnosis = detail.diagnosis
  if (diagnosis && typeof diagnosis === 'object') return cleanString(diagnosis[key])
  return ''
}

function detailRawValue(detail: Record<string, any>, key: string): unknown {
  if (Object.prototype.hasOwnProperty.call(detail, key)) return detail[key]
  const diagnosis = detail.diagnosis
  if (diagnosis && typeof diagnosis === 'object' && Object.prototype.hasOwnProperty.call(diagnosis, key)) {
    return diagnosis[key]
  }
  return undefined
}

function collectUrls(value: unknown): string[] {
  const urls: string[] = []
  if (Array.isArray(value)) {
    value.forEach((item) => urls.push(...collectUrls(item)))
  } else if (value && typeof value === 'object') {
    Object.entries(value as Record<string, unknown>).forEach(([key, item]) => {
      if (key === 'url' && typeof item === 'string') urls.push(item)
      else if (key === 'urls' && Array.isArray(item)) urls.push(...item.map((url) => cleanString(url)).filter(Boolean))
      else urls.push(...collectUrls(item))
    })
  }
  return Array.from(new Set(urls))
}

function normalizePreviewUrl(url: string): string {
  const value = cleanString(url)
  if (!value || value.startsWith('file-service://')) return ''
  if (value.startsWith('/images/') || value.startsWith('/image-thumbnails/')) return value
  if (value.startsWith('images/') || value.startsWith('image-thumbnails/')) return `/${value}`
  if (/^https?:\/\//i.test(value)) {
    try {
      const parsed = new URL(value)
      if (parsed.pathname.startsWith('/images/') || parsed.pathname.startsWith('/image-thumbnails/')) {
        return `${parsed.pathname}${parsed.search}${parsed.hash}`
      }
    } catch {
      return value
    }
    return value
  }
  if (value.startsWith('/')) return `${apiBaseUrl}${value}`
  return ''
}

function normalizePreviewUrls(urls: string[]): string[] {
  return Array.from(new Set(urls.map(normalizePreviewUrl).filter(Boolean)))
}

function isPreviewBroken(url: string): boolean {
  return brokenPreviewUrls.value.has(url)
}

function markPreviewBroken(event: Event, url: string) {
  const img = event.target as HTMLImageElement
  img.style.opacity = '0'
  brokenPreviewUrls.value = new Set([...brokenPreviewUrls.value, url])
}

function filenameFromUrl(url: string): string {
  const value = cleanString(url)
  if (!value) return '-'
  try {
    const parsed = new URL(value, window.location.origin)
    const name = parsed.pathname.split('/').filter(Boolean).pop()
    return name || parsed.hostname || value
  } catch {
    return value.split('/').filter(Boolean).pop() || value
  }
}

function prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value ?? {}, null, 2)
  } catch {
    return String(value ?? '')
  }
}

function summarizeText(value: string, max = 220): string {
  const clean = value.replace(/\s+/g, ' ').trim()
  if (clean.length <= max) return clean
  return `${clean.slice(0, max - 1)}…`
}

function formatDuration(value: string): string {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) return ''
  if (parsed < 1000) return `${Math.round(parsed)}ms`
  if (parsed < 10000) return `${(parsed / 1000).toFixed(2)}s`
  return `${(parsed / 1000).toFixed(1)}s`
}

function boolDetailLabel(value: unknown): string {
  if (value === true || value === 'true') return 'true'
  if (value === false || value === 'false') return 'false'
  return cleanString(value)
}

function buildDiagnosisChips(row: {
  status: string
  durationMs: string
  statusCode: string
  errorCode: string
  stage: string
  reason: string
  requestShape: string
  imageCount: number
  canResumePoll: boolean
  rawUpstreamMessage: string
  upstreamPreview: string
  upstreamMessageLen: string
  toolInvoked: string
}): DiagnosisChip[] {
  const chips: DiagnosisChip[] = []
  const duration = formatDuration(row.durationMs)
  if (duration) chips.push({ label: `耗时 ${duration}`, tone: 'neutral' })
  if (row.statusCode) chips.push({ label: `HTTP ${row.statusCode}`, tone: Number(row.statusCode) >= 400 ? 'danger' : 'neutral' })
  if (row.errorCode) chips.push({ label: `code=${row.errorCode}`, tone: 'warning' })
  if (row.stage) chips.push({ label: `stage=${row.stage}`, tone: 'info' })
  if (row.canResumePoll) chips.push({ label: '可继续轮询', tone: 'info' })
  if (row.rawUpstreamMessage || row.upstreamPreview || row.upstreamMessageLen) {
    chips.push({ label: row.upstreamMessageLen ? `上游文本 ${row.upstreamMessageLen}` : '上游文本', tone: 'warning' })
  }
  if (row.toolInvoked) chips.push({ label: `tool=${row.toolInvoked}`, tone: row.toolInvoked === 'false' ? 'warning' : 'neutral' })
  if (row.requestShape) chips.push({ label: `shape=${row.requestShape}`, tone: 'neutral' })
  if (row.imageCount) chips.push({ label: `图片 ${row.imageCount}`, tone: 'success' })
  if (chips.length === 0 && row.status.toLowerCase() === 'success') {
    chips.push({ label: '正常', tone: 'success' })
  }
  if (chips.length === 0 && row.reason) {
    chips.push({ label: summarizeText(row.reason, 28), tone: 'warning' })
  }
  return chips.slice(0, 5)
}

function normalizeLog(item: SystemLog, index: number): LogRow {
  const detail = item.detail || {}
  const error = detailValue(detail, 'error')
  const requestText = detailValue(detail, 'request_text')
  const rawUpstreamMessage = detailValue(detail, 'raw_upstream_message')
  const upstreamPreview = detailValue(detail, 'upstream_message_preview')
  const reason = detailValue(detail, 'reason')
  const summary = cleanString(item.summary)
  const preview = summarizeText(requestText || rawUpstreamMessage || upstreamPreview || error || reason || summary)
  const urls = collectUrls(detail)
  const imageUrls = normalizePreviewUrls(urls)
  const status = detailValue(detail, 'status')
  const durationMs = detailValue(detail, 'duration_ms')
  const statusCode = detailValue(detail, 'status_code')
  const startedAt = detailValue(detail, 'started_at')
  const endedAt = detailValue(detail, 'ended_at')
  const requestShape = detailValue(detail, 'request_shape')
  const errorCode = detailValue(detail, 'error_code')
  const stage = detailValue(detail, 'stage')
  const canResumePoll = detail.can_resume_poll === true || detailValue(detail, 'can_resume_poll') === 'true'
  const toolInvoked = boolDetailLabel(detailRawValue(detail, 'tool_invoked'))
  const blocked = boolDetailLabel(detailRawValue(detail, 'blocked'))
  const upstreamMessageLen = detailValue(detail, 'upstream_message_len')
  const time = startedAt || cleanString(item.time) || endedAt

  return {
    id: cleanString(item.id) || `log-${index}`,
    raw: item,
    time,
    type: cleanString(item.type),
    summary,
    endpoint: detailValue(detail, 'endpoint'),
    model: detailValue(detail, 'model'),
    status,
    keyId: detailValue(detail, 'key_id'),
    keyName: detailValue(detail, 'key_name'),
    role: detailValue(detail, 'role'),
    accountEmail: detailValue(detail, 'account_email'),
    conversationId: detailValue(detail, 'conversation_id'),
    durationMs,
    statusCode,
    startedAt,
    endedAt,
    requestText,
    requestShape,
    error,
    errorCode,
    stage,
    reason,
    canResumePoll,
    toolInvoked,
    upstreamMessageLen,
    blocked,
    upstreamPreview,
    rawUpstreamMessage,
    urls,
    imageUrls,
    diagnosisChips: buildDiagnosisChips({
      status,
      durationMs,
      statusCode,
      errorCode,
      stage,
      reason,
      requestShape,
      imageCount: imageUrls.length,
      canResumePoll,
      rawUpstreamMessage,
      upstreamPreview,
      upstreamMessageLen,
      toolInvoked,
    }),
    preview,
    rawJson: prettyJson(detail),
  }
}

function isFailed(item: LogRow): boolean {
  return item.status.toLowerCase() === 'failed' || Boolean(item.error || item.errorCode)
}

function isSuccess(item: LogRow): boolean {
  return item.status.toLowerCase() === 'success'
}

function isLimited(item: LogRow): boolean {
  const text = [item.status, item.errorCode, item.reason, item.error].join(' ').toLowerCase()
  return text.includes('limit') || text.includes('quota') || text.includes('受限') || text.includes('限流')
}

const logStats = computed(() => logMeta.stats)
const activeFetching = computed(() => activeLogView.value === 'runtime' ? runtimeFetching.value : isFetching.value)
const activeExportDisabled = computed(() => (
  activeLogView.value === 'runtime'
    ? runtimeLogs.value.length === 0
    : logs.value.length === 0
))
const runtimeStats = computed(() => {
  const counts = { total: runtimeLogs.value.length, warning: 0, error: 0, memory: 0, file: 0 }
  runtimeLogs.value.forEach((item) => {
    const level = cleanString(item.level).toLowerCase()
    const source = cleanString(item.source).toLowerCase()
    if (level === 'warning') counts.warning += 1
    if (level === 'error' || level === 'critical') counts.error += 1
    if (source === 'memory') counts.memory += 1
    if (source === 'file') counts.file += 1
  })
  return counts
})

function optionFromFacet(facet: Record<string, number>, allLabel: string) {
  return [
    { label: allLabel, value: '' },
    ...Object.keys(facet)
      .map(cleanString)
      .filter(Boolean)
      .sort((a, b) => a.localeCompare(b))
      .map((value) => ({ label: `${value} (${facet[value] || 0})`, value })),
  ]
}

const statusOptions = computed(() => [
  { label: '全部状态', value: '' },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
  { label: '限流/受限', value: 'limited' },
])

const endpointOptions = computed(() => optionFromFacet(logMeta.facets.endpoints, '全部接口'))
const modelOptions = computed(() => optionFromFacet(logMeta.facets.models, '全部模型'))
const accountOptions = computed(() => optionFromFacet(logMeta.facets.accounts, '全部账号'))

const visibleLogs = computed(() => {
  return logs.value
})

const selectedLogIdSet = computed(() => new Set(selectedLogIds.value))
const selectedLogCount = computed(() => selectedLogIds.value.length)
const allVisibleLogsSelected = computed(() => {
  if (visibleLogs.value.length === 0) return false
  return visibleLogs.value.every((item) => selectedLogIdSet.value.has(item.id))
})

const selectedDetailFields = computed<DetailField[]>(() => {
  const item = selectedLog.value
  if (!item) return []
  return [
    { label: 'status', value: statusLabel(item) },
    { label: 'endpoint', value: item.endpoint, copyable: true },
    { label: 'model', value: item.model, copyable: true },
    { label: 'duration_ms', value: item.durationMs },
    { label: 'status_code', value: item.statusCode },
    { label: 'started_at', value: item.startedAt || item.time },
    { label: 'ended_at', value: item.endedAt },
    { label: 'account_email', value: item.accountEmail, copyable: true },
    { label: 'conversation_id', value: item.conversationId, copyable: true },
    { label: 'error_code', value: item.errorCode, copyable: true },
    { label: 'stage', value: item.stage, copyable: true },
    { label: 'reason', value: item.reason, copyable: true },
    { label: 'request_shape', value: item.requestShape, copyable: true },
    { label: 'tool_invoked', value: item.toolInvoked },
    { label: 'blocked', value: item.blocked },
    { label: 'upstream_message_len', value: item.upstreamMessageLen },
    { label: 'key', value: [item.keyName, item.keyId].filter(Boolean).join(' / '), copyable: true },
  ]
})

function typeLabel(type: string): string {
  if (type === 'call') return '调用日志'
  if (type === 'account') return '账号日志'
  return type || '日志'
}

function tokenLabel(item: LogRow): string {
  return item.keyName || item.keyId || item.accountEmail
}

function summaryText(item: LogRow): string {
  return item.summary || item.error || item.reason || item.preview
}

function statusLabel(item: LogRow): string {
  if (isSuccess(item)) return '成功'
  if (isFailed(item)) return '失败'
  if (isLimited(item)) return '受限'
  return item.status || '记录'
}

function statusClass(item: LogRow): string {
  if (isSuccess(item)) return 'bg-emerald-500/10 text-emerald-700'
  if (isFailed(item)) return 'bg-rose-500/10 text-rose-700'
  if (isLimited(item)) return 'bg-amber-500/10 text-amber-700'
  return 'bg-muted text-muted-foreground'
}

function runtimeLogId(item: RuntimeLog): string {
  return cleanString(item.id) || [item.time, item.level, item.source, item.message].map(cleanString).join('|')
}

function runtimeLevelClass(level: unknown): string {
  const value = cleanString(level).toLowerCase()
  if (value === 'error' || value === 'critical') return 'bg-rose-500/10 text-rose-700'
  if (value === 'warning') return 'bg-amber-500/10 text-amber-700'
  if (value === 'debug') return 'bg-muted text-muted-foreground'
  return 'bg-emerald-500/10 text-emerald-700'
}

function updateLimit(value: string) {
  const parsed = Number(value)
  filters.limit = Number.isFinite(parsed) ? Math.min(Math.max(Math.trunc(parsed), 1), 20000) : 500
}

function updateRuntimeLimit(value: string) {
  const parsed = Number(value)
  runtimeFilters.limit = Number.isFinite(parsed) ? Math.min(Math.max(Math.trunc(parsed), 1), 2000) : 300
}

function setActiveLogView(view: LogView) {
  if (activeLogView.value === view) return
  activeLogView.value = view
  if (view === 'runtime' && runtimeLogs.value.length === 0 && !runtimeLoadError.value) {
    void fetchRuntimeLogs()
  }
}

function refreshActiveLogs() {
  if (activeLogView.value === 'runtime') {
    void fetchRuntimeLogs()
    return
  }
  void fetchLogs()
}

function queryValue(value: unknown): string {
  if (Array.isArray(value)) return cleanString(value[0])
  return cleanString(value)
}

function applyRouteQuery() {
  isApplyingRouteQuery = true
  try {
    const query = route.query
    const limit = Number(queryValue(query.limit))
    routeTargetLogId.value = queryValue(query.log_id)
    filters.type = queryValue(query.type) || 'call'
    filters.status = queryValue(query.status)
    filters.endpoint = queryValue(query.endpoint)
    filters.model = queryValue(query.model)
    filters.account = queryValue(query.account)
    filters.conversationId = queryValue(query.conversation_id || query.conversationId)
    filters.search = queryValue(query.search)
    filters.startDate = queryValue(query.start_date || query.startDate)
    filters.endDate = queryValue(query.end_date || query.endDate)
    if (Number.isFinite(limit) && limit > 0) {
      filters.limit = Math.min(Math.max(Math.trunc(limit), 1), 20000)
    }
    currentPage.value = 1
    clearLogSelection()
    if (routeTargetLogId.value) selectedLog.value = null
  } finally {
    isApplyingRouteQuery = false
  }
}

function resetFilters() {
  filters.type = 'call'
  filters.status = ''
  filters.endpoint = ''
  filters.model = ''
  filters.account = ''
  filters.conversationId = ''
  filters.search = ''
  filters.startDate = ''
  filters.endDate = ''
}

function setQuickStatus(status: string) {
  filters.status = status
}

function setQuickEndpoint(endpoint: string) {
  filters.endpoint = endpoint
}

function setQuickError(errorCode: string) {
  filters.status = 'failed'
  filters.search = errorCode
}

function openDetail(item: LogRow) {
  selectedLog.value = item
}

function closeDetail() {
  selectedLog.value = null
}

function isLogSelected(id: string): boolean {
  return selectedLogIdSet.value.has(id)
}

function toggleLogSelection(id: string, checked?: boolean) {
  const next = new Set(selectedLogIds.value)
  const shouldSelect = typeof checked === 'boolean' ? checked : !next.has(id)
  if (shouldSelect) next.add(id)
  else next.delete(id)
  selectedLogIds.value = Array.from(next)
}

function toggleSelectAllVisibleLogs(checked?: boolean) {
  const next = new Set(selectedLogIds.value)
  const shouldSelect = typeof checked === 'boolean' ? checked : !allVisibleLogsSelected.value
  visibleLogs.value.forEach((item) => {
    if (shouldSelect) next.add(item.id)
    else next.delete(item.id)
  })
  selectedLogIds.value = Array.from(next)
}

function clearLogSelection() {
  selectedLogIds.value = []
}

function requestDeleteLog(item: LogRow) {
  deleteTarget.value = item
}

function requestDeleteSelectedLogs() {
  if (selectedLogCount.value === 0) return
  deleteSelectedOpen.value = true
}

function goPreviousPage() {
  if (currentPage.value <= 1) return
  currentPage.value -= 1
}

function goNextPage() {
  if (!logMeta.has_more) return
  currentPage.value += 1
}

async function copyText(value: string) {
  const text = cleanString(value)
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    toast.success('已复制')
  } catch {
    toast.error('复制失败')
  }
}

async function fetchLogs() {
  if (isFetching.value) return
  isFetching.value = true
  logsLoadError.value = ''
  try {
    const response = await logsApi.listSystem({
      type: filters.type || undefined,
      start_date: filters.startDate || undefined,
      end_date: filters.endDate || undefined,
      status: filters.status || undefined,
      endpoint: filters.endpoint || undefined,
      model: filters.model || undefined,
      account: filters.account || undefined,
      conversation_id: filters.conversationId || undefined,
      search: filters.search || undefined,
      limit: filters.limit,
      offset: (currentPage.value - 1) * filters.limit,
    })
    logs.value = response.items.map(normalizeLog)
    const visibleIds = new Set(logs.value.map((item) => item.id))
    selectedLogIds.value = selectedLogIds.value.filter((id) => visibleIds.has(id))
    const targetId = routeTargetLogId.value
    if (targetId) {
      const targetLog = logs.value.find((item) => item.id === targetId)
      if (targetLog) selectedLog.value = targetLog
    }
    logMeta.total = response.total
    logMeta.limit = response.limit
    logMeta.offset = response.offset
    logMeta.has_more = response.has_more
    logMeta.facets = response.facets
    logMeta.stats = response.stats
  } catch (error: any) {
    logsLoadError.value = error.message || '日志加载失败'
    toast.error(logsLoadError.value)
  } finally {
    isFetching.value = false
  }
}

async function fetchRuntimeLogs() {
  if (runtimeFetching.value) return
  runtimeFetching.value = true
  runtimeLoadError.value = ''
  try {
    const response = await logsApi.listRuntime({
      level: runtimeFilters.level || undefined,
      source: runtimeFilters.source || undefined,
      search: runtimeFilters.search || undefined,
      limit: runtimeFilters.limit,
    })
    runtimeLogs.value = response.items
    runtimeMeta.items = response.items
    runtimeMeta.total = response.total
    runtimeMeta.limit = response.limit
    runtimeMeta.sources = response.sources
  } catch (error: any) {
    runtimeLoadError.value = error.message || '运行日志加载失败'
    toast.error(runtimeLoadError.value)
  } finally {
    runtimeFetching.value = false
  }
}

function saveJsonBlob(payload: unknown, filename: string) {
  const blob = new Blob(
    [JSON.stringify(payload, null, 2)],
    { type: 'application/json' },
  )
  const blobUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = blobUrl
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(blobUrl)
}

function exportLogs() {
  saveJsonBlob(
    { exported_at: new Date().toISOString(), page: currentPage.value, total: logMeta.total, logs: logs.value.map((item) => item.raw) },
    `logs_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`,
  )
}

function exportRuntimeLogs() {
  saveJsonBlob(
    { exported_at: new Date().toISOString(), total: runtimeMeta.total, logs: runtimeLogs.value },
    `runtime_logs_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`,
  )
}

function exportActiveLogs() {
  if (activeLogView.value === 'runtime') {
    exportRuntimeLogs()
    return
  }
  exportLogs()
}

async function clearLogs() {
  confirmOpen.value = false
  try {
    await logsApi.clear()
    clearLogSelection()
    toast.success('日志已清空')
    await fetchLogs()
  } catch (error: any) {
    toast.error(error.message || '清空失败')
  }
}

async function deleteLog() {
  const item = deleteTarget.value
  if (!item) return
  deleteTarget.value = null
  isDeleting.value = true
  try {
    await logsApi.delete([item.id])
    if (selectedLog.value?.id === item.id) selectedLog.value = null
    selectedLogIds.value = selectedLogIds.value.filter((id) => id !== item.id)
    toast.success('日志已删除')
    await fetchLogs()
  } catch (error: any) {
    toast.error(error.message || '删除失败')
  } finally {
    isDeleting.value = false
  }
}

async function deleteSelectedLogs() {
  const ids = Array.from(new Set(selectedLogIds.value)).filter(Boolean)
  if (ids.length === 0) {
    deleteSelectedOpen.value = false
    return
  }
  deleteSelectedOpen.value = false
  isDeleting.value = true
  try {
    const result = await logsApi.delete(ids)
    if (selectedLog.value && ids.includes(selectedLog.value.id)) selectedLog.value = null
    clearLogSelection()
    toast.success(`已删除 ${result.removed ?? ids.length} 条日志`)
    await fetchLogs()
  } catch (error: any) {
    toast.error(error.message || '删除失败')
  } finally {
    isDeleting.value = false
  }
}

function scheduleAutoRefresh() {
  if (autoRefreshTimer) window.clearTimeout(autoRefreshTimer)
  if (!autoRefreshEnabled.value) return
  autoRefreshTimer = window.setTimeout(async () => {
    if (activeLogView.value === 'runtime') {
      await fetchRuntimeLogs()
    } else {
      await fetchLogs()
    }
    scheduleAutoRefresh()
  }, 8000)
}

function scheduleFilterFetch() {
  if (activeLogView.value !== 'system') return
  if (isApplyingRouteQuery) return
  if (filterFetchTimer) window.clearTimeout(filterFetchTimer)
  filterFetchTimer = window.setTimeout(() => {
    if (currentPage.value === 1) {
      void fetchLogs()
      return
    }
    currentPage.value = 1
  }, 250)
}

function toggleAutoRefresh() {
  autoRefreshEnabled.value = !autoRefreshEnabled.value
  scheduleAutoRefresh()
}

watch(
  () => [
    filters.type,
    filters.status,
    filters.endpoint,
    filters.model,
    filters.account,
    filters.conversationId,
    filters.search,
    filters.startDate,
    filters.endDate,
    filters.limit,
  ],
  scheduleFilterFetch,
)

watch(currentPage, () => {
  if (activeLogView.value === 'system') void fetchLogs()
})

watch(autoRefreshEnabled, scheduleAutoRefresh)

watch(activeLogView, () => {
  scheduleAutoRefresh()
})

watch(
  () => [
    runtimeFilters.level,
    runtimeFilters.source,
    runtimeFilters.search,
    runtimeFilters.limit,
  ],
  () => {
    if (activeLogView.value !== 'runtime') return
    if (filterFetchTimer) window.clearTimeout(filterFetchTimer)
    filterFetchTimer = window.setTimeout(() => {
      void fetchRuntimeLogs()
    }, 250)
  },
)

watch(
  () => route.query,
  () => {
    applyRouteQuery()
    void fetchLogs()
  },
  { deep: true },
)

onMounted(() => {
  applyRouteQuery()
  void fetchLogs()
})

onBeforeUnmount(() => {
  if (autoRefreshTimer) window.clearTimeout(autoRefreshTimer)
  if (filterFetchTimer) window.clearTimeout(filterFetchTimer)
})
</script>

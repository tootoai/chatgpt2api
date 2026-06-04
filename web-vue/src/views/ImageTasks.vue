<template>
  <div class="space-y-6">
    <section class="grid grid-cols-2 gap-3 md:grid-cols-4">
      <div
        v-for="item in taskStats"
        :key="item.label"
        class="ui-card-sm"
      >
        <div class="text-[11px] text-muted-foreground">{{ item.label }}</div>
        <div class="mt-1 text-xl font-semibold text-foreground">{{ item.value }}</div>
      </div>
    </section>

    <section class="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
      <div class="ui-panel space-y-5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p class="ui-section-title">图片任务</p>
            <p class="mt-1 text-xs text-muted-foreground">{{ submitMode === 'generate' ? '文生图' : '图生图' }}</p>
          </div>
          <SegmentedTabs
            v-model="submitMode"
            :options="modeOptions"
            aria-label="图片任务模式"
          />
        </div>

        <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div class="space-y-1.5">
            <label class="text-xs text-muted-foreground">模型</label>
            <SelectMenu
              v-model="form.model"
              :options="modelSelectOptions"
              aria-label="图片模型"
              class="w-full"
            />
          </div>
          <div class="space-y-1.5">
            <label class="text-xs text-muted-foreground">尺寸</label>
            <SelectMenu
              v-model="form.size"
              :options="IMAGE_SIZE_OPTIONS"
              aria-label="图片尺寸"
              class="w-full"
            />
          </div>
          <div class="space-y-1.5">
            <label class="text-xs text-muted-foreground">质量</label>
            <SelectMenu
              v-model="form.quality"
              :options="IMAGE_QUALITY_OPTIONS"
              aria-label="图片质量"
              class="w-full"
            />
          </div>
        </div>

        <div class="space-y-1.5">
          <label class="text-xs text-muted-foreground">Prompt</label>
          <textarea
            v-model.trim="form.prompt"
            class="task-textarea"
            rows="8"
            placeholder="输入图片提示词"
          ></textarea>
        </div>

        <div v-if="submitMode === 'edit'" class="space-y-3">
          <div class="space-y-1.5">
            <label class="text-xs text-muted-foreground">参考图 URL</label>
            <textarea
              v-model.trim="imageUrlsInput"
              class="task-textarea min-h-[5rem]"
              rows="3"
              placeholder="每行一个图片 URL，也可以粘贴 data:image"
            ></textarea>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              :disabled="isSubmitting"
              @click="openFilePicker"
            >
              选择图片
            </Button>
            <Button
              v-if="selectedFiles.length"
              size="sm"
              variant="outline"
              :disabled="isSubmitting"
              @click="clearFiles"
            >
              清空文件
            </Button>
            <span class="text-xs text-muted-foreground">已选 {{ selectedFiles.length }} 个文件</span>
            <input
              ref="fileInputRef"
              type="file"
              accept="image/*"
              multiple
              class="hidden"
              @change="handleFileChange"
            />
          </div>

          <div v-if="selectedFiles.length" class="flex flex-wrap gap-2">
            <button
              v-for="(file, index) in selectedFiles"
              :key="`${file.name}-${file.size}-${index}`"
              class="task-file-chip"
              type="button"
              @click="removeFile(index)"
            >
              <span class="truncate">{{ file.name }}</span>
              <span class="text-muted-foreground">{{ formatSize(file.size) }}</span>
            </button>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="primary"
            root-class="min-w-24 justify-center"
            :disabled="isSubmitting || !form.prompt"
            @click="submitTask"
          >
            {{ isSubmitting ? '提交中...' : '提交任务' }}
          </Button>
          <Button
            size="sm"
            variant="outline"
            :disabled="isFetching"
            @click="refreshTasks"
          >
            刷新任务
          </Button>
        </div>
      </div>

      <div class="ui-panel space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p class="ui-section-title">任务队列</p>
            <p class="mt-1 text-xs text-muted-foreground">{{ pollingLabel }}</p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              :variant="autoPoll ? 'primary' : 'outline'"
              @click="toggleAutoPoll"
            >
              {{ autoPoll ? '自动轮询 3s' : '自动轮询已关' }}
            </Button>
            <Button
              size="sm"
              variant="outline"
              :disabled="!tasks.length"
              @click="clearLocalTasks"
            >
              清空本地
            </Button>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div class="task-stage-card">
            <span class="task-stage-dot bg-sky-500"></span>
            <span>上游等待 {{ stageCounts.upstream }}</span>
          </div>
          <div class="task-stage-card">
            <span class="task-stage-dot bg-emerald-500"></span>
            <span>结果入库 {{ stageCounts.upload }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="ui-panel !p-0 overflow-hidden">
      <div class="task-list-toolbar">
        <div>
          <p class="ui-section-kicker">最近任务</p>
          <p class="mt-1 text-xs text-muted-foreground">显示 {{ tasks.length }} 条</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <Button
            size="xs"
            variant="outline"
            :disabled="isFetching"
            @click="refreshTasks"
          >
            {{ isFetching ? '刷新中...' : '刷新' }}
          </Button>
        </div>
      </div>

      <div v-if="isFetching && !hasLoadedOnce" class="task-empty-state">
        <div class="task-loading-bar"></div>
      </div>

      <div v-else-if="!tasks.length" class="task-empty-state">
        <p class="text-sm text-muted-foreground">暂无图片任务</p>
      </div>

      <div v-else class="divide-y divide-border">
        <article
          v-for="task in tasks"
          :key="task.id"
          class="task-row"
        >
          <div class="flex min-w-0 flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="task-status" :class="statusClass(task.status)">
                  {{ statusLabel(task.status) }}
                </span>
                <span class="ui-chip text-[11px]">{{ task.mode === 'edit' ? '图生图' : '文生图' }}</span>
                <span class="ui-chip text-[11px]">{{ task.model }}</span>
                <span v-if="task.size" class="ui-chip text-[11px]">{{ task.size }}</span>
                <span v-if="task.quality" class="ui-chip text-[11px]">quality={{ task.quality }}</span>
              </div>

              <div class="mt-2 min-w-0 font-mono text-[11px] text-muted-foreground">
                <button class="task-id" type="button" @click="copyText(task.id)">
                  {{ task.id }}
                </button>
              </div>

              <div class="mt-3 grid grid-cols-1 gap-2 text-xs text-muted-foreground md:grid-cols-4">
                <span>阶段：<b class="font-medium text-foreground">{{ stageLabel(task.stage || task.progress || task.status) }}</b></span>
                <span>创建：{{ task.created_at || '-' }}</span>
                <span>更新：{{ task.updated_at || '-' }}</span>
                <span>耗时：{{ formatDuration(task.duration_ms, task.elapsed_secs) }}</span>
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <Button
                v-if="task.status === 'error'"
                size="xs"
                variant="outline"
                :disabled="resumingTaskId === task.id"
                @click="resumeTask(task)"
              >
                {{ resumingTaskId === task.id ? '恢复中...' : '恢复轮询' }}
              </Button>
              <Button size="xs" variant="outline" @click="copyTaskError(task)">
                复制诊断
              </Button>
            </div>
          </div>

          <div v-if="task.data?.length" class="task-assets">
            <a
              v-for="(asset, index) in task.data"
              :key="`${task.id}-asset-${index}`"
              :href="assetUrl(asset)"
              target="_blank"
              rel="noopener noreferrer"
              class="task-asset"
            >
              <img
                v-if="assetUrl(asset)"
                :src="assetUrl(asset)"
                :alt="`task-${task.id}-${index}`"
                loading="lazy"
              />
              <span v-else>无图片 URL</span>
            </a>
          </div>

          <div v-if="task.status === 'error'" class="task-error-panel">
            <div class="grid grid-cols-1 gap-2 text-xs md:grid-cols-2 xl:grid-cols-4">
              <div>
                <span class="text-muted-foreground">error_code</span>
                <p class="mt-1 break-all font-mono text-foreground">{{ task.error_code || '-' }}</p>
              </div>
              <div>
                <span class="text-muted-foreground">stage</span>
                <p class="mt-1 break-all font-mono text-foreground">{{ task.stage || '-' }}</p>
              </div>
              <div>
                <span class="text-muted-foreground">conversation_id</span>
                <p class="mt-1 break-all font-mono text-foreground">{{ task.conversation_id || '-' }}</p>
              </div>
              <div>
                <span class="text-muted-foreground">tool_invoked</span>
                <p class="mt-1 font-mono text-foreground">{{ String(task.tool_invoked ?? '-') }}</p>
              </div>
            </div>

            <p v-if="primaryMessage(task)" class="mt-3 whitespace-pre-wrap text-sm text-foreground">
              {{ primaryMessage(task) }}
            </p>
            <pre
              v-if="task.raw_upstream_message"
              class="scrollbar-slim mt-3 max-h-52 overflow-auto rounded-xl border border-border bg-background p-3 text-[11px] leading-relaxed text-muted-foreground"
            >{{ task.raw_upstream_message }}</pre>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Button, SegmentedTabs, SelectMenu } from 'nanocat-ui'
import {
  DEFAULT_IMAGE_MODEL,
  DEFAULT_IMAGE_QUALITY,
  DEFAULT_IMAGE_SIZE,
  IMAGE_QUALITY_OPTIONS,
  IMAGE_SIZE_OPTIONS,
  imageAssetUrl,
  imageTasksApi,
  isImageTaskTerminal,
  taskPrimaryMessage,
  type ImageTask,
  type ImageTaskAsset,
  type ImageTaskStatus,
} from '@/api/imageTasks'
import { resolveImageModels } from '@/config/modelCatalog'
import { useSettingsStore } from '@/stores/settings'
import { useToast } from '@/composables/useToast'

const LOCAL_TASK_IDS_KEY = 'chatgpt2api.imageTaskIds'

const settingsStore = useSettingsStore()
const { settings } = storeToRefs(settingsStore)
const toast = useToast()

const submitMode = ref<'generate' | 'edit'>('generate')
const form = reactive({
  prompt: '',
  model: DEFAULT_IMAGE_MODEL,
  size: DEFAULT_IMAGE_SIZE,
  quality: DEFAULT_IMAGE_QUALITY,
})
const imageUrlsInput = ref('')
const selectedFiles = ref<File[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)
const tasks = ref<ImageTask[]>([])
const isSubmitting = ref(false)
const isFetching = ref(false)
const hasLoadedOnce = ref(false)
const autoPoll = ref(true)
const resumingTaskId = ref('')

let pollTimer: number | null = null

const modeOptions = [
  { label: '文生图', value: 'generate' },
  { label: '图生图', value: 'edit' },
]

const modelSelectOptions = computed(() => {
  const values = resolveImageModels(settings.value)
  const withDefault = values.includes(form.model) ? values : [form.model, ...values]
  return withDefault.map((model) => ({ label: model, value: model }))
})

const unfinishedTasks = computed(() => tasks.value.filter((task) => !isImageTaskTerminal(task)))

const taskStats = computed(() => {
  const total = tasks.value.length
  const running = tasks.value.filter((task) => task.status === 'running').length
  const queued = tasks.value.filter((task) => task.status === 'queued').length
  const success = tasks.value.filter((task) => task.status === 'success').length
  const error = tasks.value.filter((task) => task.status === 'error').length
  return [
    { label: '总任务', value: total },
    { label: '排队/运行', value: queued + running },
    { label: '成功', value: success },
    { label: '失败', value: error },
  ]
})

const stageCounts = computed(() => ({
  upstream: tasks.value.filter((task) => ['upstream_sse', 'running', 'account_acquire'].includes(task.stage || '')).length,
  upload: tasks.value.filter((task) => ['result_download', 'upload'].includes(task.stage || '')).length,
}))

const pollingLabel = computed(() => {
  if (!autoPoll.value) return '轮询暂停'
  if (!unfinishedTasks.value.length) return '没有运行中的任务'
  return `${unfinishedTasks.value.length} 个任务轮询中`
})

function storedTaskIds() {
  try {
    const raw = localStorage.getItem(LOCAL_TASK_IDS_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.map((id) => String(id)).filter(Boolean) : []
  } catch {
    return []
  }
}

function saveTaskIds() {
  const ids = tasks.value.map((task) => task.id).filter(Boolean).slice(0, 80)
  localStorage.setItem(LOCAL_TASK_IDS_KEY, JSON.stringify(ids))
}

function sortTasks(items: ImageTask[]) {
  return [...items].sort((a, b) => String(b.updated_at || b.created_at || '').localeCompare(String(a.updated_at || a.created_at || '')))
}

function mergeTasks(nextTasks: ImageTask[]) {
  const map = new Map(tasks.value.map((task) => [task.id, task]))
  nextTasks.forEach((task) => {
    if (task.id) map.set(task.id, task)
  })
  tasks.value = sortTasks(Array.from(map.values()))
  saveTaskIds()
}

async function refreshTasks() {
  if (isFetching.value) return
  isFetching.value = true
  try {
    const response = await imageTasksApi.list()
    tasks.value = sortTasks(response.items)
    if (!tasks.value.length) {
      const ids = storedTaskIds()
      if (ids.length) {
        const stored = await imageTasksApi.list(ids)
        tasks.value = sortTasks(stored.items)
      }
    }
    saveTaskIds()
  } catch (error: any) {
    toast.error(error.message || '刷新图片任务失败')
  } finally {
    isFetching.value = false
    hasLoadedOnce.value = true
    schedulePoll()
  }
}

async function pollUnfinishedTasks() {
  if (!autoPoll.value || !unfinishedTasks.value.length || isFetching.value) return
  isFetching.value = true
  try {
    const response = await imageTasksApi.list(unfinishedTasks.value.map((task) => task.id))
    mergeTasks(response.items)
  } catch (error: any) {
    toast.error(error.message || '轮询图片任务失败')
  } finally {
    isFetching.value = false
    schedulePoll()
  }
}

function schedulePoll() {
  if (pollTimer) {
    window.clearTimeout(pollTimer)
    pollTimer = null
  }
  if (!autoPoll.value || !unfinishedTasks.value.length) return
  pollTimer = window.setTimeout(() => {
    void pollUnfinishedTasks()
  }, 3000)
}

function parseImageUrls() {
  return imageUrlsInput.value
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function openFilePicker() {
  fileInputRef.value?.click()
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFiles.value = Array.from(input.files || [])
}

function removeFile(index: number) {
  selectedFiles.value = selectedFiles.value.filter((_file, fileIndex) => fileIndex !== index)
}

function clearFiles() {
  selectedFiles.value = []
  if (fileInputRef.value) fileInputRef.value.value = ''
}

async function submitTask() {
  if (!form.prompt.trim() || isSubmitting.value) return

  const imageUrls = parseImageUrls()
  if (submitMode.value === 'edit' && !imageUrls.length && !selectedFiles.value.length) {
    toast.warning('图生图需要至少一个参考图')
    return
  }

  isSubmitting.value = true
  try {
    const baseInput = {
      prompt: form.prompt.trim(),
      model: form.model || DEFAULT_IMAGE_MODEL,
      size: form.size,
      quality: form.quality,
    }
    const task = submitMode.value === 'edit'
      ? await imageTasksApi.createEdit({ ...baseInput, files: selectedFiles.value, imageUrls })
      : await imageTasksApi.createGeneration(baseInput)
    mergeTasks([task])
    toast.success('图片任务已提交')
    schedulePoll()
  } catch (error: any) {
    toast.error(error.message || '提交图片任务失败')
  } finally {
    isSubmitting.value = false
  }
}

async function resumeTask(task: ImageTask) {
  if (resumingTaskId.value) return
  resumingTaskId.value = task.id
  try {
    const next = await imageTasksApi.resumePoll(task.id, 30)
    mergeTasks([next])
    toast.success('已恢复轮询')
  } catch (error: any) {
    toast.error(error.message || '恢复轮询失败')
  } finally {
    resumingTaskId.value = ''
    schedulePoll()
  }
}

function clearLocalTasks() {
  tasks.value = []
  localStorage.removeItem(LOCAL_TASK_IDS_KEY)
  schedulePoll()
}

function toggleAutoPoll() {
  autoPoll.value = !autoPoll.value
  schedulePoll()
}

function assetUrl(asset: ImageTaskAsset) {
  return imageAssetUrl(asset)
}

function primaryMessage(task: ImageTask) {
  return taskPrimaryMessage(task)
}

function statusLabel(status: ImageTaskStatus) {
  const labels: Record<ImageTaskStatus, string> = {
    queued: '排队',
    running: '运行',
    success: '成功',
    error: '失败',
  }
  return labels[status] || status
}

function statusClass(status: ImageTaskStatus) {
  return {
    queued: 'task-status--queued',
    running: 'task-status--running',
    success: 'task-status--success',
    error: 'task-status--error',
  }[status]
}

function stageLabel(stage: string | undefined) {
  const labels: Record<string, string> = {
    queued: '排队中',
    running: '运行中',
    account_acquire: '获取账号',
    upstream_sse: '等待上游',
    result_download: '下载结果',
    upload: '上传存储',
    completed: '已完成',
    success: '已完成',
    error: '失败',
  }
  const key = String(stage || '').trim()
  return labels[key] || key || '-'
}

function formatDuration(durationMs?: number, elapsedSecs?: number) {
  if (Number.isFinite(durationMs) && Number(durationMs) > 0) {
    return `${(Number(durationMs) / 1000).toFixed(1)}s`
  }
  if (Number.isFinite(elapsedSecs) && Number(elapsedSecs) >= 0) {
    return `${Number(elapsedSecs).toFixed(1)}s`
  }
  return '-'
}

function formatSize(size: number) {
  if (!Number.isFinite(size) || size <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = size
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}

async function copyText(value: string) {
  if (!value) return
  await navigator.clipboard.writeText(value)
  toast.success('已复制')
}

async function copyTaskError(task: ImageTask) {
  const payload = {
    id: task.id,
    status: task.status,
    stage: task.stage,
    error_code: task.error_code,
    reason: task.reason,
    error: task.error,
    conversation_id: task.conversation_id,
    raw_upstream_message: task.raw_upstream_message,
    diagnosis: task.diagnosis,
  }
  await copyText(JSON.stringify(payload, null, 2))
}

watch(unfinishedTasks, schedulePoll)

onMounted(() => {
  if (!settings.value && !settingsStore.isLoading) {
    void settingsStore.loadSettings()
  }
  void refreshTasks()
})

onBeforeUnmount(() => {
  if (pollTimer) {
    window.clearTimeout(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped>
.task-textarea {
  width: 100%;
  min-height: 9rem;
  resize: vertical;
  border-radius: 14px;
  border: 1px solid hsl(var(--border));
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  padding: 0.75rem 0.875rem;
  font-size: 0.875rem;
  line-height: 1.6;
  outline: none;
}

.task-textarea:focus {
  border-color: hsl(var(--primary));
  box-shadow: 0 0 0 3px hsl(var(--primary) / 0.12);
}

.task-file-chip {
  display: inline-flex;
  max-width: 15rem;
  align-items: center;
  gap: 0.5rem;
  border-radius: 999px;
  border: 1px solid hsl(var(--border));
  background: hsl(var(--secondary) / 0.55);
  padding: 0.35rem 0.65rem;
  font-size: 0.75rem;
  color: hsl(var(--foreground));
}

.task-stage-card {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border-radius: 14px;
  border: 1px solid hsl(var(--border));
  background: hsl(var(--background));
  padding: 0.75rem;
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
}

.task-stage-dot {
  width: 0.55rem;
  height: 0.55rem;
  flex: 0 0 auto;
  border-radius: 999px;
}

.task-list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border-bottom: 1px solid hsl(var(--border));
  padding: 1rem 1.25rem;
}

.task-empty-state {
  display: flex;
  min-height: 13rem;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.task-loading-bar {
  width: min(18rem, 80vw);
  height: 0.45rem;
  overflow: hidden;
  border-radius: 999px;
  background: hsl(var(--secondary));
}

.task-loading-bar::before {
  content: "";
  display: block;
  width: 45%;
  height: 100%;
  border-radius: inherit;
  background: hsl(var(--primary));
  animation: task-loading 1.1s ease-in-out infinite;
}

.task-row {
  padding: 1.25rem;
}

.task-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 0.25rem 0.65rem;
  font-size: 0.75rem;
  font-weight: 600;
}

.task-status--queued {
  background: #f3f4f6;
  color: #4b5563;
}

.task-status--running {
  background: #dbeafe;
  color: #1d4ed8;
}

.task-status--success {
  background: #d1fae5;
  color: #047857;
}

.task-status--error {
  background: #fee2e2;
  color: #b91c1c;
}

.task-id {
  max-width: 100%;
  overflow-wrap: anywhere;
  text-align: left;
  transition: color 0.15s ease;
}

.task-id:hover {
  color: hsl(var(--foreground));
}

.task-assets {
  margin-top: 1rem;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
  gap: 0.75rem;
}

.task-asset {
  display: flex;
  aspect-ratio: 1 / 1;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 14px;
  border: 1px solid hsl(var(--border));
  background: hsl(var(--background));
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.task-asset img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.task-error-panel {
  margin-top: 1rem;
  border-radius: 14px;
  border: 1px solid rgb(254 202 202);
  background: rgb(254 242 242);
  padding: 1rem;
}

@keyframes task-loading {
  0% {
    transform: translateX(-110%);
  }
  100% {
    transform: translateX(230%);
  }
}
</style>

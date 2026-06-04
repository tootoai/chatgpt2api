<template>
  <div class="space-y-6">
    <section class="ui-panel space-y-5">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="min-w-0">
          <p class="ui-section-title">图片画廊</p>
          <p class="mt-1 text-xs text-muted-foreground">{{ paginationSummary }}</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="outline" :disabled="isLoading" @click="refreshAll">
            {{ isLoading ? '刷新中...' : '刷新' }}
          </Button>
          <Button
            size="sm"
            variant="primary"
            root-class="min-w-20 justify-center"
            :disabled="isSaving"
            @click="handleSaveRetentionDays"
          >
            {{ isSaving ? '保存中...' : '保存设置' }}
          </Button>
        </div>
      </div>

      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <div class="gallery-stat">
          <Icon icon="lucide:image" class="gallery-stat-icon text-cyan-600" />
          <div>
            <p class="gallery-stat-label">当前图片</p>
            <p class="gallery-stat-value">{{ totalItems }}</p>
          </div>
        </div>
        <div class="gallery-stat">
          <Icon icon="lucide:database" class="gallery-stat-icon text-emerald-600" />
          <div>
            <p class="gallery-stat-label">当前占用</p>
            <p class="gallery-stat-value">{{ formatSize(totalSize) }}</p>
          </div>
        </div>
        <div class="gallery-stat">
          <Icon icon="lucide:hard-drive" class="gallery-stat-icon text-amber-600" />
          <div>
            <p class="gallery-stat-label">磁盘剩余</p>
            <p class="gallery-stat-value">{{ storageStats ? `${storageStats.disk_free_mb} MB` : '-' }}</p>
          </div>
        </div>
        <div class="gallery-stat">
          <Icon icon="lucide:archive" class="gallery-stat-icon text-violet-600" />
          <div>
            <p class="gallery-stat-label">图库总量</p>
            <p class="gallery-stat-value">{{ storageStats ? `${storageStats.image_count}` : counts.all }}</p>
          </div>
        </div>
        <div class="gallery-stat">
          <Icon icon="lucide:check-square" class="gallery-stat-icon text-rose-600" />
          <div>
            <p class="gallery-stat-label">已选择</p>
            <p class="gallery-stat-value">{{ selectedCount }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="ui-panel space-y-4">
      <div class="grid gap-3 xl:grid-cols-[1.2fr_12rem_9rem_9rem_7rem]">
        <Input
          :model-value="searchQuery"
          type="text"
          placeholder="搜索文件名、路径、标签"
          block
          @update:model-value="searchQuery = $event"
        />
        <SelectMenu
          v-model="tagFilter"
          :options="tagOptions"
          placeholder="全部标签"
          selected-indicator="none"
        />
        <Input
          :model-value="startDate"
          type="date"
          root-class="min-w-36"
          @update:model-value="startDate = $event"
        />
        <Input
          :model-value="endDate"
          type="date"
          root-class="min-w-36"
          @update:model-value="endDate = $event"
        />
        <SelectMenu
          v-model="pageSize"
          :options="pageSizeOptions"
          selected-indicator="none"
          aria-label="每页数量"
        />
      </div>

      <div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div class="flex min-w-0 flex-wrap items-center gap-2">
          <SegmentedTabs
            v-model="activeFilter"
            :options="filterOptions"
            aria-label="图片类型筛选"
          />
          <Button size="xs" variant="outline" @click="resetFilters">重置筛选</Button>
        </div>

        <div class="gallery-setting-row">
          <span class="text-xs text-muted-foreground">保留</span>
          <Input
            :model-value="retentionDaysField"
            type="number"
            root-class="w-16 text-center"
            @update:model-value="updateRetentionDaysField"
            @keyup.enter="handleSaveRetentionDays"
          />
          <span class="text-xs text-muted-foreground">天</span>
          <HelpTip text="后端按图片保留天数自动清理，最小值为 1 天。" />
          <Button size="xs" variant="outline" :disabled="batchBusy" @click="handleCleanupExpired">
            清理过期
          </Button>
        </div>
      </div>
    </section>

    <section class="ui-panel space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="min-w-0">
          <p class="ui-section-kicker">存储维护</p>
          <div class="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
            <span class="ui-chip">图库占用 {{ storageStats ? formatSize(storageStats.image_size_bytes) : '-' }}</span>
            <span class="ui-chip">磁盘使用 {{ storageUsagePercent }}%</span>
            <span v-if="cleanupPreviewText" class="ui-chip text-amber-700">{{ cleanupPreviewText }}</span>
          </div>
        </div>
        <div class="gallery-storage-actions">
          <Button size="xs" variant="outline" :disabled="storageBusy" @click="handleCompressStorage">
            {{ storageBusy === 'compress' ? '压缩中...' : '压缩图片' }}
          </Button>
          <span class="text-xs text-muted-foreground">目标剩余</span>
          <Input
            :model-value="targetFreeMbField"
            type="number"
            root-class="w-20 text-center"
            @update:model-value="targetFreeMbField = $event"
          />
          <span class="text-xs text-muted-foreground">MB</span>
          <Button size="xs" variant="outline" :disabled="Boolean(storageBusy)" @click="handleCleanupToTarget(true)">
            预估清理
          </Button>
          <Button size="xs" variant="outline" :disabled="Boolean(storageBusy)" @click="handleCleanupToTarget(false)">
            执行清理
          </Button>
        </div>
      </div>
      <div class="h-2 overflow-hidden rounded-full bg-muted">
        <div class="h-full rounded-full bg-primary transition-all" :style="{ width: `${storageUsagePercent}%` }"></div>
      </div>
    </section>

    <section class="ui-panel !p-0 overflow-hidden">
      <div class="gallery-content-toolbar">
        <div class="flex min-w-0 items-center gap-3">
          <Checkbox
            :model-value="allVisibleSelected"
            :disabled="files.length === 0 || isLoading"
            @update:model-value="toggleSelectAllVisible"
          />
          <div class="min-w-0">
            <p class="ui-section-kicker">当前视图</p>
            <p class="mt-1 text-xs text-muted-foreground">{{ paginationSummary }}</p>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <Button
            size="xs"
            variant="outline"
            :disabled="selectedCount === 0 || batchBusy"
            @click="handleBatchDownload"
          >
            批量下载
          </Button>
          <Button
            size="xs"
            variant="outline"
            :disabled="selectedCount === 0 || batchBusy"
            @click="handleDeleteSelected"
          >
            批量删除
          </Button>
          <Button
            size="xs"
            variant="ghost"
            :disabled="selectedCount === 0 || batchBusy"
            @click="clearSelection"
          >
            取消选择
          </Button>
        </div>
      </div>

      <div v-if="!hasLoadedOnce && files.length === 0" class="gallery-state-wrap">
        <div class="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
      </div>

      <div v-else-if="files.length === 0" class="gallery-state-wrap">
        <Icon icon="lucide:image-off" class="h-12 w-12 text-muted-foreground/40" />
        <EmptyState
          plain
          :title="galleryLoadError ? '图片画廊加载失败' : '暂无图片'"
          :description="galleryLoadError || '换个筛选条件或刷新后再看。'"
        />
      </div>

      <div v-else class="space-y-4 p-4 lg:p-5">
        <div class="image-grid">
          <article
            v-for="file in files"
            :key="file.path"
            class="gallery-item"
            :class="{ 'is-selected': isSelected(file.path), 'is-expired': file.expired }"
          >
            <div class="media-wrapper" @click="openPreview(file)">
              <img
                v-if="canPreviewFile(file)"
                :src="getFileUrl(file.thumbnail_url || file.url)"
                :alt="file.filename"
                loading="lazy"
                class="media-content"
                @error="handleImageError($event, file.path)"
              />
              <div v-else class="media-fallback">
                <Icon icon="lucide:image-off" class="h-8 w-8" />
                <span>无法预览</span>
              </div>

              <div class="media-topline">
                <Checkbox
                  :model-value="isSelected(file.path)"
                  @click.stop
                  @update:model-value="(checked) => toggleSelect(file.path, checked)"
                />
                <span v-if="file.expired" class="media-badge danger">已过期</span>
                <span v-else class="media-badge">{{ storageLabel(file) }}</span>
              </div>

              <div class="media-overlay">
                <button class="overlay-btn" title="复制链接" @click.stop="copyFileLink(file)">
                  <Icon :icon="copiedFileKey === file.path ? 'lucide:check' : 'lucide:copy'" />
                </button>
                <button class="overlay-btn" title="编辑标签" @click.stop="openTagEditor(file)">
                  <Icon icon="lucide:tag" />
                </button>
                <button class="overlay-btn" title="下载" @click.stop="downloadFile(file)">
                  <Icon icon="lucide:download" />
                </button>
                <button class="overlay-btn danger" title="删除" @click.stop="handleDelete(file)">
                  <Icon icon="lucide:trash-2" />
                </button>
              </div>
            </div>

            <div class="file-info">
              <p class="file-name" :title="file.path">{{ file.filename }}</p>
              <div class="file-meta">
                <span>{{ formatSize(file.size) }}</span>
                <span v-if="formatDimensions(file)">{{ formatDimensions(file) }}</span>
                <Tooltip
                  v-if="file.expires_in_seconds !== null && !file.expired"
                  :text="'将在 ' + formatTimeRemaining(file.expires_in_seconds) + ' 后自动删除'"
                >
                  <span class="file-countdown">{{ formatTimeRemaining(file.expires_in_seconds) }}</span>
                </Tooltip>
              </div>
              <div v-if="file.tags.length" class="tag-row">
                <button
                  v-for="tag in file.tags"
                  :key="`${file.path}-${tag}`"
                  type="button"
                  class="tag-chip"
                  @click="setTagFilter(tag)"
                >
                  {{ tag }}
                </button>
              </div>
            </div>
          </article>
        </div>

        <div class="gallery-pagination">
          <div class="text-xs text-muted-foreground">
            {{ paginationSummary }}
          </div>
          <div class="flex items-center gap-2">
            <Button
              size="xs"
              variant="outline"
              root-class="min-w-14 justify-center"
              :disabled="currentPage <= 1 || isLoading"
              @click="currentPage -= 1"
            >
              上一页
            </Button>
            <span class="ui-chip">{{ currentPage }} / {{ pageCount }}</span>
            <Button
              size="xs"
              variant="outline"
              root-class="min-w-14 justify-center"
              :disabled="currentPage >= pageCount || isLoading"
              @click="currentPage += 1"
            >
              下一页
            </Button>
          </div>
        </div>
      </div>
    </section>

    <Teleport to="body">
      <div v-if="previewFile" class="lightbox" @click.self="closePreview">
        <div class="lightbox-content">
          <button class="lightbox-close" @click="closePreview">
            <Icon icon="lucide:x" />
          </button>
          <img
            :src="getFileUrl(previewFile.url)"
            :alt="previewFile.filename"
            class="lightbox-media"
          />
          <div class="lightbox-info">
            <span class="max-w-[24rem] truncate" :title="previewFile.path">{{ previewFile.filename }}</span>
            <span>{{ formatSize(previewFile.size) }}</span>
            <span>{{ previewFile.created_at || '-' }}</span>
            <button class="lightbox-btn" @click="downloadFile(previewFile)">
              <Icon icon="lucide:download" />
              下载
            </button>
            <button class="lightbox-btn" @click="copyFileLink(previewFile)">
              <Icon :icon="copiedFileKey === previewFile.path ? 'lucide:check' : 'lucide:copy'" />
              {{ copiedFileKey === previewFile.path ? '已复制' : '复制链接' }}
            </button>
            <button class="lightbox-btn" @click="openTagEditor(previewFile)">
              <Icon icon="lucide:tag" />
              标签
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="tagEditorFile" class="fixed inset-0 z-[150] overflow-y-auto bg-black/40 px-3 py-4" @click.self="closeTagEditor">
        <div class="mx-auto flex min-h-full w-full max-w-2xl items-center">
          <div class="w-full rounded-xl border border-border bg-background shadow-xl">
            <div class="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
              <div class="min-w-0">
                <p class="ui-section-title">编辑标签</p>
                <p class="mt-1 truncate text-xs text-muted-foreground">{{ tagEditorFile.path }}</p>
              </div>
              <Button size="xs" variant="outline" root-class="min-w-14 justify-center" :disabled="isTagSaving" @click="closeTagEditor">
                关闭
              </Button>
            </div>

            <div class="space-y-4 px-5 py-4">
              <div class="grid gap-4 md:grid-cols-[10rem_1fr]">
                <img
                  :src="getFileUrl(tagEditorFile.thumbnail_url || tagEditorFile.url)"
                  :alt="tagEditorFile.filename"
                  class="tag-editor-thumb"
                />
                <div class="space-y-3">
                  <Input
                    :model-value="tagDraft"
                    type="text"
                    placeholder="多个标签用逗号或空格分隔"
                    block
                    @update:model-value="tagDraft = $event"
                    @keyup.enter="saveTagEditor"
                  />
                  <div class="flex flex-wrap gap-2">
                    <button
                      v-for="tag in allTags"
                      :key="tag"
                      type="button"
                      class="tag-picker"
                      :class="{ active: draftTags.includes(tag) }"
                      @click="toggleDraftTag(tag)"
                    >
                      {{ tag }}
                    </button>
                    <span v-if="allTags.length === 0" class="text-xs text-muted-foreground">暂无已有标签</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="flex flex-wrap items-center justify-end gap-2 border-t border-border px-5 py-4">
              <Button size="sm" variant="outline" :disabled="isTagSaving" @click="tagDraft = ''">
                清空
              </Button>
              <Button size="sm" variant="primary" :disabled="isTagSaving" @click="saveTagEditor">
                {{ isTagSaving ? '保存中...' : '保存标签' }}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <transition name="gallery-bulk-bar">
        <div v-if="selectedCount > 0" class="fixed inset-x-0 bottom-5 z-[130] flex justify-center px-4">
          <div class="gallery-bulk-bar">
            <p class="text-sm font-semibold text-foreground">已选择 {{ selectedCount }} 张图片</p>
            <div class="flex flex-wrap items-center gap-2">
              <Button size="xs" variant="outline" :disabled="batchBusy" @click="handleBatchDownload">下载 zip</Button>
              <Button size="xs" variant="outline" :disabled="batchBusy" @click="handleDeleteSelected">删除</Button>
              <Button size="xs" variant="ghost" :disabled="batchBusy" @click="clearSelection">取消</Button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <ConfirmDialog
      :open="confirmDialog.open.value"
      :title="confirmDialog.title.value"
      :message="confirmDialog.message.value"
      :confirm-text="confirmDialog.confirmText.value"
      :cancel-text="confirmDialog.cancelText.value"
      @confirm="confirmDialog.confirm"
      @cancel="confirmDialog.cancel"
    />
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { computed, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { galleryApi, type GalleryFile, type GalleryMediaType, type ImageCleanupTargetResult, type ImageStorageStats } from '@/api/gallery'
import { settingsApi } from '@/api/settings'
import { Button, Checkbox, ConfirmDialog, EmptyState, HelpTip, Input, SegmentedTabs, SelectMenu, Tooltip } from 'nanocat-ui'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useToast } from '@/composables/useToast'

const apiBaseUrl = import.meta.env.VITE_API_URL || window.location.origin
const toast = useToast()
const confirmDialog = useConfirmDialog()

const files = ref<GalleryFile[]>([])
const totalSize = ref(0)
const totalItems = ref(0)
const lastLoadedAt = ref(0)
const retentionDaysInput = ref(15)
const retentionDaysField = ref('15')
const targetFreeMbField = ref('500')
const isLoading = ref(true)
const hasLoadedOnce = ref(false)
const galleryLoadError = ref('')
const isSaving = ref(false)
const batchBusy = ref(false)
const storageBusy = ref<'' | 'compress' | 'cleanup'>('')
const isTagSaving = ref(false)
const previewFile = ref<GalleryFile | null>(null)
const tagEditorFile = ref<GalleryFile | null>(null)
const tagDraft = ref('')
const copiedFileKey = ref('')
const activeFilter = ref<GalleryMediaType>('all')
const tagFilter = ref('all')
const searchQuery = ref('')
const startDate = ref('')
const endDate = ref('')
const pageSize = ref(24)
const currentPage = ref(1)
const pageCount = ref(1)
const counts = ref({ all: 0, image: 0, video: 0, music: 0 })
const allTags = ref<string[]>([])
const selectedPaths = ref<Set<string>>(new Set())
const brokenImagePaths = ref<Set<string>>(new Set())
const storageStats = ref<ImageStorageStats | null>(null)
const cleanupPreview = ref<ImageCleanupTargetResult | null>(null)

const pageSizeOptions = [
  { label: '24 / 页', value: 24 },
  { label: '48 / 页', value: 48 },
  { label: '96 / 页', value: 96 },
]

const filterOptions = computed(() => {
  const options: Array<{ label: string; value: GalleryMediaType; count?: number }> = [
    { label: '全部', value: 'all', count: counts.value.all },
    { label: '图片', value: 'image', count: counts.value.image },
  ]
  if (counts.value.video > 0 || activeFilter.value === 'video') {
    options.push({ label: '视频', value: 'video', count: counts.value.video })
  }
  if (counts.value.music > 0 || activeFilter.value === 'music') {
    options.push({ label: '音乐', value: 'music', count: counts.value.music })
  }
  return options
})

const tagOptions = computed(() => [
  { label: '全部标签', value: 'all' },
  ...allTags.value.map((tag) => ({ label: tag, value: tag })),
])

const paginationSummary = computed(() => `第 ${currentPage.value} / ${pageCount.value} 页，共 ${totalItems.value} 张`)
const selectedCount = computed(() => selectedPaths.value.size)
const allVisibleSelected = computed(() => files.value.length > 0 && files.value.every((file) => selectedPaths.value.has(file.path)))
const draftTags = computed(() => parseTags(tagDraft.value))
const storageUsagePercent = computed(() => {
  const stats = storageStats.value
  if (!stats?.disk_total_mb) return 0
  return Math.min(100, Math.max(0, Math.round((stats.disk_used_mb / stats.disk_total_mb) * 100)))
})
const cleanupPreviewText = computed(() => {
  const preview = cleanupPreview.value
  if (!preview) return ''
  const prefix = preview.dry_run ? '预计' : '已'
  return `${prefix}删除 ${preview.removed || 0} 张，释放 ${preview.freed_mb ?? 0} MB，剩余 ${preview.current_free_mb} MB`
})

let latestLoadToken = 0
let copyResetTimer: number | null = null
let searchTimer: number | null = null

function getFileUrl(url: string) {
  if (/^https?:\/\//i.test(url)) return url
  return `${apiBaseUrl}${url}`
}

async function loadGallery() {
  const loadToken = ++latestLoadToken
  isLoading.value = true
  galleryLoadError.value = ''
  try {
    const [data, tags, storage] = await Promise.all([
      galleryApi.getFiles({
        page: Number(pageSize.value) ? currentPage.value : 1,
        page_size: Number(pageSize.value),
        media_type: activeFilter.value,
        tag: tagFilter.value,
        search: searchQuery.value,
        start_date: startDate.value,
        end_date: endDate.value,
      }),
      galleryApi.getTags().catch(() => allTags.value),
      galleryApi.getStorage().catch(() => storageStats.value),
    ])
    if (loadToken !== latestLoadToken) return
    files.value = data.files
    totalSize.value = data.total_size
    totalItems.value = data.total
    retentionDaysInput.value = data.retention_days
    counts.value = data.counts
    currentPage.value = data.page
    pageCount.value = Math.max(1, data.page_count)
    allTags.value = tags || []
    storageStats.value = storage || null
    brokenImagePaths.value = new Set()
    lastLoadedAt.value = Date.now()
    pruneSelection()
  } catch (error: any) {
    if (loadToken !== latestLoadToken) return
    galleryLoadError.value = error?.message || '加载图片画廊失败'
    toast.error(galleryLoadError.value, '加载失败')
  } finally {
    if (loadToken === latestLoadToken) {
      isLoading.value = false
      hasLoadedOnce.value = true
    }
  }
}

async function refreshAll() {
  cleanupPreview.value = null
  await loadGallery()
}

function resetAndLoad() {
  cleanupPreview.value = null
  if (currentPage.value !== 1) {
    currentPage.value = 1
    return
  }
  void loadGallery()
}

function resetFilters() {
  activeFilter.value = 'all'
  tagFilter.value = 'all'
  searchQuery.value = ''
  startDate.value = ''
  endDate.value = ''
  resetAndLoad()
}

async function handleSaveRetentionDays() {
  const val = Number(retentionDaysField.value.trim())
  if (val < 1 || !Number.isInteger(val)) {
    toast.warning('图片保留天数只能设置为大于等于 1 的整数。', '输入有误')
    return
  }

  const confirmed = await confirmDialog.ask({
    title: '确认修改保留天数',
    message: `即将把图片保留策略改为 ${val} 天，这会影响后续自动过期判断和清理范围。是否继续？`,
    confirmText: '保存',
    cancelText: '取消',
  })
  if (!confirmed) return

  retentionDaysInput.value = val
  isSaving.value = true
  try {
    const settings = await settingsApi.get()
    settings.image_retention_days = val
    settings.basic.image_expire_hours = val
    await settingsApi.update(settings)
    await loadGallery()
    toast.success('图片保留天数已保存。', '保存成功')
  } catch (error: any) {
    toast.error(error?.message || '保存画廊设置失败', '保存失败')
  } finally {
    isSaving.value = false
  }
}

async function handleCleanupExpired() {
  const confirmed = await confirmDialog.ask({
    title: '确认清理',
    message: '确定要立即清理所有已过期图片吗？此操作不可恢复。',
    confirmText: '立即清理',
    cancelText: '取消',
  })
  if (!confirmed) return

  batchBusy.value = true
  try {
    const result = await galleryApi.cleanupExpired()
    await loadGallery()
    clearSelection()
    toast.success(result.message || '已完成过期图片清理。', '清理完成')
  } catch (error: any) {
    toast.error(error?.message || '清理过期图片失败', '清理失败')
  } finally {
    batchBusy.value = false
  }
}

async function handleDelete(file: GalleryFile) {
  const confirmed = await confirmDialog.ask({
    title: '确认删除',
    message: `确定要删除 ${file.filename} 吗？此操作不可恢复。`,
    confirmText: '删除',
    cancelText: '取消',
  })
  if (!confirmed) return

  batchBusy.value = true
  try {
    await galleryApi.deleteFile(file.path)
    selectedPaths.value.delete(file.path)
    selectedPaths.value = new Set(selectedPaths.value)
    if (previewFile.value?.path === file.path) closePreview()
    if (tagEditorFile.value?.path === file.path) closeTagEditor()
    if (files.value.length === 1 && currentPage.value > 1) {
      currentPage.value -= 1
    } else {
      await loadGallery()
    }
    toast.success(`已删除 ${file.filename}`, '删除成功')
  } catch (error: any) {
    toast.error(error?.message || '删除图片失败', '删除失败')
  } finally {
    batchBusy.value = false
  }
}

async function handleDeleteSelected() {
  const paths = Array.from(selectedPaths.value)
  if (!paths.length) return
  const confirmed = await confirmDialog.ask({
    title: '批量删除',
    message: `确定要删除已选择的 ${paths.length} 张图片吗？此操作不可恢复。`,
    confirmText: '删除',
    cancelText: '取消',
  })
  if (!confirmed) return

  batchBusy.value = true
  try {
    const result = await galleryApi.deleteFiles(paths)
    clearSelection()
    await loadGallery()
    toast.success(`已删除 ${Number(result.removed || 0)} 张图片。`, '删除成功')
  } catch (error: any) {
    toast.error(error?.message || '批量删除失败', '删除失败')
  } finally {
    batchBusy.value = false
  }
}

async function handleBatchDownload() {
  const paths = Array.from(selectedPaths.value)
  if (!paths.length) return
  batchBusy.value = true
  try {
    const blob = await galleryApi.downloadZip(paths)
    saveBlob(blob, `images_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.zip`)
    toast.success(`已打包 ${paths.length} 张图片。`, '下载已开始')
  } catch (error: any) {
    toast.error(error?.message || '批量下载失败', '下载失败')
  } finally {
    batchBusy.value = false
  }
}

function downloadFile(file: GalleryFile) {
  const anchor = document.createElement('a')
  anchor.href = getFileUrl(file.url)
  anchor.download = file.filename
  anchor.target = '_blank'
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
}

function saveBlob(blob: Blob, filename: string) {
  const blobUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = blobUrl
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(blobUrl)
}

async function copyFileLink(file: GalleryFile | null) {
  if (!file) return
  const url = getFileUrl(file.url)
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url)
    } else {
      const input = document.createElement('input')
      input.value = url
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
    }
    copiedFileKey.value = file.path
    if (copyResetTimer !== null) {
      window.clearTimeout(copyResetTimer)
    }
    copyResetTimer = window.setTimeout(() => {
      copiedFileKey.value = ''
      copyResetTimer = null
    }, 1800)
    toast.success('图片链接已复制。', '复制成功')
  } catch {
    copiedFileKey.value = ''
    toast.error('复制链接失败。', '复制失败')
  }
}

function openPreview(file: GalleryFile) {
  previewFile.value = file
}

function closePreview() {
  previewFile.value = null
}

function openTagEditor(file: GalleryFile) {
  tagEditorFile.value = file
  tagDraft.value = file.tags.join(', ')
}

function closeTagEditor() {
  if (isTagSaving.value) return
  tagEditorFile.value = null
  tagDraft.value = ''
}

async function saveTagEditor() {
  const file = tagEditorFile.value
  if (!file) return
  const tags = draftTags.value
  isTagSaving.value = true
  try {
    const result = await galleryApi.updateTags(file.path, tags)
    applyFileTags(file.path, result.tags || tags)
    allTags.value = await galleryApi.getTags()
    if (tagFilter.value !== 'all' && !(result.tags || tags).includes(tagFilter.value)) {
      await loadGallery()
    }
    toast.success('标签已保存。', '保存成功')
    closeTagEditor()
  } catch (error: any) {
    toast.error(error?.message || '保存标签失败', '保存失败')
  } finally {
    isTagSaving.value = false
  }
}

function applyFileTags(path: string, tags: string[]) {
  files.value = files.value.map((file) => (file.path === path ? { ...file, tags } : file))
  if (previewFile.value?.path === path) previewFile.value = { ...previewFile.value, tags }
  if (tagEditorFile.value?.path === path) tagEditorFile.value = { ...tagEditorFile.value, tags }
}

function parseTags(value: string) {
  return Array.from(new Set(value.split(/[,\s，、]+/).map((tag) => tag.trim()).filter(Boolean)))
}

function toggleDraftTag(tag: string) {
  const next = new Set(draftTags.value)
  if (next.has(tag)) {
    next.delete(tag)
  } else {
    next.add(tag)
  }
  tagDraft.value = Array.from(next).join(', ')
}

function setTagFilter(tag: string) {
  tagFilter.value = tag
  resetAndLoad()
}

async function handleCompressStorage() {
  const confirmed = await confirmDialog.ask({
    title: '压缩图片',
    message: '确定要压缩本地图片吗？压缩会尝试减少磁盘占用。',
    confirmText: '开始压缩',
    cancelText: '取消',
  })
  if (!confirmed) return

  storageBusy.value = 'compress'
  try {
    const result = await galleryApi.compressStorage()
    await loadGallery()
    toast.success(`已压缩 ${result.compressed || 0} 张，节省 ${formatSize(result.saved_bytes || 0)}。`, '压缩完成')
  } catch (error: any) {
    toast.error(error?.message || '压缩图片失败', '压缩失败')
  } finally {
    storageBusy.value = ''
  }
}

async function handleCleanupToTarget(dryRun: boolean) {
  const target = Number(targetFreeMbField.value)
  if (!Number.isFinite(target) || target <= 0) {
    toast.warning('目标剩余空间必须是大于 0 的 MB 数。', '输入有误')
    return
  }

  if (dryRun) {
    const confirmed = await confirmDialog.ask({
      title: '确认预估清理',
      message: `即将按目标剩余 ${target} MB 运行一次清理预估。该操作不会删除图片，但会扫描图库并调用后端清理逻辑。是否继续？`,
      confirmText: '开始预估',
      cancelText: '取消',
    })
    if (!confirmed) return
  } else {
    const confirmed = await confirmDialog.ask({
      title: '执行清理',
      message: `确定要删除最旧图片，直到磁盘剩余空间达到 ${target} MB 吗？此操作不可恢复。`,
      confirmText: '执行清理',
      cancelText: '取消',
    })
    if (!confirmed) return
  }

  storageBusy.value = 'cleanup'
  try {
    const result = await galleryApi.cleanupToTarget(target, dryRun)
    cleanupPreview.value = result
    if (!dryRun) {
      clearSelection()
      await loadGallery()
    } else {
      storageStats.value = await galleryApi.getStorage().catch(() => storageStats.value)
    }
    toast.success(cleanupPreviewText.value || '清理任务已完成。', dryRun ? '预估完成' : '清理完成')
  } catch (error: any) {
    toast.error(error?.message || '存储清理失败', '清理失败')
  } finally {
    storageBusy.value = ''
  }
}

function toggleSelect(path: string, checked?: boolean) {
  const next = new Set(selectedPaths.value)
  const shouldSelect = typeof checked === 'boolean' ? checked : !next.has(path)
  if (shouldSelect) {
    next.add(path)
  } else {
    next.delete(path)
  }
  selectedPaths.value = next
}

function toggleSelectAllVisible(checked?: boolean) {
  const next = new Set(selectedPaths.value)
  const shouldSelect = typeof checked === 'boolean' ? checked : !allVisibleSelected.value
  for (const file of files.value) {
    if (shouldSelect) next.add(file.path)
    else next.delete(file.path)
  }
  selectedPaths.value = next
}

function isSelected(path: string) {
  return selectedPaths.value.has(path)
}

function clearSelection() {
  selectedPaths.value = new Set()
}

function pruneSelection() {
  if (selectedPaths.value.size === 0) return
  const loadedPaths = new Set(files.value.map((file) => file.path))
  const next = new Set(Array.from(selectedPaths.value).filter((path) => loadedPaths.has(path)))
  selectedPaths.value = next
}

function formatSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function formatTimeRemaining(seconds: number): string {
  if (seconds <= 0) return '已过期'
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}天 ${h}小时`
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

function formatDimensions(file: GalleryFile): string {
  return file.width && file.height ? `${file.width}x${file.height}` : ''
}

function storageLabel(file: GalleryFile): string {
  if (file.storage === 'both') return '本地+云'
  if (file.storage === 'webdav') return '云端'
  return '本地'
}

function canPreviewFile(file: GalleryFile): boolean {
  return file.size > 128 && !brokenImagePaths.value.has(file.path)
}

function handleImageError(event: Event, path: string) {
  const img = event.target as HTMLImageElement
  img.style.opacity = '0'
  brokenImagePaths.value = new Set([...brokenImagePaths.value, path])
}

function updateRetentionDaysField(value: string) {
  retentionDaysField.value = value
  const parsed = Number(value)
  if (value.trim() !== '' && Number.isFinite(parsed)) {
    retentionDaysInput.value = parsed
  }
}

watch(retentionDaysInput, (value) => {
  const next = String(value)
  if (retentionDaysField.value !== next) {
    retentionDaysField.value = next
  }
}, { immediate: true })

watch([activeFilter, tagFilter, startDate, endDate, pageSize], () => {
  resetAndLoad()
})

watch(searchQuery, () => {
  if (searchTimer !== null) {
    window.clearTimeout(searchTimer)
  }
  searchTimer = window.setTimeout(() => {
    searchTimer = null
    resetAndLoad()
  }, 250)
})

watch(currentPage, () => {
  void loadGallery()
})

onMounted(() => {
  void loadGallery()
})

onActivated(() => {
  if (!lastLoadedAt.value || Date.now() - lastLoadedAt.value > 30000) {
    void loadGallery()
  }
})

onBeforeUnmount(() => {
  if (copyResetTimer !== null) {
    window.clearTimeout(copyResetTimer)
    copyResetTimer = null
  }
  if (searchTimer !== null) {
    window.clearTimeout(searchTimer)
    searchTimer = null
  }
})
</script>

<style scoped>
.gallery-stat {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 64px;
  padding: 12px;
  border: 1px solid hsl(var(--border));
  border-radius: 8px;
  background: hsl(var(--card));
}

.gallery-stat-icon {
  width: 18px;
  height: 18px;
  flex: none;
}

.gallery-stat-label {
  font-size: 11px;
  color: hsl(var(--muted-foreground));
}

.gallery-stat-value {
  margin-top: 2px;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
  color: hsl(var(--foreground));
}

.gallery-setting-row,
.gallery-storage-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.gallery-content-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid hsl(var(--border));
  background: hsl(var(--card));
}

.gallery-state-wrap {
  display: flex;
  min-height: 320px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(172px, 1fr));
  gap: 12px;
}

@media (min-width: 1280px) {
  .image-grid {
    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  }
}

.gallery-item {
  overflow: hidden;
  border: 1px solid hsl(var(--border));
  border-radius: 8px;
  background: hsl(var(--card));
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}

.gallery-item:hover {
  border-color: hsl(var(--primary) / 0.35);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.gallery-item.is-selected {
  border-color: hsl(var(--primary) / 0.7);
  box-shadow: 0 0 0 2px hsl(var(--primary) / 0.16);
}

.gallery-item.is-expired {
  opacity: 0.65;
}

.media-wrapper {
  position: relative;
  aspect-ratio: 1 / 1;
  overflow: hidden;
  cursor: pointer;
  background: hsl(var(--muted));
}

.media-content {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s, opacity 0.2s;
}

.media-fallback {
  display: flex;
  width: 100%;
  height: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: hsl(var(--muted-foreground));
  font-size: 12px;
}

.gallery-item:hover .media-content {
  transform: scale(1.025);
}

.media-topline {
  position: absolute;
  top: 8px;
  left: 8px;
  right: 8px;
  z-index: 2;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  pointer-events: none;
}

.media-topline :deep(*) {
  pointer-events: auto;
}

.media-badge {
  padding: 3px 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: hsl(var(--foreground));
  font-size: 10px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
}

.media-badge.danger {
  background: hsl(0 84.2% 60.2%);
  color: white;
}

.media-overlay {
  position: absolute;
  inset: auto 8px 8px 8px;
  z-index: 2;
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.15s;
}

.media-wrapper:hover .media-overlay,
.gallery-item.is-selected .media-overlay {
  opacity: 1;
}

.overlay-btn {
  display: inline-flex;
  width: 30px;
  height: 30px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: hsl(var(--foreground));
  cursor: pointer;
  transition: background 0.15s, color 0.15s, transform 0.15s;
  backdrop-filter: blur(4px);
}

.overlay-btn:hover {
  transform: translateY(-1px);
  background: hsl(var(--foreground));
  color: hsl(var(--card));
}

.overlay-btn.danger:hover {
  background: hsl(0 84.2% 60.2%);
  color: white;
}

.overlay-btn svg {
  width: 15px;
  height: 15px;
}

.file-info {
  padding: 10px;
}

.file-name {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.file-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 11px;
  color: hsl(var(--muted-foreground));
}

.file-countdown {
  color: hsl(25 95% 53%);
  font-weight: 500;
  cursor: help;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 8px;
}

.tag-chip,
.tag-picker {
  display: inline-flex;
  max-width: 100%;
  align-items: center;
  padding: 3px 8px;
  border: 1px solid hsl(var(--border));
  border-radius: 999px;
  background: hsl(var(--background));
  color: hsl(var(--muted-foreground));
  font-size: 11px;
  line-height: 1.2;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}

.tag-chip:hover,
.tag-picker:hover,
.tag-picker.active {
  border-color: hsl(var(--primary) / 0.45);
  background: hsl(var(--primary) / 0.08);
  color: hsl(var(--foreground));
}

.gallery-pagination {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 2px;
}

.lightbox {
  position: fixed;
  inset: 0;
  z-index: 140;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(0, 0, 0, 0.62);
  backdrop-filter: blur(10px);
}

.lightbox-content {
  position: relative;
  display: flex;
  max-width: 92vw;
  max-height: 92vh;
  flex-direction: column;
  align-items: center;
}

.lightbox-close {
  position: absolute;
  top: -40px;
  right: -4px;
  display: flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  color: white;
  cursor: pointer;
  transition: background 0.15s;
}

.lightbox-close:hover {
  background: rgba(255, 255, 255, 0.28);
}

.lightbox-media {
  max-width: 100%;
  max-height: 80vh;
  border-radius: 8px;
  object-fit: contain;
}

.lightbox-info {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.78);
}

.lightbox-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 999px;
  background: transparent;
  color: white;
  font-size: 11px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.lightbox-btn:hover {
  border-color: rgba(255, 255, 255, 0.65);
  background: rgba(255, 255, 255, 0.1);
}

.tag-editor-thumb {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 8px;
  background: hsl(var(--muted));
  object-fit: cover;
}

.gallery-bulk-bar {
  display: flex;
  width: 100%;
  max-width: 34rem;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid hsl(var(--border));
  border-radius: 999px;
  background: hsl(var(--card) / 0.96);
  padding: 10px 12px 10px 16px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(10px);
}

.gallery-bulk-bar-enter-active,
.gallery-bulk-bar-leave-active {
  transition: all 0.2s ease;
}

.gallery-bulk-bar-enter-from,
.gallery-bulk-bar-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

@media (max-width: 640px) {
  .gallery-content-toolbar,
  .gallery-bulk-bar {
    align-items: stretch;
    border-radius: 8px;
  }

  .gallery-storage-actions,
  .gallery-setting-row {
    justify-content: flex-start;
  }
}
</style>

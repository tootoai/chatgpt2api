<template>
  <div class="space-y-5">
    <section class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <StatCard
        v-for="stat in stats"
        :key="stat.label"
        :label="stat.label"
        :value="stat.value"
        :caption="stat.meta"
        :icon="stat.icon"
        :icon-bg="stat.iconBg"
        :icon-color="stat.iconColor"
      />
    </section>

    <section class="grid grid-cols-1 gap-4">
      <ChartCard title="模型请求分布">
        <template #actions>
          <SegmentedTabs v-model="timeRangeHourlyRequests" :options="timeRanges" aria-label="模型请求分布时间范围" />
        </template>
        <div ref="hourlyRequestsChartRef" class="h-72 w-full px-2"></div>
      </ChartCard>
    </section>

    <section class="grid grid-cols-1 gap-4">
      <ChartCard title="调用趋势">
        <template #actions>
          <SegmentedTabs v-model="timeRangeTrend" :options="timeRanges" aria-label="调用趋势时间范围" />
        </template>
        <div ref="trendChartRef" class="h-56 w-full"></div>
      </ChartCard>
    </section>

    <section class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <ChartCard title="成功率趋势">
        <template #actions>
          <SegmentedTabs v-model="timeRangeSuccessRate" :options="timeRanges" aria-label="成功率趋势时间范围" />
        </template>
        <div ref="successRateChartRef" class="h-56 w-full"></div>
      </ChartCard>

      <ChartCard title="平均响应时间">
        <template #actions>
          <SegmentedTabs v-model="timeRangeResponseTime" :options="timeRanges" aria-label="平均响应时间范围" />
        </template>
        <div ref="responseTimeChartRef" class="h-56 w-full"></div>
      </ChartCard>
    </section>

    <section class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <ChartCard title="模型调用占比">
        <template #actions>
          <SegmentedTabs v-model="timeRangeModel" :options="timeRanges" aria-label="模型调用占比时间范围" />
        </template>
        <div ref="modelChartRef" class="h-56 w-full"></div>
      </ChartCard>

      <ChartCard title="模型使用排行">
        <template #actions>
          <SegmentedTabs v-model="timeRangeModelRank" :options="timeRanges" aria-label="模型使用排行时间范围" />
        </template>
        <div ref="modelRankChartRef" class="h-56 w-full"></div>
      </ChartCard>
    </section>

    <PagePanel class="dashboard-image-panel">
      <PanelHeader title="画图面板">
        <template #actions>
          <Button size="sm" variant="outline" :disabled="imageTasksLoading" @click="loadImageTasks">
            {{ imageTasksLoading ? '刷新中...' : '刷新任务' }}
          </Button>
          <Button size="sm" variant="outline" @click="openFullImageTasks">
            完整任务页
          </Button>
          <Button size="sm" variant="primary" :disabled="imageSubmitting || !imageForm.prompt.trim()" @click="submitImageTask">
            {{ imageSubmitting ? '提交中...' : '提交画图' }}
          </Button>
        </template>
      </PanelHeader>
      <div class="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <div class="space-y-3">
          <div class="grid gap-3 md:grid-cols-3">
            <Input v-model.trim="imageForm.model" type="text" placeholder="模型" block />
            <SelectMenu v-model="imageForm.size" :options="dashboardImageSizeOptions" selected-indicator="none" />
            <SelectMenu v-model="imageForm.quality" :options="IMAGE_QUALITY_OPTIONS" selected-indicator="none" />
          </div>
          <textarea
            v-model.trim="imageForm.prompt"
            class="dashboard-image-textarea"
            rows="6"
            placeholder="输入图片提示词"
          ></textarea>
          <p v-if="imageTaskError" class="dashboard-image-error">{{ imageTaskError }}</p>
        </div>
        <div class="dashboard-image-tasks">
          <div v-if="recentImageTasks.length === 0" class="dashboard-image-empty">暂无图片任务</div>
          <article v-for="task in recentImageTasks" :key="task.id" class="dashboard-image-task-card">
            <div class="flex flex-wrap items-center gap-2">
              <StateBadge :tone="imageTaskTone(task.status)" shape="rounded" :bordered="false">
                {{ imageTaskStatusLabel(task.status) }}
              </StateBadge>
              <span class="font-mono text-[11px] text-muted-foreground">{{ task.model }}</span>
              <span v-if="task.elapsed_secs !== undefined" class="text-[11px] text-muted-foreground">{{ task.elapsed_secs }}s</span>
            </div>
            <p v-if="task.stage || task.progress" class="mt-2 text-xs text-muted-foreground">
              {{ [task.stage, task.progress].filter(Boolean).join(' / ') }}
            </p>
            <p v-if="taskPrimaryMessage(task)" class="mt-2 line-clamp-2 text-xs text-rose-600">
              {{ taskPrimaryMessage(task) }}
            </p>
            <div v-if="firstImageAssetUrl(task)" class="mt-3">
              <img :src="firstImageAssetUrl(task)" alt="图片任务结果" class="dashboard-image-preview" loading="lazy" />
            </div>
          </article>
        </div>
      </div>
    </PagePanel>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ChartCard, PagePanel, PanelHeader, StateBadge, StatCard } from '@/components/ai'
import { Button, Input, SegmentedTabs, SelectMenu } from 'nanocat-ui'
import {
  DEFAULT_IMAGE_MODEL,
  DEFAULT_IMAGE_QUALITY,
  DEFAULT_IMAGE_SIZE,
  IMAGE_QUALITY_OPTIONS,
  imageAssetUrl,
  imageTasksApi,
  isImageSizeSupportedByModel,
  resolveImageSizeOptions,
  taskPrimaryMessage,
  type ImageTask,
  type ImageTaskStatus,
} from '@/api/imageTasks'
import { useToast } from '@/composables/useToast'
import { useDashboardPage } from './dashboard/useDashboardPage'

const router = useRouter()
const toast = useToast()
const {
  stats,
  timeRanges,
  timeRangeHourlyRequests,
  timeRangeTrend,
  timeRangeSuccessRate,
  timeRangeModel,
  timeRangeModelRank,
  timeRangeResponseTime,
  hourlyRequestsChartRef,
  trendChartRef,
  successRateChartRef,
  responseTimeChartRef,
  modelChartRef,
  modelRankChartRef,
} = useDashboardPage()

const imageForm = reactive({
  model: DEFAULT_IMAGE_MODEL,
  size: DEFAULT_IMAGE_SIZE,
  quality: DEFAULT_IMAGE_QUALITY,
  prompt: '',
})
const recentImageTasks = ref<ImageTask[]>([])
const imageTasksLoading = ref(false)
const imageSubmitting = ref(false)
const imageTaskError = ref('')
const dashboardImageSizeOptions = computed(() => resolveImageSizeOptions(imageForm.model))

watch(() => imageForm.model, () => {
  if (!isImageSizeSupportedByModel(imageForm.size, imageForm.model)) {
    imageForm.size = DEFAULT_IMAGE_SIZE
  }
})

function imageTaskStatusLabel(status: ImageTaskStatus) {
  return {
    queued: '排队中',
    running: '生成中',
    success: '成功',
    error: '失败',
  }[status] || status
}

function imageTaskTone(status: ImageTaskStatus): 'success' | 'danger' | 'warning' | 'muted' {
  if (status === 'success') return 'success'
  if (status === 'error') return 'danger'
  if (status === 'queued' || status === 'running') return 'warning'
  return 'muted'
}

function firstImageAssetUrl(task: ImageTask) {
  const asset = task.data?.[0]
  return asset ? imageAssetUrl(asset) : ''
}

async function loadImageTasks() {
  if (imageTasksLoading.value) return
  imageTasksLoading.value = true
  imageTaskError.value = ''
  try {
    const response = await imageTasksApi.list()
    recentImageTasks.value = response.items.slice(0, 6)
  } catch (error: any) {
    imageTaskError.value = error?.message || '图片任务加载失败'
  } finally {
    imageTasksLoading.value = false
  }
}

async function submitImageTask() {
  const prompt = imageForm.prompt.trim()
  if (!prompt || imageSubmitting.value) return
  imageSubmitting.value = true
  imageTaskError.value = ''
  try {
    const task = await imageTasksApi.createGeneration({
      prompt,
      model: imageForm.model || DEFAULT_IMAGE_MODEL,
      size: imageForm.size,
      quality: imageForm.quality,
    })
    recentImageTasks.value = [task, ...recentImageTasks.value].slice(0, 6)
    toast.success('画图任务已提交')
  } catch (error: any) {
    imageTaskError.value = error?.message || '画图任务提交失败'
  } finally {
    imageSubmitting.value = false
  }
}

function openFullImageTasks() {
  void router.push('/image-tasks')
}

onMounted(() => {
  void loadImageTasks()
})
</script>

<style scoped>
.dashboard-image-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px 20px;
}

.dashboard-image-textarea {
  width: 100%;
  min-height: 10rem;
  resize: vertical;
  border: 1px solid hsl(var(--border));
  border-radius: 12px;
  background: hsl(var(--background));
  padding: 10px 12px;
  color: hsl(var(--foreground));
  font-size: 13px;
  line-height: 1.65;
  outline: none;
}

.dashboard-image-textarea:focus {
  border-color: hsl(var(--primary));
  box-shadow: 0 0 0 3px hsl(var(--primary) / 0.12);
}

.dashboard-image-error {
  border: 1px solid hsl(var(--destructive) / 0.3);
  border-radius: 12px;
  background: hsl(var(--destructive) / 0.08);
  padding: 10px 12px;
  color: hsl(var(--destructive));
  font-size: 13px;
}

.dashboard-image-tasks {
  display: grid;
  min-height: 14rem;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
}

.dashboard-image-task-card,
.dashboard-image-empty {
  border: 1px solid hsl(var(--border));
  border-radius: 16px;
  background: hsl(var(--background));
  padding: 12px;
}

.dashboard-image-empty {
  display: flex;
  min-height: 12rem;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
  font-size: 13px;
}

.dashboard-image-preview {
  aspect-ratio: 16 / 10;
  width: 100%;
  border-radius: 12px;
  object-fit: cover;
}
</style>

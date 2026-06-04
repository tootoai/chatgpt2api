<template>
  <div
    v-if="totalCount > 0"
    class="flex flex-col gap-3 border-t border-border/60 pt-4 md:flex-row md:items-center md:justify-between"
  >
    <div class="text-xs text-muted-foreground">
      当前展示 {{ visibleCount }} / {{ totalCount }} {{ unit }}
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <span class="text-xs text-muted-foreground">每页</span>
      <div class="w-[110px] shrink-0">
        <SelectMenu
          :model-value="pageSize"
          :options="pageSizeMenuOptions"
          placement="up"
          :aria-label="`${unit}每页数量`"
          @update:model-value="setPageSize"
        />
      </div>
      <Button
        size="sm"
        variant="outline"
        :disabled="disabled || safePage <= 1"
        @click="emit('update:page', safePage - 1)"
      >
        上一页
      </Button>
      <span class="text-sm text-muted-foreground tabular-nums">{{ safePage }} / {{ pageCount }}</span>
      <Button
        size="sm"
        variant="outline"
        :disabled="disabled || safePage >= pageCount"
        @click="emit('update:page', safePage + 1)"
      >
        下一页
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, SelectMenu } from 'nanocat-ui'

const props = withDefaults(defineProps<{
  page: number
  pageSize: number
  totalCount: number
  pageSizeOptions?: number[]
  unit?: string
  disabled?: boolean
}>(), {
  pageSizeOptions: () => [20, 50, 100],
  unit: '条',
  disabled: false,
})

const emit = defineEmits<{
  (e: 'update:page', value: number): void
  (e: 'update:pageSize', value: number): void
}>()

const pageCount = computed(() => Math.max(1, Math.ceil(props.totalCount / Math.max(1, props.pageSize))))
const safePage = computed(() => Math.min(pageCount.value, Math.max(1, props.page)))
const startIndex = computed(() => (props.totalCount ? (safePage.value - 1) * props.pageSize + 1 : 0))
const endIndex = computed(() => Math.min(props.totalCount, safePage.value * props.pageSize))
const visibleCount = computed(() => (props.totalCount ? Math.max(0, endIndex.value - startIndex.value + 1) : 0))
const pageSizeMenuOptions = computed(() => props.pageSizeOptions.map((value) => ({
  label: `${value} / 页`,
  value,
})))

function setPageSize(value: string | number) {
  const next = Number(value)
  if (!Number.isFinite(next) || next <= 0) return
  emit('update:pageSize', next)
}
</script>

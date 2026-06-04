<template>
  <Teleport to="body">
    <transition name="accounts-bulk-bar">
      <div
        v-if="selectedCount > 0"
        class="fixed inset-x-0 bottom-5 z-[130] flex justify-center px-4"
      >
        <div class="flex w-full max-w-3xl flex-wrap items-center justify-between gap-3 rounded-3xl border border-border bg-card/95 px-4 py-3 shadow-2xl backdrop-blur">
          <div class="min-w-0">
            <p class="text-sm font-semibold text-foreground">已选择 {{ selectedCount }} 个账户</p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <ActionMenu
              :label="busy ? (busyLabel || '批量处理中...') : `批量操作（${selectedCount}）`"
              :items="items"
              :disabled="busy"
              button-class="w-[7.75rem]"
              @select="emit('select', $event)"
            />
            <Button
              size="xs"
              variant="outline"
              :disabled="busy"
              @click="emit('clear')"
            >
              取消选择
            </Button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ActionMenu, Button } from 'nanocat-ui'
import type { ActionMenuItem } from 'nanocat-ui'

defineProps<{
  selectedCount: number
  busy: boolean
  busyLabel?: string
  items: ActionMenuItem[]
}>()

const emit = defineEmits<{
  (e: 'select', key: string): void
  (e: 'clear'): void
}>()
</script>

<style scoped>
.accounts-bulk-bar-enter-active,
.accounts-bulk-bar-leave-active {
  transition: all 0.2s ease;
}

.accounts-bulk-bar-enter-from,
.accounts-bulk-bar-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
</style>

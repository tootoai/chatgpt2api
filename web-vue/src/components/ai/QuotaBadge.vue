<template>
  <span
    class="inline-flex min-w-[2.5rem] items-center font-mono text-sm font-medium leading-5"
    :class="quotaClass"
  >
    {{ quotaText }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Account } from '@/api/accounts'

const props = defineProps<{
  account: Account
}>()

const quotaValue = computed(() => Number(props.account.quota || 0))

const quotaText = computed(() => {
  if (props.account.image_quota_unknown) return '未知'
  return String(Math.max(0, Math.trunc(quotaValue.value)))
})

const quotaClass = computed(() => {
  if (props.account.image_quota_unknown) {
    return 'text-muted-foreground'
  }
  if (quotaValue.value <= 0) {
    return 'text-rose-600'
  }
  if (quotaValue.value <= 3) {
    return 'text-amber-600'
  }
  return 'text-emerald-600'
})
</script>

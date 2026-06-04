<template>
  <div ref="rootRef" class="relative inline-flex">
    <Button
      variant="outline"
      :size="size === 'xs' ? 'xs' : 'sm'"
      :disabled="disabled"
      :root-class="`justify-between gap-2 ${triggerClass || buttonClass}`.trim()"
      @click.stop="toggleMenu"
    >
      <span>{{ label }}</span>
      <svg
        viewBox="0 0 20 20"
        class="h-3.5 w-3.5 transition-transform"
        :class="open ? 'rotate-180' : ''"
        fill="currentColor"
        aria-hidden="true"
      >
        <path d="M5 7l5 6 5-6H5z" />
      </svg>
    </Button>

    <Teleport to="body">
      <div
        v-if="open && !disabled"
        ref="menuRef"
        class="ui-floating-panel fixed z-[1000] !rounded-2xl !p-1.5"
        :class="contentClass || menuClass"
        :style="menuStyle"
        @click.stop
      >
        <template v-for="item in items" :key="item.key">
          <div v-if="item.dividerBefore" class="my-1 h-px bg-border" />
          <button
            type="button"
            class="ui-menu-item"
            :class="item.danger ? 'ui-menu-item-danger' : ''"
            :disabled="item.disabled"
            @click="selectItem(item)"
          >
            {{ item.label }}
          </button>
        </template>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Button } from 'nanocat-ui'
import type { ActionMenuItem, UiSize } from 'nanocat-ui'
import type { CSSProperties } from 'vue'

const props = withDefaults(defineProps<{
  label: string
  items: ActionMenuItem[]
  disabled?: boolean
  align?: 'left' | 'right'
  size?: UiSize
  triggerClass?: string
  buttonClass?: string
  contentClass?: string
  menuClass?: string
}>(), {
  disabled: false,
  align: 'right',
  size: 'sm',
  triggerClass: '',
  buttonClass: '',
  contentClass: '',
  menuClass: 'min-w-max',
})

const emit = defineEmits<{
  (e: 'select', key: string): void
}>()

const rootRef = ref<HTMLElement | null>(null)
const menuRef = ref<HTMLElement | null>(null)
const open = ref(false)
const menuPosition = ref({ left: 0, top: 0, minWidth: 0 })

const menuStyle = computed<CSSProperties>(() => ({
  left: `${menuPosition.value.left}px`,
  top: `${menuPosition.value.top}px`,
  minWidth: `${menuPosition.value.minWidth}px`,
}))

function closeMenu() {
  open.value = false
}

async function toggleMenu() {
  if (props.disabled) return
  open.value = !open.value
  if (open.value) {
    await nextTick()
    updatePosition()
    requestAnimationFrame(updatePosition)
  }
}

function selectItem(item: ActionMenuItem) {
  if (item.disabled) return
  closeMenu()
  emit('select', item.key)
}

function updatePosition() {
  const root = rootRef.value
  const menu = menuRef.value
  if (!root || !menu) return

  const rect = root.getBoundingClientRect()
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight
  const margin = 8
  const gap = 8
  const menuWidth = Math.max(menu.offsetWidth || 0, rect.width)
  const menuHeight = menu.offsetHeight || 0
  const maxLeft = Math.max(margin, viewportWidth - margin - menuWidth)

  const rawLeft = props.align === 'left' ? rect.left : rect.right - menuWidth
  const left = Math.min(maxLeft, Math.max(margin, rawLeft))

  const canOpenUp = rect.top - gap - menuHeight >= margin
  const canOpenDown = rect.bottom + gap + menuHeight <= viewportHeight - margin
  let top = rect.top - gap - menuHeight
  if (!canOpenUp && canOpenDown) {
    top = rect.bottom + gap
  } else if (!canOpenUp) {
    top = Math.max(margin, Math.min(viewportHeight - margin - menuHeight, top))
  }

  menuPosition.value = {
    left,
    top,
    minWidth: rect.width,
  }
}

function handleDocumentClick(event: MouseEvent) {
  const target = event.target as Node | null
  if (!target) return
  if (rootRef.value?.contains(target) || menuRef.value?.contains(target)) return
  closeMenu()
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') closeMenu()
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
  window.addEventListener('resize', updatePosition)
  window.addEventListener('scroll', updatePosition, true)
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  window.removeEventListener('resize', updatePosition)
  window.removeEventListener('scroll', updatePosition, true)
  document.removeEventListener('keydown', handleKeydown)
})
</script>

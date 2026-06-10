<template>
  <div ref="rootRef" class="floating-action-menu" :style="rootStyle">
    <Button
      variant="outline"
      :size="size === 'xs' ? 'xs' : 'sm'"
      :disabled="disabled"
      :root-class="triggerRootClass"
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
        class="floating-action-menu-panel ui-floating-panel fixed z-[1000]"
        :class="panelClass"
        :style="menuStyle"
        @click.stop
      >
        <template v-for="item in items" :key="item.key">
          <div
            v-if="item.dividerBefore"
            class="floating-menu-divider"
            role="separator"
            aria-hidden="true"
          />
          <button
            type="button"
            class="floating-action-menu-item ui-menu-item"
            :class="item.danger ? 'floating-action-menu-item-danger ui-menu-item-danger' : ''"
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
  menuClass?: string
  menuMinWidth?: number
  triggerMinWidth?: number
  triggerWidth?: number
}>(), {
  disabled: false,
  align: 'right',
  size: 'sm',
  triggerClass: '',
  menuClass: 'min-w-max',
})

const emit = defineEmits<{
  (e: 'select', key: string): void
}>()

const rootRef = ref<HTMLElement | null>(null)
const menuRef = ref<HTMLElement | null>(null)
const open = ref(false)
const menuPosition = ref({ left: 0, top: 0, minWidth: 0, maxHeight: 0 })
const menuId = `floating-menu-${Math.random().toString(36).slice(2)}`
const hasTriggerSizing = computed(() => Boolean(props.triggerWidth || props.triggerMinWidth))
const triggerRootClass = computed(() => [
  'floating-action-menu-trigger justify-between gap-2',
  hasTriggerSizing.value ? 'w-full' : '',
  props.triggerClass,
].filter(Boolean).join(' '))
const panelClass = computed(() => props.menuClass)
const rootStyle = computed<CSSProperties>(() => {
  const style: CSSProperties = {}
  if (props.triggerWidth) {
    style.width = `${props.triggerWidth}px`
  } else if (props.triggerMinWidth) {
    style.minWidth = `${props.triggerMinWidth}px`
  }
  return style
})

const menuStyle = computed<CSSProperties>(() => {
  const minWidth = Math.max(menuPosition.value.minWidth, props.menuMinWidth || 0)

  return {
    left: `${menuPosition.value.left}px`,
    top: `${menuPosition.value.top}px`,
    minWidth: `${minWidth}px`,
    width: 'max-content',
    maxWidth: 'min(20rem, calc(100vw - 1rem))',
    maxHeight: menuPosition.value.maxHeight ? `${menuPosition.value.maxHeight}px` : undefined,
  }
})

function closeMenu() {
  open.value = false
}

async function toggleMenu() {
  if (props.disabled) return
  open.value = !open.value
  if (open.value) {
    window.dispatchEvent(new CustomEvent('ai-floating-menu-open', { detail: menuId }))
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

  const availableDown = Math.max(0, viewportHeight - margin - rect.bottom - gap)
  const availableUp = Math.max(0, rect.top - margin - gap)
  const shouldOpenUp = menuHeight > availableDown && availableUp > availableDown
  const top = shouldOpenUp
    ? Math.max(margin, rect.top - gap - menuHeight)
    : rect.bottom + gap
  const maxHeight = Math.max(96, Math.floor(shouldOpenUp ? availableUp : availableDown))

  menuPosition.value = {
    left,
    top,
    minWidth: rect.width,
    maxHeight,
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

function handleOtherMenuOpen(event: Event) {
  if ((event as CustomEvent<string>).detail === menuId) return
  closeMenu()
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
  window.addEventListener('resize', updatePosition)
  window.addEventListener('scroll', updatePosition, true)
  window.addEventListener('ai-floating-menu-open', handleOtherMenuOpen)
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  window.removeEventListener('resize', updatePosition)
  window.removeEventListener('scroll', updatePosition, true)
  window.removeEventListener('ai-floating-menu-open', handleOtherMenuOpen)
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.floating-action-menu {
  position: relative;
  display: inline-flex;
}

.floating-action-menu-panel {
  padding: 6px !important;
  border-radius: 14px !important;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.floating-action-menu-item {
  width: 100%;
  justify-content: flex-start !important;
  white-space: nowrap;
  text-align: left;
  border-radius: 10px;
}

.floating-action-menu-item:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.floating-action-menu-item-danger {
  color: hsl(var(--tone-error-foreground));
}

.floating-menu-divider {
  height: 0;
  margin: 4px 8px;
  flex-shrink: 0;
  border-top: 1px solid hsl(var(--border) / 0.82);
}
</style>

<template>
  <div class="space-y-6">
    <section class="ui-panel">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="ui-section-title">文档中心</p>
          <p class="mt-1 text-xs text-muted-foreground">
            当前页面只展示 chatgpt2api 控制台相关接口、运维边界和风险说明。
          </p>
        </div>
      </div>

      <div class="mt-6 [&_.ui-segmented]:w-full [&_.ui-segmented-btn]:flex-1 [&_.ui-segmented-btn]:justify-center">
        <SegmentedTabs
          v-model="activeTab"
          :options="tabs"
          aria-label="文档标签"
        />
      </div>

      <div class="mt-6 space-y-6 text-sm text-foreground">
        <div v-if="activeTab === 'api'" class="space-y-6">
          <section class="rounded-2xl border border-border bg-card p-5">
            <p class="text-sm font-semibold">认证方式</p>
            <p class="mt-2 text-xs leading-6 text-muted-foreground">
              管理端和 OpenAI 兼容接口都使用 Bearer key。管理端登录会把 key 写入本地浏览器存储；接口调用时放在
              <code class="font-mono text-foreground">Authorization: Bearer YOUR_API_KEY</code>。
            </p>
          </section>

          <section class="grid gap-4 lg:grid-cols-2">
            <article class="rounded-2xl border border-border bg-muted/20 p-4">
              <p class="text-sm font-semibold">聊天模型</p>
              <div class="mt-3 flex flex-wrap gap-2">
                <span v-for="model in chatModels" :key="model" class="ui-chip">
                  {{ model }}
                </span>
              </div>
            </article>

            <article class="rounded-2xl border border-border bg-muted/20 p-4">
              <p class="text-sm font-semibold">图片模型</p>
              <div class="mt-3 flex flex-wrap gap-2">
                <span v-for="model in imageModels" :key="model" class="ui-chip">
                  {{ model }}
                </span>
              </div>
            </article>
          </section>

          <section class="space-y-2">
            <p class="text-sm font-semibold">文本对话（/v1/chat/completions）</p>
            <pre class="mt-3 overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-card px-4 py-3 text-xs font-mono scrollbar-slim">{{ chatCompletionExample }}</pre>
          </section>

          <section class="space-y-2">
            <p class="text-sm font-semibold">文生图（/v1/images/generations）</p>
            <pre class="mt-3 overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-card px-4 py-3 text-xs font-mono scrollbar-slim">{{ imageGenerationExample }}</pre>
          </section>

          <section class="space-y-2">
            <p class="text-sm font-semibold">图生图（/v1/images/edits）</p>
            <pre class="mt-3 overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-card px-4 py-3 text-xs font-mono scrollbar-slim">{{ imageEditExample }}</pre>
            <p class="mt-2 text-xs text-muted-foreground">
              也支持 image_url / image_b64，mask_url / mask_b64 同理；真实支持情况以后端版本和上游返回为准。
            </p>
          </section>
        </div>

        <div v-else-if="activeTab === 'ops'" class="grid gap-4 lg:grid-cols-2">
          <article
            v-for="section in operationSections"
            :key="section.title"
            class="rounded-2xl border border-border bg-card p-5"
          >
            <p class="text-sm font-semibold">{{ section.title }}</p>
            <ul class="mt-3 space-y-2 text-xs leading-6 text-muted-foreground">
              <li v-for="item in section.items" :key="item">{{ item }}</li>
            </ul>
          </article>
        </div>

        <div v-else class="space-y-4">
          <section class="rounded-2xl border border-border bg-card p-5">
            <p class="text-sm font-semibold">动作风险等级</p>
            <div class="mt-4 grid gap-3">
              <div
                v-for="risk in riskRows"
                :key="risk.level"
                class="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-border bg-muted/20 px-4 py-3"
              >
                <div>
                  <p class="text-xs font-semibold text-foreground">{{ risk.level }}</p>
                  <p class="mt-1 text-xs leading-5 text-muted-foreground">{{ risk.description }}</p>
                </div>
                <span class="ui-chip text-xs">{{ risk.policy }}</span>
              </div>
            </div>
          </section>

          <section class="rounded-2xl border border-border bg-card p-5">
            <p class="text-sm font-semibold">当前验收状态</p>
            <div class="mt-4 grid gap-3 lg:grid-cols-2">
              <div
                v-for="row in smokeRows"
                :key="row.scope"
                class="rounded-xl border border-border bg-muted/20 px-4 py-3"
              >
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <p class="text-xs font-semibold text-foreground">{{ row.scope }}</p>
                  <span class="ui-chip text-xs">{{ row.status }}</span>
                </div>
                <p class="mt-2 text-xs leading-5 text-muted-foreground">{{ row.note }}</p>
              </div>
            </div>
          </section>

          <section class="rounded-2xl border border-border bg-card p-5">
            <p class="text-sm font-semibold">R2 测试对象</p>
            <ul class="mt-3 space-y-2 text-xs leading-6 text-muted-foreground">
              <li v-for="item in r2Requirements" :key="item">{{ item }}</li>
            </ul>
          </section>

          <section class="rounded-2xl border border-border bg-muted/30 p-5 text-xs leading-6 text-muted-foreground">
            图片任务和本地画图第一版仍隐藏。后续恢复时必须走异步任务接口，不再让浏览器页面直接等待长时间图片请求。
          </section>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { SegmentedTabs } from 'nanocat-ui'
import { useSettingsStore } from '@/stores/settings'
import { resolveChatModels, resolveImageModels } from '@/config/modelCatalog'

const activeTab = ref('api')
const settingsStore = useSettingsStore()

const tabs = [
  { value: 'api', label: '接口说明' },
  { value: 'ops', label: '运维边界' },
  { value: 'risk', label: '风险说明' },
]

const chatModels = computed(() => resolveChatModels(settingsStore.settings))
const imageModels = computed(() => resolveImageModels(settingsStore.settings))
const primaryChatModel = computed(() => chatModels.value[0] || 'gpt-5-mini')
const primaryImageModel = computed(() => imageModels.value[0] || 'gpt-image-2')

const chatCompletionExample = computed(() => `curl -X POST "http://localhost:7860/v1/chat/completions" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{
    "model": "${primaryChatModel.value}",
    "stream": false,
    "messages": [
      { "role": "user", "content": "你好" }
    ]
  }'`)

const imageGenerationExample = computed(() => `curl -X POST "http://localhost:7860/v1/images/generations" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{
    "model": "${primaryImageModel.value}",
    "prompt": "draw a tiny cat icon, minimal flat vector",
    "n": 1,
    "size": "1024x1024",
    "response_format": "url"
  }'`)

const imageEditExample = computed(() => `curl -X POST "http://localhost:7860/v1/images/edits" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "model=${primaryImageModel.value}" \\
  -F "prompt=把这张图改成赛博风格" \\
  -F "response_format=url" \\
  -F "image=@reference.png"`)

const operationSections = [
  {
    title: '账号来源',
    items: [
      '支持 OAuth 登录、Access Token、Session JSON、Codex 认证 JSON、CPA JSON 文件。',
      '远程 CPA 和 Sub2API 来源只在设置页配置连接，真正导入动作在账号管理页执行。',
      '批量刷新、恢复异常和导出账号都会先确认范围，避免误操作真实账号池。',
    ],
  },
  {
    title: '图片和存储',
    items: [
      '图库使用 /api/images 服务端分页，避免大图库一次性压到浏览器。',
      '图片保留口径使用 image_retention_days，和设置页、后端自动清理保持一致。',
      'WebDAV/R2 测试、同步、备份都属于外部副作用动作，需要确认后再执行。',
    ],
  },
  {
    title: '代理',
    items: [
      '账号代理为空时使用全局代理，direct 表示强制直连，profile:<id> 表示使用代理分组。',
      '代理测试会访问外部网络；真实 smoke 需要明确测试代理和测试账号。',
      '代理分组编辑保存视为确认，删除分组属于破坏性动作。',
    ],
  },
  {
    title: '暂缓模块',
    items: [
      '图片任务和本地画图第一版不进主菜单，后续恢复时走 /api/image-tasks/*。',
      '注册机第一版不接入主控制台，后续从 D:\\codexzz\\webfree_server 单独任务化。',
      '真正进程运行日志已接 /api/runtime-logs 只读接口；Docker stdout/stderr 需要部署侧重定向或挂载日志文件。',
    ],
  },
]

const riskRows = [
  {
    level: 'R0 只读',
    description: '加载页面、读取列表、查看详情、读取统计。',
    policy: '可直接 smoke',
  },
  {
    level: 'R1 本地状态',
    description: '切换筛选、分页、打开弹窗、当前页勾选。',
    policy: '可直接 smoke',
  },
  {
    level: 'R2 可恢复写入',
    description: '保存设置、编辑账号、编辑标签、编辑代理分组。',
    policy: '需要测试对象',
  },
  {
    level: 'R3 外部副作用',
    description: 'OAuth、CPA、Sub2API、WebDAV、R2、代理测试和批量刷新。',
    policy: '需要确认配置',
  },
  {
    level: 'R4 破坏性',
    description: '删除账号、日志、图片、备份或执行图库清理。',
    policy: '只对测试数据',
  },
]

const smokeRows = [
  {
    scope: 'R0/R1 只读',
    status: '已完成',
    note: 'Dashboard、Accounts、Logs、Gallery、Proxy、Settings、Docs 已完成只读巡检，页面控制台 error 为 0。',
  },
  {
    scope: 'R2 可恢复写入',
    status: '待测试对象',
    note: '需要明确测试账号、测试图片、测试代理分组和可恢复设置项后再执行。',
  },
  {
    scope: 'R3 外部副作用',
    status: '待确认配置',
    note: 'OAuth、CPA、Sub2API、WebDAV、R2、代理测试和批量刷新都需要真实配置确认。',
  },
  {
    scope: 'R4 破坏性',
    status: '默认禁止',
    note: '删除账号、日志、图片、备份和图库清理只允许作用于专门创建的测试数据。',
  },
]

const r2Requirements = [
  '测试账号：用于账号编辑、代理引用、单账号刷新和恢复状态。',
  '测试图片：用于标签编辑、预览、下载和删除验证。',
  '测试代理分组：用于新增、编辑、禁用和删除验证。',
  '测试设置项：选择低风险字段，保存前记录原值，验证后改回。',
]

onMounted(async () => {
  if (!settingsStore.settings && !settingsStore.isLoading) {
    await settingsStore.loadSettings()
  }
})
</script>

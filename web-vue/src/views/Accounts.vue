<template>
  <div class="relative space-y-8">
    <section class="ui-panel space-y-5">
      <ToolbarShell stack-on-mobile start-class="flex-1" end-class="xl:justify-end">
        <template #start>
          <Input
            :model-value="keyword"
            type="text"
            placeholder="搜索账号 ID / 邮箱 / Token / 类型 / 来源"
            block
            root-class="min-w-[11rem] flex-1 md:w-80 md:flex-none"
            @update:model-value="keyword = $event.trim()"
          />
          <FilterSelect
            v-model="statusFilter"
            :options="statusFilterOptions"
            placeholder="状态筛选"
            aria-label="账号状态筛选"
          />
          <Button
            size="sm"
            variant="outline"
            root-class="shrink-0 whitespace-nowrap"
            :disabled="loading"
            @click="loadData"
          >
            刷新列表
          </Button>
          <Button
            size="sm"
            variant="outline"
            root-class="shrink-0 whitespace-nowrap"
            :disabled="loading || batchBusy || accounts.length === 0"
            @click="refreshAllAccounts"
          >
            刷新所有账号信息和额度
          </Button>
          <Button
            size="sm"
            variant="outline"
            root-class="shrink-0 whitespace-nowrap"
            :disabled="loading || batchBusy || abnormalAccountCount === 0"
            @click="reLoginAbnormalAccounts"
          >
            恢复异常账号 {{ abnormalAccountCount ? `(${abnormalAccountCount})` : '' }}
          </Button>
          <Button
            size="sm"
            variant="primary"
            root-class="shrink-0 whitespace-nowrap"
            @click="openCreateModal"
          >
            添加账号
          </Button>
          <Button
            size="sm"
            variant="outline"
            root-class="shrink-0 whitespace-nowrap"
            :disabled="importBusy"
            @click="openImportModal('oauth')"
          >
            导入账号
          </Button>
          <Button
            size="sm"
            variant="outline"
            root-class="shrink-0 whitespace-nowrap"
            :disabled="exportBusy || selectedCount === 0"
            @click="handleExportSelected"
          >
            导出选中
          </Button>
          <Button
            size="sm"
            variant="outline"
            root-class="shrink-0 whitespace-nowrap"
            :disabled="exportBusy || accounts.length === 0"
            @click="handleExportAll"
          >
            导出全部
          </Button>
        </template>

        <template #end>
          <AccountSelectionSummary
            :all-selected="allVisibleSelected"
            :total-count="filteredAccounts.length"
            :selected-count="selectedCount"
            :view-mode="viewMode"
            @toggle-all="toggleSelectAllVisible"
            @update:view-mode="setViewMode"
          />
        </template>
      </ToolbarShell>

      <div
        v-if="loading && filteredAccounts.length === 0"
        class="rounded-2xl border border-border/70 bg-card/40 px-4 py-8 text-center text-sm text-muted-foreground"
      >
        加载中...
      </div>

      <div v-else-if="viewMode === 'list'" class="scrollbar-slim overflow-x-auto">
        <table class="min-w-[980px] w-full text-left text-sm">
          <thead class="text-xs uppercase tracking-[0.16em] text-muted-foreground">
            <tr>
              <th class="w-12 py-3 pr-4">
                <Checkbox
                  :model-value="allVisibleSelected"
                  @update:model-value="toggleSelectAllVisible"
                />
              </th>
              <th class="py-3 pr-5">TOKEN</th>
              <th class="py-3 pr-5">类型 / 来源</th>
              <th class="py-3 pr-5">状态</th>
              <th class="py-3 pr-5">账户信息</th>
              <th class="py-3 pr-5">创建时间</th>
              <th class="py-3 pr-5">图片额度</th>
              <th class="py-3 pr-5">恢复时间</th>
              <th class="py-3 pr-5">成功 / 失败</th>
              <th class="py-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody class="text-sm text-foreground">
            <tr v-if="!loading && filteredAccounts.length === 0">
              <td colspan="10" class="py-6">
                <EmptyState
                  plain
                  title="暂无账号数据"
                  description="可以先导入 Access Token 或通过 OAuth 登录添加账号。"
                />
              </td>
            </tr>
            <tr
              v-for="item in pagedAccounts"
              :key="item.id"
              class="border-t border-border transition-colors"
              :class="[rowClass(item), isSelected(item.id) ? 'bg-primary/5' : '']"
            >
              <td class="py-4 pr-4 align-top">
                <Checkbox
                  :model-value="isSelected(item.id)"
                  :disabled="item.is_demo"
                  @update:model-value="(checked) => toggleSelect(item.id, checked)"
                />
              </td>
              <td class="py-4 pr-5 align-top">
                <StatusPill
                  :label="accountTokenPreview(item)"
                  tone-class="border-muted bg-muted/20 text-muted-foreground"
                  title="Access Token"
                  :detail="accountTokenPreview(item)"
                  card-class="w-80"
                />
              </td>
              <td class="py-4 pr-5 align-top">
                <div class="space-y-1 text-xs">
                  <p class="font-medium text-foreground">{{ accountSourceText(item) }}</p>
                  <p class="max-w-[13rem] truncate text-muted-foreground">{{ accountProxyText(item) }}</p>
                </div>
              </td>
              <td class="py-4 pr-5 align-top">
                <StatusDetailPill
                  :label="statusText(item)"
                  :tone-class="`${statusClass(item)} border-border`"
                  title="状态详情"
                  detail-label="状态说明"
                  raw-error-label="原始报错"
                  :detail="statusReason(item)"
                  :raw-error="statusRawError(item)"
                />
              </td>
              <td class="py-4 pr-5 align-top">
                <p class="max-w-[16rem] truncate text-sm font-medium text-foreground">{{ accountPrimaryText(item) }}</p>
                <p class="mt-1 max-w-[16rem] truncate font-mono text-xs text-muted-foreground">{{ accountSecondaryText(item) }}</p>
              </td>
              <td class="py-4 pr-5 align-top text-xs text-muted-foreground">
                {{ accountCreatedText(item) }}
              </td>
              <td class="py-4 pr-5 align-top">
                <QuotaBadge :account="item" />
              </td>
              <td class="py-4 pr-5 align-top text-xs text-muted-foreground">
                {{ accountRestoreText(item) }}
              </td>
              <td class="py-4 pr-5 align-top">
                <div class="space-y-1 text-xs text-muted-foreground">
                  <p class="text-emerald-600">成功 {{ item.success_count || 0 }}</p>
                  <p class="text-rose-600">失败 {{ item.failure_count || 0 }}</p>
                </div>
              </td>
              <td class="py-4 text-right align-top">
                <AccountActionButtons
                  :item="item"
                  :refreshing="refreshingAccountId === item.id"
                  :resetting="resettingAccountId === item.id"
                  :relogining="reloginingAccountId === item.id"
                  align="end"
                  @edit="openEditModal(item)"
                  @toggle-enabled="toggleEnabled(item)"
                  @refresh-token="refreshToken(item.id)"
                  @reset-state="resetAccountState(item.id)"
                  @re-login="reLoginAccount(item.id)"
                  @remove="removeAccount(item.id)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <div v-if="!loading && filteredAccounts.length === 0" class="col-span-full">
          <EmptyState
            plain
            title="暂无账号数据"
            description="可以先导入 Access Token 或通过 OAuth 登录添加账号。"
          />
        </div>

        <article
          v-for="item in pagedAccounts"
          :key="`${item.id}-card`"
          class="ui-card flex h-full flex-col gap-4 transition-all"
          :class="[rowClass(item), isSelected(item.id) ? 'ring-2 ring-primary/30' : 'hover:border-primary/30']"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="flex min-w-0 items-start gap-3">
              <Checkbox
                :model-value="isSelected(item.id)"
                :disabled="item.is_demo"
                @update:model-value="(checked) => toggleSelect(item.id, checked)"
              />
              <div class="min-w-0">
                <h3 class="truncate text-sm font-medium text-foreground">{{ accountPrimaryText(item) }}</h3>
                <p class="mt-1 truncate font-mono text-xs text-muted-foreground">{{ accountSecondaryText(item) }}</p>
              </div>
            </div>
            <StatusDetailPill
              :label="statusText(item)"
              :tone-class="`${statusClass(item)} border-border`"
              title="状态详情"
              detail-label="状态说明"
              raw-error-label="原始报错"
              :detail="statusReason(item)"
              :raw-error="statusRawError(item)"
            />
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <StatusPill
              :label="accountSourceText(item)"
              tone-class="border-cyan-500/40 bg-cyan-500/10 text-cyan-600"
              title="类型 / 来源"
              :detail="accountProxyText(item)"
              card-class="w-80"
            />
            <StatusPill
              :label="accountTokenPreview(item)"
              tone-class="border-muted bg-muted/20 text-muted-foreground"
              title="Access Token"
              :detail="accountTokenPreview(item)"
              card-class="w-80"
            />
          </div>

          <KeyValueList
            :items="[
              { label: '创建时间', value: accountCreatedText(item) },
              { label: '恢复时间', value: accountRestoreText(item) },
              { label: '图片额度', value: accountQuotaText(item) },
              { label: '成功', value: String(item.success_count || 0) },
              { label: '失败', value: String(item.failure_count || 0) },
            ]"
            :columns="2"
          />

          <AccountActionButtons
            class="mt-auto"
            :item="item"
            :refreshing="refreshingAccountId === item.id"
            :resetting="resettingAccountId === item.id"
            :relogining="reloginingAccountId === item.id"
            @edit="openEditModal(item)"
            @toggle-enabled="toggleEnabled(item)"
            @refresh-token="refreshToken(item.id)"
            @reset-state="resetAccountState(item.id)"
            @re-login="reLoginAccount(item.id)"
            @remove="removeAccount(item.id)"
          />
        </article>
      </div>

      <ListPagination
        v-model:page="currentPage"
        v-model:page-size="pageSize"
        :total-count="filteredAccounts.length"
        :page-size-options="pageSizeOptions"
        unit="个账号"
        :disabled="loading"
      />
    </section>

    <AccountBulkBar
      :selected-count="selectedCount"
      :busy="batchBusy"
      :busy-label="batchActionLabel"
      :items="batchMenuItems"
      @select="handleBatchAction"
      @clear="clearSelection"
    />

    <Teleport to="body">
      <div v-if="showModal" class="fixed inset-0 z-[120] overflow-y-auto bg-black/40 px-3 py-4">
        <div class="flex min-h-full items-center justify-center">
          <div class="ui-surface w-full max-w-[44rem] overflow-hidden shadow-lg">
            <div class="flex items-center justify-between border-b border-border px-5 py-3">
              <h4 class="ui-section-title">{{ editingId ? '编辑账号' : '添加账号' }}</h4>
              <Button size="xs" variant="outline" root-class="min-w-14 justify-center text-muted-foreground" @click="closeModal">
                关闭
              </Button>
            </div>

            <div class="px-4 py-3">
              <div class="space-y-3">
                <div class="rounded-xl border border-border bg-card p-3">
                  <p class="mb-2.5 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">基础信息</p>
                  <div class="grid grid-cols-1 gap-2.5 md:grid-cols-4">
                    <label v-if="editingId" class="text-xs md:col-span-2">
                      <span class="ui-field-label">账号 ID</span>
                      <Input :model-value="form.id" disabled block />
                    </label>
                    <label class="text-xs">
                      <span class="ui-field-label">类型</span>
                      <Input
                        :model-value="form.type"
                        block
                        placeholder="free / Plus / Pro"
                        @update:model-value="form.type = $event.trim()"
                      />
                    </label>
                    <div class="text-xs">
                      <span class="ui-field-label">状态</span>
                      <FilterSelect
                        v-model="form.status"
                        :options="accountStatusOptions"
                        placeholder="状态"
                        aria-label="账号状态"
                      />
                    </div>
                  </div>
                </div>

                <div class="rounded-xl border border-border bg-card p-3">
                  <label class="block text-xs">
                    <span class="ui-field-label">Access Token（必填）</span>
                    <textarea
                      v-model.trim="form.access_token"
                      rows="3"
                      class="ui-textarea-sm font-mono"
                      placeholder="粘贴完整 access token"
                      :disabled="!!editingId"
                    ></textarea>
                  </label>
                </div>

                <div class="rounded-xl border border-border bg-card p-3">
                  <p class="mb-2.5 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">调度属性</p>
                  <div class="grid grid-cols-1 gap-2 md:grid-cols-3">
                    <label class="text-xs">
                      <span class="ui-field-label">来源</span>
                      <Input
                        :model-value="form.source_type"
                        block
                        placeholder="web / oauth_login / codex"
                        @update:model-value="form.source_type = $event.trim()"
                      />
                    </label>
                    <label class="text-xs">
                      <span class="ui-field-label">图片额度</span>
                      <Input
                        :model-value="form.quota"
                        type="number"
                        block
                        placeholder="留空表示未知"
                        @update:model-value="form.quota = $event.trim()"
                      />
                    </label>
                    <div class="space-y-2 text-xs md:col-span-3">
                      <div class="grid grid-cols-1 gap-2 md:grid-cols-[11rem_minmax(0,1fr)]">
                        <label>
                          <span class="ui-field-label">代理模式</span>
                          <SelectMenu
                            :model-value="proxyMode"
                            :options="accountProxyModeOptions"
                            aria-label="代理模式"
                            class="w-full"
                            @update:model-value="setProxyMode"
                          />
                        </label>

                        <label v-if="proxyMode === 'profile'">
                          <span class="ui-field-label">代理分组</span>
                          <SelectMenu
                            :model-value="selectedProxyProfileId"
                            :options="proxyProfileOptions"
                            :disabled="proxyProfilesLoading"
                            aria-label="代理分组"
                            class="w-full"
                            @update:model-value="selectProxyProfile"
                          />
                        </label>

                        <label v-else-if="proxyMode === 'custom'">
                          <span class="ui-field-label">自定义代理</span>
                          <Input
                            :model-value="customProxyInput"
                            block
                            root-class="font-mono"
                            placeholder="http://127.0.0.1:7890"
                            @update:model-value="setCustomProxyInput"
                          />
                        </label>

                        <div v-else class="rounded-xl border border-border bg-background px-3 py-2">
                          <span class="ui-field-label">账号代理</span>
                          <p class="mt-1 text-sm text-foreground">{{ proxyMode === 'direct' ? '强制直连' : '使用全局代理' }}</p>
                        </div>
                      </div>

                      <div class="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                        <span>{{ accountProxyPreview }}</span>
                        <Button size="xs" variant="outline" root-class="min-w-16 justify-center" :disabled="proxyProfilesLoading" @click="loadProxyProfiles()">
                          {{ proxyProfilesLoading ? '刷新中...' : '刷新分组' }}
                        </Button>
                        <Button size="xs" variant="outline" root-class="min-w-16 justify-center" :disabled="proxyTesting || proxyProfilesLoading" @click="testAccountProxy">
                          {{ proxyTesting ? '测试中...' : '测试代理' }}
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
              <Button size="xs" variant="primary" root-class="min-w-14 justify-center" :disabled="saving" @click="saveAccount">
                {{ saving ? '保存中...' : '保存' }}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showImportModal" class="fixed inset-0 z-[120] overflow-y-auto bg-black/40 px-3 py-4">
        <div class="flex min-h-full items-center justify-center">
          <div class="ui-surface w-full max-w-[58rem] overflow-hidden shadow-lg">
            <div class="flex items-center justify-between border-b border-border px-5 py-3">
              <h4 class="ui-section-title">导入账号</h4>
              <Button size="xs" variant="outline" root-class="min-w-14 justify-center text-muted-foreground" :disabled="importBusy" @click="closeImportModal">
                关闭
              </Button>
            </div>

            <div class="grid grid-cols-1 gap-0 md:grid-cols-[15rem_1fr]">
              <div class="border-b border-border bg-muted/20 p-3 md:border-b-0 md:border-r">
                <div class="space-y-1">
                  <button
                    v-for="option in importModeOptions"
                    :key="option.value"
                    type="button"
                    class="w-full rounded-xl px-3 py-2 text-left text-sm transition-colors"
                    :class="importMode === option.value ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-card hover:text-foreground'"
                    @click="setImportMode(option.value)"
                  >
                    {{ option.label }}
                  </button>
                </div>
              </div>

              <div class="min-h-[26rem] p-4">
                <div v-if="importMode === 'oauth'" class="space-y-3">
                  <div class="rounded-xl border border-border bg-card p-3">
                    <p class="text-sm font-medium text-foreground">OAuth 登录已有账号（带自动刷新）</p>
                    <p class="mt-1 text-xs text-muted-foreground">用浏览器登录自己的 ChatGPT 账号，回填 callback URL 即可拿到 refresh_token，后台会自动续期。</p>
                  </div>
                  <label class="block text-xs">
                    <span class="ui-field-label">邮箱提示（可选）</span>
                    <Input
                      :model-value="oauthEmailHint"
                      type="email"
                      block
                      :disabled="Boolean(oauthSession) || oauthStarting"
                      placeholder="you@example.com"
                      @update:model-value="oauthEmailHint = $event.trim()"
                    />
                  </label>
                  <div v-if="oauthSession" class="rounded-xl border border-border bg-card p-3">
                    <p class="ui-field-label">授权 URL</p>
                    <p class="max-h-24 overflow-y-auto break-all rounded-lg border border-border bg-muted/30 px-2.5 py-2 font-mono text-[11px] leading-5 text-muted-foreground">
                      {{ oauthSession.authorize_url }}
                    </p>
                    <div class="mt-2 flex flex-wrap gap-2">
                      <Button size="xs" variant="outline" @click="copyOAuthUrl">复制 URL</Button>
                      <Button size="xs" variant="outline" @click="reopenOAuthUrl">再次打开</Button>
                      <Button size="xs" variant="outline" :disabled="oauthStarting" @click="startOAuthLogin">重新生成</Button>
                    </div>
                  </div>
                  <label class="block text-xs">
                    <span class="ui-field-label">Callback URL / Code</span>
                    <textarea
                      v-model.trim="oauthCallback"
                      rows="4"
                      class="ui-textarea-sm font-mono"
                      placeholder="https://platform.openai.com/auth/callback?code=..."
                    ></textarea>
                  </label>
                  <div class="flex justify-end gap-2">
                    <Button size="xs" variant="outline" :disabled="oauthStarting || oauthSubmitting" @click="startOAuthLogin">
                      {{ oauthStarting ? '生成中...' : oauthSession ? '重新生成 URL' : '生成 URL' }}
                    </Button>
                    <Button size="xs" variant="primary" :disabled="oauthSubmitting || !oauthSession || !oauthCallback.trim()" @click="finishOAuthLogin">
                      {{ oauthSubmitting ? '导入中...' : '完成导入' }}
                    </Button>
                  </div>
                </div>

                <div v-else-if="importMode === 'access_token'" class="space-y-3">
                  <div class="rounded-xl border border-border bg-card p-3">
                    <p class="text-sm font-medium text-foreground">导入 Access Token</p>
                    <p class="mt-1 text-xs text-muted-foreground">支持直接粘贴，一行一个；也支持从 TXT 文件读取，一行一个。</p>
                  </div>
                  <textarea
                    v-model.trim="manualTokenText"
                    rows="10"
                    class="ui-textarea-sm font-mono"
                    placeholder="一行一个 access token"
                  ></textarea>
                  <div class="flex flex-wrap justify-end gap-2">
                    <Button size="xs" variant="outline" :disabled="importBusy" @click="openManualTokenFile">
                      读取 TXT 文件
                    </Button>
                    <Button size="xs" variant="primary" :disabled="importBusy || !manualTokenText.trim()" @click="importManualTokenText">
                      {{ importBusy ? '导入中...' : '开始导入' }}
                    </Button>
                  </div>
                </div>

                <div v-else-if="importMode === 'session_json'" class="space-y-3">
                  <div class="rounded-xl border border-border bg-card p-3">
                    <p class="text-sm font-medium text-foreground">导入 Session JSON</p>
                    <p class="mt-1 text-xs text-muted-foreground">从 chatgpt.com 的 session 接口复制完整 JSON，自动提取 accessToken。</p>
                  </div>
                  <textarea v-model.trim="sessionJsonText" rows="12" class="ui-textarea-sm font-mono" placeholder="粘贴完整 session JSON"></textarea>
                  <div class="flex justify-end">
                    <Button size="xs" variant="primary" :disabled="importBusy || !sessionJsonText.trim()" @click="importSessionJson">
                      {{ importBusy ? '导入中...' : '开始导入' }}
                    </Button>
                  </div>
                </div>

                <div v-else-if="importMode === 'codex_json'" class="space-y-3">
                  <div class="rounded-xl border border-border bg-card p-3">
                    <p class="text-sm font-medium text-foreground">导入 Codex 认证 JSON</p>
                    <p class="mt-1 text-xs text-muted-foreground">粘贴 Codex 认证 JSON，导入后账号来源标记为 codex。</p>
                  </div>
                  <textarea v-model.trim="codexJsonText" rows="12" class="ui-textarea-sm font-mono" placeholder="粘贴 Codex auth JSON"></textarea>
                  <div class="flex justify-end">
                    <Button size="xs" variant="primary" :disabled="importBusy || !codexJsonText.trim()" @click="importCodexJson">
                      {{ importBusy ? '导入中...' : '开始导入' }}
                    </Button>
                  </div>
                </div>

                <div v-else-if="importMode === 'cpa_json'" class="space-y-3">
                  <div class="rounded-xl border border-border bg-card p-3">
                    <p class="text-sm font-medium text-foreground">导入 CPA JSON 文件</p>
                    <p class="mt-1 text-xs text-muted-foreground">支持一次多选多个本地 JSON 文件，逐个读取对象里的 access_token 后导入。</p>
                  </div>
                  <div class="rounded-xl border border-dashed border-border bg-card p-6 text-center">
                    <Button size="sm" variant="outline" :disabled="importBusy" @click="openCPAFileDialog">
                      选择 CPA JSON 文件
                    </Button>
                  </div>
                </div>

                <div v-else-if="importMode === 'remote_cpa'" class="space-y-3">
                  <div class="rounded-xl border border-border bg-card p-3">
                    <p class="text-sm font-medium text-foreground">从远程 CPA 服务器导入</p>
                    <p class="mt-1 text-xs text-muted-foreground">前往设置页面配置远程 CPA 服务器后再执行导入。</p>
                  </div>
                  <div class="flex flex-wrap items-center gap-2">
                    <div class="min-w-[14rem] flex-1">
                      <SelectMenu v-model="selectedCPAPoolId" :options="cpaPoolOptions" aria-label="CPA 服务器" />
                    </div>
                    <Button size="xs" variant="outline" :disabled="importBusy" @click="loadCPAPools">刷新服务器</Button>
                    <Button size="xs" variant="outline" :disabled="importBusy || !selectedCPAPoolId" @click="loadCPAFiles">加载文件</Button>
                  </div>
                  <div class="max-h-64 overflow-y-auto rounded-xl border border-border bg-card">
                    <label
                      v-for="file in remoteCPAFiles"
                      :key="file.name"
                      class="flex items-center justify-between gap-3 border-b border-border px-3 py-2 last:border-b-0"
                    >
                      <span class="min-w-0">
                        <span class="block truncate text-sm text-foreground">{{ file.email || file.name }}</span>
                        <span class="block truncate text-xs text-muted-foreground">{{ file.name }}</span>
                      </span>
                      <Checkbox
                        :model-value="selectedCPAFileNames.includes(file.name)"
                        @update:model-value="(checked) => toggleCPAFile(file.name, checked)"
                      />
                    </label>
                    <p v-if="remoteCPAFiles.length === 0" class="px-3 py-8 text-center text-xs text-muted-foreground">
                      暂无可导入文件
                    </p>
                  </div>
                  <div class="flex items-center justify-between gap-3">
                    <p class="text-xs text-muted-foreground">
                      {{ cpaImportJob ? `进度 ${cpaImportJob.completed}/${cpaImportJob.total}，失败 ${cpaImportJob.failed}` : '未开始' }}
                    </p>
                    <Button size="xs" variant="primary" :disabled="importBusy || selectedCPAFileNames.length === 0" @click="startRemoteCPAImport">
                      {{ importBusy ? '导入中...' : '开始导入' }}
                    </Button>
                  </div>
                </div>

                <div v-else-if="importMode === 'sub2api'" class="space-y-3">
                  <div class="rounded-xl border border-border bg-card p-3">
                    <p class="text-sm font-medium text-foreground">从 Sub2API 服务器导入</p>
                    <p class="mt-1 text-xs text-muted-foreground">前往设置页面配置 Sub2API 服务器，再选择其中的 OpenAI 账号导入。</p>
                  </div>
                  <div class="flex flex-wrap items-center gap-2">
                    <div class="min-w-[14rem] flex-1">
                      <SelectMenu v-model="selectedSub2APIServerId" :options="sub2apiServerOptions" aria-label="Sub2API 服务器" />
                    </div>
                    <Button size="xs" variant="outline" :disabled="importBusy" @click="loadSub2APIServers">刷新服务器</Button>
                    <Button size="xs" variant="outline" :disabled="importBusy || !selectedSub2APIServerId" @click="loadSub2APIAccounts">加载账号</Button>
                  </div>
                  <div class="max-h-64 overflow-y-auto rounded-xl border border-border bg-card">
                    <label
                      v-for="account in sub2apiAccounts"
                      :key="account.id"
                      class="flex items-center justify-between gap-3 border-b border-border px-3 py-2 last:border-b-0"
                    >
                      <span class="min-w-0">
                        <span class="block truncate text-sm text-foreground">{{ account.email || account.name || account.id }}</span>
                        <span class="block truncate text-xs text-muted-foreground">{{ account.plan_type || '-' }} · {{ account.status || '-' }}</span>
                      </span>
                      <Checkbox
                        :model-value="selectedSub2APIAccountIds.includes(account.id)"
                        @update:model-value="(checked) => toggleSub2APIAccount(account.id, checked)"
                      />
                    </label>
                    <p v-if="sub2apiAccounts.length === 0" class="px-3 py-8 text-center text-xs text-muted-foreground">
                      暂无可导入账号
                    </p>
                  </div>
                  <div class="flex items-center justify-between gap-3">
                    <p class="text-xs text-muted-foreground">
                      {{ sub2apiImportJob ? `进度 ${sub2apiImportJob.completed}/${sub2apiImportJob.total}，失败 ${sub2apiImportJob.failed}` : '未开始' }}
                    </p>
                    <Button size="xs" variant="primary" :disabled="importBusy || selectedSub2APIAccountIds.length === 0" @click="startSub2APIImport">
                      {{ importBusy ? '导入中...' : '开始导入' }}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showRefreshProgress" class="fixed inset-0 z-[140] flex items-center justify-center bg-black/40 px-3">
        <div class="ui-surface w-full max-w-[34rem] overflow-hidden shadow-lg">
          <div class="flex items-center justify-between border-b border-border px-5 py-3">
            <h4 class="ui-section-title">{{ refreshProgressTitle || '刷新账号信息和额度' }}</h4>
            <Button
              size="xs"
              variant="outline"
              root-class="min-w-14 justify-center text-muted-foreground"
              :disabled="batchBusy && !refreshProgress?.done"
              @click="closeRefreshProgress"
            >
              关闭
            </Button>
          </div>
          <div class="space-y-4 px-5 py-4">
            <div class="flex items-center justify-between text-xs text-muted-foreground">
              <span>{{ refreshProgress?.processed || 0 }} / {{ refreshProgress?.total || 0 }}</span>
              <span>{{ refreshProgressPercent }}%</span>
            </div>
            <div class="h-2 overflow-hidden rounded-full bg-muted">
              <div class="h-full rounded-full bg-primary transition-all" :style="{ width: `${refreshProgressPercent}%` }"></div>
            </div>
            <div class="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
              <div class="rounded-xl border border-border bg-card px-3 py-2">
                <p>{{ refreshProgressTitle.includes('恢复') ? '处理账号' : '图片总额度' }}</p>
                <p class="mt-1 text-base font-semibold text-foreground">
                  {{ refreshProgressTitle.includes('恢复') ? `${refreshProgress?.processed || 0} 个` : (refreshProgress?.total_quota ?? '-') }}
                </p>
              </div>
              <div class="rounded-xl border border-border bg-card px-3 py-2">
                <p>状态</p>
                <p class="mt-1 text-base font-semibold text-foreground">{{ refreshProgress?.done ? '已完成' : (refreshProgressTitle.includes('恢复') ? '恢复中' : '刷新中') }}</p>
              </div>
            </div>
            <p v-if="refreshProgress?.error" class="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-600">
              {{ refreshProgress.error }}
            </p>
          </div>
        </div>
      </div>
    </Teleport>

    <input ref="manualTokenFileInputRef" type="file" accept=".txt,text/plain" class="hidden" @change="handleManualTokenFileChange" />
    <input ref="cpaFileInputRef" type="file" accept=".json,application/json" multiple class="hidden" @change="handleCPAFileChange" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Button, Checkbox, EmptyState, FilterSelect, Input, KeyValueList, SelectMenu, StatusDetailPill, StatusPill, ToolbarShell } from 'nanocat-ui'
import type { ActionMenuItem } from 'nanocat-ui'
import { AccountActionButtons, AccountBulkBar, AccountSelectionSummary, ListPagination, QuotaBadge } from '@/components/ai'
import { useAccountsPage } from './accounts/useAccountsPage'
import {
  accountCreatedText,
  accountPrimaryText,
  accountProxyText,
  accountQuotaText,
  accountRestoreText,
  accountSecondaryText,
  accountSourceText,
  accountTokenPreview,
  rowClass,
  statusClass,
  statusRawError,
  statusReason,
  statusText,
} from './accounts/viewUtils'

const {
  loading,
  saving,
  showModal,
  keyword,
  statusFilter,
  statusFilterOptions,
  editingId,
  accounts,
  selectedCount,
  abnormalAccountCount,
  allVisibleSelected,
  currentPage,
  pageSize,
  pageSizeOptions,
  batchBusy,
  batchActionLabel,
  viewMode,
  refreshingAccountId,
  resettingAccountId,
  reloginingAccountId,
  importBusy,
  exportBusy,
  showImportModal,
  importMode,
  importModeOptions,
  manualTokenText,
  sessionJsonText,
  codexJsonText,
  remoteCPAFiles,
  selectedCPAPoolId,
  selectedCPAFileNames,
  cpaImportJob,
  sub2apiAccounts,
  selectedSub2APIServerId,
  selectedSub2APIAccountIds,
  sub2apiImportJob,
  proxyProfilesLoading,
  proxyTesting,
  proxyMode,
  accountProxyModeOptions,
  proxyProfileOptions,
  selectedProxyProfileId,
  customProxyInput,
  accountProxyPreview,
  showRefreshProgress,
  refreshProgressTitle,
  refreshProgress,
  refreshProgressPercent,
  cpaPoolOptions,
  sub2apiServerOptions,
  oauthStarting,
  oauthSubmitting,
  oauthEmailHint,
  oauthCallback,
  oauthSession,
  accountStatusOptions,
  form,
  filteredAccounts,
  pagedAccounts,
  loadData,
  setViewMode,
  isSelected,
  toggleSelect,
  clearSelection,
  toggleSelectAllVisible,
  setImportMode,
  openImportModal,
  closeImportModal,
  loadProxyProfiles,
  testAccountProxy,
  setProxyMode,
  selectProxyProfile,
  setCustomProxyInput,
  importManualTokenText,
  importTokenTextFile,
  importSessionJson,
  importCodexJson,
  importLocalCPAFiles,
  loadCPAPools,
  loadCPAFiles,
  toggleCPAFile,
  startRemoteCPAImport,
  loadSub2APIServers,
  loadSub2APIAccounts,
  toggleSub2APIAccount,
  startSub2APIImport,
  refreshAllAccounts,
  reLoginAbnormalAccounts,
  reLoginAccount,
  closeRefreshProgress,
  openCreateModal,
  openEditModal,
  closeModal,
  startOAuthLogin,
  finishOAuthLogin,
  copyOAuthUrl,
  reopenOAuthUrl,
  saveAccount,
  toggleEnabled,
  refreshToken,
  resetAccountState,
  removeAccount,
  runBulkAction,
  exportAccounts,
} = useAccountsPage()

type BatchAction = 'refresh' | 'relogin' | 'reset' | 'enable' | 'disable' | 'delete'

const manualTokenFileInputRef = ref<HTMLInputElement | null>(null)
const cpaFileInputRef = ref<HTMLInputElement | null>(null)

const batchMenuItems: ActionMenuItem[] = [
  { key: 'refresh', label: '批量刷新账号信息和额度' },
  { key: 'relogin', label: '批量恢复异常账号' },
  { key: 'reset', label: '批量重置' },
  { key: 'enable', label: '批量启用', dividerBefore: true },
  { key: 'disable', label: '批量禁用' },
  { key: 'delete', label: '批量删除', danger: true },
]

async function handleBatchAction(action: BatchAction) {
  await runBulkAction(action)
}

async function handleExportSelected() {
  await exportAccounts('selected')
}

async function handleExportAll() {
  await exportAccounts('all')
}

function openManualTokenFile() {
  if (!manualTokenFileInputRef.value || importBusy.value) return
  manualTokenFileInputRef.value.value = ''
  manualTokenFileInputRef.value.click()
}

async function handleManualTokenFileChange(event: Event) {
  const target = event.target as HTMLInputElement | null
  const file = target?.files?.[0]
  await importTokenTextFile(file)
  if (target) target.value = ''
}

function openCPAFileDialog() {
  if (!cpaFileInputRef.value || importBusy.value) return
  cpaFileInputRef.value.value = ''
  cpaFileInputRef.value.click()
}

async function handleCPAFileChange(event: Event) {
  const target = event.target as HTMLInputElement | null
  await importLocalCPAFiles(target?.files)
  if (target) target.value = ''
}
</script>

<template>
  <div class="relative space-y-8">
    <PagePanel class="space-y-5">
      <div class="accounts-toolbar">
        <div class="accounts-toolbar-row accounts-toolbar-row-main">
          <FilterToolbar class="accounts-toolbar-filters" :bordered="false">
            <Input
              :model-value="keyword"
              type="text"
              placeholder="搜索账号 ID / 邮箱 / Token / 类型 / 来源"
              block
              root-class="min-w-[14rem] flex-1 md:max-w-sm"
              @update:model-value="keyword = $event.trim()"
            />
            <FilterSelect
              v-model="statusFilter"
              :options="statusFilterOptions"
              placeholder="状态筛选"
              aria-label="账号状态筛选"
            />
            <FilterSelect
              v-model="groupFilter"
              :options="groupFilterOptions"
              placeholder="账号组"
              aria-label="账号组筛选"
            />
          </FilterToolbar>

          <div class="accounts-toolbar-summary">
            <AccountSelectionSummary
              :all-selected="allVisibleSelected"
              :total-count="accountListTotal"
              :selected-count="selectedCount"
              :view-mode="viewMode"
              @toggle-all="toggleSelectAllVisible"
              @update:view-mode="setViewMode"
            />
          </div>
        </div>

        <div class="accounts-toolbar-row accounts-toolbar-row-actions">
          <div class="accounts-toolbar-action-cluster">
            <FilterToolbar class="accounts-toolbar-group accounts-toolbar-group-binding" :bordered="false" gap="tight">
              <FloatingActionMenu
                :label="bindAccountGroupLabel"
                :items="bindAccountGroupMenuItems"
                :disabled="accountGroupsLoading"
                align="left"
                aria-label="绑定账号组"
                :trigger-class="accountToolbarMenuClass"
                @select="selectBindAccountGroup"
              />
              <Button
                size="sm"
                variant="outline"
                :root-class="accountToolbarButtonClass"
                :disabled="selectedCount === 0 || batchBusy || accountGroupsLoading"
                @click="bindSelectedAccountsToGroup"
              >
                绑定分组
              </Button>
              <Button
                size="sm"
                variant="outline"
                :root-class="accountToolbarButtonClass"
                :disabled="accountGroupsLoading"
                @click="openAccountGroupsModal"
              >
                账号组管理
              </Button>
            </FilterToolbar>

            <FilterToolbar class="accounts-toolbar-group accounts-toolbar-group-ops" :bordered="false" gap="tight">
              <FloatingActionMenu
                label="导入 / 添加"
                :items="accountEntryItems"
                :disabled="importBusy"
                align="left"
                :trigger-class="accountToolbarMenuClass"
                @select="handleAccountEntryAction"
              />
              <FloatingActionMenu
                label="批量操作"
                :items="topBatchItems"
                :disabled="loading || batchBusy"
                align="left"
                :trigger-class="accountToolbarMenuClass"
                @select="handleTopBatchAction"
              />
              <FloatingActionMenu
                label="导出"
                :items="exportMenuItems"
                :disabled="exportBusy"
                align="left"
                :trigger-class="accountToolbarMenuClass"
                @select="handleExportAction"
              />
            </FilterToolbar>
          </div>

          <FilterToolbar class="accounts-toolbar-group accounts-toolbar-group-refresh" :bordered="false" gap="tight">
            <Button
              size="sm"
              variant="outline"
              :root-class="accountToolbarSecondaryClass"
              :disabled="loading"
              @click="loadData"
            >
              刷新列表
            </Button>
          </FilterToolbar>
        </div>
      </div>

      <StateBlock v-if="loading && filteredAccounts.length === 0">
        加载中...
      </StateBlock>

      <TableShell v-else-if="viewMode === 'list'">
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
                <button
                  type="button"
                  class="text-left"
                  title="点击复制完整 Token"
                  @click="copyAccountToken(item)"
                >
                  <StatusPill
                    :label="accountTokenPreview(item)"
                    tone-class="border-muted bg-muted/20 text-muted-foreground"
                    title="Access Token"
                    detail="点击复制完整 Token"
                    card-class="w-48"
                  />
                </button>
              </td>
              <td class="py-4 pr-5 align-top">
                <div class="space-y-1 text-xs">
                  <p class="font-medium text-foreground">{{ accountSourceText(item) }}</p>
                  <p class="max-w-[13rem] truncate text-muted-foreground">{{ accountGroupLabel(item.group_id) }}</p>
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
      </TableShell>

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
            <button
              type="button"
              class="text-left"
              title="点击复制完整 Token"
              @click="copyAccountToken(item)"
            >
              <StatusPill
                :label="accountTokenPreview(item)"
                tone-class="border-muted bg-muted/20 text-muted-foreground"
                title="Access Token"
                detail="点击复制完整 Token"
                card-class="w-48"
              />
            </button>
          </div>

          <KeyValueList
            :items="[
              { label: '创建时间', value: accountCreatedText(item) },
              { label: '账号组', value: accountGroupLabel(item.group_id) },
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
        :total-count="accountListTotal"
        :page-size-options="pageSizeOptions"
        unit="个账号"
        :disabled="loading"
      />
    </PagePanel>

    <AccountBulkBar
      :selected-count="selectedCount"
      :busy="batchBusy"
      :busy-label="batchActionLabel"
      :items="batchMenuItems"
      @select="handleBatchAction"
      @clear="clearSelection"
    />

    <ModalShell :open="showModal" max-width="44rem" :z-index="120">
            <ModalHeader :title="editingId ? '编辑账号' : '添加账号'" :bordered="false" compact @close="closeModal" />

            <ModalBody density="compact" class="space-y-3">
                <FormSection title="基础信息" surface="plain">
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
                </FormSection>

                <FormSection surface="plain">
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
                </FormSection>

                <FormSection title="调度属性" surface="plain">
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
                    <label class="text-xs">
                      <span class="ui-field-label">账号组</span>
                      <SelectMenu
                        v-model="form.group_id"
                        :options="accountGroupOptions"
                        :disabled="accountGroupsLoading"
                        aria-label="账号组"
                        class="w-full"
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

                        <label v-if="proxyMode === 'group'">
                          <span class="ui-field-label">代理组（多节点）</span>
                          <SelectMenu
                            :model-value="selectedProxyGroupId"
                            :options="proxyGroupOptions"
                            :disabled="accountGroupsLoading"
                            aria-label="代理组"
                            class="w-full"
                            @update:model-value="selectProxyGroup"
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

                        <SurfaceBox v-else tone="muted" dashed density="compact" class="flex min-h-[3.25rem] items-center">
                          {{ proxyMode === 'direct' ? '该账号强制直连，不读取账号组或全局代理。' : '该账号不单独指定代理，会按账号组代理组、全局代理顺序回退。' }}
                        </SurfaceBox>
                      </div>

                      <SurfaceBox tone="muted" density="compact" class="flex flex-wrap items-center justify-between gap-2">
                        <div class="min-w-0">
                          <span class="ui-field-label">当前代理</span>
                          <p class="mt-1 max-w-full truncate text-xs text-foreground" :title="accountProxyPreview">{{ accountProxyPreview }}</p>
                        </div>
                        <div class="flex flex-wrap items-center gap-2">
                          <Button
                            v-if="proxyMode === 'group'"
                            size="xs"
                            variant="outline"
                            root-class="min-w-24 justify-center"
                            :disabled="accountGroupsLoading"
                            @click="loadAccountGroups()"
                          >
                            {{ accountGroupsLoading ? '刷新中...' : '刷新代理组' }}
                          </Button>
                          <Button
                            v-if="proxyMode !== 'direct'"
                            size="xs"
                            variant="outline"
                            root-class="min-w-24 justify-center"
                            :disabled="proxyTesting || accountGroupsLoading"
                            @click="testAccountProxy"
                          >
                            {{ proxyTesting ? '测试中...' : '测试当前代理' }}
                          </Button>
                          <span v-else class="text-[11px] text-muted-foreground">直连模式无需测试代理</span>
                        </div>
                      </SurfaceBox>
                    </div>
                  </div>
                </FormSection>
            </ModalBody>

            <ModalFooter :bordered="false">
              <Button size="xs" variant="primary" root-class="min-w-14 justify-center" :disabled="saving" @click="saveAccount">
                {{ saving ? '保存中...' : '保存' }}
              </Button>
            </ModalFooter>
    </ModalShell>

    <ModalShell :open="showAccountGroupsModal" max-width="58rem" :z-index="130">
            <ModalHeader
              title="账号组管理"
              subtitle="先创建账号组，再在账号列表勾选账号批量绑定。"
              :close-disabled="accountGroupSaving"
              compact
              @close="closeAccountGroupsModal"
            />

            <div class="grid grid-cols-1 gap-0 md:grid-cols-[18rem_1fr]">
              <div class="border-b border-border bg-muted/20 p-4 md:border-b-0 md:border-r">
                <div class="space-y-3">
                  <p class="text-sm font-medium text-foreground">
                    {{ editingAccountGroupId ? '编辑账号组' : '新建账号组' }}
                  </p>

                  <label class="block text-xs">
                    <span class="ui-field-label">账号组名称</span>
                    <Input
                      :model-value="accountGroupForm.name"
                      block
                      placeholder="微软账号 / 域名邮箱 / Codex"
                      @update:model-value="accountGroupForm.name = $event.trim()"
                    />
                  </label>

                  <label class="block text-xs">
                    <span class="ui-field-label">默认代理组</span>
                    <SelectMenu
                      v-model="accountGroupForm.proxy_group_id"
                      :options="accountGroupProxyOptions"
                      :disabled="accountGroupsLoading"
                      aria-label="默认代理组"
                      class="w-full"
                    />
                  </label>

                  <SurfaceBox tag="label" density="compact" class="flex items-center gap-2">
                    <Checkbox
                      :model-value="accountGroupForm.enabled"
                      @update:model-value="accountGroupForm.enabled = Boolean($event)"
                    />
                    启用账号组
                  </SurfaceBox>

                  <label class="block text-xs">
                    <span class="ui-field-label">备注</span>
                    <textarea
                      v-model.trim="accountGroupForm.notes"
                      rows="3"
                      class="ui-textarea-sm"
                      placeholder="例如：微软 webfree 注册账号，默认走香港代理池"
                    ></textarea>
                  </label>

                  <Button size="sm" variant="primary" root-class="w-full justify-center" :disabled="accountGroupSaving" @click="saveAccountGroup">
                    {{ accountGroupSaving ? '保存中...' : editingAccountGroupId ? '保存账号组' : '创建账号组' }}
                  </Button>
                </div>
              </div>

              <div class="max-h-[32rem] overflow-y-auto p-4">
                <StateBlock v-if="accountGroupRows.length === 0" dashed>
                  还没有账号组。先在左侧创建，比如微软账号、域名邮箱、Codex。
                </StateBlock>

                <div v-else class="space-y-2">
                  <InfoCard
                    v-for="group in accountGroupRows"
                    :key="group.id"
                    tag="article"
                    density="compact"
                  >
                    <div class="flex flex-wrap items-start justify-between gap-3">
                      <div class="min-w-0">
                        <div class="flex flex-wrap items-center gap-2">
                          <p class="font-medium text-foreground">{{ group.name }}</p>
                          <StateBadge :tone="group.enabled ? 'success' : 'muted'" size="xs">
                            {{ group.enabled ? '启用' : '停用' }}
                          </StateBadge>
                        </div>
                        <p class="mt-1 text-xs text-muted-foreground">
                          {{ group.account_count }} 个账号 · 默认代理：{{ group.proxy_label }}
                        </p>
                        <p v-if="group.notes" class="mt-1 line-clamp-2 text-xs text-muted-foreground">{{ group.notes }}</p>
                      </div>

                      <div class="flex shrink-0 items-center gap-2">
                        <Button size="xs" variant="outline" :disabled="accountGroupSaving" @click="editAccountGroup(group.raw)">
                          编辑
                        </Button>
                        <Button size="xs" variant="outline" root-class="text-rose-600" :disabled="accountGroupSaving" @click="deleteAccountGroup(group.raw)">
                          删除
                        </Button>
                      </div>
                    </div>
                  </InfoCard>
                </div>
              </div>
            </div>
    </ModalShell>

    <ModalShell :open="showImportModal" max-width="58rem" :z-index="120">
            <ModalHeader title="导入账号" :close-disabled="importBusy" compact @close="closeImportModal" />

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
                  <ImportModePanel
                    title="OAuth 登录已有账号（带自动刷新）"
                    description="用浏览器登录自己的 ChatGPT 账号，回填 callback URL 即可拿到 refresh_token，后台会自动续期。"
                  />
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
                  <InfoCard v-if="oauthSession" title="授权 URL" density="compact">
                    <template #actions>
                      <Button size="xs" variant="outline" @click="copyOAuthUrl">复制 URL</Button>
                      <Button size="xs" variant="outline" @click="reopenOAuthUrl">再次打开</Button>
                      <Button size="xs" variant="outline" :disabled="oauthStarting" @click="startOAuthLogin">重新生成</Button>
                    </template>
                    <SurfaceBox tag="p" tone="muted" density="compact" scroll mono wrap class="leading-5">
                      {{ oauthSession.authorize_url }}
                    </SurfaceBox>
                  </InfoCard>
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
                  <ImportModePanel
                    title="导入 Access Token"
                    description="支持直接粘贴，一行一个；也支持从 TXT 文件读取，一行一个。"
                  />
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
                  <ImportModePanel
                    title="导入 Session JSON"
                    description="从 chatgpt.com 的 session 接口复制完整 JSON，自动提取 accessToken。"
                  />
                  <textarea v-model.trim="sessionJsonText" rows="12" class="ui-textarea-sm font-mono" placeholder="粘贴完整 session JSON"></textarea>
                  <div class="flex justify-end">
                    <Button size="xs" variant="primary" :disabled="importBusy || !sessionJsonText.trim()" @click="importSessionJson">
                      {{ importBusy ? '导入中...' : '开始导入' }}
                    </Button>
                  </div>
                </div>

                <div v-else-if="importMode === 'codex_json'" class="space-y-3">
                  <ImportModePanel
                    title="导入 Codex 认证 JSON"
                    description="粘贴 Codex 认证 JSON，导入后账号来源标记为 codex。"
                  />
                  <textarea v-model.trim="codexJsonText" rows="12" class="ui-textarea-sm font-mono" placeholder="粘贴 Codex auth JSON"></textarea>
                  <div class="flex justify-end">
                    <Button size="xs" variant="primary" :disabled="importBusy || !codexJsonText.trim()" @click="importCodexJson">
                      {{ importBusy ? '导入中...' : '开始导入' }}
                    </Button>
                  </div>
                </div>

                <div v-else-if="importMode === 'cpa_json'" class="space-y-3">
                  <ImportModePanel
                    title="导入 CPA JSON 文件"
                    description="支持一次多选多个本地 JSON 文件，逐个读取对象里的 access_token 后导入。"
                  />
                  <StateBlock dashed compact>
                    <Button size="sm" variant="outline" :disabled="importBusy" @click="openCPAFileDialog">
                      选择 CPA JSON 文件
                    </Button>
                  </StateBlock>
                </div>

                <div v-else-if="importMode === 'remote_cpa'" class="space-y-3">
                  <ImportModePanel
                    title="从远程 CPA 服务器导入"
                    description="前往设置页面配置远程 CPA 服务器后再执行导入。"
                  />
                  <div class="flex flex-wrap items-center gap-2">
                    <div class="min-w-[14rem] flex-1">
                      <SelectMenu v-model="selectedCPAPoolId" :options="cpaPoolOptions" aria-label="CPA 服务器" />
                    </div>
                    <Button size="xs" variant="outline" :disabled="importBusy" @click="loadCPAPools">刷新服务器</Button>
                    <Button size="xs" variant="outline" :disabled="importBusy || !selectedCPAPoolId" @click="loadCPAFiles">加载文件</Button>
                  </div>
                  <SelectableListPanel
                    :has-items="remoteCPAFiles.length > 0"
                    empty-text="暂无可导入文件"
                  >
                    <label
                      v-for="file in remoteCPAFiles"
                      :key="file.name"
                      class="selectable-list-panel-row"
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
                  </SelectableListPanel>
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
                  <ImportModePanel
                    title="从 Sub2API 服务器导入"
                    description="前往设置页面配置 Sub2API 服务器，再选择其中的 OpenAI 账号导入。"
                  />
                  <div class="flex flex-wrap items-center gap-2">
                    <div class="min-w-[14rem] flex-1">
                      <SelectMenu v-model="selectedSub2APIServerId" :options="sub2apiServerOptions" aria-label="Sub2API 服务器" />
                    </div>
                    <Button size="xs" variant="outline" :disabled="importBusy" @click="loadSub2APIServers">刷新服务器</Button>
                    <Button size="xs" variant="outline" :disabled="importBusy || !selectedSub2APIServerId" @click="loadSub2APIAccounts">加载账号</Button>
                  </div>
                  <SelectableListPanel
                    :has-items="sub2apiAccounts.length > 0"
                    empty-text="暂无可导入账号"
                  >
                    <label
                      v-for="account in sub2apiAccounts"
                      :key="account.id"
                      class="selectable-list-panel-row"
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
                  </SelectableListPanel>
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
    </ModalShell>

    <ModalShell :open="showRefreshProgress" max-width="34rem" :z-index="140">
          <ModalHeader
            :title="refreshProgressTitle || '刷新账号信息和额度'"
            :close-disabled="batchBusy && !refreshProgress?.done"
            compact
            @close="closeRefreshProgress"
          >
            <template #actions>
              <Button
                v-if="canStopRefreshProgress"
                size="xs"
                variant="outline"
                root-class="min-w-14 justify-center text-amber-600"
                :disabled="bulkStopRequested"
                @click="requestStopRefreshProgress"
              >
                {{ bulkStopRequested ? '停止中...' : '停止' }}
              </Button>
            </template>
          </ModalHeader>
          <div class="space-y-4 px-5 py-4">
            <div class="flex items-center justify-between text-xs text-muted-foreground">
              <span>{{ refreshProgress?.processed || 0 }} / {{ refreshProgress?.total || 0 }}</span>
              <span>{{ refreshProgressPercent }}%</span>
            </div>
            <ProgressBar :value="refreshProgressPercent" aria-label="账号刷新进度" />
            <MetricStrip :items="refreshProgressItems" columns-class="grid-cols-2" density="compact" />
            <SurfaceBox v-if="refreshProgress?.error" tag="p" tone="danger" density="compact">
              {{ refreshProgress.error }}
            </SurfaceBox>
          </div>
    </ModalShell>

    <input ref="manualTokenFileInputRef" type="file" accept=".txt,text/plain" class="hidden" @change="handleManualTokenFileChange" />
    <input ref="cpaFileInputRef" type="file" accept=".json,application/json" multiple class="hidden" @change="handleCPAFileChange" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, Checkbox, EmptyState, FilterSelect, Input, KeyValueList, SelectMenu, StatusDetailPill, StatusPill } from 'nanocat-ui'
import type { ActionMenuItem } from 'nanocat-ui'
import { AccountActionButtons, AccountBulkBar, AccountSelectionSummary, FilterToolbar, FloatingActionMenu, FormSection, ImportModePanel, InfoCard, ListPagination, MetricStrip, ModalBody, ModalFooter, ModalHeader, ModalShell, PagePanel, ProgressBar, QuotaBadge, SelectableListPanel, StateBadge, StateBlock, SurfaceBox, TableShell, actionMenuGroups } from '@/components/ai'
import { useAccountsPage, type AccountImportMode } from './accounts/useAccountsPage'
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
  groupFilter,
  statusFilterOptions,
  groupFilterOptions,
  editingId,
  accounts,
  accountListTotal,
  accountAllTotal,
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
  accountGroups,
  proxyGroups,
  accountGroupsLoading,
  showAccountGroupsModal,
  accountGroupSaving,
  editingAccountGroupId,
  accountGroupForm,
  accountGroupOptions,
  accountGroupProxyOptions,
  bindAccountGroupOptions,
  selectedBindGroupId,
  proxyTesting,
  proxyMode,
  accountProxyModeOptions,
  proxyGroupOptions,
  selectedProxyGroupId,
  customProxyInput,
  accountProxyPreview,
  showRefreshProgress,
  refreshProgressTitle,
  refreshProgress,
  refreshProgressPercent,
  refreshProgressMetricLabel,
  refreshProgressMetricValue,
  refreshProgressStatusText,
  canStopRefreshProgress,
  bulkStopRequested,
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
  loadAccountGroups,
  setViewMode,
  isSelected,
  toggleSelect,
  clearSelection,
  toggleSelectAllVisible,
  setImportMode,
  openImportModal,
  closeImportModal,
  testAccountProxy,
  openAccountGroupsModal,
  closeAccountGroupsModal,
  resetAccountGroupForm,
  editAccountGroup,
  saveAccountGroup,
  deleteAccountGroup,
  setProxyMode,
  selectProxyGroup,
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
  requestStopRefreshProgress,
  closeRefreshProgress,
  copyAccountToken,
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
  bindSelectedAccountsToGroup,
  exportAccounts,
} = useAccountsPage()

type BatchAction = 'refresh' | 'relogin' | 'reset' | 'enable' | 'disable' | 'delete'

const manualTokenFileInputRef = ref<HTMLInputElement | null>(null)
const cpaFileInputRef = ref<HTMLInputElement | null>(null)
const accountToolbarMenuClass = 'shrink-0 whitespace-nowrap'
const accountToolbarButtonClass = 'shrink-0 whitespace-nowrap justify-between gap-2'
const accountToolbarSecondaryClass = `${accountToolbarButtonClass} text-muted-foreground`

const accountGroupNameMap = computed(() => new Map(
  accountGroups.value.map((group) => [group.id, group.name || group.id]),
))

const accountGroupRows = computed(() => accountGroups.value.map((group) => {
  const proxyGroupId = String(group.proxy_group_id || '').trim()
  const proxyGroup = proxyGroups.value.find((item) => item.id === proxyGroupId)
  return {
    ...group,
    raw: group,
    name: group.name || group.id,
    account_count: Number(group.account_count || 0),
    proxy_label: proxyGroupId ? (proxyGroup?.name || proxyGroupId) : '不绑定代理组',
  }
}))

function accountGroupLabel(groupId: string | undefined) {
  const id = String(groupId || '').trim()
  if (!id) return '未分组'
  return accountGroupNameMap.value.get(id) || id
}

const bindAccountGroupLabel = computed(() => {
  const selected = String(selectedBindGroupId.value || '').trim()
  if (!selected) return '选择账号组'
  if (selected === '__ungrouped__') return '取消分组'
  return accountGroups.value.find((group) => group.id === selected)?.name || selected
})

const refreshProgressItems = computed(() => [
  {
    key: 'metric',
    label: refreshProgressMetricLabel.value,
    value: refreshProgressMetricValue.value,
  },
  {
    key: 'status',
    label: '状态',
    value: refreshProgressStatusText.value,
  },
])

const bindAccountGroupMenuItems = computed<ActionMenuItem[]>(() => {
  const normalOptions = bindAccountGroupOptions.value.filter((option) => option.value && option.value !== '__ungrouped__')
  const ungroupedOptions = bindAccountGroupOptions.value.filter((option) => option.value === '__ungrouped__')

  return actionMenuGroups(
    normalOptions.map((option) => ({ key: option.value, label: option.label })),
    ungroupedOptions.map((option) => ({ key: option.value, label: option.label })),
  )
})

function selectBindAccountGroup(key: string) {
  selectedBindGroupId.value = key
}

const importActionKeys = new Set<AccountImportMode>([
  'oauth',
  'access_token',
  'session_json',
  'codex_json',
  'cpa_json',
  'remote_cpa',
  'sub2api',
])

const accountEntryItems = computed<ActionMenuItem[]>(() => actionMenuGroups(
  [
    { key: 'create', label: '手动添加账号' },
  ],
  [
    { key: 'oauth', label: 'OAuth 登录已有账号' },
    { key: 'access_token', label: '导入 Access Token' },
    { key: 'session_json', label: '导入 Session JSON' },
    { key: 'codex_json', label: '导入 Codex 认证 JSON' },
    { key: 'cpa_json', label: '导入 CPA JSON 文件' },
    { key: 'remote_cpa', label: '从远程 CPA 导入' },
    { key: 'sub2api', label: '从 Sub2API 导入' },
  ],
))

const topBatchItems = computed<ActionMenuItem[]>(() => actionMenuGroups(
  [
    {
      key: 'refresh_all',
      label: '刷新所有账号信息和额度',
      disabled: accountAllTotal.value === 0,
    },
    {
      key: 'relogin_abnormal',
      label: `恢复异常账号${abnormalAccountCount.value ? ` (${abnormalAccountCount.value})` : ''}`,
      disabled: abnormalAccountCount.value === 0,
    },
  ],
  [
    {
      key: 'selected_refresh',
      label: `刷新选中账号${selectedCount.value ? ` (${selectedCount.value})` : ''}`,
      disabled: selectedCount.value === 0,
    },
    {
      key: 'selected_relogin',
      label: '恢复选中异常账号',
      disabled: selectedCount.value === 0,
    },
    {
      key: 'selected_reset',
      label: '重置选中账号状态',
      disabled: selectedCount.value === 0,
    },
  ],
  [
    {
      key: 'selected_enable',
      label: '启用选中账号',
      disabled: selectedCount.value === 0,
    },
    {
      key: 'selected_disable',
      label: '禁用选中账号',
      disabled: selectedCount.value === 0,
    },
    {
      key: 'selected_delete',
      label: '删除选中账号',
      disabled: selectedCount.value === 0,
      danger: true,
    },
  ],
))

const exportMenuItems = computed<ActionMenuItem[]>(() => actionMenuGroups(
  [
    {
      key: 'selected',
      label: `导出选中${selectedCount.value ? ` (${selectedCount.value})` : ''}`,
      disabled: selectedCount.value === 0,
    },
  ],
  [
    {
      key: 'all',
      label: '导出全部',
      disabled: accountAllTotal.value === 0,
    },
  ],
))

const batchMenuItems: ActionMenuItem[] = actionMenuGroups(
  [
    { key: 'refresh', label: '批量刷新账号信息和额度' },
    { key: 'relogin', label: '批量恢复异常账号' },
    { key: 'reset', label: '批量重置' },
  ],
  [
    { key: 'enable', label: '批量启用' },
    { key: 'disable', label: '批量禁用' },
    { key: 'delete', label: '批量删除', danger: true },
  ],
)

async function handleBatchAction(action: BatchAction) {
  await runBulkAction(action)
}

function handleAccountEntryAction(key: string) {
  if (key === 'create') {
    openCreateModal()
    return
  }
  if (importActionKeys.has(key as AccountImportMode)) {
    openImportModal(key as AccountImportMode)
  }
}

async function handleTopBatchAction(key: string) {
  if (key === 'refresh_all') {
    await refreshAllAccounts()
    return
  }
  if (key === 'relogin_abnormal') {
    await reLoginAbnormalAccounts()
    return
  }
  const selectedActionMap: Record<string, BatchAction> = {
    selected_refresh: 'refresh',
    selected_relogin: 'relogin',
    selected_reset: 'reset',
    selected_enable: 'enable',
    selected_disable: 'disable',
    selected_delete: 'delete',
  }
  const action = selectedActionMap[key]
  if (action) {
    await runBulkAction(action)
  }
}

async function handleExportAction(key: string) {
  if (key === 'selected') {
    await handleExportSelected()
    return
  }
  if (key === 'all') {
    await handleExportAll()
  }
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

<style scoped>
.accounts-toolbar {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.accounts-toolbar-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.accounts-toolbar-row-main {
  justify-content: space-between;
}

.accounts-toolbar-row-actions {
  align-items: flex-start;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid hsl(var(--border) / 0.62);
}

.accounts-toolbar-filters {
  min-width: min(100%, 34rem);
  flex: 1 1 34rem;
}

.accounts-toolbar-summary {
  display: flex;
  flex: 0 0 auto;
  justify-content: flex-end;
}

.accounts-toolbar-group {
  min-width: 0;
}

.accounts-toolbar-action-cluster {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}

.accounts-toolbar-group-binding {
  padding-right: 12px;
  border-right: 1px solid hsl(var(--border) / 0.7);
}

.accounts-toolbar-group-ops {
  flex: 0 1 auto;
}

.accounts-toolbar-group-refresh {
  margin-left: auto;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .accounts-toolbar-summary {
    width: 100%;
    justify-content: flex-start;
  }

  .accounts-toolbar-group-binding {
    padding-right: 0;
    border-right: 0;
  }

  .accounts-toolbar-group-refresh {
    width: 100%;
    margin-left: 0;
    justify-content: flex-start;
  }
}
</style>

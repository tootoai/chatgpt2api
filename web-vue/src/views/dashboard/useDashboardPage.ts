import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { statsApi } from '@/api'
import {
  getLineChartTheme,
  getPieChartTheme,
  createLineSeries,
  createPieDataItem,
  chartColors,
  getModelColor,
  filterValidModels,
} from '@/lib/chartTheme'


export function useDashboardPage() {
  type ChartInstance = {
    setOption: (
      option: unknown,
      opts?: boolean | { notMerge?: boolean; lazyUpdate?: boolean; replaceMerge?: string[] }
    ) => void
    resize: () => void
    dispose: () => void
    clear?: () => void
    off?: (eventName: string) => void
    on?: (eventName: string, handler: (params: any) => void) => void
    dispatchAction?: (payload: Record<string, unknown>) => void
  }
  type RenderMode = 'initial' | 'range' | 'refresh'
  type ChartType = 'hourlyRequests' | 'trend' | 'successRate' | 'model' | 'modelRank' | 'responseTime'
  type OverviewPayload = Record<string, any>

  // 时间范围选择
  const timeRanges = [
    { label: '24小时', value: '24h' },
    { label: '7天', value: '7d' },
    { label: '30天', value: '30d' },
  ]

  // 每个图表独立的时间范围
  const timeRangeHourlyRequests = ref('24h')
  const timeRangeTrend = ref('24h')
  const timeRangeSuccessRate = ref('24h')
  const timeRangeModel = ref('24h')
  const timeRangeModelRank = ref('24h')
  const timeRangeResponseTime = ref('24h')

  // 创建图表监听器的工厂函数
  function createChartWatcher(chartType: ChartType, updateFn: (mode?: RenderMode) => void) {
    return async (newVal: string) => {
      await loadChartData(chartType, newVal)
      updateFn('range')
    }
  }

  // 监听各图表时间范围变化 - 只更新对应图表
  watch(timeRangeHourlyRequests, createChartWatcher('hourlyRequests', updateHourlyRequestsChart))
  watch(timeRangeTrend, createChartWatcher('trend', updateTrendChart))
  watch(timeRangeSuccessRate, createChartWatcher('successRate', updateSuccessRateChart))
  watch(timeRangeModel, createChartWatcher('model', updateModelChart))
  watch(timeRangeModelRank, createChartWatcher('modelRank', updateModelRankChart))
  watch(timeRangeResponseTime, createChartWatcher('responseTime', updateResponseTimeChart))

  const stats = ref([
    {
      label: '账号总数',
      value: '0',
      caption: '账号池中的总数量',
      icon: 'M16 11c1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3 1.34 3 3 3zM8 11c1.66 0 3-1.34 3-3S9.66 5 8 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4zm8 0c-.33 0-.7.02-1.09.05 1.33.96 2.09 2.18 2.09 3.95v2h7v-2c0-2.66-5.33-4-8-4z',
      iconBg: 'bg-sky-100',
      iconColor: 'text-sky-600'
    },
    {
      label: '正常账号',
      value: '0',
      caption: '正常运行中，可随时调用',
      icon: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1.2 13.6-3.9-3.9 1.4-1.4 2.5 2.5 5.7-5.7 1.4 1.4-7.1 7.1z',
      iconBg: 'bg-emerald-100',
      iconColor: 'text-emerald-600'
    },
    {
      label: '限流账号',
      value: '0',
      caption: '触发限流，正在冷却中',
      icon: 'M12 1.8a10.2 10.2 0 1 0 0 20.4 10.2 10.2 0 0 0 0-20.4zm1 5.2v5.2l4.2 2.5-1 1.6L11 13V7h2z',
      iconBg: 'bg-amber-100',
      iconColor: 'text-amber-600'
    },
    {
      label: '异常账号',
      value: '0',
      caption: '鉴权异常或上游不可用',
      icon: 'M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z',
      iconBg: 'bg-rose-100',
      iconColor: 'text-rose-600'
    },
    {
      label: '禁用账号',
      value: '0',
      caption: '手动禁用，不参与调度',
      icon: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM4 12a8 8 0 0 1 12.9-6.3L5.7 16.9A7.96 7.96 0 0 1 4 12zm8 8a7.96 7.96 0 0 1-4.9-1.7L18.3 7.1A8 8 0 0 1 12 20z',
      iconBg: 'bg-slate-100',
      iconColor: 'text-slate-600'
    },
    {
      label: '剩余额度',
      value: '0',
      caption: '正常账号剩余图片额度',
      icon: 'M12 2C8.1 2 5 3.8 5 6v12c0 2.2 3.1 4 7 4s7-1.8 7-4V6c0-2.2-3.1-4-7-4zm0 2c3.3 0 5 1.3 5 2s-1.7 2-5 2-5-1.3-5-2 1.7-2 5-2zm0 8c-2 0-3.8-.5-5-1.3V8.9c1.3.8 3.1 1.1 5 1.1s3.7-.4 5-1.1v1.8c-1.2.8-3 1.3-5 1.3zm0 6c-2 0-3.8-.5-5-1.3v-2.8c1.3.8 3.1 1.1 5 1.1s3.7-.4 5-1.1v2.8c-1.2.8-3 1.3-5 1.3z',
      iconBg: 'bg-cyan-100',
      iconColor: 'text-cyan-600'
    },
  ])

  // 每个图表独立的数据状态
  const chartData = ref({
    hourlyRequests: {
      labels: [] as string[],
      modelRequests: {} as Record<string, number[]>,
    },
    trend: {
      labels: [] as string[],
      totalRequests: [] as number[],
      failedRequests: [] as number[],
      rateLimitedRequests: [] as number[],
      successRequests: [] as number[],
    },
    successRate: {
      labels: [] as string[],
      totalRequests: [] as number[],
      failedRequests: [] as number[],
    },
    model: {
      modelRequests: {} as Record<string, number[]>,
    },
    modelRank: {
      modelRequests: {} as Record<string, number[]>,
    },
    responseTime: {
      labels: [] as string[],
      modelTtfbTimes: {} as Record<string, number[]>,
      modelTotalTimes: {} as Record<string, number[]>,
    },
  })

  const overviewCache = new Map<string, OverviewPayload>()
  const overviewRequests = new Map<string, Promise<OverviewPayload>>()

  const trendChartRef = ref<HTMLDivElement | null>(null)
  const modelChartRef = ref<HTMLDivElement | null>(null)
  const successRateChartRef = ref<HTMLDivElement | null>(null)
  const hourlyRequestsChartRef = ref<HTMLDivElement | null>(null)
  const modelRankChartRef = ref<HTMLDivElement | null>(null)
  const responseTimeChartRef = ref<HTMLDivElement | null>(null)

  const charts = {
    trend: null as ChartInstance | null,
    model: null as ChartInstance | null,
    successRate: null as ChartInstance | null,
    hourlyRequests: null as ChartInstance | null,
    modelRank: null as ChartInstance | null,
    responseTime: null as ChartInstance | null,
  }

  type ChartKey = keyof typeof charts
  const renderProfiles: Record<RenderMode, {
    duration: number
    updateDuration: number
    delayStep: number
    lazyUpdate: boolean
  }> = {
    initial: { duration: 860, updateDuration: 620, delayStep: 14, lazyUpdate: false },
    range: { duration: 560, updateDuration: 460, delayStep: 8, lazyUpdate: false },
    refresh: { duration: 260, updateDuration: 220, delayStep: 0, lazyUpdate: true },
  }
  const chartFirstRenderState = ref<Record<ChartKey, boolean>>({
    trend: true,
    model: true,
    successRate: true,
    hourlyRequests: true,
    modelRank: true,
    responseTime: true,
  })
  const chartsBootstrapped = ref(false)
  const dashboardDataReady = ref(false)
  let chartBootstrapTimer: number | null = null
  const modelLayoutIsMobile = ref<boolean | null>(null)

  function bindResizeListener() {
    window.removeEventListener('resize', handleResize)
    window.addEventListener('resize', handleResize)
  }

  function unbindResizeListener() {
    window.removeEventListener('resize', handleResize)
  }

  function applyAnimatedOption(key: ChartKey, option: Record<string, unknown>, mode: RenderMode = 'refresh') {
    const chart = charts[key]
    if (!chart) return
    const isFirstRender = chartFirstRenderState.value[key]
    const activeMode: RenderMode = isFirstRender ? 'initial' : mode
    const profile = renderProfiles[activeMode]
    const optionWithAnimation = {
      ...option,
      animation: true,
      animationDuration: profile.duration,
      animationDurationUpdate: profile.updateDuration,
      animationEasing: 'cubicOut',
      animationEasingUpdate: 'cubicOut',
      animationDelay: profile.delayStep > 0 ? (idx: number) => Math.min(idx * profile.delayStep, 180) : 0,
      animationDelayUpdate: profile.delayStep > 0 ? (idx: number) => Math.min(idx * Math.max(4, Math.floor(profile.delayStep / 2)), 120) : 0,
    }
    chart.setOption(optionWithAnimation, {
      notMerge: false,
      lazyUpdate: profile.lazyUpdate,
    })
    chartFirstRenderState.value[key] = false
  }

  function initChart(
    ref: HTMLDivElement | null,
    key: ChartKey,
    updateFn: (mode?: RenderMode) => void
  ) {
    const echarts = (window as any).echarts as { init: (el: HTMLElement) => ChartInstance } | undefined
    if (!echarts || !ref) return
    charts[key] = echarts.init(ref)
    updateFn('initial')
  }

  function bootstrapCharts() {
    if (chartsBootstrapped.value) return
    initChart(trendChartRef.value, 'trend', updateTrendChart)
    initChart(modelChartRef.value, 'model', updateModelChart)
    initChart(successRateChartRef.value, 'successRate', updateSuccessRateChart)
    initChart(hourlyRequestsChartRef.value, 'hourlyRequests', updateHourlyRequestsChart)
    initChart(modelRankChartRef.value, 'modelRank', updateModelRankChart)
    initChart(responseTimeChartRef.value, 'responseTime', updateResponseTimeChart)
    chartsBootstrapped.value = true
  }

  function resetChartFirstRenderState() {
    chartFirstRenderState.value = {
      trend: true,
      model: true,
      successRate: true,
      hourlyRequests: true,
      modelRank: true,
      responseTime: true,
    }
  }

  function disposeCharts() {
    ;(Object.keys(charts) as ChartKey[]).forEach((key) => {
      charts[key]?.dispose()
      charts[key] = null
    })
    chartsBootstrapped.value = false
    resetChartFirstRenderState()
  }

  function scheduleChartBootstrap(delayMs = 80) {
    if (chartsBootstrapped.value) return
    if (chartBootstrapTimer) window.clearTimeout(chartBootstrapTimer)
    chartBootstrapTimer = window.setTimeout(() => {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          bootstrapCharts()
        })
      })
    }, delayMs)
  }

  onMounted(async () => {
    await preloadInitialDashboardData()

    scheduleChartBootstrap()
    bindResizeListener()
  })

  onActivated(() => {
    bindResizeListener()
    if (!dashboardDataReady.value) return
    if (chartsBootstrapped.value) disposeCharts()
    scheduleChartBootstrap(0)
  })

  onDeactivated(() => {
    unbindResizeListener()
    if (chartBootstrapTimer) {
      window.clearTimeout(chartBootstrapTimer)
      chartBootstrapTimer = null
    }
    disposeCharts()
  })

  onBeforeUnmount(() => {
    unbindResizeListener()
    if (chartBootstrapTimer) window.clearTimeout(chartBootstrapTimer)
    disposeCharts()
  })

  function updateTrendChart(mode: RenderMode = 'refresh') {
    if (!charts.trend) return

    const theme = getLineChartTheme()

    applyAnimatedOption('trend', {
      ...theme,
      xAxis: {
        ...theme.xAxis,
        data: chartData.value.trend.labels,
      },
      series: [
        createLineSeries('成功', chartData.value.trend.successRequests, chartColors.primary, {
          areaOpacity: 0.25,
          zIndex: 1,
        }),
        createLineSeries('失败', chartData.value.trend.failedRequests, chartColors.danger, {
          areaOpacity: 0.3,
          zIndex: 2,
        }),
        createLineSeries('限流', chartData.value.trend.rateLimitedRequests, chartColors.warning, {
          areaOpacity: 0.3,
          zIndex: 2,
        }),
      ],
    }, mode)
  }

  function getModelTotals() {
    return Object.entries(chartData.value.model.modelRequests)
      .map(([model, data]) => ({
        model,
        data: createPieDataItem(model, data.reduce((sum, item) => sum + item, 0), getModelColor(model)),
        total: data.reduce((sum, item) => sum + item, 0),
      }))
      .filter(item => item.total > 0)
  }

  function updateModelChart(mode: RenderMode = 'refresh') {
    if (!charts.model) return

    const isMobile = window.innerWidth < 768
    modelLayoutIsMobile.value = isMobile
    const theme = getPieChartTheme(isMobile)
    const modelData = getModelTotals().map(item => item.data)
    const modelColors = modelData.map(item => String(item?.itemStyle?.color || getModelColor(String(item?.name || ''))))

    applyAnimatedOption('model', {
      ...theme,
      color: modelColors,
      tooltip: {
        ...theme.tooltip,
        formatter: (params: { name: string; value: number; percent: number }) =>
          `${params.name}: ${params.value} 次 (${params.percent}%)`,
      },
      legend: {
        ...theme.legend,
        data: modelData.map(item => item.name),
      },
      series: [
        {
          ...theme.series,
          center: ['50%', '50%'],
          data: modelData,
        },
      ],
    }, mode)
  }

  function handleResize() {
    Object.entries(charts).forEach(([key, chart]) => {
      if (chart) {
        if (key === 'model') {
          const nowMobile = window.innerWidth < 768
          if (modelLayoutIsMobile.value !== nowMobile) {
            updateModelChart()
          } else {
            chart.resize()
          }
        } else {
          chart.resize()
        }
      }
    })
  }

  function getChartRange(chartType: ChartType) {
    switch (chartType) {
      case 'hourlyRequests':
        return timeRangeHourlyRequests.value
      case 'trend':
        return timeRangeTrend.value
      case 'successRate':
        return timeRangeSuccessRate.value
      case 'model':
        return timeRangeModel.value
      case 'modelRank':
        return timeRangeModelRank.value
      case 'responseTime':
        return timeRangeResponseTime.value
    }
  }

  async function getOverview(timeRange: string) {
    const cached = overviewCache.get(timeRange)
    if (cached) return cached

    const inflight = overviewRequests.get(timeRange)
    if (inflight) return inflight

    const request = statsApi
      .overview(timeRange)
      .then((overview) => {
        const payload = overview as OverviewPayload
        overviewCache.set(timeRange, payload)
        return payload
      })
      .finally(() => {
        overviewRequests.delete(timeRange)
      })

    overviewRequests.set(timeRange, request)
    return request
  }

  function applyAccountStats(overview: OverviewPayload) {
    stats.value[0].value = (overview.total_accounts ?? 0).toString()
    stats.value[1].value = (overview.active_accounts ?? 0).toString()
    stats.value[2].value = (overview.rate_limited_accounts ?? 0).toString()
    stats.value[3].value = (overview.abnormal_accounts ?? 0).toString()
    stats.value[4].value = (overview.disabled_accounts ?? 0).toString()
    const totalQuota = Number(overview.total_quota || 0)
    const unlimited = Number(overview.unlimited_quota_count || 0)
    stats.value[5].value = unlimited > 0 ? `${totalQuota}+${unlimited}∞` : totalQuota.toString()
  }

  function getTrendPayload(overview: OverviewPayload) {
    return overview.trend || {
      labels: [],
      total_requests: [],
      success_requests: [],
      failed_requests: [],
      rate_limited_requests: [],
      model_requests: {},
      model_ttfb_times: {},
      model_total_times: {},
    }
  }

  function applyOverviewToChartData(chartType: ChartType, overview: OverviewPayload) {
    const trend = getTrendPayload(overview)
    const failed = trend.failed_requests || []
    const limited = trend.rate_limited_requests || []
    const success = trend.success_requests || []
    const failureSeries = (trend.total_requests || []).map((_: number, idx: number) => (failed[idx] || 0) + (limited[idx] || 0))
    const successSeries = (trend.total_requests || []).map((total: number, idx: number) => {
      const explicitSuccess = Number(success[idx])
      if (Number.isFinite(explicitSuccess)) return explicitSuccess
      return Math.max(Number(total || 0) - (failed[idx] || 0) - (limited[idx] || 0), 0)
    })

    switch (chartType) {
      case 'hourlyRequests':
        chartData.value.hourlyRequests.labels = trend.labels || []
        chartData.value.hourlyRequests.modelRequests = filterValidModels(trend.model_requests || {})
        break
      case 'trend':
        chartData.value.trend.labels = trend.labels || []
        chartData.value.trend.totalRequests = trend.total_requests || []
        chartData.value.trend.failedRequests = failed
        chartData.value.trend.rateLimitedRequests = limited
        chartData.value.trend.successRequests = successSeries
        break
      case 'successRate':
        chartData.value.successRate.labels = trend.labels || []
        chartData.value.successRate.totalRequests = trend.total_requests || []
        chartData.value.successRate.failedRequests = failureSeries
        break
      case 'model':
        chartData.value.model.modelRequests = filterValidModels(trend.model_requests || {})
        break
      case 'modelRank':
        chartData.value.modelRank.modelRequests = filterValidModels(trend.model_requests || {})
        break
      case 'responseTime':
        chartData.value.responseTime.labels = trend.labels || []
        chartData.value.responseTime.modelTtfbTimes = filterValidModels(trend.model_ttfb_times || {})
        chartData.value.responseTime.modelTotalTimes = filterValidModels(trend.model_total_times || {})
        break
    }
  }

  async function preloadInitialDashboardData() {
    try {
      const initialRanges = Array.from(
        new Set<string>([
          '24h',
          timeRangeHourlyRequests.value,
          timeRangeTrend.value,
          timeRangeSuccessRate.value,
          timeRangeModel.value,
          timeRangeModelRank.value,
          timeRangeResponseTime.value,
        ])
      )

      await Promise.all(initialRanges.map((timeRange) => getOverview(timeRange)))

      const accountOverview = overviewCache.get('24h')
      if (accountOverview) {
        applyAccountStats(accountOverview)
      }

      ;(['hourlyRequests', 'trend', 'successRate', 'model', 'modelRank', 'responseTime'] as ChartType[]).forEach((chartType) => {
        const overview = overviewCache.get(getChartRange(chartType))
        if (overview) applyOverviewToChartData(chartType, overview)
      })
    } catch (error) {
      console.error('Failed to preload dashboard data:', error)
    } finally {
      dashboardDataReady.value = true
    }
  }

  async function loadChartData(chartType: ChartType, timeRange: string) {
    try {
      const overview = await getOverview(timeRange)
      applyOverviewToChartData(chartType, overview)
    } catch (error) {
      console.error(`Failed to load ${chartType} data:`, error)
    }
  }

  function updateSuccessRateChart(mode: RenderMode = 'refresh') {
    if (!charts.successRate) return

    const theme = getLineChartTheme()
    const successRates = chartData.value.successRate.totalRequests.map((total, idx) => {
      const failure = chartData.value.successRate.failedRequests[idx] || 0
      return total > 0 ? Math.round(((total - failure) / total) * 100) : 100
    })

    applyAnimatedOption('successRate', {
      ...theme,
      tooltip: {
        ...theme.tooltip,
        trigger: 'axis',
        formatter: (params: any) => {
          if (!params || params.length === 0) return ''
          const param = params[0]
          return `<div style="font-weight: 600; margin-bottom: 4px;">${param.axisValue}</div>
            <div style="display: flex; justify-content: space-between; gap: 16px; align-items: center;">
              <span>${param.marker} ${param.seriesName}</span>
              <span style="font-weight: 600;">${param.value}%</span>
            </div>`
        },
      },
      grid: {
        ...theme.grid,
        top: 32,
        bottom: 32,
      },
      xAxis: {
        ...theme.xAxis,
        data: chartData.value.successRate.labels,
      },
      yAxis: {
        ...theme.yAxis,
        max: 100,
        axisLabel: {
          ...theme.yAxis.axisLabel,
          formatter: '{value}%',
        },
      },
      series: [
        {
          name: '成功率',
          type: 'line',
          data: successRates,
          smooth: true,
          showSymbol: false,
          lineStyle: {
            width: 3,
          },
          areaStyle: {
            opacity: 0.3,
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: chartColors.success },
                { offset: 1, color: 'rgba(16, 185, 129, 0.1)' },
              ],
            },
          },
          itemStyle: {
            color: chartColors.success,
          },
        },
      ],
    }, mode)
  }

  function updateHourlyRequestsChart(mode: RenderMode = 'refresh') {
    if (!charts.hourlyRequests) return

    const theme = getLineChartTheme()
    const modelNames = Object.keys(chartData.value.hourlyRequests.modelRequests)

    if (modelNames.length === 0) {
      applyAnimatedOption('hourlyRequests', {
        ...theme,
        grid: {
          ...theme.grid,
          left: 34,
          right: 24,
          top: 32,
          bottom: 32,
        },
        xAxis: {
          ...theme.xAxis,
          data: chartData.value.hourlyRequests.labels,
          boundaryGap: true,
        },
        yAxis: {
          ...theme.yAxis,
        },
        series: [
          {
            name: '总请求',
            type: 'bar',
            data: [],
            barWidth: '60%',
            itemStyle: {
              color: chartColors.primary,
              borderRadius: [4, 4, 0, 0],
            },
          },
        ],
      }, mode)
      return
    }

    const pointCount = chartData.value.hourlyRequests.labels.length
    const topSeriesIndexByPoint = Array.from({ length: pointCount }, (_, pointIndex) => {
      for (let seriesIndex = modelNames.length - 1; seriesIndex >= 0; seriesIndex -= 1) {
        const value = Number(chartData.value.hourlyRequests.modelRequests[modelNames[seriesIndex]]?.[pointIndex] || 0)
        if (value > 0) return seriesIndex
      }
      return -1
    })

    const series = modelNames.map((modelName, seriesIndex) => ({
      name: modelName,
      type: 'bar',
      stack: 'total',
      itemStyle: {
        color: getModelColor(modelName),
      },
      data: (chartData.value.hourlyRequests.modelRequests[modelName] || []).map((value, pointIndex) => ({
        value,
        itemStyle: {
          color: getModelColor(modelName),
          borderRadius: topSeriesIndexByPoint[pointIndex] === seriesIndex ? [4, 4, 0, 0] : [0, 0, 0, 0],
        },
      })),
    }))

    applyAnimatedOption('hourlyRequests', {
      ...theme,
      color: modelNames.map(name => getModelColor(name)),
      tooltip: {
        ...theme.tooltip,
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
        },
        formatter: (params: any) => {
          if (!params || params.length === 0) return ''
          let result = `<div style="font-weight: 600; margin-bottom: 4px;">${params[0].axisValue}</div>`
          let total = 0
          params.forEach((item: any) => {
            total += item.value || 0
            result += `<div style="display: flex; justify-content: space-between; gap: 16px; align-items: center;">
              <span>${item.marker} ${item.seriesName}</span>
              <span style="font-weight: 600;">${item.value || 0}</span>
            </div>`
          })
          result += `<div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid #e5e5e5; font-weight: 600;">
            总计: ${total}
          </div>`
          return result
        },
      },
      legend: {
        ...theme.legend,
        data: modelNames,
        top: 0,
        right: 0,
        type: 'scroll',
        pageIconSize: 10,
        pageTextStyle: {
          fontSize: 10,
        },
      },
      grid: {
        ...theme.grid,
        left: 34,
        right: 24,
        top: modelNames.length > 5 ? 56 : 48,
        bottom: 32,
      },
      xAxis: {
        ...theme.xAxis,
        data: chartData.value.hourlyRequests.labels,
        boundaryGap: true,
      },
      yAxis: {
        ...theme.yAxis,
      },
      series: series,
    }, mode)

  }

  function updateModelRankChart(mode: RenderMode = 'refresh') {
    if (!charts.modelRank) return

    const theme = getLineChartTheme()
    const modelTotals = Object.entries(chartData.value.modelRank.modelRequests)
      .map(([model, data]) => ({
        model,
        total: data.reduce((sum, item) => sum + item, 0),
      }))
      .filter(item => item.total > 0)
      .sort((a, b) => b.total - a.total)

    const modelNames = modelTotals.map(item => item.model)
    const modelValues = modelTotals.map(item => item.total)
    const modelColors = modelNames.map(name => getModelColor(name))

    applyAnimatedOption('modelRank', {
      ...theme,
      grid: {
        left: 12,
        right: 60,
        top: 16,
        bottom: 16,
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        axisLine: {
          show: false,
        },
        axisTick: {
          show: false,
        },
        axisLabel: {
          ...theme.xAxis.axisLabel,
          fontSize: 10,
        },
        splitLine: {
          lineStyle: {
            color: '#e5e5e5',
            type: 'solid',
          },
        },
      },
      yAxis: {
        type: 'category',
        data: modelNames,
        axisLine: {
          show: false,
        },
        axisTick: {
          show: false,
        },
        axisLabel: {
          ...theme.yAxis.axisLabel,
          fontSize: 11,
        },
      },
      series: [
        {
          type: 'bar',
          data: modelValues.map((value, idx) => ({
            value,
            itemStyle: {
              color: modelColors[idx],
              borderRadius: [0, 4, 4, 0],
            },
          })),
          barWidth: '50%',
          label: {
            show: true,
            position: 'right',
            fontSize: 11,
            color: '#6b6b6b',
            formatter: '{c}',
          },
        },
      ],
    }, mode)
  }

  function updateResponseTimeChart(mode: RenderMode = 'refresh') {
    if (!charts.responseTime) return

    const theme = getLineChartTheme()
    const responseSeriesByModel = chartData.value.responseTime.modelTotalTimes
    const modelNames = Object.keys(responseSeriesByModel)
      .filter((modelName) => (responseSeriesByModel[modelName] || []).some((value) => Number(value || 0) > 0))

    if (modelNames.length === 0) {
      applyAnimatedOption('responseTime', {
        ...theme,
        grid: {
          ...theme.grid,
          top: 32,
          bottom: 32,
        },
        xAxis: {
          ...theme.xAxis,
          data: chartData.value.responseTime.labels,
        },
        yAxis: {
          ...theme.yAxis,
          axisLabel: {
            ...theme.yAxis.axisLabel,
            formatter: '{value}s',
          },
        },
        series: [],
      }, mode)
      return
    }

    const series = modelNames.map((modelName) => {
      const color = getModelColor(modelName)
      const seconds = (responseSeriesByModel[modelName] || []).map((ms) => Number((Number(ms || 0) / 1000).toFixed(2)))
      return createLineSeries(modelName, seconds, color, {
        smooth: true,
        areaOpacity: 0.15,
        zIndex: 2,
      })
    })

    applyAnimatedOption('responseTime', {
      ...theme,
      color: modelNames.map((modelName) => getModelColor(modelName)),
      tooltip: {
        ...theme.tooltip,
        trigger: 'axis',
        formatter: (params: any) => {
          if (!params || params.length === 0) return ''
          let result = `<div style="font-weight: 600; margin-bottom: 4px;">${params[0].axisValue}</div>`
          params.forEach((item: any) => {
            result += `<div style="display: flex; justify-content: space-between; gap: 16px; align-items: center;">
              <span>${item.marker} ${item.seriesName}</span>
              <span style="font-weight: 600;">${item.value || 0}s</span>
            </div>`
          })
          return result
        },
      },
      legend: {
        ...theme.legend,
        data: modelNames,
        top: 0,
        right: 0,
        type: 'scroll',
        pageIconSize: 10,
        pageTextStyle: {
          fontSize: 10,
        },
      },
      grid: {
        ...theme.grid,
        top: modelNames.length > 5 ? 56 : 48,
        bottom: 32,
      },
      xAxis: {
        ...theme.xAxis,
        data: chartData.value.responseTime.labels,
      },
      yAxis: {
        ...theme.yAxis,
        axisLabel: {
          ...theme.yAxis.axisLabel,
          formatter: '{value}s',
        },
      },
      series,
    }, mode)
  }

  return {
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
  }
}

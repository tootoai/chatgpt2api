import apiClient from './client'

export interface ProxyTestResult {
  ok: boolean
  status: number
  latency_ms: number
  error?: string | null
}

export interface ProxyProfile {
  id: string
  name: string
  proxy: string
  no_proxy?: string
  enabled: boolean
  notes?: string
}

export type ProxyProfilePayload = Partial<ProxyProfile> & {
  create_only?: boolean
}

export const proxyApi = {
  test: (url: string) =>
    apiClient.post<{ url: string }, { result: ProxyTestResult }>('/api/proxy/test', { url }),

  listProfiles: () =>
    apiClient.get<never, { profiles: ProxyProfile[] }>('/api/proxy/profiles'),

  saveProfile: (payload: ProxyProfilePayload) =>
    apiClient.post<ProxyProfilePayload, { profile: ProxyProfile; profiles: ProxyProfile[] }>(
      '/api/proxy/profiles',
      payload,
    ),

  deleteProfile: (id: string) =>
    apiClient.delete<never, { deleted: string; profiles: ProxyProfile[] }>(
      `/api/proxy/profiles/${encodeURIComponent(id)}`,
    ),

  testProfile: (payload: { id?: string; url?: string }) =>
    apiClient.post<{ id?: string; url?: string }, { result: ProxyTestResult }>(
      '/api/proxy/profiles/test',
      payload,
    ),
}

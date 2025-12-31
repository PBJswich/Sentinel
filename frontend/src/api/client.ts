const API_BASE = '/api'

export interface Signal {
  signal_id: string
  market: string
  category: string
  name: string
  direction: 'Bullish' | 'Bearish' | 'Neutral'
  confidence: 'Low' | 'Medium' | 'High'
  last_updated: string
  data_asof: string
  explanation: string
  definition: string
  source: string
  key_driver: string
  validity_window: string
  decay_behavior: string
  signal_type: string
  score?: number
  confidence_rationale?: string
}

export interface SignalsResponse {
  signals: Signal[]
  total: number
  filtered_count: number
  limit?: number
  offset?: number
}

export interface Market {
  market: string
  groups: string[]
}

export interface MarketSummary {
  market: string
  total_signals: number
  direction_breakdown: {
    bullish: number
    bearish: number
    neutral: number
  }
  confidence_breakdown: {
    high: number
    medium: number
    low: number
  }
  pillar_breakdown: Record<string, number>
  conflicts: any[]
}

export interface Watchlist {
  watchlist_id: string
  name: string
  signal_ids: string[]
  market_ids: string[]
  created_at: string
  updated_at: string
}

export interface Alert {
  alert_id: string
  alert_type: string
  name: string
  description: string
  conditions: Record<string, any>
  enabled: boolean
  created_at: string
  last_triggered?: string
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`API error (${response.status}): ${errorText || response.statusText}`)
    }

    return response.json()
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Failed to connect to API. Make sure the backend is running on http://localhost:8000')
    }
    throw error
  }
}

export const api = {
  signals: {
    getAll: (params?: {
      market?: string
      category?: string
      direction?: string
      confidence?: string
      search?: string
      sort_by?: string
      limit?: number
      offset?: number
    }): Promise<SignalsResponse> => {
      const query = new URLSearchParams()
      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            query.append(key, String(value))
          }
        })
      }
      return fetchJson<SignalsResponse>(`/signals?${query}`)
    },
    getByMarket: (market: string): Promise<SignalsResponse> => {
      return fetchJson<SignalsResponse>(`/signals/${encodeURIComponent(market)}`)
    },
  },
  markets: {
    getAll: (): Promise<{ markets: Market[]; total_markets: number }> => {
      return fetchJson('/markets')
    },
    getSummary: (market: string): Promise<MarketSummary> => {
      return fetchJson(`/markets/${encodeURIComponent(market)}/summary`)
    },
  },
  watchlists: {
    getAll: (): Promise<{ watchlists: Watchlist[] }> => {
      return fetchJson('/watchlists')
    },
    get: (id: string): Promise<{ watchlist: Watchlist }> => {
      return fetchJson(`/watchlists/${id}`)
    },
    create: (watchlist: Omit<Watchlist, 'watchlist_id' | 'created_at' | 'updated_at'>): Promise<{ watchlist: Watchlist }> => {
      return fetchJson('/watchlists', {
        method: 'POST',
        body: JSON.stringify(watchlist),
      })
    },
    update: (id: string, watchlist: Partial<Watchlist>): Promise<{ watchlist: Watchlist }> => {
      return fetchJson(`/watchlists/${id}`, {
        method: 'PUT',
        body: JSON.stringify(watchlist),
      })
    },
    delete: (id: string): Promise<void> => {
      return fetchJson(`/watchlists/${id}`, {
        method: 'DELETE',
      })
    },
    getSignals: (id: string): Promise<{ signals: Signal[]; total_signals: number }> => {
      return fetchJson(`/watchlists/${id}/signals`)
    },
  },
  alerts: {
    getAll: (): Promise<{ alerts: Alert[] }> => {
      return fetchJson('/alerts')
    },
    getActive: (): Promise<{ alerts: Alert[] }> => {
      // The active endpoint returns triggered alerts, but we need to get all alerts
      // and filter for enabled ones, or return empty array if no alerts exist
      return fetchJson('/alerts')
        .then((data) => {
          // Filter for enabled alerts
          return { alerts: data.alerts.filter((a: Alert) => a.enabled) }
        })
        .catch(() => {
          // If alerts endpoint fails, return empty array
          return { alerts: [] }
        })
    },
    create: (alert: Omit<Alert, 'alert_id' | 'created_at' | 'last_triggered'>): Promise<{ alert: Alert }> => {
      return fetchJson('/alerts', {
        method: 'POST',
        body: JSON.stringify(alert),
      })
    },
    update: (id: string, alert: Partial<Alert>): Promise<{ alert: Alert }> => {
      return fetchJson(`/alerts/${id}`, {
        method: 'PUT',
        body: JSON.stringify(alert),
      })
    },
    delete: (id: string): Promise<void> => {
      return fetchJson(`/alerts/${id}`, {
        method: 'DELETE',
      })
    },
  },
}


export interface Site {
  site_id: string
  name: string
  region: string
  latitude: number
  longitude: number
}

export interface Point {
  timestamp: string
  value: number | null
  isAnomaly: boolean
}

export interface ReadingsResponse {
  siteId: string
  metric: string
  k: number
  summary: {
    count: number
    average: number | null
    peak: number | null
    anomalies: number
  }
  series: Point[]
}

export type Metric = "solar_radiation" | "wind_speed"

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail ?? `Request failed (${res.status})`)
  }
  return res.json()
}

export const fetchSites = () => getJSON<Site[]>("/api/sites")

export function fetchReadings(params: {
  siteId: string
  metric: Metric
  k: number
}): Promise<ReadingsResponse> {
  const q = new URLSearchParams({
    site_id: params.siteId,
    metric: params.metric,
    k: String(params.k),
  })
  return getJSON<ReadingsResponse>(`/api/readings?${q}`)
}

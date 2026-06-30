import { useEffect, useState } from "react"
import { AlertTriangle, Sun, Wind } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { AskPanel } from "@/components/AskPanel"
import { TimeSeriesChart } from "@/components/TimeSeriesChart"
import {
  fetchReadings,
  fetchSites,
  type Metric,
  type ReadingsResponse,
  type Site,
} from "@/lib/api"

const METRICS: Record<Metric, { label: string; unit: string; icon: typeof Sun }> = {
  solar_radiation: { label: "Solar radiation", unit: "W/m²", icon: Sun },
  wind_speed: { label: "Wind speed", unit: "m/s", icon: Wind },
}

function Kpi({ title, value }: { title: string; value: string }) {
  return (
    <Card>
      <CardHeader className="pb-0">
        <CardTitle className="text-muted-foreground text-xs font-medium uppercase tracking-wide">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <span className="text-2xl font-semibold tabular-nums">{value}</span>
      </CardContent>
    </Card>
  )
}

export default function App() {
  const [sites, setSites] = useState<Site[]>([])
  const [siteId, setSiteId] = useState<string>("")
  const [metric, setMetric] = useState<Metric>("solar_radiation")
  const [data, setData] = useState<ReadingsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchSites()
      .then((s) => {
        setSites(s)
        if (s.length) setSiteId(s[0].site_id)
      })
      .catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (!siteId) return
    setLoading(true)
    setError(null)
    fetchReadings({ siteId, metric, k: 1.5 })
      .then(setData)
      .catch((e) => {
        setError(e.message)
        setData(null)
      })
      .finally(() => setLoading(false))
  }, [siteId, metric])

  const site = sites.find((s) => s.site_id === siteId)
  const m = METRICS[metric]
  const fmt = (v: number | null) => (v == null ? "—" : v.toFixed(1))

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">
          Renewable Site Monitor
        </h1>
        <p className="text-muted-foreground text-sm">
          Hourly solar radiation &amp; wind speed across renewable sites — with IQR
          anomaly flagging.
        </p>
      </header>

      {/* Controls */}
      <div className="mb-6 flex flex-wrap items-end gap-4">
        <div className="w-72 space-y-1.5">
          <label className="text-muted-foreground text-xs font-medium">Site</label>
          <Select value={siteId} onValueChange={setSiteId}>
            <SelectTrigger>
              <SelectValue placeholder="Select a site" />
            </SelectTrigger>
            <SelectContent>
              {sites.map((s) => (
                <SelectItem key={s.site_id} value={s.site_id}>
                  {s.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <label className="text-muted-foreground block text-xs font-medium">
            Metric
          </label>
          <div className="flex gap-2">
            {(Object.keys(METRICS) as Metric[]).map((key) => {
              const Icon = METRICS[key].icon
              return (
                <Button
                  key={key}
                  variant={metric === key ? "default" : "outline"}
                  size="sm"
                  onClick={() => setMetric(key)}
                >
                  <Icon className="size-4" />
                  {METRICS[key].label}
                </Button>
              )
            })}
          </div>
        </div>

        {site && (
          <p className="text-muted-foreground ml-auto text-xs">
            {site.region} · ({site.latitude.toFixed(3)}, {site.longitude.toFixed(3)})
          </p>
        )}
      </div>

      {error && (
        <Card className="border-destructive mb-6">
          <CardContent className="text-destructive flex items-center gap-2 py-4 text-sm">
            <AlertTriangle className="size-4" />
            {error} — is the backend running? Try{" "}
            <code className="bg-muted rounded px-1">python -m src.etl</code> then{" "}
            <code className="bg-muted rounded px-1">uvicorn api:app</code>.
          </CardContent>
        </Card>
      )}

      {data && (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Kpi title="Readings" value={data.summary.count.toLocaleString()} />
            <Kpi title="Average" value={`${fmt(data.summary.average)} ${m.unit}`} />
            <Kpi title="Peak" value={`${fmt(data.summary.peak)} ${m.unit}`} />
            <Kpi title="Anomalies" value={String(data.summary.anomalies)} />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>
                {m.label} ({m.unit})
              </CardTitle>
              <p className="text-muted-foreground text-xs">
                Red points are IQR-flagged anomalies (k=1.5). Solar baseline uses
                daytime hours only.
              </p>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-muted-foreground flex h-[380px] items-center justify-center text-sm">
                  Loading…
                </div>
              ) : (
                <TimeSeriesChart series={data.series} unit={m.unit} label={m.label} />
              )}
            </CardContent>
          </Card>
        </>
      )}

      <AskPanel />
    </div>
  )
}

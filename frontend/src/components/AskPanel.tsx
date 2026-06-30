import { useState } from "react"
import { Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { ask, type AskResponse } from "@/lib/api"

const EXAMPLES = [
  "Which site had the highest average solar radiation last week?",
  "Compare average wind speed across all three sites for the past month.",
]

export function AskPanel() {
  const [question, setQuestion] = useState("")
  const [result, setResult] = useState<AskResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function run(q: string) {
    const text = q.trim()
    if (!text) return
    setQuestion(text)
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await ask(text))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="size-4" /> Ask the data
        </CardTitle>
        <p className="text-muted-foreground text-xs">
          Plain-English questions answered from the stored readings only — the model
          writes a read-only SQL query, and answers from the rows it returns.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <Textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Which site had the highest average solar radiation last week?"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) run(question)
          }}
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={() => run(question)} disabled={loading}>
            {loading ? "Thinking…" : "Ask"}
          </Button>
          {EXAMPLES.map((ex) => (
            <Button
              key={ex}
              variant="outline"
              size="sm"
              disabled={loading}
              onClick={() => run(ex)}
            >
              {ex.length > 42 ? ex.slice(0, 42) + "…" : ex}
            </Button>
          ))}
        </div>

        {error && (
          <p className="text-destructive text-sm">
            {error}
          </p>
        )}

        {result && (
          <div className="space-y-3">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{result.answer}</p>
            {result.sql && (
              <details className="text-xs">
                <summary className="text-muted-foreground cursor-pointer select-none">
                  Show SQL &amp; {result.rows.length} row(s)
                </summary>
                <pre className="bg-muted mt-2 overflow-x-auto rounded-md p-3 text-xs">
                  {result.sql}
                </pre>
                {result.rows.length > 0 && (
                  <pre className="bg-muted mt-2 max-h-56 overflow-auto rounded-md p-3 text-xs">
                    {JSON.stringify(result.rows, null, 2)}
                  </pre>
                )}
              </details>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

import { useState } from 'react'

function normalizeSeed(input) {
  if (input === '' || input === null || input === undefined) {
    return Math.floor(Date.now() % 1_000_000_000)
  }
  return Number(input)
}

export default function ChaosPanel({ onLaunchChaos }) {
  const [open, setOpen] = useState(false)
  const [count, setCount] = useState(50)
  const [seed, setSeed] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState('')

  const launch = async (event) => {
    event.preventDefault()
    setError('')
    setResult('')

    const parsedCount = Number(count)
    const parsedSeed = normalizeSeed(seed)

    if (!Number.isFinite(parsedCount) || parsedCount <= 0) {
      setError('Count must be a positive number')
      return
    }

    if (!Number.isFinite(parsedSeed)) {
      setError('Seed must be numeric')
      return
    }

    setSubmitting(true)
    try {
      const response = await onLaunchChaos({ count: parsedCount, seed: parsedSeed })
      setResult(`Spawned ${response.spawned} ambulances (seed ${response.seed})`)
      setSeed(String(response.seed))
    } catch (launchError) {
      setError(launchError instanceof Error ? launchError.message : 'Chaos launch failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="chaos-panel" aria-label="Chaos controls">
      <button
        type="button"
        className={`chaos-button ${submitting ? 'active' : ''}`}
        onClick={() => setOpen(true)}
      >
        CHAOS
      </button>

      {open && (
        <div className="chaos-modal-backdrop" onClick={() => setOpen(false)}>
          <div className="chaos-modal" onClick={(event) => event.stopPropagation()}>
            <h2 className="panel-title">Launch Chaos</h2>
            <form className="chaos-form" onSubmit={launch}>
              <label>
                <span>count</span>
                <input
                  type="number"
                  min="1"
                  value={count}
                  onChange={(event) => setCount(event.target.value)}
                />
              </label>

              <label>
                <span>seed (optional)</span>
                <input
                  type="number"
                  value={seed}
                  onChange={(event) => setSeed(event.target.value)}
                  placeholder="auto-generated"
                />
              </label>

              <div className="chaos-actions">
                <button type="button" onClick={() => setOpen(false)} disabled={submitting}>
                  Cancel
                </button>
                <button type="submit" disabled={submitting}>
                  {submitting ? 'Launching…' : 'Launch Chaos'}
                </button>
              </div>

              {error && <p className="error-text">{error}</p>}
              {result && <p className="success-text">{result}</p>}
            </form>
          </div>
        </div>
      )}
    </section>
  )
}

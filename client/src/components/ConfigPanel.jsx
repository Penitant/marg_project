import { useMemo, useState } from 'react'

const DEFAULT_FORM = {
  grid_rows: 4,
  grid_cols: 4,
  corridor_depth: 3,
  tick_interval: 1,
  deadlock_check_interval: 5,
  snapshot_broadcast_interval: 2,
}

function toPayload(form) {
  return {
    seed: Date.now(),
    grid_rows: Number(form.grid_rows),
    grid_cols: Number(form.grid_cols),
    corridor_depth: Number(form.corridor_depth),
    tick_interval: Number(form.tick_interval),
    deadlock_check_interval: Number(form.deadlock_check_interval),
    snapshot_broadcast_interval: Number(form.snapshot_broadcast_interval),
  }
}

export default function ConfigPanel({
  onApplyConfig,
  isWaitingSnapshot,
  uiConfig,
  onUiConfigChange,
  hiddenAmbulances,
}) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(DEFAULT_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const disabled = useMemo(() => submitting || isWaitingSnapshot, [isWaitingSnapshot, submitting])

  const updateField = (field) => (event) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }))
  }

  const updateUiField = (field) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : Number(event.target.value)
    onUiConfigChange((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')

    try {
      await onApplyConfig(toPayload(form))
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to apply config')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <aside className={`config-panel ${open ? 'open' : 'collapsed'}`}>
      <button type="button" className="config-toggle" onClick={() => setOpen((value) => !value)}>
        {open ? 'Close Config' : 'Open Config'}
      </button>

      <div className="config-panel-body">
        <form className="config-form" onSubmit={handleSubmit}>
          <h2 className="panel-title">Configuration</h2>

          <label>
            <span>grid_rows</span>
            <input type="number" min="1" value={form.grid_rows} onChange={updateField('grid_rows')} />
          </label>

          <label>
            <span>grid_cols</span>
            <input type="number" min="1" value={form.grid_cols} onChange={updateField('grid_cols')} />
          </label>

          <label>
            <span>corridor_depth</span>
            <input type="number" min="1" value={form.corridor_depth} onChange={updateField('corridor_depth')} />
          </label>

          <label>
            <span>tick_interval</span>
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.tick_interval}
              onChange={updateField('tick_interval')}
            />
          </label>

          <label>
            <span>deadlock_check_interval</span>
            <input
              type="number"
              min="1"
              value={form.deadlock_check_interval}
              onChange={updateField('deadlock_check_interval')}
            />
          </label>

          <label>
            <span>snapshot_broadcast_interval</span>
            <input
              type="number"
              min="1"
              value={form.snapshot_broadcast_interval}
              onChange={updateField('snapshot_broadcast_interval')}
            />
          </label>

          <button type="submit" disabled={disabled}>
            {isWaitingSnapshot ? 'Waiting for snapshot…' : submitting ? 'Applying…' : 'Apply & Reset'}
          </button>

          {error && <p className="error-text">{error}</p>}
        </form>

        <div className="ui-config-block">
          <h3 className="sub-title">Visibility</h3>

          <label>
            <span>fade_after_ticks</span>
            <input
              type="number"
              min="1"
              value={uiConfig.fadeAfterTicks}
              onChange={updateUiField('fadeAfterTicks')}
            />
          </label>

          <label className="check-line">
            <input
              type="checkbox"
              checked={uiConfig.autoSpawnEnabled}
              onChange={updateUiField('autoSpawnEnabled')}
            />
            <span>auto_spawn_continuous</span>
          </label>

          <label>
            <span>auto_spawn_interval_ticks</span>
            <input
              type="number"
              min="1"
              value={uiConfig.autoSpawnIntervalTicks}
              onChange={updateUiField('autoSpawnIntervalTicks')}
            />
          </label>

          <h3 className="sub-title">Hidden Ambulances</h3>
          <div className="hidden-list">
            {hiddenAmbulances.length === 0 ? (
              <small>None</small>
            ) : (
              hiddenAmbulances.map((item) => (
                <small key={item.id}>{item.id} · hidden at tick {item.hiddenAt}</small>
              ))
            )}
          </div>
        </div>
      </div>
    </aside>
  )
}

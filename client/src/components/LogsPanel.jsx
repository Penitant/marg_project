import { formatNodeLabel } from '../utils/labels'

export default function LogsPanel({ logs }) {
  return (
    <section className="logs-panel" aria-label="Ambulance movement logs">
      <h2 className="panel-title">Movement Logs</h2>
      <div className="logs-list">
        {logs.length === 0 ? (
          <small>No movement events yet</small>
        ) : (
          logs.map((entry) => (
            <div key={entry.id} className="log-item">
              <small>
                t{entry.tick} · {entry.ambulanceId} · {formatNodeLabel(entry.from)} → {formatNodeLabel(entry.to)}
              </small>
            </div>
          ))
        )}
      </div>
    </section>
  )
}

function formatNumber(value, digits = 2) {
  const numeric = Number(value ?? 0)
  if (Number.isNaN(numeric)) {
    return '0'
  }
  return numeric.toFixed(digits)
}

export default function MetricsPanel({ metrics }) {
  return (
    <section className="metrics-panel" aria-label="Simulation metrics">
      <h2 className="panel-title">Metrics</h2>
      <div className="metrics-grid">
        <div className="metric-item">
          <span className="metric-label">Avg Response Time</span>
          <span className="metric-value">{formatNumber(metrics.avg_response_time)}</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Deadlock Count</span>
          <span className="metric-value">{formatNumber(metrics.deadlock_count, 0)}</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Fairness Index</span>
          <span className="metric-value">{formatNumber(metrics.fairness_index)}</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Queue Length</span>
          <span className="metric-value">{formatNumber(metrics.average_queue_length)}</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Reservation Success Rate</span>
          <span className="metric-value">{formatNumber(Number(metrics.reservation_success_rate) * 100)}%</span>
        </div>
      </div>
    </section>
  )
}

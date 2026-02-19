import MetricsPanel from './MetricsPanel'
import SpawnPanel from './SpawnPanel'
import ConfigPanel from './ConfigPanel'

export default function BodySection({
  metrics,
  connectionState,
  timestamp,
  nodes,
  onSpawnAmbulance,
  onApplyConfig,
  isWaitingSnapshot,
  uiConfig,
  onUiConfigChange,
  hiddenAmbulances,
}) {
  return (
    <section className="body-section">
      <div className="status-row" role="status" aria-live="polite">
        <span>Socket: {connectionState}</span>
        <span>Tick: {timestamp}</span>
      </div>
      <div className="panel-grid">
        <div className="controls-column">
          <SpawnPanel nodes={nodes} onSpawnAmbulance={onSpawnAmbulance} />
          <ConfigPanel
            onApplyConfig={onApplyConfig}
            isWaitingSnapshot={isWaitingSnapshot}
            uiConfig={uiConfig}
            onUiConfigChange={onUiConfigChange}
            hiddenAmbulances={hiddenAmbulances}
          />
        </div>
        <MetricsPanel metrics={metrics} />
      </div>
    </section>
  )
}

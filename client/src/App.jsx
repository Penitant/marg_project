import { useEffect, useRef, useState } from 'react'
import Navbar from './components/Navbar'
import HeroCanvas from './components/HeroCanvas'
import BodySection from './components/BodySection'
import { useSimulationSocket } from './hooks/useSimulationSocket'

function App() {
  const { snapshot, connectionState } = useSimulationSocket(80)
  const [awaitingSnapshot, setAwaitingSnapshot] = useState(false)
  const [uiConfig, setUiConfig] = useState({
    fadeAfterTicks: 15,
    autoSpawnEnabled: false,
    autoSpawnIntervalTicks: 8,
  })
  const [hiddenAmbulances, setHiddenAmbulances] = useState([])
  const [movementLogs, setMovementLogs] = useState([])
  const lastSeenTimestampRef = useRef(0)
  const arrivedAtByIdRef = useRef(new Map())
  const autoSpawnTickRef = useRef(-1)
  const previousNodeByIdRef = useRef(new Map())

  useEffect(() => {
    if (snapshot.timestamp > lastSeenTimestampRef.current) {
      lastSeenTimestampRef.current = snapshot.timestamp
      setAwaitingSnapshot(false)
    }
  }, [snapshot.timestamp])

  const applyConfig = async (configPayload) => {
    const response = await fetch('http://localhost:8000/reset_with_config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(configPayload),
    })

    if (!response.ok) {
      throw new Error('Failed to apply simulation configuration')
    }

    setAwaitingSnapshot(true)
  }

  const spawnAmbulance = async (payload) => {
    const response = await fetch('http://localhost:8000/spawn_ambulance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      throw new Error('Failed to spawn ambulance')
    }

    const data = await response.json()
    return data.ambulance_id
  }

  const launchChaos = async (payload) => {
    const response = await fetch('http://localhost:8000/chaos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      const errorBody = await response.json().catch(() => null)
      const detail = typeof errorBody?.detail === 'string' ? errorBody.detail : 'Failed to launch chaos'
      throw new Error(detail)
    }

    return response.json()
  }

  useEffect(() => {
    const nowTick = Number(snapshot.timestamp ?? 0)
    const map = arrivedAtByIdRef.current

    const aliveIds = new Set((snapshot.ambulances ?? []).map((ambulance) => ambulance.id))

    for (const ambulance of snapshot.ambulances ?? []) {
      if (ambulance.arrived && !map.has(ambulance.id)) {
        map.set(ambulance.id, nowTick)
      }
      if (!ambulance.arrived && map.has(ambulance.id)) {
        map.delete(ambulance.id)
      }
    }

    for (const id of Array.from(map.keys())) {
      if (!aliveIds.has(id)) {
        map.delete(id)
      }
    }

    const hidden = []
    for (const [id, arrivedAt] of map.entries()) {
      if (nowTick - arrivedAt >= Number(uiConfig.fadeAfterTicks)) {
        hidden.push({ id, hiddenAt: arrivedAt + Number(uiConfig.fadeAfterTicks) })
      }
    }
    hidden.sort((a, b) => b.hiddenAt - a.hiddenAt)
    setHiddenAmbulances(hidden)
  }, [snapshot.ambulances, snapshot.timestamp, uiConfig.fadeAfterTicks])

  useEffect(() => {
    if (!uiConfig.autoSpawnEnabled) {
      return
    }

    const tick = Number(snapshot.timestamp ?? 0)
    const interval = Math.max(1, Number(uiConfig.autoSpawnIntervalTicks))
    const nodes = snapshot.nodes ?? []

    if (tick <= 0 || nodes.length < 2 || tick % interval !== 0 || autoSpawnTickRef.current === tick) {
      return
    }

    autoSpawnTickRef.current = tick

    const startIndex = Math.floor(Math.random() * nodes.length)
    let destinationIndex = Math.floor(Math.random() * nodes.length)
    if (destinationIndex === startIndex) {
      destinationIndex = (destinationIndex + 1) % nodes.length
    }

    spawnAmbulance({
      start_node: nodes[startIndex].id,
      destination_node: nodes[destinationIndex].id,
    }).catch(() => {
      // Keep UI passive on transient spawn failures.
    })
  }, [snapshot.nodes, snapshot.timestamp, uiConfig.autoSpawnEnabled, uiConfig.autoSpawnIntervalTicks])

  useEffect(() => {
    const tick = Number(snapshot.timestamp ?? 0)
    const previousNodeById = previousNodeByIdRef.current
    const nextMap = new Map()
    const newEntries = []

    for (const ambulance of snapshot.ambulances ?? []) {
      const currentNode = ambulance.current_node
      const previousNode = previousNodeById.get(ambulance.id)

      if (previousNode && previousNode !== currentNode) {
        newEntries.push({
          id: `${ambulance.id}:${tick}:${currentNode}`,
          tick,
          ambulanceId: ambulance.id,
          from: previousNode,
          to: currentNode,
        })
      }

      nextMap.set(ambulance.id, currentNode)
    }

    previousNodeByIdRef.current = nextMap

    if (newEntries.length) {
      setMovementLogs((prev) => [...newEntries, ...prev].slice(0, 200))
    }
  }, [snapshot.ambulances, snapshot.timestamp])

  const fadeAfterTicks = Math.max(1, Number(uiConfig.fadeAfterTicks))
  const visibleAmbulances = (snapshot.ambulances ?? []).filter((ambulance) => {
    if (!ambulance.arrived) {
      return true
    }
    const arrivedAt = arrivedAtByIdRef.current.get(ambulance.id)
    if (arrivedAt === undefined) {
      return true
    }
    return Number(snapshot.timestamp ?? 0) - arrivedAt < fadeAfterTicks
  })

  return (
    <div className="app-shell">
      <Navbar />
      <main className="app-main">
        <HeroCanvas snapshot={{ ...snapshot, ambulances: visibleAmbulances }} />
        <BodySection
          metrics={snapshot.metrics}
          connectionState={connectionState}
          timestamp={snapshot.timestamp}
          nodes={snapshot.nodes}
          onSpawnAmbulance={spawnAmbulance}
          onApplyConfig={applyConfig}
          isWaitingSnapshot={awaitingSnapshot}
          uiConfig={uiConfig}
          onUiConfigChange={setUiConfig}
          hiddenAmbulances={hiddenAmbulances}
          movementLogs={movementLogs}
          onLaunchChaos={launchChaos}
        />
      </main>
    </div>
  )
}

export default App

import { useEffect, useMemo, useState } from 'react'
import { formatNodeLabel } from '../utils/labels'

function getDefaultNodes(nodes) {
  if (!Array.isArray(nodes) || nodes.length === 0) {
    return { start: '', destination: '' }
  }

  return {
    start: nodes[0].id,
    destination: nodes[nodes.length - 1].id,
  }
}

export default function SpawnPanel({ nodes, onSpawnAmbulance }) {
  const defaults = useMemo(() => getDefaultNodes(nodes), [nodes])
  const [startNode, setStartNode] = useState(defaults.start)
  const [destinationNode, setDestinationNode] = useState(defaults.destination)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const options = useMemo(() => (Array.isArray(nodes) ? nodes.map((node) => node.id) : []), [nodes])

  useEffect(() => {
    if (!options.length) {
      setStartNode('')
      setDestinationNode('')
      return
    }

    if (!options.includes(startNode)) {
      setStartNode(defaults.start)
    }

    if (!options.includes(destinationNode)) {
      setDestinationNode(defaults.destination)
    }
  }, [defaults.destination, defaults.start, destinationNode, options, startNode])

  const syncDefaults = () => {
    setStartNode(defaults.start)
    setDestinationNode(defaults.destination)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setSuccess('')

    if (!startNode || !destinationNode) {
      setError('Pick both start and destination nodes')
      return
    }

    setSubmitting(true)
    try {
      const ambulanceId = await onSpawnAmbulance({ start_node: startNode, destination_node: destinationNode })
      setSuccess(`Spawned ${ambulanceId}`)
    } catch (spawnError) {
      setError(spawnError instanceof Error ? spawnError.message : 'Failed to spawn ambulance')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="spawn-panel" aria-label="Ambulance controls">
      <h2 className="panel-title">Ambulance</h2>
      <form className="spawn-form" onSubmit={handleSubmit}>
        <label>
          <span>start_node</span>
          <select value={startNode} onChange={(event) => setStartNode(event.target.value)}>
            {options.map((id) => (
              <option key={`start-${id}`} value={id}>
                {formatNodeLabel(id)}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>destination_node</span>
          <select value={destinationNode} onChange={(event) => setDestinationNode(event.target.value)}>
            {options.map((id) => (
              <option key={`destination-${id}`} value={id}>
                {formatNodeLabel(id)}
              </option>
            ))}
          </select>
        </label>

        <div className="spawn-actions">
          <button type="button" onClick={syncDefaults} disabled={submitting}>
            Use Defaults
          </button>
          <button type="submit" disabled={submitting || options.length < 2}>
            {submitting ? 'Spawning…' : 'Spawn Ambulance'}
          </button>
        </div>

        {error && <p className="error-text">{error}</p>}
        {success && <p className="success-text">{success}</p>}
      </form>
    </section>
  )
}

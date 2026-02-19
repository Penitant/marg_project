export function formatNodeLabel(nodeId) {
  const match = /^r(\d+)c(\d+)$/i.exec(String(nodeId ?? ''))
  if (!match) {
    return String(nodeId ?? '')
  }
  return `J-${match[1]}-${match[2]}`
}

export function formatNodeLongLabel(nodeId) {
  const match = /^r(\d+)c(\d+)$/i.exec(String(nodeId ?? ''))
  if (!match) {
    return `Junction ${String(nodeId ?? '')}`
  }
  return `Junction ${formatNodeLabel(nodeId)}`
}

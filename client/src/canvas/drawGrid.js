function parseGridIndex(nodeId) {
  const match = /^r(\d+)c(\d+)$/i.exec(String(nodeId))
  if (!match) {
    return null
  }

  return {
    row: Number(match[1]),
    col: Number(match[2]),
  }
}

export function buildNodeLayout(nodes, edges, width, height, padding = 72) {
  if (!nodes.length || width <= 0 || height <= 0) {
    return new Map()
  }

  const parsed = nodes.map((node, index) => ({
    id: node.id,
    parsed: parseGridIndex(node.id),
    index,
  }))

  const hasGridCoordinates = parsed.every((item) => item.parsed !== null)
  const innerWidth = Math.max(width - padding * 2, 1)
  const innerHeight = Math.max(height - padding * 2, 1)
  const layout = new Map()

  if (hasGridCoordinates) {
    const maxRow = Math.max(...parsed.map((item) => item.parsed.row), 1)
    const maxCol = Math.max(...parsed.map((item) => item.parsed.col), 1)

    for (const item of parsed) {
      const x = padding + (maxCol === 0 ? 0 : (item.parsed.col / maxCol) * innerWidth)
      const y = padding + (maxRow === 0 ? 0 : (item.parsed.row / maxRow) * innerHeight)
      layout.set(item.id, { x, y })
    }
    return layout
  }

  const side = Math.ceil(Math.sqrt(nodes.length))
  for (const item of parsed) {
    const row = Math.floor(item.index / side)
    const col = item.index % side
    const x = padding + (side <= 1 ? 0 : (col / (side - 1)) * innerWidth)
    const y = padding + (side <= 1 ? 0 : (row / (side - 1)) * innerHeight)
    layout.set(item.id, { x, y })
  }

  return layout
}

export function drawGrid(ctx, edges, layout, colors) {
  ctx.save()
  ctx.lineWidth = 0.9
  ctx.globalAlpha = 0.55

  for (const edge of edges) {
    const source = layout.get(edge.source)
    const target = layout.get(edge.target)
    if (!source || !target) {
      continue
    }

    const isHorizontal = Math.abs(target.x - source.x) >= Math.abs(target.y - source.y)
    ctx.strokeStyle = isHorizontal ? colors.edgeEW : colors.edgeNS
    ctx.shadowColor = ctx.strokeStyle
    ctx.shadowBlur = 1.5

    ctx.beginPath()
    ctx.moveTo(source.x, source.y)
    ctx.lineTo(target.x, target.y)
    ctx.stroke()
  }

  ctx.shadowBlur = 0
  ctx.restore()
}

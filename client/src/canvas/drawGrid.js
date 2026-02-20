function hashValue(input) {
  let value = 0
  for (let i = 0; i < input.length; i += 1) {
    value = (value * 31 + input.charCodeAt(i)) >>> 0
  }
  return value / 4294967295
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

export function buildNodeLayout(nodes, edges, width, height, padding = 72) {
  if (!nodes.length || width <= 0 || height <= 0) {
    return new Map()
  }

  const innerWidth = Math.max(width - padding * 2, 1)
  const innerHeight = Math.max(height - padding * 2, 1)

  const positions = new Map(
    nodes.map((node, index) => {
      const radial = (index / Math.max(nodes.length, 1)) * Math.PI * 2
      const jitterX = (hashValue(`${node.id}:x`) - 0.5) * innerWidth * 0.24
      const jitterY = (hashValue(`${node.id}:y`) - 0.5) * innerHeight * 0.24
      const x = padding + innerWidth * 0.5 + Math.cos(radial) * innerWidth * 0.25 + jitterX
      const y = padding + innerHeight * 0.5 + Math.sin(radial) * innerHeight * 0.25 + jitterY
      return [node.id, { x, y }]
    }),
  )

  const uniqueEdges = []
  const seen = new Set()
  for (const edge of edges) {
    const source = String(edge.source)
    const target = String(edge.target)
    const key = source < target ? `${source}|${target}` : `${target}|${source}`
    if (seen.has(key)) {
      continue
    }
    seen.add(key)
    uniqueEdges.push({ source, target })
  }

  const area = innerWidth * innerHeight
  const k = Math.sqrt(area / Math.max(nodes.length, 1))
  const iterations = Math.min(170, 70 + nodes.length)

  for (let step = 0; step < iterations; step += 1) {
    const displacement = new Map(nodes.map((node) => [node.id, { dx: 0, dy: 0 }]))

    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        const a = positions.get(nodes[i].id)
        const b = positions.get(nodes[j].id)
        if (!a || !b) {
          continue
        }

        let dx = a.x - b.x
        let dy = a.y - b.y
        let distance = Math.hypot(dx, dy)
        if (distance < 0.001) {
          distance = 0.001
          dx = (hashValue(`${nodes[i].id}:${nodes[j].id}:x`) - 0.5) * 0.01
          dy = (hashValue(`${nodes[i].id}:${nodes[j].id}:y`) - 0.5) * 0.01
        }

        const force = (k * k) / distance
        const fx = (dx / distance) * force
        const fy = (dy / distance) * force

        const dispA = displacement.get(nodes[i].id)
        const dispB = displacement.get(nodes[j].id)
        if (dispA && dispB) {
          dispA.dx += fx
          dispA.dy += fy
          dispB.dx -= fx
          dispB.dy -= fy
        }
      }
    }

    for (const edge of uniqueEdges) {
      const source = positions.get(edge.source)
      const target = positions.get(edge.target)
      if (!source || !target) {
        continue
      }

      const dx = source.x - target.x
      const dy = source.y - target.y
      const distance = Math.max(0.001, Math.hypot(dx, dy))
      const force = (distance * distance) / k
      const fx = (dx / distance) * force
      const fy = (dy / distance) * force

      const dispSource = displacement.get(edge.source)
      const dispTarget = displacement.get(edge.target)
      if (dispSource && dispTarget) {
        dispSource.dx -= fx
        dispSource.dy -= fy
        dispTarget.dx += fx
        dispTarget.dy += fy
      }
    }

    const cooling = Math.max(0.08, 1 - step / iterations)
    const temp = k * 0.18 * cooling

    for (const node of nodes) {
      const point = positions.get(node.id)
      const disp = displacement.get(node.id)
      if (!point || !disp) {
        continue
      }

      const distance = Math.max(0.001, Math.hypot(disp.dx, disp.dy))
      const nextX = point.x + (disp.dx / distance) * Math.min(distance, temp)
      const nextY = point.y + (disp.dy / distance) * Math.min(distance, temp)

      point.x = clamp(nextX, padding, padding + innerWidth)
      point.y = clamp(nextY, padding, padding + innerHeight)
    }
  }

  return positions
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

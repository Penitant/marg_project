function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

export function drawCongestion(ctx, edges, layout, colors) {
  ctx.save()

  for (const edge of edges) {
    const source = layout.get(edge.source)
    const target = layout.get(edge.target)
    if (!source || !target) {
      continue
    }

    const congestion = clamp(Number(edge.congestion_factor ?? 1), 0, 2)
    const intensity = clamp((congestion - 0.2) / 1.8, 0, 1)

    ctx.lineWidth = 2 + intensity * 2
    ctx.strokeStyle = intensity > 0.5 ? colors.congestionHigh : colors.congestionLow
    ctx.globalAlpha = 0.25 + intensity * 0.65

    ctx.beginPath()
    ctx.moveTo(source.x, source.y)
    ctx.lineTo(target.x, target.y)
    ctx.stroke()
  }

  ctx.restore()
}

import { PHASE_COLORS } from '../types/snapshot'

export function drawSignals(ctx, signals, layout, colors) {
  ctx.save()

  for (const signal of signals) {
    const node = layout.get(signal.intersection_id)
    if (!node) {
      continue
    }

    const phaseKey = PHASE_COLORS[signal.current_phase] ?? 'YELLOW'
    const fill =
      phaseKey === 'NS_GREEN'
        ? colors.signalNS
        : phaseKey === 'EW_GREEN'
          ? colors.signalEW
          : colors.signalYellow

    ctx.shadowColor = fill
    ctx.shadowBlur = 10
    ctx.beginPath()
    ctx.fillStyle = fill
    ctx.strokeStyle = colors.signalOutline
    ctx.lineWidth = 1.2
    ctx.arc(node.x, node.y, 5.4, 0, Math.PI * 2)
    ctx.fill()
    ctx.stroke()

    ctx.shadowBlur = 0
    ctx.beginPath()
    ctx.fillStyle = colors.signalCore
    ctx.arc(node.x, node.y, 1.6, 0, Math.PI * 2)
    ctx.fill()
  }

  ctx.restore()
}

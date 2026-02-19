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

    ctx.beginPath()
    ctx.fillStyle = fill
    ctx.arc(node.x, node.y, 5, 0, Math.PI * 2)
    ctx.fill()
  }

  ctx.restore()
}

function lerp(start, end, t) {
  return start + (end - start) * t
}

function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3)
}

function getAmbulanceNode(ambulance, previousSnapshot) {
  if (!previousSnapshot) {
    return ambulance.current_node
  }

  const previous = previousSnapshot.ambulances.find((item) => item.id === ambulance.id)
  return previous?.current_node ?? ambulance.current_node
}

export function drawReservations(ctx, reservations, ambulancesById, layout, colors, clock) {
  ctx.save()

  for (const reservation of reservations) {
    if (reservation.activated_at === null || reservation.activated_at === undefined) {
      continue
    }

    const ambulance = ambulancesById.get(reservation.ambulance_id)
    const fromNode = ambulance ? layout.get(ambulance.current_node) : null
    const toNode = layout.get(reservation.intersection_id)
    if (!fromNode || !toNode) {
      continue
    }

    ctx.strokeStyle = colors.corridor
    ctx.lineWidth = 2
    ctx.globalAlpha = 0.8

    ctx.beginPath()
    ctx.moveTo(fromNode.x, fromNode.y)
    ctx.lineTo(toNode.x, toNode.y)
    ctx.stroke()

    const arrowProgress = (clock / 700) % 1
    const arrowX = lerp(fromNode.x, toNode.x, arrowProgress)
    const arrowY = lerp(fromNode.y, toNode.y, arrowProgress)

    ctx.beginPath()
    ctx.fillStyle = colors.corridor
    ctx.arc(arrowX, arrowY, 2.5, 0, Math.PI * 2)
    ctx.fill()
  }

  ctx.restore()
}

export function computeAmbulanceRenderPoints(ambulances, layout, previousSnapshot, progress) {
  const eased = easeOutCubic(Math.min(Math.max(progress, 0), 1))

  return ambulances
    .map((ambulance) => {
      const currentNode = layout.get(ambulance.current_node)
      if (!currentNode) {
        return null
      }

      const previousNodeId = getAmbulanceNode(ambulance, previousSnapshot)
      const previousNode = layout.get(previousNodeId) ?? currentNode

      return {
        id: ambulance.id,
        current_node: ambulance.current_node,
        destination: ambulance.destination,
        reservation_status: ambulance.reservation_status,
        x: lerp(previousNode.x, currentNode.x, eased),
        y: lerp(previousNode.y, currentNode.y, eased),
      }
    })
    .filter(Boolean)
}

export function drawDestinations(ctx, ambulances, layout, colors) {
  ctx.save()

  const seenDestinations = new Set()
  for (const ambulance of ambulances) {
    const destination = layout.get(ambulance.destination)
    if (!destination || seenDestinations.has(ambulance.destination)) {
      continue
    }
    seenDestinations.add(ambulance.destination)

    ctx.beginPath()
    ctx.strokeStyle = colors.destinationRing
    ctx.lineWidth = 1.4
    ctx.arc(destination.x, destination.y, 8.5, 0, Math.PI * 2)
    ctx.stroke()

    ctx.beginPath()
    ctx.fillStyle = colors.destinationCore
    ctx.arc(destination.x, destination.y, 2.6, 0, Math.PI * 2)
    ctx.fill()
  }

  ctx.restore()
}

export function drawAmbulances(ctx, ambulances, layout, previousSnapshot, progress, colors, clock) {
  ctx.save()

  const points = computeAmbulanceRenderPoints(ambulances, layout, previousSnapshot, progress)
  const ambulancesById = new Map(ambulances.map((item) => [item.id, item]))

  for (const point of points) {
    const ambulance = ambulancesById.get(point.id)
    if (!ambulance) {
      continue
    }

    const approved = Object.values(ambulance.reservation_window ?? {}).some(
      (state) => state?.status === 'approved',
    )
    const denied = ambulance.reservation_status === 'denied'

    if (approved) {
      ctx.shadowColor = colors.ambulanceGlow
      ctx.shadowBlur = 12
    } else {
      ctx.shadowBlur = 0
    }

    const pulse = denied ? 1 + 0.15 * Math.sin((clock / 220) * Math.PI * 2) : 1

    ctx.beginPath()
    ctx.fillStyle = colors.ambulanceFill
    ctx.strokeStyle = colors.ambulanceBorder
    ctx.lineWidth = 1.5
    ctx.arc(point.x, point.y, 5.5 * pulse, 0, Math.PI * 2)
    ctx.fill()
    ctx.stroke()
  }

  ctx.restore()
}

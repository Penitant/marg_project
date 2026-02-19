import { useEffect, useMemo, useRef, useState } from 'react'
import { buildNodeLayout, drawGrid } from '../canvas/drawGrid'
import { drawCongestion } from '../canvas/drawCongestion'
import { drawSignals } from '../canvas/drawSignals'
import {
  computeAmbulanceRenderPoints,
  drawAmbulances,
  drawDestinations,
  drawReservations,
} from '../canvas/drawAmbulances'
import { formatNodeLabel, formatNodeLongLabel } from '../utils/labels'

function getCssColorMap() {
  const styles = getComputedStyle(document.documentElement)
  return {
    edgeNS: styles.getPropertyValue('--road-ns').trim(),
    edgeEW: styles.getPropertyValue('--road-ew').trim(),
    congestionLow: styles.getPropertyValue('--road-congestion-low').trim(),
    congestionHigh: styles.getPropertyValue('--road-congestion-high').trim(),
    signalNS: styles.getPropertyValue('--primary').trim(),
    signalEW: styles.getPropertyValue('--secondary').trim(),
    signalYellow: styles.getPropertyValue('--accent').trim(),
    corridor: styles.getPropertyValue('--corridor-500').trim(),
    ambulanceFill: styles.getPropertyValue('--text').trim(),
    ambulanceBorder: styles.getPropertyValue('--primary').trim(),
    ambulanceGlow: styles.getPropertyValue('--accent').trim(),
    destinationRing: styles.getPropertyValue('--secondary').trim(),
    destinationCore: styles.getPropertyValue('--primary').trim(),
  }
}

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

function pointToSegmentDistance(px, py, ax, ay, bx, by) {
  const abx = bx - ax
  const aby = by - ay
  const abLengthSq = abx * abx + aby * aby
  if (abLengthSq === 0) {
    return Math.hypot(px - ax, py - ay)
  }

  const t = Math.max(0, Math.min(1, ((px - ax) * abx + (py - ay) * aby) / abLengthSq))
  const cx = ax + abx * t
  const cy = ay + aby * t
  return Math.hypot(px - cx, py - cy)
}

export default function HeroCanvas({ snapshot }) {
  const staticCanvasRef = useRef(null)
  const dynamicCanvasRef = useRef(null)
  const shellRef = useRef(null)
  const frameRef = useRef(null)
  const transitionStartRef = useRef(0)
  const previousSnapshotRef = useRef(null)
  const latestAmbulancePointsRef = useRef([])
  const sizeRef = useRef({ width: 0, height: 0 })
  const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 })
  const [hoverInfo, setHoverInfo] = useState(null)

  const layout = useMemo(() => {
    const { width, height } = canvasSize
    return buildNodeLayout(snapshot.nodes ?? [], snapshot.edges ?? [], width, height)
  }, [canvasSize, snapshot.edges, snapshot.nodes])

  useEffect(() => {
    const staticCanvas = staticCanvasRef.current
    const dynamicCanvas = dynamicCanvasRef.current
    if (!staticCanvas || !dynamicCanvas) {
      return
    }

    const resize = () => {
      const parent = staticCanvas.parentElement
      if (!parent) {
        return
      }

      const { width, height } = parent.getBoundingClientRect()
      sizeRef.current = { width, height }
      setCanvasSize({ width, height })
      const dpr = window.devicePixelRatio || 1

      ;[staticCanvas, dynamicCanvas].forEach((canvas) => {
        canvas.width = Math.floor(width * dpr)
        canvas.height = Math.floor(height * dpr)
        canvas.style.width = `${width}px`
        canvas.style.height = `${height}px`

        const ctx = canvas.getContext('2d')
        if (ctx) {
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
        }
      })
    }

    resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [])

  useEffect(() => {
    const staticCanvas = staticCanvasRef.current
    if (!staticCanvas) {
      return
    }

    const ctx = staticCanvas.getContext('2d')
    if (!ctx) {
      return
    }

    const { width, height } = sizeRef.current
    ctx.clearRect(0, 0, width, height)

    const colors = getCssColorMap()
    drawGrid(ctx, snapshot.edges ?? [], layout, colors)
  }, [layout, snapshot.edges])

  useEffect(() => {
    const dynamicCanvas = dynamicCanvasRef.current
    if (!dynamicCanvas) {
      return
    }

    const ctx = dynamicCanvas.getContext('2d')
    if (!ctx) {
      return
    }

    transitionStartRef.current = performance.now()
    const transitionDuration = 760

    const paint = (now) => {
      const { width, height } = sizeRef.current
      const rawProgress = Math.min((now - transitionStartRef.current) / transitionDuration, 1)
      const progress = easeInOutCubic(rawProgress)
      const colors = getCssColorMap()

      ctx.clearRect(0, 0, width, height)
      drawCongestion(ctx, snapshot.edges ?? [], layout, colors)
      drawSignals(ctx, snapshot.signals ?? [], layout, colors)
      drawDestinations(ctx, snapshot.ambulances ?? [], layout, colors)

      const ambulancesById = new Map((snapshot.ambulances ?? []).map((item) => [item.id, item]))
      drawReservations(ctx, snapshot.reservations ?? [], ambulancesById, layout, colors, now)
      latestAmbulancePointsRef.current = computeAmbulanceRenderPoints(
        snapshot.ambulances ?? [],
        layout,
        previousSnapshotRef.current,
        progress,
      )
      drawAmbulances(
        ctx,
        snapshot.ambulances ?? [],
        layout,
        previousSnapshotRef.current,
        progress,
        colors,
        now,
      )

      if (rawProgress < 1) {
        frameRef.current = requestAnimationFrame(paint)
      }
    }

    frameRef.current = requestAnimationFrame(paint)
    previousSnapshotRef.current = snapshot

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current)
      }
    }
  }, [layout, snapshot])

  const handlePointerMove = (event) => {
    const shell = shellRef.current
    if (!shell) {
      return
    }

    const rect = shell.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top

    let closestAmbulance = null
    let closestAmbulanceDist = Infinity
    for (const point of latestAmbulancePointsRef.current) {
      const distance = Math.hypot(point.x - x, point.y - y)
      if (distance < closestAmbulanceDist) {
        closestAmbulanceDist = distance
        closestAmbulance = point
      }
    }

    if (closestAmbulance && closestAmbulanceDist < 14) {
      setHoverInfo({
        x,
        y,
        label: `AMB ${closestAmbulance.id} · ${formatNodeLabel(closestAmbulance.current_node)} → ${formatNodeLabel(closestAmbulance.destination)}`,
      })
      return
    }

    let closestEdge = null
    let closestEdgeDist = Infinity
    for (const edge of snapshot.edges ?? []) {
      const source = layout.get(edge.source)
      const target = layout.get(edge.target)
      if (!source || !target) {
        continue
      }
      const distance = pointToSegmentDistance(x, y, source.x, source.y, target.x, target.y)
      if (distance < closestEdgeDist) {
        closestEdgeDist = distance
        closestEdge = edge
      }
    }

    if (closestEdge && closestEdgeDist < 7) {
      setHoverInfo({
        x,
        y,
        label: `${formatNodeLabel(closestEdge.source)} → ${formatNodeLabel(closestEdge.target)} · congestion ${(Number(closestEdge.congestion_factor) || 0).toFixed(2)}`,
      })
      return
    }

    let closestNode = null
    let closestNodeDist = Infinity
    for (const node of snapshot.nodes ?? []) {
      const point = layout.get(node.id)
      if (!point) {
        continue
      }
      const distance = Math.hypot(point.x - x, point.y - y)
      if (distance < closestNodeDist) {
        closestNodeDist = distance
        closestNode = node.id
      }
    }

    if (closestNode && closestNodeDist < 12) {
      setHoverInfo({ x, y, label: formatNodeLongLabel(closestNode) })
      return
    }

    setHoverInfo(null)
  }

  return (
    <section className="hero" aria-label="Simulation visualizer">
      <div
        className="canvas-shell"
        ref={shellRef}
        onMouseMove={handlePointerMove}
        onMouseLeave={() => setHoverInfo(null)}
      >
        <canvas ref={staticCanvasRef} aria-hidden="true" />
        <canvas ref={dynamicCanvasRef} aria-hidden="true" />
        {hoverInfo && (
          <div
            className="canvas-tooltip"
            style={{ left: `${hoverInfo.x + 12}px`, top: `${hoverInfo.y + 12}px` }}
          >
            {hoverInfo.label}
          </div>
        )}
      </div>
    </section>
  )
}

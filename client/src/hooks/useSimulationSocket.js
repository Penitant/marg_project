import { useCallback, useEffect, useRef, useState } from 'react'
import { EMPTY_SNAPSHOT, normalizeSnapshot } from '../types/snapshot'

const SOCKET_URL = 'ws://localhost:8000/ws'
const STATE_CONNECTING = 'connecting'
const STATE_CONNECTED = 'connected'
const STATE_DISCONNECTED = 'disconnected'

export function useSimulationSocket(throttleMs = 100) {
  const [snapshot, setSnapshot] = useState(EMPTY_SNAPSHOT)
  const [connectionState, setConnectionState] = useState(STATE_CONNECTING)

  const socketRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const latestMessageRef = useRef(null)
  const throttleTimerRef = useRef(null)

  const flushSnapshot = useCallback(() => {
    if (!latestMessageRef.current) {
      return
    }

    setSnapshot(normalizeSnapshot(latestMessageRef.current))
    latestMessageRef.current = null
    throttleTimerRef.current = null
  }, [])

  const queueSnapshot = useCallback(
    (payload) => {
      latestMessageRef.current = payload
      if (throttleMs <= 0) {
        flushSnapshot()
        return
      }

      if (throttleTimerRef.current) {
        return
      }

      throttleTimerRef.current = setTimeout(flushSnapshot, throttleMs)
    },
    [flushSnapshot, throttleMs],
  )

  const connect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close()
    }

    setConnectionState(STATE_CONNECTING)

    const socket = new WebSocket(SOCKET_URL)
    socketRef.current = socket

    socket.onopen = () => {
      setConnectionState(STATE_CONNECTED)
    }

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        queueSnapshot(parsed)
      } catch {
        // Ignore malformed payloads without mutating state.
      }
    }

    socket.onerror = () => {
      setConnectionState(STATE_DISCONNECTED)
    }

    socket.onclose = () => {
      setConnectionState(STATE_DISCONNECTED)
      reconnectTimerRef.current = setTimeout(connect, 1000)
    }
  }, [queueSnapshot])

  useEffect(() => {
    connect()

    fetch('http://localhost:8000/state')
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (data) {
          setSnapshot(normalizeSnapshot(data))
        }
      })
      .catch(() => {
        // Snapshot bootstrap is best-effort only.
      })

    return () => {
      if (socketRef.current) {
        socketRef.current.close()
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
      }
      if (throttleTimerRef.current) {
        clearTimeout(throttleTimerRef.current)
      }
    }
  }, [connect])

  return {
    snapshot,
    connectionState,
  }
}

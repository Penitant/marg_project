export const PHASE_COLORS = {
  NS_GREEN: 'NS_GREEN',
  EW_GREEN: 'EW_GREEN',
  NS_YELLOW: 'YELLOW',
  EW_YELLOW: 'YELLOW',
  YELLOW: 'YELLOW',
}

export const EMPTY_SNAPSHOT = {
  timestamp: 0,
  running: false,
  nodes: [],
  signals: [],
  ambulances: [],
  edges: [],
  reservations: [],
  deadlocks: [],
  revocations: [],
  metrics: {
    avg_response_time: 0,
    deadlock_count: 0,
    fairness_index: 0,
    average_queue_length: 0,
    reservation_success_rate: 0,
  },
}

export function isSnapshot(value) {
  return (
    value &&
    typeof value === 'object' &&
    Array.isArray(value.nodes) &&
    Array.isArray(value.edges) &&
    Array.isArray(value.signals) &&
    Array.isArray(value.ambulances) &&
    typeof value.metrics === 'object'
  )
}

export function normalizeSnapshot(raw) {
  if (!isSnapshot(raw)) {
    return EMPTY_SNAPSHOT
  }

  return {
    ...EMPTY_SNAPSHOT,
    ...raw,
    metrics: {
      ...EMPTY_SNAPSHOT.metrics,
      ...(raw.metrics ?? {}),
    },
  }
}

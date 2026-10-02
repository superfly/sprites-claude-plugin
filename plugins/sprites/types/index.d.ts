export type SpriteSummary = {
  id: string
  name: string
  organization: string
  orgId: string
  url: string
  status: string
  version: string
  created: string
  uri: string
}

export type ServiceRow = { name: string; status: string }

export type CheckpointRow = { id: string; comment: string; created: string }

export type Section<T> = {
  state: 'idle' | 'loading' | 'ready' | 'error'
  items: T[]
  message: string
}

export type LogsView = {
  service: string
  state: 'loading' | 'ready' | 'error'
  text: string
}

export type InspectorState = {
  status: string
  statusTone: 'info' | 'error'
  prefix: string
  sprites: SpriteSummary[]
  cursor: string | null
  listedAt: number | null
  isListing: boolean
  selected: SpriteSummary | null
  isChecking: boolean
  attachedId: string | null
  services: Section<ServiceRow>
  checkpoints: Section<CheckpointRow>
  logs: LogsView | null
}

declare module 'claude-code' {
  interface PluginState {
    sprites: { inspector: InspectorState }
  }
}

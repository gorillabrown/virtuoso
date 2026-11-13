export type ProgressItem = {
  id: string
  label: string
  state: string
  started?: string
  finished?: string
}

export type ProgressRun = {
  schema: number
  run: { id: string; title: string; kind?: 'dispatch' | 'epic' }
  root?: string
  colors?: [string, string]
  started: string
  updated: string
  milestones: ProgressItem[]
  current?: string | null
  steps: ProgressItem[]
  end?: { state: 'complete' | 'stopped'; at: string; reason?: string; evidence?: string }
}

export type ProgressView = { kind: 'running' | 'ended'; doc: ProgressRun }

declare module 'claude-code' {
  interface PluginState {
    virtuoso: { progress: ProgressView | null; progressError: string | null }
  }
}

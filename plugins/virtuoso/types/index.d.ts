export type ProgressItem = { id: string; label: string; state: string }

export type Progress = {
  title: string
  deadline?: string
  updated?: string
  now?: string
  items: ProgressItem[]
}

declare module 'claude-code' {
  interface PluginState {
    virtuoso: { progress: Progress | null; progressError: string | null }
  }
}

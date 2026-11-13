// Virtuoso progress band: two lines above the prompt and a status-line entry showing
// progress through the project's build queue (references/registry-contract.md, "The
// progress band"). It reads one JSON file at session start, every 30 seconds, and at the
// end of every turn. The file is the `progressFile` option when set, else the registry's
// `progress` role; never a conventional path. Where neither names a file, or the file is
// absent, the band draws nothing and the status entry is cleared.
import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Progress } from '../types'

const MANIFEST = 'Virtuoso/workspace-layout.json'
const PERIOD_MS = 30_000
const BAR = 20

const progress = atom({ plugin: 'virtuoso', key: 'progress' } as const, null)
const progressError = atom({ plugin: 'virtuoso', key: 'progressError' } as const, null)

function isAbsolute(p: string) {
  return /^([A-Za-z]:[\\/]|[\\/])/.test(p)
}

function joinPath(dir: string, rel: string) {
  return dir.replace(/[\\/]+$/, '') + '/' + rel.replace(/^\.?[\\/]/, '')
}

function rolePath(manifestText: string): string | null {
  const m = JSON.parse(manifestText)
  const path = m && m.roles && m.roles.progress && m.roles.progress.path
  return typeof path === 'string' && path.trim() ? path.trim() : null
}

function parse(text: string): Progress {
  const p = JSON.parse(text) as Progress
  if (!p || !Array.isArray(p.items)) throw new Error('no "items" array')
  return p
}

function summarize(p: Progress, now: number) {
  const total = p.items.length
  const done = p.items.filter(i => i.state === 'done').length
  const pct = total === 0 ? 0 : Math.round((done / total) * 100)
  const filled = total === 0 ? 0 : Math.round((done / total) * BAR)
  const bar = '█'.repeat(filled) + '░'.repeat(BAR - filled)
  const next = p.items.find(i => i.state !== 'done' && i.state !== 'active')
  const deadlineMs = p.deadline ? Date.parse(p.deadline + 'T00:00:00Z') : NaN
  const days = Number.isNaN(deadlineMs) ? null : Math.ceil((deadlineMs - now) / 86_400_000)
  return { total, done, pct, bar, next, days }
}

function statusText(p: Progress, now: number) {
  const s = summarize(p, now)
  return `${p.title || 'Build'} ${s.done}/${s.total} (${s.pct}%)`
}

export const register: Register = (on, options) => {
  const configured = typeof options.progressFile === 'string' && options.progressFile.trim()
    ? options.progressFile.trim()
    : null
  // '' until resolved; a path once the option or the registry names one.
  let source = ''
  let lastText: string | null = null

  on('session.start', async ($, e, next) => {
    const result = await next(e)
    lastText = null

    const refresh = async () => {
      try {
        const cwd = await $.session.cwd()
        let named = configured
        if (named === null) {
          const manifest = joinPath(cwd, MANIFEST)
          named = (await $.fs.exists(manifest)) ? rolePath(await $.fs.read(manifest)) : null
        }
        source = named === null ? '' : isAbsolute(named) ? named : joinPath(cwd, named)
        if (source === '' || !(await $.fs.exists(source))) {
          if (lastText !== '') {
            lastText = ''
            await update($, progress, () => null)
            await update($, progressError, () => null)
            $.ui.status(undefined)
          }
          return
        }
        const text = await $.fs.read(source)
        if (text === lastText) return
        lastText = text
        const parsed = parse(text)
        await update($, progress, () => parsed)
        await update($, progressError, () => null)
        $.ui.status(statusText(parsed, await $.clock.now()))
      } catch (err) {
        await update($, progressError, () => String(err))
      }
    }

    await refresh()
    $.clock.every(PERIOD_MS, () => refresh())
    return result
  })

  on('turn.complete', async ($, e, next) => {
    try {
      if (source === '' || !(await $.fs.exists(source))) {
        if (lastText !== '') {
          lastText = ''
          await update($, progress, () => null)
          await update($, progressError, () => null)
          $.ui.status(undefined)
        }
      } else {
        const text = await $.fs.read(source)
        if (text !== lastText) {
          lastText = text
          const parsed = parse(text)
          await update($, progress, () => parsed)
          await update($, progressError, () => null)
          $.ui.status(statusText(parsed, await $.clock.now()))
        }
      }
    } catch (err) {
      await update($, progressError, () => String(err))
    }
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const p = await read($, progress)
    const err = await read($, progressError)
    const { Box, Text } = $.ui.resolve(e)

    if (p === null) {
      if (err === null) return next(e)
      return (
        <Box>
          <Text dimColor>{`Virtuoso progress: cannot read ${source || MANIFEST} (${err})`}</Text>
        </Box>
      )
    }

    const s = summarize(p, await $.clock.now())
    const active = p.items.filter(i => i.state === 'active').map(i => i.label).join(', ')
    const tail = [
      s.next ? `Next: ${s.next.label}` : '',
      p.updated ? `updated ${p.updated}` : '',
    ].filter(Boolean).map(t => `  ·  ${t}`).join('')

    return (
      <Box flexDirection="column">
        <Text>
          <Text bold>{`${p.title || 'Build'} `}</Text>
          <Text color="green">{s.bar}</Text>
          <Text bold>{` ${s.done}/${s.total} (${s.pct}%)`}</Text>
          {s.days !== null ? <Text dimColor>{`  ·  ${s.days} days to ${p.deadline}`}</Text> : null}
        </Text>
        <Text dimColor>{`Now: ${active || 'none'}${tail}`}</Text>
      </Box>
    )
  })
}

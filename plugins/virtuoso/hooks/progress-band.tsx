// Virtuoso progress band: the dispatch or epic this session is running, above the prompt
// (references/registry-contract.md, "The progress band").
//
//   Running  two lines: the current step, with a bar over the current milestone's steps,
//            and the current milestone, with a bar over the run's milestones, each ending
//            in its percent finished and an ETA measured from finished work.
//   Stale    no feed for 30 minutes: both lines dim, "no update since hh:mmZ" for the ETA.
//   Ended    one line from the archived run: "✓ COMPLETE · …" or "■ STOPPED · …", kept
//            until the session's next run starts or `progress --clear` removes it.
//   Hidden   no run has started in this session, or its end line was cleared.
//
// Everything is read from the user's own state folder, <VIRTUOSO_HOME or home>/.virtuoso/
// progress/, never from a project: sessions/<session id>.json names the session's run, and
// runs/<run>.json (or archive/<run>.json once it ended) holds it. Each session draws only
// its own run, so two sessions in one folder each see theirs. The band re-reads at session
// start, every 30 seconds and at the end of every turn. It never blocks: a file it cannot
// read draws one dim line naming the path and the error. The figures repeat
// tools/governance/progress.py, and a test holds the constants equal.
import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { ProgressItem, ProgressRun, ProgressView } from '../types'

const PERIOD_MS = 30_000
const BAR = 20
const MIN_BAR = 10
const STALE_FEED_MINUTES = 30
const PALETTE: [string, string][] = [['cyan', 'blue'], ['magenta', 'red'], ['green', 'yellow'],
  ['yellow', 'magenta'], ['blue', 'cyan'], ['red', 'green']]

const progress = atom({ plugin: 'virtuoso', key: 'progress' } as const, null)
const progressError = atom({ plugin: 'virtuoso', key: 'progressError' } as const, null)

let errorPath = ''

const safe = (name: string) => name.replace(/[^\w.-]/g, '_')

function crc32(text: string) {
  let c = ~0
  for (const byte of new TextEncoder().encode(text)) {
    c ^= byte
    for (let k = 0; k < 8; k++) c = (c >>> 1) ^ (0xedb88320 & -(c & 1))
  }
  return (~c) >>> 0
}

function colorsOf(doc: ProgressRun): [string, string] {
  return doc.colors && doc.colors.length === 2 ? doc.colors
    : PALETTE[crc32(doc.run.id) % PALETTE.length]!
}

function stamp(text: string | undefined): number | null {
  if (!text) return null
  const ms = Date.parse(text)
  return Number.isNaN(ms) ? null : ms
}

const hhmm = (ms: number) => new Date(ms).toISOString().slice(11, 16) + 'Z'
const dayHhmm = (ms: number) => new Date(ms).toISOString().slice(0, 10) + ' ' + hhmm(ms)
/** "12:29Z" today (UTC), "11-20 18:05Z" on a later day. */
const when = (ms: number, now: number) => {
  const iso = new Date(ms).toISOString()
  return iso.slice(0, 10) === new Date(now).toISOString().slice(0, 10) ? hhmm(ms)
    : iso.slice(5, 10) + ' ' + hhmm(ms)
}

/** max(30 minutes, 2 × the median finished step); 30 minutes until two are finished. */
function staleAfter(steps: ProgressItem[]) {
  const durations: number[] = []
  for (const s of steps) {
    if (s.state !== 'done') continue
    const a = stamp(s.started), b = stamp(s.finished)
    if (a !== null && b !== null && b >= a) durations.push(b - a)
  }
  const floor = STALE_FEED_MINUTES * 60_000
  return durations.length < 2 ? floor : Math.max(floor, 2 * median(durations))
}

function median(values: number[]) {
  const s = [...values].sort((a, b) => a - b)
  const mid = Math.floor(s.length / 2)
  return s.length % 2 ? s[mid]! : (s[mid - 1]! + s[mid]!) / 2
}

/** now + remaining × the median finished duration; null until two items are finished. */
/** A cancelled step or milestone drops out of X/Y. */
const live = (items: ProgressItem[]) => items.filter(i => i.state !== 'cancelled')

/** A run's length: "12m", "3h12m", "2d4h". */
function took(ms: number) {
  const minutes = Math.max(0, Math.floor(ms / 60_000))
  const days = Math.floor(minutes / 1440), hours = Math.floor((minutes % 1440) / 60)
  const mins = minutes % 60
  if (days) return `${days}d${hours}h`
  return hours ? `${hours}h${String(mins).padStart(2, '0')}m` : `${mins}m`
}

function eta(all: ProgressItem[], now: number): number | null {
  const items = live(all)
  const durations: number[] = []
  for (const i of items) {
    if (i.state !== 'done') continue
    const a = stamp(i.started), b = stamp(i.finished)
    if (a !== null && b !== null && b >= a) durations.push(b - a)
  }
  if (durations.length < 2) return null
  return now + items.filter(i => i.state !== 'done').length * median(durations)
}

function bar(done: number, total: number, width = BAR) {
  const filled = total ? Math.round(done / total * width) : 0
  return '█'.repeat(filled) + '░'.repeat(width - filled)
}

const SHORTEN: [string, string][] = [[' complete;', ';'], ['milestone ETA', 'ETA'],
  ['dispatch ETA', 'ETA'], ['epic ETA', 'ETA'], ['took ', ''], ['finished ', ''],
  ['stopped ', ''], ['Milestone ', 'M'], ['Step ', 'S'], [' of M', ' M']]

type Row ={ done: number; total: number; counter: string; paren: string; name: string }

/** `<bar> <counter> (<% complete; ETA>) <name>`, both bars one width and the counters padded
 * to one width so the "(" lines up. Never wraps: the name is cut with "…" first, then both
 * bars shrink alike down to MIN_BAR; the counter, percent and ETA are never cut. */
function layout(rows: Row[], width: number | null): string[] {
  const counterWidth = Math.max(...rows.map(r => r.counter.length))
  // Still too wide at the narrowest bar: shorten the labels, never the values.
  for (const [from, to] of SHORTEN) {
    const longest = Math.max(...rows.map(r => r.paren.length))
    if (width === null || MIN_BAR + 1 + counterWidth + 1 + longest <= width) break
    rows = rows.map(r => ({ ...r, paren: r.paren.replace(from, to) }))
  }
  const parenWidth = Math.max(...rows.map(r => r.paren.length))
  const fixed = counterWidth + 1 + parenWidth
  let widthBar = BAR
  if (width !== null && widthBar + 1 + fixed > width) {
    widthBar = Math.max(MIN_BAR, width - 1 - fixed)
  }
  return rows.map(r => {
    const line = `${bar(r.done, r.total, widthBar)} ${r.counter.padEnd(counterWidth)} `
      + r.paren.padEnd(parenWidth)
    let name = r.name
    if (width !== null) {
      const room = width - line.length - 1
      name = name.length <= room ? name
        : room >= 2 ? name.slice(0, room - 1).trimEnd() + '…' : ''
    }
    return name ? `${line} ${name}` : line.trimEnd()
  })
}

const percent = (p: number) => `${String(p).padStart(3)}%`

function view(v: ProgressView, now: number, width: number | null = null) {
  const doc = v.doc
  const title = doc.run.title
  const milestones = live(doc.milestones || []), steps = live(doc.steps || [])
  const current = milestones.find(m => m.id === doc.current)
  const stepsDone = steps.filter(s => s.state === 'done').length
  const msDone = milestones.filter(m => m.state === 'done').length
  const status = `Step ${stepsDone}/${steps.length} · Milestone ${msDone}/${milestones.length}`
  const colors = colorsOf(doc)
  if (v.kind === 'ended' && doc.end) {
    const at = stamp(doc.end.at) ?? now
    const row: Row = doc.end.state === 'complete'
      ? { done: 1, total: 1, counter: '✓ COMPLETE', name: title,
          paren: `(Milestone ${msDone}/${milestones.length}; finished ${dayHhmm(at)}; `
            + `took ${took(at - (stamp(doc.started) ?? at))})` }
      : { done: msDone, total: milestones.length, counter: '■ STOPPED', name: title,
          paren: `(Step ${stepsDone}/${steps.length} of Milestone `
            + `${current ? milestones.indexOf(current) + 1 : msDone}/${milestones.length}; `
            + `stopped ${dayHhmm(at)}; ${doc.end.reason || 'stopped'})` }
    const end = layout([row], width)[0]!
    return { end, colors, status: undefined, stale: false, line1: '', line2: '' }
  }
  const updated = stamp(doc.updated) ?? now
  const stale = now - updated > staleAfter(steps)
  let tailStep: string, tailRun: string
  if (stale) {
    tailStep = tailRun = `no update since ${when(updated, now)}`
  } else {
    const se = eta(steps, now), re = eta(milestones, now)
    tailStep = `milestone ETA ${se === null ? '—' : when(se, now)}`
    tailRun = `${doc.run.kind === 'epic' ? 'epic' : 'dispatch'} ETA ${re === null ? '—' : when(re, now)}`
  }
  const active = steps.find(s => s.state === 'active') || steps.find(s => s.state !== 'done')
    || steps[steps.length - 1]
  const pct = (d: number, t: number) => (t ? Math.round(100 * d / t) : 0)
  const stepLabel = active ? active.label : current ? current.label : title
  const [line1, line2] = layout([
    { done: stepsDone, total: steps.length, counter: `Step ${stepsDone}/${steps.length}`,
      paren: `(${percent(pct(stepsDone, steps.length))} complete; ${tailStep})`, name: stepLabel },
    { done: msDone, total: milestones.length, counter: `Milestone ${msDone}/${milestones.length}`,
      paren: `(${percent(pct(msDone, milestones.length))} complete; ${tailRun})`,
      name: current ? current.label : title },
  ], width)
  return { end: '', colors, status, stale, line1: line1!, line2: line2! }
}

async function readJson($: any, path: string): Promise<any> {
  errorPath = path
  if (!(await $.fs.exists(path))) return undefined
  return JSON.parse(await $.fs.read(path))
}

async function refresh($: any) {
  try {
    const home = (await $.env.get('VIRTUOSO_HOME')) || (await $.env.get('HOME'))
      || (await $.env.get('USERPROFILE')) || ''
    const store = home.replace(/[\\/]+$/, '') + '/.virtuoso/progress'
    const pointer = await readJson($, `${store}/sessions/${safe(await $.session.id())}.json`)
    let next: ProgressView | null = null
    if (pointer && typeof pointer === 'object' && !pointer.cleared && pointer.run) {
      const running = await readJson($, `${store}/runs/${safe(pointer.run)}.json`)
      if (running !== undefined) {
        next = { kind: 'running', doc: running }
      } else {
        const ended = await readJson($, `${store}/archive/${safe(pointer.run)}.json`)
        if (ended !== undefined) next = { kind: 'ended', doc: ended }
      }
      if (next && !(next.doc && next.doc.run && Array.isArray(next.doc.milestones))) {
        throw new Error('not a progress run')
      }
    }
    await update($, progress, () => next)
    await update($, progressError, () => null)
    $.ui.status(next ? view(next, await $.clock.now()).status : undefined)
  } catch (err) {
    await update($, progress, () => null)
    await update($, progressError, () => String(err))
    $.ui.status(undefined)
  }
}

export const register: Register = (on) => {
  on('session.start', async ($, e, next) => {
    const result = await next(e)
    await refresh($)
    $.clock.every(PERIOD_MS, () => refresh($))
    return result
  })

  on('turn.complete', async ($, e, next) => {
    await refresh($)
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const v = await read($, progress)
    const err = await read($, progressError)
    const { Box, Text } = $.ui.resolve(e)

    if (v === null) {
      if (err === null) return next(e)
      return (
        <Box>
          <Text dimColor>{`Virtuoso progress: cannot read ${errorPath} (${err})`}</Text>
        </Box>
      )
    }

    // Fit the body width at every render, so a resize re-fits the lines.
    const columns = typeof e.props.bodyColumns === 'number' ? e.props.bodyColumns : null
    const s = view(v, await $.clock.now(), columns)
    if (s.end) {
      return (
        <Box>
          <Text color={s.colors[0]}>{s.end}</Text>
        </Box>
      )
    }
    return (
      <Box flexDirection="column">
        <Text color={s.colors[0]} dimColor={s.stale}>{s.line1}</Text>
        <Text color={s.colors[1]} dimColor={s.stale}>{s.line2}</Text>
      </Box>
    )
  })
}

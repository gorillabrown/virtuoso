import { expect, test } from 'claude-code/testing'

const BAND = {
  plugin: 'virtuoso',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isCollapsed: false,
    isWorking: false,
    maxRows: 4,
    bodyColumns: 100,
    scroll: { offset: 0, bodyRows: 4 },
    view: {},
  },
} as const

const NOW = '2026-11-12T12:14:00Z'
const STORE = 'C:/Users/u/.virtuoso/progress'

function aRun(id: string, title: string, updated = '2026-11-12T12:08:00Z', colors?: [string, string]) {
  return {
    schema: 3, run: { id, title }, root: 'C:/proj', started: '2026-11-12T12:00:00Z', updated,
    ...(colors ? { colors } : {}),
    current: 'M1',
    milestones: [
      { id: 'M1', label: 'Core', state: 'active', started: '2026-11-12T12:00:00Z' },
      { id: 'M2', label: 'Proof', state: 'queued' },
    ],
    steps: [
      { id: '1', label: 'Write the parser', state: 'done', started: '2026-11-12T12:00:00Z', finished: '2026-11-12T12:04:00Z' },
      { id: '2', label: 'Wire the CLI', state: 'done', started: '2026-11-12T12:04:00Z', finished: '2026-11-12T12:08:00Z' },
      { id: '3', label: 'Check the CLI', state: 'active', started: '2026-11-12T12:08:00Z' },
      { id: '4', label: 'Document it', state: 'queued' },
    ],
  }
}

const LINE1 = '██████████░░░░░░░░░░ Step 2/4      ( 50% complete; milestone ETA 12:22Z) Check the CLI'
const LINE2 = '░░░░░░░░░░░░░░░░░░░░ Milestone 0/2 (  0% complete; dispatch ETA —)       Core'

const pointer = (run: string, extra = {}) => JSON.stringify({ run, at: '2026-11-12T12:00:00Z', ...extra })

function engine(on: any, files: Record<string, string>, statuses: unknown[], session = 's-1') {
  const norm = (p: string) => p.replace(/\\/g, '/')
  on('env.get', (_: unknown, e: any) => ({ value: e.name === 'HOME' ? 'C:/Users/u' : undefined }))
  on('session.cwd', () => ({ value: 'C:/proj' }))
  on('session.id', () => ({ value: session }))
  on('fs.exists', (_: unknown, e: any) => ({ value: norm(e.path) in files }))
  on('fs.read', (_: unknown, e: any) => ({ value: files[norm(e.path)] }))
  on('clock.now', () => ({ value: Date.parse(NOW) }))
  on('clock.every', () => ({ value: undefined }))
  on('ui.status', (_: unknown, e: any) => { statuses.push(e.text); return { value: undefined } })
  on('session.start', (_: unknown, e: any) => ({ cwd: e.cwd }))
  on('ui.render', ($: any, e: any) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
}

async function start($: any) {
  await $.session.start({ cwd: 'C:/proj', surface: 'desktop', isInteractive: true })
}

async function texts($: any) {
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  const found = (await ui.findAll({ type: 'Text' })).map((n: any) => n.text)
  await ui.unmount()
  return found.filter((t: string) => t !== 'engine') // the engine's own row, beneath the band
}

test('a running run draws both lines and the status entry', async ($, on) => {
  const statuses: unknown[] = []
  engine(on, {
    [`${STORE}/sessions/s-1.json`]: pointer('VIR-900'),
    [`${STORE}/runs/VIR-900.json`]: JSON.stringify(aRun('VIR-900', 'Sample')),
  }, statuses)
  await start($)
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...BAND, surface })
    expect((await ui.find({ type: 'Text', text: /Step 2\/4/ }))?.text).toBe(LINE1)
    expect((await ui.find({ type: 'Text', text: /Milestone 0\/2/ }))?.text).toBe(LINE2)
    await ui.unmount()
  }
  expect(statuses).toContain('Step 2/4 · Milestone 0/2')
})

test('two concurrent runs: each session draws only its own, in its own colours', async ($, on) => {
  const files = {
    [`${STORE}/sessions/s-1.json`]: pointer('VIR-900'),
    [`${STORE}/sessions/s-2.json`]: pointer('EPIC-7'),
    [`${STORE}/runs/VIR-900.json`]: JSON.stringify(aRun('VIR-900', 'Sample', undefined, ['cyan', 'blue'])),
    [`${STORE}/runs/EPIC-7.json`]: JSON.stringify({ ...aRun('EPIC-7', 'Importer', undefined, ['magenta', 'red']),
      run: { id: 'EPIC-7', title: 'Importer', kind: 'epic' },
      steps: [{ id: '1.1', label: 'Map the layout', state: 'active', started: '2026-11-12T12:08:00Z' }] }),
  }
  engine(on, files, [], 's-2')
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  const line = await ui.find({ type: 'Text', text: /Map the layout/ })
  expect(line?.text).toBe('░░░░░░░░░░░░░░░░░░░░ Step 0/1      (  0% complete; milestone ETA —) Map the layout')
  expect(line?.props?.color).toBe('magenta')
  const second = await ui.find({ type: 'Text', text: /Milestone 0\/2/ })
  expect(second?.text).toBe('░░░░░░░░░░░░░░░░░░░░ Milestone 0/2 (  0% complete; epic ETA —)      Core')
  expect(second?.props?.color).toBe('red')
  expect(await ui.find({ type: 'Text', text: /Check the CLI/ })).toBeFalsy()
  await ui.unmount()
})

test('ETA is a dash until two items at that level are finished', async ($, on) => {
  const run = aRun('VIR-900', 'Sample')
  run.steps[1] = { id: '2', label: 'Wire the CLI', state: 'active', started: '2026-11-12T12:04:00Z' } as any
  run.steps[2] = { id: '3', label: 'Check the CLI', state: 'queued' } as any
  engine(on, {
    [`${STORE}/sessions/s-1.json`]: pointer('VIR-900'),
    [`${STORE}/runs/VIR-900.json`]: JSON.stringify(run),
  }, [])
  await start($)
  const found = await texts($)
  expect(found).toContain('█████░░░░░░░░░░░░░░░ Step 1/4      ( 25% complete; milestone ETA —) Wire the CLI')
})

const LONG = 'Wire the command line interface into the registry and its parser'

async function fitted($: any, on: any, columns: number) {
  const run = aRun('VIR-900', 'Sample')
  run.steps[2] = { ...run.steps[2]!, label: LONG } as any
  engine(on, {
    [`${STORE}/sessions/s-1.json`]: pointer('VIR-900'),
    [`${STORE}/runs/VIR-900.json`]: JSON.stringify(run),
  }, [])
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal', props: { ...BAND.props, bodyColumns: columns } })
  const found = (await ui.findAll({ type: 'Text' })).map((n: any) => n.text).filter((t: string) => t !== 'engine')
  await ui.unmount()
  return found
}

const nameColumn = (line: string, name: string) => line.lastIndexOf(name)

test('at 80 columns the name is cut first; the "(" and the names line up', async ($, on) => {
  const found = await fitted($, on, 80)
  expect(found).toEqual([
    '██████████░░░░░░░░░░ Step 2/4      ( 50% complete; milestone ETA 12:22Z) Wire t…',
    '░░░░░░░░░░░░░░░░░░░░ Milestone 0/2 (  0% complete; dispatch ETA —)       Core',
  ])
  expect(found.every((t: string) => t.length <= 80)).toBe(true)
  expect(found[0]!.indexOf('(')).toBe(found[1]!.indexOf('('))
  expect(nameColumn(found[0]!, 'Wire t…')).toBe(nameColumn(found[1]!, 'Core'))
})

test('at 120 columns the name is cut only as far as it must be', async ($, on) => {
  const found = await fitted($, on, 120)
  expect(found).toEqual([
    '██████████░░░░░░░░░░ Step 2/4      ( 50% complete; milestone ETA 12:22Z) Wire the command line interface into the regis…',
    '░░░░░░░░░░░░░░░░░░░░ Milestone 0/2 (  0% complete; dispatch ETA —)       Core',
  ])
  expect(found[0]!.length).toBe(120)
})

test('narrower, both bars shrink alike and the counter, percent and ETA stay whole', async ($, on) => {
  const found = await fitted($, on, 66)
  expect(found).toEqual([
    '███████░░░░░░░ Step 2/4      ( 50% complete; milestone ETA 12:22Z)',
    '░░░░░░░░░░░░░░ Milestone 0/2 (  0% complete; dispatch ETA —)',
  ])
  expect(found.every((t: string) => t.length <= 66)).toBe(true)
})

test('a run with no feed for 30 minutes is drawn dim, with when it last moved', async ($, on) => {
  engine(on, {
    [`${STORE}/sessions/s-1.json`]: pointer('VIR-900'),
    [`${STORE}/runs/VIR-900.json`]: JSON.stringify(aRun('VIR-900', 'Sample', '2026-11-12T11:40:00Z')),
  }, [])
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  const line = await ui.find({ type: 'Text', text: /Step 2\/4/ })
  expect(line?.text).toMatch(/\( 50% complete; no update since 11:40Z\) Check the CLI$/)
  expect(line?.props?.dimColor).toBe(true)
  expect((await ui.find({ type: 'Text', text: /Milestone 0\/2/ }))?.text).toMatch(/no update since 11:40Z\) Core$/)
  await ui.unmount()
})

test('a long step is not stale before twice the median step, and a later-day ETA has its date', async ($, on) => {
  const run = aRun('VIR-900', 'Sample', '2026-11-12T11:29:00Z')
  run.steps[0] = { ...run.steps[0]!, started: '2026-11-12T03:29:00Z', finished: '2026-11-12T07:29:00Z' }
  run.steps[1] = { ...run.steps[1]!, started: '2026-11-12T07:29:00Z', finished: '2026-11-12T11:29:00Z' }
  engine(on, {
    [`${STORE}/sessions/s-1.json`]: pointer('VIR-900'),
    [`${STORE}/runs/VIR-900.json`]: JSON.stringify(run),
  }, [])
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  const line = await ui.find({ type: 'Text', text: /Step 2\/4/ })
  // median 4h: not stale 45 minutes after the last feed; two left from 12:14Z is 20:14Z today
  expect(line?.props?.dimColor).toBe(false)
  expect(line?.text).toMatch(/milestone ETA 20:14Z\)/)
  await ui.unmount()
})

test('an ETA on a later UTC day carries its month and day', async ($, on) => {
  const run = aRun('VIR-900', 'Sample', '2026-11-12T12:10:00Z')
  run.steps[0] = { ...run.steps[0]!, started: '2026-11-11T00:00:00Z', finished: '2026-11-11T12:00:00Z' }
  run.steps[1] = { ...run.steps[1]!, started: '2026-11-11T12:00:00Z', finished: '2026-11-12T00:00:00Z' }
  engine(on, {
    [`${STORE}/sessions/s-1.json`]: pointer('VIR-900'),
    [`${STORE}/runs/VIR-900.json`]: JSON.stringify(run),
  }, [])
  await start($)
  // median 12h, two left from 12:14Z: 12:14Z the next day
  expect((await texts($))[0]).toMatch(/milestone ETA 11-13 12:14Z\)/)
})

test('COMPLETE: one line from the archived run', async ($, on) => {
  const done = aRun('VIR-900', 'Sample')
  done.milestones = done.milestones.map(m => ({ ...m, state: 'done' })) as any
  done.steps = done.steps.map(s => ({ ...s, state: 'done' })) as any
  const archived = { ...done, end: { state: 'complete', at: '2026-11-12T15:12:00Z', evidence: 'suite green' } }
  const statuses: unknown[] = []
  engine(on, {
    [`${STORE}/sessions/s-1.json`]: pointer('VIR-900'),
    [`${STORE}/archive/VIR-900.json`]: JSON.stringify(archived),
  }, statuses)
  await start($)
  expect(await texts($)).toEqual(['████████████████████ ✓ COMPLETE (Milestone 2/2; finished 2026-11-12 15:12Z; took 3h12m) Sample'])
  expect(statuses.filter(s => s !== undefined)).toEqual([])
})

test('STOPPED: any other end, with its reason', async ($, on) => {
  const archived = { ...aRun('VIR-900', 'Sample'), end: { state: 'stopped', at: '2026-11-12T12:30:00Z', reason: 'halted' } }
  engine(on, {
    [`${STORE}/sessions/s-1.json`]: pointer('VIR-900'),
    [`${STORE}/archive/VIR-900.json`]: JSON.stringify(archived),
  }, [])
  await start($)
  expect(await texts($)).toEqual(['░░░░░░░░░░░░░░░░░░░░ ■ STOPPED (Step 2/4 of Milestone 1/2; stopped 2026-11-12 12:30Z; halted) Sample'])
})

test('a cancelled step or milestone drops out of X/Y', async ($, on) => {
  const run = aRun('VIR-900', 'Sample')
  run.steps[3] = { ...run.steps[3]!, state: 'cancelled' }
  run.milestones[1] = { ...run.milestones[1]!, state: 'cancelled' }
  const statuses: unknown[] = []
  engine(on, {
    [`${STORE}/sessions/s-1.json`]: pointer('VIR-900'),
    [`${STORE}/runs/VIR-900.json`]: JSON.stringify(run),
  }, statuses)
  await start($)
  const [one, two] = await texts($)
  expect(one!.includes('Step 2/3      ( 67% complete;')).toBe(true)
  expect(two!.includes('Milestone 0/1 (  0% complete;')).toBe(true)
  expect(statuses[statuses.length - 1]).toEqual('Step 2/3 · Milestone 0/1')
})

test('hidden: no run in this session, a cleared end line, another session\'s run', async ($, on) => {
  const archived = { ...aRun('VIR-900', 'Sample'), end: { state: 'stopped', at: '2026-11-12T12:30:00Z', reason: 'halted' } }
  engine(on, {
    [`${STORE}/sessions/s-1.json`]: pointer('VIR-900', { cleared: '2026-11-12T12:40:00Z' }),
    [`${STORE}/sessions/s-2.json`]: pointer('VIR-901'),
    [`${STORE}/archive/VIR-900.json`]: JSON.stringify(archived),
    [`${STORE}/runs/VIR-901.json`]: JSON.stringify(aRun('VIR-901', 'Other')),
  }, [])
  await start($)
  expect(await texts($)).toEqual([])
})

test('hidden: nothing has run on this machine', async ($, on) => {
  engine(on, {}, [])
  await start($)
  expect(await texts($)).toEqual([])
})

test('an invalid file draws one dim line naming it', async ($, on) => {
  engine(on, {
    [`${STORE}/sessions/s-1.json`]: pointer('VIR-900'),
    [`${STORE}/runs/VIR-900.json`]: '{ nope',
  }, [])
  await start($)
  const found = await texts($)
  expect(found.length).toBe(1)
  expect(found[0]).toMatch(/^Virtuoso progress: cannot read C:\/Users\/u\/\.virtuoso\/progress\/runs\/VIR-900\.json \(/)
})

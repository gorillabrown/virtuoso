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

const FILE = JSON.stringify({
  title: 'Build queue',
  deadline: '2027-01-01',
  updated: '2026-11-12T22:42Z',
  items: [
    { id: 'a', label: 'a', state: 'done' },
    { id: 'b', label: 'economy batch', state: 'active' },
    { id: 'c', label: 'catalogue', state: 'building' },
    { id: 'd', label: 'd', state: 'queued' },
  ],
})
const REGISTRY = JSON.stringify({ roles: { progress: { path: 's/briefs/progress.json' } } })
const NO_ROLE = JSON.stringify({ roles: {} })

function engine(on: any, files: Record<string, string>, statuses: unknown[]) {
  const norm = (p: string) => p.replace(/\\/g, '/')
  on('session.cwd', () => ({ value: 'C:/proj' }))
  on('fs.exists', (_: unknown, e: any) => ({ value: norm(e.path) in files }))
  on('fs.read', (_: unknown, e: any) => ({ value: files[norm(e.path)] }))
  on('clock.now', () => ({ value: Date.parse('2026-11-12T12:00:00Z') }))
  on('clock.every', () => ({ value: undefined }))
  on('ui.status', (_: unknown, e: any) => { statuses.push(e.text); return { value: undefined } })
  on('session.start', (_: unknown, e: any) => ({ cwd: e.cwd }))
  on('ui.render', ($: any, e: any) => { const { Text } = $.ui.resolve(e); return <Text>engine</Text> })
}

async function start($: any) {
  await $.session.start({ cwd: 'C:/proj', surface: 'desktop', isInteractive: true })
}

test('band draws the file the registry progress role names', async ($, on) => {
  const statuses: unknown[] = []
  engine(on, {
    'C:/proj/Virtuoso/workspace-layout.json': REGISTRY,
    'C:/proj/s/briefs/progress.json': FILE,
  }, statuses)
  await start($)
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...BAND, surface })
    expect(await ui.find({ type: 'Text', text: /1\/4 \(25%\)/ })).toBeTruthy()
    expect(await ui.find({ type: 'Text', text: /Now: economy batch.*Next: catalogue.*updated 2026-11-12T22:42Z/ })).toBeTruthy()
    expect(await ui.find({ type: 'Text', text: /50 days to 2027-01-01/ })).toBeTruthy()
    await ui.unmount()
  }
  expect(statuses).toContain('Build queue 1/4 (25%)')
})

test('the progressFile option overrides the registry', { options: { progressFile: 'D:/elsewhere/p.json' } }, async ($, on) => {
  engine(on, {
    'C:/proj/Virtuoso/workspace-layout.json': NO_ROLE,
    'D:/elsewhere/p.json': FILE,
  }, [])
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /1\/4 \(25%\)/ })).toBeTruthy()
  await ui.unmount()
})

test('no progress role: no band, no conventional fallback', async ($, on) => {
  const statuses: unknown[] = []
  engine(on, {
    'C:/proj/Virtuoso/workspace-layout.json': NO_ROLE,
    'C:/proj/.virtuoso/progress.json': FILE,
  }, statuses)
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect((await ui.find({ type: 'Text', text: /engine/ }))?.text).toBe('engine')
  await ui.unmount()
  expect(statuses).not.toContain('Build queue 1/4 (25%)')
})

test('not a Virtuoso project: no band', async ($, on) => {
  engine(on, {}, [])
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect((await ui.find({ type: 'Text', text: /engine/ }))?.text).toBe('engine')
  await ui.unmount()
})

test('a bad file says so', async ($, on) => {
  engine(on, {
    'C:/proj/Virtuoso/workspace-layout.json': REGISTRY,
    'C:/proj/s/briefs/progress.json': '{ nope',
  }, [])
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /cannot read .*progress\.json/ })).toBeTruthy()
  await ui.unmount()
})

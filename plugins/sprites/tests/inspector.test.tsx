import { expect, mock, test } from 'claude-code/testing'
import type { McpToolResult } from 'claude-code'

const SPRITES = [
  {
    id: 'spr_1',
    name: 'mcp-web',
    organization: 'acme',
    org_id: 'org_1',
    status: 'running',
    url: 'https://mcp-web-abc.sprites.app',
    version: '1.2.3',
    resource: { uri: 'sprites://org/org_1/mcp-web?id=spr_1' },
  },
  {
    id: 'spr_2',
    name: 'mcp-db',
    organization: 'acme',
    org_id: 'org_1',
    status: 'cold',
    url: '',
    version: '',
    resource: { uri: 'sprites://org/org_1/mcp-db?id=spr_2' },
  },
]

// Extension tools answer with structuredContent; generated runtime tools with JSON text alone.
function result(data: unknown, structured = true): McpToolResult {
  return {
    content: [{ type: 'text', text: JSON.stringify(data) }],
    isError: false,
    ...(structured ? { structuredContent: data } : {}),
  }
}

const PANE = {
  plugin: 'sprites',
  component: 'Pane',
  requestId: 'sprites-inspector',
  props: {
    title: 'Sprites',
    isFocused: true,
    bodyColumns: 48,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
} as const

for (const [surface, bodyColumns] of [['terminal', 48], ['desktop', 48], ['terminal', 120], ['desktop', 120]] as const) {
  test(`browses, selects, and loads runtime on ${surface} at ${bodyColumns} columns`, async ($, on) => {
    const clock = mock.clock(on)
    const calls: { tool: string; args: Record<string, unknown> }[] = []
    let dbStatus = 'cold'

    on('mcp.connect', () => ({ value: { isConnected: true, server: 'plugin:sprites:sprites' } }))
    on('mcp.call', (_$, e) => {
      calls.push({ tool: e.tool, args: e.args })
      switch (e.tool) {
        case 'open_sprite_inspector':
          return {
            value: result({
              sprites: SPRITES.map(one => (one.id === 'spr_2' ? { ...one, status: dbStatus } : one)),
              prefix: e.args.prefix,
              next_continuation_token: null,
              selected: null,
            }),
          }
        case 'get_sprite_info':
          // As the server does today: a Sprite the listing calls running reads cold here.
          return { value: result({ ...SPRITES[0], status: 'cold' }) }
        case 'service_list':
          return { value: result([{ name: 'web', state: { status: 'running' } }], false) }
        case 'checkpoint_list':
          return { value: result([{ id: 'v3', comment: 'before migrate', create_time: '2026-10-01T12:00:00Z' }], false) }
        case 'service_logs':
          return {
            value: {
              content: [{ type: 'text', text: '{"type":"stdout","data":"listening on :8080\\n"}\n' }],
              isError: false,
            },
          }
      }
      return { value: { content: [{ type: 'text', text: `unexpected ${e.tool}` }], isError: true } }
    })

    const ui = await $.ui.mount({ ...PANE, props: { ...PANE.props, bodyColumns }, surface })
    expect(await ui.find({ text: /Press Find/ })).toBeDefined()

    await ui.input({ key: 'prefix', text: 'mcp-' })
    await clock.settle()
    expect(calls[0]).toEqual({ tool: 'open_sprite_inspector', args: { prefix: 'mcp-', continuation_token: '' } })
    expect(await ui.find({ text: /^Sprites$/ })).toBeDefined()
    expect(await ui.find({ text: /^2 · as of / })).toBeDefined()

    await ui.press({ key: 'sprite-spr_1' })
    await clock.settle()
    expect(calls[1]).toEqual({ tool: 'get_sprite_info', args: { sprite: 'mcp-web', sprite_id: 'spr_1' } })
    expect((await ui.find({ key: 'attach' }))?.props.label).toBe('Use in chat')
    expect(await ui.find({ text: /● running/ })).toBeDefined()
    // Only mcp-db, which the listing itself calls cold.
    expect(await ui.findAll({ type: 'Text', text: /^cold$/ })).toHaveLength(1)

    // The kit has no conversation to append to, so this exercises the refusal
    // path; the append itself is checked in a live session.
    await ui.press({ key: 'attach' })
    await clock.settle()
    expect(await ui.find({ text: /Could not attach the Sprite/ })).toBeDefined()
    expect((await ui.find({ key: 'attach' }))?.props.label).toBe('Use in chat')

    await ui.press({ key: 'runtime' })
    await clock.settle()
    expect(await ui.find({ text: /before migrate/ })).toBeDefined()
    expect(await ui.find({ key: 'logs-web' })).toBeDefined()

    await ui.press({ key: 'logs-web' })
    await clock.settle()
    expect(calls.at(-1)?.args).toMatchObject({ service_name: 'web', lines: 100, sprite_id: 'spr_1' })
    expect(await ui.find({ text: /listening on :8080/ })).toBeDefined()

    // Focus coming back lists again, quietly: the selection and logs stay.
    const props = { ...PANE.props, bodyColumns }
    const listings = () => calls.filter(one => one.tool === 'open_sprite_inspector').length
    dbStatus = 'warm'
    await ui.redraw({ ...props, isFocused: false })
    await ui.redraw({ ...props, isFocused: true })
    await clock.settle()
    expect(listings()).toBe(1) // within the gap since the last listing

    await clock.advance(11_000)
    await ui.redraw({ ...props, isFocused: false })
    await ui.redraw({ ...props, isFocused: true })
    await clock.settle()
    expect(listings()).toBe(2)
    expect(calls.at(-1)?.args).toEqual({ prefix: 'mcp-', continuation_token: '' })
    expect(await ui.find({ type: 'Text', text: /^warm$/ })).toBeDefined()
    expect(await ui.find({ key: 'attach' })).toBeDefined()
    expect(await ui.find({ text: /listening on :8080/ })).toBeDefined()

    await ui.redraw({ ...props, isFocused: true })
    await clock.settle()
    expect(listings()).toBe(2) // still focused: no change, no listing

    await ui.unmount()
  })
}

test('says how to sign in when the server needs auth', async ($, on) => {
  const clock = mock.clock(on)
  on('mcp.connect', () => ({ value: { isConnected: false, reason: 'auth', message: 'needs sign-in' } }))

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.input({ key: 'prefix', text: '' })
  await clock.settle()
  expect(await ui.find({ text: /Authenticate it in \/mcp/ })).toBeDefined()
  await ui.unmount()
})

for (const surface of ['terminal', 'desktop'] as const) {
  test(`refresh resets pagination when Sprites move between pages on ${surface}`, async ($, on) => {
    const clock = mock.clock(on)
    const sprite = (i: number) => ({ ...SPRITES[0], id: `spr_${i}`, name: `mcp-${i}` })
    let sprites = Array.from({ length: 40 }, (_, i) => sprite(i + 1))
    on('mcp.connect', () => ({ value: { isConnected: true, server: 'plugin:sprites:sprites' } }))
    on('mcp.call', (_$, e) => {
      const offset = Number(e.args.continuation_token || 0)
      return {
        value: result({
          sprites: sprites.slice(offset, offset + 20),
          prefix: e.args.prefix,
          next_continuation_token: offset + 20 < sprites.length ? String(offset + 20) : null,
        }),
      }
    })

    const ui = await $.ui.mount({ ...PANE, surface })
    await ui.input({ key: 'prefix', text: 'mcp-' })
    await clock.settle()
    await ui.press({ key: 'more' })
    await clock.settle()
    expect(await ui.find({ key: 'sprite-spr_20' })).toBeDefined()
    expect(await ui.find({ key: 'sprite-spr_40' })).toBeDefined()
    expect(await ui.find({ key: 'more' })).toBeUndefined()

    // Inserting ahead of the first page pushes Sprite 20 onto the second.
    sprites = [sprite(0), ...sprites]
    await clock.advance(11_000)
    await ui.redraw({ ...PANE.props, isFocused: false })
    await ui.redraw({ ...PANE.props, isFocused: true })
    await clock.settle()
    expect(await ui.find({ key: 'sprite-spr_0' })).toBeDefined()
    expect(await ui.find({ key: 'more' })).toBeDefined()
    await ui.press({ key: 'more' })
    await clock.settle()
    expect(await ui.find({ key: 'sprite-spr_20' })).toBeDefined()
    await ui.press({ key: 'more' })
    await clock.settle()
    for (const one of sprites) expect(await ui.find({ key: `sprite-${one.id}` })).toBeDefined()
    expect(await ui.findAll({ type: 'Button', text: /^mcp-/ })).toHaveLength(41)
    expect(await ui.find({ key: 'more' })).toBeUndefined()
    await ui.unmount()
  })

  test(`failed filter change clears the previous rows and cursor on ${surface}`, async ($, on) => {
    const clock = mock.clock(on)
    const calls: Record<string, unknown>[] = []
    let fail = true
    on('mcp.connect', () => ({ value: { isConnected: true, server: 'plugin:sprites:sprites' } }))
    on('mcp.call', (_$, e) => {
      calls.push(e.args)
      if (e.args.prefix === 'other-' && fail) {
        return { value: { content: [{ type: 'text', text: 'Temporary server failure' }], isError: true } }
      }
      return {
        value: result({
          sprites: e.args.prefix === 'other-' ? [{ ...SPRITES[1], name: 'other-db' }] : [SPRITES[0]],
          prefix: e.args.prefix,
          next_continuation_token: e.args.prefix === 'other-' ? null : '20',
        }),
      }
    })

    const ui = await $.ui.mount({ ...PANE, surface })
    await ui.input({ key: 'prefix', text: 'mcp-' })
    await clock.settle()
    expect(await ui.find({ key: 'more' })).toBeDefined()
    await ui.input({ key: 'prefix', text: 'other-' })
    await clock.settle()
    expect(await ui.find({ text: /Temporary server failure/ })).toBeDefined()
    expect(await ui.find({ key: 'more' })).toBeUndefined()
    expect(await ui.find({ key: 'sprite-spr_1' })).toBeUndefined()

    fail = false
    await ui.input({ key: 'prefix', text: 'other-' })
    await clock.settle()
    expect(calls.at(-1)).toEqual({ prefix: 'other-', continuation_token: '' })
    expect(await ui.find({ key: 'sprite-spr_2' })).toBeDefined()
    expect(await ui.find({ key: 'sprite-spr_1' })).toBeUndefined()
    await ui.unmount()
  })
}

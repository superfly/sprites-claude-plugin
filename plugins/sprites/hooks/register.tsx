import { atom, read, update } from 'claude-code'
import type { EngineInterface, McpToolResult, Register } from 'claude-code'

import type { CheckpointRow, InspectorState, Section, ServiceRow, SpriteSummary } from '../types'

// A read-only Sprite Inspector: the Claude Code counterpart of the MCP App the
// hosted server serves at ui://sprites/inspector.html. It calls the same tools
// over the session's own connection, so it needs no credentials of its own.

const PANE = 'sprites-inspector'
const COMMAND = 'sprites-inspector'
const SERVER = 'sprites'
const LOG_LINES = 100
const LOG_CHARS = 10000
// The server's page size for open_sprite_inspector.
const PAGE_SIZE = 20
// Focus that returns sooner than this after a listing does not list again.
const REFRESH_GAP_MS = 10_000

// From this many columns the list and the details sit side by side.
const WIDE_COLUMNS = 64
const LIST_COLUMNS = 30
const LABEL_COLUMNS = 8

// Theme keys, so the colors follow the person's light or dark theme.
const STATUS_COLORS: Record<string, string> = { running: 'success', warm: 'warning', cold: 'inactive' }

const section = <T,>(state: Section<T>['state'], items: T[] = [], message = ''): Section<T> => ({ state, items, message })
const idle = <T,>(): Section<T> => section<T>('idle')

const CLEARED = {
  selected: null,
  isChecking: false,
  services: idle<ServiceRow>(),
  checkpoints: idle<CheckpointRow>(),
  logs: null,
} satisfies Partial<InspectorState>

const inspector = atom({ plugin: 'sprites', key: 'inspector' } as const, {
  status: '',
  statusTone: 'info',
  prefix: '',
  sprites: [],
  cursor: null,
  listedAt: null,
  isListing: false,
  attachedId: null,
  ...CLEARED,
} as InspectorState)

// Each counter discards answers that arrive after a newer request of its kind.
let listRun = 0
let selectRun = 0
let runtimeRun = 0
let logsRun = 0
let server: string | undefined
// The pane's focus as the latest drawing saw it, to notice it coming back.
let wasFocused = false

async function connection($: EngineInterface): Promise<string> {
  if (server) return server
  const connected = await $.mcp.connect(SERVER)
  if (!connected.isConnected) {
    throw new Error(
      connected.reason === 'auth'
        ? 'The Sprites MCP server needs sign-in. Authenticate it in /mcp, then press Find again.'
        : connected.message,
    )
  }
  server = connected.server
  return server
}

async function call($: EngineInterface, tool: string, args: Record<string, unknown>): Promise<McpToolResult> {
  let result: McpToolResult
  try {
    result = await $.mcp.call(await connection($), tool, args)
  } catch (error) {
    server = undefined
    throw error
  }
  if (result.isError) throw new Error(textOf(result) || `${tool} failed.`)
  return result
}

function textOf(result: McpToolResult): string {
  return result.content
    .filter(block => block.type === 'text')
    .map(block => block.text ?? '')
    .join('\n')
}

// Extension tools return structuredContent; the generated runtime tools return JSON as text.
function dataOf(result: McpToolResult): unknown {
  return result.structuredContent ?? JSON.parse(textOf(result))
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

const info = (status: string) => ({ status, statusTone: 'info' as const })
const failure = (error: unknown) => ({ status: errorText(error), statusTone: 'error' as const })

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function str(value: unknown): string {
  return typeof value === 'string' ? value : typeof value === 'number' ? String(value) : ''
}

// A bare array, or an object holding one under `key`.
function listOf(value: unknown, key: string, what: string): unknown[] {
  const list = Array.isArray(value) ? value : record(value)[key]
  if (!Array.isArray(list)) throw new Error(`Invalid ${what} response.`)
  return list
}

function summary(value: unknown): SpriteSummary | null {
  const v = record(value)
  if (!str(v.id) || !str(v.name)) return null
  return {
    id: str(v.id),
    name: str(v.name),
    organization: str(v.organization),
    orgId: str(v.org_id),
    url: str(v.url),
    status: str(v.status),
    version: str(v.version),
    created: str(v.created_at),
    uri: str(record(v.resource).uri),
  }
}

function safeUrl(value: string): string | null {
  try {
    const url = new URL(value)
    return url.protocol === 'https:' && !url.username && !url.password ? url.href : null
  } catch {
    return null
  }
}

// Logs can carry terminal escapes; Code and Text take tab and newline as their only control characters.
function printable(text: string): string {
  return text.replace(/\x1b\[[0-9;?]*[ -/]*[@-~]/g, '').replace(/[\x00-\x08\x0b-\x1f\x7f]/g, '')
}

const day = (iso: string) => iso.slice(0, 10)

function timeOfDay(ms: number): string {
  try {
    return new Date(ms).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return new Date(ms).toISOString().slice(11, 16)
  }
}
const statusColor = (status: string) => STATUS_COLORS[status] ?? 'warning'

async function loadPage($: EngineInterface, append: boolean, nextPrefix?: string): Promise<void> {
  const run = ++listRun
  const before = await read($, inspector)
  const prefix = append ? before.prefix : (nextPrefix ?? before.prefix).trim()
  if (!append) {
    ++selectRun
    ++runtimeRun
    ++logsRun
  }
  await update($, inspector, s => ({
    ...s,
    ...(append ? {} : { ...CLEARED, prefix }),
    ...info(''),
    isListing: true,
  }))
  try {
    const page = record(
      dataOf(await call($, 'open_sprite_inspector', { prefix, continuation_token: append ? (before.cursor ?? '') : '' })),
    )
    const incoming = listOf(page, 'sprites', 'Sprite listing')
      .map(summary)
      .filter((one): one is SpriteSummary => one !== null)
    const listedAt = await $.clock.now()
    if (run !== listRun) return
    await update($, inspector, s => {
      const sprites = append ? [...s.sprites, ...incoming.filter(one => !s.sprites.some(old => old.id === one.id))] : incoming
      return {
        ...s,
        ...info(sprites.length ? '' : 'No matching Sprites.'),
        sprites,
        cursor: str(page.next_continuation_token) || null,
        listedAt,
        prefix: typeof page.prefix === 'string' ? page.prefix : s.prefix,
        isListing: false,
      }
    })
  } catch (error) {
    if (run === listRun) await update($, inspector, s => ({ ...s, ...failure(error), isListing: false }))
  }
}

// The quiet re-list the pane runs when it regains focus: it changes only what
// the listing says now, and keeps the selection, runtime details and logs.
async function refresh($: EngineInterface): Promise<void> {
  const before = await read($, inspector)
  if (before.isListing || before.listedAt === null) return
  if ((await $.clock.now()) - before.listedAt < REFRESH_GAP_MS) return
  const run = ++listRun
  try {
    const page = record(dataOf(await call($, 'open_sprite_inspector', { prefix: before.prefix, continuation_token: '' })))
    const fresh = listOf(page, 'sprites', 'Sprite listing')
      .map(summary)
      .filter((one): one is SpriteSummary => one !== null)
    const listedAt = await $.clock.now()
    if (run !== listRun) return
    const byId = new Map(fresh.map(one => [one.id, one]))
    await update($, inspector, s => {
      // Rows from pages after the first stay as they were.
      const isOnePage = s.sprites.length <= PAGE_SIZE
      const rest = isOnePage ? [] : s.sprites.slice(PAGE_SIZE).filter(old => !byId.has(old.id))
      const listed = s.selected && byId.get(s.selected.id)
      return {
        ...s,
        ...(s.statusTone === 'error' ? info('') : {}),
        sprites: [...fresh, ...rest],
        cursor: isOnePage ? str(page.next_continuation_token) || null : s.cursor,
        listedAt,
        selected: s.selected && listed ? { ...s.selected, status: listed.status } : s.selected,
      }
    })
  } catch (error) {
    if (run === listRun) await update($, inspector, s => ({ ...s, ...failure(error) }))
  }
}

async function selectSprite($: EngineInterface, sprite: SpriteSummary): Promise<void> {
  const run = ++selectRun
  ++runtimeRun
  ++logsRun
  await update($, inspector, s => ({ ...s, ...CLEARED, ...info(''), selected: sprite, isChecking: true }))
  try {
    const checked = summary(dataOf(await call($, 'get_sprite_info', { sprite: sprite.name, sprite_id: sprite.id })))
    if (!checked) throw new Error('Invalid Sprite info response.')
    if (run !== selectRun) return
    // get_sprite_info's status can disagree with the listing's live runtime
    // state (a running Sprite reads cold), so the listing's status stands.
    const fresh = { ...checked, status: sprite.status || checked.status }
    await update($, inspector, s => ({
      ...s,
      selected: fresh,
      isChecking: false,
      sprites: s.sprites.map(one => (one.id === fresh.id ? fresh : one)),
    }))
  } catch (error) {
    if (run === selectRun) await update($, inspector, s => ({ ...s, ...CLEARED, ...failure(error) }))
  }
}

// The counterpart of the MCP App's ui/update-model-context: a row the model
// reads and the person does not see as typed. Rows add up rather than replace,
// so the newest attachment is the one that counts.
async function attach($: EngineInterface): Promise<void> {
  const { selected } = await read($, inspector)
  if (!selected) return
  const identity = {
    sprite: selected.name,
    sprite_id: selected.id,
    org_id: selected.orgId,
    organization: selected.organization,
    uri: selected.uri,
  }
  const text =
    `The user selected this Sprite in the Sprite Inspector pane: ${JSON.stringify(identity)}. ` +
    'Treat it as the target when they refer to "the Sprite" or "this Sprite". Verify the identity with get_sprite_info ' +
    'before operating on it, and pass sprite_id alongside sprite on Sprite-scoped tool calls.'
  let refused: string | undefined
  try {
    refused = (await $.session.append({ message: { type: 'user', content: [{ type: 'text', text }] } })).deny
  } catch (error) {
    refused = errorText(error)
  }
  await update($, inspector, s =>
    refused
      ? { ...s, ...failure(`Could not attach the Sprite: ${refused}`) }
      : { ...s, ...info(''), attachedId: selected.id },
  )
}

async function loadRuntime($: EngineInterface): Promise<void> {
  const { selected } = await read($, inspector)
  if (!selected) return
  const selection = selectRun
  const run = ++runtimeRun
  const current = () => selection === selectRun && run === runtimeRun
  await update($, inspector, s => ({ ...s, services: section<ServiceRow>('loading'), checkpoints: section<CheckpointRow>('loading') }))
  const args = { sprite: selected.name, sprite_id: selected.id }

  await Promise.all([
    (async () => {
      try {
        const items = listOf(dataOf(await call($, 'service_list', args)), 'services', 'services').map(one => {
          const v = record(one)
          return { name: str(v.name), status: str(record(v.state).status) || 'unknown' }
        })
        if (current()) await update($, inspector, s => ({ ...s, services: section('ready', items) }))
      } catch (error) {
        if (current()) await update($, inspector, s => ({ ...s, services: section('error', [], errorText(error)) }))
      }
    })(),
    (async () => {
      try {
        const items = listOf(dataOf(await call($, 'checkpoint_list', args)), 'checkpoints', 'checkpoints').map(one => {
          const v = record(one)
          return { id: str(v.id), comment: str(v.comment), created: str(v.create_time) }
        })
        if (current()) await update($, inspector, s => ({ ...s, checkpoints: section('ready', items) }))
      } catch (error) {
        if (current()) await update($, inspector, s => ({ ...s, checkpoints: section('error', [], errorText(error)) }))
      }
    })(),
  ])
}

async function loadLogs($: EngineInterface, service: string): Promise<void> {
  const { selected } = await read($, inspector)
  if (!selected) return
  const selection = selectRun
  const run = ++logsRun
  const current = () => selection === selectRun && run === logsRun
  await update($, inspector, s => ({ ...s, logs: { service, state: 'loading' as const, text: '' } }))
  try {
    const result = await call($, 'service_logs', {
      sprite: selected.name,
      sprite_id: selected.id,
      service_name: service,
      lines: LOG_LINES,
      duration: '0s',
    })
    // The endpoint streams NDJSON events; `data` carries the output itself.
    const text = printable(
      textOf(result)
        .split('\n')
        .filter(Boolean)
        .map(line => {
          try {
            const event = record(JSON.parse(line))
            return typeof event.data === 'string' ? event.data : event.type === 'error' ? `${JSON.stringify(event)}\n` : ''
          } catch {
            return `${line}\n`
          }
        })
        .join(''),
    )
      .replace(/\n+$/, '')
      .slice(-LOG_CHARS)
    if (current()) await update($, inspector, s => ({ ...s, logs: { service, state: 'ready' as const, text } }))
  } catch (error) {
    if (current()) await update($, inspector, s => ({ ...s, logs: { service, state: 'error' as const, text: errorText(error) } }))
  }
}

// MCP calls can outlast the dispatch that asked for them; a timer runs them on their own.
function later($: EngineInterface, work: () => Promise<void>): void {
  $.clock.after(0, () => void work())
}

function listing(s: InspectorState): string {
  if (!s.sprites.length) return s.status || 'No Sprites loaded.'
  const rows = s.sprites.map(one => `- ${one.name} · ${one.status || 'unknown'}${one.organization ? ` · ${one.organization}` : ''}`)
  return [`${s.sprites.length} Sprite${s.sprites.length === 1 ? '' : 's'}${s.cursor ? ' (more available)' : ''}`, ...rows].join('\n')
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: COMMAND,
      description: 'Browse your Sprites, their services, checkpoints, and logs in a read-only pane',
      argumentHint: '[name prefix]',
    })
    // State outlives a reload or resume, but the requests in flight did not.
    await update($, inspector, s => ({
      ...s,
      ...info(''),
      isListing: false,
      isChecking: false,
      services: s.services.state === 'loading' ? idle<ServiceRow>() : s.services,
      checkpoints: s.checkpoints.state === 'loading' ? idle<CheckpointRow>() : s.checkpoints,
      logs: s.logs?.state === 'loading' ? null : s.logs,
    }))
    return next(e)
  })

  on('command.run', { command: COMMAND }, async ($, e) => {
    const opened = await $.ui.open({ id: PANE, title: 'Sprites' })
    const before = await read($, inspector)
    const prefix = e.args.trim()

    // Where no pane can draw (the VS Code panel, claude -p), answer in text.
    if (!opened.isPlaced) {
      await loadPage($, false, prefix)
      return { text: listing(await read($, inspector)) }
    }
    // Opening always lists afresh: statuses change while the pane sits idle.
    if (!before.isListing || prefix) later($, () => loadPage($, false, prefix || undefined))
    return { text: 'Sprite Inspector opened.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button, Link, Code } = $.ui.resolve(e)
    const Input = e.surface === 'mobile' ? undefined : $.ui.resolve(e).Input
    // Coming back to the pane lists again; a drawing only schedules it, since it may not write.
    if (e.props.isFocused && !wasFocused) later($, () => refresh($))
    wasFocused = e.props.isFocused

    const s = await read($, inspector)
    const selected = s.selected
    const isWide = e.props.bodyColumns >= WIDE_COLUMNS
    const hasRuntime = s.services.state !== 'idle' || s.checkpoints.state !== 'idle'
    const isRuntimeLoading = s.services.state === 'loading' || s.checkpoints.state === 'loading'

    const field = (label: string, value: string) => (
      <Box flexDirection="row">
        <Box width={LABEL_COLUMNS} flexShrink={0}>
          <Text dimColor>{label}</Text>
        </Box>
        <Text wrap="truncate-middle">{value}</Text>
      </Box>
    )

    const heading = (title: string, detail?: string) => (
      <Box flexDirection="row" justifyContent="space-between">
        <Text bold>{title}</Text>
        {detail ? <Text dimColor>{detail}</Text> : null}
      </Box>
    )

    const search = (
      <Box flexDirection="column">
        {Input && (
          <Input
            key="prefix"
            placeholder="Filter by name prefix"
            value={s.prefix}
            submitLabel="Find"
            onSubmit={value => later($, () => loadPage($, false, value))}
          />
        )}
        {s.isListing && <Text dimColor>Loading Sprites…</Text>}
        {s.status && (
          <Text color={s.statusTone === 'error' ? 'error' : undefined} dimColor={s.statusTone !== 'error'} wrap="wrap">
            {s.status}
          </Text>
        )}
      </Box>
    )

    const list = (
      <Box flexDirection="column" width={isWide ? LIST_COLUMNS : undefined} flexShrink={0}>
        {s.sprites.length > 0 &&
          heading(
            'Sprites',
            `${s.sprites.length}${s.cursor ? '+' : ''}${s.listedAt !== null ? ` · as of ${timeOfDay(s.listedAt)}` : ''}`,
          )}
        {!s.sprites.length && !s.isListing && !s.status && (
          <Text dimColor>Press Find to list your Sprites, or filter by a name prefix.</Text>
        )}
        {s.sprites.map(one => {
          const isSelected = one.id === selected?.id
          return (
            <Box key={`row-${one.id}`} flexDirection="row" gap={1}>
              <Text color="claude">{isSelected ? '▌' : ' '}</Text>
              <Text color={statusColor(one.status)}>●</Text>
              <Box flexGrow={1} flexShrink={1}>
                {/* The selected row stays a Button: a focused element that leaves the
                    tree takes the pane's focus with it, and on desktop the next click
                    into an unfocused pane only focuses. */}
                <Button
                  key={`sprite-${one.id}`}
                  plain
                  label={one.name}
                  onPress={() => {
                    if (!isSelected) later($, () => selectSprite($, one))
                  }}
                />
              </Box>
              {one.id === s.attachedId && <Text color="suggestion">in chat</Text>}
              <Text dimColor>{one.status || 'unknown'}</Text>
            </Box>
          )
        })}
        {s.cursor && (
          <Box marginTop={1}>
            <Button key="more" label={s.isListing ? 'Loading…' : 'Load more'} onPress={() => later($, () => loadPage($, true))} />
          </Box>
        )}
      </Box>
    )

    const details = selected ? (
      <Box flexDirection="column" borderStyle="round" borderColor="claude" paddingX={1} gap={1}>
        <Box flexDirection="row" justifyContent="space-between" gap={1}>
          <Box flexShrink={1}>
            <Text bold wrap="truncate-end">
              {selected.name}
            </Text>
          </Box>
          <Box flexDirection="row" gap={1} flexShrink={0}>
            {selected.id === s.attachedId && <Text color="suggestion">in chat</Text>}
            <Text color={statusColor(selected.status)}>● {s.isChecking ? 'checking…' : selected.status || 'unknown'}</Text>
          </Box>
        </Box>

        <Box flexDirection="column">
          {selected.organization && field('Org', selected.organization)}
          {selected.created && field('Created', day(selected.created))}
          {safeUrl(selected.url) && (
            <Box flexDirection="row">
              <Box width={LABEL_COLUMNS} flexShrink={0}>
                <Text dimColor>URL</Text>
              </Box>
              <Link href={safeUrl(selected.url) ?? ''} label={selected.url.replace(/^https:\/\//, '').replace(/\/$/, '')} />
            </Box>
          )}
        </Box>

        {!s.isChecking && (
          <Box flexDirection="column">
            <Box flexDirection="row" flexWrap="wrap" columnGap={1}>
              <Button
                key="attach"
                variant={selected.id === s.attachedId ? 'secondary' : 'primary'}
                label={selected.id === s.attachedId ? 'In chat ✓' : 'Use in chat'}
                onPress={() => later($, () => attach($))}
              />
              <Button
                key="runtime"
                label={isRuntimeLoading ? 'Loading…' : hasRuntime ? 'Refresh runtime' : 'Load runtime'}
                onPress={() => later($, () => loadRuntime($))}
              />
            </Box>
            {!hasRuntime && selected.status !== 'running' && (
              <Text color="warning" wrap="wrap">
                Loading runtime wakes this {selected.status || 'idle'} Sprite.
              </Text>
            )}
          </Box>
        )}
      </Box>
    ) : isWide && s.sprites.length > 0 ? (
      <Text dimColor>Select a Sprite to see its details.</Text>
    ) : null

    const services = selected && hasRuntime && (
      <Box flexDirection="column">
        {heading('Services', s.services.state === 'ready' ? String(s.services.items.length) : undefined)}
        {s.services.state === 'loading' && <Text dimColor>Loading…</Text>}
        {s.services.state === 'error' && <Text color="error" wrap="wrap">{s.services.message}</Text>}
        {s.services.state === 'ready' && !s.services.items.length && <Text dimColor>No services configured.</Text>}
        {s.services.items.map(service => (
          <Box key={`svc-${service.name}`} flexDirection="row" gap={1}>
            <Text color={service.status === 'running' ? 'success' : service.status === 'stopped' ? 'inactive' : 'warning'}>●</Text>
            <Box flexGrow={1} flexShrink={1}>
              <Text wrap="truncate-end">{service.name}</Text>
            </Box>
            <Text dimColor>{service.status}</Text>
            <Button
              key={`logs-${service.name}`}
              label={s.logs?.service === service.name ? 'Logs ✓' : 'Logs'}
              onPress={() => later($, () => loadLogs($, service.name))}
            />
          </Box>
        ))}
      </Box>
    )

    const checkpoints = selected && hasRuntime && (
      <Box flexDirection="column">
        {heading('Checkpoints', s.checkpoints.state === 'ready' ? String(s.checkpoints.items.length) : undefined)}
        {s.checkpoints.state === 'loading' && <Text dimColor>Loading…</Text>}
        {s.checkpoints.state === 'error' && <Text color="error" wrap="wrap">{s.checkpoints.message}</Text>}
        {s.checkpoints.state === 'ready' && !s.checkpoints.items.length && <Text dimColor>No checkpoints.</Text>}
        {s.checkpoints.items.map(checkpoint => (
          <Box key={`cp-${checkpoint.id}`} flexDirection="row" gap={1}>
            <Box width={6} flexShrink={0}>
              <Text bold>{checkpoint.id}</Text>
            </Box>
            <Box flexGrow={1} flexShrink={1}>
              <Text wrap="truncate-end">{checkpoint.comment || 'No comment'}</Text>
            </Box>
            {checkpoint.created && <Text dimColor>{day(checkpoint.created)}</Text>}
          </Box>
        ))}
      </Box>
    )

    const logs = selected && s.logs && (
      <Box flexDirection="column">
        <Box flexDirection="row" justifyContent="space-between">
          <Text bold>
            Logs <Text dimColor>· {s.logs.service} · last {LOG_LINES} lines</Text>
          </Text>
          <Button
            key="hide-logs"
            plain
            label="Hide"
            onPress={() =>
              later($, async () => {
                // Hide leaves the tree with the logs; hand the ring to a Button that stays.
                await $.ui.focus({ requestId: PANE, key: 'runtime' })
                await update($, inspector, st => ({ ...st, logs: null }))
              })
            }
          />
        </Box>
        {s.logs.state === 'loading' && <Text dimColor>Loading…</Text>}
        {s.logs.state === 'error' && <Text color="error" wrap="wrap">{s.logs.text}</Text>}
        {s.logs.state === 'ready' && (s.logs.text ? <Code source={s.logs.text} /> : <Text dimColor>No recent logs.</Text>)}
      </Box>
    )

    const detailColumn = (
      <Box flexDirection="column" gap={1} flexGrow={1} flexShrink={1}>
        {details}
        {services}
        {checkpoints}
        {logs}
      </Box>
    )

    return (
      <Box flexDirection="column" gap={1}>
        {search}
        {isWide ? (
          <Box flexDirection="row" gap={2}>
            {list}
            {detailColumn}
          </Box>
        ) : (
          <Box flexDirection="column" gap={1}>
            {list}
            {detailColumn}
          </Box>
        )}
      </Box>
    )
  })
}

import { Fragment, useEffect, useState } from 'react'
import { api, errorText } from '../api'
import type { Shared } from '../App'
import type { MarketPoint, MarketStatus, Skill, SkillsResponse } from '../types'

const LEVELS = ['None', 'Learning', 'Working', 'Production']
type Scope = 'all' | 'open'
type Sort = 'demand' | 'gap'

/** Demand weighted by how far you are from production level: the skills worth your next hour. */
function gapScore(s: Skill, scope: Scope): number {
  return (scope === 'all' ? s.pct_all : s.pct_open) * ((3 - s.my_level) / 3)
}

const SOURCE_LABEL: Record<string, string> = {
  'career-ops': 'the career-ops market scan',
  boards: 'live job boards (Greenhouse, Lever, Ashby)',
}

function signed(n: number): string {
  return `${n > 0 ? '+' : n < 0 ? '−' : '±'}${Math.abs(n).toFixed(1)}`
}

/** Share of postings over time, from the snapshots of one source. */
function Trend({ points, scope }: { points: MarketPoint[]; scope: Scope }) {
  const values = points.map((p) => (scope === 'all' ? p.pct_all : p.pct_open)).filter((v): v is number => v != null)
  if (values.length < 2) return <p className="muted small">Not enough snapshots from this source yet to show a trend.</p>
  const w = 220, h = 48, max = Math.max(...values, 1)
  const xy = values.map((v, i) => `${(i / (values.length - 1)) * (w - 8) + 4},${h - 4 - (v / max) * (h - 8)}`)
  return (
    <svg className="trend" viewBox={`0 0 ${w} ${h}`} width={w} height={h} role="img"
         aria-label={`From ${values[0].toFixed(1)}% to ${values[values.length - 1].toFixed(1)}% over ${values.length} snapshots`}>
      <polyline points={xy.join(' ')} fill="none" stroke="var(--accent)" strokeWidth="2" />
      {xy.map((p, i) => <circle key={i} cx={p.split(',')[0]} cy={p.split(',')[1]} r="2.5" fill="var(--accent)" />)}
    </svg>
  )
}

export default function Market({ user, version, changed }: Shared) {
  const [data, setData] = useState<SkillsResponse | null>(null)
  const [error, setError] = useState('')
  const [status, setStatus] = useState<MarketStatus | null>(null)
  const [openSkill, setOpenSkill] = useState<string | null>(null)
  const [history, setHistory] = useState<MarketPoint[]>([])
  const [scope, setScope] = useState<Scope>('all')
  const [sort, setSort] = useState<Sort>('demand')
  const [roadmapOnly, setRoadmapOnly] = useState(true)

  useEffect(() => {
    api.get<SkillsResponse>('/skills').then((d) => { setData(d); setError('') }).catch((e) => setError(errorText(e)))
    if (user.is_admin) api.get<MarketStatus>('/market/status').then(setStatus).catch(() => setStatus(null))
  }, [version, user.is_admin])

  // While a refresh runs, check every 10 seconds and reload when it's done.
  useEffect(() => {
    if (!status?.running) return
    const t = setTimeout(() => {
      api.get<MarketStatus>('/market/status').then((s) => { setStatus(s); if (!s.running) changed() }).catch(() => {})
    }, 10_000)
    return () => clearTimeout(t)
  }, [status, changed])

  useEffect(() => {
    if (!openSkill || !data) return
    api.get<MarketPoint[]>(`/market/history?skill=${encodeURIComponent(openSkill)}`)
      .then((h) => setHistory(h.filter((p) => p.source === data.source)))
      .catch(() => setHistory([]))
  }, [openSkill, data])

  if (error) return <p className="banner error">{error}</p>
  if (!data) return <p className="muted">Loading…</p>
  if (!data.snapshot_date) return <section className="panel"><p className="empty">No market data yet.</p></section>

  const pct = (s: Skill) => (scope === 'all' ? s.pct_all : s.pct_open)
  const rows = data.skills
    .filter((s) => !roadmapOnly || s.units_total > 0 || s.my_level > 0)
    .sort((a, b) => (sort === 'demand' ? pct(b) - pct(a) : gapScore(b, scope) - gapScore(a, scope)))
  const max = Math.max(...rows.map(pct), 1)
  const topGaps = [...data.skills]
    .filter((s) => s.units_total > 0)
    .sort((a, b) => gapScore(b, scope) - gapScore(a, scope))
    .slice(0, 3)

  async function setLevel(name: string, my_level: number) {
    try {
      await api.patch(`/skills/${encodeURIComponent(name)}`, { my_level })
      changed()
    } catch (e) {
      setError(errorText(e))
    }
  }

  async function refresh() {
    try {
      await api.post('/market/refresh', {})
      setStatus(await api.get<MarketStatus>('/market/status'))
    } catch (e) {
      setError(errorText(e))
    }
  }

  const delta = (s: Skill) => (scope === 'all' ? s.delta_all : s.delta_open)

  return (
    <div className="stack">
      <section className="panel intro">
        <p>
          Share of engineering job postings that mention each skill, from {SOURCE_LABEL[data.source ?? ''] ?? data.source} on{' '}
          <strong>{data.snapshot_date}</strong>: {data.postings.toLocaleString()} postings
          {data.companies > 0 && <> at {data.companies} companies</>}, of which {data.open_postings.toLocaleString()} were
          remote with no country restriction. {data.previous_date
            ? <>Changes compare with the snapshot from {data.previous_date}.</>
            : <>Changes show once there's a second snapshot from the same source.</>}{' '}
          Rate yourself on each skill; the gap sort ranks high-demand skills you haven't reached production level in.
        </p>
        {user.is_admin && status && (
          <p className="refresh-line">
            {status.running
              ? <span className="muted small">Fetching job postings… this takes a minute or two.</span>
              : <button className="small-btn" onClick={refresh} disabled={!status.can_refresh}
                        title={status.can_refresh ? '' : 'Market data can be refreshed once a day.'}>Refresh market data now</button>}
            {status.last_refresh && <span className="muted small"> Last live refresh: {new Date(status.last_refresh).toLocaleString()}.</span>}
            {status.last_error && <span className="error-text small"> Last refresh failed: {status.last_error}</span>}
          </p>
        )}
        {topGaps.length > 0 && (
          <p className="gaps">
            Biggest gaps right now: {topGaps.map((s, i) => (
              <span key={s.name}><strong>{s.name}</strong>{i < topGaps.length - 1 ? ', ' : ''}</span>
            ))}.
          </p>
        )}
      </section>

      <div className="filter-bar">
        <div className="segmented" role="group" aria-label="Which postings">
          <button className={scope === 'all' ? 'active' : ''} onClick={() => setScope('all')}>All postings</button>
          <button className={scope === 'open' ? 'active' : ''} onClick={() => setScope('open')}>Remote, anywhere</button>
        </div>
        <div className="segmented" role="group" aria-label="Sort">
          <button className={sort === 'demand' ? 'active' : ''} onClick={() => setSort('demand')}>By demand</button>
          <button className={sort === 'gap' ? 'active' : ''} onClick={() => setSort('gap')}>By gap</button>
        </div>
        <label className="check">
          <input id="roadmap-only" type="checkbox" checked={roadmapOnly} onChange={(e) => setRoadmapOnly(e.target.checked)} />
          Only skills on my roadmap or CV
        </label>
      </div>

      <section className="panel">
        <div className="table-scroll">
          <table className="skills-table">
            <thead>
              <tr>
                <th scope="col">Skill</th>
                <th scope="col">In postings</th>
                <th scope="col" className="num">Change (pts)</th>
                <th scope="col" className="num">Median pay (US)</th>
                <th scope="col">Your level</th>
                <th scope="col" className="num">Units done</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <Fragment key={s.name}>
                <tr>
                  <th scope="row">
                    <button className="link-btn" aria-expanded={openSkill === s.name}
                            onClick={() => setOpenSkill(openSkill === s.name ? null : s.name)}>{s.name}</button>
                  </th>
                  <td>
                    <div className="bar-cell">
                      <div className="bar"><span style={{ width: `${(pct(s) / max) * 100}%` }} /></div>
                      <span className="mono small">{pct(s).toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className={`num mono small ${(delta(s) ?? 0) > 0 ? 'up' : (delta(s) ?? 0) < 0 ? 'down' : ''}`}>
                    {delta(s) == null ? '–' : signed(delta(s)!)}
                  </td>
                  <td className="num mono small">{s.median_usd ? `$${Math.round(s.median_usd / 1000)}k` : '–'}</td>
                  <td>
                    <div className="levels" role="radiogroup" aria-label={`Your level in ${s.name}`}>
                      {LEVELS.map((label, lvl) => (
                        <button
                          key={label}
                          role="radio"
                          aria-checked={s.my_level === lvl}
                          title={label}
                          className={lvl <= s.my_level && s.my_level > 0 ? 'lvl on' : 'lvl'}
                          onClick={() => setLevel(s.name, lvl)}
                        >
                          <span className="sr-only">{label}</span>
                        </button>
                      ))}
                      <span className="small muted lvl-label">{LEVELS[s.my_level]}</span>
                    </div>
                  </td>
                  <td className="num mono small">{s.units_total ? `${s.units_done}/${s.units_total}` : '–'}</td>
                </tr>
                {openSkill === s.name && (
                  <tr className="trend-row">
                    <td colSpan={6}><Trend points={history} scope={scope} /></td>
                  </tr>
                )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small footnote">
          Pay is the median listed salary on US-heavy postings. Use it to compare skills, not as an estimate of what you'd be paid.
        </p>
      </section>
    </div>
  )
}

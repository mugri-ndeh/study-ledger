import { hours } from '../api'
import type { Dashboard, Strengths, Track } from '../types'

const shortDate = (iso: string) => new Date(iso + 'T00:00:00').toLocaleDateString('en', { day: 'numeric', month: 'short' })

function niceMax(v: number, step: number): number {
  return Math.max(step, Math.ceil(v / step) * step)
}

/** Stacked weekly hours per track for the last 12 weeks, with the weekly target as a dashed line. */
export function WeeklyBars({ weekly, tracks, targetMinutes }: { weekly: Dashboard['weekly']; tracks: Track[]; targetMinutes: number }) {
  const W = 640, H = 220, L = 34, B = 24, T = 10
  const totals = weekly.map((w) => Object.values(w.tracks).reduce((a, b) => a + b, 0))
  const maxH = niceMax(Math.max(targetMinutes, ...totals) / 60 * 1.1, 4)
  const y = (minutes: number) => H - B - (minutes / 60 / maxH) * (H - B - T)
  const band = (W - L) / weekly.length
  const ticks = Array.from({ length: 5 }, (_, i) => (maxH / 4) * i)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label="Hours studied per week, last 12 weeks">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={L} x2={W} y1={y(t * 60)} y2={y(t * 60)} className="grid" />
          <text x={L - 6} y={y(t * 60) + 4} className="axis" textAnchor="end">{t}h</text>
        </g>
      ))}
      {weekly.map((w, i) => {
        let acc = 0
        const x = L + i * band + band * 0.18
        return (
          <g key={w.week_start}>
            {tracks.map((t) => {
              const m = w.tracks[t.id] || 0
              if (!m) return null
              const y0 = y(acc), y1 = y(acc + m)
              acc += m
              return <rect key={t.id} x={x} width={band * 0.64} y={y1} height={Math.max(0, y0 - y1)} fill={t.color}><title>{`${t.name}: ${hours(m)} h`}</title></rect>
            })}
            {i % 2 === (weekly.length - 1) % 2 && <text x={x + band * 0.32} y={H - 6} className="axis" textAnchor="middle">{shortDate(w.week_start)}</text>}
          </g>
        )
      })}
      <line x1={L} x2={W} y1={y(targetMinutes)} y2={y(targetMinutes)} className="target" />
      <text x={W - 4} y={y(targetMinutes) - 5} className="axis strong" textAnchor="end">target {hours(targetMinutes)}h</text>
    </svg>
  )
}

/** Cumulative hours actually studied vs. what the weekly targets add up to. */
export function BurnUp({ burnup }: { burnup: Dashboard['burnup'] }) {
  const W = 640, H = 220, L = 40, B = 24, T = 12, R = 12
  const maxV = niceMax(Math.max(...burnup.map((b) => Math.max(b.actual_minutes, b.planned_minutes))) / 60, 10)
  const n = Math.max(burnup.length, 2)
  const x = (i: number) => L + (i / (n - 1)) * (W - L - R)
  const y = (m: number) => H - B - (m / 60 / maxV) * (H - B - T)
  const line = (key: 'actual_minutes' | 'planned_minutes') => burnup.map((b, i) => `${i ? 'L' : 'M'}${x(i)},${y(b[key])}`).join(' ')
  const last = burnup[burnup.length - 1]
  const ticks = Array.from({ length: 5 }, (_, i) => (maxV / 4) * i)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label="Cumulative hours: actual vs planned">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={y(t * 60)} y2={y(t * 60)} className="grid" />
          <text x={L - 6} y={y(t * 60) + 4} className="axis" textAnchor="end">{Math.round(t)}h</text>
        </g>
      ))}
      <path d={line('planned_minutes')} className="line planned" />
      <path d={`${line('actual_minutes')} L${x(burnup.length - 1)},${y(0)} L${x(0)},${y(0)} Z`} className="area actual" />
      <path d={line('actual_minutes')} className="line actual" />
      {burnup.map((b, i) => <circle key={b.week_start} cx={x(i)} cy={y(b.actual_minutes)} r={i === burnup.length - 1 ? 4.5 : 2.5} className="dot-actual"><title>{`${shortDate(b.week_start)}: ${hours(b.actual_minutes)} h of ${hours(b.planned_minutes)} h planned`}</title></circle>)}
      <text x={L} y={H - 6} className="axis">{shortDate(burnup[0].week_start)}</text>
      {burnup.length > 1 && <text x={W - R} y={H - 6} className="axis" textAnchor="end">{shortDate(last.week_start)}</text>}
    </svg>
  )
}

/** Radar of confidence (avg recap rating) and coverage (share of the track done), both on a 0-5 scale. */
export function Radar({ data }: { data: Strengths['tracks'] }) {
  const S = 320, C = S / 2, R = 110
  const n = data.length
  const pt = (i: number, v: number) => {
    const a = -Math.PI / 2 + (i / n) * Math.PI * 2
    return [C + Math.cos(a) * (v / 5) * R, C + Math.sin(a) * (v / 5) * R]
  }
  const poly = (vals: number[]) => vals.map((v, i) => pt(i, v).join(',')).join(' ')

  return (
    <svg viewBox={`-60 -10 ${S + 120} ${S + 20}`} className="chart radar" role="img" aria-label="Confidence and coverage per track">
      {[1, 2, 3, 4, 5].map((lvl) => <polygon key={lvl} points={poly(Array(n).fill(lvl))} className="grid" fill="none" />)}
      {data.map((d, i) => {
        const [x, y] = pt(i, 5)
        const [lx, ly] = pt(i, 6.1)
        return (
          <g key={d.id}>
            <line x1={C} y1={C} x2={x} y2={y} className="grid" />
            <text x={lx} y={ly} className="axis strong" textAnchor={lx < C - 5 ? 'end' : lx > C + 5 ? 'start' : 'middle'} dominantBaseline="middle">{d.name}</text>
          </g>
        )
      })}
      <polygon points={poly(data.map((d) => d.coverage * 5))} className="radar-coverage" />
      <polygon points={poly(data.map((d) => d.confidence ?? 0))} className="radar-confidence" />
      {data.map((d, i) => d.confidence ? <circle key={d.id} cx={pt(i, d.confidence)[0]} cy={pt(i, d.confidence)[1]} r={3.5} fill={d.color}><title>{`${d.name}: ${d.confidence}/5`}</title></circle> : null)}
    </svg>
  )
}

/** One stacked bar per LeetCode pattern: solved alone, with a hint, after the solution, untouched. */
export function PatternBars({ patterns }: { patterns: Strengths['patterns'] }) {
  const rowH = 26, L = 190, W = 640
  const H = patterns.length * rowH + 8
  const max = Math.max(...patterns.map((p) => p.total), 1)
  const scale = (W - L - 40) / max
  const parts: [keyof Strengths['patterns'][number], string][] = [['solo', 'seg-solo'], ['hint', 'seg-hint'], ['solution', 'seg-solution'], ['untouched', 'seg-untouched']]

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label="LeetCode problems by pattern and how they were solved">
      {patterns.map((p, i) => {
        let acc = 0
        const yTop = i * rowH + 4
        return (
          <g key={p.key}>
            <text x={L - 8} y={yTop + 13} className="axis strong" textAnchor="end">{p.title}</text>
            {parts.map(([k, cls]) => {
              const v = p[k] as number
              if (!v) return null
              const x = L + acc * scale
              acc += v
              return <rect key={k} x={x} y={yTop} width={v * scale - 2} height={rowH - 10} rx={3} className={cls}><title>{`${p.title}: ${v} ${k}`}</title></rect>
            })}
            <text x={L + p.total * scale + 6} y={yTop + 13} className="axis">{Math.round(p.score * 100)}%</text>
          </g>
        )
      })}
    </svg>
  )
}

export function Legend({ items }: { items: { label: string; className?: string; color?: string }[] }) {
  return (
    <div className="legend">
      {items.map((it) => (
        <span key={it.label}><i className={it.className} style={it.color ? { background: it.color } : undefined} />{it.label}</span>
      ))}
    </div>
  )
}

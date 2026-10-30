import type { Plan, Unit } from '../types'

const PX_PER_WEEK = 14
const ROW_H = 58
const LEFT = 150
const TOP = 34

/**
 * The whole plan as a timeline: one lane per track, one bar per unit at its planned weeks,
 * curved arrows where a unit waits for another track. Click a unit to open it in the plan.
 */
export default function RoadmapGraph({ plan, onOpen }: { plan: Plan; onOpen: (u: Unit) => void }) {
  const lanes = plan.tracks
  const laneOf = Object.fromEntries(lanes.map((t, i) => [t.id, i]))
  const byKey = Object.fromEntries(plan.units.map((u) => [u.key, u]))
  const maxWeek = Math.ceil(Math.max(...plan.units.map((u) => u.plan_end_week)) / 4) * 4
  const W = LEFT + maxWeek * PX_PER_WEEK + 30
  const H = TOP + lanes.length * ROW_H + 10
  const x = (week: number) => LEFT + week * PX_PER_WEEK
  const laneY = (i: number) => TOP + i * ROW_H + ROW_H / 2

  const start = new Date(plan.plan_start + 'T00:00:00')
  const nowWeek = (Date.now() - start.getTime()) / (7 * 24 * 3600 * 1000)
  const months: { week: number; label: string }[] = []
  for (let w = 0; w <= maxWeek; w += 1) {
    const d = new Date(start.getTime() + w * 7 * 24 * 3600 * 1000)
    const prev = new Date(start.getTime() + (w - 1) * 7 * 24 * 3600 * 1000)
    if (w === 0 || d.getMonth() !== prev.getMonth()) {
      months.push({ week: w, label: d.toLocaleDateString('en', { month: 'short', year: d.getMonth() === 0 || w === 0 ? '2-digit' : undefined }) })
    }
  }

  return (
    <div className="roadmap-scroll">
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="roadmap" role="img" aria-label="Roadmap of every unit on a timeline">
        <defs>
          <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L8,4 L0,8 z" className="dep-head" />
          </marker>
          <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="6" className="hatch" />
          </pattern>
        </defs>

        {months.map((m) => (
          <g key={m.week}>
            <line x1={x(m.week)} x2={x(m.week)} y1={TOP - 8} y2={H} className="grid" />
            <text x={x(m.week) + 4} y={16} className="axis">{m.label}</text>
          </g>
        ))}

        {lanes.map((t, i) => (
          <g key={t.id}>
            <line x1={LEFT} x2={W - 20} y1={laneY(i)} y2={laneY(i)} stroke={t.color} className="lane-line" />
            <circle cx={14} cy={laneY(i)} r={6} fill={t.color} />
            <text x={26} y={laneY(i) - 4} className="lane-label">{t.name}</text>
            <text x={26} y={laneY(i) + 12} className="axis">{t.weekly_target_hours} h/week</text>
          </g>
        ))}

        {plan.units.filter((u) => u.requires_key && byKey[u.requires_key]).map((u) => {
          const req = byKey[u.requires_key!]
          const x1 = x(req.plan_end_week), y1 = laneY(laneOf[req.track_id])
          const x2 = x(u.plan_start_week) + 2, y2 = laneY(laneOf[u.track_id])
          const mid = (x1 + x2) / 2
          return <path key={u.key} d={`M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}`} className={`dep ${u.state === 'blocked' ? 'active' : ''}`} markerEnd="url(#arrow)" />
        })}

        {plan.units.map((u) => {
          const t = lanes[laneOf[u.track_id]]
          const bx = x(u.plan_start_week) + 1
          const bw = Math.max(6, (u.plan_end_week - u.plan_start_week) * PX_PER_WEEK - 2)
          const by = laneY(laneOf[u.track_id]) - 11
          const pct = u.steps_total ? u.steps_done / u.steps_total : 0
          return (
            <g key={u.key} className={`unit-bar ${u.state}`} tabIndex={0} role="button"
               onClick={() => onOpen(u)} onKeyDown={(e) => { if (e.key === 'Enter') onOpen(u) }}>
              <title>{`${u.title}\n${u.steps_done}/${u.steps_total} steps · ${u.state}${u.rating ? ` · confidence ${u.rating}/5` : ''}`}</title>
              <rect x={bx} y={by} width={bw} height={22} rx={6} className="bar-bg" stroke={t.color} />
              {u.state === 'blocked' && <rect x={bx} y={by} width={bw} height={22} rx={6} fill="url(#hatch)" />}
              <rect x={bx} y={by} width={bw * (u.state === 'done' ? 1 : pct)} height={22} rx={6} fill={t.color} className="bar-fill" />
              {bw > 64 && <text x={bx + 7} y={by + 15} className={`bar-label ${u.state === 'done' || pct > 0.5 ? 'on-fill' : ''}`}>{trim(u.title, bw)}</text>}
              {u.project_key && <circle cx={bx + bw - 6} cy={by - 4} r={4} className="build-dot" stroke={t.color}><title>Ends with a build project</title></circle>}
            </g>
          )
        })}

        {nowWeek >= 0 && nowWeek <= maxWeek && (
          <g>
            <line x1={x(nowWeek)} x2={x(nowWeek)} y1={TOP - 12} y2={H} className="now-line" />
            <text x={x(nowWeek) + 4} y={TOP - 2} className="axis strong">today</text>
          </g>
        )}
      </svg>
    </div>
  )
}

function trim(s: string, width: number): string {
  const chars = Math.floor((width - 14) / 6.4)
  return s.length > chars ? s.slice(0, Math.max(3, chars - 1)) + '…' : s
}

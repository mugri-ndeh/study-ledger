import { hours } from '../api'

const CELL = 13
const GAP = 3
const DAY_LABELS = ['Mon', '', 'Wed', '', 'Fri', '', 'Sun']

function level(minutes: number): number {
  if (minutes <= 0) return 0
  if (minutes < 45) return 1
  if (minutes < 90) return 2
  if (minutes < 180) return 3
  return 4
}

/** GitHub-style calendar: one column per week (Monday first), the series starts on a Monday. */
export default function Heatmap({ days }: { days: { day: string; minutes: number }[] }) {
  const weeks = Math.ceil(days.length / 7)
  const left = 30
  const top = 16
  const width = left + weeks * (CELL + GAP)
  const height = top + 7 * (CELL + GAP)

  const monthLabels: { x: number; label: string }[] = []
  days.forEach((d, i) => {
    const date = new Date(d.day + 'T00:00:00')
    if (i % 7 === 0 && date.getDate() <= 7) {
      monthLabels.push({ x: left + Math.floor(i / 7) * (CELL + GAP), label: date.toLocaleString('en', { month: 'short' }) })
    }
  })

  return (
    <div className="heatmap-wrap">
      <svg className="heatmap" viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="img" aria-label="Study time per day over the last 26 weeks">
        {monthLabels.map((m) => (
          <text key={m.x} x={m.x} y={10} className="hm-label">{m.label}</text>
        ))}
        {DAY_LABELS.map((label, row) => label && (
          <text key={label} x={0} y={top + row * (CELL + GAP) + CELL - 3} className="hm-label">{label}</text>
        ))}
        {days.map((d, i) => (
          <rect
            key={d.day}
            x={left + Math.floor(i / 7) * (CELL + GAP)}
            y={top + (i % 7) * (CELL + GAP)}
            width={CELL}
            height={CELL}
            rx={3}
            className={`hm-cell l${level(d.minutes)}`}
          >
            <title>{`${d.day}: ${d.minutes ? hours(d.minutes) + ' h' : 'no study'}`}</title>
          </rect>
        ))}
      </svg>
      <div className="hm-legend" aria-hidden="true">
        <span>Less</span>
        {[0, 1, 2, 3, 4].map((l) => <span key={l} className={`hm-swatch l${l}`} />)}
        <span>3h+</span>
      </div>
    </div>
  )
}

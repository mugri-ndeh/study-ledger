import type { Shared } from '../App'
import RoadmapGraph from '../charts/RoadmapGraph'
import { hours } from '../api'

export default function RoadmapView({ plan, openUnit }: Shared) {
  const totalHours = plan.units.reduce((n, u) => n + u.est_minutes, 0)
  const weekly = plan.tracks.reduce((n, t) => n + t.weekly_target_hours, 0)
  const lastWeek = Math.max(...plan.units.map((u) => u.plan_end_week))

  return (
    <div className="stack">
      <section className="panel intro">
        <p>
          Every unit on one timeline, at your weekly targets ({weekly} h a week). Tracks run side by side; an arrow means a
          unit waits for one in another track. The whole plan is about <strong>{hours(totalHours)} hours</strong>, so roughly{' '}
          <strong>{Math.round(lastWeek)} weeks</strong> until the last unit finishes. Click any unit to open it.
        </p>
        <div className="legend">
          <span><i className="lg-done" />Done</span>
          <span><i className="lg-current" />In progress</span>
          <span><i className="lg-blocked" />Waiting on another track</span>
          <span><i className="lg-upcoming" />Upcoming</span>
          <span><i className="lg-build" />Ends with a build project</span>
        </div>
      </section>
      <section className="panel flush">
        <RoadmapGraph plan={plan} onOpen={openUnit} />
      </section>
      <section className="panel">
        <div className="panel-head"><h2>Milestones</h2><span className="muted small">When each track should finish at your current targets</span></div>
        <ul className="milestones">
          {plan.tracks.map((t) => {
            const own = plan.units.filter((u) => u.track_id === t.id)
            const end = Math.max(...own.map((u) => u.plan_end_week))
            const date = new Date(new Date(plan.plan_start + 'T00:00:00').getTime() + end * 7 * 86400000)
            return (
              <li key={t.id} style={{ '--track': t.color } as React.CSSProperties}>
                <span className="dot" />
                <strong>{t.name}</strong>
                <span className="muted small">{own.length} units · {hours(own.reduce((n, u) => n + u.est_minutes, 0))} h</span>
                <span className="mono small">{date.toLocaleDateString('en', { month: 'short', year: 'numeric' })}</span>
              </li>
            )
          })}
        </ul>
      </section>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { api, localDay } from '../api'
import type { Shared } from '../App'
import type { Dashboard, RatedUnit, Strengths } from '../types'
import { BurnUp, Legend, PatternBars, Radar } from '../charts/charts'

export default function Progress({ plan, version, openUnit }: Shared) {
  const [s, setS] = useState<Strengths | null>(null)
  const [dash, setDash] = useState<Dashboard | null>(null)

  useEffect(() => {
    api.get<Strengths>('/strengths').then(setS).catch(() => setS(null))
    api.get<Dashboard>(`/dashboard?today=${localDay()}`).then(setDash).catch(() => setDash(null))
  }, [version])

  if (!s || !dash) return <p className="muted">Loading…</p>

  const trackName = (id: number) => plan.tracks.find((t) => t.id === id)?.name ?? id
  const open = (key: string) => { const u = plan.units.find((x) => x.key === key); if (u) openUnit(u) }
  const rated = s.timeline.length

  const UnitList = ({ items, empty }: { items: RatedUnit[]; empty: string }) => (
    items.length === 0 ? <p className="empty small">{empty}</p> : (
      <ul className="rated-list">
        {items.map((u) => (
          <li key={u.key}>
            <button className="link-btn" onClick={() => open(u.key)}>{u.title}</button>
            <span className="muted small">{trackName(u.track_id)} · {u.rating}/5</span>
            {u.reflection && <span className="small reflection">“{u.reflection}”</span>}
          </li>
        ))}
      </ul>
    )
  )

  return (
    <div className="stack">
      <section className="panel intro">
        <p>
          Strengths come from your own recaps: at the end of every unit you answer questions from memory and rate your
          confidence. LeetCode strength comes from how you solved each problem. {rated === 0 && 'Finish your first unit and the charts below fill in.'}
        </p>
      </section>

      <div className="two-col">
        <section className="panel">
          <div className="panel-head"><h2>Confidence vs coverage</h2></div>
          <Radar data={s.tracks} />
          <Legend items={[{ label: 'Confidence (avg recap rating, 0-5)', className: 'lg-confidence' }, { label: 'Coverage (share of track done)', className: 'lg-coverage' }]} />
        </section>
        <section className="panel">
          <div className="panel-head"><h2>Hours: actual vs plan</h2><span className="muted small">Cumulative since {dash.plan_start}</span></div>
          <BurnUp burnup={dash.burnup} />
          <Legend items={[{ label: 'You', className: 'lg-actual' }, { label: 'Weekly targets added up', className: 'lg-planned' }]} />
        </section>
      </div>

      <section className="panel">
        <div className="panel-head"><h2>Track progress</h2><span className="muted small">Projected finish at current targets</span></div>
        <ul className="progress-rows">
          {dash.tracks.map((t) => {
            const pct = t.est_minutes_total ? (t.est_minutes_done / t.est_minutes_total) * 100 : 0
            const conf = s.tracks.find((x) => x.id === t.id)?.confidence
            return (
              <li key={t.id} style={{ '--track': t.color } as React.CSSProperties}>
                <span className="track-name-sm"><span className="dot" />{t.name}</span>
                <div className="meter track"><span style={{ width: `${pct}%` }} /></div>
                <span className="mono small">{Math.round(pct)}%</span>
                <span className="mono small muted">{conf ? `${conf}/5` : '–'}</span>
                <span className="mono small muted">{new Date(t.projected_finish + 'T00:00:00').toLocaleDateString('en', { month: 'short', year: 'numeric' })}</span>
              </li>
            )
          })}
        </ul>
      </section>

      <section className="panel">
        <div className="panel-head"><h2>LeetCode by pattern</h2><span className="muted small">Score: solo 100%, hint 60%, solution 30%</span></div>
        <PatternBars patterns={s.patterns} />
        <Legend items={[{ label: 'Solo', className: 'seg-solo' }, { label: 'With a hint', className: 'seg-hint' }, { label: 'After the solution', className: 'seg-solution' }, { label: 'Not yet', className: 'seg-untouched' }]} />
      </section>

      <div className="two-col">
        <section className="panel">
          <div className="panel-head"><h2>Strengths</h2><span className="muted small">Units rated 4-5</span></div>
          <UnitList items={s.strong} empty="Units you rate 4 or 5 show up here." />
        </section>
        <section className="panel">
          <div className="panel-head"><h2>Revisit</h2><span className="muted small">Units rated 1-2, with your notes</span></div>
          <UnitList items={s.weak} empty="Units you rate 1 or 2 show up here, so you can review them before interviews." />
        </section>
      </div>

      {s.skills.length > 0 && (
        <section className="panel">
          <div className="panel-head"><h2>Skill confidence</h2><span className="muted small">Average recap rating of units that teach each skill</span></div>
          <ul className="skill-bars">
            {s.skills.map((k) => (
              <li key={k.name}>
                <span>{k.name}</span>
                <div className="meter"><span style={{ width: `${(k.confidence / 5) * 100}%` }} /></div>
                <span className="mono small">{k.confidence}/5 · {k.units} units</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

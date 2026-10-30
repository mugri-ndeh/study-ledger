import { useEffect, useState } from 'react'
import { api, hours } from '../api'
import type { Shared } from '../App'
import type { Unit } from '../types'
import StepCard, { KIND_LABEL } from '../components/StepCard'
import LogPanel from '../components/LogPanel'

const STATE_LABEL: Record<Unit['state'], string> = { done: 'Done', current: 'Current', blocked: 'Waiting', upcoming: 'Upcoming' }

export default function PlanView({ plan, changed, selectedUnit }: Shared) {
  const initial = plan.units.find((u) => u.key === selectedUnit)
  const [trackId, setTrackId] = useState(initial?.track_id ?? plan.tracks[0].id)
  const [unitKey, setUnitKey] = useState<string | null>(initial?.key ?? null)
  const [openStep, setOpenStep] = useState<number | null>(null)

  useEffect(() => {
    const u = plan.units.find((x) => x.key === selectedUnit)
    if (u) { setTrackId(u.track_id); setUnitKey(u.key) }
  }, [selectedUnit, plan.units])

  const track = plan.tracks.find((t) => t.id === trackId)
  const units = plan.units.filter((u) => u.track_id === trackId)
  const unit = units.find((u) => u.key === unitKey) ?? units.find((u) => u.state === 'current' || u.state === 'blocked') ?? units[0]
  const byKey = Object.fromEntries(plan.units.map((u) => [u.key, u]))
  const pct = track?.est_minutes_total ? Math.round((track.est_minutes_done / track.est_minutes_total) * 100) : 0
  const weeksTotal = Math.max(0, ...units.map((u) => u.plan_end_week))

  async function reopen(stepId: number) {
    await api.post(`/steps/${stepId}/reopen`, {})
    changed()
  }

  const trackChips = (
    <div className="filter-bar" role="group" aria-label="Tracks">
      <div className="chips">
        {plan.tracks.map((t) => (
          <button key={t.id} className={t.id === trackId ? 'chip active' : 'chip'} style={{ '--track': t.color } as React.CSSProperties}
                  onClick={() => { setTrackId(t.id); setUnitKey(null) }}>
            <span className="dot" /> {t.name}
          </button>
        ))}
      </div>
    </div>
  )

  if (!track || !unit) {
    return (
      <div className="stack">
        {trackChips}
        <section className="panel"><p className="empty">This track has no units yet. Add some in <a href="#edit">Edit plan</a>.</p></section>
      </div>
    )
  }

  return (
    <div className="stack">
      {trackChips}

      <section className="panel track-hero" style={{ '--track': track.color } as React.CSSProperties}>
        <div>
          <h2>{track.name}</h2>
          <p className="muted">{track.goal}</p>
        </div>
        <div className="hero-figures">
          <div><span className="stat-label">Done</span><span className="mono">{pct}%</span></div>
          <div><span className="stat-label">Units</span><span className="mono">{units.filter((u) => u.complete).length}/{units.length}</span></div>
          <div><span className="stat-label">Plan length</span><span className="mono">{Math.round(weeksTotal)} wks at {track.weekly_target_hours} h</span></div>
        </div>
        <div className="meter track"><span style={{ width: `${pct}%` }} /></div>
      </section>

      <div className="plan-layout">
        <nav className="unit-path" aria-label={`${track.name} units`}>
          {units.map((u, i) => (
            <button key={u.key} className={`path-node ${u.state} ${u.key === unit.key ? 'selected' : ''}`} style={{ '--track': track.color } as React.CSSProperties}
                    onClick={() => { setUnitKey(u.key); setOpenStep(null) }}>
              <span className="node" aria-hidden="true">{u.state === 'done' ? '✓' : i + 1}</span>
              <span className="path-text">
                <strong>{u.title}</strong>
                <span className="muted small">{STATE_LABEL[u.state]} · {u.steps_done}/{u.steps_total} steps{u.rating ? ` · ${u.rating}/5` : ''}</span>
              </span>
            </button>
          ))}
        </nav>

        <section className="panel unit-detail" style={{ '--track': track.color } as React.CSSProperties}>
          <div className="unit-head">
            <span className={`state-pill ${unit.state}`}>{STATE_LABEL[unit.state]}</span>
            <h2>{unit.title}</h2>
            <span className="muted small mono">weeks {Math.floor(unit.plan_start_week) + 1}–{Math.ceil(unit.plan_end_week)} · {hours(unit.est_minutes)} h planned · {hours(unit.logged_minutes)} h logged</span>
          </div>
          <div className="lesson-brief">
            <p><span className="label">Why this unit</span>{unit.why}</p>
            <p><span className="label">By the end you can</span>{unit.outcome}</p>
            {unit.requires_key && byKey[unit.requires_key] && (
              <p><span className="label">Starts after</span>{byKey[unit.requires_key].title} ({plan.tracks.find((t) => t.id === byKey[unit.requires_key!].track_id)?.name}){byKey[unit.requires_key].complete ? ', done' : ''}</p>
            )}
            {unit.skills.length > 0 && <div className="tags">{unit.skills.map((s) => <span key={s} className="tag">{s}</span>)}</div>}
          </div>

          <ol className="step-list">
            {unit.steps.map((s) => {
              const isCurrent = s.id === track.current_step_id
              const expanded = openStep === s.id || (openStep === null && isCurrent)
              return (
                <li key={s.id} className={`step-row ${s.status} ${isCurrent ? 'current' : ''}`}>
                  <button className="step-row-head" onClick={() => setOpenStep(expanded ? -1 : s.id)} aria-expanded={expanded}>
                    <span className="step-check" aria-hidden="true">{s.status === 'done' ? '✓' : ''}</span>
                    <span className={`kind-badge ${s.kind}`}>{KIND_LABEL[s.kind]}</span>
                    <span className="step-title">{s.title}</span>
                    {isCurrent && <span className="now-tag">{track.blocked_by ? 'waiting' : 'you are here'}</span>}
                    <span className="mono small muted">{hours(s.est_minutes)} h</span>
                  </button>
                  {expanded && (
                    <div className="step-row-body">
                      <StepCard step={s} changed={changed} />
                      {isCurrent && !track.blocked_by && <LogPanel key={s.id} trackId={track.id} step={s} changed={changed} />}
                      {isCurrent && track.blocked_by && <p className="banner">This step opens after you finish <strong>{track.blocked_by.title}</strong>.</p>}
                      {s.id === track.last_done_step_id && <button className="quiet" onClick={() => reopen(s.id)}>Undo: mark as not finished</button>}
                    </div>
                  )}
                </li>
              )
            })}
          </ol>
        </section>
      </div>
    </div>
  )
}

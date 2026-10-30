import { useEffect, useState } from 'react'
import { api, hours, localDay } from '../api'
import type { Shared } from '../App'
import type { Dashboard, PlanItem, Step } from '../types'
import Heatmap from '../components/Heatmap'
import StepCard, { KIND_LABEL } from '../components/StepCard'
import LogPanel from '../components/LogPanel'
import { Legend, WeeklyBars } from '../charts/charts'

export default function Today({ plan, version, changed, openUnit }: Shared) {
  const [dash, setDash] = useState<Dashboard | null>(null)
  const [open, setOpen] = useState<number | null>(null)

  useEffect(() => {
    api.get<Dashboard>(`/dashboard?today=${localDay()}`).then(setDash).catch(() => setDash(null))
  }, [version])

  if (!dash) return <p className="muted">Loading…</p>

  // The plan carries resources for every step; the dashboard only carries the step itself.
  const fullStep = (s: Step) => plan.units.flatMap((u) => u.steps).find((x) => x.id === s.id) ?? s
  const trackOf = (id: number) => plan.tracks.find((t) => t.id === id)!
  const todayItems = dash.today_plan.filter((x) => x.slot === 'today')
  const later = dash.today_plan.filter((x) => x.slot === 'later' || x.slot === 'done_for_week')
  const blocked = dash.today_plan.filter((x) => x.slot === 'blocked')
  const weekPct = Math.min(100, Math.round((dash.week_minutes / dash.week_target_minutes) * 100))
  const todayTotal = todayItems.reduce((n, x) => n + x.suggested_minutes, 0)

  const renderItem = (item: PlanItem) => {
    const t = trackOf(item.track_id)
    const unit = plan.units.find((u) => u.id === item.unit.id)!
    const isOpen = open === item.track_id
    const stepIndex = unit.steps.findIndex((s) => s.id === item.step.id) + 1
    return (
      <li key={item.track_id} className={`plan-item ${isOpen ? 'open' : ''}`} style={{ '--track': t.color } as React.CSSProperties}>
        <button className="plan-item-head" onClick={() => setOpen(isOpen ? null : item.track_id)} aria-expanded={isOpen}>
          <span className="dot" />
          <span className="plan-item-text">
            <span className="muted small">{t.name} · {item.unit.title} · step {stepIndex} of {unit.steps.length}</span>
            <strong>{item.step.title}</strong>
          </span>
          <span className={`kind-badge ${item.step.kind}`}>{KIND_LABEL[item.step.kind]}</span>
          {item.suggested_minutes > 0 && <span className="mono block-time">{hours(item.suggested_minutes)} h</span>}
        </button>
        {isOpen && (
          <div className="plan-item-body">
            <StepCard step={fullStep(item.step)} changed={changed} />
            <LogPanel key={item.step.id} trackId={item.track_id} step={item.step} suggested={item.suggested_minutes} changed={changed} />
            <button className="link-btn" onClick={() => openUnit(unit)}>Open the whole unit</button>
          </div>
        )}
      </li>
    )
  }

  return (
    <div className="stack">
      <section className="stats" aria-label="Totals">
        <div className="stat stat-streak">
          <span className="stat-label">Streak</span>
          <span className="stat-value">{dash.current_streak}<small> {dash.current_streak === 1 ? 'day' : 'days'}</small></span>
          <span className="stat-note">{dash.studied_today ? 'Today is logged.' : dash.current_streak ? 'Log today to keep it.' : 'Log a session to start one.'} Best: {dash.longest_streak}</span>
        </div>
        <div className="stat">
          <span className="stat-label">This week</span>
          <span className="stat-value">{hours(dash.week_minutes)}<small> / {hours(dash.week_target_minutes)} h</small></span>
          <div className="meter" aria-hidden="true"><span style={{ width: `${weekPct}%` }} /></div>
        </div>
        <div className="stat">
          <span className="stat-label">Last 7 days</span>
          <span className="stat-value">{hours(dash.last7_minutes)}<small> h</small></span>
          <span className="stat-note">All time: {hours(dash.total_minutes)} h</span>
        </div>
        <div className="stat">
          <span className="stat-label">Plan progress</span>
          <span className="stat-value">{dash.tracks.reduce((n, t) => n + t.steps_done, 0)}<small> / {dash.tracks.reduce((n, t) => n + t.steps_total, 0)} steps</small></span>
          <span className="stat-note">{plan.units.filter((u) => u.complete).length} of {plan.units.length} units finished</span>
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Today’s plan</h2>
          <span className="muted small">{todayItems.length ? `${todayItems.length} blocks · about ${hours(todayTotal)} h` : 'Weekly targets met. Rest, or get ahead below.'}</span>
        </div>
        <p className="muted small intro-line">Each track moves one step at a time. Open a block, follow the steps, then log your time. Tick “I finished this step” and that track moves on.</p>
        <ul className="plan-list">{todayItems.map(renderItem)}</ul>
        {later.length > 0 && (
          <>
            <h3 className="sub-head">Later this week</h3>
            <ul className="plan-list quiet">{later.map(renderItem)}</ul>
          </>
        )}
        {blocked.length > 0 && (
          <ul className="blocked-list">
            {blocked.map((x) => (
              <li key={x.track_id} style={{ '--track': trackOf(x.track_id).color } as React.CSSProperties}>
                <span className="dot" /> <strong>{trackOf(x.track_id).name}</strong> waits for <em>{x.blocked_by!.title}</em> ({trackOf(x.blocked_by!.track_id).name}).
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="two-col">
        <section className="panel">
          <div className="panel-head"><h2>Hours per week</h2><span className="muted small">Last 12 weeks</span></div>
          <WeeklyBars weekly={dash.weekly} tracks={plan.tracks} targetMinutes={dash.week_target_minutes} />
          <Legend items={plan.tracks.map((t) => ({ label: t.name, color: t.color }))} />
        </section>
        <section className="panel">
          <div className="panel-head"><h2>This week by track</h2></div>
          <ul className="track-rows">
            {dash.tracks.map((t) => {
              const target = t.weekly_target_hours * 60
              const pct = target ? Math.min(100, (t.week_minutes / target) * 100) : 0
              return (
                <li key={t.id} className="track-row compact" style={{ '--track': t.color } as React.CSSProperties}>
                  <span className="track-name-sm"><span className="dot" />{t.name}</span>
                  <div className="meter track"><span style={{ width: `${pct}%` }} /></div>
                  <span className="mono small">{hours(t.week_minutes)}/{t.weekly_target_hours}h</span>
                </li>
              )
            })}
          </ul>
        </section>
      </div>

      <section className="panel">
        <div className="panel-head"><h2>Study calendar</h2><span className="muted small">Last 26 weeks</span></div>
        <Heatmap days={dash.heatmap} />
      </section>
    </div>
  )
}

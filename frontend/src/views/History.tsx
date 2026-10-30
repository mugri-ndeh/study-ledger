import { useEffect, useState } from 'react'
import { api, hours } from '../api'
import type { Shared } from '../App'
import type { Session } from '../types'
import { KIND_LABEL } from '../components/StepCard'

export default function History({ plan, version, changed }: Shared) {
  const [sessions, setSessions] = useState<Session[]>([])
  const [confirm, setConfirm] = useState<number | null>(null)

  useEffect(() => {
    api.get<Session[]>('/sessions?limit=300').then(setSessions).catch(() => setSessions([]))
  }, [version])

  const byDay = new Map<string, Session[]>()
  for (const s of sessions) byDay.set(s.day, [...(byDay.get(s.day) ?? []), s])

  return (
    <section className="panel">
      <div className="panel-head"><h2>Session history</h2><span className="muted small">Latest 300 sessions</span></div>
      {sessions.length === 0 && <p className="empty">No sessions yet. Start from Today: open a block and log your first session.</p>}
      <div className="days">
        {[...byDay.entries()].map(([day, list]) => (
          <div key={day} className="day-group">
            <div className="day-head">
              <strong>{new Date(day + 'T00:00:00').toLocaleDateString('en', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}</strong>
              <span className="mono small">{hours(list.reduce((n, s) => n + s.minutes, 0))} h</span>
            </div>
            <ul className="session-list">
              {list.map((s) => {
                const t = plan.tracks.find((x) => x.id === s.track_id)
                return (
                  <li key={s.id} style={{ '--track': t?.color } as React.CSSProperties}>
                    <span className="dot" />
                    <div className="session-body">
                      <span>{s.step_kind && <span className={`kind-badge ${s.step_kind}`}>{KIND_LABEL[s.step_kind]}</span>} {s.step_title ?? t?.name}</span>
                      <span className="muted small">{t?.name}{s.unit_title ? ` · ${s.unit_title}` : ''}{s.note ? ` · ${s.note}` : ''}</span>
                    </div>
                    <span className="mono small">{hours(s.minutes)} h</span>
                    {confirm === s.id ? (
                      <span className="row-actions">
                        <button className="danger small-btn" onClick={async () => { await api.del(`/sessions/${s.id}`); setConfirm(null); changed() }}>Delete</button>
                        <button className="small-btn" onClick={() => setConfirm(null)}>Keep</button>
                      </span>
                    ) : (
                      <button className="icon-btn" aria-label="Delete session" onClick={() => setConfirm(s.id)}>×</button>
                    )}
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </div>
    </section>
  )
}

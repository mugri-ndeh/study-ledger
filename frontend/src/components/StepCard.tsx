import { api, hours } from '../api'
import type { Outcome, Resource, Step } from '../types'

export const KIND_LABEL: Record<Step['kind'], string> = {
  learn: 'Learn',
  practice: 'Practice',
  build: 'Build',
  recap: 'Recap',
}

const OUTCOMES: { value: Outcome; label: string }[] = [
  { value: 'solo', label: 'Solo' },
  { value: 'hint', label: 'Hint' },
  { value: 'solution', label: 'Solution' },
]

/** The teacher's view of one step: what to do, what "done" means, and the material to use. */
export default function StepCard({ step, changed, compact = false }: { step: Step; changed: () => void; compact?: boolean }) {
  const resources = step.resources ?? []
  const problems = resources.filter((r) => r.kind === 'problem')
  const material = resources.filter((r) => r.kind !== 'problem')
  const pct = Math.min(100, (step.logged_minutes / step.est_minutes) * 100)

  return (
    <div className={`step-card kind-${step.kind}`}>
      <div className="step-head">
        <span className={`kind-badge ${step.kind}`}>{KIND_LABEL[step.kind]}</span>
        <h4>{step.title}</h4>
        <span className="mono small muted">{hours(step.logged_minutes)} / {hours(step.est_minutes)} h</span>
      </div>
      <div className="meter thin track" aria-hidden="true"><span style={{ width: `${pct}%` }} /></div>

      <ol className="tasks">
        {step.tasks.map((t, i) => <li key={i}>{t}</li>)}
      </ol>

      {step.prompts.length > 0 && (
        <div className="prompts">
          <span className="label">Answer from memory</span>
          <ul>{step.prompts.map((p, i) => <li key={i}>{p}</li>)}</ul>
        </div>
      )}

      <p className="done-when"><span className="label">Done when</span>{step.done_when}</p>

      {!compact && material.length > 0 && (
        <ul className="resources">
          {material.map((r) => <ResourceRow key={r.id} r={r} changed={changed} />)}
        </ul>
      )}

      {problems.length > 0 && (
        <div className="problems">
          <span className="label">Problems · how did you solve it?</span>
          <ul>
            {problems.map((r) => (
              <li key={r.id} className={r.outcome ? `solved ${r.outcome}` : ''}>
                <a href={r.url} target="_blank" rel="noreferrer">{r.title}</a>
                <div className="outcome" role="radiogroup" aria-label={`Outcome for ${r.title}`}>
                  {OUTCOMES.map((o) => (
                    <button
                      key={o.value}
                      role="radio"
                      aria-checked={r.outcome === o.value}
                      className={r.outcome === o.value ? `on ${o.value}` : ''}
                      onClick={async () => {
                        await api.patch(`/resources/${r.id}`, { outcome: r.outcome === o.value ? '' : o.value })
                        changed()
                      }}
                    >{o.label}</button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {step.status === 'done' && (
        <p className="muted small">
          Finished {step.completed_on}{step.rating ? ` · confidence ${step.rating}/5` : ''}{step.reflection ? ` · “${step.reflection}”` : ''}
        </p>
      )}
    </div>
  )
}

function ResourceRow({ r, changed }: { r: Resource; changed: () => void }) {
  return (
    <li>
      <input
        id={`res-${r.id}`}
        type="checkbox"
        checked={r.done}
        onChange={async () => { await api.patch(`/resources/${r.id}`, { done: !r.done }); changed() }}
      />
      <label htmlFor={`res-${r.id}`} className="sr-only">Mark {r.title} as used</label>
      <span className={`res-kind ${r.kind}`}>{r.kind}</span>
      {r.url ? <a href={r.url} target="_blank" rel="noreferrer">{r.title}</a> : <span>{r.title}</span>}
    </li>
  )
}

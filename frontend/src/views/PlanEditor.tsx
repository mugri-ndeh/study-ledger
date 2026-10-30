import { useEffect, useRef, useState } from 'react'
import { api, errorText } from '../api'
import type { Shared } from '../App'
import type { Step, StepKind, Template, TrackState, Unit } from '../types'
import { KIND_LABEL } from '../components/StepCard'

const KINDS: StepKind[] = ['learn', 'practice', 'build', 'recap']
const lines = (text: string) => text.split('\n').map((l) => l.trim()).filter(Boolean)

/** Runs a write, shows its error, and refreshes every view on success. */
function useAction(changed: () => void) {
  const [error, setError] = useState('')
  const run = async (fn: () => Promise<unknown>) => {
    setError('')
    try {
      await fn()
      changed()
      return true
    } catch (e) {
      setError(errorText(e))
      return false
    }
  }
  return { error, run }
}

/** A delete button that asks once more before acting. */
function ConfirmButton({ label, confirm, onConfirm }: { label: string; confirm: string; onConfirm: () => void }) {
  const [asking, setAsking] = useState(false)
  if (!asking) return <button className="quiet small-btn" onClick={() => setAsking(true)}>{label}</button>
  return (
    <span className="confirm">
      <span className="small">{confirm}</span>
      <button className="danger small-btn" onClick={() => { setAsking(false); onConfirm() }}>Yes</button>
      <button className="quiet small-btn" onClick={() => setAsking(false)}>No</button>
    </span>
  )
}

export default function PlanEditor({ plan, changed }: Shared) {
  const { error, run } = useAction(changed)
  const [trackId, setTrackId] = useState<number | null>(plan.tracks[0]?.id ?? null)
  const [unitId, setUnitId] = useState<number | null>(null)

  useEffect(() => {
    if (!plan.tracks.some((t) => t.id === trackId)) setTrackId(plan.tracks[0]?.id ?? null)
  }, [plan.tracks, trackId])

  const track = plan.tracks.find((t) => t.id === trackId)
  const units = plan.units.filter((u) => u.track_id === trackId)
  const unit = units.find((u) => u.id === unitId) ?? units[0]

  return (
    <div className="stack">
      <section className="panel intro">
        <p>
          Change anything in your plan. Steps run in the order shown; each track logs time against its first unfinished
          step. Editing text keeps your progress. Deleting a unit or step keeps the hours you logged, but deleting a
          track removes its logged sessions too.
        </p>
        {error && <p className="banner error" role="alert">{error}</p>}
      </section>

      <TrackBar plan={plan} trackId={trackId} setTrackId={(id) => { setTrackId(id); setUnitId(null) }} run={run} />

      {track && (
        <>
          <TrackForm key={track.id} track={track} run={run} isFirst={track.id === plan.tracks[0].id}
                     isLast={track.id === plan.tracks[plan.tracks.length - 1].id} />
          <div className="plan-layout">
            <nav className="unit-path editor-units" aria-label={`${track.name} units`}>
              {units.map((u, i) => (
                <div key={u.id} className={`editor-unit ${unit && u.id === unit.id ? 'selected' : ''}`}>
                  <button className="link-btn" onClick={() => setUnitId(u.id)}>{i + 1}. {u.title}</button>
                  <span className="editor-arrows">
                    <button className="icon-btn" aria-label={`Move ${u.title} up`} disabled={i === 0}
                            onClick={() => run(() => api.post(`/units/${u.id}/move`, { direction: -1 }))}>↑</button>
                    <button className="icon-btn" aria-label={`Move ${u.title} down`} disabled={i === units.length - 1}
                            onClick={() => run(() => api.post(`/units/${u.id}/move`, { direction: 1 }))}>↓</button>
                  </span>
                </div>
              ))}
              <AddUnit trackId={track.id} run={run} onAdded={setUnitId} />
            </nav>
            {unit ? <UnitEditor key={unit.id} unit={unit} allUnits={plan.units} run={run} onDeleted={() => setUnitId(null)} />
                  : <section className="panel"><p className="empty">This track has no units yet. Add one on the left.</p></section>}
          </div>
        </>
      )}

      <WholePlan run={run} />
    </div>
  )
}

type Run = (fn: () => Promise<unknown>) => Promise<boolean>

function TrackBar({ plan, trackId, setTrackId, run }: { plan: Shared['plan']; trackId: number | null; setTrackId: (id: number) => void; run: Run }) {
  const [name, setName] = useState('')
  async function add(e: React.FormEvent) {
    e.preventDefault()
    let created: TrackState | undefined
    if (await run(async () => { created = await api.post<TrackState>('/tracks', { name, weekly_target_hours: 2 }) })) {
      setName('')
      if (created) setTrackId(created.id)
    }
  }
  return (
    <div className="filter-bar" role="group" aria-label="Tracks">
      <div className="chips">
        {plan.tracks.map((t) => (
          <button key={t.id} className={t.id === trackId ? 'chip active' : 'chip'} style={{ '--track': t.color } as React.CSSProperties}
                  onClick={() => setTrackId(t.id)}>
            <span className="dot" /> {t.name}
          </button>
        ))}
      </div>
      <form className="inline-form" onSubmit={add}>
        <label htmlFor="new-track" className="sr-only">New track name</label>
        <input id="new-track" type="text" placeholder="New track name" value={name} onChange={(e) => setName(e.target.value)} required />
        <button type="submit">Add track</button>
      </form>
    </div>
  )
}

function TrackForm({ track, run, isFirst, isLast }: { track: TrackState; run: Run; isFirst: boolean; isLast: boolean }) {
  const [form, setForm] = useState({ name: track.name, goal: track.goal, weekly_target_hours: track.weekly_target_hours, color: track.color })
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: k === 'weekly_target_hours' ? Number(e.target.value) : e.target.value })
  return (
    <section className="panel" style={{ '--track': track.color } as React.CSSProperties}>
      <div className="panel-head">
        <h2>Track</h2>
        <span className="editor-arrows">
          <button className="quiet small-btn" disabled={isFirst} onClick={() => run(() => api.post(`/tracks/${track.id}/move`, { direction: -1 }))}>← Move left</button>
          <button className="quiet small-btn" disabled={isLast} onClick={() => run(() => api.post(`/tracks/${track.id}/move`, { direction: 1 }))}>Move right →</button>
          <ConfirmButton label="Delete track" confirm="Delete this track, its units and its logged hours?"
                         onConfirm={() => run(() => api.del(`/tracks/${track.id}`))} />
        </span>
      </div>
      <form className="form-grid" onSubmit={(e) => { e.preventDefault(); run(() => api.patch(`/tracks/${track.id}`, form)) }}>
        <div className="field wide"><label htmlFor="t-name">Name</label><input id="t-name" type="text" value={form.name} onChange={set('name')} required /></div>
        <div className="field narrow"><label htmlFor="t-hours">Hours / week</label><input id="t-hours" type="number" min={0} max={80} step={0.5} value={form.weekly_target_hours} onChange={set('weekly_target_hours')} /></div>
        <div className="field narrow"><label htmlFor="t-color">Colour</label><input id="t-color" type="color" value={form.color} onChange={set('color')} /></div>
        <div className="field full"><label htmlFor="t-goal">Goal</label><input id="t-goal" type="text" value={form.goal} onChange={set('goal')} /></div>
        <div className="form-actions"><button className="primary" type="submit">Save track</button></div>
      </form>
    </section>
  )
}

function AddUnit({ trackId, run, onAdded }: { trackId: number; run: Run; onAdded: (id: number) => void }) {
  const [title, setTitle] = useState('')
  async function add(e: React.FormEvent) {
    e.preventDefault()
    let created: Unit | undefined
    if (await run(async () => { created = await api.post<Unit>('/units', { track_id: trackId, title }) })) {
      setTitle('')
      if (created) onAdded(created.id)
    }
  }
  return (
    <form className="inline-form" onSubmit={add}>
      <label htmlFor="new-unit" className="sr-only">New unit title</label>
      <input id="new-unit" type="text" placeholder="New unit title" value={title} onChange={(e) => setTitle(e.target.value)} required />
      <button type="submit">Add unit</button>
    </form>
  )
}

function UnitEditor({ unit, allUnits, run, onDeleted }: { unit: Unit; allUnits: Unit[]; run: Run; onDeleted: () => void }) {
  const [form, setForm] = useState({ title: unit.title, why: unit.why, outcome: unit.outcome,
                                     skills: unit.skills.join(', '), requires_key: unit.requires_key ?? '' })
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value })
  function save(e: React.FormEvent) {
    e.preventDefault()
    run(() => api.patch(`/units/${unit.id}`, {
      title: form.title, why: form.why, outcome: form.outcome,
      skills: form.skills.split(',').map((s) => s.trim()).filter(Boolean),
      requires_key: form.requires_key || null,
    }))
  }
  return (
    <section className="panel unit-detail">
      <div className="panel-head">
        <h2>Unit</h2>
        <ConfirmButton label="Delete unit" confirm="Delete this unit and its steps?"
                       onConfirm={async () => { if (await run(() => api.del(`/units/${unit.id}`))) onDeleted() }} />
      </div>
      <form className="form-grid" onSubmit={save}>
        <div className="field full"><label htmlFor="u-title">Title</label><input id="u-title" type="text" value={form.title} onChange={set('title')} required /></div>
        <div className="field full"><label htmlFor="u-why">Why this unit</label><textarea id="u-why" rows={2} value={form.why} onChange={set('why')} /></div>
        <div className="field full"><label htmlFor="u-outcome">By the end you can</label><textarea id="u-outcome" rows={2} value={form.outcome} onChange={set('outcome')} /></div>
        <div className="field wide"><label htmlFor="u-skills">Skills (comma separated)</label><input id="u-skills" type="text" value={form.skills} onChange={set('skills')} /></div>
        <div className="field wide">
          <label htmlFor="u-requires">Starts after</label>
          <select id="u-requires" value={form.requires_key} onChange={set('requires_key')}>
            <option value="">Nothing: starts when the track gets here</option>
            {allUnits.filter((u) => u.id !== unit.id).map((u) => <option key={u.id} value={u.key}>{u.title}</option>)}
          </select>
        </div>
        <div className="form-actions"><button className="primary" type="submit">Save unit</button></div>
      </form>

      <h3 className="sub-head">Steps</h3>
      <ol className="editor-steps">
        {unit.steps.map((s, i) => (
          <StepEditor key={s.id} step={s} run={run} isFirst={i === 0} isLast={i === unit.steps.length - 1} />
        ))}
      </ol>
      <AddStep unitId={unit.id} run={run} />
    </section>
  )
}

function StepFields({ form, setForm, idPrefix }: { form: StepForm; setForm: (f: StepForm) => void; idPrefix: string }) {
  const set = (k: keyof StepForm) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: k === 'est_minutes' ? Number(e.target.value) : e.target.value })
  return (
    <>
      <div className="field narrow-date">
        <label htmlFor={`${idPrefix}-kind`}>Kind</label>
        <select id={`${idPrefix}-kind`} value={form.kind} onChange={set('kind')}>
          {KINDS.map((k) => <option key={k} value={k}>{KIND_LABEL[k]}</option>)}
        </select>
      </div>
      <div className="field wide"><label htmlFor={`${idPrefix}-title`}>Title</label><input id={`${idPrefix}-title`} type="text" value={form.title} onChange={set('title')} required /></div>
      <div className="field narrow"><label htmlFor={`${idPrefix}-min`}>Minutes</label><input id={`${idPrefix}-min`} type="number" min={1} value={form.est_minutes} onChange={set('est_minutes')} /></div>
      <div className="field full"><label htmlFor={`${idPrefix}-tasks`}>Tasks (one per line)</label><textarea id={`${idPrefix}-tasks`} rows={3} value={form.tasks} onChange={set('tasks')} /></div>
      {form.kind === 'recap' && (
        <div className="field full"><label htmlFor={`${idPrefix}-prompts`}>Recap questions (one per line)</label><textarea id={`${idPrefix}-prompts`} rows={3} value={form.prompts} onChange={set('prompts')} /></div>
      )}
      <div className="field full"><label htmlFor={`${idPrefix}-done`}>Done when</label><input id={`${idPrefix}-done`} type="text" value={form.done_when} onChange={set('done_when')} /></div>
    </>
  )
}

interface StepForm { kind: StepKind; title: string; est_minutes: number; tasks: string; prompts: string; done_when: string }

const toBody = (f: StepForm) => ({ kind: f.kind, title: f.title, est_minutes: f.est_minutes, tasks: lines(f.tasks),
                                   prompts: lines(f.prompts), done_when: f.done_when })

function StepEditor({ step, run, isFirst, isLast }: { step: Step; run: Run; isFirst: boolean; isLast: boolean }) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<StepForm>({ kind: step.kind, title: step.title, est_minutes: step.est_minutes,
                                               tasks: step.tasks.join('\n'), prompts: step.prompts.join('\n'), done_when: step.done_when })
  return (
    <li className={`editor-step ${step.status}`}>
      <div className="editor-step-head">
        <span className={`kind-badge ${step.kind}`}>{KIND_LABEL[step.kind]}</span>
        <button className="link-btn" onClick={() => setOpen(!open)} aria-expanded={open}>{step.title}</button>
        {step.status === 'done' && <span className="muted small">done</span>}
        <span className="editor-arrows">
          <button className="icon-btn" aria-label="Move step up" disabled={isFirst} onClick={() => run(() => api.post(`/steps/${step.id}/move`, { direction: -1 }))}>↑</button>
          <button className="icon-btn" aria-label="Move step down" disabled={isLast} onClick={() => run(() => api.post(`/steps/${step.id}/move`, { direction: 1 }))}>↓</button>
          <ConfirmButton label="Delete" confirm="Delete this step?" onConfirm={() => run(() => api.del(`/steps/${step.id}`))} />
        </span>
      </div>
      {open && (
        <form className="form-grid editor-step-body" onSubmit={async (e) => { e.preventDefault(); if (await run(() => api.patch(`/steps/${step.id}`, toBody(form)))) setOpen(false) }}>
          <StepFields form={form} setForm={setForm} idPrefix={`s${step.id}`} />
          <div className="form-actions"><button className="primary" type="submit">Save step</button></div>
        </form>
      )}
    </li>
  )
}

const EMPTY_STEP: StepForm = { kind: 'learn', title: '', est_minutes: 60, tasks: '', prompts: '', done_when: '' }

function AddStep({ unitId, run }: { unitId: number; run: Run }) {
  const [form, setForm] = useState<StepForm>(EMPTY_STEP)
  const [open, setOpen] = useState(false)
  if (!open) return <button onClick={() => setOpen(true)}>Add a step</button>
  return (
    <form className="form-grid editor-step-body" onSubmit={async (e) => {
      e.preventDefault()
      if (await run(() => api.post('/steps', { unit_id: unitId, ...toBody(form) }))) { setForm(EMPTY_STEP); setOpen(false) }
    }}>
      <StepFields form={form} setForm={setForm} idPrefix="new-step" />
      <div className="form-actions">
        <button className="primary" type="submit">Add step</button>
        <button type="button" className="quiet" onClick={() => setOpen(false)}>Cancel</button>
        <span className="form-status">New steps go before the unit’s recap.</span>
      </div>
    </form>
  )
}

function WholePlan({ run }: { run: Run }) {
  const [templates, setTemplates] = useState<Template[]>([])
  const [template, setTemplate] = useState('blank')
  const [pending, setPending] = useState<unknown>(null)
  const [message, setMessage] = useState('')
  const file = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.get<Template[]>('/auth/templates').then((t) => { setTemplates(t); if (t.length) setTemplate(t[0].slug) }).catch(() => {})
  }, [])

  async function exportPlan() {
    const data = await api.get('/plan/export')
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'study-plan.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  async function pick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    try {
      setPending(JSON.parse(await f.text()))
      setMessage(`Loaded ${f.name}.`)
    } catch {
      setMessage('That file isn’t valid JSON.')
    }
  }

  return (
    <section className="panel">
      <div className="panel-head"><h2>Whole plan</h2></div>
      <p className="muted small">Export your plan to share it or keep a copy. Importing, resetting or building a new plan replaces the plan and deletes your progress and logged hours.</p>
      <p><a href="#build">Build a new plan from a few questions →</a></p>
      <div className="form-grid">
        <div className="form-actions">
          <button onClick={exportPlan}>Export as JSON</button>
          <button onClick={() => file.current?.click()}>Import a JSON plan…</button>
          <input ref={file} type="file" accept="application/json,.json" hidden onChange={pick} />
          {pending !== null && (
            <ConfirmButton label="Replace my plan with it" confirm="Replace your plan and delete your progress?"
                           onConfirm={async () => { if (await run(() => api.post('/plan/import', { plan: pending, confirm: true }))) { setPending(null); setMessage('Plan imported.') } }} />
          )}
          {message && <span className="form-status">{message}</span>}
        </div>
        <div className="form-actions">
          <label htmlFor="reset-template">Start over with</label>
          <select id="reset-template" value={template} onChange={(e) => setTemplate(e.target.value)} style={{ width: 'auto' }}>
            {templates.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
            <option value="blank">An empty plan</option>
          </select>
          <ConfirmButton label="Reset plan" confirm="Delete your plan and progress and start over?"
                         onConfirm={() => run(() => api.post('/plan/reset', { template, confirm: true }))} />
        </div>
      </div>
    </section>
  )
}

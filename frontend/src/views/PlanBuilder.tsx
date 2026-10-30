import { useEffect, useState } from 'react'
import { api, errorText } from '../api'
import type { Shared } from '../App'
import type { BuilderAnswers, BuilderOptions, BuilderSummary } from '../types'

const WEIGHT_LABEL: Record<number, string> = { 3: 'main focus', 2: 'supporting', 1: 'a little each week' }

/** Questions → a generated plan (pure code on the server) → preview → apply. */
export default function PlanBuilder({ plan, changed }: Shared) {
  const [opts, setOpts] = useState<BuilderOptions | null>(null)
  const [answers, setAnswers] = useState<BuilderAnswers>({ goal: 'backend-python', experience: 'some', depth: 'deep', hours_per_week: 8, topics: [] })
  const [preview, setPreview] = useState<BuilderSummary | null>(null)
  const [error, setError] = useState('')
  const [confirming, setConfirming] = useState(false)
  const hasPlan = plan.tracks.length > 0

  useEffect(() => {
    api.get<BuilderOptions>('/builder/options').then((o) => {
      setOpts(o)
      setAnswers((a) => ({ ...a, topics: Object.keys(o.goals.find((g) => g.key === a.goal)?.topics ?? {}) }))
    }).catch((e) => setError(errorText(e)))
  }, [])

  // Any change to the answers makes the old preview stale.
  useEffect(() => { setPreview(null); setConfirming(false) }, [answers])

  if (!opts) return error ? <p className="banner error">{error}</p> : <p className="muted">Loading…</p>

  const goal = opts.goals.find((g) => g.key === answers.goal)!
  const set = (patch: Partial<BuilderAnswers>) => setAnswers({ ...answers, ...patch })
  const pickGoal = (key: string) => set({ goal: key, topics: Object.keys(opts.goals.find((g) => g.key === key)!.topics) })
  const toggleTopic = (key: string) =>
    set({ topics: answers.topics.includes(key) ? answers.topics.filter((t) => t !== key) : [...answers.topics, key] })

  async function showPreview(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      setPreview(await api.post<BuilderSummary>('/builder/preview', answers))
    } catch (err) {
      setError(errorText(err))
    }
  }

  async function apply() {
    setError('')
    try {
      await api.post('/plan/build', { answers, confirm: hasPlan })
      changed()
      window.location.hash = 'today'
    } catch (err) {
      setError(errorText(err))
    }
  }

  return (
    <div className="stack">
      <section className="panel intro">
        <h2>Build a plan</h2>
        <p>
          Answer a few questions and Study Ledger puts together a plan from its topic library: units in order, free
          resources, projects to build and a weekly target per track. Afterwards you can change anything in <a href="#edit">Edit plan</a>.
        </p>
      </section>

      <form className="panel builder" onSubmit={showPreview}>
        <fieldset>
          <legend>What's your goal?</legend>
          <div className="choice-grid">
            {opts.goals.map((g) => (
              <label key={g.key} className={`template-option ${answers.goal === g.key ? 'on' : ''}`}>
                <input type="radio" name="goal" checked={answers.goal === g.key} onChange={() => pickGoal(g.key)} />
                <span><strong>{g.label}</strong></span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="form-grid">
          <fieldset className="field wide">
            <legend>Your experience</legend>
            <div className="segmented">
              {opts.experience.map((x) => (
                <button type="button" key={x.key} className={answers.experience === x.key ? 'active' : ''}
                        onClick={() => set({ experience: x.key })}>{x.label}</button>
              ))}
            </div>
          </fieldset>
          <fieldset className="field wide">
            <legend>How deep</legend>
            <div className="segmented">
              {opts.depth.map((x) => (
                <button type="button" key={x.key} className={answers.depth === x.key ? 'active' : ''}
                        onClick={() => set({ depth: x.key })}>{x.label}</button>
              ))}
            </div>
          </fieldset>
          <div className="field narrow-date">
            <label htmlFor="b-hours">Hours a week</label>
            <input id="b-hours" type="number" min={1} max={60} step={0.5} value={answers.hours_per_week}
                   onChange={(e) => set({ hours_per_week: Number(e.target.value) })} />
          </div>
        </div>

        <fieldset>
          <legend>What do you want to learn?</legend>
          <p className="muted small">Ticked topics come from your goal. Add or remove any.</p>
          <div className="choice-grid">
            {opts.topics.map((t) => {
              const weight = goal.topics[t.key]
              return (
                <label key={t.key} className={`template-option ${answers.topics.includes(t.key) ? 'on' : ''}`}>
                  <input type="checkbox" checked={answers.topics.includes(t.key)} onChange={() => toggleTopic(t.key)} />
                  <span>
                    <strong>{t.name}</strong>
                    <span className="muted small">{t.goal}{weight ? ` · ${WEIGHT_LABEL[weight]}` : ''}</span>
                  </span>
                </label>
              )
            })}
          </div>
        </fieldset>

        <div className="form-actions">
          <button className="primary" type="submit" disabled={answers.topics.length === 0}>Preview my plan</button>
          {answers.topics.length === 0 && <span className="form-status">Pick at least one topic.</span>}
          {error && <span className="form-status error-text" role="alert">{error}</span>}
        </div>
      </form>

      {preview && (
        <section className="panel">
          <div className="panel-head">
            <h2>Your plan</h2>
            <span className="muted small">about {preview.weeks} weeks at {answers.hours_per_week} h a week · {preview.projects} projects</span>
          </div>
          <ul className="builder-preview">
            {preview.tracks.map((t) => (
              <li key={t.key} style={{ '--track': t.color } as React.CSSProperties}>
                <div className="builder-track-head">
                  <span className="track-name-sm"><span className="dot" />{t.name}</span>
                  <span className="mono small muted">{t.hours_per_week} h/wk · {t.units} units · ~{t.weeks} wks</span>
                </div>
                <ol className="small muted">{t.unit_titles.map((u) => <li key={u}>{u}</li>)}</ol>
              </li>
            ))}
          </ul>
          <div className="form-actions">
            {!hasPlan && <button className="primary" onClick={apply}>Use this plan</button>}
            {hasPlan && !confirming && <button className="primary" onClick={() => setConfirming(true)}>Replace my plan with this</button>}
            {hasPlan && confirming && (
              <span className="confirm">
                <span className="small">This deletes your current plan, progress and logged hours.</span>
                <button className="danger small-btn" onClick={apply}>Replace it</button>
                <button className="quiet small-btn" onClick={() => setConfirming(false)}>Cancel</button>
              </span>
            )}
          </div>
        </section>
      )}
    </div>
  )
}

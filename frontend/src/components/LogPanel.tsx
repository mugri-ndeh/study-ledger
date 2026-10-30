import { useState } from 'react'
import { api, errorText, localDay } from '../api'
import type { Step } from '../types'

/**
 * Logs time against a track's current step. There is no topic picker on purpose:
 * the plan decides what comes next, and finishing a step moves the track forward.
 */
export default function LogPanel({ trackId, step, suggested, changed }: {
  trackId: number
  step: Step
  suggested?: number
  changed: () => void
}) {
  const [duration, setDuration] = useState(String((suggested || 60) / 60))
  const [day, setDay] = useState(localDay())
  const [note, setNote] = useState('')
  const [finished, setFinished] = useState(false)
  const [rating, setRating] = useState<number | null>(null)
  const [reflection, setReflection] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const isRecap = step.kind === 'recap'
  const id = `log-${trackId}`

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const minutes = Math.round(parseFloat(duration) * 60)
    if (!minutes || minutes <= 0) return setMessage('Enter the time in hours, for example 1.5.')
    if (finished && isRecap && !rating) return setMessage('Rate your confidence to finish the recap.')
    try {
      await api.post('/sessions', { day, minutes, track_id: trackId, note, finish_step: finished, rating, reflection })
      setMessage(finished ? 'Logged. On to the next step.' : 'Logged.')
      setNote('')
      setFinished(false)
      setRating(null)
      setReflection('')
      changed()
    } catch (err) {
      setMessage(errorText(err))
    }
  }

  async function finishWithoutTime() {
    if (isRecap && !rating) return setMessage('Rate your confidence to finish the recap.')
    try {
      await api.post(`/steps/${step.id}/complete`, { day, rating, reflection })
      setMessage('Marked done.')
      changed()
    } catch (err) {
      setMessage(errorText(err))
    }
  }

  return (
    <form className="log-panel" onSubmit={submit}>
      <div className="log-row">
        <div className="field narrow">
          <label htmlFor={`${id}-hours`}>Hours</label>
          <input id={`${id}-hours`} type="number" min="0.25" step="0.25" value={duration} onChange={(e) => setDuration(e.target.value)} />
        </div>
        <div className="field narrow-date">
          <label htmlFor={`${id}-day`}>Day</label>
          <input id={`${id}-day`} type="date" max={localDay()} value={day} onChange={(e) => setDay(e.target.value)} />
        </div>
        <div className="field wide">
          <label htmlFor={`${id}-note`}>What did you do?</label>
          <input id={`${id}-note`} type="text" value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. lectures 0-1, wrote the guessing game" />
        </div>
      </div>
      <label className="check finish-check">
        <input id={`${id}-finished`} type="checkbox" checked={finished} onChange={(e) => setFinished(e.target.checked)} />
        I finished this step (moves the track to the next one)
      </label>
      {isRecap && (
        <div className="recap-fields">
          <div className="rating" role="radiogroup" aria-label="Confidence from 1 to 5">
            <span className="label">Confidence</span>
            {[1, 2, 3, 4, 5].map((n) => (
              <button type="button" key={n} role="radio" aria-checked={rating === n} className={rating === n ? 'on' : ''} onClick={() => setRating(n)}>{n}</button>
            ))}
            <span className="muted small">1 lost · 3 with notes · 5 could teach it</span>
          </div>
          <label htmlFor={`${id}-reflection`}>Weak spots and what to revisit</label>
          <textarea id={`${id}-reflection`} rows={2} value={reflection} onChange={(e) => setReflection(e.target.value)} />
        </div>
      )}
      <div className="form-actions">
        <button type="submit" className="primary">Log session</button>
        <button type="button" className="quiet" onClick={finishWithoutTime} title="For steps you already know">Already know this, mark done</button>
        {message && <span className="form-status" role="status">{message}</span>}
      </div>
    </form>
  )
}

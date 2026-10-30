import { useEffect, useState } from 'react'
import { api, errorText } from '../api'
import type { Template, User } from '../types'

type Mode = 'login' | 'signup'

/** After sign-up with "build", the app opens the plan builder. */
export default function Auth({ onAuthed }: { onAuthed: (u: User, next?: string) => void }) {
  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [templates, setTemplates] = useState<Template[]>([])
  const [template, setTemplate] = useState('build')
  const [upload, setUpload] = useState<{ name: string; plan: unknown } | null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get<Template[]>('/auth/templates')
      .then(setTemplates)
      .catch(() => setTemplates([]))
  }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setMessage('')
    try {
      if (mode === 'login') {
        onAuthed(await api.post<User>('/auth/login', { email, password }))
        return
      }
      if (template === 'upload' && !upload) throw new Error('Choose a plan file first.')
      const body = template === 'build' ? { template: 'blank' }
        : template === 'upload' ? { template: 'upload', plan: upload!.plan }
        : { template }
      const user = await api.post<User>('/auth/signup', { email, password, display_name: name, ...body })
      onAuthed(user, template === 'build' ? 'build' : undefined)
    } catch (err) {
      setMessage(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  async function pickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (!f) return
    try {
      setUpload({ name: f.name, plan: JSON.parse(await f.text()) })
      setMessage('')
    } catch {
      setUpload(null)
      setMessage('That file isn’t valid JSON.')
    }
  }

  const option = (value: string, title: string, text: string, extra?: React.ReactNode) => (
    <label key={value} className={`template-option ${template === value ? 'on' : ''}`}>
      <input type="radio" name="template" value={value} checked={template === value} onChange={() => setTemplate(value)} />
      <span><strong>{title}</strong><span className="muted small">{text}</span>{template === value && extra}</span>
    </label>
  )

  return (
    <div className="auth-wrap">
      <section className="panel auth-card">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">∑</span>
          <div>
            <h1>Study Ledger</h1>
            <p className="tagline">A study plan you follow one step at a time.</p>
          </div>
        </div>

        <div className="segmented" role="group" aria-label="Log in or sign up">
          <button className={mode === 'login' ? 'active' : ''} onClick={() => { setMode('login'); setMessage('') }}>Log in</button>
          <button className={mode === 'signup' ? 'active' : ''} onClick={() => { setMode('signup'); setMessage('') }}>Create account</button>
        </div>

        <form className="form-grid" onSubmit={submit}>
          {mode === 'signup' && (
            <div className="field full">
              <label htmlFor="auth-name">Your name</label>
              <input id="auth-name" type="text" value={name} onChange={(e) => setName(e.target.value)} required maxLength={80} autoComplete="name" />
            </div>
          )}
          <div className="field full">
            <label htmlFor="auth-email">Email</label>
            <input id="auth-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
          </div>
          <div className="field full">
            <label htmlFor="auth-password">Password{mode === 'signup' ? ' (at least 10 characters)' : ''}</label>
            <input id="auth-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
                   minLength={mode === 'signup' ? 10 : undefined} autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} />
          </div>

          {mode === 'signup' && (
            <fieldset className="field full template-pick">
              <legend>Start with</legend>
              {option('build', 'Build a plan for me', 'Answer a few questions (goal, experience, hours a week) and get a plan you can edit.')}
              {templates.map((t) => option(t.slug, `Starter: ${t.name}`, t.description))}
              {option('upload', 'Upload a plan file', 'A plan exported from Study Ledger (JSON).',
                <input className="file-input" type="file" accept="application/json,.json" onChange={pickFile} aria-label="Plan file" />)}
              {option('blank', 'An empty plan', 'Build your own tracks and units in “Edit plan”.')}
            </fieldset>
          )}

          <div className="form-actions">
            <button className="primary" type="submit" disabled={busy}>{mode === 'login' ? 'Log in' : 'Create account'}</button>
            {message && <span className="form-status error-text" role="alert">{message}</span>}
          </div>
        </form>
      </section>
    </div>
  )
}

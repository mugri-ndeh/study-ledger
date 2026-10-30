import { useCallback, useEffect, useState } from 'react'
import { ApiError, api, errorText, setUnauthorizedHandler } from './api'
import type { Plan, Unit, User } from './types'
import Auth from './views/Auth'
import PlanEditor from './views/PlanEditor'
import PlanBuilder from './views/PlanBuilder'
import Today from './views/Today'
import PlanView from './views/PlanView'
import RoadmapView from './views/RoadmapView'
import Progress from './views/Progress'
import Projects from './views/Projects'
import Market from './views/Market'
import History from './views/History'

const VIEWS = [
  { id: 'today', label: 'Today' },
  { id: 'plan', label: 'Study plan' },
  { id: 'roadmap', label: 'Roadmap' },
  { id: 'progress', label: 'Strengths' },
  { id: 'projects', label: 'Projects' },
  { id: 'market', label: 'Market' },
  { id: 'history', label: 'History' },
  { id: 'edit', label: 'Edit plan' },
  { id: 'build', label: 'Build a plan', hidden: true },
] as const
type ViewId = (typeof VIEWS)[number]['id']

function viewFromHash(): ViewId {
  const id = window.location.hash.slice(1)
  return (VIEWS.find((v) => v.id === id)?.id ?? 'today') as ViewId
}

export interface Shared {
  plan: Plan
  user: User
  /** Bumps after any write so every view refetches what it shows. */
  version: number
  changed: () => void
  openUnit: (u: Unit) => void
  selectedUnit: string | null
}

export default function App() {
  // undefined: still checking the session; null: logged out.
  const [user, setUser] = useState<User | null | undefined>(undefined)
  const [view, setView] = useState<ViewId>(viewFromHash)
  const [plan, setPlan] = useState<Plan | null>(null)
  const [version, setVersion] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [selectedUnit, setSelectedUnit] = useState<string | null>(null)

  useEffect(() => {
    const onHash = () => setView(viewFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => { setUser(null); setPlan(null) })
    api.get<User>('/auth/me')
      .then(setUser)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) setUser(null)
        else setError(errorText(e))
      })
  }, [])

  useEffect(() => {
    if (!user) return
    api.get<Plan>('/plan')
      .then((p) => { setPlan(p); setError(null) })
      .catch((e) => { if (!(e instanceof ApiError && e.status === 401)) setError(errorText(e)) })
  }, [version, user])

  const changed = useCallback(() => setVersion((v) => v + 1), [])
  const openUnit = useCallback((u: Unit) => {
    setSelectedUnit(u.key)
    window.location.hash = 'plan'
  }, [])

  async function logout() {
    await api.post('/auth/logout', {}).catch(() => {})
    setUser(null)
    setPlan(null)
  }

  if (user === null) {
    return <Auth onAuthed={(u, next) => {
      if (next) window.location.hash = next
      setUser(u); setError(null); setVersion((v) => v + 1)
    }} />
  }
  if (user === undefined) {
    return <div className="shell">{error ? <div className="banner error">{error}</div> : <p className="muted">Loading…</p>}</div>
  }

  const emptyPlan = plan !== null && plan.tracks.length === 0

  return (
    <div className="shell">
      <header className="masthead">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">∑</span>
          <div>
            <h1>Study Ledger</h1>
            <p className="tagline">{plan && plan.tracks.length ? plan.tracks.map((t) => t.name).join(' · ') : 'Your study plan'}</p>
          </div>
          <div className="account">
            <span className="muted small">{user.display_name}</span>
            <button className="quiet small-btn" onClick={logout}>Log out</button>
          </div>
        </div>
        <nav className="tabs" aria-label="Sections">
          {VIEWS.filter((v) => !('hidden' in v)).map((v) => (
            <a key={v.id} href={`#${v.id}`} className={v.id === view ? 'tab active' : 'tab'} aria-current={v.id === view ? 'page' : undefined}>{v.label}</a>
          ))}
        </nav>
      </header>

      {error && <div className="banner error">{error}</div>}
      {!plan && !error && <p className="muted">Loading your plan…</p>}

      {plan && (
        <main>
          {(() => {
            const shared: Shared = { plan, user, version, changed, openUnit, selectedUnit }
            if (emptyPlan && !['edit', 'market', 'build'].includes(view)) {
              return (
                <section className="panel intro">
                  <h2>Your plan is empty</h2>
                  <p>
                    <a href="#build">Answer a few questions</a> and get a plan made for you, or build your own
                    in <a href="#edit">Edit plan</a>.
                  </p>
                </section>
              )
            }
            switch (view) {
              case 'today': return <Today {...shared} />
              case 'plan': return <PlanView {...shared} />
              case 'roadmap': return <RoadmapView {...shared} />
              case 'progress': return <Progress {...shared} />
              case 'projects': return <Projects {...shared} />
              case 'market': return <Market {...shared} />
              case 'history': return <History {...shared} />
              case 'edit': return <PlanEditor {...shared} />
              case 'build': return <PlanBuilder {...shared} />
            }
          })()}
        </main>
      )}
    </div>
  )
}

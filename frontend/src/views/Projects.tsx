import { useEffect, useState } from 'react'
import { api } from '../api'
import type { Shared } from '../App'
import type { Difficulty, Project, ProjectStatus } from '../types'

const LEVELS: Difficulty[] = ['beginner', 'intermediate', 'advanced']
const LEVEL_LABEL: Record<Difficulty, string> = { beginner: 'Beginner', intermediate: 'Intermediate', advanced: 'Advanced' }
const STATUS_LABEL: Record<ProjectStatus, string> = { idea: 'Not started', building: 'Building', shipped: 'Shipped' }

export default function Projects({ plan, version, changed, openUnit }: Shared) {
  const [projects, setProjects] = useState<Project[]>([])
  const [level, setLevel] = useState<'all' | Difficulty>('all')
  const [source, setSource] = useState<'all' | 'plan' | 'extra'>('all')
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    api.get<Project[]>('/projects').then(setProjects).catch(() => setProjects([]))
  }, [version])

  const shown = projects.filter((p) => (level === 'all' || p.difficulty === level) &&
    (source === 'all' || (source === 'plan' ? p.unit_key : !p.unit_key)))
  const count = (d: Difficulty, s: ProjectStatus) => projects.filter((p) => p.difficulty === d && p.status === s).length

  return (
    <div className="stack">
      <section className="panel intro">
        <p>
          Projects are where the learning sticks. Projects marked <strong>In the plan</strong> are the build step at the
          end of a unit, so you reach them in order. <strong>Extras</strong> are for when you want more practice at a level,
          or something to show in a particular application.
        </p>
        <div className="level-summary">
          {LEVELS.map((d) => {
            const total = projects.filter((p) => p.difficulty === d).length
            return (
              <div key={d} className={`level-card ${d}`}>
                <span className="stat-label">{LEVEL_LABEL[d]}</span>
                <span className="mono">{count(d, 'shipped')}<small> / {total} shipped</small></span>
                <div className="stacked-meter" aria-hidden="true">
                  <span className="shipped" style={{ flex: count(d, 'shipped') }} />
                  <span className="building" style={{ flex: count(d, 'building') }} />
                  <span className="idea" style={{ flex: count(d, 'idea') }} />
                </div>
              </div>
            )
          })}
        </div>
      </section>

      <div className="filter-bar">
        <div className="segmented" role="group" aria-label="Difficulty">
          {(['all', ...LEVELS] as const).map((d) => (
            <button key={d} className={level === d ? 'active' : ''} onClick={() => setLevel(d)}>{d === 'all' ? 'All levels' : LEVEL_LABEL[d]}</button>
          ))}
        </div>
        <div className="segmented" role="group" aria-label="Source">
          {(['all', 'plan', 'extra'] as const).map((x) => (
            <button key={x} className={source === x ? 'active' : ''} onClick={() => setSource(x)}>{x === 'all' ? 'All' : x === 'plan' ? 'In the plan' : 'Extras'}</button>
          ))}
        </div>
        <button className="primary" onClick={() => setAdding(!adding)}>{adding ? 'Cancel' : 'Add your own'}</button>
      </div>

      {adding && <NewProject onDone={() => { setAdding(false); changed() }} />}

      <div className="project-grid">
        {shown.map((p) => {
          const unit = plan.units.find((u) => u.key === p.unit_key)
          const track = plan.tracks.find((t) => t.id === p.unit_track)
          return <ProjectCard key={p.id} p={p} color={track?.color} unitTitle={unit?.title} onOpenUnit={unit ? () => openUnit(unit) : undefined} changed={changed} />
        })}
      </div>
    </div>
  )
}

function ProjectCard({ p, color, unitTitle, onOpenUnit, changed }: {
  p: Project; color?: string; unitTitle?: string; onOpenUnit?: () => void; changed: () => void
}) {
  const [repo, setRepo] = useState(p.repo_url)
  const [demo, setDemo] = useState(p.demo_url)
  const [showMore, setShowMore] = useState(false)

  async function save(field: 'repo_url' | 'demo_url', value: string) {
    if (value !== p[field]) { await api.patch(`/projects/${p.id}`, { [field]: value }); changed() }
  }

  return (
    <article className={`project-card ${p.status}`} style={{ '--track': color ?? 'var(--muted)' } as React.CSSProperties}>
      <header>
        <span className={`level-badge ${p.difficulty}`}>{LEVEL_LABEL[p.difficulty]}</span>
        <span className="mono small muted">~{p.est_hours} h</span>
      </header>
      <h3>{p.title}</h3>
      <p className="card-desc">{p.description}</p>
      {unitTitle
        ? <button className="link-btn small" onClick={onOpenUnit}>In the plan: end of “{unitTitle}”</button>
        : <span className="muted small">Extra project</span>}
      <div className="tags">{p.skills.map((s) => <span key={s} className="tag">{s}</span>)}</div>

      <button className="link-btn small" onClick={() => setShowMore(!showMore)} aria-expanded={showMore}>{showMore ? 'Hide' : 'Show'} requirements</button>
      {showMore && (
        <div className="reqs">
          <span className="label">Must have</span>
          <ul>{p.features.map((f) => <li key={f}>{f}</li>)}</ul>
          {p.stretch.length > 0 && <><span className="label">Stretch goals</span><ul>{p.stretch.map((f) => <li key={f}>{f}</li>)}</ul></>}
          <label htmlFor={`repo-${p.id}`}>Repository</label>
          <input id={`repo-${p.id}`} value={repo} placeholder="https://github.com/…" onChange={(e) => setRepo(e.target.value)} onBlur={() => save('repo_url', repo)} />
          <label htmlFor={`demo-${p.id}`}>Demo</label>
          <input id={`demo-${p.id}`} value={demo} placeholder="https://…" onChange={(e) => setDemo(e.target.value)} onBlur={() => save('demo_url', demo)} />
        </div>
      )}

      <footer>
        <select id={`status-${p.id}`} aria-label="Status" value={p.status}
                onChange={async (e) => { await api.patch(`/projects/${p.id}`, { status: e.target.value }); changed() }}>
          {(Object.keys(STATUS_LABEL) as ProjectStatus[]).map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
        </select>
        {p.repo_url && <a href={p.repo_url} target="_blank" rel="noreferrer" className="small">Repo</a>}
        {p.demo_url && <a href={p.demo_url} target="_blank" rel="noreferrer" className="small">Demo</a>}
      </footer>
    </article>
  )
}

function NewProject({ onDone }: { onDone: () => void }) {
  const [title, setTitle] = useState('')
  const [difficulty, setDifficulty] = useState<Difficulty>('intermediate')
  const [description, setDescription] = useState('')
  const [features, setFeatures] = useState('')
  const [skills, setSkills] = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    await api.post('/projects', {
      title: title.trim(), difficulty, description,
      features: features.split('\n').map((s) => s.trim()).filter(Boolean),
      skills: skills.split(',').map((s) => s.trim()).filter(Boolean),
    })
    onDone()
  }

  return (
    <form className="panel form-grid" onSubmit={submit}>
      <div className="field wide"><label htmlFor="np-title">Project name</label><input id="np-title" value={title} onChange={(e) => setTitle(e.target.value)} /></div>
      <div className="field"><label htmlFor="np-level">Level</label>
        <select id="np-level" value={difficulty} onChange={(e) => setDifficulty(e.target.value as Difficulty)}>
          {LEVELS.map((d) => <option key={d} value={d}>{LEVEL_LABEL[d]}</option>)}
        </select>
      </div>
      <div className="field full"><label htmlFor="np-desc">What it does</label><textarea id="np-desc" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} /></div>
      <div className="field full"><label htmlFor="np-features">Must-have features (one per line)</label><textarea id="np-features" rows={3} value={features} onChange={(e) => setFeatures(e.target.value)} /></div>
      <div className="field full"><label htmlFor="np-skills">Skills (comma-separated)</label><input id="np-skills" value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="Python, FastAPI" /></div>
      <div className="form-actions"><button type="submit" className="primary">Add project</button></div>
    </form>
  )
}

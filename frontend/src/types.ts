export type StepKind = 'learn' | 'practice' | 'build' | 'recap'
export type UnitState = 'done' | 'current' | 'blocked' | 'upcoming'
export type Outcome = '' | 'solo' | 'hint' | 'solution'
export type Difficulty = 'beginner' | 'intermediate' | 'advanced'
export type ProjectStatus = 'idea' | 'building' | 'shipped'

export interface Track {
  id: number
  key: string
  name: string
  goal: string
  weekly_target_hours: number
  color: string
  position: number
}

export interface UnitRef { key: string; title: string; track_id: number }

export interface TrackState extends Track {
  current_step_id: number | null
  current_unit_id: number | null
  blocked_by: UnitRef | null
  complete: boolean
  steps_done: number
  steps_total: number
  est_minutes_done: number
  est_minutes_total: number
  last_done_step_id: number | null
}

export interface Resource {
  id: number
  unit_id: number
  step_id: number | null
  title: string
  url: string
  kind: string
  done: boolean
  outcome: Outcome
}

export interface Step {
  id: number
  unit_id: number
  track_id: number
  seq: number
  kind: StepKind
  title: string
  tasks: string[]
  prompts: string[]
  done_when: string
  est_minutes: number
  status: 'todo' | 'done'
  started_on: string | null
  completed_on: string | null
  rating: number | null
  reflection: string
  logged_minutes: number
  resources?: Resource[]
}

export interface Unit {
  id: number
  key: string
  track_id: number
  seq: number
  title: string
  why: string
  outcome: string
  skills: string[]
  requires_key: string | null
  project_key: string | null
  steps_total: number
  steps_done: number
  est_minutes: number
  logged_minutes: number
  complete: boolean
  rating: number | null
  state: UnitState
  plan_start_week: number
  plan_end_week: number
  steps: Step[]
}

export interface Plan {
  plan_start: string
  tracks: TrackState[]
  units: Unit[]
}

export interface PlanItem {
  track_id: number
  week_minutes: number
  target_minutes: number
  deficit: number
  blocked_by: UnitRef | null
  slot: 'today' | 'later' | 'done_for_week' | 'blocked'
  suggested_minutes: number
  step: Step
  unit: { id: number; key: string; title: string; seq: number }
}

export interface Dashboard {
  today: string
  week_start: string
  plan_start: string
  current_streak: number
  longest_streak: number
  studied_today: boolean
  total_minutes: number
  last7_minutes: number
  week_minutes: number
  week_target_minutes: number
  tracks: (TrackState & { week_minutes: number; total_minutes: number; projected_finish: string })[]
  today_plan: PlanItem[]
  heatmap: { day: string; minutes: number }[]
  weekly: { week_start: string; tracks: Record<string, number> }[]
  burnup: { week_start: string; actual_minutes: number; planned_minutes: number }[]
}

export interface Strengths {
  tracks: { id: number; name: string; color: string; confidence: number | null; rated_units: number; coverage: number }[]
  patterns: { key: string; title: string; total: number; solo: number; hint: number; solution: number; untouched: number; score: number; rating: number | null }[]
  skills: { name: string; confidence: number; units: number }[]
  strong: RatedUnit[]
  weak: RatedUnit[]
  timeline: RatedUnit[]
}

export interface RatedUnit {
  key: string
  title: string
  track_id: number
  rating: number
  reflection: string
  completed_on: string | null
}

export interface Session {
  id: number
  day: string
  minutes: number
  track_id: number
  step_id: number | null
  step_title: string | null
  step_kind: StepKind | null
  unit_title: string | null
  note: string
}

export interface Project {
  id: number
  key: string
  title: string
  difficulty: Difficulty
  est_hours: number
  skills: string[]
  description: string
  features: string[]
  stretch: string[]
  unit_key: string | null
  unit_title: string | null
  unit_track: number | null
  status: ProjectStatus
  repo_url: string
  demo_url: string
  notes: string
}

export interface Skill {
  name: string
  pct_all: number
  pct_open: number
  median_usd: number | null
  my_level: number
  units_total: number
  units_done: number
  delta_all: number | null
  delta_open: number | null
}

export interface SkillsResponse {
  snapshot_date: string | null
  /** 'career-ops' (the original scan) or 'boards' (live job boards). */
  source: string | null
  /** The previous snapshot from the same source; deltas compare against it. */
  previous_date: string | null
  postings: number
  open_postings: number
  companies: number
  skills: Skill[]
}

export interface MarketPoint {
  taken_on: string
  source: string
  postings: number
  open_postings: number
  pct_all?: number | null
  pct_open?: number | null
  median_usd?: number | null
}

export interface MarketStatus {
  running: string | null
  last_error: string | null
  last_finished: string | null
  last_refresh: string | null
  can_refresh: boolean
}

export interface User {
  id: number
  email: string
  display_name: string
  plan_start: string
  is_admin: boolean
}

export interface Template {
  slug: string
  name: string
  description: string
  tracks: number
  units: number
}

export interface BuilderOptions {
  goals: { key: string; label: string; topics: Record<string, number> }[]
  experience: { key: string; label: string }[]
  depth: { key: string; label: string }[]
  topics: { key: string; name: string; goal: string; units: number }[]
}

export interface BuilderAnswers {
  goal: string
  experience: string
  depth: string
  hours_per_week: number
  topics: string[]
}

export interface BuilderSummary {
  tracks: { key: string; name: string; color: string; hours_per_week: number; units: number; steps: number;
            total_hours: number; weeks: number | null; unit_titles: string[] }[]
  projects: number
  weeks: number
}

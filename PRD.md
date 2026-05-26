# Reality Check — Product Requirements Document

**Product name:** Reality Check for Startup/Product Philosophies

**One-line pitch:** Startup and product advice is consumed universally but works conditionally. Reality Check stress-tests advice against operational reality.

**Status:** Backend + frontend implemented — next step: Replit deploy (as-is, no rebuild)  
**Last updated:** 2026-05-26

---

## Problem

Two failures in the startup/product ecosystem:

1. **Information → action gap** — People consume podcasts, newsletters, frameworks, and advice but rarely operationalize them effectively.
2. **Context collapse** — The same advice works in one org and fails in another, but consumers rarely see *why*.

---

## Product thesis

The RIGHT experience combines **both**:

- **Lenny hook** — user enters through a philosophy, framework, or aspiration they already believe
- **Reality engine** — system surfaces where that philosophy breaks in *their* org under pressure

The user should **never** feel: *"I'm being organizationally analyzed."*

The user **should** feel: *"I'm stress-testing startup advice against reality."*

**NOT building:** an "organizational intelligence platform."

**Building:** Reality Check for Startup/Product Philosophies — powered by organizational diagnostics, operational distortions, and AI-era pressure simulations (in service of stress-testing advice, not auditing orgs).

---

## Target user

PMs, founders, and leaders who consume Lenny's Podcast / Newsletter content and are trying to apply a specific belief or playbook inside their org.

---

## Core user journey (5 steps)

### Step 1 — Philosophy / Aspiration Input (Advice layer)

User selects or describes a philosophy, framework, startup belief, or AI transformation goal.

**Entry examples:**

- "We want empowered teams."
- "We want AI-native PMs."
- "We want faster experimentation."
- "We want founder mode."
- "We want to move faster with AI."

**Launch philosophy cards (MVP):**

| Card | Label |
|------|-------|
| `move_fast` | Move fast / ship daily |
| `empower_teams` | Empower teams / PMs |
| `ai_first` | AI-first org |
| `founder_mode` | Founder mode |
| `high_experimentation` | High experimentation culture |
| `ai_native_pms` | AI-native PMs |
| `design_led` | Design-led cohesion |
| `minimal_process` | Kill PRDs / minimal process |

**Purpose:** Connects to the original Lenny ecosystem. User arrives with intent they already have — not a blank search box.

---

### Step 2 — Organizational Reality Mapping (Context layer)

Hybrid calibration (5–6 questions per philosophy):

- **4 universal:** roadmap override, priority chaos, revenue pressure, bottleneck
- **1 philosophy-specific:** tailored to the belief chosen in Step 1 (15 unique questions)
- **1 conditional:** AI reality — only for AI-related philosophies
- **Optional:** user role (Founder/CEO, PM, eng/design leader, other)
- **Optional:** stage, size, B2B/B2C (LLM context today)

**Internal engine (not shown to user):** archetypes, distortions, bottlenecks, pressure patterns from the intelligence corpus.

**Purpose:** Map the user's org to operational reality signals without feeling like a diagnostic audit.

---

### Step 3 — Reality Diagnosis (Contradiction layer) — **THE EMOTIONAL HOOK**

System reveals:

- Organizational distortions
- Hidden assumptions
- Likely collapse patterns
- Operational mismatch between aspiration and reality

**Example output:**

> "You want empowered teams, but your org recentralizes decisions under revenue pressure."

**Purpose:** Named tension between what they believe and what their org actually does. This is the magic moment.

---

### Step 4 — Pressure Simulation (Reality layer)

"What happens when…"

- AI velocity increases?
- Enterprise escalation occurs?
- Roadmap chaos begins?
- Revenue misses?
- Headcount pressure hits?

**Purpose:** Memorable, forward-looking stress test — not retrospective blame.

---

### Step 5 — Operational Adaptation (Action layer)

**NOT:** "Best practices."

**YES:** "What version of this philosophy ACTUALLY works in your environment?"

**Output structure:**

- **Keep** — what's still true from the philosophy
- **Modify** — what must be constrained for this org
- **Add** — what this org type needs that the philosophy omits
- **Watch for** — failure modes when implementing

**Purpose:** Closes the information → action gap with *conditional* guidance grounded in corpus evidence.

---

## Tone & copy guardrails

| Do | Don't |
|----|-------|
| "Stress-test **founder mode** against your reality" | "Analyze your organization" |
| "You want X, but under pressure your org Y" | "Your org is dysfunctional" |
| "Your version of empowered teams" | "Best practices for empowered teams" |
| Cite Lenny guests with real quotes | Invent advice or fake citations |
| "We can't answer X from this corpus" when coverage is weak | Hallucinate a solution |

---

## Data & intelligence layer

| Asset | Role |
|-------|------|
| [`reality-check-intelligence.json`](reality-check-intelligence.json) | 458 operational intelligence objects — evidence, quotes, failure modes |
| [`normalized-intelligence.json`](normalized-intelligence.json) | 45 meta-patterns — routing, collapse patterns, contradictions |
| Philosophy registry | Maps user-facing aspirations → meta-patterns |
| Calibration schema | Maps org answers → distortion tags → retrieval boost |

**Retrieval flow:** Philosophy → org distortions → meta-patterns → intelligence objects → LLM synthesis (grounded, structured).

**Gap handling:** When confidence is low, say so. Offer adjacent patterns as weak match. Never invent sources.

---

## Backend / API (MVP)

**Implementation:** Done — see [`REALITY_CHECK_API.md`](REALITY_CHECK_API.md) for setup, testing checklist, and troubleshooting.

| Endpoint | UX step |
|----------|---------|
| `GET /api/philosophies` | Step 1 |
| `GET /api/calibration/questions` | Step 2 |
| `POST /api/stress-test` | Steps 3–5 (single call after Steps 1–2 collected) |
| `POST /api/stress-test/preview` | Retrieval debug (no LLM) |
| `GET /api/health` | Corpus status |

**Response schema (`RealityCheckResponse`) — transformation report:**

- `confidence`, `confidence_reason`
- `transformation_name`, `philosophy_label`
- `what_youre_trying_to_change` — `goal`, `operational_meaning`
- `environment_readiness` — `supporting_conditions`, `resisting_conditions`, `readiness_summary`
- `first_bottleneck` — `bottleneck`, `what_teams_usually_do_next`, `unintended_effect`
- `how_to_drive_change` — `start_with`, `avoid`, `introduce_later`
- `what_to_measure` — `positive_signals`, `warning_signs`
- `when_to_course_correct` — `course_correct_if`, `typical_adaptation`
- `where_this_works_best` — `conditions`
- `core_organizational_insight`
- `sources`, `sources_more` — corpus citations (`intelligence_id`)
- `gap_notice` — when corpus coverage is insufficient

**Philosophy relevance:** Retrieval and synthesis are scoped to the selected philosophy's linked patterns and keywords (`reality_check/engine/relevance.py`). Automated tests in `tests/test_philosophy_relevance.py` guard against cross-topic bleed.

**Results UI sections (GroundWork):** Hero → What You're Trying To Change → Environment Readiness → First Bottleneck → How To Drive Change → What To Measure / Course Correct → Works Best → Core Insight → Operational Patterns. *(Resistance section removed from UI.)*

---

## Acceptance criteria (MVP demo-ready)

A successful demo response must:

1. Open with the transformation / philosophy the user selected (`transformation_name`)
2. Reflect at least one calibration answer in readiness or bottleneck copy
3. Name a **first bottleneck** grounded in that philosophy's corpus (not unrelated topics)
4. Provide **start_with / avoid / introduce_later** steps that feel operational, not generic consulting
5. Include measurable **positive signals** and **warning signs**
6. End with a sharp **core organizational insight** tied to the philosophy
7. Cite real sources from the corpus (featured sources match the philosophy)
8. Read as advice stress-test, not org audit

---

## Buildathon positioning

**Pitch (30 seconds):**

> Startup and product advice is consumed everywhere but works conditionally. Reality Check lets you pick a transformation you want — empowered teams, stronger cohesion, AI-native PMs — then stress-tests it against how your org actually behaves under pressure. You get readiness, the first bottleneck, how to drive the change, and what to measure — grounded in Lenny's corpus.

**Why this wins:**

- Simple
- Sharp
- Demoable in 90 seconds
- Aligned to Lenny ecosystem
- Emotionally resonant (the mismatch headline)

**Demo script:**

1. Pick aspiration: "Make AI actually change workflows"
2. Calibrate: mid-size B2B, CEO overrides roadmap, recentralizes under revenue pressure
3. Report hero: transformation name + confidence badge
4. Environment readiness: supporting vs resisting conditions from answers
5. First bottleneck: what breaks first under pressure (philosophy-specific)
6. How to drive change: start with / avoid / introduce later
7. Core insight + operational pattern sources from corpus

---

## Out of scope (MVP)

- User auth / saved sessions
- Full open-ended chat ("ask anything")
- Vertical-specific playbooks (fintech, healthcare depth)
- Writing to corpus at runtime
- "Organizational intelligence platform" framing in UI or marketing

---

## Build sequence

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Intelligence corpus (458 objects, 45 patterns) | Done | `reality-check-intelligence.json`, `normalized-intelligence.json` |
| 2. Backend API + retrieval + LLM synthesis | Done | `reality_check/` — 25 tests passing |
| 3. Frontend (GroundWork) | Done | `frontend/` — aspiration → calibration → results; served at `/` |
| 4. Local testing with OpenAI | In progress | Checklist in [`REALITY_CHECK_API.md`](REALITY_CHECK_API.md) |
| 5. Replit deploy | **Next** | Import repo as-is; see **Replit deployment plan** in [`REALITY_CHECK_API.md`](REALITY_CHECK_API.md) |
| 6. Buildathon demo | Pending | Rehearse `empower_teams` or `ai_native_pms` |

**When you test locally:**

1. `source .venv/bin/activate && uvicorn reality_check.api.main:app --reload --port 8000`
2. Open http://localhost:8000/ (UI) or http://localhost:8000/docs (API)
3. Complete the GroundWork flow in the browser, or run `POST /api/stress-test` with `empower_teams` + exec override + recentralize
4. Run `pytest tests/ -v`; confirm transformation report sections are philosophy-relevant + real sources

**Replit (planned):** Import from GitHub → set `OPENAI_API_KEY` in Secrets → `uvicorn reality_check.api.main:app --host 0.0.0.0 --port $PORT`. No rebuild. Full runbook: [`REALITY_CHECK_API.md`](REALITY_CHECK_API.md#replit-deployment-plan-canonical).

---

## Success metrics (buildathon)

- User completes flow in < 3 minutes
- First bottleneck + readiness generate "that's exactly my org" reaction
- Sources are verifiable against corpus
- Judge understands pitch in one sentence without explanation

---

## Related documents

- Backend API runbook: [`REALITY_CHECK_API.md`](REALITY_CHECK_API.md)
- Backend implementation plan: `.cursor/plans/reality_check_backend_292e913f.plan.md`
- Corpus coverage: [`reality-check-coverage.md`](reality-check-coverage.md)
- Meta-patterns: [`normalized-intelligence.json`](normalized-intelligence.json)

# Reality Check API

Stress-test startup/product philosophies against operational reality.

- **Product spec:** [PRD.md](PRD.md)
- **Status:** Backend + frontend implemented — ready for local testing and Replit deploy (as-is)

---

## Implementation status

| Component | Status | Location |
|-----------|--------|----------|
| Philosophy registry (15 cards) | Done | `reality_check/data/philosophies.json` |
| Aspirations (15 transformations) | Done | `reality_check/data/aspirations.json` |
| Calibration (hybrid per philosophy) | Done | `calibration.json` + `philosophy_questions.json` |
| Philosophy-scoped retrieval | Done | `reality_check/engine/retrieval.py` + `relevance.py` |
| Distortion mapping | Done | `reality_check/engine/distortions.py` |
| LLM synthesis (OpenAI) | Done | `reality_check/engine/synthesis.py` |
| Fallback (no API key) | Done | Set `REALITY_CHECK_SKIP_LLM=1` |
| FastAPI routes | Done | `reality_check/api/main.py` |
| Tests (25 passing) | Done | `tests/test_api.py`, `tests/test_philosophy_relevance.py` |
| Frontend UI (GroundWork) | Done | `frontend/` — static HTML/CSS/JS, no build step |
| Static serving | Done | FastAPI mounts `frontend/` at `/` when folder exists |

---

## Project layout

```
reality_check/
  api/main.py              # FastAPI app
  api/schemas.py           # Request/response models
  data/philosophies.json   # 15 philosophy cards
  data/aspirations.json    # 15 user-facing transformations
  data/calibration.json    # Questions + distortions
  engine/
    loader.py              # Corpus loader
    retrieval.py           # Match philosophy + org → evidence
    relevance.py           # Philosophy-scoped object filtering
    distortions.py
    synthesis.py           # OpenAI + fallback
    prompts.py
frontend/
  index.html              # Aspiration → calibration → results report
  why.html                # Marketing / purpose page
  app.js                  # Same-origin fetch to /api/*
  styles.css
  assets/
reality-check-intelligence.json   # 458 objects (runtime)
normalized-intelligence.json      # 45 meta-patterns (runtime)
tests/
  test_api.py
  test_philosophy_relevance.py
  test_synthesis_timeout.py
PRD.md
REALITY_CHECK_API.md      # this file
.env                      # OPENAI_API_KEY (do not commit)
```

---

## Local setup (one time)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY to .env
```

---

## Run the server

```bash
source .venv/bin/activate
uvicorn reality_check.api.main:app --reload --port 8000
```

- **App UI:** http://localhost:8000/ (GroundWork frontend)
- **Swagger UI:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/api/health

**Important:** Do not export `REALITY_CHECK_SKIP_LLM=1` when starting the server if you want OpenAI synthesis. That flag forces the deterministic fallback (still philosophy-scoped).

After code changes, hard-refresh the browser (`Cmd + Shift + R`) or open with a cache-bust query (e.g. `/?v=29`).

---

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | (empty) | Required for LLM-polished responses |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for synthesis |
| `REALITY_CHECK_SKIP_LLM` | `0` | Set to `1` to skip OpenAI (instant fallback) |
| `REALITY_CHECK_ENV` | `development` | Set to `production` on Replit (disables `/docs`, trims `/api/health`) |
| `REALITY_CHECK_CORS_ORIGINS` | (empty) | Comma-separated allowed origins; empty = same-origin only |
| `REALITY_CHECK_ENABLE_DOCS` | auto | `1` to force Swagger; default off in production |
| `REALITY_CHECK_STRESS_TEST_API_KEY` | (empty) | If set, requires `X-Reality-Check-Key` on stress-test routes |
| `REALITY_CHECK_RATE_LIMIT_STRESS_TEST` | `6` | Max stress-test requests per IP per minute |
| `REALITY_CHECK_RATE_LIMIT_PREVIEW` | `20` | Max preview requests per IP per minute |
| `REALITY_CHECK_RATE_LIMIT_FEEDBACK` | `10` | Max feedback posts per IP per minute |
| `REALITY_CHECK_FEEDBACK_ENABLED` | `1` | Set to `0` to disable feedback endpoint |

---

## Testing checklist

### 1. Automated tests (no OpenAI spend)

```bash
source .venv/bin/activate
pytest tests/ -v
```

Expected: **30+ passed** (includes API, philosophy relevance, synthesis timeout, security).

Philosophy relevance tests ensure retrieval and fallback output stay on the selected philosophy (no cross-topic corpus bleed).

### 2. Retrieval only (instant)

```bash
curl -s http://localhost:8000/api/health | python3 -m json.tool
curl -s http://localhost:8000/api/aspirations | python3 -m json.tool
```

Or in Swagger: `POST /api/stress-test/preview`

### 3. Full stress test with LLM (~10–40 seconds)

Use Swagger at `/docs` → **POST /api/stress-test**, or:

```bash
curl -s -X POST http://localhost:8000/api/stress-test \
  -H "Content-Type: application/json" \
  -d '{
    "aspiration_id": "product_cohesion",
    "org_profile": {
      "stage": "scaleup",
      "size": "medium",
      "model": "b2b",
      "calibration": {
        "roadmap_override": "exec_override",
        "priority_chaos": "chaos_monthly",
        "revenue_pressure": "recentralize",
        "bottleneck": "design_gate",
        "design_led_gate_role": "design_bypassed"
      }
    }
  }' | python3 -m json.tool
```

**What to verify:**

- [ ] `transformation_name` matches the selected aspiration label
- [ ] `what_youre_trying_to_change` reflects the philosophy hook and operational meaning
- [ ] `environment_readiness` has supporting + resisting conditions (not binary)
- [ ] `first_bottleneck` uses design/cohesion language for `product_cohesion` — not unrelated AI newsletter patterns
- [ ] `how_to_drive_change` has `start_with`, `avoid`, `introduce_later`
- [ ] `core_organizational_insight` is one sharp sentence
- [ ] `sources` (≤2 featured) cite corpus objects that match the philosophy
- [ ] Tone feels like advice stress-test, not org audit

### 4. Recommended paths to try

| Entry | Why |
|-------|-----|
| `aspiration_id: team_ownership` | Autonomy vs exec override |
| `aspiration_id: product_cohesion` | Design-led cohesion under pressure |
| `philosophy_id: ai_native_pms` | Builder PM vs coordination trap |
| `move_fast` vs `design_led` | Contrasting philosophies |

### 5. Confidence / gap handling

Use `custom_philosophy` with obscure text to see `confidence: low` and `gap_notice`.

---

## API endpoints

| Method | Path | UX step | Notes |
|--------|------|---------|-------|
| GET | `/api/aspirations` | Step 1 | 15 transformations (preferred UI entry) |
| GET | `/api/aspirations/{id}` | Step 1 | Single aspiration + reflection layers |
| GET | `/api/philosophies` | Step 1 | 15 philosophy cards (API/direct) |
| GET | `/api/philosophies/{id}` | Step 1 | Single card + meta links |
| GET | `/api/calibration/questions` | Step 2 | Requires `philosophy_id` or `aspiration_id`; 5–6 questions + `role_options` |
| POST | `/api/stress-test` | Results | Full transformation report; OpenAI if key set |
| POST | `/api/stress-test/preview` | Debug | Retrieval bundle only, no LLM |
| GET | `/api/health` | — | Corpus counts |

### Request body (`POST /api/stress-test`)

```json
{
  "aspiration_id": "product_cohesion",
  "philosophy_id": null,
  "custom_philosophy": null,
  "org_profile": {
    "stage": "scaleup",
    "size": "medium",
    "model": "b2b",
    "user_role": "pm_product_lead",
    "calibration": {
      "roadmap_override": "exec_override",
      "priority_chaos": "chaos_monthly",
      "revenue_pressure": "recentralize",
      "bottleneck": "design_gate",
      "design_led_gate_role": "design_bypassed"
    }
  }
}
```

Provide **one of:** `aspiration_id`, `philosophy_id`, or `custom_philosophy`.

### Response shape (`RealityCheckResponse`)

| Field | UI section |
|-------|------------|
| `confidence`, `confidence_reason` | Hero badge |
| `transformation_name`, `philosophy_label` | Hero title |
| `what_youre_trying_to_change` | What You're Trying To Change (`goal`, `operational_meaning`) |
| `environment_readiness` | Is Your Environment Ready? (`supporting_conditions`, `resisting_conditions`, `readiness_summary`) |
| `first_bottleneck` | What Usually Becomes the First Bottleneck? (`bottleneck`, `what_teams_usually_do_next`, `unintended_effect`) |
| `likely_resistance` | *(returned by API; not shown in current UI)* |
| `how_to_drive_change` | How To Drive This Change Successfully (`start_with`, `avoid`, `introduce_later`) |
| `what_to_measure` | What To Measure (`positive_signals`, `warning_signs`) |
| `when_to_course_correct` | When To Course Correct (`course_correct_if`, `typical_adaptation`) |
| `where_this_works_best` | Where This Usually Works Best (`conditions`) |
| `core_organizational_insight` | Core Organizational Insight (quote block) |
| `sources`, `sources_more` | Operational Patterns (citations) |
| `gap_notice` | Banner when coverage is weak |
| `contradicting_philosophies` | Metadata (optional future UI) |

**Removed from UI (legacy):** pressure simulation timeline, headline mismatch, adaptation steps-only view, resistance section.

---

## Philosophy relevance (how bleed is prevented)

1. **Retrieval** — Intelligence objects come only from the selected philosophy's linked meta-patterns. Objects must contain that philosophy's keywords in their own text (linked-list membership alone is not enough).
2. **Synthesis prompt** — Instructs the model to ignore objects that do not fit the philosophy.
3. **Fallback** — Bottleneck and measures are built from the top-ranked philosophy object, not generic boilerplate.
4. **Tests** — `tests/test_philosophy_relevance.py` runs all 15 philosophies and blocks known cross-topic phrases (e.g. AI newsletter text on design-led runs).

---

## Architecture (data flow)

```
Aspiration or philosophy (Step 1)
    +
Org calibration (Step 2)
    → distortion tags
    → philosophy-scoped retrieval (meta-patterns + filtered objects)
    → OpenAI synthesis (or fallback)
    → RealityCheckResponse (transformation template)
    → GroundWork results report (frontend)
```

Corpus files are read at startup. No writes at runtime.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Fallback responses only | Remove `REALITY_CHECK_SKIP_LLM=1`; restart server; check `.env` has key |
| Old UI still showing | Hard refresh; confirm `app.js?v=29` and `styles.css?v=29` in page source |
| Wrong philosophy content in a section | Check `/api/stress-test/preview` intelligence IDs; run `pytest tests/test_philosophy_relevance.py` |
| `ModuleNotFoundError: reality_check` | Run from repo root; `source .venv/bin/activate` |
| Slow response | Normal for LLM path (10–40s); use `/preview` or `REALITY_CHECK_SKIP_LLM=1` |
| Empty sources | Check `/api/health` — corpus files must be in repo root |
| Port 8000 in use | `uvicorn ... --port 8001` or kill existing process |

---

## Replit deployment (canonical)

**Do not rebuild on Replit.** Import this repo; `.replit` already sets the run command and `REALITY_CHECK_ENV=production`.

### 1. Create the Repl

1. Go to [replit.com](https://replit.com) → **Create Repl** → **Import from GitHub** (or upload the repo).
2. Replit detects Python via `.replit` and `requirements.txt`.

### 2. Secrets (required)

Open **Secrets** (lock icon) and add:

| Secret | Value |
|--------|--------|
| `OPENAI_API_KEY` | Your OpenAI key (`sk-...`) |

Do **not** put the key in code or `.env` committed to git.

### 3. Optional Secrets / env

| Key | Recommended for public demo |
|-----|-----------------------------|
| `REALITY_CHECK_ENV` | `production` (already in `.replit`) |
| `REALITY_CHECK_CORS_ORIGINS` | `https://YOUR-REPL-NAME.replit.app` (only if you split frontend host) |
| `REALITY_CHECK_SKIP_LLM` | `0` for full LLM reports; `1` for free instant fallback demo |
| `REALITY_CHECK_STRESS_TEST_API_KEY` | Leave **unset** for browser UI (users cannot see a secret). Set only if you lock API access for scripts. |

### 4. Install and run

Replit runs automatically. Manual shell:

```bash
pip install -r requirements.txt
uvicorn reality_check.api.main:app --host 0.0.0.0 --port $PORT
```

### 5. Publish

Use **Deploy** → get your `*.replit.app` URL. Share that link.

### 6. Verify after deploy

| URL | Expected |
|-----|----------|
| `/` | GroundWork UI |
| `/api/health` | `status: ok` + corpus counts (no `llm_configured` in production) |
| `/docs` | **404** in production |
| Complete one aspiration → results | LLM report in ~10–40s (or fallback if no key) |

### Security built in (production)

- Rate limits on stress-test, preview, and feedback
- Swagger disabled when `REALITY_CHECK_ENV=production`
- CORS off unless you set `REALITY_CHECK_CORS_ORIGINS`
- `custom_philosophy` capped at 500 chars; calibration answers bounded
- Feedback stores rating + comment + slim summary only (no full org profile)
- Privacy notice in site footer; no third-party analytics

### Cost control tips

- Keep default rate limits (`6` stress-tests / IP / minute)
- Monitor usage in the [OpenAI dashboard](https://platform.openai.com/usage)
- For a no-cost demo booth: set `REALITY_CHECK_SKIP_LLM=1` in Secrets

---

## What's next

1. Run `pytest tests/ -v` before each demo
2. Rehearse 2–3 aspiration paths (see recommended table above)
3. Deploy to Replit using this runbook
4. Demo script: [PRD.md](PRD.md)

---

## Regenerating corpus (optional)

```bash
python3 merge_reality_check.py && python3 semantic_dedupe.py
python3 compress_patterns.py
```

Not required for running the API.

# GroundWork

**Aspiration → operational reality**

GroundWork helps PMs, founders, and leaders stress-test startup and product philosophies against operational reality. Pick a transformation you care about, answer a short calibration, and get a personalized report on environment readiness, bottlenecks, and what to measure — grounded in patterns from [Lenny's Podcast](https://www.lennyspodcast.com) and [Lenny's Newsletter](https://www.lennysnewsletter.com).

Powered by **Reality Check** (FastAPI + corpus retrieval + optional OpenAI synthesis).

## Quick start

```bash
git clone https://github.com/chaiitanyaanaik/groundwork.git
cd groundwork

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY
uvicorn reality_check.api.main:app --reload --port 8000
```

- **App:** http://localhost:8000/
- **API docs:** http://localhost:8000/docs (disabled in production — see below)
- **Health:** http://localhost:8000/api/health

**Tests (no OpenAI spend):**

```bash
pytest tests/ -v
```

**Corpus-only / instant responses (no API key):** set `REALITY_CHECK_SKIP_LLM=1` in `.env`.

## How it works

1. Choose an **aspiration** (e.g. empower teams, move faster, recentralize).
2. Complete **calibration** questions about your org.
3. Receive a **stress-tested report**: environment readiness, first bottleneck, how to drive change, metrics, and corpus-backed operational patterns.

See [`PRD.md`](PRD.md) for product spec and [`REALITY_CHECK_API.md`](REALITY_CHECK_API.md) for API schema, verification checklist, and Replit deployment.

## Repo layout

| Path | Purpose |
|------|---------|
| `frontend/` | GroundWork UI (static HTML/CSS/JS; served at `/`) |
| `reality_check/` | FastAPI backend, retrieval, synthesis |
| `reality-check-intelligence.json` | Intelligence objects (runtime corpus) |
| `normalized-intelligence.json` | Meta-patterns (runtime) |
| `reality_check/data/` | Philosophies, aspirations, calibration |
| `tests/` | API, security, relevance, timeout tests |
| `evals/` | LLM-as-judge eval harness — see [`evals/README.md`](evals/README.md) |
| `newsletters/`, `podcasts/` | Starter Lenny content (markdown) |
| `index.json` | Index of starter posts and transcripts |
| `LICENSE.md` | Dataset and project license terms |

## Environment variables

Copy `.env.example` → `.env`. Never commit `.env`.

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Required for LLM-polished reports |
| `OPENAI_MODEL` | Default: `gpt-4o-mini` |
| `REALITY_CHECK_SKIP_LLM` | `1` = instant fallback (no OpenAI) |
| `OPENAI_TIMEOUT_SECONDS` | Hard cap; over limit → corpus fallback |
| `REALITY_CHECK_ENV` | `production` on deploy (hides `/docs`, tightens health) |
| `REALITY_CHECK_CORS_ORIGINS` | Comma-separated origins for cross-origin API |
| `REALITY_CHECK_STRESS_TEST_API_KEY` | Optional API key for scripted clients |

Full list: [`.env.example`](.env.example) and [`REALITY_CHECK_API.md`](REALITY_CHECK_API.md).

## Evals (optional)

Quality checks with a separate judge model:

```bash
python evals/run_eval.py --list
python evals/run_eval.py --scenario experiment_exec_kill_pm --save
python evals/run_eval.py --all --save
```

Details: [`evals/README.md`](evals/README.md).

## Deploy

Configured for **Replit** (`.replit`). Set `REALITY_CHECK_ENV=production` and any CORS origins you need. See the **Replit deployment plan** in [`REALITY_CHECK_API.md`](REALITY_CHECK_API.md).

## Dataset & attribution

This repo builds on Lenny Rachitsky’s public **starter pack** (10 newsletter posts + 50 podcast transcripts) plus derived operational-intelligence artifacts for Reality Check.

- Starter content: `newsletters/`, `podcasts/`, `index.json`
- Full archive (paid): [lennysdata.com](https://www.lennysdata.com)

Usage terms: [`LICENSE.md`](LICENSE.md).

## License

See [`LICENSE.md`](LICENSE.md) for Lenny dataset terms and starter-pack restrictions.

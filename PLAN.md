# hackhunt — Plan

Finds open hackathons, filters and ranks them for me, and emails a daily digest.
Later phases add LLM idea briefs and a "go" → kickoff flow.

## Phase 1 (build this now)

Fetch → filter → score → digest. Devpost only. No LLM.

### Runs on
- GitHub Actions cron, daily at 06:00 UTC (07:00 Lagos), plus `workflow_dispatch` for manual runs.
- Also runnable locally: `python -m hackhunt run` and `python -m hackhunt run --dry-run` (prints the digest, sends nothing).

### Layout (mirror my jobhunt_app structure)
```
hackhunt/
  cli.py          # run, --dry-run
  config.py       # loads settings.json + env vars
  fetchers/
    devpost.py    # first source
  models.py       # Hackathon dataclass
  filters.py      # hard rules
  scoring.py      # rule-based fit score
  storage.py      # SQLite: seen hackathons
  email_delivery.py
settings.json     # my filters and interests (no secrets)
state/hackhunt.db # committed back by the workflow
.github/workflows/daily.yml
```

### Fetch (Devpost)
- Devpost has an unofficial JSON listing endpoint (`/api/hackathons`, open status). Check that it still works and what fields it returns before writing the fetcher. If it's gone, fall back to the listing page HTML.
- Paginate, be polite (small delay, real User-Agent), and fail soft: if a source breaks, still send the digest and note the error at the bottom.

### Hackathon model
id, source, title, url, organizer, start/end dates, submission deadline, online/in-person, location, prize total (number + raw text), themes/tags, eligibility text, registrations count, first_seen.

### Filters (hard, from settings.json)
- online only (default true)
- deadline at least `min_days_left` away (default 5)
- skip if eligibility text clearly excludes Nigeria/students (simple keyword check, log what was dropped and why)
- skip already-digested ones (unless the deadline is in ≤3 days and I haven't seen it flagged as urgent)

### Scoring (rule-based, explainable)
- theme/tag match with my interests list (AI/agents, backend, Python/Django, Go, fintech, Africa/social impact, dev tools)
- prize size (log-scaled)
- time left (sweet spot 7–30 days)
- fewer registrations = small bonus
- Store the score breakdown so the digest can say *why* each one ranked.

### Digest email
- Gmail SMTP with an app password (same approach as jobhunt). Secrets from env / GitHub Secrets: `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `DIGEST_TO`.
- Top 10 new ones: title, link, deadline + days left, prize, themes, score with a one-line reason.
- Separate "closing soon" section.
- Skip sending if nothing new (unless `--force`).

### Workflow
- Python 3.12, pip cache, run, then commit `state/hackhunt.db` back only if it changed.

### Done when
- `--dry-run` locally prints a sensible ranked list from live Devpost data.
- A manual workflow run sends me a real email.
- A second run the same day sends nothing new.
- Basic tests for filters and scoring.

## Phase 2 (later)
- LLM briefs for the top 2–3: read rules + judging criteria, write 2–3 ideas with Ghost Data–level depth. Provider: TBD (Gemini free tier vs Claude API).
- More sources: MLH, DoraHacks, lablab.ai.

## Phase 3 (later)
- Bot opens a GitHub Issue per briefed hackathon; I comment "go".
- "go" triggers kickoff: new repo + PLAN.md with milestones up to the deadline, then pings me to review.
- Registration stays a manual click by me.

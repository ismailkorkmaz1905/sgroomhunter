# WordGames

This repository contains only the `WordGames` app under `apps/wordgames`.

## Setup

```powershell
pip install -r requirements.txt
```

## Run Locally

```powershell
python apps/wordgames/serve.py
```

Then open `http://127.0.0.1:5051`.

## Main Routes

- `/en`
- `/tr`
- `/nl`
- `/id`
- `/ms`
- `/en/daily-ladder`
- `/en/word-scramble`
- `/en/typo-hunt`
- `/tr/daily-ladder`
- `/tr/word-scramble`
- `/tr/typo-hunt`
- `/nl/daily-ladder`
- `/nl/word-scramble`
- `/nl/typo-hunt`
- `/id/daily-ladder`
- `/id/word-scramble`
- `/id/typo-hunt`
- `/ms/daily-ladder`
- `/ms/word-scramble`
- `/ms/typo-hunt`
- `/analytics`
- `/analytics-summary`

## Deploy to Render

This repo includes a Render Blueprint at `render.yaml`.

- Build Command: `pip install -r apps/wordgames/requirements-render.txt`
- Start Command: `gunicorn apps.wordgames.render_wsgi:app --bind 0.0.0.0:$PORT`

## Notes

- `apps/wordgames/analytics.sqlite3` is local runtime state and stays untracked.
- Server log files stay untracked.

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

## Deploy to GitHub Pages

Run the static export locally:

```powershell
$env:WORDSPRINT_BASE_PATH="/wordsprint"
python apps/wordgames/export_static.py
```

The export writes the static site to `dist`.

In GitHub, enable Pages in the repository settings and choose GitHub Actions as the source. The Pages workflow deploys `dist` to:

```text
https://ismailkorkmaz1905.github.io/wordsprint/
```

Render remains the Flask deployment and still supports backend analytics. GitHub Pages is static only, so analytics endpoints and profile-name POST storage are not available there.

## Notes

- `apps/wordgames/analytics.sqlite3` is local runtime state and stays untracked.
- Server log files stay untracked.

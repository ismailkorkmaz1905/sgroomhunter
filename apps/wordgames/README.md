# WordGames

Minimal Flask-served, frontend-played multilingual word game app.

## Run

```powershell
python apps/wordgames/serve.py
```

Then open:

```text
http://127.0.0.1:5051
```

## Routes

- `/en`
- `/tr`
- `/nl`
- `/id`
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

## Render

Render-ready files:

- `render.yaml`
- `apps/wordgames/render_wsgi.py`
- `apps/wordgames/requirements-render.txt`

Manual Render setup:

- Build Command: `pip install -r apps/wordgames/requirements-render.txt`
- Start Command: `gunicorn apps.wordgames.render_wsgi:app --bind 0.0.0.0:$PORT`

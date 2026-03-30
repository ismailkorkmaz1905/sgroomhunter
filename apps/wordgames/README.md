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
- `/en/privacy`
- `/en/terms`
- `/analytics`
- `/analytics-summary`

## Privacy-friendly analytics

WordGames keeps minimal server-side aggregate analytics only.

- No raw IP storage
- No analytics cookies
- No device fingerprinting
- Aggregates include route, language, status code, device type, browser family, and referrer domain

To protect `/analytics` and `/analytics-summary`, set these environment variables in Render:

- `ANALYTICS_USERNAME`
- `ANALYTICS_PASSWORD`

When these are set, the analytics endpoint requires HTTP Basic Auth.

## Ad readiness

WordGames includes the free ad-readiness setup:

- `/ads.txt`
- `/robots.txt`
- `/sitemap.xml`
- localized `Privacy`, `Terms`, and `About` pages

To publish a real AdSense line later, set:

- `ADSENSE_PUBLISHER_ID`

## Render

Render-ready files:

- `render.yaml`
- `apps/wordgames/render_wsgi.py`
- `apps/wordgames/requirements-render.txt`

## iPhone home screen / PWA

WordGames now includes:

- `manifest.webmanifest`
- root-scoped `service-worker.js`
- Apple touch icon and PWA icons

On iPhone:

1. Open the deployed site in Safari
2. Tap `Share`
3. Tap `Add to Home Screen`

Manual Render setup:

- Build Command: `pip install -r apps/wordgames/requirements-render.txt`
- Start Command: `gunicorn apps.wordgames.render_wsgi:app --bind 0.0.0.0:$PORT`

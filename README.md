# net-tools

Local toolbox repo for automation scripts and lightweight web apps.

## Setup

```powershell
pip install -r requirements.txt
```

## Apps

### WordGames

Multilingual frontend-only word game app under `apps/wordgames`.

Run:

```powershell
python apps/wordgames/serve.py
```

Open:

```text
http://127.0.0.1:5051
```

Routes:

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

### Ad readiness

WordGames now includes the no-cost prep pieces for future ad approval:

- `ads.txt` endpoint at `/ads.txt`
- `robots.txt`
- `sitemap.xml`
- localized `Privacy`, `Terms`, and `About` pages

To publish a real `ads.txt` line later, set:

- `ADSENSE_PUBLISHER_ID`

### Deploy to Render

This repo includes a Render Blueprint for `WordGames` at `render.yaml`.

Render settings:

- Build Command: `pip install -r apps/wordgames/requirements-render.txt`
- Start Command: `gunicorn apps.wordgames.render_wsgi:app --bind 0.0.0.0:$PORT`

You can either:

- create a new Web Service manually and paste the commands above, or
- create a new Blueprint in Render and point it at this repo

### PropertyGuru automation

Core files:

- `automation/propertyguru/propertyguru_monitor.py`
- `automation/propertyguru/propertyguru_monitor_config.json`
- `automation/propertyguru/propertyguru_outreach_template.txt`
- `automation/propertyguru/propertyguru_whatsapp_helper.py`
- `automation/propertyguru/propertyguru_message_template.txt`

Commands:

```powershell
python automation/propertyguru/propertyguru_monitor.py scan-once
python automation/propertyguru/propertyguru_monitor.py run-once
python automation/propertyguru/propertyguru_monitor.py run
python automation/propertyguru/propertyguru_whatsapp_helper.py
```

## Notes

- Secrets are intentionally not included in tracked config.
- Use local config files for real tokens and chat ids.
- Runtime state, logs, browser profiles, and temporary outputs should stay untracked.

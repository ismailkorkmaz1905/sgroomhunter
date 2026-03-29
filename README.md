# PropertyGuru Automation

PropertyGuru listing monitor and WhatsApp outreach toolkit.

## Included

- `automation/propertyguru/propertyguru_monitor.py`
- `automation/propertyguru/propertyguru_monitor_config.json`
- `automation/propertyguru/propertyguru_outreach_template.txt`
- `automation/propertyguru/propertyguru_whatsapp_helper.py`
- `automation/propertyguru/propertyguru_message_template.txt`

## What It Does

- scans PropertyGuru search pages on a schedule
- filters listings by price, area, bathroom, and rule keywords
- sends candidate listings to Telegram for approval
- after approval, opens or sends a WhatsApp message

## Setup

```powershell
pip install -r requirements.txt
```

## Commands

Shortlist once:

```powershell
python automation/propertyguru/propertyguru_monitor.py scan-once
```

Run one cycle:

```powershell
python automation/propertyguru/propertyguru_monitor.py run-once
```

Run continuously:

```powershell
python automation/propertyguru/propertyguru_monitor.py run
```

WhatsApp helper:

```powershell
python automation/propertyguru/propertyguru_whatsapp_helper.py
```

## Notes

- Secrets are intentionally not included in the tracked config.
- Use a local config file such as `propertyguru_monitor_config.local.json` for real tokens and chat ids.
- Runtime state, logs, and browser profiles are ignored by git.

# WordSprint

WordSprint is a static-first multilingual game site for GitHub Pages.

Live URL:

```text
https://ismailkorkmaz1905.github.io/wordsprint/
```

## Setup

```powershell
pip install -r requirements.txt
```

## Local Flask Preview

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

## Deploy to GitHub Pages

Run the static export locally:

```powershell
$env:WORDSPRINT_BASE_PATH="/wordsprint"
python apps/wordgames/export_static.py
```

The export writes the static site to `dist`.

Test the exported site locally:

```powershell
mkdir C:\tmp\pages-test\wordsprint
Copy-Item -Recurse -Force dist\* C:\tmp\pages-test\wordsprint\
python -m http.server 8000 --directory C:\tmp\pages-test
```

Then open:

```text
http://localhost:8000/wordsprint/
```

The GitHub Actions workflow deploys `dist` to:

```text
https://ismailkorkmaz1905.github.io/wordsprint/
```

## Data

Player data is localStorage-only. The GitHub Pages version has no server-side database, profile POST endpoint, or backend usage tracking.

## Notes

- Server log files stay untracked.

# WordSprint

Static-first multilingual word game app.

## Local Preview

```powershell
python apps/wordgames/serve.py
```

Then open:

```text
http://127.0.0.1:5051
```

## Static Export

```powershell
$env:WORDSPRINT_BASE_PATH="/wordsprint"
python apps/wordgames/export_static.py
```

The export writes the GitHub Pages site to `dist`.

## Local Static Test

```powershell
mkdir C:\tmp\pages-test\wordsprint
Copy-Item -Recurse -Force dist\* C:\tmp\pages-test\wordsprint\
python -m http.server 8000 --directory C:\tmp\pages-test
```

Open:

```text
http://localhost:8000/wordsprint/
```

## Data

Player name, history, and game progress are stored in browser localStorage only. There is no server-side database, profile POST endpoint, or backend usage tracking.

## PWA

WordSprint includes:

- `manifest.webmanifest`
- `service-worker.js`
- Apple touch icon and PWA icons
